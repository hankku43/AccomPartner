<template>
  <section class="workspace-panel realtime-dark-theme immersive-layout">
    <div class="sidebar glass-panel">
      <div class="control-section">
        <h4 class="section-title">Engine Setup</h4>
        <div class="control-row">
          <div class="control-group">
            <label>Target BPM</label>
            <input
              type="number"
              v-model.number="realtimeBPM"
              class="modern-input"
              min="40"
              :max="currentMaxBPM"
              :disabled="isRealtimePlaying"
            />
          </div>
          <div class="control-group">
            <label>Metronome</label>
            <select v-model="metronomeStyle" class="modern-select" :disabled="isRealtimePlaying">
              <option value="beep">Beep Click</option>
              <option value="drum">Drum Kit</option>
            </select>
          </div>
        </div>
      </div>

      <div class="control-section">
        <h4 class="section-title">Mixer</h4>

        <div class="mixer-row">
          <div class="mixer-info">
            <label>User Piano</label>
            <div class="mute-toggle">
              <input type="checkbox" :id="'muteUser'" v-model="muteUser" />
              <label :for="'muteUser'">Mute</label>
            </div>
          </div>
          <input
            type="range"
            v-model="userVolume"
            min="0"
            max="100"
            class="volume-slider"
            :disabled="muteUser"
          />
        </div>

        <div class="mixer-row">
          <div class="mixer-info">
            <label>AI Accompaniment</label>
            <div class="mute-toggle">
              <input type="checkbox" :id="'muteAi'" v-model="muteAi" />
              <label :for="'muteAi'">Mute</label>
            </div>
          </div>
          <input
            type="range"
            v-model="aiVolume"
            min="0"
            max="100"
            class="volume-slider"
            :disabled="muteAi"
          />
        </div>

        <div class="mixer-row">
          <div class="mixer-info">
            <label>Metronome</label>
            <div class="mute-toggle">
              <input type="checkbox" :id="'muteMetro'" v-model="muteMetronome" />
              <label :for="'muteMetro'">Mute</label>
            </div>
          </div>
          <input
            type="range"
            v-model="metroVolume"
            min="0"
            max="100"
            class="volume-slider"
            :disabled="muteMetronome"
          />
        </div>
      </div>

      <div class="control-section">
        <h4 class="section-title">AI Personality & Style</h4>
        <div class="control-row-simple mb-15">
          <label class="small-label">Starting Style</label>
          <select v-model="selectedBaseStyle" class="modern-select minimal w-100">
            <option value="soft">Soft (Arpeggio)</option>
            <option value="light">Light (Rhythmic)</option>
            <option value="grave">Grave (Deep)</option>
          </select>
        </div>

        <div class="mixer-row">
          <div class="mixer-info">
            <label>Creativity (Insp.)</label>
            <span class="value-label">×{{ (aiCreativity / 100).toFixed(1) }}</span>
          </div>
          <input
            type="range"
            v-model.number="aiCreativity"
            min="50"
            max="200"
            step="10"
            class="volume-slider accent-purple"
          />
        </div>
        <div class="mixer-row">
          <div class="mixer-info">
            <label>Complexity (Texture)</label>
            <span class="value-label">{{ aiComplexity }}%</span>
          </div>
          <input
            type="range"
            v-model.number="aiComplexity"
            min="10"
            max="100"
            step="5"
            class="volume-slider accent-blue"
          />
        </div>
      </div>

      <div class="control-section">
        <h4 class="section-title">Visuals</h4>
        <div class="anim-switches">
          <div class="switch-row">
            <div
              class="modern-switch"
              :class="{ active: enableUserAnimation }"
              @click="toggleUserAnimation"
            >
              <div class="switch-handle"></div>
            </div>
            <label @click="toggleUserAnimation">User Input Animation</label>
          </div>
          <div class="switch-row">
            <div
              class="modern-switch"
              :class="{ active: enableAiAnimation }"
              @click="toggleAiAnimation"
            >
              <div class="switch-handle"></div>
            </div>
            <label @click="toggleAiAnimation">AI Accompaniment Animation</label>
          </div>
        </div>
      </div>

      <div class="action-buttons sidebar-actions">
        <button
          v-if="!isRealtimePlaying"
          @click="startRealtime"
          class="modern-btn btn-primary btn-large w-100"
        >
          <span style="font-size: 1.2rem; font-family: 'Outfit', sans-serif">Start Engine 🚀</span>
        </button>
        <button v-else @click="stopRealtime" class="modern-btn btn-danger btn-large w-100">
          <span style="font-size: 1.2rem; font-family: 'Outfit', sans-serif">Stop Engine 🛑</span>
        </button>
      </div>
    </div>

    <div class="main-stage">
      <div class="stage-inner-wrapper">
        <div class="canvas-container">
          <canvas
            ref="rtAiCanvas"
            width="1220"
            height="430"
            class="stage-canvas"
            style="z-index: 1"
          ></canvas>
          <canvas
            ref="rtSlidingCanvas"
            width="1220"
            height="430"
            class="stage-canvas"
            style="z-index: 2"
          ></canvas>
        </div>

        <div class="modern-keyboard stage-keyboard">
          <div
            v-for="key in pianoKeys"
            :key="key.midi"
            class="piano-key"
            :class="[
              key.isWhite ? 'white-key' : 'black-key',
              { active: activeKeys.has(key.keyCode) },
            ]"
            @mousedown.prevent="rtHandleMouseDown(key)"
            @mouseup.prevent="rtHandleMouseUp(key)"
            @mouseleave.prevent="rtHandleMouseUp(key)"
          >
            <span class="key-label">{{ key.note }}</span>
            <span v-if="key.key" class="key-binding">{{ key.key }}</span>
          </div>
        </div>
      </div>

      <div class="stage-footer compact-footer">
        <div class="glass-container rt-staff-panel">
          <div class="mini-status-bar">
            <div class="mini-status-item" :class="{ 'is-active': isRealtimePlaying }">
              <div class="status-dot"></div>
              <span :style="{ color: isRealtimePlaying ? '#5fe3a1' : '#f1c40f' }">{{
                realtimeStatus
              }}</span>
            </div>
            <div class="mini-status-divider"></div>
            <div class="mini-status-item">
              <span
                >Measure: <strong>{{ currentBar >= 0 ? currentBar + 1 : '--' }}</strong></span
              >
            </div>
            <div class="mini-status-item">
              <span
                >Beat:
                <strong :class="{ 'beat-pulse-text': beatPulse }">{{
                  isRealtimePlaying ? currentBeat : '-'
                }}</strong></span
              >
            </div>

            <!-- 🌟 移入：MIDI 下載按鍵，並加入動態禁用邏輯 -->
            <div class="mini-status-divider"></div>
            <button
              @click="downloadRealtimeMidi"
              class="mini-export-btn"
              :disabled="
                isRealtimePlaying ||
                (realtimeRecordedNotes.length === 0 && realtimeRecordedAI.length === 0)
              "
              title="Download results after stopping playback"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              MIDI
            </button>
          </div>

          <div ref="rtVexflowContainer" class="rt-vexflow-container"></div>
        </div>
      </div>
    </div>

    <Transition name="fade">
      <div v-if="showCalibrationModal" class="modal-overlay">
        <div class="modal-content glass-panel calibrator-card">
          <div class="modal-header">
            <h3>🚀 System Performance Benchmark</h3>
            <p v-if="isCalibrating">Optimizing engine for your hardware...</p>
            <p v-else>Benchmark complete. Safety limits have been applied.</p>
          </div>

          <div v-if="isCalibrating" class="calibration-loader">
            <div class="progress-bar-container">
              <div class="progress-bar-fill" :style="{ width: calibrationProgress + '%' }"></div>
            </div>
            <div class="progress-text">
              {{ Math.round(calibrationProgress) }}% Analysing Inference Speed...
            </div>
          </div>

          <div v-else class="calibration-report">
            <div class="stats-grid">
              <div class="stat-box">
                <span class="stat-label">Avg. Latency</span>
                <span class="stat-value">{{ calibrationSummary.avg.toFixed(1) }}ms</span>
              </div>
              <div class="stat-box" :class="{ warning: calibrationSummary.std > 50 }">
                <span class="stat-label">Jitter (Std dev)</span>
                <span class="stat-value">±{{ calibrationSummary.std.toFixed(1) }}ms</span>
              </div>
            </div>

            <div class="result-summary">
              <div class="limit-item">
                <span class="label">Current Safe Limit:</span>
                <span class="value highlight">{{ currentMaxBPM }} BPM</span>
              </div>
              <div class="limit-item">
                <span class="label">Animation Status:</span>
                <div class="flex-row">
                  <div
                    class="modern-switch small"
                    :class="{ active: modalAnimationState }"
                    @click="toggleAnimationInModal"
                  >
                    <div class="switch-handle"></div>
                  </div>
                  <span class="value">{{ modalAnimationState ? 'Enabled' : 'Disabled' }}</span>
                </div>
              </div>
            </div>

            <div class="notice-info">
              <p v-if="calibrationSummary.lowSafeBPM">
                ⚠️ Restricted BPM limit due to device performance constraints.
              </p>
              <p
                v-if="!modalAnimationState && realtimeBPM > safeBPMWithAnim"
                class="highlight-warning"
              >
                💡 Enabling animations will lower your current BPM to {{ safeBPMWithAnim }} to
                ensure stability.
              </p>
              <p v-else-if="calibrationSummary.autoDisabledAnim && !modalAnimationState">
                ✅ Animations are currently disabled for maximum speed.
              </p>
              <p v-else>✅ Your device is capable of high-speed accompaniment.</p>
            </div>

            <button @click="confirmAndStart" class="modern-btn btn-primary btn-full mt-20">
              Confirm & Start Playing
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </section>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import * as Tone from 'tone'
import { Midi } from '@tonejs/midi'
import {
  Renderer,
  Stave,
  StaveNote,
  Accidental,
  Voice,
  Formatter,
  Dot,
  StaveConnector,
  Annotation,
  Barline,
} from 'vexflow'
import tokenizerService from '../../services/tokenizerService'
import aiService from '../../services/aiService'
import audioService from '../../services/audioService'

