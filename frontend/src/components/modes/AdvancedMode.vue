<template>
  <section class="workspace-panel glass-panel">
    <div class="panel-header">
      <h2>MIDI Upload</h2>
    </div>

    <div class="advanced-grid-layout">
      <!-- 左側控制列 -->
      <div class="advanced-sidebar">
        <div class="upload-controls modern-upload glass-card">
          <label class="modern-file-upload">
            <input type="file" accept=".mid,.midi" @change="handleFileUpload" />
            <div class="upload-content">
              <div class="upload-icon">
                <svg
                  width="40"
                  height="40"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
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
          <button @click="loadDemoSong" class="modern-btn btn-outline btn-demo mt-10">
            🎵 Load Demo Song (如果可以)
          </button>
        </div>

        <transition name="fade-up">
          <div v-if="parsedTracks.length > 0" class="track-selection-wrapper mt-20">
            <div class="glass-card">
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

              <div class="advanced-params-group mt-20">
                <div class="control-group">
                  <label>Inference Mode:</label>
                  <select v-model="selectedInferenceMode" class="modern-select">
                    <option value="oneStage">One-Stage (Direct Generation)</option>
                    <option value="twoStage-bar">Two-Stage AR (Autoregressive)</option>
                    <option value="twoStage-nar">Two-Stage NAR (Non-Autoregressive)</option>
                    <option value="threeStage">Three-Stage (For Long Song)</option>
                  </select>
                </div>

                <div class="params-adjustment modern-params mt-20">
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
                  <div class="slider-group mt-10">
                    <label
                      >Creativity: <span class="val-badge">{{ generationCreativity }}</span></label
                    >
                    <input
                      type="range"
                      v-model.number="generationCreativity"
                      min="0.1"
                      max="2.0"
                      step="0.1"
                      class="modern-range"
                    />
                  </div>
                </div>
              </div>

              <div class="action-footer mt-20">
                <button
                  :disabled="selectedTrackIndex === '' || isGenerating"
                  @click="submitMidiFile"
                  class="modern-btn btn-primary btn-large w-full"
                >
                  <span v-if="!isGenerating">Generate Accompaniment</span>
                  <span v-else>⏳ {{ queuePosition > 0 ? `Queued #${queuePosition}` : 'Generating...' }}</span>
                </button>
              </div>
            </div>
          </div>
        </transition>
      </div>

      <!-- 右側譜面與展示區 -->
      <div class="advanced-canvas-area glass-card">
        <div class="canvas-header">
          <h3>Grand Staff Preview</h3>
          <div class="canvas-actions">
            <!-- 播放／停止鍵：樂譜出現前 disable -->
            <button
              @click="playAdvancedScope"
              :disabled="advancedGenerationHistory.length === 0"
              class="play-btn"
              :class="isPlayingAdvanced ? 'play-btn--stop' : 'play-btn--play'"
              :title="isPlayingAdvanced ? 'Stop' : 'Play'"
            >
              <!-- Play icon -->
              <svg
                v-if="!isPlayingAdvanced"
                viewBox="0 0 24 24"
                fill="currentColor"
                width="16"
                height="16"
              >
                <path d="M8 5v14l11-7z" />
              </svg>
              <!-- Stop icon -->
              <svg v-else viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
              </svg>
            </button>
            <a
              v-if="advancedResultMidiUrl"
              :href="advancedResultMidiUrl"
              :download="advancedResultDownloadName"
              class="modern-btn btn-outline btn-compact"
            >
              ↓ MIDI
            </a>
            <span v-if="advancedCurrentParams" class="params-badge">
              {{ advancedCurrentParams }}
            </span>
          </div>
        </div>

        <div class="version-controls mt-10" v-if="advancedGenerationHistory.length > 1">
          <button
            @click="prevAdvancedVersion"
            :disabled="currentAdvancedHistoryIndex === 0"
            class="modern-btn btn-outline"
          >
            ❮ Prev
          </button>
          <span
            >Version {{ currentAdvancedHistoryIndex + 1 }} /
            {{ advancedGenerationHistory.length }}</span
          >
          <button
            @click="nextAdvancedVersion"
            :disabled="currentAdvancedHistoryIndex === advancedGenerationHistory.length - 1"
            class="modern-btn btn-outline"
          >
            Next ❯
          </button>
        </div>

        <div v-if="showLengthWarning" class="length-warning mt-10">
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path
              d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
            ></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          Notice: The uploaded track exceeds 32 measures. Only the first 32 measures are previewed
          and played.
        </div>

        <div class="advanced-vexflow-wrapper mt-20" style="overflow-x: auto; overflow-y: hidden">
          <div ref="advancedVexflowContainer" class="advanced-vexflow-container"></div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
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
  StaveTie,
  Annotation,
  Barline,
} from 'vexflow'
import * as Tone from 'tone'
import { useAppState } from '../../composables/useAppState'
import { useQueueState } from '../../composables/useQueueState'
import audioService from '../../services/audioService'

const { isGenerating } = useAppState()

const rawFile = ref(null)
const rawMidiBuffer = ref(null)
const parsedTracks = ref([])
const selectedTrackIndex = ref('')
const selectedInferenceMode = ref('oneStage')
const generationComplexity = ref(0.5)
const generationCreativity = ref(1.0)

const advancedVexflowContainer = ref(null)
const advancedGenerationHistory = ref([])
const currentAdvancedHistoryIndex = ref(-1)
const isPlayingAdvanced = ref(false)
const showLengthWarning = ref(false)
const detectedKeySignature = ref(null) // e.g. 'G' or 'Bb'

// Duration step resolution: 1 step = 16th note
const STEPS_PER_MEASURE = 16
const detectedBpm = ref(120)

const diatonicScale = [
  { step: 'c/4', basePitch: 60 },
  { step: 'd/4', basePitch: 62 },
  { step: 'e/4', basePitch: 64 },
  { step: 'f/4', basePitch: 65 },
  { step: 'g/4', basePitch: 67 },
  { step: 'a/4', basePitch: 69 },
  { step: 'b/4', basePitch: 71 },
  { step: 'c/5', basePitch: 72 },
  { step: 'd/5', basePitch: 74 },
  { step: 'e/5', basePitch: 76 },
  { step: 'f/5', basePitch: 77 },
  { step: 'g/5', basePitch: 79 },
  { step: 'a/5', basePitch: 81 },
]

const advancedResultMidiUrl = computed(() => {
  if (currentAdvancedHistoryIndex.value === -1) return null
  return advancedGenerationHistory.value[currentAdvancedHistoryIndex.value]?.midiUrl
})

// Task 4: Dynamic download filename containing mode/complexity/creativity
const advancedResultDownloadName = computed(() => {
  if (currentAdvancedHistoryIndex.value === -1) return 'accompaniment.mid'
  const item = advancedGenerationHistory.value[currentAdvancedHistoryIndex.value]
  if (!item?.params) return 'accompaniment.mid'
  const { mode, complexity, creativity } = item.params
  return `accom_${mode}_c${complexity}_t${creativity}.mid`
})

