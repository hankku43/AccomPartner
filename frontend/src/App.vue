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

    <!-- 全局 Loading 遮罩：獨立於模糊容器外，保持清晰 -->
    <Transition name="fade">
      <div v-if="isGenerating" class="global-loading-overlay">
        <div class="futuristic-spinner">
          <div class="ring"></div>
          <div class="ring"></div>
          <div class="ring"></div>
        </div>
        <div class="loading-text">GENERATING</div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { watch } from 'vue'
import { useAppState } from './composables/useAppState'
import Navigation from './components/layout/Navigation.vue'
import HeroSection from './components/layout/HeroSection.vue'
import MelodyEditor from './components/modes/MelodyEditor.vue'
import AdvancedMode from './components/modes/AdvancedMode.vue'
import RealtimePiano from './components/modes/RealtimePiano.vue'

const { currentAppMode, showHero, isGenerating, switchMode, startExperience } = useAppState()

// 鎖定滾動邏輯
watch(isGenerating, (val) => {
  document.body.style.overflow = val ? 'hidden' : ''
})

const handleSwitchMode = (mode) => {
  switchMode(mode, false)
}
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