const isRealtimePlaying = ref(false)
const realtimeStatus = ref('Ready...')
const currentBar = ref(-1)
const currentBeat = ref(1)
const beatPulse = ref(false) // 🌟 補回缺失變數
const realtimeBPM = ref(60)
const metronomeStyle = ref('beep')
const visibleBarCount = ref(3) // 預設 3，將在 onMounted 更新

// Mixer 控制
const muteMetronome = ref(false)
const muteUser = ref(false)
const muteAi = ref(false)
const userVolume = ref(80)
const aiVolume = ref(80)
const metroVolume = ref(80)

// 動畫開關分離
const enableUserAnimation = ref(true)
const enableAiAnimation = ref(true)

// Modal 統一綁定狀態 (若兩者其一關閉，就視為未全開)
const modalAnimationState = computed(() => enableUserAnimation.value && enableAiAnimation.value)

// 性能檢測相關
const isCalibrated = ref(false)
const showCalibrationModal = ref(false)
const isCalibrating = ref(false)
const calibrationProgress = ref(0)
const safeBPMWithAnim = ref(100)
const absoluteMaxBPM = ref(100)
const calibrationSummary = ref({ avg: 0, std: 0, autoDisabledAnim: false, lowSafeBPM: false })
const aiCreativity = ref(100) // 創造力: 50~200 (對應 0.5~2.0)
const aiComplexity = ref(50) // 複雜度: 10~100 (對應 0.55~1.0)
const selectedBaseStyle = ref('soft') // 起始風格 (soft/light/grave)

// 🌟 預定義風格資料 (單位: Position 0~15, Duration in Ticks 1~16)
const BASE_STYLES = {
  soft: [
    { midi: 48, pos: 0, dur: 2 },
    { midi: 55, pos: 2, dur: 2 },
    { midi: 64, pos: 4, dur: 2 },
    { midi: 55, pos: 6, dur: 2 },
    { midi: 62, pos: 8, dur: 2 },
    { midi: 55, pos: 10, dur: 2 },
    { midi: 60, pos: 12, dur: 2 },
    { midi: 55, pos: 14, dur: 2 },
  ],
  light: [
    { midi: 48, pos: 0, dur: 4 },
    { midi: 55, pos: 2, dur: 2 },
    { midi: 60, pos: 2, dur: 2 },
    { midi: 64, pos: 2, dur: 2 },
    { midi: 55, pos: 4, dur: 2 },
    { midi: 60, pos: 4, dur: 2 },
    { midi: 64, pos: 4, dur: 2 },
    { midi: 55, pos: 6, dur: 2 },
    { midi: 60, pos: 6, dur: 2 },
    { midi: 64, pos: 6, dur: 2 },
    { midi: 48, pos: 8, dur: 4 },
    { midi: 55, pos: 10, dur: 2 },
    { midi: 60, pos: 10, dur: 2 },
    { midi: 64, pos: 10, dur: 2 },
    { midi: 55, pos: 12, dur: 2 },
    { midi: 60, pos: 12, dur: 2 },
    { midi: 64, pos: 12, dur: 2 },
    { midi: 55, pos: 14, dur: 2 },
    { midi: 60, pos: 14, dur: 2 },
    { midi: 64, pos: 14, dur: 2 },
  ],
  grave: [
    { midi: 52, pos: 0, dur: 8 },
    { midi: 36, pos: 0, dur: 8 },
    { midi: 43, pos: 0, dur: 8 },
    { midi: 55, pos: 8, dur: 8 },
    { midi: 43, pos: 8, dur: 8 },
    { midi: 48, pos: 8, dur: 8 },
    { midi: 52, pos: 8, dur: 8 },
  ],
}

// 監聽音量變化：加入 Gain 補償大幅提升上限
watch(userVolume, (val) => {
  // 將 0~100 映射到 0~2.5 Gain (約 +8dB)
  if (audioService.melodySynth)
    audioService.melodySynth.volume.value = Tone.gainToDb((val / 100) * 2.5)
})
watch(aiVolume, (val) => {
  if (audioService.accSynth) audioService.accSynth.volume.value = Tone.gainToDb((val / 100) * 2.5)
})
watch(metroVolume, (val) => {
  const gain = (val / 100) * 2.5
  if (audioService.metronome) audioService.metronome.volume.value = Tone.gainToDb(gain)
  if (audioService.kickSynth) audioService.kickSynth.volume.value = Tone.gainToDb(gain)
  if (audioService.hatSynth) audioService.hatSynth.volume.value = Tone.gainToDb(gain)
  if (audioService.snareSynth) audioService.snareSynth.volume.value = Tone.gainToDb(gain)
})

// 強制 BPM 範圍防呆 (防止手動輸入超過 Max)
watch(realtimeBPM, (newVal) => {
  if (newVal > currentMaxBPM.value) {
    realtimeBPM.value = currentMaxBPM.value
  } else if (newVal < 40 && newVal !== null && newVal !== '') {
    // 預留刪除時的空值，否則無法重新輸入
    realtimeBPM.value = 40
  }
})

const generatePianoKeys = (startOctave = 3, numOctaves = 3) => {
  const keys = []
  const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
  const keyMap = {
    48: { k: 'z', code: 'KeyZ' },
    49: { k: 's', code: 'KeyS' },
    50: { k: 'x', code: 'KeyX' },
    51: { k: 'd', code: 'KeyD' },
    52: { k: 'c', code: 'KeyC' },
    53: { k: 'v', code: 'KeyV' },
    54: { k: 'g', code: 'KeyG' },
    55: { k: 'b', code: 'KeyB' },
    56: { k: 'h', code: 'KeyH' },
    57: { k: 'n', code: 'KeyN' },
    58: { k: 'j', code: 'KeyJ' },
    59: { k: 'm', code: 'KeyM' },
    60: { k: 'q', code: 'KeyQ', altK: ',', altCode: 'Comma' },
    61: { k: '2', code: 'Digit2', altK: 'l', altCode: 'KeyL' },
    62: { k: 'w', code: 'KeyW', altK: '.', altCode: 'Period' },
    63: { k: '3', code: 'Digit3', altK: ';', altCode: 'Semicolon' },
    64: { k: 'e', code: 'KeyE', altK: '/', altCode: 'Slash' },
    65: { k: 'r', code: 'KeyR' },
    66: { k: '5', code: 'Digit5' },
    67: { k: 't', code: 'KeyT' },
    68: { k: '6', code: 'Digit6' },
    69: { k: 'y', code: 'KeyY' },
    70: { k: '7', code: 'Digit7' },
    71: { k: 'u', code: 'KeyU' },
    72: { k: 'i', code: 'KeyI' },
    73: { k: '9', code: 'Digit9' },
    74: { k: 'o', code: 'KeyO' },
    75: { k: '0', code: 'Digit0' },
    76: { k: 'p', code: 'KeyP' },
  }
  for (let oct = startOctave; oct < startOctave + numOctaves; oct++) {
    for (let i = 0; i < 12; i++) {
      const isWhite = !notes[i].includes('#')
      const noteName = `${notes[i]}${oct}`
      const midi = (oct + 1) * 12 + i
      keys.push({
        key: keyMap[midi]
          ? keyMap[midi].altK
            ? `${keyMap[midi].k.toUpperCase()} / ${keyMap[midi].altK.toUpperCase()}`
            : keyMap[midi].k.toUpperCase()
          : '',
        keyCode: keyMap[midi] ? keyMap[midi].code : `Midi${midi}`,
        note: noteName,
        midi: midi,
        isWhite: isWhite,
      })
    }
  }
  const finalMidi = (startOctave + numOctaves + 1) * 12
  keys.push({
    key: '',
    keyCode: `Midi${finalMidi}`,
    note: `C${startOctave + numOctaves}`,
    midi: finalMidi,
    isWhite: true,
  })
  return keys
}
const pianoKeys = generatePianoKeys(3, 3)

const activeKeys = ref(new Set())
const keyAliases = {
  Comma: 'KeyQ',
  KeyL: 'Digit2',
  Period: 'KeyW',
  Semicolon: 'Digit3',
  Slash: 'KeyE',
}
const generationHistory = ref([])

let schedulerId = null
let currentlyPlayingNotes = new Map()
let recordingStartTime = 0
const currentBarNotes = ref([])
let previousAccompaniment = []
let realtimeRecordedNotes = []
let realtimeRecordedAI = []

