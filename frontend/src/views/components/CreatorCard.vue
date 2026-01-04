<template>
  <div class="creator-card" @click="$emit('card-click', creator)">
    <div class="creator-info">
      <img
        v-if="creator.avatar"
        :src="creator.avatar"
        :alt="creator.name"
        class="creator-avatar"
      />
      <div v-else class="creator-avatar placeholder">
        {{ creator.name.charAt(0) }}
      </div>

      <div class="creator-details">
        <h4 class="creator-name">{{ creator.name }}</h4>
        <div class="creator-meta">
          <span class="followers">{{ creator.followers }}</span>
          <span class="handle">{{ creator.handle }}</span>
        </div>
      </div>
    </div>

    <button
      class="follow-button"
      :class="{ 'is-followed': creator.is_followed }"
      type="button"
      @click.stop="$emit('follow', creator)"
    >
      {{ creator.is_followed ? "已关注" : "关注" }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  creator: {
    type: Object,
    required: true
  }
});

defineEmits(["card-click", "follow"]);
</script>

<style scoped>
.creator-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border: 1px solid rgba(94, 234, 212, 0.18);
  border-radius: 12px;
  background: rgba(17, 24, 39, 0.92);
  transition: all 0.2s ease;
  cursor: pointer;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.32);
}

.creator-card:hover {
  border-color: rgba(94, 234, 212, 0.35);
  transform: translateY(-1px);
  box-shadow: 0 16px 38px rgba(0, 0, 0, 0.4);
}

.creator-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.creator-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.creator-avatar.placeholder {
  background: linear-gradient(135deg, #5eead4, #60a5fa);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0b1021;
  font-weight: 700;
  font-size: 1rem;
}

.creator-details {
  flex: 1;
  min-width: 0;
}

.creator-name {
  font-size: 0.95rem;
  font-weight: 700;
  color: #f8fafc;
  margin: 0 0 4px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.creator-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.followers {
  font-size: 0.82rem;
  color: rgba(226, 232, 240, 0.86);
  font-weight: 600;
}

.handle {
  font-size: 0.78rem;
  color: rgba(148, 163, 184, 0.9);
}

.follow-button {
  background: linear-gradient(120deg, #5eead4, #60a5fa);
  color: #0b1021;
  border: none;
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 0.85rem;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  flex-shrink: 0;
  white-space: nowrap;
}

.follow-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(96, 165, 250, 0.35);
}

.follow-button:active {
  transform: translateY(0);
}

.follow-button.is-followed {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(226, 232, 240, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.16);
  box-shadow: none;
}

.follow-button.is-followed:hover {
  background: rgba(255, 255, 255, 0.12);
  box-shadow: none;
}
</style>

