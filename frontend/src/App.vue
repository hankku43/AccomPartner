<template>
  <div class="app-wrapper light-theme" :class="{ 'is-loading': isGenerating }">
    <!-- Overlay Loading Animation -->
    <transition name="fade">
      <div v-if="isGenerating" class="global-loading-overlay">
        <div class="futuristic-spinner">
          <div class="ring"></div>
          <div class="ring"></div>
          <div class="ring"></div>
        </div>
        <h2 class="loading-text" data-text="GENERATING...">GENERATING...</h2>
      </div>
    </transition>

    <!-- Top Navbar -->
    <nav class="premium-navbar">
      <div class="nav-brand" @click="showHero = true">
        <svg class="nav-logo" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L2 22h20L12 2z" fill="url(#grad1)" />
          <defs>
            <linearGradient id="grad1" x1="2" y1="22" x2="22" y2="2" gradientUnits="userSpaceOnUse">
              <stop stop-color="#4e54c8" />
              <stop offset="1" stop-color="#8f94fb" />
            </linearGradient>
          </defs>
        </svg>
        <span class="nav-title">AccomPartner</span>
      </div>
      <div class="nav-menu">
        <button
          :class="{ active: currentAppMode === 'quick' && !showHero }"
          @click="switchMode('quick')"
        >
          Melody Editor
        </button>
        <button
          :class="{ active: currentAppMode === 'advanced' && !showHero }"
          @click="switchMode('advanced')"
        >
          MIDI Upload
        </button>
        <button
          :class="{ active: currentAppMode === 'realtime' && !showHero }"
          @click="switchMode('realtime')"
        >
          Realtime Piano
        </button>
      </div>
    </nav>

    <!-- Hero Section -->
    <transition name="fade-slide">
      <section v-show="showHero" class="hero-section">
        <canvas ref="musicParticlesCanvas" id="music-particles"></canvas>
        <div class="hero-content">
          <h1 class="hero-title">
            Experience Liftoff with<br /><span class="text-gradient">AccomPartner</span>
          </h1>
          <p class="hero-subtitle">
            Create, edit, and explore piano accompaniments instantly in our premium musical IDE.
          </p>
          <div class="hero-buttons">
            <button @click="startExperience" class="hero-btn primary-btn-glow">
              <span class="btn-text">Start Experience</span>
            </button>
            <button @click="switchMode('advanced')" class="hero-btn secondary-btn">
              <span class="btn-text">Explore Use Cases</span>
            </button>
          </div>
        </div>
      </section>
    </transition>

    <!-- Main Workspace -->
    <transition name="fade-up">
      <main v-show="!showHero" class="main-workspace">
        <!-- ==========================================
             Part 1: Quick Experience (Melody Editor)
             ========================================== -->
        <section v-show="currentAppMode === 'quick'" class="workspace-panel glass-panel">
          <div class="panel-header">
            <h2>Melody Editor</h2>
          </div>

          <div class="controls-card glass-card">
            <div class="control-row">
              <div class="control-group">
                <label>Editor Mode</label>
                <select v-model="editorMode" class="modern-select">
                  <option value="pad">Grid Pad Mode</option>
                  <option value="staff">Staff Mode (VexFlow)</option>
                </select>
              </div>

              <div class="control-group">
                <label>Inference Mode</label>
                <select v-model="selectedInferenceMode" class="modern-select">
                  <option value="oneStage">One-Stage</option>
                  <option value="twoStage-std">Two-Stage Std</option>
                  <option value="twoStage-bar">Two-Stage Bar</option>
                  <option value="twoStage-nar">Two-Stage NAR</option>
                </select>
              </div>
            </div>

            <div class="params-row flex-params">
              <div class="slider-group">
                <label
                  >Complexity: <span class="val-badge">{{ generationComplexity }}</span></label
                >
                <input
                  type="range"
                  v-model.number="generationComplexity"
                  min="0"
                  max="1"
                  step="0.05"
                  class="modern-range"
                />
              </div>
              <div class="slider-group">
                <label
                  >Creativity: <span class="val-badge">{{ generationCreativity }}</span></label
                >
                <input
                  type="range"
                  v-model.number="generationCreativity"
                  min="0.5"
                  max="1.5"
                  step="0.1"
                  class="modern-range"
                />
              </div>
              <div class="action-buttons">
                <!-- Removed Emojis -->
                <button
                  @click="generateRandomMelody"
                  class="modern-btn btn-outline"
                  :disabled="isGenerating"
                >
                  Generate Random
                </button>
                <button
                  @click="submitMelodyJson"
                  class="modern-btn btn-primary"
                  :disabled="isGenerating"
                >
                  Generate Accompaniment
                </button>
              </div>
            </div>
          </div>

          <div class="editor-area modern-editor-area">
            <!-- Pad Editor -->
            <div v-show="editorMode === 'pad'" class="pad-grid-wrapper">
              <div class="pad-toolbar">
                <button
                  @click="togglePreview"
                  class="modern-btn"
                  :class="isPlayingPreview ? 'btn-danger' : 'btn-info'"
                >
                  {{ isPlayingPreview ? 'Stop Playback' : 'Preview Melody' }}
                </button>
                <button @click="melodyData = []" class="modern-btn btn-outline-danger">
                  Clear Canvas
                </button>
              </div>

              <div class="pad-editor-container glass-container" @mouseleave="handleMouseUp">
                <div
                  class="pad-row"
                  v-for="pitch in pitches"
                  :key="pitch"
                  :class="{ 'is-black-key': isBlackKey(pitch) }"
                >
                  <div class="pad-label">{{ getPitchName(pitch) }}</div>
                  <div class="pad-grid-cells">
                    <div
                      class="pad-cell"
                      v-for="step in TOTAL_STEPS"
                      :key="step - 1"
                      @mousedown.prevent="handleMouseDown(pitch, step - 1)"
                      @mouseenter="handleMouseEnter(pitch, step - 1)"
                    >
                      <div
                        v-if="getNoteClass(pitch, step - 1) !== ''"
                        class="pad-cell-note-inner"
                        :class="getNoteClass(pitch, step - 1)"
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- VexFlow Editor -->
            <div v-show="editorMode === 'staff'" class="vexflow-container">
              <div class="vf-toolbar modern-vf-toolbar">
                <div class="tool-group">
                  <span class="tool-label">Duration:</span>
                  <button :class="{ active: vfToolDuration === 1 }" @click="vfToolDuration = 1">
                    Eighth Note
                  </button>
                  <button :class="{ active: vfToolDuration === 2 }" @click="vfToolDuration = 2">
                    Quarter Note
                  </button>
                </div>
                <div class="tool-group">
                  <span class="tool-label">Accidental:</span>
                  <button
                    :class="{ active: vfToolAccidental === '' }"
                    @click="vfToolAccidental = ''"
                  >
                    Natural
                  </button>
                  <button
                    :class="{ active: vfToolAccidental === '#' }"
                    @click="vfToolAccidental = '#'"
                  >
                    Sharp
                  </button>
                  <button
                    :class="{ active: vfToolAccidental === 'b' }"
                    @click="vfToolAccidental = 'b'"
                  >
                    Flat
                  </button>
                </div>
              </div>

              <div class="staff-layout glass-container">
                <div class="fixed-clef" ref="clefContainer"></div>
                <div
                  class="scrollable-measures"
                  ref="vexflowContainer"
                  @mousedown="handleVexFlowClick"
                  @mousemove="handleVexFlowMouseMove"
                  @mouseleave="handleVexFlowMouseLeave"
                ></div>
              </div>
              <p class="helper-text">Select duration, then click staff to add or remove notes.</p>
            </div>
          </div>

          <transition name="slide-fade">
            <div v-if="resultMidiUrl" class="player-section glass-container player-ui-card">
              <h3>Generation Result</h3>
              <midi-player
                :src="resultMidiUrl"
                sound-font
                visualizer="#my-visualizer"
              ></midi-player>
              <midi-visualizer
                type="piano-roll"
                id="my-visualizer"
                :src="resultMidiUrl"
              ></midi-visualizer>
              <div class="dl-wrapper mt-10">
                <a
                  :href="resultMidiUrl"
                  download="melody_accompaniment.mid"
                  class="modern-btn btn-outline dl-link"
                >
                  Download MIDI
                </a>
              </div>
            </div>
          </transition>
        </section>

        <!-- ==========================================
             Part 2: Advanced Mode (MIDI Upload)
             ========================================== -->
        <section v-show="currentAppMode === 'advanced'" class="workspace-panel glass-panel">
          <div class="panel-header">
            <h2>MIDI Upload</h2>
          </div>

          <div class="upload-controls modern-upload glass-card">
            <label class="modern-file-upload">
              <input type="file" accept=".mid,.midi" @change="handleFileUpload" />
              <div class="upload-content">
                <div class="upload-icon">
                  <!-- Clean SVG Icon instead of emoji -->
                  <svg
                    width="40"
                    height="40"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    class="feather feather-upload-cloud"
                  >
                    <polyline points="16 16 12 12 8 16"></polyline>
                    <line x1="12" y1="12" x2="12" y2="21"></line>
                    <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"></path>
                    <polyline points="16 16 12 12 8 16"></polyline>
                  </svg>
                </div>
                <div class="upload-text">
                  {{ rawFile ? rawFile.name : 'Click to Upload MIDI File (.mid, .midi)' }}
                </div>
              </div>
            </label>
          </div>

          <transition name="fade-up">
            <div v-if="parsedTracks.length > 0" class="track-selection-wrapper">
              <div class="track-selection glass-container">
                <div class="control-row">
                  <div class="control-group fill-width">
                    <label>Select Primary Melody Track:</label>
                    <select v-model="selectedTrackIndex" class="modern-select">
                      <option disabled value="">Select Track...</option>
                      <option
                        v-for="track in parsedTracks"
                        :key="track.originalIndex"
                        :value="track.originalIndex"
                      >
                        Track {{ track.originalIndex + 1 }} - {{ track.instrumentName }} ({{
                          track.noteCount
                        }}
                        notes)
                      </option>
                    </select>
                  </div>
                </div>

                <transition name="slide-fade">
                  <div
                    v-if="previewMidiUrl"
                    class="preview-section modern-preview player-ui-card mt-20"
                  >
                    <h4>Melody Preview (Single Track)</h4>
                    <midi-player
                      :src="previewMidiUrl"
                      sound-font
                      visualizer="#preview-visualizer"
                    ></midi-player>
                    <midi-visualizer
                      type="staff"
                      id="preview-visualizer"
                      :src="previewMidiUrl"
                    ></midi-visualizer>
                  </div>
                </transition>

                <div class="advanced-params-group mt-20">
                  <div class="control-group">
                    <label>Inference Mode:</label>
                    <select v-model="selectedInferenceMode" class="modern-select">
                      <option value="oneStage">One-Stage (Direct Generation)</option>
                      <option value="twoStage-std">Two-Stage Std (AR Chords)</option>
                      <option value="twoStage-bar">Two-Stage Bar</option>
                      <option value="twoStage-nar">Two-Stage NAR (Non-Autoregressive)</option>
                    </select>
                  </div>

                  <div class="params-adjustment modern-params">
                    <div class="slider-group">
                      <label
                        >Complexity: <span class="val-badge">{{ generationComplexity }}</span></label
                      >
                      <input
                        type="range"
                        v-model.number="generationComplexity"
                        min="0"
                        max="1"
                        step="0.05"
                        class="modern-range"
                      />
                      <div class="slider-ticks">
                        <span>Minimal</span><span>Balanced</span><span>Complex</span>
                      </div>
                    </div>
                    <div class="slider-group">
                      <label
                        >Creativity:
                        <span class="val-badge">{{ generationCreativity }}</span></label
                      >
                      <input
                        type="range"
                        v-model.number="generationCreativity"
                        min="0.1"
                        max="2.0"
                        step="0.1"
                        class="modern-range"
                      />
                      <div class="slider-ticks">
                        <span>Stable</span><span>Creative</span><span>Chaotic</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="action-footer mt-20">
                  <button
                    :disabled="selectedTrackIndex === '' || isGenerating"
                    @click="submitMidiFile"
                    class="modern-btn btn-primary btn-large w-full"
                  >
                    Generate Accompaniment
                  </button>
                </div>
              </div>

              <transition name="fade">
                <div
                  v-if="resultMidiUrl"
                  class="player-section glass-container mt-20 player-ui-card"
                >
                  <h3>Accompaniment Output</h3>
                  <midi-player
                    :src="resultMidiUrl"
                    sound-font
                    visualizer="#advanced-visualizer"
                  ></midi-player>
                  <midi-visualizer
                    type="staff"
                    id="advanced-visualizer"
                    :src="resultMidiUrl"
                  ></midi-visualizer>
                  <div class="dl-wrapper mt-10">
                    <a
                      :href="resultMidiUrl"
                      download="melody_accompaniment.mid"
                      class="modern-btn btn-outline dl-link"
                    >
                      Download MIDI
                    </a>
                  </div>
                </div>
              </transition>
            </div>
          </transition>
        </section>

        <!-- ==========================================
             Part 3: Realtime Accompaniment
             ========================================== -->
        <section v-show="currentAppMode === 'realtime'" class="workspace-panel glass-panel">
          <div class="panel-header">
            <h2>Realtime Accompaniment Engine</h2>
          </div>

          <div class="realtime-controls modern-controls glass-card">
            <div class="control-group">
              <label>Tempo (BPM):</label>
              <input
                type="number"
                v-model.number="realtimeBPM"
                min="60"
                max="200"
                step="10"
                class="modern-input"
              />
              <span class="bpm-display val-badge">{{ realtimeBPM }}</span>
            </div>
            <div class="control-buttons">
              <button
                @click="startRealtime"
                :disabled="isRealtimePlaying"
                class="modern-btn btn-primary"
              >
                Start Engine
              </button>
              <button
                @click="stopRealtime"
                :disabled="!isRealtimePlaying"
                class="modern-btn btn-danger"
              >
                Stop Engine
              </button>
            </div>
          </div>

          <transition name="fade-up">
            <div class="realtime-status modern-status glow-box" v-if="isRealtimePlaying">
              <div class="status-item">
                <span class="label">Current Bar</span>
                <span class="value">{{ currentBar }}</span>
              </div>
              <div class="status-item">
                <span class="label">Current Beat</span>
                <span class="value beat-indicator" :class="{ pulse: beatPulse }"
                  >{{ currentBeat }} / 4</span
                >
              </div>
              <div class="status-item">
                <span class="label">Status</span>
                <span class="value status-text">{{ realtimeStatus }}</span>
              </div>
            </div>
          </transition>

          <div class="virtual-keyboard glass-container glow-hover">
            <h3 class="panel-subtitle">Virtual Piano (C4 ~ E5)</h3>
            <div class="keyboard-container modern-keyboard">
              <div
                v-for="(key, index) in pianoKeys"
                :key="index"
                class="piano-key"
                :class="{
                  active: activeKeys.has(key.keyCode),
                  'white-key': key.isWhite,
                  'black-key': !key.isWhite,
                }"
              >
                <div class="key-label">{{ key.note }}</div>
                <div class="key-binding">{{ key.key }}</div>
              </div>
            </div>
            <p class="keyboard-hint">
              Use Keyboard A S D F G H J K L ; to play. Hold for longer notes.
            </p>
          </div>

          <div class="history-logs-grid mt-20">
            <div class="note-history glass-card" v-if="recordedNotes && recordedNotes.length > 0">
              <h3 class="panel-subtitle">Played Notes (Current Bar)</h3>
              <div class="note-list">
                <div
                  v-for="(note, idx) in recordedNotes.slice(-20)"
                  :key="idx"
                  class="note-item modern-chip"
                >
                  {{ note.note }}
                </div>
              </div>
            </div>

            <div class="generation-log glass-card" v-if="generationHistory.length > 0">
              <h3 class="panel-subtitle">Generation Logs</h3>
              <div class="log-entries">
                <div
                  v-for="(entry, idx) in generationHistory"
                  :key="idx"
                  class="log-entry modern-log"
                >
                  <span class="log-time gradient-text">Bar {{ entry.bar }}</span>
                  <span class="log-message">{{ entry.message }}</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { Midi } from '@tonejs/midi' // npm install @tonejs/midi.