const rtSlidingCanvas = ref(null)
const rtAiCanvas = ref(null)
let rtVisualizerFrameId = null
let rtVisualizerNotes = []

const getBeatDuration = () => 60 / realtimeBPM.value
const getBarDuration = () => getBeatDuration() * 4
let barCount = 0
let aiSchedulerId = null

const initToneJs = async () => {
  await audioService.init()
  await tokenizerService.init()
  await aiService.init()

  // 初始化設定音量：補上 * 2.5 增益補償，保持與 watch 邏輯一致
  if (audioService.melodySynth) {
    audioService.melodySynth.volume.value = Tone.gainToDb((userVolume.value / 100) * 2.5)
  }
  if (audioService.accSynth) {
    audioService.accSynth.volume.value = Tone.gainToDb((aiVolume.value / 100) * 2.5)
  }

  // 補上節拍器與鼓組的初始音量設定
  const metroGain = (metroVolume.value / 100) * 2.5
  if (audioService.metronome) audioService.metronome.volume.value = Tone.gainToDb(metroGain)
  if (audioService.kickSynth) audioService.kickSynth.volume.value = Tone.gainToDb(metroGain)
  if (audioService.hatSynth) audioService.hatSynth.volume.value = Tone.gainToDb(metroGain)
  if (audioService.snareSynth) audioService.snareSynth.volume.value = Tone.gainToDb(metroGain)
}

const triggerKeyStart = (key) => {
  if (activeKeys.value.has(key.keyCode)) return
  activeKeys.value.add(key.keyCode)
  const noteName = Tone.Frequency(key.midi, 'midi').toNote()
  if (!muteUser.value) {
    audioService.melodySynth.triggerAttack(noteName)
  }
  currentlyPlayingNotes.set(key.keyCode, { midi: key.midi, note: key.note, startTime: Tone.now() })
}

const triggerKeyEnd = (key) => {
  if (!activeKeys.value.has(key.keyCode)) return
  activeKeys.value.delete(key.keyCode)
  const noteName = Tone.Frequency(key.midi, 'midi').toNote()
  audioService.melodySynth.triggerRelease(noteName)

  const noteInfo = currentlyPlayingNotes.get(key.keyCode)
  if (noteInfo) {
    const duration = Math.max(0.01, Tone.now() - noteInfo.startTime)
    const timeOffset = noteInfo.startTime - recordingStartTime

    if (enableUserAnimation.value) {
      rtVisualizerNotes.push({
        midi: noteInfo.midi,
        start: noteInfo.startTime,
        end: Tone.now(),
        isAi: false,
      })
    }

    if (timeOffset >= -0.1 && timeOffset < getBarDuration()) {
      const safeTimeOffset = Math.max(0, timeOffset)
      currentBarNotes.value.push({ midi: noteInfo.midi, time: safeTimeOffset, duration })
      if (barCount >= 0) {
        realtimeRecordedNotes.push({
          pitch: noteInfo.midi,
          step: Math.round((barCount * 4 + safeTimeOffset / getBeatDuration()) * 2),
          duration: Math.max(1, Math.round(duration / (getBeatDuration() / 2))),
          exactTime: barCount * getBarDuration() + safeTimeOffset,
          exactDuration: duration,
          velocity: 0.8,
        })
      }
    }
    currentlyPlayingNotes.delete(key.keyCode)
  }
}

const getPianoKeyX = (midi) => {
  const baseMidi = 48
  if (midi < baseMidi) return 0
  const offset = midi - baseMidi
  const octaves = Math.floor(offset / 12)
  const pitchInOctave = offset % 12
  const whiteCounts = [0, 1, 1, 2, 2, 3, 4, 4, 5, 5, 6, 6]
  const isWhiteList = [true, false, true, false, true, true, false, true, false, true, false, true]
  // 🌟 校準：針對 1220px 畫布，置中偏移應為 (1220 - 858)/2 = 181
  const centeringOffset = 181
  const wIndex = octaves * 7 + whiteCounts[pitchInOctave]

  if (isWhiteList[pitchInOctave]) {
    return centeringOffset + wIndex * 39
  } else {
    // 🌟 修復：原本的 +1 是誤算，導致黑鍵向右偏移了一個白鍵
    return centeringOffset + wIndex * 39 - 12
  }
}

const getVisualizerKeyWidth = (midi) => {
  const isWhite = [true, false, true, false, true, true, false, true, false, true, false, true][
    (midi - 48) % 12
  ]
  // 🌟 校準：白鍵 CSS 39px -> 動畫 37px (左右各留 1px)；黑鍵 CSS 24px -> 動畫 24px
  return isWhite ? 37 : 24
}

const drawRealtimeVisualizer = () => {
  if (!rtSlidingCanvas.value || !rtAiCanvas.value) {
    rtVisualizerFrameId = requestAnimationFrame(drawRealtimeVisualizer)
    return
  }
  rtVisualizerFrameId = requestAnimationFrame(drawRealtimeVisualizer)

  const ctx = rtSlidingCanvas.value.getContext('2d')
  const ctxAi = rtAiCanvas.value.getContext('2d')

  // 🌟 強制確保 Canvas 邏輯維度與 CSS 一致 (1220px)
  if (rtSlidingCanvas.value.width !== 1220 || rtSlidingCanvas.value.height !== 430) {
    rtSlidingCanvas.value.width = 1220
    rtSlidingCanvas.value.height = 430
    rtAiCanvas.value.width = 1220
    rtAiCanvas.value.height = 430
  }

  const w = 1220
  const h = 430

  if (!isRealtimePlaying.value || (!enableUserAnimation.value && !enableAiAnimation.value)) {
    ctx.clearRect(0, 0, w, h)
    ctxAi.clearRect(0, 0, w, h)
    return
  }

  // 分別依據開關清除畫布
  if (!enableUserAnimation.value) ctx.clearRect(0, 0, w, h)
  else {
    ctx.clearRect(0, 0, w, h)
    ctx.shadowBlur = 8
  }

  if (!enableAiAnimation.value) ctxAi.clearRect(0, 0, w, h)
  else {
    ctxAi.clearRect(0, 0, w, h)
  }

  const now = Tone.now()
  const pps = 120
  const pitchClassToCol = [0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6]

  for (let i = rtVisualizerNotes.length - 1; i >= 0; i--) {
    const note = rtVisualizerNotes[i]
    const ageSinceEnd = now - note.end

    if (!note.isAi) {
      if (ageSinceEnd * pps > h + 200) {
        rtVisualizerNotes.splice(i, 1)
        continue
      }
      if (enableUserAnimation.value) {
        const yOffset = h - (now - note.start) * pps
        const nh = (note.end - note.start) * pps
        const xOffset = getPianoKeyX(note.midi)
        const kw = getVisualizerKeyWidth(note.midi)
        const x = xOffset + 1
        const noteW = kw - 2
        const r = Math.min(4, noteW / 2)

        // Gradient fill for note bar
        const grad = ctx.createLinearGradient(x, yOffset, x + noteW, yOffset + nh)
        grad.addColorStop(0, 'rgba(120, 255, 195, 0.95)')
        grad.addColorStop(0.5, 'rgba(95, 227, 161, 0.9)')
        grad.addColorStop(1, 'rgba(50, 180, 130, 0.7)')

        ctx.shadowBlur = 18
        ctx.shadowColor = 'rgba(95, 227, 161, 0.7)'

        ctx.beginPath()
        ctx.moveTo(x + r, yOffset)
        ctx.lineTo(x + noteW - r, yOffset)
        ctx.quadraticCurveTo(x + noteW, yOffset, x + noteW, yOffset + r)
        ctx.lineTo(x + noteW, yOffset + nh - r)
        ctx.quadraticCurveTo(x + noteW, yOffset + nh, x + noteW - r, yOffset + nh)
        ctx.lineTo(x + r, yOffset + nh)
        ctx.quadraticCurveTo(x, yOffset + nh, x, yOffset + nh - r)
        ctx.lineTo(x, yOffset + r)
        ctx.quadraticCurveTo(x, yOffset, x + r, yOffset)
        ctx.closePath()
        ctx.fillStyle = grad
        ctx.fill()

        // Bright top edge highlight
        ctx.shadowBlur = 0
        ctx.strokeStyle = 'rgba(180, 255, 220, 0.8)'
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(x + r, yOffset + 0.5)
        ctx.lineTo(x + noteW - r, yOffset + 0.5)
        ctx.stroke()
      }
    } else {
      const duration = note.end - note.start
      const lifeTime = duration + 0.6
      const age = now - note.start

      if (age >= lifeTime) {
        rtVisualizerNotes.splice(i, 1)
        continue
      }

      if (enableAiAnimation.value && age >= 0 && age < lifeTime) {
        const pitchClass = note.midi % 12
        const octave = Math.floor(note.midi / 12) - 1
        const col = pitchClassToCol[pitchClass]
        const row = Math.max(0, Math.min(4, octave - 2))

        const cellW = w / 7
        const cellH = h / 5
        const baseX = col * cellW + cellW / 2
        const baseY = h - (row * cellH + cellH / 2)

        const offsetX = Math.sin(note.start * 1234.56) * (cellW * 0.3)
        const offsetY = Math.cos(note.start * 7890.12) * (cellH * 0.3)
        const centerX = baseX + offsetX
        const centerY = baseY + offsetY

        const progress = age / lifeTime
        const maxRadius = Math.max(cellW, cellH) * (0.6 + duration * 0.4)
        const currentRadius = progress * maxRadius
        const alpha = 1 - Math.pow(progress, 1.5)

        // Outer glow ring
        ctxAi.shadowBlur = 20
        ctxAi.shadowColor = `rgba(143, 148, 251, ${alpha * 0.6})`
        ctxAi.beginPath()
        ctxAi.arc(centerX, centerY, currentRadius, 0, Math.PI * 2)
        ctxAi.strokeStyle = `rgba(180, 185, 255, ${alpha * 0.9})`
        ctxAi.lineWidth = 2.5 + (1 - progress) * 3
        ctxAi.stroke()
        ctxAi.shadowBlur = 0

        // Second ring (slightly delayed)
        if (progress > 0.08) {
          const ring2R = Math.max(0, (progress - 0.08) * maxRadius)
          ctxAi.beginPath()
          ctxAi.arc(centerX, centerY, ring2R, 0, Math.PI * 2)
          ctxAi.strokeStyle = `rgba(120, 130, 255, ${alpha * 0.55})`
          ctxAi.lineWidth = 1.5 + (1 - progress) * 2
          ctxAi.stroke()
        }

        // Third inner ring
        if (progress > 0.22) {
          const ring3R = Math.max(0, (progress - 0.22) * maxRadius)
          ctxAi.beginPath()
          ctxAi.arc(centerX, centerY, ring3R, 0, Math.PI * 2)
          ctxAi.strokeStyle = `rgba(200, 200, 255, ${alpha * 0.25})`
          ctxAi.lineWidth = 1
          ctxAi.stroke()
        }

        // Soft center dot at birth
        if (progress < 0.25) {
          const dotAlpha = (1 - progress / 0.25) * alpha
          const radGrad = ctxAi.createRadialGradient(centerX, centerY, 0, centerX, centerY, 18)
          radGrad.addColorStop(0, `rgba(220, 220, 255, ${dotAlpha * 0.8})`)
          radGrad.addColorStop(1, `rgba(143, 148, 251, 0)`)
          ctxAi.beginPath()
          ctxAi.arc(centerX, centerY, 18, 0, Math.PI * 2)
          ctxAi.fillStyle = radGrad
          ctxAi.fill()
        }
      }
    }
  }

  if (enableUserAnimation.value) {
    currentlyPlayingNotes.forEach((val) => {
      const yOffset = h - (now - val.startTime) * pps
      const nh = (now - val.startTime) * pps
      const xOffset = getPianoKeyX(val.midi)
      const kw = getVisualizerKeyWidth(val.midi)
      const x = xOffset + 1
      const noteW = kw - 2
      const r = Math.min(4, noteW / 2)

      const grad = ctx.createLinearGradient(x, yOffset, x + noteW, yOffset + nh)
      grad.addColorStop(0, 'rgba(160, 255, 210, 0.98)')
      grad.addColorStop(0.4, 'rgba(95, 227, 161, 0.92)')
      grad.addColorStop(1, 'rgba(40, 170, 120, 0.75)')

      ctx.shadowBlur = 22
      ctx.shadowColor = 'rgba(95, 227, 161, 0.85)'

      ctx.beginPath()
      ctx.moveTo(x + r, yOffset)
      ctx.lineTo(x + noteW - r, yOffset)
      ctx.quadraticCurveTo(x + noteW, yOffset, x + noteW, yOffset + r)
      ctx.lineTo(x + noteW, yOffset + nh)
      ctx.lineTo(x, yOffset + nh)
      ctx.lineTo(x, yOffset + r)
      ctx.quadraticCurveTo(x, yOffset, x + r, yOffset)
      ctx.closePath()
      ctx.fillStyle = grad
      ctx.fill()
      ctx.shadowBlur = 0
    })
  }
}

