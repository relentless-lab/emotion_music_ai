<template>
  <div class="search-page">
    <SearchHeader v-model="keyword" @search="triggerSearch" />
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        class="tab"
        :class="{ active: activeTab === tab.value }"
        type="button"
        @click="switchTab(tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="result-panel">
      <div v-if="loading" class="state">加载中...</div>
      <div v-else>
        <template v-if="activeTab === 'all' || activeTab === 'song'">
          <div class="section-head">
            <h3>单曲</h3>
          </div>
          <div v-if="songs.length === 0" class="state">暂无符合条件的单曲</div>
          <div v-else class="song-list">
            <div
              v-for="song in songs"
              :key="song.id"
              class="song-row"
              @mouseenter="hoverId = song.id"
              @mouseleave="hoverId = null"
            >
              <div
                class="cover"
                :class="{ disabled: !song.url }"
                :style="coverStyle(song.cover_url)"
                role="button"
                tabindex="0"
                :title="song.url ? '点击播放' : '暂无可播放地址'"
                @click.stop="song.url && playSong(song)"
                @keydown.enter.stop.prevent="song.url && playSong(song)"
                @keydown.space.stop.prevent="song.url && playSong(song)"
              >
                <span class="play-count">▶ {{ song.play_count || 0 }}</span>
              </div>
              <div class="song-info">
                <div class="title" :title="song.title">{{ song.title }}</div>
                <div class="meta">
                  <span>作者：{{ song.author_name }}</span>
                  <span>点赞 {{ song.like_count || 0 }}</span>
                </div>
              </div>
              <div class="row-actions" :class="{ show: hoverId === song.id }">
                <button
                  class="icon-btn"
                  type="button"
                  :disabled="likeLoadingId === song.id"
                  @click.stop="toggleLike(song)"
                  :title="song.liked ? '取消点赞' : '点赞'"
                >
                  <span :class="{ liked: song.liked }">❤</span>
                </button>
                <button class="icon-btn" type="button" @click.stop="downloadSong(song)" title="下载">⬇</button>
                <button class="icon-btn" type="button" @click.stop="gotoSong(song.id)" title="详情">⋯</button>
              </div>
            </div>
          </div>
        </template>

        <template v-if="activeTab === 'all' || activeTab === 'user'">
          <div class="section-head users-head">
            <h3>用户</h3>
          </div>
          <div v-if="users.length === 0" class="state">暂无符合条件的用户</div>
          <div v-else class="user-list">
            <div v-for="user in users" :key="user.id" class="user-card">
              <div class="avatar" :style="avatarStyle(user.avatar)">
                <span v-if="!user.avatar">{{ initials(user.username) }}</span>
              </div>
              <div class="user-info">
                <div class="name">{{ user.username }}</div>
                <div class="bio">{{ user.bio || "这个人很神秘，还没有简介" }}</div>
                <div class="meta">
                  <span>粉丝 {{ user.followers }}</span>
                  <span>关注 {{ user.following }}</span>
                </div>
              </div>
              <div class="row-actions show">
                <button
                  class="icon-btn"
                  type="button"
                  :disabled="followLoadingId === user.id"
                  @click="toggleFollow(user)"
                  :title="user.is_followed ? '取消关注' : '关注'"
                >
                  <span :class="{ liked: user.is_followed }">❤</span>
                </button>
                <button class="icon-btn" type="button" @click="gotoUser(user.id)" title="详情">⋯</button>
              </div>
            </div>
          </div>
        </template>
      </div>

      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";
import { usePlayerStore } from "@/stores/player";
import { followUser, likeWork, searchAll, unfollowUser, unlikeWork } from "@/services/searchApi";
import SearchHeader from "@/components/SearchHeader.vue";

const API_BASE_URL = ((import.meta.env.VITE_API_BASE_URL || "").trim()
  || (import.meta.env.DEV ? "http://127.0.0.1:8000" : window.location.origin))
  .replace(/\/+$/, "")
  .replace(/\/api$/, "");
const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const ui = useUiStore();
const player = usePlayerStore();

const tabs = [
  { label: "综合", value: "all" },
  { label: "单曲", value: "song" },
  { label: "用户", value: "user" }
];

const keyword = ref("");
const activeTab = ref("all");
const loading = ref(false);
const errorMessage = ref("");
const songs = ref([]);
const users = ref([]);
const likeLoadingId = ref(null);
const followLoadingId = ref(null);
const hoverId = ref(null);

const initials = name => (name || "").slice(0, 1).toUpperCase();
const toAbsoluteUrl = url => {
  if (!url) return "";
  if (url.startsWith("http") || url.startsWith("data:") || url.startsWith("blob:")) return url;
  // Keep consistent with `src/services/api.js` default in dev and avoid using Vite (5173) as asset host.
  const base = API_BASE_URL || window.location.origin;
  const fileBase = base.replace(/\/api$/, "");
  return url.startsWith("/") ? `${fileBase}${url}` : `${fileBase}/${url}`;
};