// Task 4: Params display string for UI badge
const advancedCurrentParams = computed(() => {
  if (currentAdvancedHistoryIndex.value === -1) return null
  const item = advancedGenerationHistory.value[currentAdvancedHistoryIndex.value]
  if (!item?.params) return null
  const { mode, complexity, creativity } = item.params
  return `${mode} | C:${complexity} T:${creativity}`
})

const initSynth = async () => {
  await audioService.init()
}

// Task 5: shared MIDI parsing helper — extracts notes and key signature from an ArrayBuffer
const parseMidiBuffer = (arrayBuffer) => {
  const midi = new Midi(arrayBuffer)
  // Task 5: detect key signature
  const keySigs = midi.header?.keySignatures
  if (keySigs && keySigs.length > 0) {
    const ks = keySigs[0]
    let vfKey = ks.key
    if (ks.scale === 'minor' && !vfKey.endsWith('m')) vfKey += 'm'
    detectedKeySignature.value = vfKey
  } else {
    detectedKeySignature.value = null
  }

  if (midi.header?.tempos?.length > 0) {
    detectedBpm.value = midi.header.tempos[0].bpm
  } else {
    detectedBpm.value = 120
  }
  return midi
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  rawFile.value = file
  parsedTracks.value = []
  selectedTrackIndex.value = ''
  advancedGenerationHistory.value = []
  currentAdvancedHistoryIndex.value = -1
  showLengthWarning.value = false

  try {
    const arrayBuffer = await file.arrayBuffer()
    rawMidiBuffer.value = arrayBuffer
    const midi = parseMidiBuffer(arrayBuffer)
    const trackInfoList = []

    midi.tracks.forEach((track, originalIndex) => {
      if (track.notes.length > 0) {
        trackInfoList.push({
          originalIndex,
          noteCount: track.notes.length,
          instrumentName: track.instrument?.name || 'Unknown Instrument',
        })
      }
    })
    parsedTracks.value = trackInfoList
  } catch (error) {
    console.error('[Tone.js Error]', error)
    alert('Failed to parse MIDI.')
  }
}

// Task 1: load static demo song from /public/test_midis/demo.mid
const loadDemoSong = async () => {
  try {
    const response = await fetch('/test_midis/demo.mid')
    if (!response.ok) throw new Error('Demo file not found')
    const arrayBuffer = await response.arrayBuffer()
    const file = new File([arrayBuffer], '如果可以.mid', { type: 'audio/midi' })

    rawFile.value = file
    parsedTracks.value = []
    selectedTrackIndex.value = ''
    advancedGenerationHistory.value = []
    currentAdvancedHistoryIndex.value = -1
    showLengthWarning.value = false

    rawMidiBuffer.value = arrayBuffer
    const midi = parseMidiBuffer(arrayBuffer)
    const trackInfoList = []
    midi.tracks.forEach((track, originalIndex) => {
      if (track.notes.length > 0) {
        trackInfoList.push({
          originalIndex,
          noteCount: track.notes.length,
          instrumentName: track.instrument?.name || 'Unknown Instrument',
        })
      }
    })
    parsedTracks.value = trackInfoList
  } catch (error) {
    console.error('[Demo Load Error]', error)
    alert('Failed to load demo song.')
  }
}

watch(selectedTrackIndex, (newIndex) => {
  if (newIndex === '' || !rawMidiBuffer.value) return
  try {
    const originalMidi = new Midi(rawMidiBuffer.value)
    const targetTrack = originalMidi.tracks[newIndex]

    const newMelodyData = []
    targetTrack.notes.forEach((note) => {
      // Task 3: 16th note resolution — map ticks to steps (1 step = 16th note)
      // @tonejs/midi uses header.ppq (pulses per quarter note), NOT ticksPerBeat
      const ppq = originalMidi.header.ppq || 480
      const ticksPerStep = ppq / 4
      const step = Math.round(note.ticks / ticksPerStep)
      const duration = Math.max(1, Math.round(note.durationTicks / ticksPerStep))
      let accidental = ''
      if (note.name.includes('#')) accidental = '#'
      if (note.name.includes('b')) accidental = 'b'
      newMelodyData.push({ pitch: note.midi, step, duration, accidental })
    })

    advancedGenerationHistory.value = [
      {
        midiUrl: null,
        melodyData: newMelodyData,
        aiData: [],
        chords: [],
        params: null,
      },
    ]
    currentAdvancedHistoryIndex.value = 0
    nextTick(() => renderAdvancedVexFlow())
  } catch (error) {
    console.error('[Preview Error]', error)
  }
})

// ── Queue 狀態（使用共用 composable，讓 App.vue 全局遮罩也能讀取）────────────
const {
  currentJobId,
  queuePosition,
  jobProgress,
  jobStageLabel,
  estimatedWait,
  vipPasswordInput,
  vipEligible,
  vipCooldownRemaining,
  vipSubmitting,
  vipMessage,
  vipMessageType,
  resetQueueState,
  startPolling,
  stopPolling,
} = useQueueState()

let _cooldownTimer = null

// 取得最終結果並渲染
const fetchAndHandleResult = async (jobId) => {
  try {
    const res = await fetch(`/api/queue/result/${jobId}`)
    if (!res.ok) throw new Error(`result fetch failed: ${res.status}`)
    const jsonData = await res.json()
    await processMidiResult(jsonData)
  } catch (e) {
    console.error('[Queue] Result fetch error:', e)
    alert(`取得結果失敗：${e.message}`)
  } finally {
    isGenerating.value = false
    currentJobId.value = null
    resetQueueState()
  }
}

// 把 API 回傳的 jsonData 轉成樂譜資料（抽出共用邏輯）
const processMidiResult = async (jsonData) => {
  let blob
  let chordLabels = []
  if (jsonData && jsonData.midi_b64) {
    const binaryStr = atob(jsonData.midi_b64)
    const len = binaryStr.length
    const bytes = new Uint8Array(len)
    for (let i = 0; i < len; i++) bytes[i] = binaryStr.charCodeAt(i)
    blob = new Blob([bytes], { type: 'audio/midi' })
    if (jsonData.chords) chordLabels = jsonData.chords
  } else {
    console.error('[AdvancedMode] processMidiResult: midi_b64 missing in response', jsonData)
    throw new Error('後端回傳格式異常（缺少 midi_b64），請重試')
  }

  const url = URL.createObjectURL(blob)
  const arrayBuffer = await blob.arrayBuffer()
  const midi = new Midi(arrayBuffer)

  const newMelodyData = []
  const newAiData = []
  const noteTracks = midi.tracks.filter((t) => t.notes.length > 0)
  noteTracks.forEach((track, index) => {
    const targetArray = index === 0 && noteTracks.length > 1 ? newMelodyData : newAiData
    track.notes.forEach((note) => {
      const ppq = midi.header.ppq || 480
      const ticksPerStep = ppq / 4
      const step = Math.round(note.ticks / ticksPerStep)
      const duration = Math.max(1, Math.round(note.durationTicks / ticksPerStep))
      let accidental = ''
      if (note.name.includes('#')) accidental = '#'
      if (note.name.includes('b')) accidental = 'b'
      targetArray.push({ pitch: note.midi, step, duration, accidental })
    })
  })

  if (
    advancedGenerationHistory.value.length === 1 &&
    advancedGenerationHistory.value[0].aiData.length === 0
  ) {
    advancedGenerationHistory.value = []
  }

  advancedGenerationHistory.value.push({
    midiUrl: url,
    melodyData: newMelodyData,
    aiData: newAiData,
    chords: chordLabels,
    params: {
      mode: selectedInferenceMode.value,
      complexity: generationComplexity.value,
      creativity: generationCreativity.value,
    },
  })
  currentAdvancedHistoryIndex.value = advancedGenerationHistory.value.length - 1
  nextTick(() => renderAdvancedVexFlow())
}