const handleKeyDown = (e) => {
  if (!isRealtimePlaying.value) return
  const code = keyAliases[e.code] || e.code
  const key = pianoKeys.find((k) => k.keyCode === code)
  if (key) triggerKeyStart(key)
}

const handleKeyUp = (e) => {
  if (!isRealtimePlaying.value) return
  const code = keyAliases[e.code] || e.code
  const key = pianoKeys.find((k) => k.keyCode === code)
  if (key) triggerKeyEnd(key)
}

const rtHandleMouseDown = (key) => {
  if (isRealtimePlaying.value) triggerKeyStart(key)
}
const rtHandleMouseUp = (key) => {
  if (isRealtimePlaying.value) triggerKeyEnd(key)
}

const playMetronomeClick = (time, beatIndex = 0) => {
  if (muteMetronome.value) return
  if (metronomeStyle.value === 'beep') {
    const pitch = beatIndex === 0 ? 'G5' : 'C5'
    audioService.metronome.triggerAttackRelease(pitch, '64n', time)
  } else {
    // 每一拍都有鈸 (Hi-Hat) 作為底
    audioService.hatSynth.triggerAttackRelease('16n', time)

    // 第 1 拍大鼓，第 3 拍小鼓
    if (beatIndex === 0) {
      audioService.kickSynth.triggerAttackRelease('A1', '8n', time)
    } else if (beatIndex === 2) {
      audioService.snareSynth.triggerAttackRelease('B1', '8n', time)
    }
  }
}

const generateAccompaniment = async (melodyNotes, accompNotes) => {
  try {
    // 🌟 第一小節注入邏輯：如果是 Bar 0，且選定了風格，將靜態資料併入伴奏容器
    if (currentBar.value === 0 && selectedBaseStyle.value) {
      const styleData = BASE_STYLES[selectedBaseStyle.value] || []
      const secPerTick = 60 / realtimeBPM.value / 4

      styleData.forEach((s) => {
        accompNotes.push({
          midi: s.midi,
          time: s.pos * secPerTick,
          duration: s.dur * secPerTick,
        })
      })
      console.log(`🎹 Bar 0 Style Injected: ${selectedBaseStyle.value} (${styleData.length} notes)`)
    }

    const inputTokens = tokenizerService.encodeBar(melodyNotes, accompNotes, realtimeBPM.value)

    // 將滑桿值換算為推論參數
    const options = {
      temperature: aiCreativity.value / 100,
      topP: 0.5 + (aiComplexity.value / 100) * 0.5, // 80% -> 0.9
    }

    const generatedTokenIds = await aiService.generateNextBar(inputTokens, options)
    return tokenizerService.decodeAccompaniment(generatedTokenIds, realtimeBPM.value)
  } catch (error) {
    return []
  }
}

const playAccompaniment = (accompaniment, startTime) => {
  const safeAccompaniment = accompaniment.filter(
    (n) => n && n.midi !== undefined && n.midi !== null && !isNaN(n.midi),
  )

  const beatDur = getBeatDuration() // 取得一拍的秒數

  safeAccompaniment.forEach((note) => {
    const noteName = Tone.Frequency(note.midi, 'midi').toNote()
    const scheduleTime = startTime + note.time

    if (barCount >= -1) {
      const step = Math.round(((barCount + 1) * 4 + note.time / beatDur) * 2)
      const stepDur = Math.max(1, Math.round(note.duration / (beatDur / 2)))

      realtimeRecordedAI.push({
        pitch: note.midi,
        step: step,
        duration: stepDur,
        exactTime: (barCount + 1) * getBarDuration() + note.time,
        exactDuration: note.duration,
        velocity: 0.7,
      })

      if (enableAiAnimation.value) {
        rtVisualizerNotes.push({
          midi: note.midi,
          start: scheduleTime,
          end: scheduleTime + note.duration,
          isAi: true,
        })
      }
    }
    if (!muteAi.value) {
      audioService.accSynth.triggerAttackRelease(noteName, note.duration, scheduleTime, 0.8)
    }
  })
}

const startRealtime = async () => {
  if (!isCalibrated.value) {
    showCalibrationModal.value = true
    runCalibration()
    return
  }

  await initToneJs()

  Tone.Transport.stop()
  Tone.Transport.cancel()
  Tone.Transport.seconds = 0
  Tone.Transport.bpm.value = realtimeBPM.value
  Tone.Transport.timeSignature = 4
  isRealtimePlaying.value = true
  barCount = -1
  generationHistory.value = []
  currentBarNotes.value = []
  previousAccompaniment = []
  realtimeRecordedNotes = []
  realtimeRecordedAI = []
  rtVisualizerNotes = []

  if (!rtVisualizerFrameId) rtVisualizerFrameId = requestAnimationFrame(drawRealtimeVisualizer)
  realtimeStatus.value = 'Pre-roll... Get Ready!'
  const beatDuration = getBeatDuration()

  schedulerId = Tone.Transport.scheduleRepeat(
    (time) => {
      barCount++
      currentBar.value = barCount
      if (barCount >= 100) {
        Tone.Draw.schedule(() => stopRealtime(), time)
        return
      }

      currentBarNotes.value = []
      recordingStartTime = time
      Tone.Draw.schedule(() => {
        realtimeStatus.value =
          barCount === 0 ? 'Play Melody (Recording...)' : 'Realtime Engine Active...'
        renderRealtimeStaff()
      }, time)

      for (let i = 0; i < 4; i++) {
        const beatTime = time + i * beatDuration
        playMetronomeClick(beatTime, i)
        Tone.Draw.schedule(() => {
          currentBeat.value = i + 1
          beatPulse.value = true
          setTimeout(() => {
            beatPulse.value = false
          }, 100)
        }, beatTime)
      }
    },
    '1m',
    '0:0:0',
  )

  aiSchedulerId = Tone.Transport.scheduleRepeat(
    (time) => {
      if (barCount < 0) return
      const nextBarStartTime = time + 0.5 * beatDuration
      const melodySnapshot = [...currentBarNotes.value]
      currentlyPlayingNotes.forEach((noteInfo) => {
        const timeOffset = noteInfo.startTime - recordingStartTime
        if (timeOffset >= 0 && timeOffset < 3.5 * beatDuration) {
          melodySnapshot.push({
            midi: noteInfo.midi,
            time: timeOffset,
            duration: time - noteInfo.startTime,
          })
        }
      })
      const prevAccSnapshot = [...previousAccompaniment]
      generateAccompaniment(melodySnapshot, prevAccSnapshot).then(async (acc) => {
        previousAccompaniment = acc
        playAccompaniment(acc, nextBarStartTime)
        Tone.Draw.schedule(() => {
          generationHistory.value.push({
            bar: barCount + 1,
            message: `生成 ${acc.length} 個伴奏音符`,
          })
          renderRealtimeStaff()
        }, nextBarStartTime)
      })
    },
    '1m',
    '0:3:2',
  )

  Tone.Transport.start()
}

