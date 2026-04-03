<template>
  <section class="workspace-panel glass-panel">
    <div class="action-toolbar glass-card">
      <div class="toolbar-left">
        <button
          @click="togglePreview"
          class="modern-btn btn-icon"
          :class="isPlayingPreview ? 'btn-danger' : 'btn-info'"
          :title="
            isPlayingPreview ? 'Stop Playback' : resultMidiUrl ? 'Preview Full' : 'Preview Melody'
          "
        >
          <svg
            v-if="!isPlayingPreview"
            viewBox="0 0 24 24"
            fill="currentColor"
            width="22"
            height="22"
          >
            <path d="M8 5v14l11-7z" />
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
          </svg>
        </button>
        <div class="toolbar-divider"></div>
        <button @click="clearCanvas" class="modern-btn btn-outline-danger">Clear</button>
        <div class="toolbar-divider"></div>
        <select :value="editorMode" @change="handleEditorModeChange" class="modern-select minimal">
          <option value="pad">Grid Pad</option>
          <option value="staff">Staff (VexFlow)</option>
        </select>
      </div>
      <div class="toolbar-right">
        <button
          @click="generateRandomMelody"
          class="modern-btn btn-outline"
          :disabled="isGenerating"
        >
          Generate Random
        </button>
        <button
          @click="submitMelodyJson"
          class="modern-btn btn-primary generate-btn"
          :disabled="isGenerating || melodyData.length === 0"
        >
          Generate Accompaniment
        </button>
        <a
          v-if="resultMidiUrl"
          :href="resultMidiUrl"
          download="accompaniment.mid"
          class="modern-btn btn-success download-btn"
        >
          Download MIDI
        </a>
      </div>
    </div>

    <div class="editor-area modern-editor-area">
      <div v-show="editorMode === 'pad'" class="pad-grid-wrapper">
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
                <div
                  v-if="getAiNoteClass(pitch, step - 1) !== ''"
                  class="pad-cell-note-inner ai-note"
                  :class="getAiNoteClass(pitch, step - 1)"
                ></div>
              </div>
            </div>
          </div>
        </div>
        <p class="helper-text primary-light">
          💡 Tip: Click and drag rightward to create longer notes.
        </p>
      </div>

      <div v-show="editorMode === 'staff'" class="vexflow-container">
        <div class="vf-toolbar modern-vf-toolbar">
          <div class="tool-group">
            <span class="tool-label">Duration:</span>
            <button :class="{ active: vfToolDuration === 1 }" @click="vfToolDuration = 1">
              8th
            </button>
            <button :class="{ active: vfToolDuration === 2 }" @click="vfToolDuration = 2">
              Quarter
            </button>
            <button :class="{ active: vfToolDuration === 4 }" @click="vfToolDuration = 4">
              Half
            </button>
            <button :class="{ active: vfToolDuration === 8 }" @click="vfToolDuration = 8">
              Whole
            </button>
          </div>
          <div class="tool-group">
            <span class="tool-label">Accidental:</span>
            <button :class="{ active: vfToolAccidental === '' }" @click="vfToolAccidental = ''">
              Natural
            </button>
            <button :class="{ active: vfToolAccidental === '#' }" @click="vfToolAccidental = '#'">
              Sharp
            </button>
            <button :class="{ active: vfToolAccidental === 'b' }" @click="vfToolAccidental = 'b'">
              Flat
            </button>
          </div>
        </div>

        <div class="staff-layout glass-container centered-staff">
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

const editorMode = ref('staff')
const vexflowContainer = ref(null)
const clefContainer = ref(null)

const melodyData = ref([])
const aiAccompanimentData = ref([])
const resultMidiUrl = ref(null)
const ghostNote = ref(null)

// Tone.js Singletons for this component to prevent memory leaks
let synth = null
let delSynth = null

const initSynth = async () => {
  await audioService.init()
}

const clearCanvas = () => {
  melodyData.value = []
  aiAccompanimentData.value = []
  resultMidiUrl.value = null
  ghostNote.value = null
}

const handleEditorModeChange = (e) => {
  const newMode = e.target.value
  const modeName = newMode === 'staff' ? 'Staff Mode' : 'Grid Pad Mode'

  if (melodyData.value.length > 0 || resultMidiUrl.value) {
    const confirmMsg = `Switching modes will discard your current melody and generated results. Are you sure you want to proceed to ${modeName}?`
    if (!window.confirm(confirmMsg)) {
      e.target.value = editorMode.value
      return
    }
  }

  editorMode.value = newMode
  clearCanvas()
}

