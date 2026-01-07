<template>
  <div class="sticky-player">
    <div class="player-shell">
      <!-- 左侧：歌曲信息区 -->
      <div class="player-left">
        <div class="cover-wrapper">
          <div class="cover" :style="coverStyle">
            <div class="cover-overlay"></div>
            <span v-if="!currentTrack?.cover" class="cover-fallback">♪</span>
          </div>
        </div>
        <div class="track-meta">
          <div class="track-title">{{ currentTrack?.title ?? "未选择歌曲" }}</div>
          <div class="track-artist">{{ currentTrack?.artist ?? "AI Composer" }}</div>
        </div>
      </div>

      <!-- 中央：播放控制区 -->
      <div class="player-center">
        <div class="control-buttons">
          <button 
            class="control-btn secondary" 
            :class="{ active: player.shuffle }" 
            title="随机播放" 
            @click="player.toggleShuffle"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M16 3h5v5M21 3l-5 5M8 21H3v-5M3 16l5-5M18 8a2 2 0 1 1-4 0 2 2 0 0 1 4 0zM6 16a2 2 0 1 1-4 0 2 2 0 0 1 4 0z"/>
            </svg>
          </button>
          <button class="control-btn secondary" title="上一首" @click="player.prev">
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/>
            </svg>
          </button>
          <button class="play-btn-main" title="播放/暂停" @click="player.togglePlay">
            <svg v-if="player.isPlaying" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
              <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
              <path d="M8 5v14l11-7z"/>
            </svg>
          </button>
          <button class="control-btn secondary" title="下一首" @click="player.next">
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/>
            </svg>
          </button>
          <button 
            class="control-btn secondary" 
            :class="{ active: player.repeatMode !== 'off' }" 
            :title="repeatLabel" 
            @click="player.cycleRepeatMode"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
            </svg>
            <span v-if="player.repeatMode === 'one'" class="repeat-badge">1</span>
          </button>
        </div>
        <div class="progress-section">
          <span class="time-text">{{ formatTime(player.currentTime) }}</span>
          <div class="progress-bar-wrapper">
            <input
              class="progress-slider"
              type="range"
              min="0"
              max="100"
              step="0.1"
              :value="progress"
              :style="progressStyle"
              @input="onSeek"
            />
          </div>
          <span class="time-text">{{ formatTime(player.duration) }}</span>
        </div>
      </div>

      <!-- 右侧：功能区 -->
      <div class="player-right">
        <div class="volume-control" @mouseenter="showVolumeSlider = true" @mouseleave="showVolumeSlider = false">
          <button 
            class="control-btn secondary" 
            :title="player.isMuted ? '取消静音' : '静音'" 
            @click="player.toggleMute"
          >
            <svg v-if="player.isMuted || volume === 0" viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
            </svg>
            <svg v-else-if="volume < 50" viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M18.5 12c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM5 9v6h4l5 5V4L9 9H5z"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
            </svg>
          </button>
          <div class="volume-slider-wrapper" v-show="showVolumeSlider">
            <input
              class="volume-slider"
              type="range"
              min="0"
              max="100"
              step="1"
              :value="volume"
              :style="volumeStyle"
              @input="onVolumeChange"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { usePlayerStore } from "../stores/player";

const player = usePlayerStore();
const showVolumeSlider = ref(false);

const currentTrack = computed(() => player.currentTrack);
const progress = computed(() => {
  if (!player.duration) return 0;
  return Math.min(100, (player.currentTime / player.duration) * 100);
});
const volume = computed(() => (player.isMuted ? 0 : player.volume * 100));
const repeatLabel = computed(() => {
  if (player.repeatMode === "one") return "单曲循环";
  if (player.repeatMode === "all") return "列表循环";
  return "不循环";
});

const coverStyle = computed(() => {
  if (currentTrack.value?.cover) {
    return { backgroundImage: `url(${currentTrack.value.cover})` };
  }
  return { backgroundImage: "linear-gradient(135deg, #1f2937, #0f172a)" };
});

const progressStyle = computed(() => {
  const percent = progress.value;
  return {
    background: `linear-gradient(
      to right,
      #3b82f6 0%,
      #6366f1 ${percent}%,
      rgba(255, 255, 255, 0.08) ${percent}%,
      rgba(255, 255, 255, 0.08) 100%
    )`
  };
});

