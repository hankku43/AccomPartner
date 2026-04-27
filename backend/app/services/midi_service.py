"""
midi_service.py
---------------
將前端傳入的 JSON 音符列表轉換為標準 MIDI 二進位資料（bytes）。

轉換規則：
  - 時間單位：8 分音符（8th note）
  - 1 beat = 2 個 8th-note slot（4/4 拍）
  - ticks_per_beat = 480（標準解析度）
  - ticks_per_8th  = ticks_per_beat // 2 = 240
"""

import io
import logging
from typing import List

import mido

from app.models.schemas import NoteEvent

logger = logging.getLogger(__name__)

TICKS_PER_BEAT = 480
TICKS_PER_8TH = TICKS_PER_BEAT // 2  # = 240 ticks per 8th-note slot

# ── 和弦轉調工具 ──────────────────────────────────────────────────────────────
_CHROMATIC = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
_ENHARMONIC = {
    'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#',
    'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B',
}


def transpose_chord_name(chord: str, semitones: int) -> str:
    """
    將單一和弦名稱按 semitones 半音轉調。
    例如：transpose_chord_name('Am', 5) → 'Dm'
         transpose_chord_name('G7', -7) → 'C7'
    對 'N'（無和弦）或空字串，直接回傳原值。
    """
    if not chord or chord in ('N', 'X', ''):
        return chord

    # 解析根音（1 ~ 2 字元：字母 + 可選的 # 或 b）
    if len(chord) >= 2 and chord[1] in ('#', 'b'):
        root, quality = chord[:2], chord[2:]
    else:
        root, quality = chord[:1], chord[1:]

    root_norm = _ENHARMONIC.get(root, root)
    if root_norm not in _CHROMATIC:
        return chord  # 未知根音，原樣回傳

    new_root = _CHROMATIC[(_CHROMATIC.index(root_norm) + semitones) % 12]
    return new_root + quality


def transpose_chord_list(chords: list, semitones: int) -> list:
    """
    轉調整個和弦列表（支援 List[str] 或 List[List[str]] 格式）。
    semitones = back_offset（從模型 C/Am 空間還原至原始調性所需的半音數）。
    """
    if semitones == 0:
        return chords
    if chords and isinstance(chords[0], list):
        return [
            [transpose_chord_name(c, semitones) for c in bar]
            for bar in chords
        ]
    return [transpose_chord_name(c, semitones) for c in chords]


# ── MIDI 內建調號讀取 ─────────────────────────────────────────────────────────

# mido key_signature 格式 → 轉至 C/Am 所需的半音偏移量
# 正值 = 向上移；負值 = 向下移
_MIDO_KEY_MAJOR_OFFSETS: dict[str, int] = {
    "C": 0, "G": -7, "D": -2, "A": -9, "E": -4, "B": -11,
    "F#": 6, "C#": -1, "Gb": 6, "Db": -1, "Ab": 4,
    "Eb": -3, "Bb": 2, "F": -5, "Cb": 0,
}
# minor: 目標是 Am，以相對主音計算 → 相對大調再調整 −9 (A = C - 3 semitones... 其實minor tonic to A)
# easier: minor key X → need X + offset = A(9); offset = 9 - X_semitone
# 直接對照各 minor tonic 到 A(= 9) 的偏移
_MIDO_KEY_MINOR_OFFSETS: dict[str, int] = {
    "A": 0, "E": -7, "B": -2, "F#": -9, "C#": -4, "G#": -11,
    "D#": 6, "A#": -1, "Eb": 6, "Bb": -1, "F": 4,
    "C": -3, "G": 2, "D": -5, "Ab": 4,
}


def read_key_str_from_midi(midi_path: str) -> str | None:
    """讀取 MIDI 檔案的第一個 key_signature meta event 的字串（例如 'C', 'Am', 'Bb'）。"""
    try:
        mid = mido.MidiFile(midi_path)
        for track in mid.tracks:
            for msg in track:
                if msg.type == "key_signature":
                    return msg.key
    except Exception as exc:
        logger.warning("讀取 MIDI key_signature 失敗：%s", exc)
    return None


def read_key_signature_from_midi(midi_path: str) -> tuple[int, int, int] | None:
    """
    讀取 MIDI 檔案的第一個 key_signature meta event。
    回傳 (to_c_offset, back_offset, semitones_to_c) 或 None（檔案無調號標記時）。
    """
    try:
        mid = mido.MidiFile(midi_path)
        for track in mid.tracks:
            for msg in track:
                if msg.type == "key_signature":
                    key_str: str = msg.key  # e.g. "G", "Bb", "Am", "F#m"
                    is_minor = key_str.endswith("m")
                    tonic = key_str[:-1] if is_minor else key_str

                    offset_map = _MIDO_KEY_MINOR_OFFSETS if is_minor else _MIDO_KEY_MAJOR_OFFSETS
                    offset = offset_map.get(tonic)
                    if offset is None:
                        logger.warning("未知的 MIDI 調號標記：%s，略過", key_str)
                        return None

                    logger.info(
                        "偵測到 MIDI 內建調號：%s → to_c_offset=%+d", key_str, offset
                    )
                    return offset, -offset, offset
    except Exception as exc:
        logger.warning("讀取 MIDI key_signature meta event 失敗：%s", exc)
    return None



