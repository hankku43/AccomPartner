<template>
  <div class="app-wrapper light-theme">
    <!-- 背景內容容器：受模糊濾鏡影響 -->
    <div class="app-content-layout" :class="{ 'is-loading': isGenerating }">
      <!-- 導覽列 -->
      <Navigation @switchMode="handleSwitchMode" />

      <!-- Hero Section -->
      <HeroSection @start="startExperience" @switchMode="handleSwitchMode" />

      <!-- 主工作區 -->
      <main v-show="!showHero" class="main-workspace">
        <MelodyEditor v-if="currentAppMode === 'quick'" />
        <AdvancedMode v-if="currentAppMode === 'advanced'" />
        <RealtimePiano v-if="currentAppMode === 'realtime'" />
      </main>
    </div>

    <!-- 全局 Loading 遮罩：含排隊進度條與 VIP 插隊密碼 -->
    <Transition name="fade">
      <div v-if="isGenerating" class="global-loading-overlay">

        <!-- Spinner -->
        <div class="futuristic-spinner">
          <div class="ring"></div>
          <div class="ring"></div>
          <div class="ring"></div>
        </div>

        <!-- 主標題 -->
        <div class="loading-text">{{ queuePosition > 0 ? 'WAITING' : 'GENERATING' }}</div>

        <!-- 排隊資訊面板 -->
        <div class="overlay-queue-panel">

          <!-- 等待人數（只在排隊中顯示） -->
          <div v-if="queuePosition > 0" class="oq-queue-notice">
            🕐 <strong>{{ queuePosition }}</strong> request(s) ahead — est. {{ estimatedWait }}s wait
          </div>

          <!-- 進度條：顯示實際生成進度 -->
          <div class="oq-progress-track">
            <div
              class="oq-progress-fill"
              :style="{ width: `${Math.round(jobProgress * 100)}%` }"
            ></div>
          </div>

          <!-- AI 當前狀態文字 -->
          <div class="oq-stage-label">
            {{ jobStageLabel || (queuePosition > 0 ? 'Waiting for previous tasks...' : 'Initializing...') }}
          </div>

          <!-- VIP 插隊密碼（僅在有人排前面時顯示）-->
          <Transition name="fade">
            <div v-if="queuePosition > 0" class="oq-vip">
              <div class="oq-vip-label">🔑 Priority Password <span class="oq-vip-hint">(once per minute)</span></div>
              <div class="oq-vip-row">
                <input
                  v-model="vipPasswordInput"
                  type="password"
                  placeholder="Enter priority password..."
                  class="oq-vip-input"
                  :disabled="!vipEligible || vipSubmitting"
                  @keyup.enter="emitVipSubmit"
                />
                <button
                  class="oq-vip-btn"
                  :disabled="!vipEligible || vipSubmitting || !vipPasswordInput"
                  @click="emitVipSubmit"
                >
                  {{ vipSubmitting ? '...' : 'Skip Queue' }}
                </button>
              </div>
              <div v-if="vipCooldownRemaining > 0" class="oq-vip-cooldown">
                ⏱ Cooldown: available again in {{ vipCooldownRemaining }}s
              </div>
              <div v-if="vipMessage" class="oq-vip-message" :class="vipMessageType">
                {{ vipMessage }}
              </div>
            </div>
          </Transition>

        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { watch, onUnmounted } from 'vue'
import { useAppState } from './composables/useAppState'
import { useQueueState } from './composables/useQueueState'
import Navigation from './components/layout/Navigation.vue'
import HeroSection from './components/layout/HeroSection.vue'
import MelodyEditor from './components/modes/MelodyEditor.vue'
import AdvancedMode from './components/modes/AdvancedMode.vue'
import RealtimePiano from './components/modes/RealtimePiano.vue'

const { currentAppMode, showHero, isGenerating, switchMode, startExperience } = useAppState()
const {
  currentJobId,
  queuePosition, jobProgress, jobStageLabel, estimatedWait,
  vipPasswordInput, vipEligible, vipCooldownRemaining, vipSubmitting,
  vipMessage, vipMessageType,
} = useQueueState()

// 觸發插隊：透過自訂事件讓 AdvancedMode 的 submitVipPassword 處理
// 因為 VIP 邏輯（重新 fetch）在 AdvancedMode，這裡用一個全域 EventBus 機制
const vipSubmitChannel = new BroadcastChannel('vip-submit')
const emitVipSubmit = () => {
  vipSubmitChannel.postMessage({ 
    jobId: currentJobId.value,
    password: vipPasswordInput.value 
  })
}

// 鎖定滾動邏輯
watch(isGenerating, (val) => {
  document.body.style.overflow = val ? 'hidden' : ''
})

const handleSwitchMode = (mode) => {
  switchMode(mode, false)
}

