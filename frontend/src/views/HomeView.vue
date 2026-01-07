<template>
  <div class="page-shell">
    <div
      v-if="showActionToast"
      class="toast"
      :class="actionToastType === 'error' ? 'error-toast' : 'success-toast'"
    >
      {{ actionToastMessage }}
    </div>

    <SearchHeader v-model="searchKeyword" @search="gotoSearch" />

    <section class="panel carousel-panel">
      <Carousel :slides="carouselSlides" @slide-click="handleSlideClick" />
    </section>

    <div class="grid">
      <section class="panel">
        <div class="section-header">
          <div>
            <p class="eyebrow">热门精选</p>
            <h2>热门歌曲推荐</h2>
          </div>
        </div>
        <div class="songs-grid">
          <SongImageCard 
            v-for="song in songs.slice(0, 8)" 
            :key="song.id" 
            :song="song" 
            :cover="song.cover"
            @play="playHotSong"
            @card-click="gotoSongDetail"
          />
        </div>
      </section>

      <section class="panel">
        <div class="section-header">
          <div>
            <p class="eyebrow">创作者</p>
            <h2>推荐创作者</h2>
          </div>
        </div>
        <div class="creators-list">
          <CreatorCard
            v-for="creator in creators"
            :key="creator.id"
            :creator="creator"
            @card-click="gotoUserDetail"
            @follow="toggleFollowCreator"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import Carousel from "./components/Carousel.vue";
import SongImageCard from "./components/SongImageCard.vue";
import CreatorCard from "./components/CreatorCard.vue";
import { useAuthStore } from "../stores/auth";
import { useUiStore } from "../stores/ui";
import SearchHeader from "@/components/SearchHeader.vue";
import { fetchHotSongs, fetchRecommendedCreators } from "@/services/uiApi";
import { usePlayerStore } from "@/stores/player";
import { followUser, unfollowUser } from "@/services/searchApi";

import { toAbsoluteUrl } from "@/utils/url";

const auth = useAuthStore();
const ui = useUiStore();
const router = useRouter();
const player = usePlayerStore();
const searchKeyword = ref("");

// 通用动作 toast（用于关注/提示等）
const showActionToast = ref(false);
const actionToastMessage = ref("");
const actionToastType = ref("success"); // success | error
let actionToastTimer = null;

const triggerActionToast = (message, type = "success", durationMs = 1800) => {
  actionToastMessage.value = message || "";
  actionToastType.value = type;
  showActionToast.value = !!actionToastMessage.value;
  if (actionToastTimer) clearTimeout(actionToastTimer);
  actionToastTimer = setTimeout(() => {
    showActionToast.value = false;
    actionToastMessage.value = "";
    actionToastTimer = null;
  }, durationMs);
};

const gotoSearch = () => {
  const q = searchKeyword.value.trim();
  if (!q) return;
  router.push({ name: "search", query: { q, type: "all" } });
};

onMounted(() => {
  auth.refreshProfile();
});

const ensureLogin = () => {
  if (!auth.isLoggedIn) {
    ui.openLoginPanel();
    triggerActionToast("请先登录后再操作", "error");
    return false;
  }
  return true;
};

const playableHotSongs = computed(() => (songs.value || []).filter(s => (s?.url || "").trim()));

const playHotSong = song => {
  if (!song) return;
  const list = playableHotSongs.value;
  const idx = list.findIndex(item => item.id === song.id);
  if (idx < 0) return;
  player.setPlaylist(list, idx);
  player.playTrack(idx);
};

const gotoSongDetail = song => {
  const id = song?.id;
  if (!id) return;
  router.push({ name: "songDetail", params: { id } });
};

const gotoUserDetail = creator => {
  const id = creator?.id;
  if (!id) return;
  router.push({ name: "userPublic", params: { id } });
};

const toggleFollowCreator = async creator => {
  if (!creator) return;
  if (!ensureLogin()) return;
  const myId = auth.user?.id;
  if (myId && creator.id === myId) {
    triggerActionToast("无法关注自己", "error");
    return;
  }
  try {
    if (creator.is_followed) {
      await unfollowUser(creator.id);
      creator.is_followed = false;
      triggerActionToast("已取消关注", "success");
    } else {
      await followUser(creator.id);
      creator.is_followed = true;
      triggerActionToast("关注成功", "success");
    }
  } catch (err) {
    triggerActionToast(err?.message || "操作失败", "error");
  }
};

