<template>
  <aside class="generate-sidebar">
    <div class="sidebar-header">
      <div class="header-left">
        <h3 class="sidebar-title">生成列表</h3>
        <span class="track-count">{{ tracks.length }} 首作品</span>
      </div>
      <div class="header-actions">
        <button class="icon-btn" title="搜索">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="sidebar-content custom-scrollbar">
      <div v-if="tracks.length === 0" class="empty-list">
        <div class="empty-icon">🎧</div>
        <p>暂无生成作品</p>
      </div>
      <div v-else class="track-list">
        <MusicGenerationCard
          v-for="track in sortedTracks"
          :key="track.id"
          :music="track"
          :is-playing="currentPlayingId === track.id"
          :is-generating="track.status === 'generating'"
          :show-add-button="!((track.can_save === false) || (track.canSave === false))"
          :is-added="addedWorkIds.has(track.id || track.music_file_id)"
          :is-adding="addingWorkId === (track.id || track.music_file_id)"
          @play="handlePlay"
          @add-to-works="handleAddToWorks"
        />
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from "vue";
import MusicGenerationCard from "./MusicGenerationCard.vue";

const props = defineProps({
  tracks: {
    type: Array,
    default: () => []
  },
  currentPlayingId: {
    type: [String, Number],
    default: null
  },
  addedWorkIds: {
    type: Object,
    default: () => new Set()
  },
  addingWorkId: {
    type: [String, Number],
    default: null
  }
});

const emit = defineEmits(['play', 'add-to-works']);

// Sort tracks by creation time (newest first)
const sortedTracks = computed(() => {
  return [...props.tracks].sort((a, b) => {
    return new Date(b.createdAt) - new Date(a.createdAt);
  });
});

const handlePlay = (track) => {
  emit('play', track);
};

const handleAddToWorks = (track) => {
  emit('add-to-works', track);
};
</script>

<style scoped>
.generate-sidebar {
  width: 350px;
  background: rgba(17, 24, 39, 0.5);
  backdrop-filter: blur(24px);
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  height: 100%;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.sidebar-title {
  font-size: 16px;
  font-weight: 700;
  margin: 0;
  color: #f1f5f9;
}

.track-count {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #94a3b8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.icon-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #f1f5f9;
  border-color: rgba(255, 255, 255, 0.2);
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.track-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-list {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #475569;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.3;
}

.empty-list p {
  font-size: 14px;
  margin: 0;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
}

@media (max-width: 1024px) {
  .generate-sidebar {
    width: 100%;
    height: auto;
    max-height: 400px;
    border-left: none;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }
}
</style>

