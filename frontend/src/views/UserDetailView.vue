<template>
  <div class="user-detail-page">
    <div class="panel" v-if="profile">
      <div class="hero">
        <div class="avatar" :style="avatarStyle(profile.user.avatar)">
          <span v-if="!profile.user.avatar">{{ initials(profile.user.username) }}</span>
        </div>
        <div class="info">
          <div class="name-row">
            <h2>{{ profile.user.username }}</h2>
            <div class="follow-badge">
              <span @click="openList('followers')">粉丝 {{ profile.user.followers }}</span>
              <span @click="openList('following')">关注 {{ profile.user.following }}</span>
            </div>
          </div>
          <p class="bio">{{ profile.user.bio || "暂无简介" }}</p>
          <div class="meta">
            <span>总点赞 {{ profile.user.likesReceived }}</span>
            <span>本月播放 {{ profile.user.playsThisMonth }}</span>
            <span>作品 {{ profile.user.works }}</span>
          </div>
          <div class="actions">
            <button
              class="ghost-btn"
              type="button"
              :disabled="followLoading"
              @click="toggleFollow"
            >
              {{ profile.user.is_followed ? "已关注" : "关注" }}
            </button>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-head">
          <h3>发布的作品</h3>
        </div>
        <div v-if="profile.works.length === 0" class="state">暂无作品</div>
        <div v-else class="works-grid">
          <SongImageCard
            v-for="work in workList"
            :key="work.id"
            :song="work"
            :cover="workCoverUrl(work)"
            :play-count="work.play_count"
            :liked="work.liked"
            :show-actions="true"
            @card-click="gotoSong(work.id)"
            @play="playWork(work)"
            @like="toggleLike(work)"
            @more="gotoSong(work.id)"
          />
        </div>
      </div>

      <div v-if="profile.liked_songs?.length" class="section">
        <div class="section-head">
          <h3>喜欢的音乐</h3>
        </div>
        <div class="liked-music-list">
          <div v-for="work in profile.liked_songs" :key="work.id" class="liked-item" @click="gotoSong(work.id)">
            <div class="liked-cover" :style="coverStyle(work.cover_url || work.coverUrl)" @click.stop="playWork(work)">
              <div class="play-overlay">
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M8 5v14l11-7z"/>
                </svg>
              </div>
            </div>
            <div class="liked-info">
              <div class="liked-title">{{ work.title }}</div>
              <div class="liked-meta">
                <span>点赞 {{ work.like_count }}</span>
                <span class="dot">·</span>
                <span>播放 {{ work.play_count }}</span>
              </div>
            </div>
            <div class="liked-actions">
              <button class="more-btn" title="详情" @click.stop="gotoSong(work.id)">⋯</button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="panel state">{{ loading ? "加载中..." : errorMessage }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import { fetchPublicUser, followUser, likeWork, unfollowUser, unlikeWork } from "@/services/searchApi";
import { usePlayerStore } from "@/stores/player";
import SongImageCard from "@/views/components/SongImageCard.vue";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const ui = useUiStore();
const player = usePlayerStore();
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

const profile = ref(null);
const loading = ref(false);
const errorMessage = ref("");
const followLoading = ref(false);
const likeLoadingId = ref(null);

const initials = name => (name || "").slice(0, 1).toUpperCase();
const toAbsoluteUrl = url => {
  if (!url) return "";
  if (url.startsWith("http") || url.startsWith("data:") || url.startsWith("blob:")) return url;
  const base = API_BASE_URL || window.location.origin;
  return url.startsWith("/") ? `${base}${url}` : `${base}/${url}`;
};
const avatarStyle = url => ({
  backgroundImage: url ? `url(${toAbsoluteUrl(url)})` : "linear-gradient(135deg, #22c55e, #3b82f6)",
  backgroundSize: "cover",
  backgroundPosition: "center"
});
const coverStyle = url => {
  const abs = toAbsoluteUrl(url);
  return {
    backgroundImage: abs
      ? `linear-gradient(180deg, rgba(0,0,0,0.12) 0%, rgba(0,0,0,0.28) 100%), url(${abs})`
      : "linear-gradient(135deg, #0ea5e9, #6366f1)",
    backgroundSize: "cover",
    backgroundPosition: "center",
    backgroundColor: "#111827"
  };
};

const normalizeWork = w => ({
  ...w,
  cover_url: w.cover_url || w.coverUrl || "",
  url: toAbsoluteUrl(w.url || w.audio_url || w.audioUrl || ""),
  liked: w.liked ?? w.is_liked ?? w.isLiked ?? false,
  play_count: w.play_count ?? w.playCount ?? 0
});

const loadProfile = async () => {
  loading.value = true;
  errorMessage.value = "";
  try {
    const id = route.params.id;
    profile.value = await fetchPublicUser(id);
    // 确保封面占位
    profile.value.works = (profile.value.works || []).map(normalizeWork);
    profile.value.liked_songs = (profile.value.liked_songs || []).map(w => ({
      ...w,
      cover_url: w.cover_url || w.coverUrl || ""
    }));
  } catch (err) {
    errorMessage.value = err?.message || "加载失败";
  } finally {
    loading.value = false;
  }
};

const ensureLogin = () => {
  if (!auth.isLoggedIn) {
    ui.openLoginPanel();
    return false;
  }
  return true;
};

const toggleFollow = async () => {
  if (!ensureLogin() || !profile.value) return;
  followLoading.value = true;
  try {
    if (profile.value.user.is_followed) {
      await unfollowUser(profile.value.user.id);
      profile.value.user.is_followed = false;
      profile.value.user.followers = Math.max((profile.value.user.followers || 0) - 1, 0);
    } else {
      await followUser(profile.value.user.id);
      profile.value.user.is_followed = true;
      profile.value.user.followers = (profile.value.user.followers || 0) + 1;
    }
  } catch (err) {
    errorMessage.value = err?.message || "操作失败";
  } finally {
    followLoading.value = false;
  }
};

const gotoSong = id => {
  router.push({ name: "songDetail", params: { id } });
};

const openList = type => {
  // placeholder hook for后续弹出粉丝/关注列表
};

const workList = computed(() => profile.value?.works || []);

const workCoverUrl = work => toAbsoluteUrl(work.cover_url || work.coverUrl || "");

const playWork = work => {
  if (!workList.value.length) return;
  const index = workList.value.findIndex(item => item.id === work.id);
  player.setPlaylist(workList.value, index >= 0 ? index : 0);
  player.playTrack(index >= 0 ? index : 0);
};

const toggleLike = async work => {
  if (!ensureLogin() || !work?.id || likeLoadingId.value === work.id) return;
  likeLoadingId.value = work.id;
  try {
    if (work.liked) {
      await unlikeWork(work.id);
      work.liked = false;
      work.like_count = Math.max((work.like_count || 0) - 1, 0);
    } else {
      await likeWork(work.id);
      work.liked = true;
      work.like_count = (work.like_count || 0) + 1;
    }
  } catch (err) {
    errorMessage.value = err?.message || "操作失败";
  } finally {
    likeLoadingId.value = null;
  }
};

onMounted(() => {
  loadProfile();
});
</script>

<style scoped>
.user-detail-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px;
}