const loadHotSongs = async () => {
  try {
    const res = await fetchHotSongs({ limit: 8, window_days: 3 });
    if (Array.isArray(res) && res.length) {
      songs.value = res.map(item => ({
        ...item,
        authorName: item.author_name || "AI Composer",
        artist: item.author_name || "AI Composer",
        // 关键：在这里完成 URL 绝对化，并同时赋值给多个可能的字段名以保证兼容性
        cover: toAbsoluteUrl(item.cover_url || ""),
        coverImage: toAbsoluteUrl(item.cover_url || ""),
        url: toAbsoluteUrl(item.audio_url || ""),
        audio_url: item.audio_url || "",
        playCount: item.play_count ?? 0,
        // 用于 player 上报过滤
        status: "published",
        visibility: "public"
      }));
    }
  } catch (err) {
    console.error("加载热门歌曲失败:", err);
  }
};

const loadRecommendedCreators = async () => {
  try {
    const res = await fetchRecommendedCreators({ limit: 6 });
    if (Array.isArray(res) && res.length) {
      creators.value = res.map(item => ({
        id: item.id,
        name: item.name,
        followers: item.followers,
        handle: item.handle,
        is_followed: !!item.is_followed,
        // only normalize API results (placeholders should remain local assets)
        avatar: toAbsoluteUrl(item.avatar || "")
      }));
    }
  } catch {
    // ignore
  }
};

onMounted(() => {
  loadHotSongs();
  loadRecommendedCreators();
});

onBeforeUnmount(() => {
  if (actionToastTimer) {
    clearTimeout(actionToastTimer);
  }
});

const carouselSlides = ref([
  {
    image: "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=1200&h=400&fit=crop",
    title: "音乐生成",
    description: "使用 AI 一键生成专属音乐作品",
    path: "/generate"
  },
  {
    image: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=1200&h=400&fit=crop",
    title: "情绪识别",
    description: "通过音频分析识别当前情绪状态",
    path: "/emotion"
  },
  {
    image: "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=1200&h=400&fit=crop",
    title: "我的作品",
    description: "管理和查看您创建的音乐作品",
    path: "/works"
  }
]);

const handleSlideClick = payload => {
  const path = payload?.slide?.path;
  if (path) {
    router.push(path);
  }
};

const songs = ref([
  {
    id: 1,
    title: "Used To Feel Like Home",
    authorName: "Timotheus",
    mood: "delight",
    stats: { plays: "32K", likes: "11K", comments: "24" },
    coverImage: "/0a5e185b240483d80b5d5f5ebe1bb180.jpg"
  },
  {
    id: 2,
    title: "Got A Move",
    authorName: "Brutus",
    mood: "upbeat",
    stats: { plays: "3.5K", likes: "89", comments: "8" },
    coverImage: "/100ad6d24236b7cf0a40af50d3f4fabb_720.jpg"
  },
  {
    id: 3,
    title: "Summer Vibes",
    authorName: "EvilTyremancer",
    mood: "happy",
    stats: { plays: "15K", likes: "3.2K", comments: "45" },
    coverImage: "/19463b41f316917fb2753e1cf97777ef.jpg"
  },
  {
    id: 4,
    title: "Midnight Dreams",
    authorName: "MusicMaster",
    mood: "relaxing",
    stats: { plays: "28K", likes: "8.7K", comments: "156" },
    coverImage: "/2472760da37e1ee42bdac2feebd844f4.jpg"
  },
  {
    id: 5,
    title: "Electric Pulse",
    authorName: "BeatMaker",
    mood: "energetic",
    stats: { plays: "42K", likes: "15K", comments: "89" },
    coverImage: "/4109fd0848b160292c44659b397101c8_720.jpg"
  },
  {
    id: 6,
    title: "Neon Nights",
    authorName: "SoundWave",
    mood: "nostalgic",
    stats: { plays: "21K", likes: "6.3K", comments: "54" },
    coverImage: "/6168b0078172146bda06427cf6dcca6e.jpg"
  },
  {
    id: 7,
    title: "Ocean Waves",
    authorName: "MelodyMaker",
    mood: "calm",
    stats: { plays: "18K", likes: "4.5K", comments: "67" },
    coverImage: "/9824df28ed03024e6fec7476b0215dcc_720.jpg"
  },
  {
    id: 8,
    title: "City Lights",
    authorName: "RhythmKing",
    mood: "energetic",
    stats: { plays: "25K", likes: "7.2K", comments: "92" },
    coverImage: "/af4dbbe08c41f1f08c3f273a81c14bea_720.jpg"
  }
]);