const stopRealtime = () => {
  isRealtimePlaying.value = false
  realtimeStatus.value = 'Engine Stopped'
  audioService.stopAll()
  currentlyPlayingNotes.clear()
  activeKeys.value.clear()

  if (schedulerId !== null) {
    Tone.Transport.clear(schedulerId)
    schedulerId = null
  }
  if (aiSchedulerId !== null) {
    Tone.Transport.clear(aiSchedulerId)
    aiSchedulerId = null
  }
  if (rtVisualizerFrameId !== null) {
    cancelAnimationFrame(rtVisualizerFrameId)
    rtVisualizerFrameId = null
  }
}

const downloadRealtimeMidi = () => {
  if (realtimeRecordedNotes.length === 0 && realtimeRecordedAI.length === 0) return
  const originalMidi = new Midi()
  originalMidi.header.setTempo(realtimeBPM.value)
  const melodyTrack = originalMidi.addTrack()
  melodyTrack.instrument.name = 'acoustic grand piano'
  realtimeRecordedNotes.forEach((n) => {
    melodyTrack.addNote({
      midi: n.pitch,
      time: n.exactTime,
      duration: n.exactDuration,
      velocity: n.velocity || 0.8,
    })
  })
  if (realtimeRecordedAI.length > 0) {
    const aiTrack = originalMidi.addTrack()
    aiTrack.instrument.name = 'acoustic grand piano'
    realtimeRecordedAI.forEach((n) => {
      aiTrack.addNote({
        midi: n.pitch,
        time: n.exactTime,
        duration: n.exactDuration,
        velocity: n.velocity || 0.7,
      })
    })
  }
  const blob = new Blob([originalMidi.toArray()], { type: 'audio/midi' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `realtime_performance_${new Date().getTime()}.mid`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const getPitchName = (pitch) => {
  const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
  return `${names[pitch % 12]}${Math.floor(pitch / 12) - 1}`
}

// 性能檢測實作
const runCalibration = async () => {
  isCalibrating.value = true
  calibrationProgress.value = 0
  await initToneJs()

  const warmupStr =
    'BOS_None | Bar_None | Position_0 | Program_0 | Pitch_72 | Velocity_79 | Duration_1.0.4 | Program_1 | Pitch_41 | Velocity_79 | Duration_0.2.4 | Position_2 | Program_1 | Pitch_48 | Velocity_79 | Duration_0.2.4 | Position_4 | Program_0 | Pitch_69 | Velocity_79 | Duration_0.2.4 | Program_1 | Pitch_53 | Velocity_79 | Duration_0.2.4 | Position_6 | Program_0 | Pitch_72 | Velocity_79 | Duration_1.0.4 | Program_1 | Pitch_57 | Velocity_79 | Duration_1.0.4 | Position_10 | Program_0 | Pitch_76 | Velocity_79 | Duration_1.0.4 | Program_1 | Pitch_53 | Velocity_79 | Duration_0.2.4 | Position_12 | Program_1 | Pitch_48 | Velocity_79 | Duration_0.2.4 | Position_14 | Program_0 | Pitch_76 | Velocity_79 | Duration_0.2.4 | Program_1 | Pitch_45 | Velocity_79 | Duration_0.2.4 | EOS_None'
  const warmupTokens = warmupStr.split(' | ').map((t) => tokenizerService.vocab[t] || 0)

  for (let w = 0; w < 3; w++) {
    await aiService.generateNextBar(warmupTokens)
    await new Promise((r) => setTimeout(r, 100))
  }

  const results = []
  let prevAccompanimentNotes = []

  for (let i = 0; i < 50; i++) {
    await new Promise((r) => setTimeout(r, 100))
    const noteCount = 4 + Math.floor(Math.random() * 5)
    const randomMelody = []
    for (let j = 0; j < noteCount; j++) {
      randomMelody.push({
        midi: 48 + Math.floor(Math.random() * 29),
        time: Math.random() * 3.5 * (60 / realtimeBPM.value),
        duration: 0.1 + Math.random() * 0.5,
      })
    }
    const inputTokens = tokenizerService.encodeBar(
      randomMelody,
      prevAccompanimentNotes,
      realtimeBPM.value,
    )
    const t0 = performance.now()
    const generatedTokenIds = await aiService.generateNextBar(inputTokens)
    const t1 = performance.now()
    prevAccompanimentNotes = tokenizerService.decodeAccompaniment(
      generatedTokenIds,
      realtimeBPM.value,
    )
    results.push(t1 - t0)
    calibrationProgress.value = ((i + 1) / 50) * 100
  }

  const avg = results.reduce((a, b) => a + b) / results.length
  const std = Math.sqrt(
    results.map((x) => Math.pow(x - avg, 2)).reduce((a, b) => a + b) / results.length,
  )

  const safeLimitSec = (avg + 3 * std) / 1000
  const disableAnimSec = (avg + 2 * std) / 1000
  const safeBPM = Math.floor(30 / safeLimitSec)
  const animBPM = Math.floor(30 / disableAnimSec)

  safeBPMWithAnim.value = Math.min(100, safeBPM)
  absoluteMaxBPM.value = Math.min(100, animBPM)

  calibrationSummary.value = {
    avg,
    std,
    autoDisabledAnim: realtimeBPM.value > safeBPM,
    // safeBPMWithAnim 最大被夾在 100，原閾值 240 對所有設備永遠為 true
    // 改為 80（= absoluteMaxBPM 上限的 80%）才有實際壞效能警告意義
    lowSafeBPM: safeBPM < 80,
  }

  if (realtimeBPM.value > absoluteMaxBPM.value) {
    realtimeBPM.value = absoluteMaxBPM.value
    enableUserAnimation.value = false
    enableAiAnimation.value = false
  } else if (realtimeBPM.value > safeBPMWithAnim.value) {
    enableUserAnimation.value = false
    enableAiAnimation.value = false
  } else {
    enableUserAnimation.value = true
    enableAiAnimation.value = true
  }
  isCalibrating.value = false
}

const currentMaxBPM = computed(() => {
  return modalAnimationState.value ? safeBPMWithAnim.value : absoluteMaxBPM.value
})

const confirmAndStart = () => {
  showCalibrationModal.value = false
  isCalibrated.value = true
  startRealtime()
}

// 分開控制邏輯
const toggleUserAnimation = () => {
  enableUserAnimation.value = !enableUserAnimation.value
  if (!enableUserAnimation.value) {
    // 立即清空使用者音符動畫資料
    for (let i = rtVisualizerNotes.length - 1; i >= 0; i--) {
      if (!rtVisualizerNotes[i].isAi) rtVisualizerNotes.splice(i, 1)
    }
  }
  if (realtimeBPM.value > currentMaxBPM.value) realtimeBPM.value = currentMaxBPM.value
}
const toggleAiAnimation = () => {
  enableAiAnimation.value = !enableAiAnimation.value
  if (!enableAiAnimation.value) {
    // 立即清空 AI 音符動畫資料
    for (let i = rtVisualizerNotes.length - 1; i >= 0; i--) {
      if (rtVisualizerNotes[i].isAi) rtVisualizerNotes.splice(i, 1)
    }
  }
  if (realtimeBPM.value > currentMaxBPM.value) realtimeBPM.value = currentMaxBPM.value
}

// Modal 統一開關邏輯
const toggleAnimationInModal = () => {
  const targetState = !modalAnimationState.value
  enableUserAnimation.value = targetState
  enableAiAnimation.value = targetState
  if (realtimeBPM.value > currentMaxBPM.value) {
    realtimeBPM.value = currentMaxBPM.value
  }
}

// 動態五線譜狀態與邏輯 ---
const rtVexflowContainer = ref(null)

// 建立安全、防錯的 Measure 產生器
const buildSafeMeasure = (sourceNotes, barIndex, clefType, isAI = false) => {
  const startStep = barIndex * 8
  const endStep = startStep + 8
  const measureNotes = []
  let currentStep = startStep

  while (currentStep < endStep) {
    const notesAtStep = sourceNotes.filter((n) => n.step === currentStep)

    if (notesAtStep.length > 0) {
      // 🌟 視覺截斷優化：偵測小節內下一個音符起點，防止時值溢出遮擋
      const nextNote = sourceNotes.find((n) => n.step > currentStep && n.step < endStep)
      const maxAllowed = nextNote ? nextNote.step - currentStep : endStep - currentStep
      let dur = Math.min(notesAtStep[0].duration || 1, maxAllowed)

      const validDurs = [8, 6, 4, 3, 2, 1]
      dur = validDurs.find((d) => d <= dur) || 1

      let durStr = { 1: '8', 2: 'q', 3: 'qd', 4: 'h', 6: 'hd', 8: 'w' }[dur]
      const keys = []
      const accs = []

      notesAtStep.forEach((n) => {
        const noteName = Tone.Frequency(n.pitch, 'midi').toNote()
        let letter = noteName.charAt(0).toLowerCase()
        let acc = noteName.includes('#') ? '#' : noteName.includes('b') ? 'b' : ''
        let oct = noteName.slice(-1)

        let keyStr = `${letter}/${oct}`
        if (!keys.includes(keyStr)) {
          keys.push(keyStr)
          accs.push(acc)
        }
      })

      if (keys.length === 0) keys.push(clefType === 'treble' ? 'b/4' : 'd/3')

      const sn = new StaveNote({ clef: clefType, keys, duration: durStr })
      accs.forEach((a, i) => {
        if (a) sn.addModifier(new Accidental(a), i)
      })
      if (durStr.includes('d')) sn.addModifier(new Dot(0), 0)

      // 💡 顏色區分：使用者為綠色，AI為紫色
      if (!isAI) {
        sn.setStyle({ fillStyle: '#5fe3a1', strokeStyle: '#5fe3a1' })
      } else {
        sn.setStyle({ fillStyle: '#8f94fb', strokeStyle: '#8f94fb' })
      }

      measureNotes.push(sn)
      currentStep += dur
    } else {
      let restDur = 1
      let rStr = '8r'
      if (
        currentStep % 2 === 0 &&
        !sourceNotes.find((n) => n.step === currentStep + 1) &&
        currentStep + 1 < endStep
      ) {
        restDur = 2
        rStr = 'qr'
      }
      const defaultKey = clefType === 'treble' ? 'b/4' : 'd/3'
      const rest = new StaveNote({ clef: clefType, keys: [defaultKey], duration: rStr })

      // 💡 將 AI 的休止符設為透明，避免畫面雜亂；使用者的休止符用半透明白色
      if (isAI) {
        rest.setStyle({ fillStyle: 'rgba(0,0,0,0)', strokeStyle: 'rgba(0,0,0,0)' })
      } else {
        rest.setStyle({
          fillStyle: 'rgba(210, 210, 230, 0.3)',
          strokeStyle: 'rgba(210, 210, 230, 0.3)',
        })
      }

      measureNotes.push(rest)
      currentStep += restDur
    }
  }
  return measureNotes
}

const renderRealtimeStaff = () => {
  if (!rtVexflowContainer.value) return

  const container = rtVexflowContainer.value
  container.innerHTML = ''

  const numBars = visibleBarCount.value
  const endBar = Math.max(numBars - 1, currentBar.value)
  const startBar = endBar - (numBars - 1)

  const MEASURE_WIDTH = 280
  const CLEF_WIDTH = 110
  const TREBLE_Y = -10
  const BASS_Y = 75

  const renderer = new Renderer(container, Renderer.Backends.SVG)
  renderer.resize(CLEF_WIDTH + numBars * MEASURE_WIDTH + 10, 170)
  const ctx = renderer.getContext()

  // 🎨 設定五線譜顏色：譜線、譜號、拍號用柔和的白色
  ctx.setStrokeStyle('rgba(210, 210, 230, 0.75)')
  ctx.setFillStyle('rgba(210, 210, 230, 0.75)')
  ctx.setLineWidth(1.1)

  // 🌟 優化：x 從 0 改為 25，寬度從 80 改為 85 (25+85=110)
  const trebleClef = new Stave(25, TREBLE_Y, 85)
    .addClef('treble')
    .addTimeSignature('4/4')
    .setContext(ctx)
  const bassClef = new Stave(25, BASS_Y, 85).addClef('bass').addTimeSignature('4/4').setContext(ctx)

  // 🌟 同步拍號起點
  const startX = Math.max(trebleClef.getNoteStartX(), bassClef.getNoteStartX())
  trebleClef.setNoteStartX(startX)
  bassClef.setNoteStartX(startX)

  // 隱藏末端直線，使與第一個小節完美衔接
  trebleClef.setEndBarType(Barline.type.NONE)
  bassClef.setEndBarType(Barline.type.NONE)

  trebleClef.draw()
  bassClef.draw()

  ctx.setStrokeStyle('rgba(210, 210, 230, 0.75)')
  ctx.setFillStyle('rgba(210, 210, 230, 0.75)')
  new StaveConnector(trebleClef, bassClef).setType(StaveConnector.type.BRACE).setContext(ctx).draw()
  new StaveConnector(trebleClef, bassClef)
    .setType(StaveConnector.type.SINGLE_LEFT)
    .setContext(ctx)
    .draw()

  // 💡 移除即時音符，只拿已經完整記錄的陣列
  const fullMelody = [...realtimeRecordedNotes]
  // 🌟 需求優化：伴奏一律導向低音譜，不依據 C4 劃分
  const aiTreble = []
  const aiBass = [...realtimeRecordedAI]

  for (let i = 0; i < numBars; i++) {
    const barIndex = startBar + i
    const offsetX = CLEF_WIDTH + i * MEASURE_WIDTH

    // 每個小節維持相同顏色設定
    ctx.setStrokeStyle('rgba(210, 210, 230, 0.75)')
    ctx.setFillStyle('rgba(210, 210, 230, 0.75)')
    const tStave = new Stave(offsetX, TREBLE_Y, MEASURE_WIDTH).setContext(ctx)
    const bStave = new Stave(offsetX, BASS_Y, MEASURE_WIDTH).setContext(ctx)

    // 🌟 同步小節起點
    const sX = Math.max(tStave.getNoteStartX(), bStave.getNoteStartX())
    tStave.setNoteStartX(sX)
    bStave.setNoteStartX(sX)

    // 🌟 第一小節隱藏左面直線，與譜號區域對接
    if (i === 0) {
      tStave.setBegBarType(Barline.type.NONE)
      bStave.setBegBarType(Barline.type.NONE)
    }

    tStave.draw()
    bStave.draw()

    // 💡 核心判斷：這個小節結束了嗎？
    const isCompleted = barIndex < currentBar.value

    let tNotesUser = buildSafeMeasure(isCompleted ? fullMelody : [], barIndex, 'treble', false)
    const bNotesAI = buildSafeMeasure(isCompleted ? aiBass : [], barIndex, 'bass', true)

    const tVoiceUser = new Voice({ num_beats: 4, beat_value: 4 })
      .setStrict(false)
      .addTickables(tNotesUser)
    const bVoiceAI = new Voice({ num_beats: 4, beat_value: 4 })
      .setStrict(false)
      .addTickables(bNotesAI)

    const voicesToFormat = [tVoiceUser, bVoiceAI]

    // 直接使用共享格式化，不使用 joinVoices 以修復 8px 位移
    const formatter = new Formatter()
    tVoiceUser.setStave(tStave)
    bVoiceAI.setStave(bStave)

    formatter.format(voicesToFormat, MEASURE_WIDTH - 40, { align_rests: true })

    tVoiceUser.draw(ctx, tStave)
    bVoiceAI.draw(ctx, bStave)

    ctx.setStrokeStyle('rgba(210, 210, 230, 0.75)')
    ctx.setFillStyle('rgba(210, 210, 230, 0.75)')
    new StaveConnector(tStave, bStave)
      .setType(StaveConnector.type.SINGLE_RIGHT)
      .setContext(ctx)
      .draw()
  }
}

const initStaffLayout = () => {
  const w = window.innerWidth
  let initCount = 4
  if (w < 1130) initCount = 2
  else if (w < 1545) initCount = 2
  else if (w < 1700) initCount = 3

  visibleBarCount.value = initCount
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('keyup', handleKeyUp)

  // 🌟 核心優化：僅在挂載時執行唯一的寬度偵測與小節數判定
  initStaffLayout()
  renderRealtimeStaff()
})
onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('keyup', handleKeyUp)
  if (isRealtimePlaying.value) stopRealtime()
  audioService.stopAll()
})
</script>