.panel {
  background: rgba(15, 23, 42, 0.9);
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  padding: 12px;
}

.hero {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 16px;
  align-items: center;
}

.avatar {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, #22c55e, #3b82f6);
  display: grid;
  place-items: center;
  font-size: 24px;
  font-weight: 800;
  color: #fff;
}

.info {
  display: flex;
  flex-direction: column;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.name-row h2 {
  margin: 0;
  font-size: 20px;
}

.follow-badge {
  display: inline-flex;
  gap: 10px;
  color: #c7d2fe;
  font-size: 12px;
}

.bio {
  margin: 4px 0;
  color: rgba(229, 231, 235, 0.8);
  font-size: 13px;
}

.meta {
  display: flex;
  gap: 10px;
  color: rgba(229, 231, 235, 0.65);
  font-size: 12px;
}

.actions {
  margin-top: 8px;
  align-self: flex-start;
}

.section {
  margin-top: 16px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.section-head h3 {
  font-size: 16px;
  margin: 0;
}

.works-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  padding: 4px 0 0;
}

/* --- 喜欢的音乐：单列横向布局 --- */
.liked-music-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

.liked-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.liked-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateX(6px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.liked-cover {
  width: 64px;
  height: 64px;
  border-radius: 10px;
  background-size: cover;
  background-position: center;
  position: relative;
  flex-shrink: 0;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.play-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.liked-item:hover .play-overlay {
  opacity: 1;
}

.liked-info {
  flex: 1;
  min-width: 0;
}

.liked-title {
  font-weight: 700;
  font-size: 16px;
  color: #f8fafc;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.liked-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(229, 231, 235, 0.6);
}

.liked-meta .dot {
  opacity: 0.5;
}

.liked-actions {
  flex-shrink: 0;
}

.more-btn {
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.4);
  font-size: 18px;
  padding: 4px;
  cursor: pointer;
  border-radius: 6px;
  line-height: 1;
}

.more-btn:hover {
  color: #f1f5f9;
  background: rgba(255, 255, 255, 0.08);
}

.work-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}

.work-card {
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.03);
}

.cover {
  position: relative;
  aspect-ratio: 4 / 3;
}

.play-count {
  position: absolute;
  right: 6px;
  bottom: 6px;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.5);
  font-size: 10px;
}

.work-info {
  padding: 8px;
}

.work-info .title {
  font-weight: 700;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.work-info .meta {
  display: flex;
  gap: 8px;
  color: rgba(229, 231, 235, 0.6);
  font-size: 11px;
  margin: 4px 0;
}

.actions .cta.primary {
  width: 100%;
}

.state {
  text-align: center;
  color: rgba(229, 231, 235, 0.8);
}

.ghost-btn,
.cta {
  height: 30px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.04);
  color: #e5e7eb;
  cursor: pointer;
  font-size: 12px;
}

.cta.primary {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border: none;
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
    text-align: center;
  }

  .avatar {
    width: 80px;
    height: 80px;
    margin: 0 auto;
    font-size: 20px;
  }
  
  .actions {
    align-self: center;
  }
  
  .name-row, .meta {
    justify-content: center;
  }
}

@media (max-width: 1200px) {
  .works-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .works-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .works-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .liked-music-list {
    grid-template-columns: 1fr;
  }
}
</style>