const generateRandomMelody = () => {
  melodyData.value = []
  const cMajorPitches = [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81]
  let currentStep = 0

  // 🌟 優化：不再限制音符數量，而是持續填充直到接近總步數 (TOTAL_STEPS)
  while (currentStep < TOTAL_STEPS - 1) {
    const pitch = cMajorPitches[Math.floor(Math.random() * cMajorPitches.length)]

    // 隨機決定長度：1 (8分音符), 2 (4分音符), 4 (2分音符)
    const durRand = Math.random()
    const durationSteps = durRand > 0.8 ? 4 : durRand > 0.4 ? 2 : 1

    // 檢查是否超出邊界
    if (currentStep + durationSteps > TOTAL_STEPS) break

    melodyData.value.push({ pitch, step: currentStep, duration: durationSteps })

    // 增加位移，有機率產生 1 拍的休止
    const pause = Math.random() > 0.8 ? 1 : 0
    currentStep += durationSteps + pause
  }

  if (editorMode.value === 'staff') {
    nextTick(() => renderVexFlow())
  }
}

const submitMelodyJson = async () => {
  if (melodyData.value.length === 0) return

  try {
    isGenerating.value = true
    // 🌟 新增：偵錯發送給模型的資料量
    console.log(`[API Debug] 發送給模型的旋律音符數: ${melodyData.value.length}`)

    const response = await fetch('/api/generate-from-json', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        melody: melodyData.value,
        mode: 'oneStage',
        complexity: 0.5,
        creativity: 0.8,
      }),
    })

    if (!response.ok) throw new Error('Network response was not ok')

    const blob = await response.blob()
    resultMidiUrl.value = URL.createObjectURL(blob)

    try {
      const arrayBuffer = await blob.arrayBuffer()
      const midi = new Midi(arrayBuffer)
      const newAiData = []
      midi.tracks.forEach((track, idx) => {
        console.log(
          `[MIDI Debug] Track ${idx} | Program: ${track.instrument.number} | 音符數: ${track.notes.length}`,
        )

        // Program 0 (Piano) 為伴奏
        if (track.instrument.number !== 0) return

        track.notes.forEach((note) => {
          const step = Math.round(note.time / 0.25)
          const duration = Math.round(note.duration / 0.25) || 1
          let accidental = ''
          if (note.name.includes('#')) accidental = '#'
          if (note.name.includes('b')) accidental = 'b'
          newAiData.push({ pitch: note.midi, step, duration, accidental })
        })
      })
      aiAccompanimentData.value = newAiData
      if (editorMode.value === 'staff') {
        nextTick(() => renderVexFlow())
      }
    } catch (parseErr) {
      console.error('[API Error] MIDI 本地解析失敗:', parseErr)
    }
  } catch (error) {
    console.error('[API Error] JSON 傳送失敗:', error)
  } finally {
    isGenerating.value = false
  }
}

const PITCH_MAX = 83
const PITCH_MIN = 36
const TOTAL_STEPS = 32

const pitches = computed(() => {
  const arr = []
  for (let i = PITCH_MAX; i >= PITCH_MIN; i--) {
    if (![1, 3, 6, 8, 10].includes(i % 12)) arr.push(i)
  }
  return arr
})

const playPitch = async (pitch) => {
  await initSynth()
  const noteName = Tone.Frequency(pitch, 'midi').toNote()
  audioService.melodySynth.triggerAttackRelease(noteName, '8n')
}

const playDeleteSound = () => {
  if (audioService.delSynth) audioService.delSynth.triggerAttackRelease('C2', '32n')
}

const isDrawing = ref(false)
const drawStartStep = ref(-1)
const activePitch = ref(-1)

const removeOverlappingNotes = (start, duration, excludeNote = null) => {
  const end = start + duration
  melodyData.value = melodyData.value.filter((n) => {
    if (n === excludeNote) return true
    const nEnd = n.step + n.duration
    return !(Math.max(start, n.step) < Math.min(end, nEnd))
  })
}

const handleMouseDown = async (pitch, step) => {
  await initSynth()
  const existingIndex = melodyData.value.findIndex(
    (n) => n.pitch === pitch && step >= n.step && step < n.step + n.duration,
  )
  if (existingIndex !== -1) {
    melodyData.value.splice(existingIndex, 1)
    playDeleteSound()
    return
  }

  isDrawing.value = true
  drawStartStep.value = step
  activePitch.value = pitch

  removeOverlappingNotes(step, 1)
  melodyData.value.push({ pitch, step, duration: 1 })
  playPitch(pitch)
}