<style scoped>
/* ── 全域 CSS 變數 ─────────────────── */
.immersive-layout,
.modal-overlay {
  --rt-bg-deep: #09090f;
  --rt-bg-panel: rgba(13, 13, 22, 0.82);
  --rt-border: rgba(255, 255, 255, 0.07);
  --rt-border-accent: rgba(143, 148, 251, 0.25);
  --rt-accent: #8f94fb;
  --rt-accent-green: #5fe3a1;
  --rt-accent-green-dim: rgba(95, 227, 161, 0.15);
  --rt-text-primary: rgba(240, 240, 255, 0.92);
  --rt-text-secondary: rgba(180, 180, 210, 0.65);
  --rt-text-muted: rgba(120, 120, 160, 0.55);
  --rt-radius: 14px;
  --rt-radius-sm: 8px;
}

/* ── 沉浸式整體佈局 ─────────────────── */
.immersive-layout {
  display: flex;
  height: calc(100vh - 100px);
  min-height: 700px;
  gap: 16px;
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  overflow: hidden;
}

/* ── 左側邊欄 ─────────────────── */
.sidebar {
  flex: 0 0 310px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  height: auto;
  max-height: 100%;
  margin-bottom: 5px;
  scrollbar-width: thin;
  scrollbar-color: rgba(143, 148, 251, 0.2) transparent;
}
.sidebar::-webkit-scrollbar {
  width: 4px;
}
.sidebar::-webkit-scrollbar-track {
  background: transparent;
}
.sidebar::-webkit-scrollbar-thumb {
  background: rgba(143, 148, 251, 0.25);
  border-radius: 2px;
}

