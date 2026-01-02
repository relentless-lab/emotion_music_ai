<template>
  <div class="generated-music-card">
    <div class="image-wrapper">
      <img 
        v-if="music.cover" 
        :src="music.cover" 
        :alt="musicTitle" 
        class="cover-image" 
      />
      <div v-else class="cover-placeholder">
        <span class="music-icon">🎵</span>
      </div>
      <div class="overlay">
        <button class="play-button" @click.stop="handlePlay">
          <svg viewBox="0 0 24 24" fill="white" width="24" height="24">
            <path d="M8 5v14l11-7z"/>
          </svg>
        </button>
      </div>
    </div>
    <div class="music-title">{{ musicTitle }}</div>
    <div v-if="showAddButton" class="add-to-works-section">
      <button 
        class="add-to-works-btn" 
        :class="{ 'added': isAdded, 'adding': isAdding }"
        :disabled="isAdding || isAdded"
        @click.stop="handleAddToWorks"
      >
        <svg v-if="!isAdded" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <path d="M12 5v14M5 12h14"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
          <path d="M20 6L9 17l-5-5"/>
        </svg>
        <span>{{ isAdded ? "已加入 ✅" : isAdding ? "保存中..." : "加入本地作品" }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  music: {
    type: Object,
    required: true
  },
  isAdded: {
    type: Boolean,
    default: false
  },
  isAdding: {
    type: Boolean,
    default: false
  },
  showAddButton: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['play', 'add-to-works']);

const musicTitle = computed(() => {
  // 优先使用 title，如果 title 是默认值或空，则使用 user_input
  const title = props.music.title;
  if (title && title !== "AI 生成作品" && title !== "AI 生成音乐") {
    // 如果标题过长，截取前30个字符
    return title.length > 30 ? title.substring(0, 30) + '...' : title;
  }
  // 使用用户输入作为标题
  const userInput = props.music.user_input || props.music.prompt;
  if (userInput) {
    return userInput.length > 30 ? userInput.substring(0, 30) + '...' : userInput;
  }
  return "AI 生成音乐";
});

const handlePlay = () => {
  emit('play', props.music);
};

const handleAddToWorks = () => {
  if (props.isAdded || props.isAdding) return;
  emit('add-to-works', props.music);
};
</script>

<style scoped>
.generated-music-card {
  cursor: pointer;
  transition: transform 0.2s ease;
  width: 200px;
  max-width: 100%;
}

.generated-music-card:hover {
  transform: translateY(-4px);
}

.image-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.6);
  margin-bottom: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  transition: transform 0.3s ease;
}

.generated-music-card:hover .cover-image {
  transform: scale(1.05);
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(96, 165, 250, 0.3), rgba(139, 92, 246, 0.3));
}

.music-icon {
  font-size: 48px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.generated-music-card:hover .overlay {
  opacity: 1;
}

.play-button {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(79, 133, 255, 0.9);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s ease, background 0.2s ease;
  box-shadow: 0 4px 12px rgba(79, 133, 255, 0.4);
}

.play-button:hover {
  transform: scale(1.1);
  background: rgba(79, 133, 255, 1);
}

.music-title {
  color: #f8fafc;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
  padding: 0 4px;
  margin-bottom: 8px;
}

.add-to-works-section {
  margin-top: 8px;
  display: flex;
  justify-content: center;
}

.add-to-works-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  color: #e2e8f0;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  backdrop-filter: blur(8px);
}

.add-to-works-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(59, 130, 246, 0.4);
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.25);
  transform: translateY(-1px);
}

.add-to-works-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.add-to-works-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.add-to-works-btn.added {
  background: rgba(34, 197, 94, 0.15);
  border-color: rgba(34, 197, 94, 0.3);
  color: #86efac;
}

.add-to-works-btn.adding {
  opacity: 0.7;
  cursor: wait;
}

.add-to-works-btn svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}
</style>