def notes_to_midi(notes: List[NoteEvent], bpm: int = 120) -> bytes:
    """
    把 NoteEvent 列表轉換成 MIDI bytes，包含單一旋律軌道。

    Args:
        notes: 旋律音符列表（來自前端 JSON）
        bpm:   每分鐘拍數

    Returns:
        MIDI 檔案的二進位內容（bytes）
    """
    mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    # 設定 Tempo
    tempo = mido.bpm2tempo(bpm)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    # 設定拍號 4/4
    track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))

    # 將音符事件展開為 (absolute_tick, type, pitch, velocity)
    events: list[tuple[int, str, int, int]] = []
    for note in notes:
        on_tick = note.step * TICKS_PER_8TH
        off_tick = (note.step + note.duration) * TICKS_PER_8TH
        events.append((on_tick, "note_on", note.pitch, 80))
        events.append((off_tick, "note_off", note.pitch, 0))

    # 依 tick 排序（note_off 優先於同 tick 的 note_on）
    events.sort(key=lambda e: (e[0], 0 if e[1] == "note_off" else 1))

    # 轉換成 delta-time MIDI messages
    current_tick = 0
    for abs_tick, msg_type, pitch, velocity in events:
        delta = abs_tick - current_tick
        track.append(mido.Message(msg_type, note=pitch, velocity=velocity, time=delta))
        current_tick = abs_tick

    track.append(mido.MetaMessage("end_of_track", time=0))

    # 序列化為 bytes
    buf = io.BytesIO()
    mid.save(file=buf)
    return buf.getvalue()


def extract_track_from_midi(midi_bytes: bytes, track_index: int) -> bytes:
    """
    從完整的 MIDI bytes 中提取指定音軌，回傳只有該軌的 MIDI bytes。

    用於 /api/generate-from-midi 端點的前置處理。
    """
    src = mido.MidiFile(file=io.BytesIO(midi_bytes))

    if track_index < 0 or track_index >= len(src.tracks):
        raise ValueError(f"音軌索引 {track_index} 超出範圍 (共 {len(src.tracks)} 條軌道)")

    out = mido.MidiFile(ticks_per_beat=src.ticks_per_beat)

    # 複製 meta / tempo track（若存在，通常為第 0 軌）
    if len(src.tracks) > 0 and track_index != 0:
        out.tracks.append(src.tracks[0])

    out.tracks.append(src.tracks[track_index])

    buf = io.BytesIO()
    out.save(file=buf)
    return buf.getvalue()


def add_chords_to_midi(midi_bytes: bytes, final_chords: List[List[str]], key_signature: str = None) -> bytes:
    """
    將和弦標記以 Marker Meta Event 的形式嵌入 MIDI bytes，追加一條獨立的 Chord 軌道。
    同時在 Track 0 注入正確的調號 (key_signature) Meta Message。
    """
    try:
        src = mido.MidiFile(file=io.BytesIO(midi_bytes))

        # ── 0. 注入調號至所有音軌 ────────────────────────────────────────────
        if key_signature:
            if len(key_signature) > 0:
                key_signature = key_signature[0].upper() + key_signature[1:]
                
            for track in src.tracks:
                # 先移除該軌道中原本的 key_signature 事件
                new_events = [msg for msg in track if msg.type != "key_signature"]
                # 在該軌道最前面插入新的調號
                new_events.insert(0, mido.MetaMessage("key_signature", key=key_signature, time=0))
                
                # 清空並重新載入軌道內容
                track.clear()
                track.extend(new_events)
            logger.info("已在所有軌道中強制作為調號：%s", key_signature)

            







        # ── 1. 讀取拍號（預設 4/4，供後續計算小節 tick）──────────────────────
        numerator = 4
        denominator = 4
        for track in src.tracks:
            for msg in track:
                if msg.type == "time_signature":
                    numerator = msg.numerator
                    denominator = msg.denominator
                    break



        # 一小節的 tick 數（4/4 = 4 * ticks_per_beat；3/4 = 3 * ticks_per_beat）
        ticks_per_bar = int(4 * src.ticks_per_beat * numerator / denominator)

        # ── 2. 建立新的 Chord 軌道 ────────────────────────────────────────────
        chord_track = mido.MidiTrack()
        chord_track.append(
            mido.MetaMessage("track_name", name="Chords", time=0)
        )

        # ── 3. 展開所有和弦事件 (absolute_tick, chord_text) ───────────────────
        events: List[tuple] = []
        for bar_idx, bar_chords in enumerate(final_chords):
            if not bar_chords:
                continue

            steps = len(bar_chords)  # 通常 = numerator（幾拍）
            ticks_per_step = ticks_per_bar // steps
            bar_start_tick = bar_idx * ticks_per_bar

            for step_idx, chord in enumerate(bar_chords):
                # 略過空和弦
                if not chord or chord == "N":
                    continue
                abs_tick = bar_start_tick + step_idx * ticks_per_step
                events.append((abs_tick, chord))

        # ── 4. Run-length 去重：只在和弦「變化」時寫入 marker ─────────────────
        deduped: List[tuple] = []
        prev_chord = None
        for abs_tick, chord in events:
            if chord != prev_chord:
                deduped.append((abs_tick, chord))
                prev_chord = chord

        # ── 5. 轉成 delta-time 並寫入軌道 ────────────────────────────────────
        current_tick = 0
        for abs_tick, chord in deduped:
            delta = abs_tick - current_tick
            chord_track.append(
                mido.MetaMessage("marker", text=chord, time=delta)
            )
            current_tick = abs_tick

        # ── 6. 附加軌道並序列化 ───────────────────────────────────────────────
        if len(deduped) > 0:
            src.tracks.append(chord_track)

        buf = io.BytesIO()
        src.save(file=buf)
        return buf.getvalue()

    except Exception as e:
        logger.warning("add_chords_to_midi 失敗，回傳原始 MIDI bytes：%s", e)
        return midi_bytes





