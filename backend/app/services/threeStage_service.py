"""
threeStage_service.py
-------------------
使用三階段模型 (Macro -> Local -> Accompaniment) 為旋律 MIDI 生成鋼琴伴奏。

推理流程改編自：
  model/pop909_three_stage_chord/inference.py

公開函式：
  generate(melody_midi_bytes) → tuple[bytes, list[list[str]]]
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
import tempfile
import math
from typing import Literal

import torch
import symusic
import logging
import music21
from miditok import REMI, TokSequence
from app.services import midi_service

logger = logging.getLogger(__name__)


# ── 讓 service 能 import 同目錄的 threeStage_*.py ─────────────────────
_SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
if _SERVICE_DIR not in sys.path:
    sys.path.insert(0, _SERVICE_DIR)

from threeStage_macro_transformer import POP909MacroChordPredictor  # Stage 1
from threeStage_transformer import POP909ChordPredictor             # Stage 2
from threeStage_accom_transformer import POP909Transformer          # Stage 3

# ── 資源根目錄 ────────────────────────────────────────────────────────────────
_RESOURCES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources",
    "threeStage"
)

_MACRO_CHECKPOINT = os.path.join(_RESOURCES, "macro_model.pth")
_MACRO_TOKENIZER = os.path.join(_RESOURCES, "macro_tokenizer.json")
_MACRO_CHORD_VOCAB = os.path.join(_RESOURCES, "macro_chord_vocab.json")

_LOCAL_CHECKPOINT = os.path.join(_RESOURCES, "local_model.pth")
_LOCAL_TOKENIZER = os.path.join(_RESOURCES, "local_tokenizer.json")
_LOCAL_CHORD_VOCAB = os.path.join(_RESOURCES, "local_chord_vocab.json")

_ACCOM_CHECKPOINT = os.path.join(_RESOURCES, "accom_model.pth")

# ── 裝置 ──────────────────────────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

PITCH_MAP = {
    "C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
    "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11,
}

# ── 視窗滑動參數 ─────────────────────────────────────────────────────────────
WINDOW_BARS = 4
STRIDE_BARS = 2
PREFIX_BARS = WINDOW_BARS - STRIDE_BARS  # = 2
MAX_GEN_LEN = 2048

# ── 和弦格式正規化（C:maj → C, A:min → Am, N → N）─────────────────────────
_QUALITY_SUFFIX: dict[str, str] = {
    "maj": "",
    "min": "m",
    "dim": "dim",
    "aug": "aug",
    "sus2": "sus2",
    "sus4": "sus4",
    "maj7": "maj7",
    "min7": "m7",
    "7": "7",
    "hdim7": "m7b5",
    "dim7": "dim7",
    "minmaj7": "mM7",
    "maj6": "6",
    "min6": "m6",
}


def _normalize_chord_name(raw: str) -> str:
    """
    把訓練字典格式的和弦名稱轉為前端可讀的標準格式。
    例：C:maj → C, A:min → Am, G:maj/5 → G, N → N
    """
    if not raw or raw in ("N", "PAD", "BOS", "EOS", "MASK"):
        return "N"
    raw_base = raw.split("/")[0]
    if ":" not in raw_base:
        return raw_base
    root, quality = raw_base.split(":", 1)
    suffix = _QUALITY_SUFFIX.get(quality, quality)
    return root + suffix


# ── Lazy-loaded 快取 ────────────────────────────────────────────────────────
_macro_model: POP909MacroChordPredictor | None = None
_macro_tokenizer: REMI | None = None
_macro_chord_to_id: dict | None = None

_local_model: POP909ChordPredictor | None = None
_local_tokenizer: REMI | None = None
_local_chord_to_id: dict | None = None

_accom_model: POP909Transformer | None = None


# ============================================================
# 工具函式
# ============================================================

def analyze_and_transpose_music21(input_midi, temp_midi, key_source: str | None = None):
    """
    偵測調性並將 MIDI 移調至 C/Am，回傳 (semitones, key_str)。
    key_source: 若提供，從此路徑偵測調性（用於上傳 MIDI 的原始檔），
                但仍對 input_midi 進行移調（input_midi 可能是預處理後的旋律）。
    優先順序：
      1. 讀取 MIDI 內建的 key_signature Meta Event
      2. 無標記時，使用 music21 分析音符組成
    """
    detect_from = key_source if key_source else input_midi
    key_str = midi_service.read_key_str_from_midi(detect_from)

    # ── Step 1: MIDI 內建調號 ──────────────────────────────────────────────────
    embedded = midi_service.read_key_signature_from_midi(detect_from)
    if embedded is not None:
        _, _, semitones_to_c = embedded
        if semitones_to_c != 0:
            logger.info("使用 MIDI 內建調號，移調 %+d 半音", semitones_to_c)
            score = music21.converter.parse(input_midi)
            interval = music21.interval.Interval(semitones_to_c)
            transposed_score = score.transpose(interval)
            transposed_score.write("midi", fp=temp_midi)
        else:
            logger.info("MIDI 內建調號為 C/Am，無需移調。")
            score = music21.converter.parse(input_midi)
            score.write("midi", fp=temp_midi)
        return semitones_to_c, (key_str if key_str else "C")

    # ── Step 2: Fallback — music21 演算法偵測 ─────────────────────────────────
    logger.info("MIDI 無內建調號，改用 music21 分析...")
    detect_score = music21.converter.parse(detect_from)
    key = detect_score.analyze("key")
    logger.info("偵測到原曲調性: %s %s", key.tonic.name, key.mode)

    if key.mode == "minor":
        key_str = key.tonic.name + "m"
        target_pitch = music21.pitch.Pitch("A")
    else:
        key_str = key.tonic.name
        target_pitch = music21.pitch.Pitch("C")
    key_str = key_str.replace("-", "b")

    interval = music21.interval.Interval(key.tonic, target_pitch)
    semitones = interval.semitones

    mel_score = music21.converter.parse(input_midi)
    if semitones != 0:
        logger.info("轉調至 %s %s (平移 %d 半音)", target_pitch.name, key.mode, semitones)
        transposed_score = mel_score.transpose(interval)
        transposed_score.write("midi", fp=temp_midi)
    else:
        logger.info("已是目標調性，無需轉調。")
        mel_score.write("midi", fp=temp_midi)

    return semitones, key_str



def sample_token(logits, temperature=1.2, top_k=3, invalid_ids=None):
    if invalid_ids:
        for idx in invalid_ids:
            logits[idx] = -float("Inf")
    logits = logits / temperature
    if top_k > 0:
        top_v, top_idx = torch.topk(logits, top_k)
        probs = torch.softmax(top_v, dim=-1)
        sampled_i = torch.multinomial(probs, 1).item()
        return top_idx[sampled_i].item()
    return logits.argmax().item()


def top_k_top_p_filtering(logits: torch.Tensor, top_k: int = 0, top_p: float = 1.0) -> torch.Tensor:
    if top_k > 0:
        top_k = min(top_k, logits.size(-1))
        kth_val = torch.topk(logits, top_k).values[..., -1, None]
        logits = logits.masked_fill(logits < kth_val, float("-inf"))
    if top_p < 1.0:
        sorted_logits, sorted_idx = torch.sort(logits, descending=True)
        cum_probs = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)
        to_remove = cum_probs - torch.softmax(sorted_logits, dim=-1) > top_p
        sorted_logits = sorted_logits.masked_fill(to_remove, float("-inf"))
        logits = torch.zeros_like(logits).scatter_(-1, sorted_idx, sorted_logits)
    return logits


def get_sampling_params(density: float):
    top_p = 1.0
    if density <= 0.2: top_k, top_p = 2, 0.8
    elif density <= 0.4: top_k, top_p = 3, 0.85
    elif density <= 0.6: top_k, top_p = 4, 0.90
    elif density <= 0.8: top_k, top_p = 5, 0.95
    else: top_k, top_p = 6, 0.98
    return top_k, top_p


def extract_window_notes(notes, start_tick, end_tick, pitch_offset):
    result = []
    for n in notes:
        if start_tick <= n.time < end_tick:
            new_n = copy.copy(n)
            new_n.pitch = max(0, min(127, n.pitch + pitch_offset))
            new_n.time = n.time - start_tick
            new_n.duration = min(n.duration, end_tick - n.time)
            result.append(new_n)
    return result


def notes_to_tokens(notes, tpq, numerator, denominator, tokenizer):
    score = symusic.Score(tpq)
    score.time_signatures.append(symusic.TimeSignature(0, numerator, denominator))
    track = symusic.Track()
    track.notes = notes
    score.tracks.append(track)
    encoded = tokenizer(score)
    return list(encoded[0].ids if isinstance(encoded, list) else getattr(encoded, "ids", encoded))


def tokens_to_notes(token_ids, tokenizer, tpq):
    id_to_token = {v: k for k, v in tokenizer.vocab.items()}
    tokens_str = [id_to_token.get(t, "UNK") for t in token_ids]
    seq = TokSequence(ids=token_ids, tokens=tokens_str)
    acc_score = tokenizer.decode([seq])
    acc_tpq = acc_score.ticks_per_quarter
    if not acc_score.tracks or not acc_score.tracks[0].notes: return []
    notes = list(acc_score.tracks[0].notes)
    if acc_tpq != tpq:
        ratio = tpq / acc_tpq
        for n in notes:
            n.time = int(n.time * ratio)
            n.duration = max(1, int(n.duration * ratio))
    return notes


# ============================================================
# Lazy 模型載入
# ============================================================

def _get_macro() -> tuple[POP909MacroChordPredictor, REMI, dict]:
    global _macro_model, _macro_tokenizer, _macro_chord_to_id
    if _macro_model is None:
        logger.info("正在載入 Stage 1 (Macro) Tokenizer & Vocab...")
        _macro_tokenizer = REMI(params=_MACRO_TOKENIZER)
        with open(_MACRO_CHORD_VOCAB, "r", encoding="utf-8") as f:
            _macro_chord_to_id = json.load(f)
        
        logger.info("正在載入 Stage 1 (Macro) Checkpoint...")
        ckpt = torch.load(_MACRO_CHECKPOINT, map_location="cpu", weights_only=False)
        state = {k.replace("_orig_mod.", ""): v for k, v in ckpt["model_state_dict"].items()}
        
        src_vocab_size = len(_macro_tokenizer.vocab)
        tgt_vocab_size = len(_macro_chord_to_id)
        
        m = POP909MacroChordPredictor(src_vocab_size, tgt_vocab_size).to(DEVICE)
        m.load_state_dict(state)
        m.eval()
        _macro_model = m
    return _macro_model, _macro_tokenizer, _macro_chord_to_id


def _get_local() -> tuple[POP909ChordPredictor, REMI, dict]:
    global _local_model, _local_tokenizer, _local_chord_to_id
    if _local_model is None:
        logger.info("正在載入 Stage 2 (Local) Tokenizer & Vocab...")
        _local_tokenizer = REMI(params=_LOCAL_TOKENIZER)
        with open(_LOCAL_CHORD_VOCAB, "r", encoding="utf-8") as f:
            _local_chord_to_id = json.load(f)
        
        logger.info("正在載入 Stage 2 (Local) Checkpoint...")
        ckpt = torch.load(_LOCAL_CHECKPOINT, map_location="cpu", weights_only=False)
        state = {k.replace("_orig_mod.", ""): v for k, v in ckpt["model_state_dict"].items()}
        
        src_vocab_size = len(_local_tokenizer.vocab)
        tgt_vocab_size = len(_local_chord_to_id)
        
        m = POP909ChordPredictor(src_vocab_size, tgt_vocab_size).to(DEVICE)
        m.load_state_dict(state)
        m.eval()
        _local_model = m
    return _local_model, _local_tokenizer, _local_chord_to_id


def _get_accom() -> POP909Transformer:
    global _accom_model
    if _accom_model is None:
        logger.info("正在載入 Stage 3 (Accompaniment) Checkpoint...")
        ckpt = torch.load(_ACCOM_CHECKPOINT, map_location="cpu", weights_only=False)
        state = {k.replace("_orig_mod.", ""): v for k, v in ckpt["model_state_dict"].items()}
        
        _, local_tokenizer, local_chord_to_id = _get_local()
        src_vocab_size = len(local_tokenizer.vocab)
        tgt_vocab_size = len(local_chord_to_id) + 1 # +1 for SEP or similar if needed in transformer_accom.py, actually in inference.py it's len(local_chord_to_id) + 1
        
        m = POP909Transformer(src_vocab_size, tgt_vocab_size).to(DEVICE)
        m.load_state_dict(state)
        m.eval()
        _accom_model = m
    return _accom_model


# ============================================================
# 推理邏輯
# ============================================================

@torch.no_grad()
def generate_window_accom(
    model, tokenizer, src_ids, chords_ids, prefix_ids, bar_id,
    density, temperature, window_idx, is_first, target_bars
):
    vocab = tokenizer.vocab
    BOS_ID = vocab.get("BOS_None", vocab.get("BOS", 0))
    EOS_ID = vocab.get("EOS_None", vocab.get("EOS", 0))

    top_k, top_p = get_sampling_params(density)
    early_stop_bars = target_bars * 1.0
    force_eos_bars = target_bars * 1.10

    tgt_ids = [BOS_ID] + prefix_ids
    src_tensor = torch.tensor([src_ids], dtype=torch.long).to(DEVICE)
    chords_tensor = torch.tensor([chords_ids], dtype=torch.long).to(DEVICE)

    with torch.autocast(device_type="cuda" if DEVICE == "cuda" else "cpu", dtype=torch.bfloat16 if DEVICE == "cuda" else torch.float32):
        for step in range(len(prefix_ids), MAX_GEN_LEN):
            tgt_tensor = torch.tensor([tgt_ids], dtype=torch.long).to(DEVICE)
            logits = model(src_tensor, tgt_tensor, chords_tensor)
            next_logits = logits[0, -1, :]

            invalid_ids = [vocab.get(t, 0) for t in ["BOS_None", "MASK_None", "SEP_None", "N_None"]]
            for idx in invalid_ids:
                if idx != 0: next_logits[idx] = float("-inf")
            next_logits[0] = float("-inf")  # PAD

            current_bar_count = tgt_ids.count(bar_id)
            if current_bar_count < early_stop_bars:
                next_logits[EOS_ID] = float("-inf")
            elif current_bar_count >= force_eos_bars:
                next_logits[EOS_ID] += 20.0

            filtered = top_k_top_p_filtering(next_logits, top_k, top_p)
            probs = torch.softmax(filtered / temperature, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1).item()
            tgt_ids.append(next_id)

            if next_id == EOS_ID:
                break

    return [t for t in tgt_ids if t not in (BOS_ID, EOS_ID)]


def _run_inference(
    melody_midi_bytes: bytes,
    complexity: float = 0.5,
    creativity: float = 1.0,
    original_midi_bytes: bytes | None = None,
    update_progress=None,
) -> tuple[bytes, list[list[str]]]:
    _p = update_progress or (lambda prog, label='': None)
    _p(0.05, "Loading models...")
    macro_model, macro_tokenizer, macro_chord_to_id = _get_macro()
    local_model, local_tokenizer, local_chord_to_id = _get_local()
    accom_model = _get_accom()

    macro_id_to_chord = {v: k for k, v in macro_chord_to_id.items()}
    local_id_to_chord = {v: k for k, v in local_chord_to_id.items()}

    vocab = local_tokenizer.vocab
    local_BOS = vocab.get("BOS_None", vocab.get("BOS", 0))
    local_EOS = vocab.get("EOS_None", vocab.get("EOS", 0))
    local_SEP = vocab.get("SEP_None", vocab.get("SEP", 0))

    with tempfile.NamedTemporaryFile(suffix=".mid", prefix="accom_tmp_", delete=False) as f_in:
        f_in.write(melody_midi_bytes)
        tmp_path = f_in.name

    tmp_key_source = None
    if original_midi_bytes is not None:
        with tempfile.NamedTemporaryFile(suffix=".mid", prefix="key_src_", delete=False) as f_ks:
            f_ks.write(original_midi_bytes)
            tmp_key_source = f_ks.name

    try:
        temp_path = tmp_path + "_transposed.mid"
        semitones_offset, key_str = analyze_and_transpose_music21(tmp_path, temp_path, key_source=tmp_key_source)


        score = symusic.Score(temp_path)
        ts = score.time_signatures[0] if score.time_signatures else None
        numerator = ts.numerator if ts else 4
        denominator = ts.denominator if ts else 4
        tpq = score.ticks_per_quarter
        ticks_per_bar = int(4 * tpq * numerator / denominator)
        steps_per_bar = numerator if numerator in [3, 4] else 4

        melody_notes = score.tracks[0].notes
        total_ticks = melody_notes[-1].end if melody_notes else 0
        total_bars = int(math.ceil(total_ticks / ticks_per_bar)) + 1

        # ==========================
        # STAGE 1: MACRO
        # ==========================
        _p(0.10, "Stage 1/3: Macro chord prediction...")
        logger.info("[1/3] STAGE 1: MACRO")
        macro_pad_id = macro_tokenizer.vocab.get("PAD_None", 0)
        len_token_id = macro_tokenizer.vocab.get(f"Len_{total_bars}", macro_pad_id)
        macro_src_seq = [macro_tokenizer.vocab.get("BOS_None", 0), len_token_id]
        
        for i in range(total_bars):
            start_tick = i * ticks_per_bar
            end_tick = start_tick + ticks_per_bar
            bar_mel_notes = [n for n in melody_notes if start_tick <= n.time < end_tick]
            macro_src_seq.append(macro_tokenizer.vocab.get("Bar_None", 0))
            ticks_per_step = (end_tick - start_tick) / steps_per_bar
            for s in range(steps_per_bar):
                sample_tick = int(start_tick + s * ticks_per_step)
                active_pitches = [n.pitch for n in bar_mel_notes if n.time <= sample_tick < (n.time + n.duration)]
                nearby_attack_notes = [n for n in bar_mel_notes if abs(n.time - sample_tick) <= 15]
                if nearby_attack_notes:
                    strict_notes = [n for n in nearby_attack_notes if abs(n.time - sample_tick) <= 5]
                    chosen_pitch = max(n.pitch for n in strict_notes) if strict_notes else max(n.pitch for n in nearby_attack_notes)
                elif active_pitches:
                    chosen_pitch = max(active_pitches)
                else:
                    chosen_pitch = None
                    
                token_id = macro_tokenizer.vocab.get(f"Pitch_{chosen_pitch}", macro_pad_id) if chosen_pitch is not None else macro_pad_id
                macro_src_seq.append(token_id)
                
        macro_src_seq.append(macro_tokenizer.vocab.get("EOS_None", 0))

        macro_tgt_in = [macro_chord_to_id.get("BOS", 0)]
        expected_macro_len = total_bars * steps_per_bar * 2

        with torch.no_grad():
            with torch.autocast(device_type=DEVICE if DEVICE == "cuda" else "cpu", dtype=torch.bfloat16 if DEVICE == "cuda" else torch.float32):
                macro_src_tensor = torch.tensor([macro_src_seq], dtype=torch.long).to(DEVICE)
                for _ in range(expected_macro_len * 2):
                    tgt_tensor = torch.tensor([macro_tgt_in], dtype=torch.long).to(DEVICE)
                    logits = macro_model(macro_src_tensor, tgt_tensor)
                    step_logits = logits[0, -1, :]
                    invalid = ["PAD", "BOS", "N"]
                    if len(macro_tgt_in) - 1 < expected_macro_len: invalid.append("EOS")
                    for it in invalid:
                        if it in macro_chord_to_id: step_logits[macro_chord_to_id[it]] = -float('inf')
                    next_id = torch.argmax(step_logits).item()
                    macro_tgt_in.append(next_id)
                    if next_id == macro_chord_to_id.get("EOS", 0) or len(macro_tgt_in)-1 >= expected_macro_len: break

        macro_prefix_str = [macro_id_to_chord.get(i, "N") for i in macro_tgt_in[1:] if i != macro_chord_to_id.get("EOS", 0)]

        # ==========================
        # STAGE 2: LOCAL CHORDS
        # ==========================
        _p(0.40, "Stage 2/3: Local chord refinement...")
        logger.info("[2/3] STAGE 2: LOCAL")
        window_size_ticks = WINDOW_BARS * ticks_per_bar
        step_size_ticks = STRIDE_BARS * ticks_per_bar
        total_windows = int(math.ceil((total_ticks - window_size_ticks) / step_size_ticks)) + 1 if total_ticks > window_size_ticks else 1

        pred_chords_full = []
        pred_chords_with_pos_full = [] 
        
        for w in range(total_windows):
            win_start = w * step_size_ticks
            win_end = win_start + window_size_ticks
            bar_idx = w * STRIDE_BARS
            
            prefix_start = bar_idx * steps_per_bar * 2
            prefix_end = (bar_idx + WINDOW_BARS) * steps_per_bar * 2
            win_macro_str = macro_prefix_str[prefix_start:prefix_end]
            prefix_ids = [vocab.get(f"{t}_None", vocab.get(t, 0)) for t in win_macro_str]
            
            mel_notes = [symusic.Note(n.time - win_start, n.duration, n.pitch, n.velocity) for n in score.tracks[0].notes if win_start <= n.time < win_end]
            win_score = symusic.Score(tpq)
            win_score.time_signatures.append(symusic.TimeSignature(0, numerator, denominator))
            win_track = symusic.Track()
            win_track.notes = mel_notes
            win_score.tracks.append(win_track)

            mel_encoded = local_tokenizer(win_score)
            src_mel_ids = list(mel_encoded[0].ids if isinstance(mel_encoded, list) else getattr(mel_encoded, "ids", mel_encoded))

            src_ids = [local_BOS] + prefix_ids + [local_SEP] + src_mel_ids + [local_EOS]
            src_tensor = torch.tensor([src_ids], dtype=torch.long).to(DEVICE)

            expected_pairs = WINDOW_BARS * steps_per_bar
            half_window_pairs = (STRIDE_BARS * steps_per_bar)

            if w == 0:
                tgt_in = [local_chord_to_id["BOS"]]
                start_gen_pair = 0
            else:
                context_chords = pred_chords_full[-half_window_pairs:]
                tgt_in = [local_chord_to_id["BOS"]]
                for i, c in enumerate(context_chords):
                    pos_num = (i % steps_per_bar) + 1
                    tgt_in.append(local_chord_to_id.get(f"Pos_{pos_num}", 0))
                    tgt_in.append(local_chord_to_id.get(c, 0))
                start_gen_pair = len(context_chords)

            with torch.no_grad():
                with torch.autocast(device_type="cuda" if DEVICE == "cuda" else "cpu", dtype=torch.bfloat16 if DEVICE == "cuda" else torch.float32):
                    for pair_idx in range(start_gen_pair, expected_pairs):
                        pos_num = (pair_idx % steps_per_bar) + 1
                        tgt_in.append(local_chord_to_id.get(f"Pos_{pos_num}", 0))
                        tgt_tensor = torch.tensor([tgt_in], dtype=torch.long).to(DEVICE)
                        logits = local_model(src_tensor, tgt_tensor)
                        step_logits = logits[0, -1, :]

                        if len(tgt_in) > 3:
                            last_chord = tgt_in[-2]
                            if len(tgt_in) >= 5 and tgt_in[-4] == last_chord: step_logits[last_chord] -= 1.5
                            if len(tgt_in) >= 9 and tgt_in[-8] == last_chord: step_logits[last_chord] -= 5.0

                        invalid_ids = [local_chord_to_id.get(t, 0) for t in ["BOS", "EOS", "PAD", "MASK", "N"]] + [v for k,v in local_chord_to_id.items() if k.startswith("Pos_")]
                        next_token = sample_token(step_logits, temperature=0.8, top_k=3, invalid_ids=invalid_ids)
                        tgt_in.append(next_token)

            pred_chord_ids = [t for t in tgt_in if t not in (local_chord_to_id["BOS"], local_chord_to_id["EOS"]) and not local_id_to_chord.get(t,"").startswith("Pos_")]
            pred_chord_ids = pred_chord_ids[:expected_pairs]
            pred_chords = [local_id_to_chord.get(t, "N") for t in pred_chord_ids]
            
            chords_with_pos = []
            for i, c in enumerate(pred_chords):
                chords_with_pos.append(f"Pos_{(i % steps_per_bar) + 1}")
                chords_with_pos.append(c)

            if w > 0:
                pred_chords_full.extend(pred_chords[start_gen_pair:])
                pred_chords_with_pos_full.extend(chords_with_pos[start_gen_pair*2:])
            else:
                pred_chords_full.extend(pred_chords)
                pred_chords_with_pos_full.extend(chords_with_pos)

        # ==========================
        # STAGE 3: ACCOMPANIMENT
        # ==========================
        _p(0.70, "Stage 3/3: Accompaniment generation...")
        logger.info("[3/3] STAGE 3: ACCOMPANIMENT")
        all_notes = getattr(score.tracks[0], "notes", [])
        acc_notes_all = []
        prefix_token_ids = []

        for w_idx, bar_start in enumerate(range(0, total_bars - WINDOW_BARS + 1, STRIDE_BARS)):
            bar_end = min(bar_start + WINDOW_BARS, total_bars)
            tick_start = bar_start * ticks_per_bar
            tick_end = bar_end * ticks_per_bar

            mel_notes = extract_window_notes(all_notes, tick_start, tick_end, 0)
            src_body_ids = notes_to_tokens(mel_notes, tpq, numerator, denominator, local_tokenizer)
            src_ids = [local_BOS] + src_body_ids + [local_EOS]

            start_idx = bar_start * steps_per_bar * 2
            end_idx = bar_end * steps_per_bar * 2
            win_chords_str = pred_chords_with_pos_full[start_idx:end_idx]
            chords_ids = [local_chord_to_id.get(c, 0) for c in win_chords_str]

            full_tgt_token_ids = generate_window_accom(
                model=accom_model,
                tokenizer=local_tokenizer,
                src_ids=src_ids,
                chords_ids=chords_ids,
                prefix_ids=prefix_token_ids,
                bar_id=vocab.get("Bar_None", vocab.get("Bar", 0)),
                density=complexity,
                temperature=creativity,
                window_idx=w_idx + 1,
                is_first=(w_idx == 0),
                target_bars=WINDOW_BARS
            )

            full_notes = tokens_to_notes(full_tgt_token_ids, local_tokenizer, tpq)
            
            prefix_start_local = (WINDOW_BARS - PREFIX_BARS) * ticks_per_bar
            prefix_end_local = WINDOW_BARS * ticks_per_bar
            
            prefix_notes = []
            for n in full_notes:
                if prefix_start_local <= n.time < prefix_end_local:
                    new_n = copy.copy(n)
                    new_n.time = n.time - prefix_start_local
                    prefix_notes.append(new_n)
                    
            if prefix_notes:
                prefix_token_ids = notes_to_tokens(prefix_notes, tpq, numerator, denominator, local_tokenizer)
            else:
                prefix_token_ids = []

            if w_idx == 0:
                new_notes = list(full_notes)
            else:
                prefix_tick_local = PREFIX_BARS * ticks_per_bar
                new_notes = [n for n in full_notes if n.time >= prefix_tick_local]

            for n in new_notes:
                n.time += tick_start
            acc_notes_all.extend(new_notes)

        # ==========================
        # 4. 渲染組合
        # ==========================
        _p(0.95, "Rendering final MIDI...")
        logger.info("渲染組合音樂回原曲調性中...")
        orig_score = symusic.Score(tmp_path)
        final_score = symusic.Score(orig_score.ticks_per_quarter)
        final_score.time_signatures = orig_score.time_signatures
        final_score.tempos = orig_score.tempos

        mel_track = symusic.Track()
        mel_track.program = 73
        mel_track.notes = getattr(orig_score.tracks[0], "notes", []) if orig_score.tracks else []
        final_score.tracks.append(mel_track)

        acc_track = symusic.Track()
        acc_track.program = 0
        ratio_tpq = orig_score.ticks_per_quarter / tpq
        for n in acc_notes_all:
            n.pitch = max(0, min(127, n.pitch - semitones_offset))
            if ratio_tpq != 1.0:
                n.time = int(n.time * ratio_tpq)
                n.duration = max(1, int(n.duration * ratio_tpq))
                
        acc_track.notes = acc_notes_all
        final_score.tracks.append(acc_track)

        # 整理和弦標籤回傳給前端 (每小節一個 list)
        sorted_chord_list = []
        for i in range(total_bars):
            start = i * steps_per_bar
            end = start + steps_per_bar
            bar_chords = [_normalize_chord_name(c.split("_")[0]) for c in pred_chords_full[start:end]]
            sorted_chord_list.append(bar_chords)


        with tempfile.NamedTemporaryFile(suffix=".mid", prefix="threestage_tmp_", delete=False) as f_out:
            out_path = f_out.name
        try:
            final_score.dump_midi(out_path)
            with open(out_path, "rb") as f:
                midi_b = f.read()

            # ── 和弦名稱轉調回原調 ─────────────────────────────────────────────
            # threeStage 的 semitones_offset 是「原調→C/Am」的半音數，還原需取負
            sorted_chord_list = midi_service.transpose_chord_list(sorted_chord_list, -semitones_offset)

            try:
                midi_b = midi_service.add_chords_to_midi(midi_b, sorted_chord_list, key_signature=key_str)
            except Exception as e:
                logger.warning(f"無法將和弦標記寫入 MIDI: {e}")


            return midi_b, sorted_chord_list

        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if os.path.exists(tmp_path + "_transposed.mid"):
            os.remove(tmp_path + "_transposed.mid")
        if tmp_key_source and os.path.exists(tmp_key_source):
            os.remove(tmp_key_source)


# ============================================================
# 公開的非同步 Service 函式
# ============================================================

async def generate(
    melody_midi_bytes: bytes,
    complexity: float = 0.5,
    creativity: float = 1.0,
    original_midi_bytes: bytes | None = None,
    update_progress=None,
) -> tuple[bytes, list[list[str]]]:
    """Three-Stage Coarse-to-Fine 生成器。"""
    return await asyncio.to_thread(
        _run_inference, melody_midi_bytes, complexity, creativity, original_midi_bytes, update_progress
    )