const creators = ref([
  {
    id: 1,
    name: "Timotheus",
    followers: "5.2K followers",
    handle: "@timotheus",
    is_followed: false,
    avatar: "/avatars/02567c1fd7d6e84c7bc3f5eb83fbb20b.jpg"
  },
  {
    id: 2,
    name: "Brutus",
    followers: "17K followers",
    handle: "@brutus",
    is_followed: false,
    avatar: "/avatars/13b2894291a2545053b7b80245b3ad49.jpg"
  },
  {
    id: 3,
    name: "EvilTyremancer",
    followers: "14K followers",
    handle: "@eviltyremancer",
    is_followed: false,
    avatar: "/avatars/2dc212f966be73e8ff964aac88208167.jpg"
  },
  {
    id: 4,
    name: "MusicMaster",
    followers: "23K followers",
    handle: "@musicmaster",
    is_followed: false,
    avatar: "/avatars/32b72fbc42357a2646642f721e3557fe.jpg"
  },
  {
    id: 5,
    name: "BeatMaker",
    followers: "8.7K followers",
    handle: "@beatmaker",
    is_followed: false,
    avatar: "/avatars/b5e9f4ec3ba35ebf2ef7aaf134f63072_0.jpg"
  },
  {
    id: 6,
    name: "SoundWave",
    followers: "12.5K followers",
    handle: "@soundwave",
    is_followed: false,
    avatar: "/avatars/bfd6dd67f27836dbe2df91b7b70daeae_0.jpg"
  },
  {
    id: 7,
    name: "MelodyMaker",
    followers: "9.8K followers",
    handle: "@melodymaker",
    is_followed: false,
    avatar: "/avatars/c9fa4c3f8bb8e93a7e8512ad6b101bb0_0.jpg"
  }
]);
</script>

<style scoped>
.page-shell {
  width: 100%;
  min-height: 0;
  padding: 12px 12px 32px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-sizing: border-box;
}

.panel {
  background: rgba(15, 23, 42, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 18px;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.6);
  padding: 20px;
  backdrop-filter: blur(8px);
}

.carousel-panel {
  padding: 18px 18px 22px;
}

.grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 18px;
  min-height: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h2 {
  margin: 4px 0 0;
  font-size: 18px;
}

.eyebrow {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.6);
}

.view-all {
  font-size: 13px;
  color: #60a5fa;
  cursor: pointer;
  font-weight: 600;
  transition: color 0.15s ease;
}

.view-all:hover {
  color: #7cc1ff;
}

.expand-section {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.16);
}

.expand-button {
  background: none;
  border: none;
  color: #60a5fa;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.expand-button:hover {
  color: #7cc1ff;
  transform: translateY(-1px);
}

.expand-button svg {
  transition: transform 0.2s ease;
}

.expand-button:hover svg {
  transform: translateY(2px);
}

.scroll-area {
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(255, 255, 255, 0.02);
  overflow-y: auto;
  max-height: 70vh;
  scrollbar-width: none;
}

.songs-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  padding: 14px;
}

.toast {
  position: fixed;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 16px;
  border-radius: 12px;
  font-weight: 700;
  color: #071c12;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.96), rgba(52, 211, 153, 0.96));
  border: 1px solid rgba(74, 222, 128, 0.4);
  box-shadow: 0 12px 32px rgba(16, 185, 129, 0.3);
  z-index: 10000;
  animation: toast-in 0.18s ease;
  letter-spacing: 0.02em;
}

.toast.success-toast {
  color: #071c12;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.96), rgba(52, 211, 153, 0.96));
  border: 1px solid rgba(74, 222, 128, 0.4);
  box-shadow: 0 12px 32px rgba(16, 185, 129, 0.3);
}

.toast.error-toast {
  color: #fff;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.95), rgba(248, 113, 113, 0.9));
  border: 1px solid rgba(248, 113, 113, 0.35);
  box-shadow: 0 12px 32px rgba(239, 68, 68, 0.25);
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translate(-50%, -6px);
  }
  to {
    opacity: 1;
    transform: translate(-50%, 0);
  }
}

.scroll-area::-webkit-scrollbar {
  width: 0;
  height: 0;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  height: auto;
}

.list.compact {
  gap: 10px;
}

.creators-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
}

.list::-webkit-scrollbar {
  width: 8px;
}

.list::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.03);
}

.list::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.45);
  border-radius: 4px;
}

.list::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.6);
}

@media (max-width: 1100px) {
  .grid {
    grid-template-columns: 1.4fr 1fr;
  }
}

@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }

  .login-grid {
    grid-template-columns: 1fr;
  }

  .panel-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .cta {
    align-self: flex-start;
  }

  .songs-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
}

@media (max-width: 600px) {
  .songs-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

@media (max-width: 600px) {
  .page-shell {
    padding: 10px 10px 28px;
  }

  .panel {
    padding: 16px;
  }
}
</style>
