import { ref } from 'vue'

const currentAppMode = ref('quick') // 'quick' | 'advanced' | 'realtime'
const showHero = ref(true)
const isGenerating = ref(false)

export function useAppState() {
  const switchMode = (mode, hasData = false) => {
    if (currentAppMode.value === mode && !showHero.value) return

    const modeNames = {
      quick: 'Melody Editor',
      advanced: 'MIDI Upload',
      realtime: 'Realtime Piano'
    }

    if (hasData) {
      const confirmMsg = `Switching modes will discard your current local results. Are you sure you want to proceed to ${modeNames[mode]}?`
      if (!window.confirm(confirmMsg)) return false
    }

    currentAppMode.value = mode
    showHero.value = false
    return true
  }

  const startExperience = () => {
    showHero.value = false
  }

  return {
    currentAppMode,
    showHero,
    isGenerating,
    switchMode,
    startExperience
  }
}