import { Renderer, Stave, StaveNote, Accidental, Voice, Formatter } from 'vexflow'
import * as Tone from 'tone' // npm install tone
import { aiService } from '@/services/aiService'
import { tokenizerService } from '@/services/tokenizerService'

// --- 全域狀態 ---
const currentAppMode = ref('quick') // 'quick' | 'advanced' | 'realtime'

const showHero = ref(true)
const musicParticlesCanvas = ref(null)
let animationFrameId = null

const switchMode = (mode) => {
  currentAppMode.value = mode
  showHero.value = false
}

const startExperience = () => {
  showHero.value = false
}

const initMusicParticles = () => {
  if (!showHero.value) return
  const canvas = musicParticlesCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')

  const resizeCanvas = () => {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
  }
  window.addEventListener('resize', resizeCanvas)
  resizeCanvas()

  const particles = []
  for (let i = 0; i < 150; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      radius: Math.random() * 3 + 1,
      density: Math.random() * 30 + 1,
      // Premium colors
      color: `rgba(${100 + Math.random() * 80}, ${120 + Math.random() * 105}, ${200 + Math.random() * 55}, ${Math.random() * 0.4 + 0.1})`,
      vx: (Math.random() - 0.5) * 1.5,
      vy: (Math.random() - 0.5) * 1.5,
      phase: Math.random() * Math.PI * 2,
    })
  }

  let mouse = { x: null, y: null }
  canvas.addEventListener('mousemove', (e) => {
    mouse.x = e.clientX
    mouse.y = e.clientY
  })
  canvas.addEventListener('mouseleave', () => {
    mouse.x = null
    mouse.y = null
  })

  // Pulsing connection lines
  let pulsePhase = 0

  const animate = () => {
    if (!showHero.value) {
      if (animationFrameId) cancelAnimationFrame(animationFrameId)
      return
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height)
    pulsePhase += 0.02

    for (let i = 0; i < particles.length; i++) {
      let p = particles[i]

      p.x += p.vx
      p.y += p.vy

      if (p.x < 0 || p.x > canvas.width) p.vx = -p.vx
      if (p.y < 0 || p.y > canvas.height) p.vy = -p.vy

      // breathing
      let breath = Math.sin(p.phase) * 0.5
      p.radius = Math.max(0.5, p.radius + breath * 0.05)
      p.phase += 0.05

      if (mouse.x !== null && mouse.y !== null) {
        let dx = mouse.x - p.x
        let dy = mouse.y - p.y
        let distance = Math.sqrt(dx * dx + dy * dy)
        let maxDistance = 180
        if (distance < maxDistance) {
          let force = (maxDistance - distance) / maxDistance
          p.x -= (dx / distance) * force * p.density * 0.5
          p.y -= (dy / distance) * force * p.density * 0.5
        }
      }

      ctx.beginPath()
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
      ctx.fillStyle = p.color
      ctx.fill()

      for (let j = i; j < particles.length; j++) {
        let p2 = particles[j]
        let dx = p.x - p2.x
        let dy = p.y - p2.y
        let distance = Math.sqrt(dx * dx + dy * dy)
        if (distance < 100) {
          ctx.beginPath()
          ctx.strokeStyle = `rgba(100, 140, 255, ${0.12 - distance / 833 + Math.sin(pulsePhase) * 0.02})`
          ctx.lineWidth = 1
          ctx.moveTo(p.x, p.y)
          ctx.lineTo(p2.x, p2.y)
          ctx.stroke()
        }
      }
    }

    animationFrameId = requestAnimationFrame(animate)
  }

  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  animate()
}

watch(showHero, (newVal) => {
  if (newVal) {
    nextTick(() => {
      initMusicParticles()
    })
  } else {
    if (animationFrameId) cancelAnimationFrame(animationFrameId)
  }
})

// Run on mount
onMounted(() => {
  initMusicParticles()
})