const coverStyle = url => {
  const abs = toAbsoluteUrl(url);
  return {
    backgroundImage: abs
      ? `linear-gradient(180deg, rgba(0,0,0,0.12) 0%, rgba(0,0,0,0.28) 100%), url(${abs})`
      : "linear-gradient(135deg, #1e3a8a, #312e81)",
    backgroundSize: "cover",
    backgroundPosition: "center",
    backgroundColor: "#0f172a"
  };
};
const avatarStyle = url => ({
  backgroundImage: url ? `url(${toAbsoluteUrl(url)})` : "linear-gradient(135deg, #0ea5e9, #6366f1)",
  backgroundSize: "cover",
  backgroundPosition: "center"
});

const switchTab = tab => {
  activeTab.value = tab;
  triggerSearch();
};

const applyQueryFromRoute = () => {
  const q = (route.query?.q || "").toString();
  keyword.value = q;
  const tab = (route.query?.type || "all").toString();
  activeTab.value = ["all", "song", "user"].includes(tab) ? tab : "all";
};

function normalizeSong(item) {
  const coverUrl = item?.cover_url || item?.coverUrl || "";
  const audioUrl = item?.audio_url || item?.audioUrl || item?.url || "";
  return {
    ...item,
    // 统一字段
    cover_url: coverUrl,
    // player store 读取的是 url/cover/title/artist
    url: toAbsoluteUrl(audioUrl),
    cover: toAbsoluteUrl(coverUrl),
    artist: item?.author_name || item?.authorName || "AI Composer",
    play_count: item?.play_count ?? item?.playCount ?? 0,
    like_count: item?.like_count ?? item?.likeCount ?? 0,
    liked: item?.liked ?? item?.is_liked ?? item?.isLiked ?? false,
  };
}

const triggerSearch = async () => {
  const q = keyword.value.trim();
  if (!q) return;
  loading.value = true;
  errorMessage.value = "";
  try {
    const res = await searchAll({
      query: q,
      type: activeTab.value
    });
    songs.value = (res?.songs || []).map(item => normalizeSong(item));
    users.value = res?.users || [];
    router.replace({ path: "/search", query: { q, type: activeTab.value } });
  } catch (err) {
    errorMessage.value = err?.message || "搜索失败，请稍后重试";
  } finally {
    loading.value = false;
  }
};

const playableSongs = computed(() => (songs.value || []).filter(s => (s?.url || "").trim()));

const playSong = song => {
  if (!song) return;
  const list = playableSongs.value;
  const idx = list.findIndex(item => item.id === song.id);
  if (idx < 0) return;
  player.setPlaylist(list, idx);
  player.playTrack(idx);
};

const ensureLogin = () => {
  if (!auth.isLoggedIn) {
    ui.openLoginPanel();
    errorMessage.value = "请先登录后再操作";
    return false;
  }
  return true;
};

const toggleLike = async song => {
  if (!ensureLogin()) return;
  likeLoadingId.value = song.id;
  try {
    if (song.liked) {
      await unlikeWork(song.id);
      song.like_count = Math.max((song.like_count || 0) - 1, 0);
      song.liked = false;
    } else {
      await likeWork(song.id);
      song.like_count = (song.like_count || 0) + 1;
      song.liked = true;
    }
  } catch (err) {
    errorMessage.value = err?.message || "操作失败";
  } finally {
    likeLoadingId.value = null;
  }
};

const toggleFollow = async user => {
  if (!ensureLogin()) return;
  followLoadingId.value = user.id;
  try {
    if (user.is_followed) {
      await unfollowUser(user.id);
      user.is_followed = false;
      user.followers = Math.max((user.followers || 0) - 1, 0);
    } else {
      await followUser(user.id);
      user.is_followed = true;
      user.followers = (user.followers || 0) + 1;
    }
  } catch (err) {
    errorMessage.value = err?.message || "操作失败";
  } finally {
    followLoadingId.value = null;
  }
};

const gotoSong = id => {
  router.push({ name: "songDetail", params: { id } });
};

const gotoUser = id => {
  router.push({ name: "userPublic", params: { id } });
};

