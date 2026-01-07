<template>
  <div class="song-image-card" @click="handleCardClick">
    <div class="image-wrapper">
      <template v-if="coverUrl">
        <img :src="coverUrl" :alt="title" class="cover-image" />
      </template>
      <template v-else>
        <div class="cover-fallback">{{ titleInitial }}</div>
      </template>

      <div class="overlay">
        <button class="play-button" type="button" @click.stop="handlePlay">
          <svg viewBox="0 0 24 24" fill="white" width="24" height="24">
            <path d="M8 5v14l11-7z" />
          </svg>
        </button>
        <div v-if="showActions" class="hover-actions">
          <button
            class="icon-button like-button"
            :class="{ active: isLiked }"
            type="button"
            @click.stop="handleLike"
          >
            <svg v-if="isLiked" viewBox="0 0 24 24" fill="#f87171" width="18" height="18">
              <path
                d="M12 21s-6.5-4.35-9-9.35C1.5 6.5 3.5 3 7 3a4.5 4.5 0 0 1 5 3 4.5 4.5 0 0 1 5-3c3.5 0 5.5 3.5 4 8.65C18.5 16.65 12 21 12 21z"
              />
            </svg>
            <svg
              v-else
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              width="18"
              height="18"
            >
              <path
                d="M12 21s-6.5-4.35-9-9.35C1.5 6.5 3.5 3 7 3a4.5 4.5 0 0 1 5 3 4.5 4.5 0 0 1 5-3c3.5 0 5.5 3.5 4 8.65C18.5 16.65 12 21 12 21z"
              />
            </svg>
          </button>
          <button class="icon-button more-button" type="button" @click.stop="handleMore">
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <circle cx="12" cy="5" r="2" />
              <circle cx="12" cy="12" r="2" />
              <circle cx="12" cy="19" r="2" />
            </svg>
          </button>
        </div>
      </div>
      <div class="play-count">
        <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" width="14" height="14">
          <path d="M12 4v10.55a3 3 0 1 0 2 2.83V7h4V4z" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <span>{{ playCountLabel }}</span>
      </div>
      <div v-if="authorName" class="author-badge" :title="authorName">
        @{{ authorName }}
      </div>
    </div>
    <div class="song-title" :title="title">{{ title }}</div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  song: {
    type: Object,
    required: true
  },
  cover: {
    type: String,
    default: ""
  },
  playCount: {
    type: [Number, String],
    default: null
  },
  author: {
    type: String,
    default: ""
  },
  liked: {
    type: Boolean,
    default: undefined
  },
  showActions: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(["play", "like", "more", "card-click"]);

const coverUrl = computed(() => props.cover || props.song.coverImage || props.song.cover_url || props.song.coverUrl || "");
const title = computed(() => props.song.title || props.song.name || "未命名");
const authorName = computed(() => props.author || props.song.authorName || props.song.author?.username || "");
const titleInitial = computed(() => title.value.slice(0, 1).toUpperCase());
const playCountLabel = computed(() => {
  const value = props.playCount ?? props.song.play_count ?? props.song.playCount ?? props.song.stats?.plays ?? 0;
  if (typeof value === "number") {
    if (value >= 10000) return `${Math.round(value / 1000)}K`;
    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  }
  return value ?? 0;
});
const isLiked = computed(() => (props.liked !== undefined ? props.liked : props.song.liked || props.song.is_liked || false));

const handlePlay = () => emit("play", props.song);
const handleCardClick = () => emit("card-click", props.song);
const handleLike = () => emit("like", props.song);
const handleMore = () => emit("more", props.song);
</script>

<style scoped>
.song-image-card {
  cursor: pointer;
  transition: transform 0.22s ease, box-shadow 0.22s ease;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  /* Important for CSS grid: allow card to shrink below min-content width */
  min-width: 0;
}

.song-image-card:hover {
  transform: translateY(-6px) scale(1.02);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35);
  z-index: 2;
}

.image-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: 14px;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.7), rgba(30, 41, 59, 0.8));
  margin-bottom: 4px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
}

.cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  transition: transform 0.3s ease;
  display: block;
}

.cover-fallback {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 32px;
  letter-spacing: 0.02em;
  color: #e5e7eb;
  background: linear-gradient(135deg, #4f46e5, #06b6d4);
}

.song-image-card:hover .cover-image {
  transform: scale(1.04);
}

.overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.12), rgba(0, 0, 0, 0.45));
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.song-image-card:hover .overlay {
  opacity: 1;
}

.play-button {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: rgba(79, 133, 255, 0.95);
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
  box-shadow: 0 10px 22px rgba(79, 133, 255, 0.45);
}

.play-button:hover {
  transform: scale(1.08);
  background: rgba(79, 133, 255, 1);
}

.hover-actions {
  position: absolute;
  right: 10px;
  bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-button {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: none;
  background: rgba(0, 0, 0, 0.42);
  color: #e5e7eb;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.icon-button:hover {
  transform: translateY(-1px);
  background: rgba(0, 0, 0, 0.6);
}

.like-button.active {
  background: rgba(248, 113, 113, 0.18);
  color: #fca5a5;
}

.play-count {
  position: absolute;
  top: 10px;
  right: 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(0, 0, 0, 0.58);
  padding: 6px 10px;
  border-radius: 999px;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.author-badge {
  position: absolute;
  bottom: 10px;
  left: 10px;
  max-width: calc(100% - 20px);
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(4px);
  padding: 4px 8px;
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  pointer-events: none;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.song-title {
  color: #f8fafc;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
  padding: 0 4px;
}
</style>