const handleMouseEnter = (pitch, step) => {
  if (!isDrawing.value || pitch !== activePitch.value || step < drawStartStep.value) return
  const note = melodyData.value.find(
    (n) => n.step === drawStartStep.value && n.pitch === activePitch.value,
  )
  if (note) {
    const newDuration = step - drawStartStep.value + 1
    note.duration = newDuration
    removeOverlappingNotes(drawStartStep.value, newDuration, note)
  }
}

const handleMouseUp = () => {
  isDrawing.value = false
}

onMounted(() => window.addEventListener('mouseup', handleMouseUp))
onUnmounted(() => {
  window.removeEventListener('mouseup', handleMouseUp)
  audioService.stopAll()
})

const isBlackKey = (pitch) => [1, 3, 6, 8, 10].includes(pitch % 12)

const getNoteClass = (pitch, step) => {
  const note = melodyData.value.find(
    (n) => n.pitch === pitch && step >= n.step && step < n.step + n.duration,
  )
  if (!note) return ''
  let classes = [`dur-${note.duration}`]
  if (note.step === step) classes.push('note-start')
  if (note.step + note.duration - 1 === step) classes.push('note-end')
  return classes.join(' ')
}

const getAiNoteClass = (pitch, step) => {
  const note = aiAccompanimentData.value.find(
    (n) => n.pitch === pitch && step >= n.step && step < n.step + n.duration,
  )
  if (!note) return ''
  let classes = [`dur-${note.duration}`]
  if (note.step === step) classes.push('note-start')
  if (note.step + note.duration - 1 === step) classes.push('note-end')
  return classes.join(' ')
}

const getPitchName = (pitch) => {
  const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
  return isBlackKey(pitch) ? '' : `${names[pitch % 12]}${Math.floor(pitch / 12) - 1}`
}

const isPlayingPreview = ref(false)
const togglePreview = async () => {
  await initSynth()
  if (isPlayingPreview.value) {
    audioService.stopAll() // 🌟 使用 audioService
    isPlayingPreview.value = false
    return
  }

  if (melodyData.value.length === 0) return
  isPlayingPreview.value = true
  const stepTime = Tone.Time('8n').toSeconds()

  melodyData.value.forEach((n) => {
    Tone.Transport.schedule((time) => {
      audioService.melodySynth.triggerAttackRelease(
        Tone.Frequency(n.pitch, 'midi').toNote(),
        n.duration * stepTime,
        time,
      )
    }, n.step * stepTime)
  })

  // 🌟 新增：如果已有伴奏數據，同步加入播放
  if (aiAccompanimentData.value && aiAccompanimentData.value.length > 0) {
    aiAccompanimentData.value.forEach((n) => {
      Tone.Transport.schedule((time) => {
        audioService.accSynth.triggerAttackRelease(
          Tone.Frequency(n.pitch, 'midi').toNote(),
          n.duration * stepTime,
          time,
        )
      }, n.step * stepTime)
    })
  }

  Tone.Transport.schedule(() => {
    isPlayingPreview.value = false
    audioService.stopAll()
  }, TOTAL_STEPS * stepTime)

  Tone.Transport.start()
}

// VexFlow Logic
const vfToolDuration = ref(1)
const vfToolAccidental = ref('')

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
  { step: 'f/5', basePitch: 77, lineOffset: 0 },
  { step: 'g/5', basePitch: 79, lineOffset: -0.5 },
  { step: 'a/5', basePitch: 81, lineOffset: -1 },
]