// 插隊密碼提交
const submitVipPassword = async () => {
  if (!vipPasswordInput.value || !currentJobId.value || vipSubmitting.value) return
  vipSubmitting.value = true
  vipMessage.value = ''
  try {
    // 重新提交，帶上插隊密碼；後端會把這個 job 插到最前面
    // 但注意：我們的 job 已在佇列中，這裡採用「重新提交」並拋棄舊 job 的方式
    // 更好的做法是傳送 PATCH /api/queue/promote/{job_id} ——
    // 但為簡單起見，我們在 formData 裡帶密碼重提交，後端偵測密碼正確即插隊
    const formData = new FormData()
    formData.append('midiFile', rawFile.value)
    formData.append('targetTrackIndex', selectedTrackIndex.value)
    formData.append('mode', selectedInferenceMode.value)
    formData.append('complexity', generationComplexity.value)
    formData.append('creativity', generationCreativity.value)

    const res = await fetch('/api/generate-from-midi', {
      method: 'POST',
      body: formData,
      headers: { 'X-VIP-Password': vipPasswordInput.value },
    })
    const data = await res.json()

    if (!res.ok) {
      vipMessage.value = data.detail || 'Wrong password or cooldown active'
      vipMessageType.value = 'error'
      return
    }

    if (data.job_id) {
      if (data.vip_accepted) {
        // 切換追蹤新 job（插隊成功），取消舊 job 釋放佇列資源
        const oldJobId = currentJobId.value
        stopPolling()
        if (oldJobId) {
          fetch(`/api/queue/cancel/${oldJobId}`, { method: 'DELETE' }).catch(() => {})
        }
        currentJobId.value = data.job_id
        queuePosition.value = data.position ?? 0
        estimatedWait.value = data.estimated_wait_seconds ?? 0
        vipMessage.value = data.position === 0 ? '✅ Priority jump successful! Starting soon' : `✅ Priority jump successful! Now at position ${data.position}`
        vipMessageType.value = 'success'
        vipPasswordInput.value = ''
        startPolling(data.job_id, {
          onDone: fetchAndHandleResult,
          onError: (err) => {
            alert(`生成失敗：${err}`)
            isGenerating.value = false
          }
        })
        startVipCooldown(60)
      } else {
        vipMessage.value = 'Priority jump failed: wrong password or cooldown active'
        vipMessageType.value = 'error'
        vipSubmitting.value = false
        return  // 不切換 job，不重新 startPolling
      }
    } else {
      vipMessage.value = 'Priority jump failed, check your password'
      vipMessageType.value = 'error'
    }
  } catch (e) {
    vipMessage.value = `Network error: ${e.message}`
    vipMessageType.value = 'error'
  } finally {
    vipSubmitting.value = false
  }
}

const startVipCooldown = (seconds) => {
  vipEligible.value = false
  vipCooldownRemaining.value = seconds
  if (_cooldownTimer) clearInterval(_cooldownTimer)
  _cooldownTimer = setInterval(() => {
    vipCooldownRemaining.value -= 1
    if (vipCooldownRemaining.value <= 0) {
      clearInterval(_cooldownTimer)
      _cooldownTimer = null
      vipEligible.value = true
      vipCooldownRemaining.value = 0
    }
  }, 1000)
}

// 檢查冷卻狀態（初始化時）
const checkVipStatus = async () => {
  try {
    const res = await fetch('/api/queue/vip-check')
    const data = await res.json()
    vipEligible.value = data.eligible
    if (!data.eligible) {
      startVipCooldown(data.cooldown_remaining_seconds)
    }
  } catch (e) {
    // ignore
  }
}

const submitMidiFile = async () => {
  if (!rawFile.value || selectedTrackIndex.value === '') return
  try {
    isGenerating.value = true
    resetQueueState()

    const formData = new FormData()
    formData.append('midiFile', rawFile.value)
    formData.append('targetTrackIndex', selectedTrackIndex.value)
    formData.append('mode', selectedInferenceMode.value)
    formData.append('complexity', generationComplexity.value)
    formData.append('creativity', generationCreativity.value)

    const response = await fetch('/api/generate-from-midi', { method: 'POST', body: formData })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || 'Network response was not ok')
    }

    const data = await response.json()
    if (!data.job_id) throw new Error('後端未回傳 job_id')

    currentJobId.value = data.job_id
    queuePosition.value = data.position ?? 0
    estimatedWait.value = data.estimated_wait_seconds ?? 0
    jobProgress.value = data.progress ?? 0
    jobStageLabel.value = data.stage_label ?? 'Waiting to start...'

    // 檢查 VIP 冷卻
    await checkVipStatus()

    // 開始輪詢
    startPolling(data.job_id, {
      onDone: fetchAndHandleResult,
      onError: (err) => {
        alert(`生成失敗：${err}`)
        isGenerating.value = false
      }
    })
  } catch (error) {
    console.error('[API Error]', error)
    isGenerating.value = false
    alert(`提交失敗：${error.message}`)
  }
}

const prevAdvancedVersion = () => {
  if (currentAdvancedHistoryIndex.value > 0) {
    currentAdvancedHistoryIndex.value -= 1
    nextTick(() => renderAdvancedVexFlow())
  }
}
const nextAdvancedVersion = () => {
  if (currentAdvancedHistoryIndex.value < advancedGenerationHistory.value.length - 1) {
    currentAdvancedHistoryIndex.value += 1
    nextTick(() => renderAdvancedVexFlow())
  }
}