const resultMidiUrl = ref(null) // 後端回傳的 MIDI 檔案 URL (Blob URL 或真實 URL)
const isGenerating = ref(false) // 控制 Loading 狀態

// ==========================================
// 第一部分：初步體驗邏輯 (JSON 傳遞)
// ==========================================
const editorMode = ref('pad')
const vexflowContainer = ref(null)

// 存放 16 分音符的資料結構 (適合轉 JSON 給後端)
// 範例格式: [{ pitch: 60, step: 0, durationSteps: 2 }, ...]
const melodyData = ref([])

const generateRandomMelody = () => {
  console.log('[Editor] Generating Random Melody')
  melodyData.value = []

  // C Major scale MIDI pitches (C4 to A5)
  const cMajorPitches = [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81]

  let currentStep = 0
  const totalNotes = Math.floor(Math.random() * 8) + 8 // 8 to 15 notes

  for (let i = 0; i < totalNotes; i++) {
    if (currentStep >= TOTAL_STEPS) break

    const pitch = cMajorPitches[Math.floor(Math.random() * cMajorPitches.length)]

    // Choose between eighth note (2 steps) and sixteenth note (1 step)
    const durationSteps = Math.random() > 0.5 ? 2 : 1

    if (currentStep + durationSteps > TOTAL_STEPS) break

    melodyData.value.push({
      pitch: pitch,
      step: currentStep,
      durationSteps: durationSteps,
    })

    currentStep += durationSteps + (Math.random() > 0.7 ? 1 : 0) // maybe a rest
  }

  if (editorMode.value === 'staff') {
    nextTick(() => {
      renderVexFlow()
    })
  }
}

const submitMelodyJson = async () => {
  if (melodyData.value.length === 0) {
    alert('Please create or generate a melody first!')
    return
  }

  try {
    isGenerating.value = true
    console.log('[API] 準備傳送 JSON 給後端:', melodyData.value)

    // 呼叫後端 API (假設使用 fetch)
    const response = await fetch('/api/generate-from-json', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        melody: melodyData.value,
        mode: selectedInferenceMode.value, // 這裡也讓一階段可以使用
        complexity: generationComplexity.value,
        creativity: generationCreativity.value,
      }),
    })

    if (!response.ok) throw new Error('Network response was not ok')

    // 假設後端直接回傳 .mid 檔案的二進位流
    const blob = await response.blob()
    resultMidiUrl.value = URL.createObjectURL(blob)
    console.log('[API] 成功接收生成之 MIDI URL')
  } catch (error) {
    console.error('[API Error] JSON 傳送失敗:', error)
  } finally {
    isGenerating.value = false
  }
}

// ==========================================
// 第二部分：進階上傳邏輯 (FormData & Tone.js)
// ==========================================
const rawFile = ref(null)
const rawMidiBuffer = ref(null)
const parsedTracks = ref([])
const selectedTrackIndex = ref('')
const previewMidiUrl = ref(null)
const selectedInferenceMode = ref('oneStage')
const generationComplexity = ref(0.5)
const generationCreativity = ref(1.0)

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  rawFile.value = file
  parsedTracks.value = []
  selectedTrackIndex.value = ''

  // 清理舊的預覽 URL 避免記憶體洩漏
  if (previewMidiUrl.value) {
    URL.revokeObjectURL(previewMidiUrl.value)
    previewMidiUrl.value = null
  }
  resultMidiUrl.value = null

  try {
    console.log(`[Tone.js] 開始解析檔案: ${file.name}`)
    const arrayBuffer = await file.arrayBuffer()
    rawMidiBuffer.value = arrayBuffer // 把 buffer 存起來，後面預覽會用到

    const midi = new Midi(arrayBuffer)
    const trackInfoList = []

    midi.tracks.forEach((track, originalIndex) => {
      if (track.notes.length > 0) {
        trackInfoList.push({
          originalIndex: originalIndex,
          noteCount: track.notes.length,
          instrumentName: track.instrument?.name || 'Unknown Instrument',
        })
      }
    })

    parsedTracks.value = trackInfoList
  } catch (error) {
    console.error('[Tone.js Error] 解析過程中發生錯誤:', error)
    alert('解析 MIDI 失敗。')
  }
}

// 🌟 核心魔法：監聽使用者選擇音軌，動態生成單軌 MIDI 預覽
watch(selectedTrackIndex, (newIndex) => {
  console.log(`----------------------------------------`)
  console.log(`[UI Event] 🖱️ 下拉選單改變！目前選擇的音軌 Index: ${newIndex}`)

  if (newIndex === '' || !rawMidiBuffer.value) {
    console.log('[Preview] ⚠️ 尚未選擇有效音軌或原始檔案遺失，跳過預覽生成。')
    return
  }

  try {
    console.log(`[Preview] ⚙️ 開始生成單軌預覽... (目標音軌 Index: ${newIndex})`)

    // 1. 重新讀取原始的 MIDI 資料
    const originalMidi = new Midi(rawMidiBuffer.value)

    // 2. 建立一個全新的、空的 MIDI 物件
    const singleTrackMidi = new Midi()

    // 3. 把原本 MIDI 的全域設定 (BPM、拍號) 複製過來
    singleTrackMidi.header = originalMidi.header

    // 4. 提取使用者選中的那一軌
    const targetTrack = originalMidi.tracks[newIndex]
    singleTrackMidi.tracks.push(targetTrack)
    console.log(
      `[Preview] 🎵 成功提取音軌！樂器: ${targetTrack.instrument?.name || '未知'}, 音符數量: ${targetTrack.notes.length}`,
    )

    // 5. 將這個新的單軌 MIDI 轉回二進位 Buffer
    const outBuffer = singleTrackMidi.toArray()

    // 6. 製作成 Blob URL 給 html-midi-player 吃
    const blob = new Blob([outBuffer], { type: 'audio/midi' })

    // 如果之前有預覽過，先釋放記憶體
    if (previewMidiUrl.value) {
      console.log(`[Preview] 🗑️ 清除舊的預覽 URL 釋放記憶體: ${previewMidiUrl.value}`)
      URL.revokeObjectURL(previewMidiUrl.value)
    }

    previewMidiUrl.value = URL.createObjectURL(blob)
    console.log(`[Preview] ✅ 成功生成新的預覽 URL: ${previewMidiUrl.value}`)
    console.log(`[Preview] 🚀 準備交給 html-midi-player 進行渲染！`)
    console.log(`----------------------------------------`)
  } catch (error) {
    console.error('[Preview Error] ❌ 生成單軌預覽失敗:', error)
  }
})

const submitMidiFile = async () => {
  if (!rawFile.value || selectedTrackIndex.value === '') return

  try {
    isGenerating.value = true

    // 使用 FormData 打包檔案與使用者選擇的音軌 index
    const formData = new FormData()
    formData.append('midiFile', rawFile.value)
    formData.append('targetTrackIndex', selectedTrackIndex.value)
    formData.append('mode', selectedInferenceMode.value)
    formData.append('complexity', generationComplexity.value)
    formData.append('creativity', generationCreativity.value)

    console.log(`[API] 準備上傳檔案，選擇的旋律音軌為: ${selectedTrackIndex.value}`)

    const response = await fetch('/api/generate-from-midi', {
      method: 'POST',
      body: formData, // 注意：使用 FormData 時，fetch 會自動設定 multipart/form-data header
    })

    if (!response.ok) throw new Error('Network response was not ok')

    const blob = await response.blob()
    resultMidiUrl.value = URL.createObjectURL(blob)
    console.log('[API] 成功接收雙軌伴奏 MIDI URL')
  } catch (error) {
    console.error('[API Error] 檔案上傳失敗:', error)
  } finally {
    isGenerating.value = false
  }
}

// ==========================================
// 第三部分：PAD
// ==========================================
// --- Pad 編輯器核心常數 ---
const PITCH_MAX = 95 // B6 (最高音)
const PITCH_MIN = 60 // C4 (中音 Do)
const TOTAL_STEPS = 32 // 4 小節 * 每小節 8 個八分音符

// 生成由高到低的音高陣列 (供 UI 渲染 Y 軸)
const pitches = computed(() => {
  const arr = []
  for (let i = PITCH_MAX; i >= PITCH_MIN; i--) arr.push(i)
  return arr
})

// --- Tone.js 聲音合成器設定 ---
let synth = null
const initSynth = async () => {
  if (!synth) {
    // 必須由使用者互動觸發 Tone.start()
    await Tone.start()
    // 建立一個簡單好聽的合成器並連接到主聲道
    synth = new Tone.Synth({
      oscillator: { type: 'triangle' }, // 三角波聲音比較柔和
      envelope: { attack: 0.05, decay: 0.2, sustain: 0.2, release: 1 },
    }).toDestination()
  }
}

const playPitch = async (pitch) => {
  await initSynth()
  // 將 MIDI 數字轉為頻率 (Hz)
  const freq = Tone.Frequency(pitch, 'midi').toFrequency()
  synth.triggerAttackRelease(freq, '8n')
}

// --- 互動與繪圖邏輯 (滑鼠拖曳) ---
const isDrawing = ref(false)
const drawStartStep = ref(-1)
const activePitch = ref(-1)

// 互斥機制：確保單音旋律 (吃掉重疊的音符)
const removeOverlappingNotes = (start, duration, excludeNote = null) => {
  const end = start + duration
  melodyData.value = melodyData.value.filter((n) => {
    if (n === excludeNote) return true
    const nEnd = n.step + n.duration
    // 判斷兩個區間是否重疊
    const overlap = Math.max(start, n.step) < Math.min(end, nEnd)
    return !overlap
  })
}

const handleMouseDown = async (pitch, step) => {
  await initSynth()

  // 1. 檢查是否點擊在現有音符上 (如果是，則刪除該音符)
  const existingIndex = melodyData.value.findIndex(
    (n) => n.pitch === pitch && step >= n.step && step < n.step + n.duration,
  )
  if (existingIndex !== -1) {
    melodyData.value.splice(existingIndex, 1)
    return
  }

  // 2. 開始畫新音符
  isDrawing.value = true
  drawStartStep.value = step
  activePitch.value = pitch

  removeOverlappingNotes(step, 1) // 清除該時間點的其他音符
  melodyData.value.push({ pitch, step, duration: 1 })
  playPitch(pitch)
}