const _guessExtFromUrl = (url) => {
  if (!url) return "wav";
  const m = String(url).match(/\.([a-zA-Z0-9]+)(\?|#|$)/);
  const ext = (m?.[1] || "").toLowerCase();
  // Whitelist common audio extensions
  if (["wav", "mp3", "flac", "ogg", "m4a", "aac"].includes(ext)) return ext;
  return "wav";
};

const _sanitizeFilename = (name) => {
  const s = (name || "").toString().trim() || "music";
  // Windows reserved chars: \ / : * ? " < > |
  return s.replace(/[\\/:*?"<>|]+/g, "_").slice(0, 80) || "music";
};

const _triggerBrowserDownload = (href, filename) => {
  const a = document.createElement("a");
  a.href = href;
  // NOTE: download attr may be ignored for cross-origin URLs in some browsers;
  // we still set it when possible for better UX.
  if (filename) a.download = filename;
  a.rel = "noopener";
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

const downloadSong = async (song) => {
  const url = (song?.url || "").trim();
  if (!url) {
    errorMessage.value = "暂无可下载的音频地址";
    return;
  }

  errorMessage.value = "";
  const ext = _guessExtFromUrl(url);
  const baseName = _sanitizeFilename(song?.title || `song_${song?.id || ""}`);
  const filename = `${baseName}.${ext}`;

  // Preferred: fetch -> blob -> objectURL (ensures bytes correctness when CORS allows)
  try {
    const res = await fetch(url, { method: "GET" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const blobUrl = URL.createObjectURL(blob);
    try {
      _triggerBrowserDownload(blobUrl, filename);
    } finally {
      // Give the browser a moment to start the download before revoking
      setTimeout(() => URL.revokeObjectURL(blobUrl), 10_000);
    }
    return;
  } catch (err) {
    // Fallback: direct URL (works for OSS signed URLs / cross-origin without CORS)
    try {
      _triggerBrowserDownload(url, filename);
      return;
    } catch {
      // ignore and show error below
    }
    errorMessage.value = `下载失败：${err?.message || "请稍后重试"}`;
  }
};

watch(
  () => route.query,
  () => {
    applyQueryFromRoute();
    if (keyword.value) triggerSearch();
  },
  { immediate: true }
);

onMounted(() => {
  applyQueryFromRoute();
  if (keyword.value) {
    triggerSearch();
  }
});
</script>

<style scoped>
.search-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.tabs {
  display: flex;
  gap: 32px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0;
  background: transparent;
  margin-bottom: 10px;
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 12px 4px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-weight: 600;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  outline: none;
}

.tab:hover {
  color: #e2e8f0;
}

.tab.active {
  color: #3b82f6;
  font-weight: 700;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: #3b82f6;
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
  border-radius: 2px;
}

.result-panel {
  min-height: 320px;
  padding: 6px 0 24px;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 10px 0;
}

.song-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.song-row {
  display: grid;
  /* Use minmax(0, 1fr) so long titles won't push action buttons off-screen */
  grid-template-columns: 56px minmax(0, 1fr) auto;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 12px;
  transition: all 0.16s ease;
}

.song-row:hover {
  background: rgba(255, 255, 255, 0.04);
  box-shadow: 0 8px 26px rgba(0, 0, 0, 0.25);
}

.cover {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  position: relative;
  overflow: hidden;
  background-size: cover;
  background-position: center;
  cursor: pointer;
  outline: none;
}

.cover.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.cover:focus-visible {
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.65);
}

.play-count {
  position: absolute;
  right: 6px;
  bottom: 6px;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.55);
  font-size: 11px;
}

.song-info {
  min-width: 0;
}

.song-info .title {
  font-weight: 700;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.song-info .meta {
  display: flex;
  gap: 12px;
  color: rgba(229, 231, 235, 0.7);
  font-size: 12px;
}

.row-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.16s ease;
  flex-shrink: 0;
}

.row-actions.show {
  opacity: 1;
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 6px;
}

.user-card {
  display: grid;
  grid-template-columns: 64px 1fr auto;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 12px;
  transition: all 0.16s ease;
}

.user-card:hover {
  background: rgba(255, 255, 255, 0.04);
  box-shadow: 0 8px 26px rgba(0, 0, 0, 0.25);
}

.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  display: grid;
  place-items: center;
  color: #fff;
  font-weight: 700;
  font-size: 18px;
}

.user-info .name {
  font-weight: 700;
}

.user-info .bio {
  color: rgba(229, 231, 235, 0.8);
  font-size: 13px;
  margin: 4px 0;
}

.user-info .meta {
  display: flex;
  gap: 10px;
  color: rgba(229, 231, 235, 0.7);
  font-size: 12px;
}

.state {
  padding: 12px;
  color: rgba(229, 231, 235, 0.8);
}

.error {
  color: #fca5a5;
  margin-top: 8px;
}

.pill-btn,
.icon-btn,
.cta {
  height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.04);
  color: #e5e7eb;
  cursor: pointer;
}

.icon-btn {
  width: 34px;
  padding: 0;
  display: grid;
  place-items: center;
}

.icon-btn > span {
  display: block;
  line-height: 1;
}

.cta.primary {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border: none;
}

.liked {
  color: #f87171;
}

@media (max-width: 800px) {
  .song-row,
  .user-card {
    grid-template-columns: 1fr;
  }

  .row-actions {
    justify-content: flex-end;
  }
}
</style>