const renderAdvancedVexFlow = () => {
  if (
    !advancedVexflowContainer.value ||
    advancedGenerationHistory.value.length === 0 ||
    currentAdvancedHistoryIndex.value === -1
  )
    return

  const historyItem = advancedGenerationHistory.value[currentAdvancedHistoryIndex.value]
  const container = advancedVexflowContainer.value
  container.innerHTML = ''

  const melodyDataSrc = historyItem.melodyData || []
  const aiDataSrc = historyItem.aiData || []
  const chordsSrc = historyItem.chords || []
  const isGrandStaff = aiDataSrc.length > 0

  // ── 調號隱式升降記號集合 ──────────────────────────────────────────────────
  // Key: 音名字母 (lowercase), Value: '#' | 'b'
  // 屬於調號的音符不需要再標示個別升降記號
  const KEY_SIG_ACCIDENTALS = {
    // 升號大調
    G: { f: '#' },
    D: { f: '#', c: '#' },
    A: { f: '#', c: '#', g: '#' },
    E: { f: '#', c: '#', g: '#', d: '#' },
    B: { f: '#', c: '#', g: '#', d: '#', a: '#' },
    'F#': { f: '#', c: '#', g: '#', d: '#', a: '#', e: '#' },
    'C#': { f: '#', c: '#', g: '#', d: '#', a: '#', e: '#', b: '#' },
    // 降號大調
    F: { b: 'b' },
    Bb: { b: 'b', e: 'b' },
    Eb: { b: 'b', e: 'b', a: 'b' },
    Ab: { b: 'b', e: 'b', a: 'b', d: 'b' },
    Db: { b: 'b', e: 'b', a: 'b', d: 'b', g: 'b' },
    Gb: { b: 'b', e: 'b', a: 'b', d: 'b', g: 'b', c: 'b' },
    Cb: { b: 'b', e: 'b', a: 'b', d: 'b', g: 'b', c: 'b', f: 'b' },
  }
  // 取調號（去掉小調後綴 m），若查不到則空 map
  const keySigAcc = detectedKeySignature.value
    ? KEY_SIG_ACCIDENTALS[detectedKeySignature.value.replace('m', '')] || {}
    : {}
  // 判斷某音是否已被調號涵蓋（不需額外標記）
  const isCoveredByKeySig = (letter, acc) => acc !== '' && keySigAcc[letter.toLowerCase()] === acc

  // 判斷調號是否是降號系
  const isFlatKey =
    detectedKeySignature.value &&
    ['F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Cb', 'Dm', 'Gm', 'Cm', 'Fm', 'Bbm', 'Ebm', 'Abm'].includes(
      detectedKeySignature.value,
    )

  // 根據調號優先選擇同音異名 (Enharmonic)
  const getEnharmonicNote = (pitch) => {
    const pc = pitch % 12
    const octave = Math.floor(pitch / 12) - 1

    // 無升降的自然音
    const naturalMap = {
      0: { letter: 'c', acc: '' },
      2: { letter: 'd', acc: '' },
      4: { letter: 'e', acc: '' },
      5: { letter: 'f', acc: '' },
      7: { letter: 'g', acc: '' },
      9: { letter: 'a', acc: '' },
      11: { letter: 'b', acc: '' },
    }

    if (naturalMap[pc] !== undefined) {
      return {
        vfKey: `${naturalMap[pc].letter}/${octave}`,
        letter: naturalMap[pc].letter,
        acc: '',
      }
    }

    // 變化音：1, 3, 6, 8, 10
    if (isFlatKey) {
      const flatMap = {
        1: { letter: 'd', acc: 'b' },
        3: { letter: 'e', acc: 'b' },
        6: { letter: 'g', acc: 'b' },
        8: { letter: 'a', acc: 'b' },
        10: { letter: 'b', acc: 'b' },
      }
      return {
        vfKey: `${flatMap[pc].letter}b/${octave}`,
        letter: flatMap[pc].letter,
        acc: 'b',
      }
    } else {
      const sharpMap = {
        1: { letter: 'c', acc: '#' },
        3: { letter: 'd', acc: '#' },
        6: { letter: 'f', acc: '#' },
        8: { letter: 'g', acc: '#' },
        10: { letter: 'a', acc: '#' },
      }
      return {
        vfKey: `${sharpMap[pc].letter}#/${octave}`,
        letter: sharpMap[pc].letter,
        acc: '#',
      }
    }
  }

  // 根據調號決定和弦名稱要是升號還是降號
  const getEnharmonicChord = (chord) => {
    if (!chord || chord === 'N' || chord === 'X') return chord

    // 若是降號系調號，將升號根音轉化為同音異名的降號
    if (isFlatKey) {
      let root = chord.slice(0, 1)
      let rest = chord.slice(1)
      if (chord.length > 1 && chord[1] === '#') {
        root = chord.slice(0, 2)
        rest = chord.slice(2)
      }

      const sharpToFlatMap = {
        'C#': 'Db',
        'D#': 'Eb',
        'F#': 'Gb',
        'G#': 'Ab',
        'A#': 'Bb',
      }

      if (sharpToFlatMap[root]) {
        return sharpToFlatMap[root] + rest
      }
    } else {
      // 升號系或無調號（預設）
      let root = chord.slice(0, 1)
      let rest = chord.slice(1)
      if (chord.length > 1 && chord[1] === 'b') {
        root = chord.slice(0, 2)
        rest = chord.slice(2)
      }

      const flatToSharpMap = {
        Db: 'C#',
        Eb: 'D#',
        Gb: 'F#',
        Ab: 'G#',
        Bb: 'A#',
      }

      if (flatToSharpMap[root]) {
        return flatToSharpMap[root] + rest
      }
    }
    return chord
  }

  // 💡 問題 3 修復：根據所有音符的所在位置，動態計算「整份樂譜的總小節數」
  const maxMelodyStep =
    melodyDataSrc.length > 0 ? Math.max(...melodyDataSrc.map((n) => n.step + n.duration)) : 0
  const maxAiStep =
    aiDataSrc.length > 0 ? Math.max(...aiDataSrc.map((n) => n.step + n.duration)) : 0
  const maxStep = Math.max(maxMelodyStep, maxAiStep)

  const computedTotalMeasures = Math.max(1, Math.ceil(maxStep / STEPS_PER_MEASURE))
  if (computedTotalMeasures > 32) {
    showLengthWarning.value = true
  } else {
    showLengthWarning.value = false
  }
  const TOTAL_MEASURES = Math.min(computedTotalMeasures, 32)

  const scale = 0.85 // 縮小比例以適配一行 4 小節
  const logicalAvailableWidth = (container.clientWidth - 20) / scale
  const MEASURE_WIDTH = 300
  const CLEF_WIDTH = 140
  const ROW_HEIGHT = isGrandStaff ? 280 : 180

  const MEASURES_PER_ROW = Math.max(
    1,
    Math.floor((logicalAvailableWidth - CLEF_WIDTH) / MEASURE_WIDTH),
  )
  const TOTAL_ROWS = Math.ceil(TOTAL_MEASURES / MEASURES_PER_ROW)

  const renderer = new Renderer(container, Renderer.Backends.SVG)
  // 🌟 優化：增加 10px 緩衝區確保最後一根小節線不被切掉
  const canvasWidth =
    (CLEF_WIDTH + Math.min(TOTAL_MEASURES, MEASURES_PER_ROW) * MEASURE_WIDTH + 10) * scale
  renderer.resize(canvasWidth, TOTAL_ROWS * ROW_HEIGHT * scale)
  const context = renderer.getContext()
  context.scale(scale, scale)

  let globalMeasureIndex = 0

  for (let row = 0; row < TOTAL_ROWS; row++) {
    if (globalMeasureIndex >= TOTAL_MEASURES) break

    const rowY = row * ROW_HEIGHT
    // 繪製每行開頭的譜號與調號
    const trebleClefStave = new Stave(25, rowY + 40, CLEF_WIDTH - 25)
      .addClef('treble')
      .setContext(context)
    if (detectedKeySignature.value) trebleClefStave.addKeySignature(detectedKeySignature.value)
    if (row === 0) trebleClefStave.addTimeSignature('4/4')

    if (isGrandStaff) {
      const bassClefStave = new Stave(25, rowY + 140, CLEF_WIDTH - 25)
        .addClef('bass')
        .setContext(context)
      if (detectedKeySignature.value) bassClefStave.addKeySignature(detectedKeySignature.value)
      if (row === 0) bassClefStave.addTimeSignature('4/4')

      // 🌟 同步拍號起點
      const startX = Math.max(trebleClefStave.getNoteStartX(), bassClefStave.getNoteStartX())
      trebleClefStave.setNoteStartX(startX)
      bassClefStave.setNoteStartX(startX)

      // 隱藏末端直線，使與小節自然銜接
      trebleClefStave.setEndBarType(Barline.type.NONE)
      bassClefStave.setEndBarType(Barline.type.NONE)

      trebleClefStave.draw()
      bassClefStave.draw()

      new StaveConnector(trebleClefStave, bassClefStave)
        .setType(StaveConnector.type.BRACE)
        .setContext(context)
        .draw()
      new StaveConnector(trebleClefStave, bassClefStave)
        .setType(StaveConnector.type.SINGLE_LEFT)
        .setContext(context)
        .draw()
    } else {
      trebleClefStave.setEndBarType(Barline.type.NONE)
      trebleClefStave.draw()
    }

    let currentX = CLEF_WIDTH

    for (let m = 0; m < MEASURES_PER_ROW; m++) {
      if (globalMeasureIndex >= TOTAL_MEASURES) break

      const isLastMeasureOfRow =
        m === MEASURES_PER_ROW - 1 || globalMeasureIndex === TOTAL_MEASURES - 1
      const isVeryLastMeasure = globalMeasureIndex === TOTAL_MEASURES - 1

      const trebleStave = new Stave(currentX, rowY + 40, MEASURE_WIDTH).setContext(context)
      let bassStave = null
      if (isGrandStaff) {
        bassStave = new Stave(currentX, rowY + 140, MEASURE_WIDTH).setContext(context)
      }

      // 🌟 同步起點：確保高低音軌的第一拍音符絕對對齊
      if (isGrandStaff) {
        const startX = Math.max(trebleStave.getNoteStartX(), bassStave.getNoteStartX())
        trebleStave.setNoteStartX(startX)
        bassStave.setNoteStartX(startX)
      }

      // 🌟 第一小節隱藏左側小節線，與譜號區域無縫對接
      if (m === 0) {
        trebleStave.setBegBarType(Barline.type.NONE)
        if (bassStave) bassStave.setBegBarType(Barline.type.NONE)
      }

      // 💡 修復 2：明確指定小節右側的線條
      if (isVeryLastMeasure) {
        trebleStave.setEndBarType(Barline.type.END)
        if (bassStave) bassStave.setEndBarType(Barline.type.END)
      } else if (isLastMeasureOfRow) {
        trebleStave.setEndBarType(Barline.type.SINGLE)
        if (bassStave) bassStave.setEndBarType(Barline.type.SINGLE)
      }

      trebleStave.draw()
      if (bassStave) bassStave.draw()

      const startStep = globalMeasureIndex * STEPS_PER_MEASURE
      const endStep = (globalMeasureIndex + 1) * STEPS_PER_MEASURE

      // Task 2: chord annotation — range-based lookup per beat
      // Each beat = STEPS_PER_MEASURE/4 steps (4 steps at 16th resolution)
      const STEPS_PER_BEAT = STEPS_PER_MEASURE / 4
      const chordAnnotationMap = new Map() // beatStartStep → chordLabel
      const measureChords = Array.isArray(chordsSrc[globalMeasureIndex])
        ? chordsSrc[globalMeasureIndex]
        : []
      if (measureChords.length > 0) {
        let prevChord = ''
        for (let beat = 0; beat < measureChords.length; beat++) {
          let chord = measureChords[beat] || ''
          if (!chord || chord === 'N') continue
          chord = getEnharmonicChord(chord)
          const beatStartStep = startStep + beat * STEPS_PER_BEAT
          if (beat === 0 || chord !== prevChord) {
            chordAnnotationMap.set(beatStartStep, chord)
            prevChord = chord
          }
        }
      }

      // Helper: find the chord annotation for a given note step (range lookup)
      const getChordAt = (step) => {
        // Find the last beatStartStep <= step that has an annotation
        let bestKey = null
        for (const [k] of chordAnnotationMap) {
          if (k <= step && (bestKey === null || k > bestKey)) bestKey = k
        }
        // Only show annotation on the exact beat boundary note
        return chordAnnotationMap.has(step) ? chordAnnotationMap.get(step) : null
      }

      // ==================== 繪製高音譜 ====================
      let trebleVfNotes = []
      let trebleStep = startStep
      while (trebleStep < endStep) {
        const foundNote = melodyDataSrc.find((n) => n.step === trebleStep)
        if (foundNote) {
          let renderDur = Math.min(foundNote.duration, endStep - trebleStep)
          const needsTie = foundNote.duration > endStep - trebleStep
          let vexTicks = 1
          let durStr = '16'
          let isDotted = false
          if (renderDur >= 16) {
            durStr = 'w'
            vexTicks = 16
          } else if (renderDur >= 12) {
            durStr = 'hd'
            isDotted = true
            vexTicks = 12
          } else if (renderDur >= 8) {
            durStr = 'h'
            vexTicks = 8
          } else if (renderDur >= 6) {
            durStr = 'qd'
            isDotted = true
            vexTicks = 6
          } else if (renderDur >= 4) {
            durStr = 'q'
            vexTicks = 4
          } else if (renderDur >= 3) {
            durStr = '8d'
            isDotted = true
            vexTicks = 3
          } else if (renderDur >= 2) {
            durStr = '8'
            vexTicks = 2
          } else {
            durStr = '16'
            vexTicks = 1
          }

          const { vfKey, letter, acc } = getEnharmonicNote(foundNote.pitch)
          const staveNote = new StaveNote({ clef: 'treble', keys: [vfKey], duration: durStr })
          // 加升降記號前先判斷是否已被調號涵蓋
          if (acc && !isCoveredByKeySig(letter, acc)) staveNote.addModifier(new Accidental(acc))
          if (isDotted) staveNote.addModifier(new Dot(0), 0)

          // chord annotation via range lookup
          const chordAtStep = getChordAt(trebleStep)
          if (chordAtStep) {
            staveNote.addModifier(
              new Annotation(chordAtStep)
                .setFont('Arial', 12, 'bold')
                .setVerticalJustification(Annotation.VerticalJustify.TOP),
            )
          }
          trebleVfNotes.push({
            staveNote,
            needsTie,
            pitch: foundNote.pitch,
            accidental: foundNote.accidental,
            vfKey,
          })
          trebleStep += vexTicks
        } else {
          // rests: use quarter rest every 4 steps, 8th every 2, 16th every 1
          let restNote
          if (
            trebleStep % 4 === 0 &&
            !melodyDataSrc.find((n) => n.step > trebleStep && n.step < trebleStep + 4) &&
            trebleStep + 4 <= endStep
          ) {
            restNote = new StaveNote({ clef: 'treble', keys: ['b/4'], duration: 'qr' })
            trebleStep += 4
          } else if (
            trebleStep % 2 === 0 &&
            !melodyDataSrc.find((n) => n.step === trebleStep + 1) &&
            trebleStep + 1 < endStep
          ) {
            restNote = new StaveNote({ clef: 'treble', keys: ['b/4'], duration: '8r' })
            trebleStep += 2
          } else {
            restNote = new StaveNote({ clef: 'treble', keys: ['b/4'], duration: '16r' })
            trebleStep += 1
          }
          if (chordAnnotationMap.has(startStep) && trebleVfNotes.length === 0) {
            restNote.addModifier(
              new Annotation(chordAnnotationMap.get(startStep))
                .setFont('Arial', 12, 'bold')
                .setVerticalJustification(Annotation.VerticalJustify.TOP),
            )
          }
          trebleVfNotes.push({ staveNote: restNote, needsTie: false })
        }
      }

      const trebleVoice = new Voice({ num_beats: 4, beat_value: 4 })
        .setStrict(false)
        .addTickables(trebleVfNotes.map((n) => n.staveNote))

      // ==================== 繪製低音譜 ====================
      let bassVoice = null
      if (isGrandStaff) {
        let bassVfNotes = []
        let bassStep = startStep
        while (bassStep < endStep) {
          const notesAtStep = aiDataSrc
            .filter((n) => n.step === bassStep)
            .sort((a, b) => a.pitch - b.pitch)
          if (notesAtStep.length > 0) {
            // 🌟 核心優化：增加視覺截斷偵測，防止長音符遮擋後續音符
            const nextNote = aiDataSrc.find((n) => n.step > bassStep && n.step < endStep)
            const maxAllowed = nextNote ? nextNote.step - bassStep : endStep - bassStep
            let renderDur = Math.min(notesAtStep[0].duration, maxAllowed)

            let vexTicks = 1
            let durStr = '16'
            let isDotted = false
            if (renderDur >= 16) {
              durStr = 'w'
              vexTicks = 16
            } else if (renderDur >= 12) {
              durStr = 'hd'
              isDotted = true
              vexTicks = 12
            } else if (renderDur >= 8) {
              durStr = 'h'
              vexTicks = 8
            } else if (renderDur >= 6) {
              durStr = 'qd'
              isDotted = true
              vexTicks = 6
            } else if (renderDur >= 4) {
              durStr = 'q'
              vexTicks = 4
            } else if (renderDur >= 3) {
              durStr = '8d'
              isDotted = true
              vexTicks = 3
            } else if (renderDur >= 2) {
              durStr = '8'
              vexTicks = 2
            } else {
              durStr = '16'
              vexTicks = 1
            }

            const keys = []
            const accs = []
            notesAtStep.forEach((n) => {
              const { vfKey, letter, acc } = getEnharmonicNote(n.pitch)
              keys.push(vfKey)
              accs.push(acc)
            })

            const sn = new StaveNote({
              clef: 'bass',
              keys: keys.length ? keys : ['c/3'],
              duration: durStr,
            })
            accs.forEach((a, idx) => {
              const letter = keys[idx]?.[0] || ''
              if (a && !isCoveredByKeySig(letter, a)) sn.addModifier(new Accidental(a), idx)
            })
            if (isDotted) sn.addModifier(new Dot(0), 0)
            sn.setStyle({ fillStyle: '#8f94fb', strokeStyle: '#8f94fb' })
            bassVfNotes.push(sn)
            bassStep += vexTicks
          } else {
            let rNote
            if (
              bassStep % 4 === 0 &&
              !aiDataSrc.find((n) => n.step > bassStep && n.step < bassStep + 4) &&
              bassStep + 4 <= endStep
            ) {
              rNote = new StaveNote({ clef: 'bass', keys: ['d/3'], duration: 'qr' })
              bassStep += 4
            } else if (
              bassStep % 2 === 0 &&
              !aiDataSrc.find((n) => n.step === bassStep + 1) &&
              bassStep + 1 < endStep
            ) {
              rNote = new StaveNote({ clef: 'bass', keys: ['d/3'], duration: '8r' })
              bassStep += 2
            } else {
              rNote = new StaveNote({ clef: 'bass', keys: ['d/3'], duration: '16r' })
              bassStep += 1
            }
            bassVfNotes.push(rNote)
          }
        }
        bassVoice = new Voice({ num_beats: 4, beat_value: 4 })
          .setStrict(false)
          .addTickables(bassVfNotes)
      }

      // ==================== 統一格式化 (不使用 joinVoices 以防止位移) ====================
      const voicesToFormat = [trebleVoice]
      if (bassVoice) voicesToFormat.push(bassVoice)

      const formatter = new Formatter()
      trebleVoice.setStave(trebleStave)
      if (bassVoice) bassVoice.setStave(bassStave)

      formatter.format(voicesToFormat, MEASURE_WIDTH - 40, { align_rests: true })

      trebleVoice.draw(context, trebleStave)
      if (bassVoice) {
        bassVoice.draw(context, bassStave)

        if (isLastMeasureOfRow) {
          const connectorType = isVeryLastMeasure
            ? StaveConnector.type.BOLD_DOUBLE_RIGHT
            : StaveConnector.type.SINGLE_RIGHT
          new StaveConnector(trebleStave, bassStave)
            .setType(connectorType)
            .setContext(context)
            .draw()
        }
      }

      // ==================== 連結線 (Tie) 跨小節 ====================
      trebleVfNotes.forEach((item, idx) => {
        if (!item.needsTie) return
        // The next measure's first note for this pitch should get a tie
        // We store pending ties to be resolved in next measure iteration
        // For simplicity: draw tie from this note to off-stave (open tie)
        try {
          const tie = new StaveTie({
            first_note: item.staveNote,
            last_note: null,
            first_indices: [0],
            last_indices: [0],
          })
          tie.setContext(context).draw()
        } catch (e) {
          /* tie drawing is best-effort */
        }
      })

      currentX += MEASURE_WIDTH
      globalMeasureIndex++
    }
  }
}