const volumeStyle = computed(() => {
  const vol = volume.value;
  return {
    background: `linear-gradient(
      to right,
      #3b82f6 0%,
      #6366f1 ${vol}%,
      rgba(255, 255, 255, 0.08) ${vol}%,
      rgba(255, 255, 255, 0.08) 100%
    )`
  };
});

const formatTime = (seconds) => {
  if (!seconds && seconds !== 0) return "0:00";
  const safe = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};

const onSeek = (event) => {
  const value = Number(event.target.value) / 100;
  player.seekTo(value);
};

const onVolumeChange = (event) => {
  const value = Number(event.target.value) / 100;
  player.setVolume(value);
};


onMounted(() => {
  player.initAudio();
});
</script>

<style scoped>
:global(body) {
  --player-bg: rgba(8, 15, 30, 0.75);
  --player-border: rgba(99, 102, 241, 0.15);
  --player-accent: linear-gradient(135deg, #3b82f6, #6366f1, #8b5cf6);
  --player-accent-glow: rgba(99, 102, 241, 0.4);
  --player-text: #e2e8f0;
  --player-text-muted: #94a3b8;
  --player-glass: rgba(255, 255, 255, 0.03);
}

.sticky-player {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 30;
  pointer-events: none;
}

.player-shell {
  display: flex;
  align-items: center;
  gap: 24px;
  background: linear-gradient(
    135deg,
    rgba(8, 15, 30, 0.95) 0%,
    rgba(15, 23, 42, 0.98) 100%
  );
  border-top: 1px solid var(--player-border);
  border-radius: 0;
  box-shadow: 0 -4px 30px rgba(0, 0, 0, 0.4);
  padding: 12px 24px;
  backdrop-filter: blur(24px) saturate(180%);
  pointer-events: auto;
  transition: background 0.3s ease;
}

.player-shell:hover {
  background: rgba(10, 18, 35, 0.98);
}

/* 左侧：歌曲信息区 */
.player-left {
  display: flex;
  align-items: center;
  gap: 14px;
  /* Long titles should never push other controls out of place */
  flex: 0 1 360px;
  min-width: 240px;
  max-width: 360px;
  min-width: 0;
}

.cover-wrapper {
  position: relative;
  flex-shrink: 0;
}

.cover {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  background-size: cover;
  background-position: center;
  position: relative;
  overflow: hidden;
  box-shadow: 
    0 8px 24px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.05);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.cover:hover {
  transform: scale(1.05);
  box-shadow: 
    0 12px 32px rgba(0, 0, 0, 0.5),
    0 0 0 1px rgba(99, 102, 241, 0.3),
    0 0 20px rgba(99, 102, 241, 0.2);
}

.cover-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    135deg,
    rgba(99, 102, 241, 0.1) 0%,
    transparent 100%
  );
  opacity: 0;
  transition: opacity 0.3s ease;
}

.cover:hover .cover-overlay {
  opacity: 1;
}

.cover-fallback {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--player-text-muted);
  font-size: 28px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(59, 130, 246, 0.15));
}

.track-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.track-title {
  font-weight: 700;
  font-size: 15px;
  color: var(--player-text);
  letter-spacing: 0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.track-artist {
  font-size: 13px;
  color: var(--player-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

/* 播放栏“收藏”功能后端未实现：已移除按钮，避免误导用户 */

/* 中央：播放控制区 */
.player-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.control-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.control-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid var(--player-border);
  background: var(--player-glass);
  color: var(--player-text);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  position: relative;
}

.control-btn:hover {
  transform: translateY(-2px) scale(1.05);
  border-color: rgba(99, 102, 241, 0.5);
  background: rgba(99, 102, 241, 0.15);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
}

.control-btn.active {
  border-color: rgba(99, 102, 241, 0.6);
  background: rgba(99, 102, 241, 0.2);
  color: #818cf8;
  box-shadow: 0 0 16px rgba(99, 102, 241, 0.3);
}

.control-btn.secondary {
  width: 36px;
  height: 36px;
}

.play-btn-main {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  border: none;
  background: var(--player-accent);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 
    0 8px 24px rgba(99, 102, 241, 0.4),
    0 0 0 1px rgba(255, 255, 255, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transition: all 0.25s ease;
  margin: 0 4px;
}

.play-btn-main:hover {
  transform: translateY(-3px) scale(1.08);
  box-shadow: 
    0 12px 32px rgba(99, 102, 241, 0.5),
    0 0 0 1px rgba(255, 255, 255, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.25),
    0 0 30px rgba(99, 102, 241, 0.4);
}

.play-btn-main:active {
  transform: translateY(-1px) scale(1.05);
}

.repeat-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--player-accent);
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(99, 102, 241, 0.5);
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  max-width: 500px;
}

.time-text {
  font-size: 11px;
  color: var(--player-text-muted);
  font-feature-settings: "tnum";
  min-width: 40px;
  text-align: center;
}

.progress-bar-wrapper {
  flex: 1;
  position: relative;
  height: 6px;
}

.progress-slider {
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  outline: none;
  cursor: pointer;
  position: relative;
  transition: height 0.2s ease;
}

.progress-slider:hover {
  height: 8px;
}

.progress-slider::-webkit-slider-thumb {
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 
    0 0 0 2px rgba(99, 102, 241, 0.3),
    0 2px 8px rgba(0, 0, 0, 0.3),
    0 0 16px rgba(99, 102, 241, 0.5);
  border: none;
  cursor: grab;
  transition: all 0.2s ease;
}

.progress-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 
    0 0 0 2px rgba(99, 102, 241, 0.5),
    0 4px 12px rgba(0, 0, 0, 0.4),
    0 0 24px rgba(99, 102, 241, 0.6);
}