const renderVexFlow = () => {
  if (editorMode.value !== 'staff' || !vexflowContainer.value || !clefContainer.value) return

  try {
    clefContainer.value.innerHTML = ''
    const clefRenderer = new Renderer(clefContainer.value, Renderer.Backends.SVG)
    const isGrandStaff = aiAccompanimentData.value && aiAccompanimentData.value.length > 0
    const rendererHeight = isGrandStaff ? 280 : 180

    // 🌟 優化：將寬度從 80 增加到 110，容納 (x:25 + w:75) 的空間
    clefRenderer.resize(110, rendererHeight)
    const clefCtx = clefRenderer.getContext()
    // 🌟 優化：將起始 X 從 5 改為 25，並將寬度改為 85 以填滿畫布 (25+85=110)
    const trebleClefStave = new Stave(25, 40, 85)
      .addClef('treble')
      .addTimeSignature('4/4')
      .setContext(clefCtx)

    if (isGrandStaff) {
      const bassClefStave = new Stave(25, 140, 85)
        .addClef('bass')
        .addTimeSignature('4/4')
        .setContext(clefCtx)

      // 🌟 同步拍號起點：取兩者中較寬的位移，強制對齊
      const startX = Math.max(trebleClefStave.getNoteStartX(), bassClefStave.getNoteStartX())
      trebleClefStave.setNoteStartX(startX)
      bassClefStave.setNoteStartX(startX)

      // 隱藏右側小節線
      trebleClefStave.setEndBarType(Barline.type.NONE)
      bassClefStave.setEndBarType(Barline.type.NONE)

      trebleClefStave.draw()
      bassClefStave.draw()

      const connector = new StaveConnector(trebleClefStave, bassClefStave)
        .setType(StaveConnector.type.BRACE)
        .setContext(clefCtx)
      connector.draw()
      const line = new StaveConnector(trebleClefStave, bassClefStave)
        .setType(StaveConnector.type.SINGLE_LEFT)
        .setContext(clefCtx)
      line.draw()
    } else {
      // 只有旋律時
      trebleClefStave.setEndBarType(Barline.type.NONE)
      trebleClefStave.draw()
    }

    vexflowContainer.value.innerHTML = ''
    const renderer = new Renderer(vexflowContainer.value, Renderer.Backends.SVG)
    // 🌟 優化：稍微增加到 1210，確保最後一條小節線不被截斷
    renderer.resize(1210, rendererHeight)
    const context = renderer.getContext()

    let displayData = melodyData.value.map((n) => ({ ...n, isReal: true }))
    let ghostActionMeasure = -1

    if (ghostNote.value) {
      const gStep = ghostNote.value.step
      ghostActionMeasure = Math.floor(gStep / 8)
      const existingIndex = displayData.findIndex(
        (n) => gStep >= n.step && gStep < n.step + n.duration,
      )

      if (existingIndex !== -1) {
        displayData[existingIndex].isDeleting = true
      } else {
        let safeDuration = ghostNote.value.duration
        const maxDuration = 8 - (gStep % 8)
        if (safeDuration > maxDuration) safeDuration = maxDuration

        const end = gStep + safeDuration
        displayData = displayData.filter(
          (n) => !(Math.max(gStep, n.step) < Math.min(end, n.step + n.duration)),
        )
        displayData.push({ ...ghostNote.value, duration: safeDuration, isGhost: true })
      }
    }

    let currentX = 0
    const measureWidth = 300

    for (let m = 0; m < 4; m++) {
      const stave = new Stave(currentX, 40, measureWidth)
      let bassStave = null
      if (isGrandStaff) {
        bassStave = new Stave(currentX, 140, measureWidth)
      }

      // 🌟 關鍵同步：確保高低音譜的第一拍音符從絕對相同的 X 座標開始
      if (isGrandStaff) {
        const startX = Math.max(stave.getNoteStartX(), bassStave.getNoteStartX())
        stave.setNoteStartX(startX)
        bassStave.setNoteStartX(startX)
      }

      // 繪製小節線設定
      if (m === 0) {
        stave.setBegBarType(Barline.type.NONE)
        if (bassStave) bassStave.setBegBarType(Barline.type.NONE)
      }

      stave.setContext(context).draw()
      if (bassStave) bassStave.setContext(context).draw()

      const vfNotes = []
      const vfBassNotes = []
      let currentStep = m * 8
      const endStep = (m + 1) * 8

      while (currentStep < endStep) {
        const noteData = displayData.find((n) => n.step === currentStep)
        if (noteData) {
          let renderDuration = Math.min(noteData.duration, endStep - currentStep)
          let durationStr = ['8', 'q', 'qd', 'h', 'h', 'hd', 'hd', 'w'][renderDuration - 1] || '8'

          let vfKey = 'b/4'
          const accOffset = noteData.accidental === '#' ? 1 : noteData.accidental === 'b' ? -1 : 0
          const expectedBase = noteData.pitch - accOffset
          const noteMatch = diatonicScale.find((d) => d.basePitch === expectedBase)

          if (noteMatch) {
            vfKey = noteMatch.step
          } else {
            const exact = diatonicScale.find((d) => d.basePitch === noteData.pitch)
            if (exact) {
              vfKey = exact.step
            } else {
              const sharpMatch = diatonicScale.find((d) => d.basePitch + 1 === noteData.pitch)
              if (sharpMatch) {
                vfKey = sharpMatch.step
                if (!noteData.accidental) noteData.accidental = '#'
              }
            }
          }
          if (noteData.accidental) vfKey = vfKey.replace('/', `${noteData.accidental}/`)

          const staveNote = new StaveNote({ clef: 'treble', keys: [vfKey], duration: durationStr })
          if (noteData.accidental) staveNote.addModifier(new Accidental(noteData.accidental))

          if (noteData.isDeleting)
            staveNote.setStyle({
              fillStyle: 'rgba(231,76,60,0.5)',
              strokeStyle: 'rgba(231,76,60,0.5)',
            })
          else if (noteData.isGhost)
            staveNote.setStyle({
              fillStyle: 'rgba(100,100,100,0.5)',
              strokeStyle: 'rgba(100,100,100,0.5)',
            })

          vfNotes.push(staveNote)
          currentStep += renderDuration
        } else {
          let restNote
          if (
            currentStep % 2 === 0 &&
            !displayData.find((n) => n.step === currentStep + 1) &&
            currentStep + 1 < endStep
          ) {
            restNote = new StaveNote({ clef: 'treble', keys: ['b/4'], duration: 'qr' })
            currentStep += 2
          } else {
            restNote = new StaveNote({ clef: 'treble', keys: ['b/4'], duration: '8r' })
            currentStep += 1
          }
          if (m === ghostActionMeasure)
            restNote.setStyle({
              fillStyle: 'rgba(150, 150, 150, 0.5)',
              strokeStyle: 'rgba(150, 150, 150, 0.5)',
            })
          vfNotes.push(restNote)
        }
      }

      if (isGrandStaff) {
        let bassStep = m * 8
        while (bassStep < endStep) {
          let notesAtStep = aiAccompanimentData.value
            .filter((n) => n.step === bassStep)
            .sort((a, b) => a.pitch - b.pitch)
          if (notesAtStep.length > 0) {
            // 🌟 核心修正：尋找小節內下一個「新音符」的起點，用於截斷視覺長度
            const nextNotes = aiAccompanimentData.value
              .filter((n) => n.step > bassStep && n.step < endStep)
              .sort((a, b) => a.step - b.step)

            const nextEventStep = nextNotes.length > 0 ? nextNotes[0].step : endStep
            const actualMaxDur = nextEventStep - bassStep

            const originalDur = notesAtStep[0].duration
            let renderDur = Math.min(originalDur, actualMaxDur)

            // 限制 VexFlow 支援的最大視覺長度 (1~8)
            renderDur = Math.max(1, Math.min(8, renderDur))

            let durationStr = ['8', 'q', 'qd', 'h', 'h', 'hd', 'hd', 'w'][renderDur - 1] || '8'

            const keys = []
            const accidentals = []
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
              if (n.accidental === 'b' && acc === '#') {
                letter = String.fromCharCode(letter.charCodeAt(0) + 1)
                if (letter === 'h') letter = 'a'
                acc = 'b'
              }
              const keyName = `${letter}${acc}/${octave}`
              if (!keys.includes(keyName)) {
                keys.push(keyName)
                accidentals.push(acc)
              }
            })

            if (keys.length === 0) keys.push('c/3')
            const staveNote = new StaveNote({ clef: 'bass', keys, duration: durationStr })
            accidentals.forEach((acc, i) => {
              if (acc) staveNote.addModifier(new Accidental(acc), i)
            })
            staveNote.setStyle({ fillStyle: '#8f94fb', strokeStyle: '#8f94fb' })
            vfBassNotes.push(staveNote)
            bassStep += renderDur
          } else {
            const restNote = new StaveNote({ clef: 'bass', keys: ['c/3'], duration: '8r' })
            vfBassNotes.push(restNote)
            bassStep += 1
          }
        }
      }

      const voice = new Voice({ num_beats: 4, beat_value: 4 })
        .setStrict(false)
        .addTickables(vfNotes)

      let voicesArr = [voice]
      let bassVoice = null

      if (isGrandStaff) {
        bassVoice = new Voice({ num_beats: 4, beat_value: 4 })
          .setStrict(false)
          .addTickables(vfBassNotes)
        voicesArr.push(bassVoice)

        // 🌟 顯式綁定聲部與譜表，確保座標系基礎一致
        voice.setStave(stave)
        bassVoice.setStave(bassStave)
      }

      // 🌟 重要優化：不再使用 joinVoices 以避免兩軌音符為了避讓而水平位移
      // 但保留 format(voicesArr) 以確保所有聲部的拍點 (Tick) 依然對齊
      const formatter = new Formatter()

      // 直接格式化，這能讓上下兩軌音符處於絕對垂直的基準線上
      formatter.format(voicesArr, measureWidth - 40, { align_rests: true })

      voice.draw(context, stave)
      if (isGrandStaff) bassVoice.draw(context, bassStave)
      currentX += measureWidth
    }
  } catch (error) {
    console.error('[VexFlow] Error:', error)
  }
}