const playAdvancedScope = async () => {
  // 若正在播放，則停止
  if (isPlayingAdvanced.value) {
    audioService.stopAll()
    Tone.Transport.stop()
    Tone.Transport.cancel()
    isPlayingAdvanced.value = false
    return
  }

  if (advancedGenerationHistory.value.length === 0 || currentAdvancedHistoryIndex.value === -1)
    return
  const historyItem = advancedGenerationHistory.value[currentAdvancedHistoryIndex.value]

  await initSynth()
  audioService.stopAll()
  Tone.Transport.cancel()

  Tone.Transport.bpm.value = detectedBpm.value
  const stepTime = Tone.Time('16n').toSeconds()

  // 計算這份樂譜實際需要的步數
  const melMax =
    historyItem.melodyData?.length > 0
      ? Math.max(...historyItem.melodyData.map((n) => n.step + n.duration))
      : 0
  const aiMax =
    historyItem.aiData?.length > 0
      ? Math.max(...historyItem.aiData.map((n) => n.step + n.duration))
      : 0
  const actualMaxSteps = Math.max(melMax, aiMax)

  // 長度限制為 32 小節，或實際結束點（取較小者），至少播 1 拍避免錯誤
  const playMaxSteps = Math.max(1, Math.min(actualMaxSteps, 32 * 16))

  if (historyItem.melodyData) {
    historyItem.melodyData
      .filter((n) => n.step < playMaxSteps)
      .forEach((n) => {
        Tone.Transport.schedule(
          (time) =>
            audioService.melodySynth.triggerAttackRelease(
              Tone.Frequency(n.pitch, 'midi').toNote(),
              n.duration * stepTime,
              time,
            ),
          n.step * stepTime,
        )
      })
  }
  if (historyItem.aiData) {
    historyItem.aiData
      .filter((n) => n.step < playMaxSteps)
      .forEach((n) => {
        Tone.Transport.schedule(
          (time) =>
            audioService.accSynth.triggerAttackRelease(
              Tone.Frequency(n.pitch, 'midi').toNote(),
              n.duration * stepTime,
              time,
            ),
          n.step * stepTime,
        )
      })
  }

  isPlayingAdvanced.value = true
  Tone.Transport.schedule((time) => {
    // Web Audio 回呼在獨立執行緒執行，透過 nextTick 確保 Vue 響應式更新在主執行緒進行
    nextTick(() => {
      isPlayingAdvanced.value = false
    })
    Tone.Transport.stop()
    Tone.Transport.cancel()
  }, playMaxSteps * stepTime)
  Tone.Transport.start()
}

