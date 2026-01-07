<template>
  <div class="song-detail-page">
    <div class="panel" v-if="work">
      <div class="hero">
        <div class="cover" :style="coverStyle(workCover)">
          <span class="badge">单曲</span>
        </div>
        <div class="info">
          <h2>{{ work.title }}</h2>
          <p class="author" @click="gotoAuthor(work.author.id)">
            {{ work.author.username }} · 粉丝 {{ work.author.followers }}
          </p>
          <div class="meta">
            <span>点赞 {{ work.like_count }}</span>
            <span>播放 {{ work.play_count }}</span>
            <span v-if="work.tags">标签：{{ work.tags }}</span>
          </div>
          <div class="actions">
            <button class="ghost-btn" type="button" :disabled="likeLoading" @click="toggleLike">
              {{ work.liked ? "已点赞" : "点赞" }}
            </button>
            <button class="cta primary" type="button" @click="gotoAuthor(work.author.id)">
              查看用户
            </button>
          </div>
        </div>
      </div>
      <div class="desc">
        <h4>描述</h4>
        <p>{{ work.description || "暂无描述" }}</p>
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
import { fetchPublicWork, likeWork, unlikeWork } from "@/services/searchApi";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const ui = useUiStore();
const API_BASE_URL = ((import.meta.env.VITE_API_BASE_URL || "").trim()
  || (import.meta.env.DEV ? "http://127.0.0.1:8000" : window.location.origin))
  .replace(/\/+$/, "")
  .replace(/\/api$/, "");

const work = ref(null);
const loading = ref(false);
const likeLoading = ref(false);
const errorMessage = ref("");

const toAbsoluteUrl = url => {
  if (!url) return "";
  if (url.startsWith("http") || url.startsWith("data:") || url.startsWith("blob:")) return url;
  const base = API_BASE_URL || window.location.origin;
  return url.startsWith("/") ? `${base}${url}` : `${base}/${url}`;
};

const workCover = computed(() => {
  const url = work.value?.cover_url || work.value?.coverUrl || "";
  return url ? toAbsoluteUrl(url) : "";
});

const coverStyle = url => ({
  backgroundImage: url
    ? `linear-gradient(180deg, rgba(0,0,0,0.12) 0%, rgba(0,0,0,0.28) 100%), url(${url})`
    : "linear-gradient(135deg, #0ea5e9, #6366f1)",
  backgroundSize: "cover",
  backgroundPosition: "center"
});

const loadWork = async () => {
  loading.value = true;
  errorMessage.value = "";
  try {
    const id = route.params.id;
    work.value = await fetchPublicWork(id);
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

const toggleLike = async () => {
  if (!ensureLogin() || !work.value) return;
  likeLoading.value = true;
  try {
    if (work.value.liked) {
      await unlikeWork(work.value.id);
      work.value.liked = false;
      work.value.like_count = Math.max((work.value.like_count || 0) - 1, 0);
    } else {
      await likeWork(work.value.id);
      work.value.liked = true;
      work.value.like_count = (work.value.like_count || 0) + 1;
    }
  } catch (err) {
    errorMessage.value = err?.message || "操作失败";
  } finally {
    likeLoading.value = false;
  }
};

const gotoAuthor = id => {
  router.push({ name: "userPublic", params: { id } });
};

onMounted(() => {
  loadWork();
});
</script>

<style scoped>
.song-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 4px;
}

.panel {
  background: rgba(15, 23, 42, 0.85);
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.15);
  padding: 12px;
}

.hero {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 16px;
}

.cover {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 10px;
  position: relative;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.badge {
  position: absolute;
  left: 6px;
  top: 6px;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.5);
  font-size: 10px;
  backdrop-filter: blur(4px);
}

.info {
  display: flex;
  flex-direction: column;
  justify-content: center;
  /* Allow ellipsis inside grid/flex to work correctly */
  min-width: 0;
}

.info h2 {
  margin: 0 0 2px;
  font-size: 18px;
  font-weight: 800;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.author {
  color: #a5b4fc;
  cursor: pointer;
  font-size: 13px;
  margin-bottom: 4px;
  opacity: 0.9;
}

.author:hover {
  text-decoration: underline;
}

.meta {
  display: flex;
  gap: 10px;
  color: rgba(229, 231, 235, 0.6);
  margin: 2px 0 8px;
  font-size: 11px;
}

.actions {
  display: flex;
  gap: 8px;
}

.desc {
  margin-top: 10px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  padding: 8px 10px;
  border: 1px solid rgba(148, 163, 184, 0.1);
}

.desc h4 {
  margin: 0 0 4px;
  font-size: 13px;
  color: #94a3b8;
  font-weight: 600;
}

.desc p {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: rgba(229, 231, 235, 0.8);
}

.state {
  text-align: center;
  color: rgba(229, 231, 235, 0.8);
  padding: 40px;
}

.ghost-btn,
.cta {
  height: 30px;
  padding: 0 12px;
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(255, 255, 255, 0.04);
  color: #e5e7eb;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.ghost-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(148, 163, 184, 0.5);
}

.cta.primary {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border: none;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}

.cta.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.35);
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
    text-align: center;
  }
  .cover {
    width: 120px;
    margin: 0 auto;
  }
  .actions {
    justify-content: center;
  }
  .meta {
    justify-content: center;
  }
}
</style>