const handleMouseEnter = (pitch, step) => {
  // 只允許在同一列(相同音高)向右拖曳
  if (!isDrawing.value || pitch !== activePitch.value || step < drawStartStep.value) return

  const note = melodyData.value.find(
    (n) => n.step === drawStartStep.value && n.pitch === activePitch.value,
  )
  if (note) {
    const newDuration = step - drawStartStep.value + 1
    note.duration = newDuration
    // 延音時，吃掉前方被覆蓋到的音符
    removeOverlappingNotes(drawStartStep.value, newDuration, note)
  }
}

const handleMouseUp = () => {
  isDrawing.value = false
}

// 全域監聽滑鼠放開，避免拖曳到格子外造成狀態卡住
onMounted(() => window.addEventListener('mouseup', handleMouseUp))
onUnmounted(() => window.removeEventListener('mouseup', handleMouseUp))

// --- 🌟 UI 渲染輔助函數 (修復音符類應用於子元素) ---
const isBlackKey = (pitch) => [1, 3, 6, 8, 10].includes(pitch % 12)

// 🌟 新增：獲取音符子元素的類名
const getNoteClass = (pitch, step) => {
  const note = melodyData.value.find(
    (n) => n.pitch === pitch && step >= n.step && step < n.step + n.duration,
  )
  if (!note) return ''
  return note.step === step ? 'cell-start' : 'cell-tail'
}

const getPitchName = (pitch) => {
  const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
  const name = names[pitch % 12]
  const octave = Math.floor(pitch / 12) - 1
  // 黑鍵不顯示文字，讓畫面乾淨些
  return isBlackKey(pitch) ? '' : `${name}${octave}`
}

// --- 預覽播放功能 ---
const isPlayingPreview = ref(false)
const togglePreview = async () => {
  await initSynth()
  if (isPlayingPreview.value) {
    Tone.Transport.stop()
    Tone.Transport.cancel()
    isPlayingPreview.value = false
    return
  }

  if (melodyData.value.length === 0) return

  isPlayingPreview.value = true
  const stepTime = Tone.Time('8n').toSeconds()

  // 遍歷所有音符並排程
  melodyData.value.forEach((n) => {
    const freq = Tone.Frequency(n.pitch, 'midi').toFrequency()
    Tone.Transport.schedule((time) => {
      synth.triggerAttackRelease(freq, n.duration * stepTime, time)
    }, n.step * stepTime)
  })

  // 設定在最後一拍自動停止
  Tone.Transport.schedule(() => {
    isPlayingPreview.value = false
    Tone.Transport.stop()
    Tone.Transport.cancel()
  }, TOTAL_STEPS * stepTime)

  Tone.Transport.start()
}

// ==========================================
// 第四部分：五線譜 (VexFlow) 專屬邏輯
// ==========================================
// const vexflowContainer = ref(null);

// 工具列狀態
const vfToolDuration = ref(1) // 1 = 八分音符(預設), 2 = 四分音符
const vfToolAccidental = ref('') // '' = 自然音, '#' = 升記號, 'b' = 降記號

// 定義高音譜號 (Treble Clef) 的白鍵對應表 (從 C4 到 A5)
// offset 是一個相對位置，用來換算滑鼠點擊的 Y 座標
const diatonicScale = [
  { step: 'c/4', basePitch: 60, lineOffset: 5 },
  { step: 'd/4', basePitch: 62, lineOffset: 4.5 },
  { step: 'e/4', basePitch: 64, lineOffset: 4 },
  { step: 'f/4', basePitch: 65, lineOffset: 3.5 },
  { step: 'g/4', basePitch: 67, lineOffset: 3 },
  { step: 'a/4', basePitch: 69, lineOffset: 2.5 },
  { step: 'b/4', basePitch: 71, lineOffset: 2 },
  { step: 'c/5', basePitch: 72, lineOffset: 1.5 },
  { step: 'd/5', basePitch: 74, lineOffset: 1 },
  { step: 'e/5', basePitch: 76, lineOffset: 0.5 },
  { step: 'f/5', basePitch: 77, lineOffset: 0 }, // 第五線 (最上線)
  { step: 'g/5', basePitch: 79, lineOffset: -0.5 },
  { step: 'a/5', basePitch: 81, lineOffset: -1 },
]

// 核心渲染函數：將 melodyData 轉換為完美的五線譜

const clefContainer = ref(null)

// ==========================================
// 🌟 支援懸停預覽的 VexFlow 渲染引擎
// ==========================================
const renderVexFlow = () => {
  if (editorMode.value !== 'staff' || !vexflowContainer.value || !clefContainer.value) return

  try {
    clefContainer.value.innerHTML = ''
    const clefRenderer = new Renderer(clefContainer.value, Renderer.Backends.SVG)
    clefRenderer.resize(80, 180)
    const clefCtx = clefRenderer.getContext()
    new Stave(5, 40, 75).addClef('treble').addTimeSignature('4/4').setContext(clefCtx).draw()

    vexflowContainer.value.innerHTML = ''
    const renderer = new Renderer(vexflowContainer.value, Renderer.Backends.SVG)
    renderer.resize(800, 180)
    const context = renderer.getContext()

    // 🌟 核心邏輯：建立「視覺專用」的資料陣列
    let displayData = melodyData.value.map((n) => ({ ...n, isReal: true }))
    let ghostActionMeasure = -1 // 記錄哪個小節發生了預覽行為

    if (ghostNote.value) {
      const gStep = ghostNote.value.step
      ghostActionMeasure = Math.floor(gStep / 8)

      // 檢查是否懸停在「既有音符」上
      const existingIndex = displayData.findIndex(
        (n) => gStep >= n.step && gStep < n.step + n.duration,
      )

      if (existingIndex !== -1) {
        // 動作：準備刪除 (標記為 isDeleting)
        displayData[existingIndex].isDeleting = true
      } else {
        // 動作：準備新增
        let safeDuration = ghostNote.value.duration
        const stepInMeasure = gStep % 8
        const maxDuration = 8 - stepInMeasure
        if (safeDuration > maxDuration) safeDuration = maxDuration

        // 模擬覆蓋邏輯：剔除會被新音符蓋掉的舊音符
        const end = gStep + safeDuration
        displayData = displayData.filter((n) => {
          const nEnd = n.step + n.duration
          const overlap = Math.max(gStep, n.step) < Math.min(end, nEnd)
          return !overlap
        })

        // 塞入半透明虛擬音符
        displayData.push({
          pitch: ghostNote.value.pitch,
          step: gStep,
          duration: safeDuration,
          accidental: ghostNote.value.accidental,
          isGhost: true,
        })
      }
    }

    let currentX = 0
    const measureWidth = 200

    for (let m = 0; m < 4; m++) {
      const stave = new Stave(currentX, 40, measureWidth)
      stave.setContext(context).draw()

      const vfNotes = []
      let currentStep = m * 8
      const endStep = (m + 1) * 8

      while (currentStep < endStep) {
        // 從我們合併好的 displayData 中找音符
        const noteData = displayData.find((n) => n.step === currentStep)

        if (noteData) {
          let renderDuration = noteData.duration
          if (currentStep + renderDuration > endStep) renderDuration = endStep - currentStep

          const durationStr = renderDuration === 2 ? 'q' : '8'
          let vfKey = 'b/4'
          const noteMatch = diatonicScale.find(
            (d) =>
              d.basePitch === noteData.pitch ||
              d.basePitch + 1 === noteData.pitch ||
              d.basePitch - 1 === noteData.pitch,
          )
          if (noteMatch) {
            vfKey = noteMatch.step
            if (noteData.accidental) vfKey = vfKey.replace('/', `${noteData.accidental}/`)
          }

          const staveNote = new StaveNote({ clef: 'treble', keys: [vfKey], duration: durationStr })
          if (noteData.accidental) staveNote.addModifier(new Accidental(noteData.accidental))

          // 🌟 樣式上色：根據狀態套用不同顏色
          if (noteData.isDeleting) {
            staveNote.setStyle({
              fillStyle: 'rgba(231, 76, 60, 0.5)',
              strokeStyle: 'rgba(231, 76, 60, 0.5)',
            }) // 準備刪除：半透明紅
          } else if (noteData.isGhost) {
            staveNote.setStyle({
              fillStyle: 'rgba(100, 100, 100, 0.5)',
              strokeStyle: 'rgba(100, 100, 100, 0.5)',
            }) // 準備新增：半透明灰黑
          }

          vfNotes.push(staveNote)
          currentStep += renderDuration
        } else {
          // 處理休止符
          const nextNoteExists = displayData.find((n) => n.step === currentStep + 1)
          let restNote
          if (currentStep % 2 === 0 && !nextNoteExists && currentStep + 1 < endStep) {
            restNote = new StaveNote({ clef: 'treble', keys: ['b/4'], duration: 'qr' })
            currentStep += 2
          } else {
            restNote = new StaveNote({ clef: 'treble', keys: ['b/4'], duration: '8r' })
            currentStep += 1
          }

          // 🌟 若這個休止符是跟著虛擬音符一起在該小節重新計算出來的，也讓它半透明
          if (m === ghostActionMeasure) {
            restNote.setStyle({
              fillStyle: 'rgba(150, 150, 150, 0.5)',
              strokeStyle: 'rgba(150, 150, 150, 0.5)',
            })
          }
          vfNotes.push(restNote)
        }
      }

      const voice = new Voice({ num_beats: 4, beat_value: 4 })
      voice.addTickables(vfNotes)
      new Formatter().joinVoices([voice]).format([voice], measureWidth - 20)
      voice.draw(context, stave)

      currentX += measureWidth
    }
  } catch (error) {
    console.error('[VexFlow 渲染被保護機制攔截] 發生錯誤:', error)
  }
}