/* ── 右側主舞台 ─────────────────── */
.main-stage {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: linear-gradient(160deg, rgba(12, 12, 20, 0.97) 0%, rgba(8, 8, 16, 1) 100%);
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  overflow: hidden;
  position: relative;
  align-items: center;
  box-shadow:
    0 0 80px rgba(0, 0, 0, 0.7),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

/* ── 核心：對齊校準容器 ─────────────────── */
.stage-inner-wrapper {
  width: 100%;
  display: flex;
  flex-direction: column;
  margin: 0 auto;
  position: relative;
  flex: 1;
}

/* ── Glass Panel (左側使用) ─────────────────── */
.glass-panel {
  background: rgba(13, 13, 22, 0.82);
  backdrop-filter: blur(24px) saturate(180%);
  -webkit-backdrop-filter: blur(24px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 14px;
  padding: 18px;
  box-shadow:
    0 4px 32px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

/* ── 控制區域段落 ─────────────────── */
.control-section {
  background: rgba(255, 255, 255, 0.022);
  border-radius: 10px;
  padding: 12px 14px 14px;
  margin-bottom: 12px;
  border: 1px solid rgba(255, 255, 255, 0.045);
  transition: border-color 0.2s;
}
.control-section:hover {
  border-color: rgba(143, 148, 251, 0.12);
}
.control-row-simple {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.small-label {
  font-size: 10.5px;
  font-weight: 700;
  color: rgba(120, 120, 160, 0.55);
  text-transform: uppercase;
  letter-spacing: 0.8px;
}
.mb-15 {
  margin-bottom: 15px;
}
.section-title {
  margin: 0 0 12px;
  color: #8f94fb;
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  font-weight: 700;
  border-bottom: 1px solid rgba(143, 148, 251, 0.12);
  padding-bottom: 7px;
  opacity: 0.85;
}

/* ── 表單與控制件 ─────────────────── */
.control-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}
.control-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}
.control-group label {
  color: rgba(180, 180, 210, 0.65);
  font-size: 11.5px;
  letter-spacing: 0.2px;
}
.modern-input,
.modern-select {
  width: 100%;
  padding: 8px 8px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.45);
  color: rgba(240, 240, 255, 0.92);
  font-size: 13px;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
  outline: none;
  box-sizing: border-box;
  min-width: 0;
}
.modern-input:focus,
.modern-select:focus {
  border-color: rgba(143, 148, 251, 0.45);
  box-shadow: 0 0 0 3px rgba(143, 148, 251, 0.08);
}
.modern-select option {
  background: #1a1a2e;
}

/* ── Mixer 控制區 ─────────────────── */
.mixer-row {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-bottom: 13px;
}
.mixer-row:last-child {
  margin-bottom: 0;
}
.mixer-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.mixer-info label {
  color: rgba(240, 240, 255, 0.92);
  font-size: 12.5px;
  opacity: 0.85;
}
.mute-toggle {
  display: flex;
  align-items: center;
  gap: 5px;
}
.mute-toggle input[type='checkbox'] {
  accent-color: #8f94fb;
  width: 12px;
  height: 12px;
}
.mute-toggle label {
  font-size: 10.5px;
  color: rgba(120, 120, 160, 0.55);
  cursor: pointer;
  letter-spacing: 0.3px;
}
.volume-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 3px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  outline: none;
  cursor: pointer;
}
.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: #8f94fb;
  cursor: pointer;
  transition:
    transform 0.15s,
    box-shadow 0.15s;
  box-shadow: 0 0 6px rgba(143, 148, 251, 0.5);
}
.volume-slider::-webkit-slider-thumb:hover {
  transform: scale(1.25);
  box-shadow: 0 0 12px rgba(143, 148, 251, 0.8);
}
.volume-slider:disabled::-webkit-slider-thumb {
  background: rgba(255, 255, 255, 0.2);
  box-shadow: none;
}

