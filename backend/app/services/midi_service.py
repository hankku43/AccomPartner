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
from typing import List

import mido

from app.models.schemas import NoteEvent

TICKS_PER_BEAT = 480
TICKS_PER_8TH = TICKS_PER_BEAT // 2  # = 240 ticks per 8th-note slot


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