// 監聽畫布點擊事件
const handleVexFlowClick = (event) => {
  const rect = vexflowContainer.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  // 1. 計算點擊的是第幾個 step (水平 X 軸反推)
  let measureIndex = Math.floor(x / 200) // 直接除以小節寬度
  if (measureIndex < 0) measureIndex = 0
  if (measureIndex > 3) return

  const localX = x % 200
  // 每個 8 分音符大約佔 25px (200 / 8 = 25)，平移 10px 避開小節線
  let stepInMeasure = Math.floor((localX - 10) / 23)
  if (stepInMeasure < 0) stepInMeasure = 0
  if (stepInMeasure > 7) stepInMeasure = 7

  const targetStep = measureIndex * 8 + stepInMeasure

  // 2. 判斷是否為「刪除操作」
  // 尋找點擊位置是否有音符 (包含覆蓋到的長音符)
  const existingIndex = melodyData.value.findIndex(
    (n) => targetStep >= n.step && targetStep < n.step + n.duration,
  )
  if (existingIndex !== -1) {
    melodyData.value.splice(existingIndex, 1)
    playPitch(melodyData.value[existingIndex]?.pitch || 60) // 發個聲提示刪除
    return
  }

  // 3. 計算點擊的音高 (垂直 Y 軸反推)
  // VexFlow 五線譜最上線(F5) 大約在 y=80，每條線/間 距約為 10px
  const yOffset = (y - 80) / 10

  // 找尋最接近的自然音
  let closestDiatonic = diatonicScale[0]
  let minDiff = 999
  for (const ds of diatonicScale) {
    const diff = Math.abs(ds.lineOffset - yOffset)
    if (diff < minDiff) {
      minDiff = diff
      closestDiatonic = ds
    }
  }

  // 應用工具列的升降記號
  let finalPitch = closestDiatonic.basePitch
  if (vfToolAccidental.value === '#') finalPitch += 1
  if (vfToolAccidental.value === 'b') finalPitch -= 1

  // 阻擋並提示使用者
  const duration = vfToolDuration.value
  const maxDuration = 8 - stepInMeasure

  if (duration > maxDuration) {
    // 彈出提示，並直接 return 終止函數，不讓錯誤資料進入 melodyData
    alert(`⚠️ 無法新增：此小節剩餘的空間放不下您選擇的音符！`)
    return
  }

  // 4. 加入新音符
  removeOverlappingNotes(targetStep, duration)
  melodyData.value.push({
    pitch: finalPitch,
    step: targetStep,
    duration: duration,
    accidental: vfToolAccidental.value,
  })

  playPitch(finalPitch)
}

// 🌟 懸停預覽狀態 (Ghost Note)
const ghostNote = ref(null)

// 處理滑鼠在畫布上移動的邏輯 (負責產生虛擬音符)
const handleVexFlowMouseMove = (event) => {
  if (editorMode.value !== 'staff' || !vexflowContainer.value) return
  const rect = vexflowContainer.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  let measureIndex = Math.floor(x / 200)
  // 如果滑鼠超出邊界，清空預覽
  if (measureIndex < 0 || measureIndex > 3) {
    ghostNote.value = null
    return
  }

  const localX = x % 200
  let stepInMeasure = Math.floor((localX - 10) / 23)
  if (stepInMeasure < 0) stepInMeasure = 0
  if (stepInMeasure > 7) stepInMeasure = 7
  const targetStep = measureIndex * 8 + stepInMeasure

  const yOffset = (y - 80) / 10
  let closestDiatonic = diatonicScale[0]
  let minDiff = 999
  for (const ds of diatonicScale) {
    const diff = Math.abs(ds.lineOffset - yOffset)
    if (diff < minDiff) {
      minDiff = diff
      closestDiatonic = ds
    }
  }

  let finalPitch = closestDiatonic.basePitch
  if (vfToolAccidental.value === '#') finalPitch += 1
  if (vfToolAccidental.value === 'b') finalPitch -= 1

  // 🛡️ 效能優化：只有當「網格位置」或「音高」真正改變時，才更新虛擬狀態引發重繪
  if (
    !ghostNote.value ||
    ghostNote.value.step !== targetStep ||
    ghostNote.value.pitch !== finalPitch ||
    ghostNote.value.duration !== vfToolDuration.value ||
    ghostNote.value.accidental !== vfToolAccidental.value
  ) {
    ghostNote.value = {
      step: targetStep,
      pitch: finalPitch,
      duration: vfToolDuration.value,
      accidental: vfToolAccidental.value,
    }
  }
}

// 滑鼠離開畫布時，清除預覽
const handleVexFlowMouseLeave = () => {
  ghostNote.value = null
}

// 當資料改變、或切換到五線譜模式時，重新渲染
watch(
  [melodyData, editorMode, ghostNote],
  () => {
    if (editorMode.value === 'staff') {
      nextTick(() => {
        renderVexFlow()
      })
    }
  },
  { deep: true },
)

// ==========================================
// 第三部分：即時伴奏功能
// ==========================================

// --- 即時伴奏狀態 ---
const isRealtimePlaying = ref(false)
const realtimeBPM = ref(120)
const currentBar = ref(0)
const currentBeat = ref(0)
const beatPulse = ref(false)
const realtimeStatus = ref('Waiting to Start')

// --- 鍵盤映射 (10個白鍵 C4~E5) ---
const pianoKeys = [
  { key: 'a', keyCode: 'KeyA', note: 'C4', midi: 60, isWhite: true },
  { key: 's', keyCode: 'KeyS', note: 'D4', midi: 62, isWhite: true },
  { key: 'd', keyCode: 'KeyD', note: 'E4', midi: 64, isWhite: true },
  { key: 'f', keyCode: 'KeyF', note: 'F4', midi: 65, isWhite: true },
  { key: 'g', keyCode: 'KeyG', note: 'G4', midi: 67, isWhite: true },
  { key: 'h', keyCode: 'KeyH', note: 'A4', midi: 69, isWhite: true },
  { key: 'j', keyCode: 'KeyJ', note: 'B4', midi: 71, isWhite: true },
  { key: 'k', keyCode: 'KeyK', note: 'C5', midi: 72, isWhite: true },
  { key: 'l', keyCode: 'KeyL', note: 'D5', midi: 74, isWhite: true },
  { key: ';', keyCode: 'Semicolon', note: 'E5', midi: 76, isWhite: true },
]

const activeKeys = ref(new Set())
const recordedNotes = ref([])
const generationHistory = ref([])

// --- Tone.js 音訊設定 ---
let metronome = null
let schedulerId = null
let currentlyPlayingNotes = new Map() // 追蹤正在播放的音符

// 獨立的樂器變數
let melodySynth = null // 笛子
let accSynth = null // 鋼琴

// --- 錄製狀態 ---
let recordingStartTime = 0
let currentBarNotes = [] // 當前小節錄製的音符
let previousAccompaniment = [] // 上一次生成的伴奏

// 初始化 Tone.js
const initToneJs = async () => {
  if (metronome) return // 已初始化即時伴奏專屬的合成器

  await Tone.start()
  console.log('[Realtime] Tone.js 已啟動')

  await tokenizerService.init()
  await aiService.init()

  // 1. 主音符合成器 (笛子 Flute)
  // 使用 Sine 波形，Attack 漸進，Sustain 飽滿
  melodySynth = new Tone.Sampler({
    urls: {
      C3: 'C3.mp3',
      'F#3': 'Fs3.mp3',
      C4: 'C4.mp3',
      'F#4': 'Fs4.mp3',
      C5: 'C5.mp3',
    },
    baseUrl: 'https://tonejs.github.io/audio/salamander/',
  }).toDestination()

  // 為了讓主旋律在伴奏中能被清楚聽見，我們把旋律音量稍微調大 (預設是 0)
  melodySynth.volume.value = 2

  // 2. 伴奏合成器 (真實鋼琴音色)
  // 使用 Tone.Sampler 載入真實鋼琴的音檔，聽起來最逼真
  accSynth = new Tone.Sampler({
    urls: {
      C3: 'C3.mp3',
      'F#3': 'Fs3.mp3',
      C4: 'C4.mp3',
      'F#4': 'Fs4.mp3',
      C5: 'C5.mp3',
    },
    baseUrl: 'https://tonejs.github.io/audio/salamander/', // Tone.js 官方提供的開源鋼琴取樣
  }).toDestination()
  accSynth.volume.value = -3 // 伴奏音量退後一點

  // 3. 節拍器音效 (木魚 / Click)
  // 使用 Square 波形加上極短的衰減，模擬清脆的敲擊聲
  metronome = new Tone.Synth({
    oscillator: { type: 'square' },
    envelope: {
      attack: 0.001,
      decay: 0.05, // 極短的衰減
      sustain: 0, // 沒有延音
      release: 0.01,
    },
  }).toDestination()
  metronome.volume.value = -12 // 節拍器音量降低

  // 等待所有的取樣音檔都從網路下載完畢再繼續
  await Tone.loaded()
}

// 鍵盤按下處理
const handleKeyDown = (e) => {
  if (!isRealtimePlaying.value) return

  const key = pianoKeys.find((k) => k.keyCode === e.code)
  if (!key || activeKeys.value.has(key.keyCode)) return

  // 視覺回饋
  activeKeys.value.add(key.keyCode)

  // 播放音符
  const noteName = Tone.Frequency(key.midi, 'midi').toNote()
  melodySynth.triggerAttack(noteName)

  // 記錄開始時間
  currentlyPlayingNotes.set(key.keyCode, {
    midi: key.midi,
    note: key.note,
    startTime: Tone.now(),
  })
}

// 鍵盤放開處理
const handleKeyUp = (e) => {
  if (!isRealtimePlaying.value) return
  const key = pianoKeys.find((k) => k.keyCode === e.code)
  if (!key) return

  activeKeys.value.delete(key.keyCode)
  const noteName = Tone.Frequency(key.midi, 'midi').toNote()
  melodySynth.triggerRelease(noteName)

  const noteInfo = currentlyPlayingNotes.get(key.keyCode)
  if (noteInfo) {
    const duration = Tone.now() - noteInfo.startTime
    const timeOffset = noteInfo.startTime - recordingStartTime

    // 只記錄在「當前小節」範圍內按下的音符
    if (timeOffset >= 0 && timeOffset < getBarDuration()) {
      currentBarNotes.push({
        midi: noteInfo.midi,
        time: timeOffset,
        duration: duration,
      })
    }
    currentlyPlayingNotes.delete(key.keyCode)
  }
}