let resizeTimeout = null
const handleResize = () => {
  if (resizeTimeout) clearTimeout(resizeTimeout)
  resizeTimeout = setTimeout(() => {
    if (advancedVexflowContainer.value && currentAdvancedHistoryIndex.value !== -1) {
      renderAdvancedVexFlow()
    }
  }, 200) // 延遲 200ms 避免拉動視窗時狂暴重繪
}

// ── BroadcastChannel：接收來自 App.vue 全局遮罩的 VIP 插隊請求 ───────────────
let _vipChannel = null

onMounted(async () => {
  await initSynth()
  window.addEventListener('resize', handleResize)
  _vipChannel = new BroadcastChannel('vip-submit')
  _vipChannel.onmessage = (e) => {
    // 必須檢查 jobId，確保只有發起插隊的該任務會處理回應
    if (e.data?.password && e.data?.jobId === currentJobId.value) {
      vipPasswordInput.value = e.data.password
      submitVipPassword()
    }
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  audioService.stopAll()
  isPlayingAdvanced.value = false
  stopPolling()
  if (_cooldownTimer) { clearInterval(_cooldownTimer); _cooldownTimer = null }
  if (_vipChannel) { _vipChannel.close(); _vipChannel = null }
})
</script>

<style scoped>
/* ── Outer panel ── */
.glass-panel {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05);
  border-radius: 20px;
  padding: 28px;
  margin-bottom: 25px;
}

