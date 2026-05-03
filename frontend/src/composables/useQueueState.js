// composables/useQueueState.js
// 全局共用的佇列狀態，讓 App.vue（顯示遮罩）和各 Mode 元件共享邏輯與資料。
import { ref } from 'vue'

// ── 佇列核心狀態 ─────────────────────────────────────────────────────────────
const currentJobId = ref(null)
const queuePosition = ref(0)
const jobProgress = ref(0)
const jobStageLabel = ref('')
const estimatedWait = ref(0)
const elapsedSec = ref(0)

// ── 插隊密碼狀態 ─────────────────────────────────────────────────────────────
const vipPasswordInput = ref('')
const vipEligible = ref(true)
const vipCooldownRemaining = ref(0)
const vipSubmitting = ref(false)
const vipMessage = ref('')
const vipMessageType = ref('') // 'success' | 'error'

// ── 內部定時器 ───────────────────────────────────────────────────────────────
let _pollTimer = null
let _waitCountdownTimer = null

export function useQueueState() {
  
  const resetQueueState = () => {
    queuePosition.value = 0
    jobProgress.value = 0
    jobStageLabel.value = ''
    estimatedWait.value = 0
    elapsedSec.value = 0
    vipPasswordInput.value = ''
    vipMessage.value = ''
    vipMessageType.value = ''
  }

  const stopPolling = () => {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null }
    stopWaitCountdown()
  }

  const stopWaitCountdown = () => {
    if (_waitCountdownTimer) { clearInterval(_waitCountdownTimer); _waitCountdownTimer = null }
  }

  const startWaitCountdown = () => {
    stopWaitCountdown()
    _waitCountdownTimer = setInterval(() => {
      if (estimatedWait.value > 0) {
        estimatedWait.value--
      }
    }, 1000)
  }

  /**
   * 開始輪詢工作狀態
   * @param {string} jobId 
   * @param {Object} callbacks - { onDone, onError }
   */
  const startPolling = (jobId, { onDone, onError } = {}) => {
    stopPolling()
    currentJobId.value = jobId
    startWaitCountdown()
    
    let hasUpdated = false
    _pollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/queue/status/${jobId}`)
        if (!res.ok) return
        const data = await res.json()
        
        const isFirstUpdate = !hasUpdated
        hasUpdated = true

        jobProgress.value = data.progress ?? 0
        jobStageLabel.value = data.stage_label ?? ''
        elapsedSec.value = data.elapsed_seconds ?? 0

        const newPos = data.position ?? 0
        if (isFirstUpdate || newPos < queuePosition.value) {
          queuePosition.value = newPos
          estimatedWait.value = data.estimated_wait_seconds ?? 0
        } else if (newPos === 0) {
          queuePosition.value = 0
          estimatedWait.value = 0
        }

        if (data.status === 'done') {
          stopPolling()
          if (onDone) await onDone(jobId)
        } else if (data.status === 'error') {
          stopPolling()
          if (onError) onError(data.error || '未知錯誤')
        }
      } catch (e) {
        console.error('[Queue Composable] Polling error:', e)
      }
    }, 2000)
  }

  return {
    currentJobId,
    queuePosition,
    jobProgress,
    jobStageLabel,
    estimatedWait,
    elapsedSec,
    vipPasswordInput,
    vipEligible,
    vipCooldownRemaining,
    vipSubmitting,
    vipMessage,
    vipMessageType,
    resetQueueState,
    startPolling,
    stopPolling,
    startWaitCountdown,
    stopWaitCountdown,
  }
}