// 計算一拍的時長(秒)
const getBeatDuration = () => {
  return 60 / realtimeBPM.value
}

// 計算一小節的時長(秒) - 4拍
const getBarDuration = () => {
  return getBeatDuration() * 4
}

// 播放節拍器聲音
const playMetronomeClick = (time, isDownbeat = false) => {
  // 下拍(第一拍)音高較高
  const pitch = isDownbeat ? 'G5' : 'C5'
  // 🌟 直接將絕對時間 (time) 餵給合成器，這是最精準的做法
  metronome.triggerAttackRelease(pitch, '64n', time)
}

// 🌟 輔助函數：將 Token IDs 轉為可讀字串，並把 Pitch 轉換為音名
const formatTokensForLog = (tokenIds) => {
  if (!tokenIds || tokenIds.length === 0) return '空序列'

  // MIDI Pitch 轉音名 (e.g. 60 -> C4)
  const pitchToNoteName = (pitch) => {
    const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    const octave = Math.floor(pitch / 12) - 1
    const note = notes[pitch % 12]
    return `${note}${octave}`
  }

  // 映射 Token 字串
  const strTokens = tokenIds.map((id) => {
    // 透過 tokenizerService 的反向字典查詢字串
    const tokenStr = tokenizerService.idToToken[id]
    if (!tokenStr) return `Unknown(${id})`

    // 如果是 Pitch，附加上音名
    if (tokenStr.startsWith('Pitch_')) {
      const pitchVal = parseInt(tokenStr.split('_')[1])
      return `${tokenStr}(${pitchToNoteName(pitchVal)})`
    }
    return tokenStr
  })

  // 為了好閱讀，每 8 個 Token 換一行，並用 | 分隔
  let output = ''
  let line = []
  for (const t of strTokens) {
    line.push(t)
    if (line.length >= 8) {
      output += line.join(' | ') + '\n'
      line = []
    }
  }
  if (line.length > 0) {
    output += line.join(' | ') + '\n'
  }

  return output.trim()
}

// AI即時生成伴奏
// AI即時生成伴奏
const generateAccompaniment = async (melodyNotes, accompNotes) => {
  try {
    // 1. 原本：傳入雙軌資料轉換的 tokens
    let inputTokens = tokenizerService.encodeBar(melodyNotes, accompNotes, realtimeBPM.value)

    // 🛑 ==========================================
    // 🛑 [測試專用區塊] 第一小節強制覆寫輸入！測試完可刪除
    // 🛑 ==========================================
    if (currentBar.value === 1) {
      console.warn('🛠️ [測試模式啟動] 第一小節強制載入硬編碼的 Token 序列！')

      // 乾淨的 Token 字串陣列 (去除了音名標註)
      const testSequence = [
        'BOS_None',
        'Bar_None',
        'Position_0',
        'Program_0',
        'Pitch_72',
        'Velocity_79',
        'Duration_1.0.4',
        'Program_1',
        'Pitch_41',
        'Velocity_79',
        'Duration_0.2.4',
        'Position_2',
        'Program_1',
        'Pitch_48',
        'Velocity_79',
        'Duration_0.2.4',
        'Position_4',
        'Program_0',
        'Pitch_69',
        'Velocity_79',
        'Duration_0.2.4',
        'Program_1',
        'Pitch_53',
        'Velocity_79',
        'Duration_0.2.4',
        'Position_6',
        'Program_0',
        'Pitch_72',
        'Velocity_79',
        'Duration_1.0.4',
        'Program_1',
        'Pitch_57',
        'Velocity_79',
        'Duration_1.0.4',
        'Position_10',
        'Program_0',
        'Pitch_76',
        'Velocity_79',
        'Duration_1.0.4',
        'Program_1',
        'Pitch_53',
        'Velocity_79',
        'Duration_0.2.4',
        'Position_12',
        'Program_1',
        'Pitch_48',
        'Velocity_79',
        'Duration_0.2.4',
        'Position_14',
        'Program_0',
        'Pitch_76',
        'Velocity_79',
        'Duration_0.2.4',
        'Program_1',
        'Pitch_45',
        'Velocity_79',
        'Duration_0.2.4',
        'EOS_None',
      ]

      // 透過字典將字串轉為數字 ID (找不到的就給 0 代表 PAD)
      inputTokens = testSequence.map((t) =>
        tokenizerService.vocab[t] !== undefined ? tokenizerService.vocab[t] : 0,
      )
    }
    // 🛑 ==========================================

    // 印出輸入給模型的 Token 序列
    console.log('\n==================================================')
    console.log(`🎹 準備輸入給模型的 Token 序列 (第 ${currentBar.value} 小節):`)
    console.log(`長度: ${inputTokens.length} tokens`)
    console.log('--------------------------------------------------')
    console.log(formatTokensForLog(inputTokens))
    console.log('==================================================\n')

    // 2. 呼叫 AI 模型推論
    const generatedTokenIds = await aiService.generateNextBar(inputTokens)

    // 印出模型算出來的 Token 序列
    console.log('\n==================================================')
    console.log(`✨ 模型生成的 Token 序列 (預測第 ${currentBar.value + 1} 小節):`)
    console.log(`長度: ${generatedTokenIds.length} tokens`)
    console.log('--------------------------------------------------')
    console.log(formatTokensForLog(generatedTokenIds))
    console.log('==================================================\n')

    // 3. 解碼成 Tone.js 可以播放的音符陣列
    const generatedNotes = tokenizerService.decodeAccompaniment(
      generatedTokenIds,
      realtimeBPM.value,
    )

    console.log('\n==================================================')
    console.log(`🎵 解碼後的伴奏音符陣列 (準備交給 Tone.js 播放):`)
    console.dir(generatedNotes)
    console.log('==================================================\n')

    return generatedNotes
  } catch (error) {
    console.error('[AI Error] 生成失敗:', error)
    return []
  }
}

// 播放伴奏
// 播放伴奏 (加入強力 Debug 監控)
// 播放伴奏 (加入強力 Debug 監控與終極防呆)
const playAccompaniment = (accompaniment, startTime) => {
  const currentNow = Tone.now()
  console.log(`\n[Play] 🕒 準備排程伴奏`)
  console.log(`   - 目標小節正拍絕對時間 (startTime): ${startTime.toFixed(3)}`)
  console.log(`   - 當前系統時間 (Tone.now): ${currentNow.toFixed(3)}`)

  if (startTime < currentNow) {
    console.error(
      `   🚨 [嚴重警告] 推論時間太久，已經錯過下一小節的正拍了！遲到了 ${(currentNow - startTime).toFixed(3)} 秒`,
    )
  }

  // 🛡️ 終極防護網：在上場前，把所有沒有 midi 值、或是 NaN 的幽靈音符強制剔除！
  const safeAccompaniment = accompaniment.filter(
    (note) => note && note.midi !== undefined && note.midi !== null && !isNaN(note.midi),
  )

  if (safeAccompaniment.length === 0) {
    console.warn('   ⚠️ [Play] 伴奏陣列是空的 (或全是被剔除的無效音符)。')
    return
  }

  if (accompaniment.length !== safeAccompaniment.length) {
    console.warn(
      `   🗑️ [Play] 成功攔截並丟棄了 ${accompaniment.length - safeAccompaniment.length} 個無效的幽靈音符！`,
    )
  }

  // 這裡改用過濾後的 safeAccompaniment 進行迴圈
  safeAccompaniment.forEach((note) => {
    const noteName = Tone.Frequency(note.midi, 'midi').toNote()
    const scheduleTime = startTime + note.time

    console.log(
      `   -> 預計播放: ${noteName.padEnd(4)} | 相對時間: ${note.time.toFixed(3)}s | 排程時間: ${scheduleTime.toFixed(3)}s`,
    )

    if (scheduleTime < Tone.now()) {
      console.warn(`      [⚠️ 延遲] ${noteName} 的排程時間在過去！這顆音符可能不會發聲。`)
    }

    if (!accSynth.loaded) {
      console.warn(`      [⚠️ 靜音原因] 鋼琴 MP3 取樣尚未下載完成，無法發聲！`)
    }

    accSynth.triggerAttackRelease(noteName, note.duration, scheduleTime, 0.8)
  })
}

// 主循環邏輯
// --- 主循環邏輯 (Sliding Window 架構) ---
let barCount = 0 // 追蹤目前進行到第幾小節
let aiSchedulerId = null // 🌟 新增：專屬 AI 的排程器 ID