/* ── Panel header ── */
.panel-header h2 {
  font-family: 'Outfit', sans-serif;
  font-weight: 800;
  font-size: 1.8rem;
  margin-bottom: 22px;
  background: linear-gradient(135deg, #4e54c8, #8f94fb);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  border-bottom: 2px solid rgba(78, 84, 200, 0.1);
  padding-bottom: 12px;
}

/* ── Layout ── */
.advanced-grid-layout {
  display: flex;
  gap: 22px;
  align-items: flex-start;
}
.advanced-sidebar {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Glass card (sidebar panels) ── */
.glass-card {
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.95) 0%, rgba(247, 249, 252, 0.88) 100%);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.85);
  box-shadow:
    0 6px 24px rgba(78, 84, 200, 0.05),
    0 1px 4px rgba(0, 0, 0, 0.03);
}

/* ── Upload zone ── */
.modern-file-upload {
  display: block;
  width: 100%;
  border: 2px dashed rgba(78, 84, 200, 0.25);
  border-radius: 14px;
  cursor: pointer;
  transition:
    border-color 0.2s,
    background 0.2s,
    box-shadow 0.2s;
  background: rgba(248, 249, 252, 0.8);
  box-sizing: border-box;
}
.modern-file-upload:hover {
  border-color: rgba(78, 84, 200, 0.6);
  background: rgba(78, 84, 200, 0.03);
  box-shadow: 0 4px 16px rgba(78, 84, 200, 0.08);
}
.modern-file-upload input {
  display: none;
}
.upload-content {
  padding: 36px 20px;
  text-align: center;
}
.upload-icon {
  color: #4e54c8;
  margin-bottom: 14px;
  opacity: 0.85;
}
.upload-text {
  font-family: 'Outfit', sans-serif;
  font-weight: 600;
  color: #4e54c8;
  font-size: 14px;
  opacity: 0.8;
}

/* ── Labels ── */
.control-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.control-group.fill-width {
  flex: 1;
}
.control-group label {
  font-family: 'Outfit', sans-serif;
  font-size: 11px;
  font-weight: 700;
  color: #aab4c4;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* ── Select ── */
.modern-select {
  font-family: 'Outfit', sans-serif;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1.5px solid rgba(78, 84, 200, 0.15);
  background: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  font-weight: 600;
  color: #4e54c8;
  outline: none;
  cursor: pointer;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%234e54c8' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 34px;
  box-shadow: 0 2px 8px rgba(78, 84, 200, 0.06);
  width: 100%;
}
.modern-select:hover,
.modern-select:focus {
  border-color: rgba(78, 84, 200, 0.4);
  box-shadow: 0 4px 16px rgba(78, 84, 200, 0.12);
}

/* ── Range slider ── */
.modern-range {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 5px;
  background: linear-gradient(to right, #4e54c8, #8f94fb);
  border-radius: 3px;
  outline: none;
}
.modern-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  border: 2.5px solid #4e54c8;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(78, 84, 200, 0.25);
  transition:
    transform 0.15s,
    box-shadow 0.15s;
}
.modern-range::-webkit-slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 4px 12px rgba(78, 84, 200, 0.35);
}
.slider-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}
.slider-group label {
  font-family: 'Outfit', sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #7f8c8d;
  text-transform: none;
  letter-spacing: 0;
}
.val-badge {
  background: rgba(78, 84, 200, 0.08);
  padding: 2px 9px;
  border-radius: 20px;
  font-weight: 700;
  font-size: 13px;
  color: #4e54c8;
  margin-left: 4px;
}

/* ── Buttons ── */
.modern-btn {
  font-family: 'Outfit', sans-serif;
  padding: 10px 22px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  border: none;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease,
    opacity 0.15s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 0.1px;
}
.modern-btn:not(:disabled):active {
  transform: scale(0.97);
}

/* Primary */
.btn-primary {
  background: linear-gradient(135deg, #4e54c8 0%, #8f94fb 100%);
  color: #fff !important;
  box-shadow: 0 4px 16px rgba(78, 84, 200, 0.28);
}
.btn-primary:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(78, 84, 200, 0.36);
}
.btn-primary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* Info / Play */
.btn-info {
  background: linear-gradient(135deg, #4e54c8 0%, #8f94fb 100%);
  color: #fff !important;
  box-shadow: 0 4px 14px rgba(78, 84, 200, 0.3);
}
.btn-info:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px rgba(78, 84, 200, 0.4);
}

