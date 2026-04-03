"""
twoStage_service.py
-------------------
使用兩階段模型為旋律 MIDI 生成鋼琴伴奏。

推理流程：
  Stage 1 (Chord Prediction): 由 AI 預測和弦序列，支援三種模型架構：
    - std  (Standard AR)  → pop909_chord_predictor
    - bar  (Bar-level AR) → pop909_chord_predictor_bar
    - nar  (NAR)          → pop909_chord_predictor_nar
  Stage 2 (Accompaniment Generation): 根據旋律 + 和弦生成伴奏。
    → pop909_two_stage_chord

推理邏輯改編自：
  model/pop909_two_stage_chord/generate.py

公開函式：
  generate_std(melody_midi_bytes) → bytes
  generate_bar(melody_midi_bytes) → bytes
  generate_nar(melody_midi_bytes) → bytes
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
import tempfile
from typing import Literal

import torch
import symusic
import logging
from miditok import REMI, TokSequence
from music21 import converter as m21converter

logger = logging.getLogger(__name__)

# ── 讓 service 能 import 同目錄的 twoStage_transformer.py ─────────────────────
_SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
if _SERVICE_DIR not in sys.path:
    sys.path.insert(0, _SERVICE_DIR)

from twoStage_transformer import POP909Transformer  # Stage 2  # noqa: E402
from twoStage_chord_transformer import POP909ChordPredictor  # Stage 1  # noqa: E402

# ── 資源根目錄 ────────────────────────────────────────────────────────────────
_RESOURCES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources",
)

# Stage 2（共用）
_STAGE2_DIR = os.path.join(_RESOURCES, "pop909_two_stage_chord")
_STAGE2_CHECKPOINT = os.path.join(_STAGE2_DIR, "two_stage_chord_epoch_100.pth")
_STAGE2_TOKENIZER = os.path.join(_STAGE2_DIR, "tokenizer.json")
_STAGE2_CHORD_VOCAB = os.path.join(_STAGE2_DIR, "chord_vocab.json")

# Stage 1（各模式對應不同目錄）
_STAGE1_DIRS: dict[str, str] = {
    "std": os.path.join(_RESOURCES, "pop909_chord_predictor"),
    "bar": os.path.join(_RESOURCES, "pop909_chord_predictor_bar"),
    "nar": os.path.join(_RESOURCES, "pop909_chord_predictor_nar"),
}

# ── 裝置 ──────────────────────────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ── 視窗參數 ──────────────────────────────────────────────────────────────────
WINDOW_BARS = 4
STRIDE_BARS = 2
PREFIX_BARS = 2
NEW_BARS = 2
MAX_GEN_LEN = 2048
MODEL_MAX_LEN = 2048
CREATIVITY = 1.0

# ── 複雜度控制表 ────────────────────────────────────────────────────────────────
COMPLEXITY_CONFIG = {
    0.00: (5, 0.70),
    0.25: (10, 0.80),
    0.50: (20, 0.90),
    0.75: (50, 0.95),
    1.00: (100, 0.99),
}

# ── 調性偏移表 ────────────────────────────────────────────────────────────────
KEY_MAP_MAJOR = {
    "C": 0,
    "C#": -1,
    "D-": -1,
    "D": -2,
    "E-": -3,
    "E": -4,
    "F": -5,
    "G-": 6,
    "F#": 6,
    "G": 5,
    "A-": 4,
    "A": 3,
    "B-": 2,
    "B": 1,
}
KEY_MAP_MINOR = {
    "C": -3,
    "C#": -4,
    "D-": -4,
    "D": -5,
    "D#": 6,
    "E-": 6,
    "E": 5,
    "F": 4,
    "F#": 3,
    "G-": 3,
    "G": 2,
    "G#": 1,
    "A-": 1,
    "A": 0,
    "A#": -1,
    "B-": -1,
    "B": -2,
}

# ── Lazy-loaded 快取（每種 predictor_type 各一份 Stage 1）────────────────────
_stage2_model: POP909Transformer | None = None
_stage2_tokenizer: REMI | None = None
_stage2_chord_to_id: dict | None = None

_stage1_cache: dict[str, tuple] = {}  # predictor_type → (model, chord_to_id)


# ============================================================
# 工具函式
# ============================================================


def _get_sampling_params(complexity: float) -> tuple[int, float]:
    complexity = max(0.0, min(1.0, complexity))
    keys = sorted(COMPLEXITY_CONFIG.keys())
    for i in range(len(keys) - 1):
        lo, hi = keys[i], keys[i + 1]
        if lo <= complexity <= hi:
            t = (complexity - lo) / (hi - lo)
            k_lo, p_lo = COMPLEXITY_CONFIG[lo]
            k_hi, p_hi = COMPLEXITY_CONFIG[hi]
            return int(round(k_lo + t * (k_hi - k_lo))), p_lo + t * (p_hi - p_lo)
    return COMPLEXITY_CONFIG[keys[-1]]


def _top_k_top_p_filtering(
    logits: torch.Tensor, top_k: int, top_p: float
) -> torch.Tensor:
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


def _detect_key_offset(midi_path: str) -> tuple[int, int]:
    """用 music21 分析調性，回傳 (to_c_offset, back_offset)。"""
    m21score = m21converter.parse(midi_path)
    detected = m21score.analyze("key")
    tonic_name = detected.tonic.name
    mode = detected.mode
    logger.info("調性分析結果：%s %s", tonic_name, mode)

    key_map = KEY_MAP_MINOR if mode == "minor" else KEY_MAP_MAJOR
    offset = key_map.get(tonic_name, 0)
    logger.info("轉調偏移：至 C=%+d, 還原=%+d", offset, -offset)
    return offset, -offset


def _load_midi(path: str) -> symusic.Score:
    try:
        return symusic.Score(path)
    except Exception:
        return symusic.Score.from_midi(path)


def _get_time_signature(score: symusic.Score) -> tuple[int, int]:
    if score.time_signatures:
        ts = score.time_signatures[0]
        return ts.numerator, ts.denominator
    return 4, 4


def _extract_window_notes(notes, start_tick, end_tick, pitch_offset):
    result = []
    for n in notes:
        if start_tick <= n.time < end_tick:
            new_n = copy.copy(n)
            new_n.pitch = max(0, min(127, n.pitch + pitch_offset))
            new_n.time = n.time - start_tick
            new_n.duration = min(n.duration, end_tick - n.time)
            result.append(new_n)
    return result


def _notes_to_tokens(notes, tpq, numerator, denominator, tokenizer):
    score = symusic.Score(tpq)
    score.time_signatures.append(symusic.TimeSignature(0, numerator, denominator))
    track = symusic.Track()
    track.notes = notes
    score.tracks.append(track)
    encoded = tokenizer(score)
    return list(
        encoded[0].ids
        if isinstance(encoded, list)
        else getattr(encoded, "ids", encoded)
    )


def _tokens_to_notes(token_ids, tokenizer, tpq):
    id_to_token = {v: k for k, v in tokenizer.vocab.items()}
    tokens_str = [id_to_token.get(t, "UNK") for t in token_ids]
    seq = TokSequence(ids=token_ids, tokens=tokens_str)
    acc_score = tokenizer.decode([seq])
    acc_tpq = acc_score.ticks_per_quarter
    if not acc_score.tracks or not acc_score.tracks[0].notes:
        return []
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


def _get_stage2() -> tuple[POP909Transformer, REMI, dict]:
    global _stage2_model, _stage2_tokenizer, _stage2_chord_to_id
    if _stage2_model is None:
        logger.info("正在載入 Stage 2 Tokenizer：%s", _STAGE2_TOKENIZER)
        tokenizer = REMI(params=_STAGE2_TOKENIZER)
        with open(_STAGE2_CHORD_VOCAB, "r", encoding="utf-8") as f:
            chord_to_id = json.load(f)

        vocab_size = len(tokenizer.vocab)

        logger.info("正在載入 Stage 2 模型檢查點：%s", _STAGE2_CHECKPOINT)
        # ── 從 checkpoint 的 embedding 直接讀出 chord_vocab_size，避免 shape mismatch ──
        ckpt = torch.load(_STAGE2_CHECKPOINT, map_location="cpu", weights_only=False)
        state = {
            k.replace("_orig_mod.", ""): v for k, v in ckpt["model_state_dict"].items()
        }
        chord_vocab_size = state["chord_embedding.weight"].shape[0]

        m = POP909Transformer(
            vocab_size=vocab_size, chord_vocab_size=chord_vocab_size
        ).to(DEVICE)
        m.load_state_dict(state)
        m.eval()

        epoch = ckpt.get("epoch", "?")
        logger.info("Stage 2 模型載入完成。Epoch=%s, 裝置=%s", epoch, DEVICE)

        _stage2_model = m
        _stage2_tokenizer = tokenizer
        _stage2_chord_to_id = chord_to_id

    if "Bar_None" not in _stage2_tokenizer.vocab:
        raise ValueError("❌ Stage 2 Tokenizer 詞彙表中找不到 'Bar_None'。")

    return _stage2_model, _stage2_tokenizer, _stage2_chord_to_id


def _get_stage1(predictor_type: str) -> tuple[POP909ChordPredictor, dict, int, int]:
    """回傳 (chord_model, chord_to_id, bos_id, eos_id) for the given predictor_type."""
    global _stage1_cache
    if predictor_type not in _stage1_cache:
        stage1_dir = _STAGE1_DIRS[predictor_type]
        ckpt_path = os.path.join(stage1_dir, "chord_predictor_epoch_30.pth")
        vocab_path = os.path.join(stage1_dir, "chord_vocab.json")

        _, stage2_tokenizer, _ = _get_stage2()
        src_vocab_size = len(stage2_tokenizer.vocab)

        with open(vocab_path, "r", encoding="utf-8") as f:
            chord_to_id = json.load(f)

        bos_id = chord_to_id.get("BOS", 0)
        eos_id = chord_to_id.get("EOS", 0)

        # ── 從 checkpoint 的 embedding 直接讀出 tgt_vocab_size，避免 shape mismatch ──
        logger.info("正在載入 Stage 1 (%s) 模型檢查點：%s", predictor_type, ckpt_path)
        ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
        state = {
            k.replace("_orig_mod.", ""): v for k, v in ckpt["model_state_dict"].items()
        }

        # tgt_embedding.weight shape: (tgt_vocab_size, d_model)
        tgt_vocab_size = state["tgt_embedding.weight"].shape[0]

        cm = POP909ChordPredictor(src_vocab_size, tgt_vocab_size).to(DEVICE)
        cm.load_state_dict(state)
        cm.eval()

        logger.info("Stage 1 (%s) 載入完成。裝置=%s", predictor_type, DEVICE)

        _stage1_cache[predictor_type] = (cm, chord_to_id, bos_id, eos_id)

    return _stage1_cache[predictor_type]


# ============================================================
# Stage 1：和弦預測邏輯
# ============================================================


@torch.no_grad()
def _predict_window_chords(
    chord_model: POP909ChordPredictor,
    src_ids: list,
    bos_id: int,
    eos_id: int,
    target_len: int,
    steps_per_bar: int,
    chord_to_id: dict,
    id_to_chord: dict,
    predictor_type: str,
) -> list:
    """通用 Stage 1 和弦預測 Router，相容 std / bar / nar 三種架構。"""
    src_tensor = torch.tensor([src_ids], dtype=torch.long).to(DEVICE)
    temp_stage1 = 0.9
    top_k_stage1 = 3

    if predictor_type == "nar":
        mask_id = chord_to_id.get("MASK", 0)
        tgt_in = [mask_id] * target_len
        tgt_tensor = torch.tensor([tgt_in], dtype=torch.long).to(DEVICE)

        with torch.autocast(
            device_type=DEVICE if DEVICE == "cuda" else "cpu",
            dtype=torch.bfloat16 if DEVICE == "cuda" else torch.float32,
        ):
            # NAR 模型forward時需標記
            logits = chord_model(src_tensor, tgt_tensor, is_nar=True)

        pred_chord_ids = []
        force_steps_remaining = 0
        forced_token = None

        for step in range(target_len):
            step_logits = logits[0, step, :].clone() / temp_stage1

            # --- 鎖定規則 (Smoothing) ---
            if force_steps_remaining > 0:
                candidate_id = forced_token
                is_allowed = True

                # 檢查前一小節 (Smoothing Logic)
                current_bar_start = (step // steps_per_bar) * steps_per_bar
                prev_bar_start = current_bar_start - steps_per_bar
                if prev_bar_start >= 0:
                    current_seq_so_far = pred_chord_ids
                    prev_bar_chords = current_seq_so_far[
                        prev_bar_start:current_bar_start
                    ]
                    if prev_bar_chords.count(candidate_id) >= 2:
                        probs = torch.softmax(step_logits, dim=-1)
                        top_v, top_idx = torch.topk(probs, 2)
                        if not (
                            top_idx[0].item() == candidate_id
                            and (top_v[0].item() - top_v[1].item()) > 0.03
                        ):
                            is_allowed = False

                if not is_allowed:
                    force_steps_remaining = 0
                else:
                    next_token = forced_token
                    force_steps_remaining -= 1
                    pred_chord_ids.append(next_token)
                    continue

            # --- 正常採樣 (含有向前預看鎖定規則) ---
            is_forward_matched = False
            if step + 1 < target_len:
                next_logits = logits[0, step + 1, :] / temp_stage1
                probs_curr = torch.softmax(step_logits, dim=-1)
                probs_next = torch.softmax(next_logits, dim=-1)

                top_v_curr, top_idx_curr = torch.topk(probs_curr, 2)
                top_v_next, top_idx_next = torch.topk(probs_next, 1)

                curr_top1_id = top_idx_curr[0].item()
                curr_top1_prob = top_v_curr[0].item()
                curr_top2_prob = top_v_curr[1].item()
                next_top1_id = top_idx_next[0].item()
                next_top1_prob = top_v_next[0].item()

                invalid_ids_list = [
                    chord_to_id.get(t, 0) for t in ["BOS", "EOS", "PAD", "MASK", "N"]
                ]

                # 計算連續次數
                consecutive_count = 0
                for x in reversed(pred_chord_ids):
                    if x == curr_top1_id:
                        consecutive_count += 1
                    else:
                        break

                # 檢查前一小節限制
                is_allowed = True
                current_bar_start = (step // steps_per_bar) * steps_per_bar
                prev_bar_start = current_bar_start - steps_per_bar
                if prev_bar_start >= 0:
                    prev_bar_chords = pred_chord_ids[prev_bar_start:current_bar_start]
                    if prev_bar_chords.count(curr_top1_id) >= 2:
                        if (curr_top1_prob - curr_top2_prob) <= 0.03:
                            is_allowed = False

                if (
                    curr_top1_id == next_top1_id
                    and next_top1_prob >= curr_top1_prob
                    and curr_top1_id not in invalid_ids_list
                    and consecutive_count < 4
                    and is_allowed
                ):
                    is_forward_matched = True
                    forced_token = curr_top1_id
                    force_steps_remaining = 1
                    next_token = curr_top1_id

            if not is_forward_matched:
                # 重複懲罰
                if pred_chord_ids:
                    last_chord = pred_chord_ids[-1]
                    cnt = 0
                    for x in reversed(pred_chord_ids):
                        if x == last_chord:
                            cnt += 1
                        else:
                            break
                    if cnt >= 4:
                        step_logits[last_chord] -= 1.5
                    if cnt >= 8:
                        step_logits[last_chord] -= 5.0

                invalid_ids_list = [
                    chord_to_id.get(t, 0) for t in ["BOS", "EOS", "PAD", "MASK", "N"]
                ]
                for idx in invalid_ids_list:
                    step_logits[idx] = -float("Inf")

                if top_k_stage1 > 0:
                    top_v, top_idx = torch.topk(step_logits, top_k_stage1)
                    probs = torch.softmax(top_v, dim=-1)
                    sampled_i = torch.multinomial(probs, 1).item()
                    next_token = top_idx[sampled_i].item()
                else:
                    next_token = step_logits.argmax().item()

            pred_chord_ids.append(next_token)
        return pred_chord_ids

    # ── AR / Bar-AR ──────────────────────────────────────────────────────────
    tgt_ids = [bos_id]
    for pair_idx in range(target_len):
        if predictor_type == "bar":
            pos_num = (pair_idx % steps_per_bar) + 1
            pos_token = chord_to_id.get(f"Pos_{pos_num}", 0)
            tgt_ids.append(pos_token)

        tgt_tensor = torch.tensor([tgt_ids], dtype=torch.long).to(DEVICE)
        with torch.autocast(
            device_type=DEVICE if DEVICE == "cuda" else "cpu",
            dtype=torch.bfloat16 if DEVICE == "cuda" else torch.float32,
        ):
            logits = chord_model(src_tensor, tgt_tensor)

        step_logits = logits[0, -1, :].clone() / temp_stage1

        invalid_ids = [
            chord_to_id.get(t, 0) for t in ["BOS", "EOS", "PAD", "MASK", "N"]
        ]
        for t in chord_to_id:
            if t.startswith("Pos_"):
                invalid_ids.append(chord_to_id[t])

        check_offset = 2 if predictor_type == "bar" else 1
        if len(tgt_ids) > (check_offset + 1):
            last_chord = tgt_ids[-check_offset]
            cnt = 0
            for i in range(len(tgt_ids) - (check_offset * 2), 0, -check_offset):
                if tgt_ids[i] == last_chord:
                    cnt += 1
                else:
                    break
            if cnt >= 4:
                step_logits[last_chord] -= 1.5
            if cnt >= 8:
                step_logits[last_chord] -= 5.0

        for idx in invalid_ids:
            step_logits[idx] = -float("Inf")

        top_v, top_idx = torch.topk(step_logits, 4)
        probs = torch.softmax(top_v, dim=-1)
        sampled_i = torch.multinomial(probs, 1).item()
        next_id = top_idx[sampled_i].item()
        tgt_ids.append(next_id)

    clean_ids = []
    for i in range(1, len(tgt_ids)):
        token_str = id_to_chord.get(tgt_ids[i], "")
        if tgt_ids[i] not in (bos_id, eos_id) and not token_str.startswith("Pos_"):
            clean_ids.append(tgt_ids[i])
    return clean_ids[:target_len]


# ============================================================
# Stage 2：自迴歸伴奏生成
# ============================================================


@torch.no_grad()
def _generate_window(
    model: POP909Transformer,
    tokenizer: REMI,
    src_ids: list,
    chords_ids: list,
    prefix_ids: list,
    bar_id: int,
    complexity: float,
    creativity: float,
) -> list:
    vocab = tokenizer.vocab
    BOS_ID = vocab.get("BOS_None", vocab.get("BOS", 0))
    EOS_ID = vocab.get("EOS_None", vocab.get("EOS", 0))
    top_k, top_p = _get_sampling_params(complexity)

    early_stop_bars = WINDOW_BARS * 1.0
    force_eos_bars = WINDOW_BARS * 1.10

    src_tensor = torch.tensor([src_ids], dtype=torch.long).to(DEVICE)
    chords_tensor = torch.tensor([chords_ids], dtype=torch.long).to(DEVICE)

    tgt_ids = [BOS_ID] + list(prefix_ids)

    for _ in range(len(prefix_ids), MAX_GEN_LEN):
        tgt_window = tgt_ids[-MODEL_MAX_LEN:]
        tgt_tensor = torch.tensor([tgt_window], dtype=torch.long).to(DEVICE)

        logits = model(src_tensor, tgt_tensor, chords=chords_tensor)
        next_logits = logits[0, -1, :] / creativity

        current_bar_count = tgt_ids.count(bar_id)
        if current_bar_count < early_stop_bars:
            next_logits[EOS_ID] = float("-inf")
        elif current_bar_count >= force_eos_bars:
            next_logits[EOS_ID] += 20.0

        filtered = _top_k_top_p_filtering(next_logits, top_k, top_p)
        probs = torch.softmax(filtered, dim=-1)
        next_id = torch.multinomial(probs, num_samples=1).item()
        tgt_ids.append(next_id)
        if next_id == EOS_ID:
            break

    return [t for t in tgt_ids if t not in (BOS_ID, EOS_ID)]


# ============================================================
# 核心推理（同步）
# ============================================================


def _run_inference(
    melody_midi_bytes: bytes,
    predictor_type: Literal["std", "bar", "nar"],
    complexity: float = 0.5,
    creativity: float = 1.0,
) -> tuple[bytes, list[str]]:
    # ── 載入模型 ──────────────────────────────────────────────────────────────
    stage2_model, tokenizer, stage2_chord_to_id = _get_stage2()
    chord_model, stage1_chord_to_id, chord_bos_id, chord_eos_id = _get_stage1(
        predictor_type
    )

    stage1_id_to_chord = {v: k for k, v in stage1_chord_to_id.items()}

    vocab = tokenizer.vocab
    BOS_ID = vocab.get("BOS_None", vocab.get("BOS", 0))
    EOS_ID = vocab.get("EOS_None", vocab.get("EOS", 0))
    BAR_ID = vocab["Bar_None"]

    # ── 暫存 MIDI ──────────────────────────────────────────────────────────────
    with tempfile.NamedTemporaryFile(
        suffix=".mid", prefix="accom_tmp_", delete=False
    ) as f_in:
        f_in.write(melody_midi_bytes)
        tmp_path = f_in.name
    logger.debug("旋律 MIDI 暫存於：%s", tmp_path)

    try:
        orig_score = _load_midi(tmp_path)
        if not orig_score.tracks or not orig_score.tracks[0].notes:
            raise ValueError("MIDI 沒有任何音符")

        tpq = orig_score.ticks_per_quarter
        numerator, denominator = _get_time_signature(orig_score)
        ticks_per_bar = int(4 * tpq * numerator / denominator)
        all_notes = sorted(orig_score.tracks[0].notes, key=lambda n: n.time)
        last_tick = max(n.time + n.duration for n in all_notes)
        total_bars = max(1, last_tick // ticks_per_bar)

        logger.info(
            "MIDI 解析完成。TPQ=%d, 拍號=%d/%d, 總長度=%d 小節, 音符數=%d",
            tpq,
            numerator,
            denominator,
            total_bars,
            len(all_notes),
        )

        # ── 調性分析 ────────────────────────────────────────────────────────────
        to_c_offset, back_offset = _detect_key_offset(tmp_path)

        # ── 滑動視窗 ────────────────────────────────────────────────────────────
        window_starts = list(range(0, total_bars - WINDOW_BARS + 1, STRIDE_BARS))
        if not window_starts or window_starts[-1] + WINDOW_BARS < total_bars:
            window_starts.append(max(0, total_bars - WINDOW_BARS))
        window_starts = sorted(set(window_starts))
        logger.debug("視窗起始小節：%s", window_starts)

        acc_notes_all: list = []
        prefix_token_ids: list = []
        final_chords_dict: dict[int, list[str]] = {}

        for w_idx, bar_start in enumerate(window_starts):
            logger.info(
                "處理視窗 %d/%d (起始小節: %d)",
                w_idx + 1,
                len(window_starts),
                bar_start,
            )
            is_first = w_idx == 0
            bar_end = min(bar_start + WINDOW_BARS, total_bars)
            tick_start = bar_start * ticks_per_bar
            tick_end = bar_end * ticks_per_bar

            mel_notes = _extract_window_notes(
                all_notes, tick_start, tick_end, to_c_offset
            )
            if len(mel_notes) < 4:
                logger.debug("視窗內旋律音符過少 (%d)，跳過。", len(mel_notes))
                prefix_token_ids = []
                continue

            src_body_ids = _notes_to_tokens(
                mel_notes, tpq, numerator, denominator, tokenizer
            )
            src_ids = [BOS_ID] + src_body_ids + [EOS_ID]
            logger.debug("旋律 token 數：%d", len(src_ids))

            # ── Stage 1：預測和弦 ──────────────────────────────────────────────
            steps_per_bar = numerator
            target_len = WINDOW_BARS * steps_per_bar
            logger.debug("Stage 1 預測和弦，目標長度：%d", target_len)

            chords_ids_stage1 = _predict_window_chords(
                chord_model,
                src_ids,
                chord_bos_id,
                chord_eos_id,
                target_len,
                steps_per_bar,
                stage1_chord_to_id,
                stage1_id_to_chord,
                predictor_type,
            )
            logger.debug("Stage 1 預測和弦 ID 數：%d", len(chords_ids_stage1))

            # 轉回 Stage 2 vocab 索引
            chord_names = [
                stage1_id_to_chord.get(cid, "N") for cid in chords_ids_stage1
            ]
            chords_ids = [
                stage2_chord_to_id.get(name, stage2_chord_to_id.get("N", 0))
                for name in chord_names
            ]

            # 每個小節儲存所有拍的和弦（去除尾綴），供前端做 run-length 去重顯示
            bar_range = (
                range(WINDOW_BARS) if is_first else range(PREFIX_BARS, WINDOW_BARS)
            )
            for b in bar_range:
                bar_chords = []
                for beat in range(steps_per_bar):
                    idx = b * steps_per_bar + beat
                    if idx < len(chord_names):
                        bar_chords.append(chord_names[idx].split("_")[0])
                final_chords_dict[bar_start + b] = bar_chords

            logger.debug("Stage 2 和弦 ID 數：%d", len(chords_ids))

            # ── Stage 2：生成伴奏 ──────────────────────────────────────────────
            logger.debug("Stage 2 生成伴奏，前綴 token 數：%d", len(prefix_token_ids))
            full_tgt_token_ids = _generate_window(
                stage2_model,
                tokenizer,
                src_ids=src_ids,
                chords_ids=chords_ids,
                prefix_ids=prefix_token_ids,
                bar_id=BAR_ID,
                complexity=complexity,
                creativity=creativity,
            )
            logger.debug("Stage 2 生成伴奏 token 數：%d", len(full_tgt_token_ids))

            full_notes = _tokens_to_notes(full_tgt_token_ids, tokenizer, tpq)
            if not full_notes:
                logger.warning("Stage 2 未能生成任何伴奏音符，跳過此視窗。")
                prefix_token_ids = []
                continue
            logger.debug("Stage 2 生成伴奏音符數：%d", len(full_notes))

            # ── 更新前綴 ────────────────────────────────────────────────────────
            prefix_start_local = (WINDOW_BARS - PREFIX_BARS) * ticks_per_bar
            prefix_end_local = WINDOW_BARS * ticks_per_bar
            prefix_notes = []
            for n in full_notes:
                if prefix_start_local <= n.time < prefix_end_local:
                    new_n = copy.copy(n)
                    new_n.time = n.time - prefix_start_local
                    prefix_notes.append(new_n)

            if prefix_notes:
                prefix_token_ids = _notes_to_tokens(
                    prefix_notes, tpq, numerator, denominator, tokenizer
                )
                logger.debug("更新前綴 token 數：%d", len(prefix_token_ids))
            else:
                prefix_token_ids = []
                logger.debug("前綴音符為空，重置前綴。")

            # ── 決定本視窗新增音符 ──────────────────────────────────────────────
            if is_first:
                new_notes = list(full_notes)
                logger.debug("首個視窗，加入所有生成音符。")
            else:
                prefix_tick_local = PREFIX_BARS * ticks_per_bar
                new_notes = [n for n in full_notes if n.time >= prefix_tick_local]
                logger.debug("非首個視窗，加入 %d 個新音符。", len(new_notes))

            for n in new_notes:
                n.time += tick_start

            if back_offset != 0:
                for n in new_notes:
                    n.pitch = max(0, min(127, n.pitch + back_offset))
                logger.debug("應用還原調性偏移：%+d", back_offset)

            acc_notes_all.extend(new_notes)
            logger.debug("目前累積伴奏音符總數：%d", len(acc_notes_all))

        if not acc_notes_all:
            raise ValueError("模型未生成任何伴奏音符")

        # ── 組合雙軌 ────────────────────────────────────────────────────────────
        acc_notes_all.sort(key=lambda n: (n.time, n.pitch))
        mel_track = orig_score.tracks[0]
        mel_track.program = 73

        acc_track = symusic.Track()
        acc_track.program = 0
        acc_track.notes = acc_notes_all

        combined = symusic.Score(tpq)
        combined.time_signatures.append(
            symusic.TimeSignature(0, numerator, denominator)
        )
        combined.key_signatures.append(symusic.KeySignature(0, 0, 0))

        if getattr(orig_score, "tempos", None) and len(orig_score.tempos) > 0:
            for t in orig_score.tempos:
                combined.tempos.append(t)
        else:
            combined.tempos.append(symusic.Tempo(0, 120))

        combined.tracks.append(mel_track)
        combined.tracks.append(acc_track)

        acc_end = max(n.time + n.duration for n in acc_notes_all)
        mel_end = (
            max(n.time + n.duration for n in mel_track.notes) if mel_track.notes else 0
        )
        logger.info(
            "伴奏生成完成。總音符數=%d, 旋律結束 tick=%d, 伴奏結束 tick=%d",
            len(acc_notes_all),
            mel_end,
            acc_end,
        )

        with tempfile.NamedTemporaryFile(
            suffix=".mid", prefix="accom_tmp_", delete=False
        ) as f_out:
            out_path = f_out.name
        try:
            combined.dump_midi(out_path)
            with open(out_path, "rb") as f:
                midi_b = f.read()

            sorted_chord_list = [
                final_chords_dict.get(i, []) for i in range(total_bars)
            ]
            return midi_b, sorted_chord_list
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ============================================================
# 公開的非同步 Service 函式
# ============================================================


async def generate_std(
    melody_midi_bytes: bytes, complexity: float = 0.5, creativity: float = 1.0
) -> tuple[bytes, list[list[str]]]:
    """Standard AR 和弦預測器 (pop909_chord_predictor)。"""
    return await asyncio.to_thread(
        _run_inference, melody_midi_bytes, "std", complexity, creativity
    )


async def generate_bar(
    melody_midi_bytes: bytes, complexity: float = 0.5, creativity: float = 1.0
) -> tuple[bytes, list[list[str]]]:
    """Bar-level AR 和弦預測器 (pop909_chord_predictor_bar)。"""
    return await asyncio.to_thread(
        _run_inference, melody_midi_bytes, "bar", complexity, creativity
    )


async def generate_nar(
    melody_midi_bytes: bytes, complexity: float = 0.5, creativity: float = 1.0
) -> tuple[bytes, list[list[str]]]:
    """NAR 和弦預測器 (pop909_chord_predictor_nar)。"""
    return await asyncio.to_thread(
        _run_inference, melody_midi_bytes, "nar", complexity, creativity
    )