const startRealtime = async () => {
  await initToneJs()

  realtimeBPM.value = 60
  Tone.Transport.bpm.value = 60
  Tone.Transport.timeSignature = 4

  isRealtimePlaying.value = true
  barCount = 0
  recordedNotes.value = []
  generationHistory.value = []
  currentBarNotes = []
  previousAccompaniment = []

  console.log('[Realtime] 開始單小節循環即時伴奏 (BPM: 60)')
  realtimeStatus.value = 'Ready to Start...'

  const beatDuration = getBeatDuration()

  // ==========================================
  // 軌道 1: 負責每一小節的「正拍 (0:0:0)」重置與節拍器
  // ==========================================
  schedulerId = Tone.Transport.scheduleRepeat(
    (time) => {
      barCount++
      currentBar.value = barCount

      // 在音訊排程當下立即清空紀錄，確保時間最精準
      currentBarNotes = []
      recordingStartTime = time

      Tone.Draw.schedule(() => {
        realtimeStatus.value =
          barCount === 1 ? 'Play Melody (Init State)' : 'Realtime Engine Active...'
      }, time)

      for (let i = 0; i < 4; i++) {
        // 算出每一拍的精準絕對時間
        const beatTime = time + i * beatDuration

        console.log(`[節拍器] 第 ${barCount} 小節 第 ${i + 1} 拍 排程時間: ${beatTime.toFixed(3)}s`)

        // 🌟 1. 音訊排程：直接呼叫合成器發聲，不使用巢狀 Transport.schedule！
        playMetronomeClick(beatTime, i === 0)

        // 🌟 2. 畫面排程：交給 Tone.Draw 對齊畫面
        Tone.Draw.schedule(() => {
          currentBeat.value = i + 1
          beatPulse.value = true
          // UI 動畫時間極短，使用 setTimeout 控制 class 是安全的
          setTimeout(() => {
            beatPulse.value = false
          }, 100)
        }, beatTime)
      }
    },
    '1m',
    '0:0:0',
  )

  // ==========================================
  // 軌道 2: 負責每一小節的「第 3.5 拍 (0:3:2)」啟動 AI 快門
  // ==========================================
  aiSchedulerId = Tone.Transport.scheduleRepeat(
    (time) => {
      console.log(`\n[Realtime] 📸 第 ${barCount} 小節 3.5拍 - 截取並觸發AI推論`)

      // 🌟 因為這個 callback 是在 3.5 拍被呼叫，`time` 就是現在這個瞬間！
      // 下一個小節的正拍，就是加上 0.5 拍 (剩餘的兩個 16 分音符時間)
      const nextBarStartTime = time + 0.5 * beatDuration

      const melodySnapshot = [...currentBarNotes]

      currentlyPlayingNotes.forEach((noteInfo) => {
        const timeOffset = noteInfo.startTime - recordingStartTime
        // 確保只抓取 3.5 拍以內的音符
        if (timeOffset >= 0 && timeOffset < 3.5 * beatDuration) {
          melodySnapshot.push({
            midi: noteInfo.midi,
            time: timeOffset,
            duration: time - noteInfo.startTime, // 截斷到 3.5 拍的當下
          })
        }
      })

      const prevAccSnapshot = [...previousAccompaniment]

      // 呼叫非同步生成
      generateAccompaniment(melodySnapshot, prevAccSnapshot).then(async (acc) => {
        previousAccompaniment = acc

        // 直接使用我們算好的完美下個正拍時間點！
        playAccompaniment(acc, nextBarStartTime)

        Tone.Draw.schedule(() => {
          generationHistory.value.push({
            bar: barCount + 1,
            message: `生成 ${acc.length} 個伴奏音符`,
          })
        }, nextBarStartTime)
      })
    },
    '1m',
    '0:3:2',
  ) // 🌟 魔法參數："0:3:2" 代表第 3 拍的第 2 個八分音符 (即 3.5 拍)

  Tone.Transport.start()
}

// --- 停止演奏 ---
const stopRealtime = () => {
  console.log('[Realtime] 停止演奏')

  isRealtimePlaying.value = false
  realtimeStatus.value = 'Engine Stopped'

  if (synth) synth.triggerRelease()
  if (melodySynth) melodySynth.releaseAll()
  if (accSynth) accSynth.releaseAll()

  currentlyPlayingNotes.clear()
  activeKeys.value.clear()

  // 🌟 確保兩個排程器都有被清除
  if (schedulerId !== null) {
    Tone.Transport.clear(schedulerId)
    schedulerId = null
  }
  if (aiSchedulerId !== null) {
    Tone.Transport.clear(aiSchedulerId)
    aiSchedulerId = null
  }

  Tone.Transport.stop()
  Tone.Transport.cancel()
}

// 監聽鍵盤事件 (在原有的 onMounted 中添加)
const originalOnMounted = onMounted
onMounted(() => {
  if (originalOnMounted) originalOnMounted()
  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('keyup', handleKeyUp)
})

const originalOnUnmounted = onUnmounted
onUnmounted(() => {
  if (originalOnUnmounted) originalOnUnmounted()
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('keyup', handleKeyUp)

  if (isRealtimePlaying.value) {
    stopRealtime()
  }

  // 清理 Tone.js 資源
  if (synth) {
    synth.dispose()
    synth = null
  }
  if (melodySynth) {
    melodySynth.dispose()
    melodySynth = null
  }
  if (accSynth) {
    accSynth.dispose()
    accSynth = null
  }
  if (metronome) {
    metronome.dispose()
    metronome = null
  }
})
</script>

<style scoped>
/* =========================================================================
   Global CSS Variables (Light Theme Premium)
========================================================================= */
.app-wrapper {
  /* CSS Variables */
  --primary-color: #4e54c8;
  --secondary-color: #8f94fb;
  --accent-color: #42b983;
  --bg-color: #f7f9fc;
  --glass-bg: rgba(255, 255, 255, 0.7);
  --glass-border: rgba(255, 255, 255, 0.3);
  --text-main: #2c3e50;
  --text-light: #7f8c8d;
  --shadow-mild: 0 4px 30px rgba(0, 0, 0, 0.05);
  --shadow-glow: 0 0 15px rgba(143, 148, 251, 0.4);
  
  /* Base Styles */
  font-family: 'Inter', sans-serif;
  color: var(--text-main);
  background-color: var(--bg-color);
  min-height: 100vh;
  margin: 0;
  padding: 0;
  overflow-x: hidden;
  transition: filter 0.3s ease;
}

h1,
h2,
h3,
h4,
h5,
h6,
.nav-title,
.btn-text {
  font-family: 'Outfit', sans-serif;
}

.app-wrapper.is-loading {
  filter: blur(2px) grayscale(20%);
}

.glass-panel {
  background: var(--glass-bg);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow-mild);
  border-radius: 16px;
  padding: 25px;
  margin-bottom: 25px;
}

.glass-container {
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(5px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
  padding: 15px;
}

.glass-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
  padding: 20px;
}

/* =========================================================================
   Loading Overlay
========================================================================= */
.global-loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.futuristic-spinner {
  position: relative;
  width: 100px;
  height: 100px;
  margin-bottom: 20px;
}

.futuristic-spinner .ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 4px solid transparent;
}

.futuristic-spinner .ring:nth-child(1) {
  border-top-color: var(--primary-color);
  animation: spinWave 1.2s linear infinite;
}
.futuristic-spinner .ring:nth-child(2) {
  width: 80%;
  height: 80%;
  top: 10%;
  left: 10%;
  border-right-color: var(--secondary-color);
  animation: spinWave 1.5s reverse infinite;
}
.futuristic-spinner .ring:nth-child(3) {
  width: 60%;
  height: 60%;
  top: 20%;
  left: 20%;
  border-bottom-color: var(--accent-color);
  animation: spinWave 0.8s linear infinite;
}

@keyframes spinWave {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.loading-text {
  font-weight: 800;
  letter-spacing: 4px;
  background: linear-gradient(
    90deg,
    var(--primary-color),
    var(--secondary-color),
    var(--accent-color)
  );
  background-size: 200% auto;
  color: transparent;
  -webkit-background-clip: text;
  background-clip: text;
  animation: gradientFlow 2s linear infinite;
}

@keyframes gradientFlow {
  to {
    background-position: 200% center;
  }
}

/* =========================================================================
   Navbar
========================================================================= */
.premium-navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 64px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  box-shadow: 0 1px 15px rgba(0, 0, 0, 0.05);
  z-index: 1000;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.nav-logo {
  width: 28px;
  height: 28px;
}

.nav-title {
  font-weight: 800;
  font-size: 20px;
  color: var(--text-main);
  letter-spacing: -0.5px;
}

.nav-menu {
  display: flex;
  gap: 5px;
}

.nav-menu button {
  background: transparent;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-light);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.nav-menu button:hover {
  background: rgba(78, 84, 200, 0.05);
  color: var(--primary-color);
}

.nav-menu button.active {
  background: var(--primary-color);
  color: white !important;
  box-shadow: 0 4px 10px rgba(78, 84, 200, 0.3);
}

/* =========================================================================
   Hero Section
========================================================================= */
.hero-section {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: radial-gradient(circle at center, #ffffff 0%, var(--bg-color) 100%);
}

#music-particles {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: auto;
}

.hero-content {
  position: relative;
  z-index: 10;
  text-align: center;
  pointer-events: none;
}

.hero-title {
  font-size: 4.5rem;
  font-weight: 900;
  line-height: 1.1;
  color: var(--text-main);
  margin-bottom: 20px;
  letter-spacing: -1.5px;
}

.text-gradient {
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color), #ff6a88);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-subtitle {
  font-size: 1.2rem;
  color: var(--text-light);
  margin-bottom: 40px;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.hero-buttons {
  display: flex;
  gap: 15px;
  justify-content: center;
  pointer-events: auto;
}

.hero-btn {
  padding: 14px 32px;
  border-radius: 30px;
  font-size: 1.1rem;
  font-weight: 700;
  cursor: pointer;
  border: none;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.primary-btn-glow {
  background: var(--text-main);
  color: white;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}
.primary-btn-glow:hover {
  transform: translateY(-2px);
  box-shadow: 0 15px 30px rgba(44, 62, 80, 0.2);
}

.secondary-btn {
  background: white;
  color: var(--text-main);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
  border: 1px solid #eee;
}
.secondary-btn:hover {
  background: #f8f9fa;
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
}

/* =========================================================================
   Workspace
========================================================================= */
.main-workspace {
  max-width: 1200px;
  margin: 100px auto 40px;
  padding: 0 20px;
}

.panel-header h2 {
  font-weight: 800;
  font-size: 1.8rem;
  margin-bottom: 20px;
  color: var(--primary-color);
  border-bottom: 2px solid rgba(78, 84, 200, 0.1);
  padding-bottom: 10px;
}

/* Controls */
.control-row {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}
.control-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.control-group.fill-width {
  flex: 1;
}
.control-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-light);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.modern-select {
  padding: 10px 15px;
  border-radius: 8px;
  border: 1px solid #ddd;
  background: #fff;
  font-family: inherit;
  font-size: 14px;
  outline: none;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
  font-weight: 500;
}
.modern-select:focus {
  border-color: var(--secondary-color);
  box-shadow: 0 0 0 3px rgba(143, 148, 251, 0.2);
}

.flex-params {
  display: flex;
  gap: 30px;
  align-items: flex-end;
}
.slider-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
}
.val-badge {
  background: var(--bg-color);
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 700;
  color: var(--primary-color);
}
.modern-range {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  background: #ddd;
  border-radius: 3px;
  outline: none;
}
.modern-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--primary-color);
  cursor: pointer;
  transition: transform 0.1s;
}
.modern-range::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.action-buttons {
  display: flex;
  gap: 10px;
  flex: 1;
  justify-content: flex-end;
}