/* Outline */
.btn-outline {
  background: transparent;
  border: 1.5px solid rgba(78, 84, 200, 0.2);
  color: #4e54c8;
  box-shadow: none;
}
.btn-outline:not(:disabled):hover {
  background: rgba(78, 84, 200, 0.05);
  border-color: rgba(78, 84, 200, 0.45);
}
.btn-compact {
  padding: 6px 12px !important;
  font-size: 12px !important;
  border-radius: 20px !important;
  letter-spacing: 0.3px;
}
.btn-outline:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* Demo song button */
.btn-demo {
  width: 100%;
  box-sizing: border-box;
  font-size: 13px !important;
  padding: 9px 14px !important;
  border-radius: 10px !important;
  justify-content: center;
  gap: 6px;
  border-style: dashed !important;
  opacity: 0.85;
}
.btn-demo:hover {
  opacity: 1;
}

/* Params badge shown next to download button */
.params-badge {
  font-family: 'Outfit', sans-serif;
  font-size: 11px;
  font-weight: 700;
  color: #8f94fb;
  background: rgba(78, 84, 200, 0.07);
  border: 1px solid rgba(78, 84, 200, 0.15);
  border-radius: 20px;
  padding: 3px 10px;
  white-space: nowrap;
  letter-spacing: 0.2px;
}

.btn-large {
  padding: 13px 28px;
  font-size: 15px;
}
.w-full {
  width: 100%;
  box-sizing: border-box;
}

/* ── Play button ── */
.play-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
  flex-shrink: 0;
}
.play-btn--play {
  background: linear-gradient(135deg, #4e54c8 0%, #8f94fb 100%);
  color: #fff;
  box-shadow: 0 4px 14px rgba(78, 84, 200, 0.35);
}
.play-btn--play:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px rgba(78, 84, 200, 0.45);
}
.play-btn--stop {
  background: linear-gradient(135deg, #ff6a88 0%, #ff4757 100%);
  color: #fff;
  box-shadow: 0 4px 14px rgba(255, 71, 87, 0.35);
}
.play-btn--stop:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px rgba(255, 71, 87, 0.45);
}
.play-btn:disabled {
  background: #e0e4f0;
  color: #b0b8d0;
  box-shadow: none;
  cursor: not-allowed;
}

/* ── Canvas area ── */
.advanced-canvas-area {
  flex: 1;
  min-width: 0;
  padding: 22px;
  position: relative;
}
.canvas-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(78, 84, 200, 0.08);
}
.canvas-header h3 {
  font-family: 'Outfit', sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
}
.canvas-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.advanced-vexflow-container {
  overflow-x: auto;
  overflow-y: hidden;
  border-radius: 14px;
  padding: 16px 12px;
  background: #fff;
  border: 1px solid rgba(78, 84, 200, 0.06);
  box-shadow: 0 2px 16px rgba(78, 84, 200, 0.05);
  display: flex;
  justify-content: center;
}

/* ── Version controls ── */
.version-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
}
.version-controls span {
  font-family: 'Outfit', sans-serif;
  font-size: 13px;
  font-weight: 700;
  color: #7f8c8d;
  margin: 0 12px;
}

/* ── Spacing helpers ── */
.mt-20 {
  margin-top: 20px;
}
.mt-10 {
  margin-top: 10px;
}
.mr-10 {
  margin-right: 10px;
}

/* ── Fade-up transition ── */
.fade-up-enter-active {
  transition:
    opacity 0.3s ease,
    transform 0.3s ease;
}
.fade-up-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

/* ── Warning Banner ── */
.length-warning {
  background: rgba(255, 171, 0, 0.1);
  color: #d97706;
  border: 1px solid rgba(255, 171, 0, 0.3);
  padding: 10px 16px;
  border-radius: 10px;
  font-family: 'Outfit', sans-serif;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 4px 12px rgba(255, 171, 0, 0.05);
}

/* ── Queue Status Panel ── */
.queue-status-panel {
  margin-top: 14px;
  padding: 16px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: 14px;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 24px rgba(99, 102, 241, 0.1);
  font-family: 'Outfit', sans-serif;
}

.queue-panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.queue-icon {
  font-size: 18px;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.queue-title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
}

.queue-badge {
  font-size: 12px;
  font-weight: 700;
  color: #818cf8;
  background: rgba(99, 102, 241, 0.15);
  border: 1px solid rgba(99, 102, 241, 0.3);
  padding: 2px 8px;
  border-radius: 20px;
  white-space: nowrap;
}

/* Progress Track */
.queue-progress-track {
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 6px;
  position: relative;
}

.queue-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #818cf8, #6366f1, #a78bfa);
  border-radius: 999px;
  transition: width 0.5s ease;
  min-width: 4px;
}

/* 排隊等待中：跑馬燈動畫 */
.progress-pulsing {
  background: linear-gradient(
    90deg,
    rgba(129, 140, 248, 0.4) 0%,
    rgba(99, 102, 241, 0.9) 40%,
    rgba(167, 139, 250, 0.9) 60%,
    rgba(129, 140, 248, 0.4) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.8s linear infinite;
  width: 100% !important;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.queue-stage-label {
  font-size: 11px;
  color: rgba(148, 163, 184, 0.85);
  font-weight: 500;
  letter-spacing: 0.01em;
}

/* ── VIP 插隊區塊 ── */
.vip-section {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.vip-label {
  font-size: 12px;
  font-weight: 700;
  color: #f59e0b;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.vip-hint {
  font-weight: 400;
  color: rgba(148, 163, 184, 0.7);
  font-size: 11px;
}

.vip-input-row {
  display: flex;
  gap: 8px;
}

.vip-input {
  flex: 1;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 13px;
  font-family: 'Outfit', sans-serif;
  outline: none;
  transition: border-color 0.2s;
}
.vip-input:focus {
  border-color: rgba(245, 158, 11, 0.7);
  background: rgba(245, 158, 11, 0.05);
}
.vip-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.vip-input::placeholder {
  color: rgba(148, 163, 184, 0.5);
}

.vip-btn {
  padding: 8px 16px;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 13px;
  font-weight: 700;
  font-family: 'Outfit', sans-serif;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s;
  white-space: nowrap;
}
.vip-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}
.vip-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
}

.vip-cooldown {
  margin-top: 6px;
  font-size: 11px;
  color: rgba(148, 163, 184, 0.7);
}

.vip-message {
  margin-top: 6px;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: 6px;
}
.vip-message.success {
  color: #34d399;
  background: rgba(52, 211, 153, 0.08);
  border: 1px solid rgba(52, 211, 153, 0.2);
}
.vip-message.error {
  color: #f87171;
  background: rgba(248, 113, 113, 0.08);
  border: 1px solid rgba(248, 113, 113, 0.2);
}

/* ── Transitions ── */
.queue-panel-enter-active,
.queue-panel-leave-active {
  transition: opacity 0.35s ease, transform 0.35s ease, max-height 0.4s ease;
  overflow: hidden;
  max-height: 400px;
}
.queue-panel-enter-from,
.queue-panel-leave-to {
  opacity: 0;
  transform: translateY(-8px);
  max-height: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