onUnmounted(() => {
  vipSubmitChannel.close()
})
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Outfit:wght@500;700;800;900&display=swap');

body {
  margin: 0;
  padding: 0;
  background-color: #f7f9fc;
}

.app-wrapper {
  font-family: 'Inter', sans-serif;
  color: #2c3e50;
  background-color: #f7f9fc;
  min-height: 100vh;
  margin: 0;
  padding: 0;
  overflow-x: hidden;
}

.app-content-layout {
  transition: filter 0.3s ease;
}

.app-content-layout.is-loading {
  filter: blur(2.5px) grayscale(20%);
}

.main-workspace {
  margin: 70px auto 20px;
  max-width: 100%;
  padding: 0 40px;
}

.global-loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(10px);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 0;
}

/* ── 遮罩內排隊面板 ── */
.overlay-queue-panel {
  margin-top: 28px;
  width: min(420px, 88vw);
  padding: 20px 24px;
  background: rgba(99, 102, 241, 0.07);
  border: 1px solid rgba(99, 102, 241, 0.22);
  border-radius: 18px;
  backdrop-filter: blur(8px);
  box-shadow: 0 8px 32px rgba(99, 102, 241, 0.1);
  font-family: 'Outfit', sans-serif;
}

.oq-queue-notice {
  font-size: 13px;
  font-weight: 600;
  color: #4338ca;
  background: rgba(99, 102, 241, 0.09);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 10px;
  padding: 8px 14px;
  margin-bottom: 14px;
  text-align: center;
}
.oq-queue-notice strong { color: #4f46e5; }

.oq-progress-track {
  height: 7px;
  background: rgba(0, 0, 0, 0.08);
  border-radius: 999px;
  overflow: hidden;
  margin-bottom: 7px;
}
.oq-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #818cf8, #6366f1, #a78bfa);
  border-radius: 999px;
  transition: width 0.5s ease;
  min-width: 4px;
}

.oq-stage-label {
  font-size: 12px;
  color: rgba(44, 62, 80, 0.55);
  font-weight: 500;
  margin-bottom: 2px;
}

/* VIP 插隊 */
.oq-vip {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(0, 0, 0, 0.07);
}
.oq-vip-label {
  font-size: 12px;
  font-weight: 700;
  color: #d97706;
  margin-bottom: 8px;
}
.oq-vip-hint {
  font-weight: 400;
  color: rgba(44, 62, 80, 0.5);
  font-size: 11px;
}
.oq-vip-row {
  display: flex;
  gap: 8px;
}
.oq-vip-input {
  flex: 1;
  padding: 8px 12px;
  background: rgba(255,255,255,0.8);
  border: 1px solid rgba(245, 158, 11, 0.35);
  border-radius: 8px;
  color: #2c3e50;
  font-size: 13px;
  font-family: 'Outfit', sans-serif;
  outline: none;
  transition: border-color 0.2s;
}
.oq-vip-input:focus { border-color: rgba(245,158,11,0.7); }
.oq-vip-input:disabled { opacity: 0.45; cursor: not-allowed; }
.oq-vip-input::placeholder { color: rgba(44,62,80,0.35); }
.oq-vip-btn {
  padding: 8px 18px;
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
.oq-vip-btn:hover:not(:disabled) { opacity: 0.88; transform: translateY(-1px); }
.oq-vip-btn:disabled { opacity: 0.38; cursor: not-allowed; }
.oq-vip-cooldown {
  margin-top: 6px;
  font-size: 11px;
  color: rgba(44,62,80,0.5);
}
.oq-vip-message {
  margin-top: 6px;
  font-size: 12px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 6px;
}
.oq-vip-message.success {
  color: #059669;
  background: rgba(5,150,105,0.07);
  border: 1px solid rgba(5,150,105,0.2);
}
.oq-vip-message.error {
  color: #dc2626;
  background: rgba(220,38,38,0.07);
  border: 1px solid rgba(220,38,38,0.2);
}

/* Fade transition (for VIP section) */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

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
  border-top-color: #4e54c8;
  animation: spinWave 1.2s linear infinite;
}
.futuristic-spinner .ring:nth-child(2) {
  width: 80%;
  height: 80%;
  top: 10%;
  left: 10%;
  border-right-color: #8f94fb;
  animation: spinWave 1.5s reverse infinite;
}
.futuristic-spinner .ring:nth-child(3) {
  width: 60%;
  height: 60%;
  top: 20%;
  left: 20%;
  border-bottom-color: #42b983;
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
  background: linear-gradient(90deg, #4e54c8, #8f94fb, #42b983);
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

/* Transitions */
.fade-up-enter-active,
.fade-up-leave-active {
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.fade-up-enter-from,
.fade-up-leave-to {
  opacity: 0;
  transform: translateY(30px);
}
</style>