/* Editor Area */
.modern-editor-area {
  margin-top: 25px;
  padding: 25px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.6) 100%);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 16px;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.05);
  backdrop-filter: blur(10px);
}

.modern-btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: 0.2s;
  font-family: inherit;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.btn-outline {
  background: transparent;
  border: 2px solid #ddd;
  color: var(--text-main);
}
.btn-outline:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}
.btn-outline-danger {
  background: transparent;
  border: 2px solid #ffcccc;
  color: #e74c3c;
}
.btn-outline-danger:hover {
  background: #ffe6e6;
}
.btn-primary {
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  color: white !important;
  box-shadow: 0 4px 10px rgba(78, 84, 200, 0.3);
}
.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(78, 84, 200, 0.4);
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}
.btn-large {
  padding: 14px 28px;
  font-size: 16px;
}
.w-full {
  width: 100%;
}
.btn-danger {
  background: #e74c3c;
  color: white !important;
}
.btn-info {
  background: #3498db;
  color: white !important;
}

/* Pad Editor */
.pad-grid-wrapper {
  margin-top: 20px;
}
.pad-toolbar {
  margin-bottom: 15px;
  display: flex;
  gap: 10px;
}
.pad-editor-container {
  max-height: 450px;
  overflow: auto;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.05);
}
.pad-row {
  display: flex;
  height: 32px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.03);
}
.pad-row:hover {
  background: rgba(0, 0, 0, 0.01);
}
.pad-row.is-black-key {
  background-color: rgba(0, 0, 0, 0.03);
}
.pad-label {
  position: sticky;
  left: 0;
  width: 50px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border-right: 2px solid rgba(0, 0, 0, 0.1);
  font-size: 11px;
  font-weight: 700;
  color: var(--text-light);
  z-index: 10;
}
.pad-row.is-black-key .pad-label {
  background: #f8f9fa;
}
.pad-grid-cells {
  display: flex;
}
.pad-cell {
  width: 32px;
  height: 100%;
  flex-shrink: 0;
  border-right: 1px solid rgba(0, 0, 0, 0.03);
  position: relative;
  cursor: crosshair;
}
.pad-cell:nth-child(2n) {
  border-right: 1px solid rgba(0, 0, 0, 0.06);
}
.pad-cell:nth-child(4n) {
  border-right: 2px solid rgba(0, 0, 0, 0.1);
}
.pad-cell-note-inner {
  position: absolute;
  top: 2px;
  left: 0;
  right: 0;
  bottom: 2px;
  background: linear-gradient(180deg, #5fe3a1 0%, #35a373 100%);
  border-radius: 0;
  box-shadow:
    inset 0 1px 2px rgba(255, 255, 255, 0.5),
    0 2px 5px rgba(66, 185, 131, 0.4);
  z-index: 2;
  transition:
    transform 0.1s,
    filter 0.1s;
}
.pad-cell-note-inner.cell-start {
  border-radius: 6px 0 0 6px;
  left: 2px;
}
.pad-cell-note-inner.cell-tail {
  border-radius: 0;
}
.pad-cell:hover .pad-cell-note-inner {
  filter: brightness(1.1);
}

/* VexFlow Editor */
.vexflow-container {
  margin-top: 20px;
}

.modern-vf-toolbar {
  display: flex;
  gap: 30px;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px 25px;
  background: linear-gradient(135deg, rgba(78, 84, 200, 0.03) 0%, rgba(143, 148, 251, 0.03) 100%);
  border: 1px solid rgba(78, 84, 200, 0.1);
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
}

.tool-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tool-label {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-main);
  margin-right: 5px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-family: 'Outfit', sans-serif;
}

.tool-group button {
  padding: 8px 16px;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-light);
  transition: all 0.2s ease;
  font-family: inherit;
}

.tool-group button:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
  background: rgba(78, 84, 200, 0.05);
  transform: translateY(-1px);
}

.tool-group button.active {
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  color: white !important;
  border-color: transparent;
  box-shadow: 0 4px 10px rgba(78, 84, 200, 0.3);
}

.helper-text {
  margin-top: 12px;
  font-size: 13px;
  color: var(--text-light);
  font-style: italic;
  text-align: center;
}

.staff-layout {
  display: flex;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.05);
  padding: 20px;
  min-height: 200px;
}

.fixed-clef {
  flex-shrink: 0;
  background: linear-gradient(to right, #ffffff 0%, #fafafa 100%);
  border-right: 2px solid rgba(78, 84, 200, 0.1);
  padding-right: 10px;
}

.scrollable-measures {
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0 15px;
  cursor: crosshair;
}

.scrollable-measures::-webkit-scrollbar {
  height: 8px;
}

.scrollable-measures::-webkit-scrollbar-track {
  background: #f5f5f5;
  border-radius: 4px;
}

.scrollable-measures::-webkit-scrollbar-thumb {
  background: var(--primary-color);
  border-radius: 4px;
}

.scrollable-measures::-webkit-scrollbar-thumb:hover {
  background: var(--secondary-color);
}

/* MIDI Generation Output Styling */
midi-player {
  display: block;
  width: 100%;
  margin: 15px 0;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}
midi-player::part(control-panel) {
  background: #fff;
  border-radius: 8px;
  padding: 10px 15px;
  border: 1px solid rgba(0, 0, 0, 0.05);
}
midi-player::part(play-button) {
  color: var(--primary-color);
}
midi-player::part(time-slider) {
  accent-color: var(--primary-color);
}
midi-visualizer {
  display: block;
  width: 100%;
  height: auto;
  min-height: 120px;
  background: #fff;
  border-radius: 8px;
  padding: 15px;
  box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.02);
  border: 1px solid rgba(0, 0, 0, 0.05);
  margin-bottom: 10px;
}
midi-visualizer .note {
  fill: var(--primary-color) !important;
  stroke: var(--secondary-color) !important;
}

.player-ui-card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.8) 0%, rgba(255, 255, 255, 0.5) 100%);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
  backdrop-filter: blur(10px);
  padding: 25px;
  border-radius: 16px;
}

.player-ui-card h3,
.player-ui-card h4 {
  margin-top: 0;
  margin-bottom: 15px;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Upload Controls */
.modern-file-upload {
  display: block;
  width: 100%;
  border: 2px dashed rgba(78, 84, 200, 0.3);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: var(--bg-color);
}
.modern-file-upload:hover {
  border-color: var(--primary-color);
  background: rgba(78, 84, 200, 0.02);
}
.modern-file-upload input {
  display: none;
}
.upload-content {
  padding: 40px;
  text-align: center;
}
.upload-icon {
  color: var(--primary-color);
  margin-bottom: 15px;
}
.upload-text {
  font-weight: 600;
  color: var(--text-main);
  font-size: 16px;
  font-family: 'Outfit', sans-serif;
}

/* Realtime Accompaniment */
.realtime-controls {
  margin-bottom: 25px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modern-input {
  width: 100px;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #ddd;
  font-size: 16px;
  text-align: center;
  font-weight: 600;
}
.modern-status {
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  color: white;
  display: flex;
  justify-content: space-around;
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 25px;
  box-shadow: var(--shadow-glow);
}
.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.status-item .label {
  font-size: 12px;
  opacity: 0.8;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 5px;
}
.status-item .value {
  font-size: 24px;
  font-weight: 900;
  font-family: 'Outfit', sans-serif;
}
.beat-indicator {
  background: rgba(255, 255, 255, 0.2);
  padding: 5px 15px;
  border-radius: 20px;
  transition: 0.1s;
}
.beat-indicator.pulse {
  transform: scale(1.1);
  background: white;
  color: var(--primary-color);
}
.status-text {
  color: #f1c40f;
  text-shadow: 0 0 10px rgba(241, 196, 15, 0.5);
}

/* Virtual Keyboard */
.modern-keyboard {
  display: flex;
  justify-content: center;
  gap: 4px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 12px;
}
.piano-key {
  position: relative;
  width: 60px;
  height: 180px;
  border-radius: 0 0 8px 8px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  padding-bottom: 12px;
  user-select: none;
  transition:
    transform 0.1s,
    box-shadow 0.1s;
}
.piano-key.white-key {
  background: linear-gradient(180deg, #fff 0%, #f9f9f9 100%);
  border: 1px solid #ccc;
  border-top: none;
}
.piano-key.white-key:hover {
  background: #f0f0f0;
}
.piano-key.white-key.active {
  background: linear-gradient(180deg, #5fe3a1 0%, #35a373 100%);
  transform: translateY(2px);
  color: white;
  box-shadow: inset 0 5px 10px rgba(0, 0, 0, 0.2);
}
.key-label {
  font-weight: 800;
  font-size: 14px;
  margin-bottom: 4px;
  font-family: 'Outfit', sans-serif;
}
.white-key .key-label {
  color: #333;
}
.white-key.active .key-label,
.white-key.active .key-binding {
  color: white;
}
.key-binding {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.05);
  font-weight: 600;
}

.history-logs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.panel-subtitle {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 15px;
  color: var(--text-main);
  font-family: 'Outfit', sans-serif;
}
.note-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.modern-chip {
  background: #eef2ff;
  color: #4e54c8;
  border: 1px solid #c7d2fe;
  padding: 6px 12px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 12px;
}
.log-entries {
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.modern-log {
  display: flex;
  gap: 10px;
  background: var(--bg-color);
  padding: 10px 15px;
  border-radius: 8px;
  font-size: 13px;
  font-family: 'Inter', sans-serif;
}
.log-time {
  font-weight: 700;
  width: 60px;
  flex-shrink: 0;
}
.mt-10 {
  margin-top: 10px;
}
.mt-20 {
  margin-top: 20px;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.4s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.5s ease;
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
.fade-up-enter-active,
.fade-up-leave-active {
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translateY(30px);
}
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}
.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(1, 0.5, 0.8, 1);
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(20px);
  opacity: 0;
}
</style>