const handleVexFlowClick = async (event) => {
  await initSynth()
  const rect = vexflowContainer.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  let measureIndex = Math.max(0, Math.min(3, Math.floor(x / 300)))
  const localX = x % 300
  let stepInMeasure = Math.max(0, Math.min(7, Math.floor((localX - 10) / 35)))
  const targetStep = measureIndex * 8 + stepInMeasure

  const existingIndex = melodyData.value.findIndex(
    (n) => targetStep >= n.step && targetStep < n.step + n.duration,
  )
  if (existingIndex !== -1) {
    melodyData.value.splice(existingIndex, 1)
    playDeleteSound()
    ghostNote.value = null
    renderVexFlow()
    return
  }

  const yOffset = (y - 80) / 10
  let closestDiatonic = diatonicScale.reduce((prev, curr) =>
    Math.abs(curr.lineOffset - yOffset) < Math.abs(prev.lineOffset - yOffset) ? curr : prev,
  )

  let finalPitch =
    closestDiatonic.basePitch +
    (vfToolAccidental.value === '#' ? 1 : vfToolAccidental.value === 'b' ? -1 : 0)

  const duration = vfToolDuration.value
  if (duration > 8 - stepInMeasure) {
    alert(`Space full!`)
    return
  }

  removeOverlappingNotes(targetStep, duration)
  melodyData.value.push({
    pitch: finalPitch,
    step: targetStep,
    duration: duration,
    accidental: vfToolAccidental.value,
  })
  playPitch(finalPitch)
}

