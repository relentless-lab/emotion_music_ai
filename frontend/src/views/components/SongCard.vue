<template>
  <div class="song-card">
    <button class="play-btn" @click="playSong">
      <span class="play-icon">▶</span>
    </button>

    <div class="song-content">
      <div class="song-header">
        <span class="music-icon">🎵</span>
        <h3 class="song-title">{{ song.title }}</h3>
      </div>

      <div class="song-genres">
        <span class="genre-icon">🎼</span>
        <span v-for="(genre, index) in song.genres" :key="genre" class="genre-tag">
          {{ genre }}<span v-if="index < song.genres.length - 1">, </span>
        </span>
      </div>

      <div class="song-platform">
        <span class="platform-icon">🏢</span>
        <strong>{{ song.platform }}</strong>
        <span v-if="song.mood" class="mood">
          <span class="mood-icon">😊</span>
          {{ song.mood }}
        </span>
      </div>
      <div class="song-stats">
        <div class="stat">
          <span class="stat-icon">▶️</span>
          <span class="stat-value">{{ song.stats.plays }}</span>
          <span class="stat-label">播放</span>
        </div>
        <div class="stat">
          <span class="stat-icon">❤️</span>
          <span class="stat-value">{{ song.stats.likes }}</span>
          <span class="stat-label">喜欢</span>
        </div>
        <div class="stat">
          <span class="stat-icon">💬</span>
          <span class="stat-value">{{ song.stats.comments }}</span>
          <span class="stat-label">评论</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  song: {
    type: Object,
    required: true
  }
});

const playSong = () => {
  console.log("播放歌曲:", props.song.title);
};
</script>

<style scoped>
.song-card {
  background: rgba(17, 24, 39, 0.92);
  border: 1px solid rgba(94, 234, 212, 0.16);
  border-radius: 14px;
  padding: 16px;
  cursor: pointer;
  position: relative;
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.35);
}

.song-card:hover {
  border-color: rgba(94, 234, 212, 0.4);
  transform: translateY(-1px);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.45);
}

.play-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 36px;
  height: 36px;
  background: linear-gradient(120deg, #5eead4, #60a5fa);
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.play-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 12px 26px rgba(96, 165, 250, 0.45);
}

.play-icon {
  color: #0b1021;
  font-size: 0.9rem;
  margin-left: 1px;
  font-weight: 700;
}

.song-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.song-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.music-icon {
  font-size: 1.2rem;
}

.song-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #f8fafc;
  margin: 0;
  line-height: 1.4;
}

.song-genres {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.92rem;
  color: rgba(226, 232, 240, 0.78);
  line-height: 1.4;
  flex-wrap: wrap;
}

.genre-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

.genre-tag {
  display: inline;
}

.song-platform {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.92rem;
  color: rgba(226, 232, 240, 0.9);
}

.platform-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

.song-platform strong {
  color: #e0f2fe;
  font-weight: 700;
}

.mood {
  display: flex;
  align-items: center;
  gap: 4px;
  color: rgba(94, 234, 212, 0.9);
  font-size: 0.88rem;
}

.mood-icon {
  font-size: 0.82rem;
}

.song-stats {
  display: flex;
  gap: 18px;
  margin-top: 4px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 6px;
  color: rgba(226, 232, 240, 0.86);
}

.stat-icon {
  font-size: 0.8rem;
}

.stat-value {
  font-weight: 800;
  color: #f8fafc;
  font-size: 0.92rem;
}

.stat-label {
  color: rgba(148, 163, 184, 0.85);
  font-size: 0.78rem;
}
</style>

