"""
oneStage_service.py
-------------------
使用 pop909_norm_false_modify_preprocess 模型為旋律 MIDI 生成鋼琴伴奏。

推理邏輯改編自：
  model/pop909_norm_false_modify_preprocess/generate.py

核心策略：
  - 重疊滑動視窗（4 小節視窗，2 小節步進）
  - Bar_None token 精確 EOS 控制
  - 前一視窗後 2 小節作為下一視窗的 decoder 前綴
  - music21 Krumhansl-Schmuckler 調性分析 + 轉調至 C 大 / A 小

資源路徑：
  app/resources/pop909_norm_false_modify_preprocess/
    ├── norm_first_false_epoch_100.pth
    └── tokenizer.json
"""

from __future__ import annotations

import asyncio
import copy
import io
import os
import sys
import tempfile

import torch
import symusic
import logging
from miditok import REMI, TokSequence
from music21 import converter as m21converter

logger = logging.getLogger(__name__)

# ── 讓 service 能 import 同目錄的 transformer.py ─────────────────────────────
_SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
if _SERVICE_DIR not in sys.path:
    sys.path.insert(0, _SERVICE_DIR)

from oneStage_transformer import POP909Transformer  # noqa: E402

# ── 路徑常數 ──────────────────────────────────────────────────────────────────
_RESOURCE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources",
    "pop909_norm_false_modify_preprocess",
)
_CHECKPOINT_PATH = os.path.join(_RESOURCE_DIR, "norm_first_false_epoch_100.pth")
_TOKENIZER_PATH = os.path.join(_RESOURCE_DIR, "tokenizer.json")

# ── 裝置 ──────────────────────────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ── 視窗參數（與訓練一致）────────────────────────────────────────────────────
WINDOW_BARS = 4
STRIDE_BARS = 2
PREFIX_BARS = 2  # = WINDOW_BARS - STRIDE_BARS
NEW_BARS = 2  # = STRIDE_BARS

MAX_GEN_LEN = 2048
MODEL_MAX_LEN = 2048
CREATIVITY = 1.0

# ── 複雜度控制表 (top_k, top_p) ────────────────────────────────────────────────
# complexity 0.0=極簡 ~ 1.0=複雜
COMPLEXITY_CONFIG = {
    0.00: (5, 0.70),
    0.25: (10, 0.80),
    0.50: (20, 0.90),
    0.75: (50, 0.95),
    1.00: (100, 0.99),
}

# ── 調性偏移表（與 preprocess.py 完全一致）───────────────────────────────────
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

# ── Lazy-loaded 模型（避免冷啟動每次重複載入）────────────────────────────────
_model: POP909Transformer | None = None
_tokenizer: REMI | None = None


def _get_model_and_tokenizer() -> tuple[POP909Transformer, REMI]:
    global _model, _tokenizer
    if _model is None or _tokenizer is None:
        logger.info("正在載入 Tokenizer：%s", _TOKENIZER_PATH)
        _tokenizer = REMI(params=_TOKENIZER_PATH)
        vocab_size = len(_tokenizer.vocab)

        logger.info("正在載入模型檢查點：%s", _CHECKPOINT_PATH)
        m = POP909Transformer(vocab_size=vocab_size).to(DEVICE)
        ckpt = torch.load(_CHECKPOINT_PATH, map_location=DEVICE, weights_only=False)
        state = {
            k.replace("_orig_mod.", ""): v for k, v in ckpt["model_state_dict"].items()
        }
        m.load_state_dict(state)
        m.eval()

        epoch = ckpt.get("epoch", "?")
        val_loss = ckpt.get("val_loss", 0)
        logger.info(
            "模型載入完成。Epoch=%s, Val Loss=%.4f, 裝置=%s", epoch, val_loss, DEVICE
        )

        _model = m
    return _model, _tokenizer


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