const handleVexFlowMouseMove = (event) => {
  if (editorMode.value !== 'staff' || !vexflowContainer.value) return
  const rect = vexflowContainer.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  let measureIndex = Math.floor(x / 300)
  if (measureIndex < 0 || measureIndex > 3) {
    ghostNote.value = null
    return
  }

  let stepInMeasure = Math.max(0, Math.min(7, Math.floor(((x % 300) - 10) / 35)))
  const targetStep = measureIndex * 8 + stepInMeasure
  const yOffset = (y - 80) / 10
  let closestDiatonic = diatonicScale.reduce((prev, curr) =>
    Math.abs(curr.lineOffset - yOffset) < Math.abs(prev.lineOffset - yOffset) ? curr : prev,
  )

  let finalPitch =
    closestDiatonic.basePitch +
    (vfToolAccidental.value === '#' ? 1 : vfToolAccidental.value === 'b' ? -1 : 0)

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

const handleVexFlowMouseLeave = () => (ghostNote.value = null)

watch(
  [melodyData, editorMode, ghostNote],
  () => {
    if (editorMode.value === 'staff') nextTick(() => renderVexFlow())
  },
  { deep: true },
)

onMounted(() => {
  nextTick(() => renderVexFlow())
})
</script>

<style scoped>
/* ============================================
   AccomPartner · MelodyEditor — Refined Theme
   Consistent with HeroSection design language:
   · Outfit font, brand gradient (#4e54c8 → #8f94fb → #ff6a88)
   · Soft light backgrounds, generous negative space
   · Subtle glass morphism, no heavy borders
   ============================================ */

@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800;900&display=swap');

/* ---------- Panel wrapper ---------- */
.glass-panel {
  font-family: 'Outfit', sans-serif;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow:
    0 8px 40px rgba(78, 84, 200, 0.07),
    0 2px 8px rgba(0, 0, 0, 0.04);
  border-radius: 24px;
  padding: 30px 32px;
  margin-bottom: 25px;
}

.glass-container {
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 16px;
  padding: 16px;
}

.glass-card {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 16px;
  padding: 18px 22px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.8);
}

/* ---------- Toolbar divider ---------- */
.toolbar-divider {
  width: 1px;
  height: 20px;
  background: rgba(78, 84, 200, 0.12);
  border-radius: 1px;
  flex-shrink: 0;
}