.progress-slider::-webkit-slider-thumb:active {
  cursor: grabbing;
  transform: scale(1.3);
}

.progress-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 
    0 0 0 2px rgba(99, 102, 241, 0.3),
    0 2px 8px rgba(0, 0, 0, 0.3),
    0 0 16px rgba(99, 102, 241, 0.5);
  border: none;
  cursor: grab;
  transition: all 0.2s ease;
}

.progress-slider::-moz-range-thumb:hover {
  transform: scale(1.2);
}

.progress-slider::-moz-range-thumb:active {
  cursor: grabbing;
  transform: scale(1.3);
}


/* 右侧：功能区 */
.player-right {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 120px;
  flex-shrink: 0;
  justify-content: flex-end;
}

.volume-control {
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
}

.volume-slider-wrapper {
  width: 100px;
  height: 6px;
  position: relative;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.volume-slider {
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  outline: none;
  cursor: pointer;
  transition: height 0.2s ease;
}

.volume-slider:hover {
  height: 8px;
}

.volume-slider::-webkit-slider-thumb {
  appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 
    0 0 0 2px rgba(99, 102, 241, 0.3),
    0 2px 6px rgba(0, 0, 0, 0.3),
    0 0 12px rgba(99, 102, 241, 0.4);
  border: none;
  cursor: grab;
  transition: all 0.2s ease;
}

.volume-slider::-webkit-slider-thumb:hover {
  transform: scale(1.2);
}

.volume-slider::-moz-range-thumb {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 
    0 0 0 2px rgba(99, 102, 241, 0.3),
    0 2px 6px rgba(0, 0, 0, 0.3),
    0 0 12px rgba(99, 102, 241, 0.4);
  border: none;
  cursor: grab;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .player-shell {
    gap: 16px;
    padding: 14px 20px;
  }
  
  .player-left {
    min-width: 200px;
    max-width: 300px;
    flex-basis: 300px;
  }
  
  .player-right {
    min-width: 100px;
  }
}

@media (max-width: 900px) {
  .player-shell {
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }
  
  .player-left {
    width: 100%;
    justify-content: space-between;
  }
  
  .player-center {
    width: 100%;
  }
  
  .player-right {
    width: 100%;
    justify-content: center;
  }
  
  .volume-slider-wrapper {
    width: 120px;
  }
}

@media (max-width: 600px) {
  .sticky-player {
    left: 12px;
    right: 12px;
    bottom: 12px;
  }
  
  .player-shell {
    padding: 12px;
    gap: 12px;
  }
  
  .cover {
    width: 56px;
    height: 56px;
  }
  
  .track-title {
    font-size: 14px;
  }
  
  .track-artist {
    font-size: 12px;
  }
  
  .play-btn-main {
    width: 52px;
    height: 52px;
  }
  
  .control-btn.secondary {
    width: 32px;
    height: 32px;
  }
  
  .progress-section {
    gap: 8px;
  }
  
  .time-text {
    font-size: 10px;
    min-width: 35px;
  }
}
</style>