/* ── 動畫開關區 ─────────────────── */
.anim-switches {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.switch-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.switch-row label {
  color: rgba(180, 180, 210, 0.65);
  font-size: 12.5px;
  cursor: pointer;
}

/* ── 狀態面板 ─────────────────── */
.status-row {
  display: flex;
  justify-content: space-between;
}
.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.status-item .label {
  font-size: 11px;
  opacity: 0.8;
  text-transform: uppercase;
}
.status-item .value {
  font-size: 20px;
  font-weight: 900;
  color: #fff;
}
.status-text {
  color: #f1c40f !important;
  text-shadow: 0 0 10px rgba(241, 196, 15, 0.5);
  font-size: 16px !important;
  text-align: center;
}
.beat-indicator {
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 15px;
  border-radius: 15px;
  transition: 0.1s;
}
.beat-indicator.pulse {
  transform: scale(1.1);
  background: white;
}
.beat-indicator.pulse .value {
  color: #4e54c8;
}
.value-label {
  font-size: 11px;
  color: #8f94fb;
  font-weight: 700;
  opacity: 0.9;
}
.accent-purple::-webkit-slider-thumb {
  background: #8f94fb !important;
  box-shadow: 0 0 6px rgba(143, 148, 251, 0.5) !important;
}
.accent-blue::-webkit-slider-thumb {
  background: #8f94fb !important;
  box-shadow: 0 0 6px rgba(143, 148, 251, 0.5) !important;
}

/* ── 動作按鈕 ─────────────────── */
.w-100 {
  width: 100%;
}
.modern-btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition:
    transform 0.15s,
    box-shadow 0.2s,
    filter 0.15s;
  letter-spacing: 0.3px;
}
.modern-btn:hover {
  transform: translateY(-1px);
  filter: brightness(1.1);
}
.modern-btn:active {
  transform: translateY(0);
}
.btn-primary {
  background: linear-gradient(135deg, #3d44b0 0%, #6b70e0 50%, #8f94fb 100%);
  color: white;
  box-shadow:
    0 4px 20px rgba(78, 84, 200, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
}
.btn-large {
  padding: 14px 28px;
  font-size: 15.5px;
  border-radius: 10px;
}
.btn-danger {
  background: linear-gradient(135deg, #c0392b, #e74c3c);
  color: white;
  box-shadow: 0 4px 16px rgba(231, 76, 60, 0.35);
}
.btn-outline {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: rgba(240, 240, 255, 0.92);
}
.btn-outline:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.25);
}

/* ── 主舞台 Canvas 區域 ─────────────────── */
.canvas-container {
  height: 400px;
  position: relative;
  width: 100%;
  /* Layered dark gradient for depth */
  background:
    radial-gradient(ellipse at 20% 80%, rgba(95, 227, 161, 0.03) 0%, transparent 55%),
    radial-gradient(ellipse at 80% 20%, rgba(143, 148, 251, 0.04) 0%, transparent 50%),
    linear-gradient(180deg, #07070e 0%, #0e0e1a 60%, #131320 100%);
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: flex-end;
  overflow: hidden;
}
.stage-canvas {
  position: absolute;
  width: 1320px;
  height: 430px;
  pointer-events: none;
}

/* ── 主舞台 鍵盤 ─────────────────── */
.stage-keyboard {
  background: linear-gradient(180deg, rgba(5, 5, 12, 0.95) 0%, rgba(10, 10, 18, 0.98) 100%);
  padding: 16px 0;
  border-top: 1px solid rgba(143, 148, 251, 0.08);
  border-bottom: 1px solid rgba(0, 0, 0, 0.5);
  z-index: 10;
  box-shadow: 0 -8px 30px rgba(0, 0, 0, 0.4);
}
.modern-keyboard {
  display: flex;
  position: relative;
  justify-content: center;
  overflow-x: auto;
}
.piano-key {
  position: relative;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  padding-bottom: 10px;
  user-select: none;
  transition:
    transform 0.08s,
    box-shadow 0.1s,
    background 0.08s;
}
.piano-key.white-key {
  width: 39px;
  height: 160px;
  background: linear-gradient(180deg, #e8e8e8 0%, #f5f5f5 30%, #ffffff 70%, #e0e0e0 100%);
  border: 1px solid #888;
  border-top: none;
  margin-right: 0;
  flex-shrink: 0;
  border-radius: 0 0 6px 6px;
  box-shadow:
    0 4px 8px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    inset -1px 0 0 rgba(0, 0, 0, 0.08);
}
.piano-key.white-key:hover {
  background: linear-gradient(180deg, #e0e8ff 0%, #eef0ff 40%, #f8f8ff 100%);
  box-shadow:
    0 4px 14px rgba(143, 148, 251, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}
.piano-key.white-key.active {
  background: linear-gradient(180deg, #7a80e8 0%, #9da2f9 40%, #b5b9fd 100%);
  color: white;
  transform: translateY(2px);
  box-shadow:
    0 2px 4px rgba(0, 0, 0, 0.4),
    0 0 20px rgba(143, 148, 251, 0.45),
    inset 0 -1px 0 rgba(255, 255, 255, 0.2);
}
.piano-key.black-key {
  width: 24px;
  height: 100px;
  background: linear-gradient(180deg, #1a1a1a 0%, #2a2a2a 40%, #111 100%);
  margin-left: -12px;
  margin-right: -12px;
  z-index: 10;
  border-radius: 0 0 5px 5px;
  border: 1px solid #050505;
  border-top: none;
  box-shadow:
    2px 4px 8px rgba(0, 0, 0, 0.8),
    inset 0 1px 0 rgba(255, 255, 255, 0.08),
    inset 1px 0 0 rgba(255, 255, 255, 0.04);
}
.piano-key.black-key:hover {
  background: linear-gradient(180deg, #252535 0%, #30304a 60%, #1a1a28 100%);
}
.piano-key.black-key.active {
  background: linear-gradient(180deg, #4e54c8 0%, #6b70e0 60%, #3d44b0 100%);
  box-shadow:
    1px 3px 5px rgba(0, 0, 0, 0.6),
    0 0 16px rgba(143, 148, 251, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.15);
  transform: translateY(1px);
}
.key-label {
  font-weight: 700;
  font-size: 10px;
  margin-bottom: 2px;
  letter-spacing: -0.3px;
}
.white-key .key-label {
  color: rgba(60, 60, 80, 0.7);
}
.black-key .key-label {
  color: rgba(200, 200, 220, 0.5);
  font-size: 9px;
}
.key-binding {
  font-size: 8.5px;
  padding: 1px 3px;
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.18);
  font-weight: 700;
  white-space: nowrap;
  color: rgba(255, 255, 255, 0.7);
}
.white-key .key-binding {
  color: rgba(80, 80, 120, 0.75);
  background: rgba(0, 0, 0, 0.07);
}

/* ── 主舞台 底部紀錄區 ─────────────────── */
.stage-footer {
  padding: 8px 0 0;
  display: flex;
  gap: 20px;
  align-items: stretch;
  background: rgba(0, 0, 0, 0.15);
}
.glass-container {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  padding: 12px;
  backdrop-filter: blur(8px);
}
.export-container {
  display: flex;
  align-items: center;
  justify-content: center;
}
.export-btn {
  height: 100%;
  padding: 0 30px;
  font-size: 16px;
}

/* ── 動畫開關 Switch ─────────────────── */
.modern-switch {
  width: 38px;
  height: 20px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 20px;
  position: relative;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition:
    background 0.25s,
    box-shadow 0.25s;
}
.modern-switch.active {
  background: linear-gradient(135deg, #5a5fd4, #8f94fb);
  border-color: rgba(143, 148, 251, 0.5);
  box-shadow: 0 0 12px rgba(143, 148, 251, 0.4);
}
.switch-handle {
  width: 14px;
  height: 14px;
  background: white;
  border-radius: 50%;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: left 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
}
.modern-switch.active .switch-handle {
  left: 20px;
}
.modern-switch.small {
  width: 32px;
  height: 16px;
}
.modern-switch.small .switch-handle {
  width: 10px;
  height: 10px;
  top: 2px;
  left: 2px;
}
.modern-switch.small.active .switch-handle {
  left: 18px;
}

/* ── Modal 樣式 ─────────────────── */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(12px) saturate(150%);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.calibrator-card {
  width: 420px;
  text-align: center;
  padding: 40px !important;
  border: 1px solid rgba(143, 148, 251, 0.2) !important;
  box-shadow:
    0 24px 80px rgba(0, 0, 0, 0.7),
    0 0 0 1px rgba(255, 255, 255, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.07) !important;
}
.modal-header h3 {
  margin-bottom: 8px;
  font-size: 1.35rem;
  color: #fff;
  letter-spacing: -0.3px;
}
.modal-header p {
  color: rgba(180, 180, 210, 0.65);
  font-size: 13.5px;
  margin-bottom: 28px;
}
.calibration-loader {
  padding: 20px 0;
}
.progress-bar-container {
  width: 100%;
  height: 4px;
  background: rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 12px;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #3d44b0, #6b70e0, #a0a5ff);
  transition: width 0.3s ease;
  border-radius: 10px;
}
.progress-text {
  font-size: 12px;
  color: #8f94fb;
  font-weight: 600;
  letter-spacing: 0.3px;
}
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}
.stat-box {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 14px;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
}
.stat-label {
  font-size: 10px;
  color: rgba(120, 120, 160, 0.55);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 6px;
}
.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: rgba(240, 240, 255, 0.92);
}
.stat-box.warning .stat-value {
  color: #f1c40f;
}
.result-summary {
  background: rgba(95, 227, 161, 0.07);
  border: 1px solid rgba(95, 227, 161, 0.18);
  padding: 18px;
  border-radius: 12px;
  margin-bottom: 18px;
}
.limit-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.limit-item .label {
  font-size: 13px;
  color: rgba(180, 180, 210, 0.65);
}
.limit-item .value {
  font-weight: 700;
}
.limit-item .value.highlight {
  color: #5fe3a1;
  font-size: 18px;
  text-shadow: 0 0 12px rgba(95, 227, 161, 0.4);
}
.notice-info {
  font-size: 12.5px;
  color: rgba(120, 120, 160, 0.55);
  font-style: italic;
  padding: 0 8px;
}
.flex-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.highlight-warning {
  color: #ffd60a !important;
  font-weight: 600;
  margin-top: 10px;
  background: rgba(255, 214, 10, 0.08);
  border: 1px solid rgba(255, 214, 10, 0.2);
  padding: 8px 12px;
  border-radius: 8px;
}
.btn-full {
  width: 100%;
}
.mt-20 {
  margin-top: 20px;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ── Staff 五線譜面板 ─────────────────── */
.rt-staff-panel {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.02);
}
.rt-vexflow-container {
  width: 100%;
  display: flex;
  justify-content: center;
  transform-origin: center top;
  height: 170px;
  margin-top: -25px;
  overflow: visible;
}
.rt-vexflow-container svg {
  filter: drop-shadow(0px 2px 6px rgba(0, 0, 0, 0.6));
}

/* ── 緊湊版底部佈局 ─────────────────── */
.stage-footer.compact-footer {
  padding: 5px 0 0;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  gap: 0;
  height: auto;
  overflow-x: auto;
  width: 100%;
}
.rt-staff-panel {
  display: flex;
  flex-direction: column;
  padding: 0 15px !important;
  position: relative;
  overflow: visible !important;
  margin: 0 auto;
  width: max-content;
}

/* ── 迷你狀態列 ─────────────────── */
.mini-status-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 5px 12px;
  background: rgba(0, 0, 0, 0.45);
  border-radius: 20px;
  width: max-content;
  font-size: 11.5px;
  color: rgba(180, 180, 210, 0.65);
  margin-bottom: 5px;
  border: 1px solid rgba(255, 255, 255, 0.055);
  backdrop-filter: blur(8px);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}
.mini-status-item {
  display: flex;
  align-items: center;
  gap: 7px;
  font-family: 'Outfit', sans-serif;
}
.mini-status-item strong {
  color: rgba(240, 240, 255, 0.92);
  font-size: 14px;
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #f1c40f;
  box-shadow: 0 0 8px rgba(241, 196, 15, 0.6);
}
.mini-status-item.is-active .status-dot {
  background: #5fe3a1;
  box-shadow: 0 0 10px rgba(95, 227, 161, 0.9);
  animation: pulse-dot 1.5s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%,
  100% {
    box-shadow: 0 0 6px rgba(95, 227, 161, 0.7);
  }
  50% {
    box-shadow: 0 0 14px rgba(95, 227, 161, 1);
  }
}
.mini-status-divider {
  width: 1px;
  height: 12px;
  background: rgba(255, 255, 255, 0.12);
}
.beat-pulse-text {
  color: #8f94fb !important;
  transform: scale(1.2);
  display: inline-block;
  transition: 0.1s ease;
}

/* ── 迷你下載按鈕 ─────────────────── */
.mini-export-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  background: rgba(78, 84, 200, 0.15);
  border: 1px solid rgba(143, 148, 251, 0.3);
  color: #8f94fb;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 10.5px;
  font-weight: 700;
  cursor: pointer;
  transition:
    background 0.2s,
    color 0.2s,
    box-shadow 0.2s;
  letter-spacing: 0.5px;
}
.mini-export-btn:hover:not(:disabled) {
  background: rgba(143, 148, 251, 0.25);
  color: #fff;
  box-shadow: 0 0 12px rgba(143, 148, 251, 0.3);
}
.mini-export-btn:disabled {
  opacity: 0.25;
  cursor: not-allowed;
  filter: grayscale(1);
}
</style>