/* ---------- Icon-only play/stop button ---------- */
.btn-icon {
  width: 48px;
  height: 48px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
  opacity: 1;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
}
.btn-icon:hover {
  transform: translateY(-1px);
}
.btn-icon.btn-info {
  background: linear-gradient(135deg, #4e54c8 0%, #8f94fb 100%) !important;
  color: #fff !important;
  border: none;
  box-shadow: 0 4px 14px rgba(78, 84, 200, 0.4) !important;
}
.btn-icon.btn-info:hover {
  box-shadow: 0 8px 22px rgba(78, 84, 200, 0.5) !important;
}
.btn-icon.btn-danger {
  background: linear-gradient(135deg, #ff6a88 0%, #ff4757 100%) !important;
  color: #fff !important;
  border: none;
  box-shadow: 0 4px 14px rgba(255, 71, 87, 0.4) !important;
}
.btn-icon.btn-danger:hover {
  box-shadow: 0 8px 22px rgba(255, 71, 87, 0.5) !important;
}
.btn-icon svg {
  width: 24px !important;
  height: 24px !important;
  display: block;
  flex-shrink: 0;
}

/* ---------- Select ---------- */
.modern-select {
  padding: 10px 16px;
  border-radius: 10px;
  border: 1.5px solid rgba(78, 84, 200, 0.15);
  background: rgba(255, 255, 255, 0.9);
  font-family: 'Outfit', sans-serif;
  font-size: 15px;
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
}

.modern-select:hover,
.modern-select:focus {
  border-color: rgba(78, 84, 200, 0.4);
  box-shadow: 0 4px 16px rgba(78, 84, 200, 0.12);
}

.modern-select.minimal {
  /* identical to .modern-select, kept for compat */
  border-color: rgba(78, 84, 200, 0.15);
  background-color: rgba(255, 255, 255, 0.9);
}

/* ---------- Action Toolbar ---------- */
.action-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  margin-bottom: 22px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.8);
  /* Subtle left accent replacing the heavy 4px border */
  box-shadow:
    inset 3px 0 0 #4e54c8,
    0 2px 10px rgba(0, 0, 0, 0.03);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ---------- Buttons ---------- */
.modern-btn {
  font-family: 'Outfit', sans-serif;
  padding: 11px 22px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  border: none;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease,
    opacity 0.15s;
  letter-spacing: 0.1px;
}

.modern-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none !important;
}

.modern-btn:not(:disabled):active {
  transform: scale(0.97);
}

/* Primary — hero gradient */
.btn-primary {
  background: linear-gradient(135deg, #4e54c8 0%, #8f94fb 100%);
  color: #fff !important;
  box-shadow: 0 4px 16px rgba(78, 84, 200, 0.28);
}
.btn-primary:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(78, 84, 200, 0.36);
}

/* Info / Preview — calm blue */
.btn-info {
  background: #2c3e50;
  color: #fff;
  box-shadow: 0 4px 12px rgba(44, 62, 80, 0.18);
}
.btn-info:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(44, 62, 80, 0.26);
}

/* Danger / Stop */
.btn-danger {
  background: linear-gradient(135deg, #ff6a88 0%, #ff4757 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(255, 71, 87, 0.22);
}
.btn-danger:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(255, 71, 87, 0.3);
}

/* Outline — clear canvas */
.btn-outline-danger {
  background: transparent;
  border: 1.5px solid rgba(255, 107, 136, 0.3);
  color: #ff4757;
  box-shadow: none;
}
.btn-outline-danger:hover {
  background: rgba(255, 107, 136, 0.06);
  border-color: rgba(255, 107, 136, 0.55);
}

/* Outline — secondary actions */
.btn-outline {
  background: transparent;
  border: 1.5px solid rgba(78, 84, 200, 0.2);
  color: #4e54c8;
}
.btn-outline:not(:disabled):hover {
  background: rgba(78, 84, 200, 0.05);
  border-color: rgba(78, 84, 200, 0.45);
}

/* Success — download */
.btn-success {
  background: linear-gradient(135deg, #5fe3a1 0%, #27ae60 100%);
  color: #fff !important;
  box-shadow: 0 4px 12px rgba(39, 174, 96, 0.22);
}
.btn-success:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(39, 174, 96, 0.3);
}

.generate-btn {
  padding: 11px 28px;
}

.download-btn {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}

/* ---------- Editor area ---------- */
.modern-editor-area {
  margin-top: 0;
  padding: 22px;
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.92) 0%, rgba(247, 249, 252, 0.85) 100%);
  border: 1px solid rgba(255, 255, 255, 0.85);
  border-radius: 18px;
  box-shadow:
    0 6px 24px rgba(78, 84, 200, 0.05),
    0 1px 4px rgba(0, 0, 0, 0.03);
}

/* ---------- VexFlow toolbar ---------- */
.modern-vf-toolbar {
  display: flex;
  gap: 28px;
  align-items: center;
  margin-bottom: 18px;
  padding: 14px 20px;
  background: rgba(248, 249, 252, 0.8);
  border-radius: 12px;
  border: 1px solid rgba(78, 84, 200, 0.06);
}