def _extract_window_notes(
    notes: list, start_tick: int, end_tick: int, pitch_offset: int
) -> list:
    result = []
    for n in notes:
        if start_tick <= n.time < end_tick:
            new_n = copy.copy(n)
            new_n.pitch = max(0, min(127, n.pitch + pitch_offset))
            new_n.time = n.time - start_tick
            new_n.duration = min(n.duration, end_tick - n.time)
            result.append(new_n)
    return result


def _notes_to_tokens(
    notes: list, tpq: int, numerator: int, denominator: int, tokenizer: REMI
) -> list:
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


def _tokens_to_notes(token_ids: list, tokenizer: REMI, tpq: int) -> list:
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


@torch.no_grad()
def _generate_window(
    model: POP909Transformer,
    tokenizer: REMI,
    src_ids: list,
    prefix_ids: list,
    bar_id: int,
    complexity: float,
    creativity: float,
) -> list:
    """自迴歸生成伴奏；回傳完整 token list（不含 BOS/EOS，含前綴）。"""
    vocab = tokenizer.vocab
    BOS_ID = vocab.get("BOS_None", vocab.get("BOS", 0))
    EOS_ID = vocab.get("EOS_None", vocab.get("EOS", 0))
    top_k, top_p = _get_sampling_params(complexity)

    logger.info(
        "視窗生成參數：complexity=%.2f, creativity=%.2f, top_k=%d, top_p=%.2f",
        complexity,
        creativity,
        top_k,
        top_p,
    )

    early_stop_bars = WINDOW_BARS * 1.0
    force_eos_bars = WINDOW_BARS * 1.10

    src_tensor = torch.tensor([src_ids], dtype=torch.long).to(DEVICE)
    tgt_ids = [BOS_ID] + list(prefix_ids)

    for _ in range(len(prefix_ids), MAX_GEN_LEN):
        tgt_window = tgt_ids[-MODEL_MAX_LEN:]
        tgt_tensor = torch.tensor([tgt_window], dtype=torch.long).to(DEVICE)
        logits = model(src_tensor, tgt_tensor)
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
            logger.debug(
                "生成結束：命中 EOS @ step %d, 最終 Bar 數=%d",
                len(tgt_ids),
                tgt_ids.count(bar_id),
            )
            break

    return [t for t in tgt_ids if t not in (BOS_ID, EOS_ID)]


# ============================================================
# 核心推理（同步，供 asyncio.to_thread 包裝）
# ============================================================


