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
                    <option value="twoStage-std">Two-Stage Std (AR Chords)</option>
                    <option value="twoStage-bar">Two-Stage Bar</option>
                    <option value="twoStage-nar">Two-Stage NAR (Non-Autoregressive)</option>
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
                  Generate Accompaniment
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
              download="advanced_accompaniment.mid"
              class="modern-btn btn-outline btn-compact"
            >
              ↓ MIDI
            </a>
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
  Annotation,
  Barline,
} from 'vexflow'
import * as Tone from 'tone'
import { useAppState } from '../../composables/useAppState'
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

const initSynth = async () => {
  await audioService.init()
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  rawFile.value = file
  parsedTracks.value = []
  selectedTrackIndex.value = ''
  advancedGenerationHistory.value = []
  currentAdvancedHistoryIndex.value = -1

  try {
    const arrayBuffer = await file.arrayBuffer()
    rawMidiBuffer.value = arrayBuffer
    const midi = new Midi(arrayBuffer)
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

watch(selectedTrackIndex, (newIndex) => {
  if (newIndex === '' || !rawMidiBuffer.value) return
  try {
    const originalMidi = new Midi(rawMidiBuffer.value)
    const targetTrack = originalMidi.tracks[newIndex]

    const newMelodyData = []
    targetTrack.notes.forEach((note) => {
      const step = Math.round(note.time / 0.25)
      const duration = Math.round(note.duration / 0.25) || 1
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
      },
    ]
    currentAdvancedHistoryIndex.value = 0
    nextTick(() => renderAdvancedVexFlow())
  } catch (error) {
    console.error('[Preview Error]', error)
  }
})

const submitMidiFile = async () => {
  if (!rawFile.value || selectedTrackIndex.value === '') return
  try {
    isGenerating.value = true
    const formData = new FormData()
    formData.append('midiFile', rawFile.value)
    formData.append('targetTrackIndex', selectedTrackIndex.value)
    formData.append('mode', selectedInferenceMode.value)
    formData.append('complexity', generationComplexity.value)
    formData.append('creativity', generationCreativity.value)

    const response = await fetch('/api/generate-from-midi', { method: 'POST', body: formData })
    if (!response.ok) throw new Error('Network response was not ok')

    const jsonStr = await response.text()
    let jsonData = null
    try {
      jsonData = JSON.parse(jsonStr)
      if (import.meta.env.DEV) console.log('[API] Response parsed:', jsonData)
    } catch (e) {
      // JSON 解析失敗通常代表後端回傳了非預期格式（如 HTML 錯誤頁）
      console.error('[API Error] 回應不是合法的 JSON，這可能代表後端發生了錯誤:', jsonStr.slice(0, 200))
      throw new Error('後端回應格式錯誤，請檢查後端日誌')
    }

    let blob
    let chordLabels = []
    if (jsonData && jsonData.midi_b64) {
      const binaryStr = atob(jsonData.midi_b64)
      const len = binaryStr.length
      const bytes = new Uint8Array(len)
      for (let i = 0; i < len; i++) bytes[i] = binaryStr.charCodeAt(i)
      blob = new Blob([bytes], { type: 'audio/midi' })
      console.log('chords:', jsonData.chords)
      if (jsonData.chords) chordLabels = jsonData.chords
    } else {
      blob = new Blob([jsonStr], { type: 'audio/midi' })
    }

    const url = URL.createObjectURL(blob)
    const arrayBuffer = await blob.arrayBuffer()
    const midi = new Midi(arrayBuffer)

    const newMelodyData = []
    const newAiData = []
    midi.tracks.forEach((track, index) => {
      const targetArray = index === 0 && midi.tracks.length > 1 ? newMelodyData : newAiData
      track.notes.forEach((note) => {
        const step = Math.round(note.time / 0.25)
        const duration = Math.round(note.duration / 0.25) || 1
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
    })
    currentAdvancedHistoryIndex.value = advancedGenerationHistory.value.length - 1
    nextTick(() => renderAdvancedVexFlow())
  } catch (error) {
    console.error('[API Error]', error)
  } finally {
    isGenerating.value = false
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

  // 💡 問題 3 修復：根據所有音符的所在位置，動態計算「整份樂譜的總小節數」
  const maxMelodyStep =
    melodyDataSrc.length > 0 ? Math.max(...melodyDataSrc.map((n) => n.step + n.duration)) : 0
  const maxAiStep =
    aiDataSrc.length > 0 ? Math.max(...aiDataSrc.map((n) => n.step + n.duration)) : 0
  const maxStep = Math.max(maxMelodyStep, maxAiStep)
  const TOTAL_MEASURES = Math.max(1, Math.ceil(maxStep / 8)) // 計算出確切的總小節數

  const MEASURE_WIDTH = 300
  const CLEF_WIDTH = 110
  const ROW_HEIGHT = isGrandStaff ? 280 : 180

  const availableWidth = container.clientWidth - 20
  const MEASURES_PER_ROW = Math.max(1, Math.floor((availableWidth - CLEF_WIDTH) / MEASURE_WIDTH))
  const TOTAL_ROWS = Math.ceil(TOTAL_MEASURES / MEASURES_PER_ROW)

  const renderer = new Renderer(container, Renderer.Backends.SVG)
  // 🌟 優化：增加 10px 緩衝區確保最後一根小節線不被切掉
  const canvasWidth = CLEF_WIDTH + Math.min(TOTAL_MEASURES, MEASURES_PER_ROW) * MEASURE_WIDTH + 10
  renderer.resize(canvasWidth, TOTAL_ROWS * ROW_HEIGHT)
  const context = renderer.getContext()

  let globalMeasureIndex = 0

  for (let row = 0; row < TOTAL_ROWS; row++) {
    if (globalMeasureIndex >= TOTAL_MEASURES) break

    const rowY = row * ROW_HEIGHT
    // 🌟 優化：x 從 0 改為 25，寬度從 CLEF_WIDTH 改為 85 (25+85=110)
    const trebleClefStave = new Stave(25, rowY + 40, 85).addClef('treble').setContext(context)
    if (row === 0) trebleClefStave.addTimeSignature('4/4')

    if (isGrandStaff) {
      const bassClefStave = new Stave(25, rowY + 140, 85).addClef('bass').setContext(context)
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

      const startStep = globalMeasureIndex * 8
      const endStep = (globalMeasureIndex + 1) * 8

      // 預先計算本小節每個 step 應顯示的和弦 Annotation
      // 優先規則：第一拍一定顯示
      // 次要規則：後續拍與前一拍和弦不同時才顯示
      const chordAnnotationMap = new Map() // step → chordLabel
      const measureChords = Array.isArray(chordsSrc[globalMeasureIndex])
        ? chordsSrc[globalMeasureIndex]
        : []
      if (measureChords.length > 0) {
        for (let beat = 0; beat < measureChords.length; beat++) {
          const chord = measureChords[beat] || ''
          if (!chord) continue
          const beatStartStep = startStep + beat * 2
          const isFirstBeat = beat === 0
          const prevChord = measureChords[beat - 1] || ''
          if (isFirstBeat || chord !== prevChord) {
            chordAnnotationMap.set(beatStartStep, chord)
          }
        }
      }

      // ==================== 繪製高音譜 ====================
      let trebleVfNotes = []
      let trebleStep = startStep
      while (trebleStep < endStep) {
        const foundNote = melodyDataSrc.find((n) => n.step === trebleStep)
        if (foundNote) {
          let renderDur = Math.min(foundNote.duration, endStep - trebleStep)
          let vexTicks = 1
          let durStr = '8'
          let isDotted = false
          if (renderDur >= 8) {
            durStr = 'w'
            vexTicks = 8
          } else if (renderDur >= 6) {
            durStr = 'hd'
            isDotted = true
            vexTicks = 6
          } else if (renderDur >= 4) {
            durStr = 'h'
            vexTicks = 4
          } else if (renderDur >= 3) {
            durStr = 'qd'
            isDotted = true
            vexTicks = 3
          } else if (renderDur >= 2) {
            durStr = 'q'
            vexTicks = 2
          } else {
            durStr = '8'
            vexTicks = 1
          }

          let vfKey = 'b/4'
          const accOffset = foundNote.accidental === '#' ? 1 : foundNote.accidental === 'b' ? -1 : 0
          const expectedBase = foundNote.pitch - accOffset
          const noteMatch = diatonicScale.find((d) => d.basePitch === expectedBase)

          if (noteMatch) vfKey = noteMatch.step
          else {
            const exact = diatonicScale.find((d) => d.basePitch === foundNote.pitch)
            if (exact) vfKey = exact.step
            else {
              const sharpMatch = diatonicScale.find((d) => d.basePitch + 1 === foundNote.pitch)
              if (sharpMatch) {
                vfKey = sharpMatch.step
                if (!foundNote.accidental) foundNote.accidental = '#'
              }
            }
          }
          if (foundNote.accidental) vfKey = vfKey.replace('/', `${foundNote.accidental}/`)

          const staveNote = new StaveNote({ clef: 'treble', keys: [vfKey], duration: durStr })
          if (foundNote.accidental) staveNote.addModifier(new Accidental(foundNote.accidental))
          if (isDotted) staveNote.addModifier(new Dot(0), 0)

          // 查 map：此 step 若有需要顯示的和弦就掛上 Annotation
          if (chordAnnotationMap.has(trebleStep)) {
            staveNote.addModifier(
              new Annotation(chordAnnotationMap.get(trebleStep))
                .setFont('Arial', 12, 'bold')
                .setVerticalJustification(Annotation.VerticalJustify.TOP),
            )
          }
          trebleVfNotes.push(staveNote)
          trebleStep += vexTicks
        } else {
          let restNote
          if (
            trebleStep % 2 === 0 &&
            !melodyDataSrc.find((n) => n.step === trebleStep + 1) &&
            trebleStep + 1 < endStep
          ) {
            restNote = new StaveNote({ clef: 'treble', keys: ['b/4'], duration: 'qr' })
            trebleStep += 2
          } else {
            restNote = new StaveNote({ clef: 'treble', keys: ['b/4'], duration: '8r' })
            trebleStep += 1
          }
          // 查 map：小節開頭是休止符時，檢查 startStep 是否需要標註
          if (chordAnnotationMap.has(startStep) && trebleVfNotes.length === 0) {
            restNote.addModifier(
              new Annotation(chordAnnotationMap.get(startStep))
                .setFont('Arial', 12, 'bold')
                .setVerticalJustification(Annotation.VerticalJustify.TOP),
            )
          }
          trebleVfNotes.push(restNote)
        }
      }

      const trebleVoice = new Voice({ num_beats: 4, beat_value: 4 })
        .setStrict(false)
        .addTickables(trebleVfNotes)

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
            let durStr = '8'
            let isDotted = false
            if (renderDur >= 8) {
              durStr = 'w'
              vexTicks = 8
            } else if (renderDur >= 6) {
              durStr = 'hd'
              isDotted = true
              vexTicks = 6
            } else if (renderDur >= 4) {
              durStr = 'h'
              vexTicks = 4
            } else if (renderDur >= 3) {
              durStr = 'qd'
              isDotted = true
              vexTicks = 3
            } else if (renderDur >= 2) {
              durStr = 'q'
              vexTicks = 2
            } else {
              durStr = '8'
              vexTicks = 1
            }

            const keys = []
            const accs = []
            notesAtStep.forEach((n) => {
              let letter = 'c'
              let acc = ''
              let octave = Math.floor(n.pitch / 12) - 1
              switch (n.pitch % 12) {
                case 0:
                  letter = 'c'
                  break
                case 1:
                  letter = 'c'
                  acc = '#'
                  break
                case 2:
                  letter = 'd'
                  break
                case 3:
                  letter = 'e'
                  acc = 'b'
                  break
                case 4:
                  letter = 'e'
                  break
                case 5:
                  letter = 'f'
                  break
                case 6:
                  letter = 'f'
                  acc = '#'
                  break
                case 7:
                  letter = 'g'
                  break
                case 8:
                  letter = 'g'
                  acc = '#'
                  break
                case 9:
                  letter = 'a'
                  break
                case 10:
                  letter = 'b'
                  acc = 'b'
                  break
                case 11:
                  letter = 'b'
                  break
              }
              if (n.accidental) acc = n.accidental
              keys.push(`${letter}/${octave}`)
              accs.push(acc)
            })

            const sn = new StaveNote({
              clef: 'bass',
              keys: keys.length ? keys : ['c/3'],
              duration: durStr,
            })
            accs.forEach((a, idx) => {
              if (a) sn.addModifier(new Accidental(a), idx)
            })
            if (isDotted) sn.addModifier(new Dot(0), 0)
            sn.setStyle({ fillStyle: '#8f94fb', strokeStyle: '#8f94fb' })
            bassVfNotes.push(sn)
            bassStep += vexTicks
          } else {
            let rNote
            if (
              bassStep % 2 === 0 &&
              !aiDataSrc.find((n) => n.step === bassStep + 1) &&
              bassStep + 1 < endStep
            ) {
              rNote = new StaveNote({ clef: 'bass', keys: ['d/3'], duration: 'qr' })
              bassStep += 2
            } else {
              rNote = new StaveNote({ clef: 'bass', keys: ['d/3'], duration: '8r' })
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

      // 同步所有聲部，對齊休止符，給予 40px 的內距空間
      formatter.format(voicesToFormat, MEASURE_WIDTH - 40, { align_rests: true })

      trebleVoice.draw(context, trebleStave)
      if (bassVoice) {
        bassVoice.draw(context, bassStave)

        // 💡 如果到了該行的末端，或是全曲結束，強制把上下兩個五線譜連起來封口
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

  const stepTime = Tone.Time('8n').toSeconds()
  const maxSteps = 24 * 8

  if (historyItem.melodyData) {
    historyItem.melodyData
      .filter((n) => n.step < maxSteps)
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
      .filter((n) => n.step < maxSteps)
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
  }, maxSteps * stepTime)
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

onMounted(() => {
  window.addEventListener('resize', handleResize) // 註冊監聽器
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  audioService.stopAll()
  isPlayingAdvanced.value = false
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
</style>