.tool-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-label {
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 12px;
  color: #aab4c4;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.tool-group button {
  font-family: 'Outfit', sans-serif;
  padding: 9px 18px;
  background: rgba(255, 255, 255, 0.9);
  border: 1.5px solid rgba(78, 84, 200, 0.12);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  color: #7f8c8d;
  transition:
    border-color 0.15s,
    color 0.15s,
    background 0.15s,
    box-shadow 0.15s;
}

.tool-group button:hover {
  border-color: rgba(78, 84, 200, 0.3);
  color: #4e54c8;
}

.tool-group button.active {
  background: linear-gradient(135deg, #4e54c8, #8f94fb);
  color: #fff !important;
  border-color: transparent;
  box-shadow: 0 3px 10px rgba(78, 84, 200, 0.25);
}

/* ---------- Staff layout ---------- */
.staff-layout {
  display: flex;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 2px 16px rgba(78, 84, 200, 0.06);
  min-height: 200px;
  border: 1px solid rgba(78, 84, 200, 0.06);
}

.centered-staff {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  overflow-x: auto;
  padding: 15px 40px;
}

.fixed-clef {
  flex-shrink: 0;
  border-right: 1px solid rgba(78, 84, 200, 0.08);
  padding-right: 0;
}

.scrollable-measures {
  flex: 0 1 auto;
  overflow-x: auto;
  overflow-y: hidden;
  padding-left: 0;
  cursor: crosshair;
}

/* ---------- Grid pad ---------- */
.pad-grid-wrapper {
  margin-top: 16px;
}

.pad-editor-container {
  max-height: 450px;
  overflow: auto;
  border-radius: 14px;
  border: 1px solid rgba(78, 84, 200, 0.06);
  background: #fff;
}

.pad-row {
  display: flex;
  height: 32px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.025);
}

.pad-row:hover {
  background: rgba(78, 84, 200, 0.015);
}

.pad-row.is-black-key {
  background-color: rgba(78, 84, 200, 0.025);
}

.pad-label {
  position: sticky;
  left: 0;
  width: 50px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-right: 1px solid rgba(78, 84, 200, 0.1);
  font-family: 'Outfit', sans-serif;
  font-size: 11px;
  font-weight: 700;
  color: #aab4c4;
  z-index: 10;
}

.pad-row.is-black-key .pad-label {
  background: rgba(248, 249, 252, 0.95);
}

.pad-grid-cells {
  display: flex;
  flex: 1;
}

.pad-cell {
  flex: 1 1 0;
  min-width: 0;
  height: 100%;
  border-right: 1px solid rgba(0, 0, 0, 0.025);
  position: relative;
  cursor: crosshair;
}

.pad-cell-note-inner {
  position: absolute;
  top: 3px;
  bottom: 3px;
  left: 0;
  right: 0;
  /* Match brand gradient feel: teal → green */
  background: linear-gradient(180deg, #5fe3a1 0%, #35c17a 100%);
  z-index: 2;
  transition: all 0.1s ease;
  box-shadow: 0 1px 4px rgba(53, 193, 122, 0.3);
}

.pad-cell-note-inner.note-start {
  border-top-left-radius: 5px;
  border-bottom-left-radius: 5px;
  left: 2px;
}

.pad-cell-note-inner.note-end {
  border-top-right-radius: 5px;
  border-bottom-right-radius: 5px;
  right: 2px;
}

.pad-cell-note-inner.ai-note {
  background: rgba(143, 148, 251, 0.25);
  border: 1px dashed rgba(143, 148, 251, 0.6);
  border-left: none;
  border-right: none;
  box-shadow: none;
  z-index: 5;
  pointer-events: none;
}

.pad-cell-note-inner.ai-note.note-start {
  border-left: 1px dashed rgba(143, 148, 251, 0.6);
}

.pad-cell-note-inner.ai-note.note-end {
  border-right: 1px dashed rgba(143, 148, 251, 0.6);
}

/* ---------- Helper text ---------- */
.helper-text {
  margin-top: 14px;
  font-family: 'Outfit', sans-serif;
  font-size: 13px;
  color: #aab4c4;
  font-style: italic;
  text-align: center;
}

.helper-text.primary-light {
  color: #4e54c8;
  font-weight: 600;
  opacity: 0.75;
  font-style: normal;
}

/* ---------- Control group (legacy) ---------- */
.control-group label {
  font-family: 'Outfit', sans-serif;
  font-size: 11px;
  font-weight: 700;
  color: #aab4c4;
  text-transform: uppercase;
  letter-spacing: 1px;
}
</style>
