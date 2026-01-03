<template>
  <div 
    class="generation-card" 
    :class="{ 
      'is-playing': isPlaying, 
      'is-generating': isGenerating 
    }"
  >
    <div class="card-left" @click="!isGenerating && handlePlay()">
      <div class="cover-wrapper" :class="{ 'spinning': isGenerating }">
        <img v-if="music.cover" :src="music.cover" :alt="music.title" class="cover-img" />
        <div v-else class="cover-placeholder">
          <span v-if="isGenerating" class="loading-icon">🎵</span>
          <span v-else>🎵</span>
        </div>
        <div v-if="!isGenerating" class="duration-badge">{{ formatDuration(music.duration) }}</div>
        
        <!-- Hover Overlay for Play/Pause -->
        <div v-if="!isGenerating" class="play-overlay">
          <svg v-if="isPlaying" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </div>
      </div>
    </div>

    <div class="card-middle" @click="!isGenerating && handlePlay()">
      <div class="music-info">
        <h4 class="music-title">{{ music.title }}</h4>
        <div class="music-tag" :class="{ 'tag-generating': isGenerating }">
          {{ isGenerating ? '正在生成音乐...' : 'v1.0-ai' }}
        </div>
      </div>
      <p class="music-desc">{{ isGenerating ? '正在为您编织绝妙旋律，请稍候' : (music.mood || 'AI 创作的精美旋律') }}</p>
    </div>

    <div class="card-right">
      <div class="menu-container" v-if="!isGenerating && showAddButton" v-click-outside="closeMenu">
        <button class="more-btn" @click.stop="toggleMenu">
          <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path d="M6 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm12 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm-6 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
          </svg>
        </button>
        
        <transition name="fade">
          <div v-if="showMenu" class="dropdown-menu">
            <button 
              class="menu-item" 
              :disabled="isAdded || isAdding"
              @click.stop="handleAddToWorks"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M12 5v14M5 12h14"/>
              </svg>
              <span>{{ isAdded ? "已加入本地作品" : isAdding ? "保存中..." : "加入本地作品" }}</span>
            </button>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

const props = defineProps({
  music: {
    type: Object,
    required: true
  },
  isPlaying: {
    type: Boolean,
    default: false
  },
  isAdded: {
    type: Boolean,
    default: false
  },
  isAdding: {
    type: Boolean,
    default: false
  },
  isGenerating: {
    type: Boolean,
    default: false
  },
  showAddButton: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['play', 'add-to-works']);

const showMenu = ref(false);

const toggleMenu = () => {
  if (props.isGenerating) return;
  showMenu.value = !showMenu.value;
};

const closeMenu = () => {
  showMenu.value = false;
};

const handlePlay = () => {
  if (props.isGenerating) return;
  emit('play', props.music);
};

const handleAddToWorks = () => {
  if (props.isGenerating || props.isAdded || props.isAdding) return;
  emit('add-to-works', props.music);
  showMenu.value = false;
};

const formatDuration = (seconds) => {
  if (!seconds && seconds !== 0) return "0:00";
  const safe = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

// Simple directive for clicking outside
const vClickOutside = {
  mounted(el, binding) {
    el.clickOutsideEvent = (event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value(event);
      }
    };
    document.addEventListener("click", el.clickOutsideEvent);
  },
  unmounted(el) {
    document.removeEventListener("click", el.clickOutsideEvent);
  },
};
</script>

<style scoped>
.generation-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  transition: all 0.2s ease;
  cursor: pointer;
  position: relative;
}

.generation-card:hover:not(.is-generating) {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateX(4px);
}

.generation-card.is-playing {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.4);
}

.generation-card.is-generating {
  opacity: 0.9;
  cursor: default;
}

.card-left {
  flex-shrink: 0;
}

.cover-wrapper {
  position: relative;
  width: 64px;
  height: 64px;
  border-radius: 8px;
  overflow: hidden;
  background: #1e293b;
  transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.cover-wrapper.spinning {
  animation: rotate 8s linear infinite;
  border-radius: 50%;
  border: 3px solid #1e293b;
  box-shadow: 
    0 0 0 2px rgba(59, 130, 246, 0.5),
    0 0 20px rgba(59, 130, 246, 0.3),
    inset 0 0 10px rgba(0, 0, 0, 0.8);
}

/* 旋转时在中间加一个“唱片孔” */
.cover-wrapper.spinning::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  background: #0f172a;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.5);
  z-index: 5;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  background: linear-gradient(135deg, #1e293b, #334155);
}

.loading-icon {
  animation: pulse-note 1.5s infinite ease-in-out;
  color: #60a5fa;
  filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.6));
}

@keyframes pulse-note {
  0% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.1); opacity: 1; }
  100% { transform: scale(0.8); opacity: 0.5; }
}

.duration-badge {
  position: absolute;
  bottom: 4px;
  left: 4px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 4px;
  backdrop-filter: blur(4px);
}

.play-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.generation-card:hover .play-overlay,
.generation-card.is-playing .play-overlay {
  opacity: 1;
}

.generating-ring-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.2);
}

.ring-loader {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.card-middle {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.music-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.music-title {
  font-size: 14px;
  font-weight: 600;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
}

.music-tag {
  font-size: 10px;
  padding: 1px 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  color: #94a3b8;
  white-space: nowrap;
}

.tag-generating {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  animation: pulse 2s infinite;
}

.music-desc {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
}

.card-right {
  flex-shrink: 0;
}

.menu-container {
  position: relative;
}

.more-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.more-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #f1f5f9;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 4px;
  min-width: 160px;
  z-index: 50;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

.menu-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #e2e8f0;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.menu-item:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.menu-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}
</style>
