<template>
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
        @click="$emit('switchMode', 'quick')"
      >
        Melody Editor
      </button>
      <button
        :class="{ active: currentAppMode === 'advanced' && !showHero }"
        @click="$emit('switchMode', 'advanced')"
      >
        MIDI Upload
      </button>
      <button
        :class="{ active: currentAppMode === 'realtime' && !showHero }"
        @click="$emit('switchMode', 'realtime')"
      >
        Realtime Piano
      </button>
    </div>
  </nav>
</template>

<script setup>
import { useAppState } from '../../composables/useAppState'
const { currentAppMode, showHero } = useAppState()
defineEmits(['switchMode'])
</script>

<style scoped>
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
  color: #2c3e50;
  letter-spacing: -0.5px;
  font-family: 'Outfit', sans-serif;
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
  color: #7f8c8d;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.nav-menu button:hover {
  background: rgba(78, 84, 200, 0.05);
  color: #4e54c8;
}

.nav-menu button.active {
  background: #4e54c8;
  color: white !important;
  box-shadow: 0 4px 10px rgba(78, 84, 200, 0.3);
}
</style>