def _run_inference(
    melody_midi_bytes: bytes, complexity: float = 0.5, creativity: float = 1.0
) -> tuple[bytes, list[str]]:
    """
    完整推理流程：
      1. 將 bytes 寫入暫存檔
      2. 調性分析 (music21)
      3. 滑動視窗生成
      4. 組合雙軌 MIDI 並回傳 bytes
    """
    model, tokenizer = _get_model_and_tokenizer()

    vocab = tokenizer.vocab
    BOS_ID = vocab.get("BOS_None", vocab.get("BOS", 0))
    EOS_ID = vocab.get("EOS_None", vocab.get("EOS", 0))

    if "Bar_None" not in vocab:
        raise ValueError("❌ Tokenizer 詞彙表中找不到 'Bar_None'，模型可能不相容。")
    BAR_ID = vocab["Bar_None"]

    # ── 1. 暫存輸入 MIDI ──────────────────────────────────────────────────────
    with tempfile.NamedTemporaryFile(suffix=".mid", prefix="accom_tmp_", delete=False) as f_in:
        f_in.write(melody_midi_bytes)
        tmp_path = f_in.name

    try:
        # ── 2. 讀取 & 解析 ────────────────────────────────────────────────────
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

        # ── 3. 調性分析 ───────────────────────────────────────────────────────
        to_c_offset, back_offset = _detect_key_offset(tmp_path)

        # ── 4. 計算滑動視窗起始小節 ────────────────────────────────────────────
        window_starts = list(range(0, total_bars - WINDOW_BARS + 1, STRIDE_BARS))
        if not window_starts or window_starts[-1] + WINDOW_BARS < total_bars:
            window_starts.append(max(0, total_bars - WINDOW_BARS))
        window_starts = sorted(set(window_starts))

        # ── 5. 逐視窗生成 ──────────────────────────────────────────────────────
        acc_notes_all: list = []
        prefix_token_ids: list = []

        for w_idx, bar_start in enumerate(window_starts):
            is_first = w_idx == 0
            bar_end = min(bar_start + WINDOW_BARS, total_bars)
            tick_start = bar_start * ticks_per_bar
            tick_end = bar_end * ticks_per_bar

            mel_notes = _extract_window_notes(
                all_notes, tick_start, tick_end, to_c_offset
            )
            if len(mel_notes) < 4:
                logger.debug(
                    "視窗 %d: 旋律音符不足 (%d), 跳過", w_idx + 1, len(mel_notes)
                )
                prefix_token_ids = []
                continue

            logger.info(
                "視窗 %d/%d: 小節 %d~%d, 旋律音符數=%d",
                w_idx + 1,
                len(window_starts),
                bar_start,
                bar_end,
                len(mel_notes),
            )

            src_body_ids = _notes_to_tokens(
                mel_notes, tpq, numerator, denominator, tokenizer
            )
            src_ids = [BOS_ID] + src_body_ids + [EOS_ID]

            full_tgt_token_ids = _generate_window(
                model,
                tokenizer,
                src_ids=src_ids,
                prefix_ids=prefix_token_ids,
                bar_id=BAR_ID,
                complexity=complexity,
                creativity=creativity,
            )

            full_notes = _tokens_to_notes(full_tgt_token_ids, tokenizer, tpq)
            if not full_notes:
                prefix_token_ids = []
                continue

            # ── 更新下一視窗前綴 ────────────────────────────────────────────────
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
            else:
                prefix_token_ids = []

            # ── 決定本視窗新增的音符 ────────────────────────────────────────────
            if is_first:
                new_notes = list(full_notes)
            else:
                prefix_tick_local = PREFIX_BARS * ticks_per_bar
                new_notes = [n for n in full_notes if n.time >= prefix_tick_local]

            # 還原到全局 tick
            for n in new_notes:
                n.time += tick_start

            # 還原音高回原調
            if back_offset != 0:
                for n in new_notes:
                    n.pitch = max(0, min(127, n.pitch + back_offset))

            acc_notes_all.extend(new_notes)

        if not acc_notes_all:
            raise ValueError("模型未生成任何伴奏音符")

        # ── 6. 組合雙軌 MIDI ───────────────────────────────────────────────────
        acc_notes_all.sort(key=lambda n: (n.time, n.pitch))

        mel_track = orig_score.tracks[0]
        mel_track.program = 73  # 長笛

        acc_track = symusic.Track()
        acc_track.program = 0  # 鋼琴
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

        # ── 7. 序列化為 bytes ──────────────────────────────────────────────────
        with tempfile.NamedTemporaryFile(suffix=".mid", prefix="accom_tmp_", delete=False) as f_out:
            out_path = f_out.name
        try:
            combined.dump_midi(out_path)
            with open(out_path, "rb") as f:
                return f.read(), []
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ============================================================
# 公開的非同步 Service 函式
# ============================================================


async def generate(
    melody_midi_bytes: bytes, complexity: float = 0.5, creativity: float = 1.0
) -> tuple[bytes, list[str]]:
    """
    使用 oneStage (norm_false) 模型為旋律生成伴奏，回傳雙軌 MIDI bytes。

    Args:
        melody_midi_bytes: 單軌旋律的 MIDI bytes
        complexity:        伴奏複雜度 0.0=極簡 ~ 1.0=複雜（預設 0.5）
        creativity:        創意程度（預設 1.0，越低越穩定）

    Returns:
        雙軌 MIDI bytes（旋律軌 + 伴奏軌）及空氣和弦清單
    """
    return await asyncio.to_thread(
        _run_inference, melody_midi_bytes, complexity, creativity
    )
