<template>
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
        <button @click="$emit('start')" class="hero-btn primary-btn-glow">
          <span class="btn-text">Start Experience</span>
        </button>
        <button @click="$emit('switchMode', 'advanced')" class="hero-btn secondary-btn">
          <span class="btn-text">Explore Use Cases</span>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useAppState } from '../../composables/useAppState'

const { showHero } = useAppState()
defineEmits(['start', 'switchMode'])

const musicParticlesCanvas = ref(null)
let animationFrameId = null

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

onMounted(() => {
  initMusicParticles()
})
</script>

<style scoped>
.hero-section {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: radial-gradient(circle at center, #ffffff 0%, #f7f9fc 100%);
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
  color: #2c3e50;
  margin-bottom: 20px;
  letter-spacing: -1.5px;
  font-family: 'Outfit', sans-serif;
}

.text-gradient {
  background: linear-gradient(135deg, #4e54c8, #8f94fb, #ff6a88);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-subtitle {
  font-size: 1.2rem;
  color: #7f8c8d;
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
    transform 0.25s ease,
    box-shadow 0.25s ease;
  font-family: 'Outfit', sans-serif;
}

.primary-btn-glow {
  background: linear-gradient(135deg, #4e54c8 0%, #8f94fb 60%, #ff6a88 100%);
  background-size: 200% auto;
  color: white;
  box-shadow:
    0 8px 24px rgba(78, 84, 200, 0.35),
    0 2px 8px rgba(0, 0, 0, 0.1);
  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease,
    background-position 0.4s ease;
}
.primary-btn-glow:hover {
  transform: translateY(-3px);
  background-position: right center;
  box-shadow:
    0 14px 36px rgba(78, 84, 200, 0.45),
    0 0 0 4px rgba(143, 148, 251, 0.18),
    0 4px 12px rgba(255, 106, 136, 0.2);
}
.primary-btn-glow:active {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(78, 84, 200, 0.35);
}

.secondary-btn {
  background: white;
  color: #2c3e50;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
  border: 1.5px solid rgba(78, 84, 200, 0.18);
  position: relative;
  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease,
    color 0.25s ease,
    border-color 0.25s ease;
  z-index: 0;
}
.secondary-btn::before {
  content: '';
  position: absolute;
  inset: -1.5px;
  border-radius: 30px;
  background: linear-gradient(135deg, #4e54c8, #8f94fb, #ff6a88);
  opacity: 0;
  z-index: -1;
  transition: opacity 0.3s ease;
}
.secondary-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 28px;
  background: white;
  z-index: -1;
  transition: background 0.25s ease;
}
.secondary-btn:hover {
  transform: translateY(-3px);
  color: #4e54c8;
  border-color: transparent;
  box-shadow:
    0 10px 28px rgba(78, 84, 200, 0.15),
    0 0 0 1.5px rgba(143, 148, 251, 0.3);
}
.secondary-btn:hover::before {
  opacity: 1;
}
.secondary-btn:hover::after {
  background: rgba(248, 248, 255, 0.95);
}
.secondary-btn:active {
  transform: translateY(-1px);
}
</style>
