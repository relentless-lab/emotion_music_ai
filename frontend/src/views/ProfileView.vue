<template>
  <div class="profile-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">个人中心</p>
        <h1>个人资料</h1>
        <p class="muted">管理你的基础信息与数据概览，保持账号形象一致。</p>
      </div>
      <div class="header-actions">
        <button class="ghost-btn" type="button" @click="isEditing ? cancelEdit() : startEdit()" :disabled="saving || !isLoggedIn">
          {{ isEditing ? "取消" : "编辑" }}
        </button>
        <button class="primary-btn" type="button" @click="saveProfile" :disabled="!isEditing || saving || !isLoggedIn">
          {{ saving ? "保存中..." : "保存" }}
        </button>
      </div>
    </header>

    <!-- 顶部 Toast：用于“保存成功/失败”等即时提示，避免提示在页面底部用户看不到 -->
    <div v-if="toastMessage" class="toast" :class="toastType === 'error' ? 'toast-error' : 'toast-success'">
      {{ toastMessage }}
    </div>

    <section class="card base-info">
      <div class="card-title">
        <span>基本信息</span>
        <span class="status-chip">
          <span class="dot online"></span>
          {{ statusText }}
        </span>
      </div>
      <div class="base-grid">
        <div class="avatar-block">
          <div
            class="avatar-circle"
            :class="{ editable: isLoggedIn }"
            :style="avatarCircleStyle"
            :title="isLoggedIn ? '点击更换头像' : ''"
            @click="isLoggedIn ? triggerAvatarPick() : null"
          >
            <span v-if="!currentAvatarUrl">{{ (form.name || auth.user?.name || "U").slice(0, 1).toUpperCase() }}</span>
            <div v-if="isLoggedIn" class="avatar-hover">
              <div class="avatar-hover-inner">
                <span class="avatar-hover-icon">✎</span>
                <span>{{ avatarUploading ? "上传中..." : "更换头像" }}</span>
              </div>
            </div>
          </div>
          <input ref="avatarInputRef" class="avatar-input" type="file" accept="image/*" @change="onAvatarFileChange" />
          <div class="avatar-meta">
            <span v-for="tag in displayTags" :key="tag" class="tag">{{ tag }}</span>
            <span v-if="!displayTags.length" class="tag outline">未设置</span>
          </div>
          <button
            v-if="isLoggedIn"
            class="ghost-btn avatar-btn"
            type="button"
            @click="triggerAvatarPick"
            :disabled="avatarUploading"
          >
            {{ avatarUploading ? "上传中..." : "上传头像" }}
          </button>
          <div class="follow-inline">
            <button class="count-chip" type="button" @click="openList('followers')">
              粉丝 {{ userStats.followers ?? 0 }}
            </button>
            <button class="count-chip" type="button" @click="openList('following')">
              关注 {{ userStats.following ?? 0 }}
            </button>
            <button class="count-chip" type="button" @click="openList('likes')">
              喜欢 {{ userStats.likedSongs ?? 0 }}
            </button>
          </div>
        </div>
        <div class="field-grid">
          <div class="field">
            <label>姓名/用户名</label>
            <template v-if="isEditing">
              <input v-model="form.name" placeholder="请输入用户名" />
            </template>
            <div v-else class="field-value">{{ form.name || "未填写" }}</div>
          </div>
          <div class="field">
            <label>邮箱</label>
            <template v-if="isEditing">
              <input v-model="form.email" type="email" placeholder="请输入邮箱" disabled />
            </template>
            <div v-else class="field-value">{{ form.email || "未填写" }}</div>
          </div>
          <div class="field span-2">
            <label>个人简介</label>
            <template v-if="isEditing">
              <textarea v-model="form.bio" rows="3" placeholder="介绍一下自己"></textarea>
            </template>
            <div v-else class="field-value multiline">
              {{ form.bio || "暂无简介" }}
            </div>
          </div>
          <div class="field span-2">
            <label>标签</label>
            <div class="field-value tag-list">
              <template v-if="displayTags.length">
                <span v-for="tag in displayTags" :key="tag" class="tag outline">{{ tag }}</span>
              </template>
              <span v-else class="muted">未设置标签</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="card stats">
      <div class="card-title">
        <span>个人数据</span>
      </div>
      <div class="stat-grid">
        <div v-for="item in statItems" :key="item.label" class="stat-item">
          <div class="stat-value">{{ item.value }}</div>
          <div class="stat-label">{{ item.label }}</div>
        </div>
      </div>
    </section>

    <section class="card works-card">
      <div class="card-title">
        <span>发布的作品</span>
      </div>
      <div v-if="loadingWorks" class="state">加载中...</div>
      <div v-else-if="publishedWorks.length === 0" class="state">暂无已发布作品</div>
      <div v-else class="published-grid">
        <SongImageCard
          v-for="work in publishedWorks"
          :key="work.id"
          :song="work"
          :cover="work.cover"
          :play-count="work.play_count"
          :liked="isWorkLiked(work)"
          :show-actions="true"
          @play="playWork(work)"
          @like="toggleLike(work)"
          @card-click="goToWorkDetail(work.id)"
          @more="handleWorkMore"
        />
      </div>
    </section>

    <section class="card works-card">
      <div class="card-title">
        <span>喜欢的音乐</span>
      </div>
      <div v-if="loadingLikes" class="state">加载中...</div>
      <div v-else-if="likesError" class="state">{{ likesError }}</div>
      <div v-else-if="likedWorks.length === 0" class="state">暂无喜欢的音乐</div>
      <div v-else class="liked-music-list">
        <div v-for="work in likedWorks" :key="work.id" class="liked-item" @click="goToWorkDetail(work.id)">
          <div class="liked-cover" :style="coverStyle(work)" @click.stop="playLikedWork(work)">
            <div class="play-overlay">
              <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M8 5v14l11-7z"/>
              </svg>
            </div>
          </div>
          <div class="liked-info">
            <div class="liked-title">{{ work.title }}</div>
            <div class="liked-meta">
              <span>点赞 {{ work.like_count ?? 0 }}</span>
              <span class="dot">·</span>
              <span>播放 {{ work.play_count ?? 0 }}</span>
            </div>
          </div>
          <div class="liked-actions">
            <button class="more-btn" title="详情" @click.stop="goToWorkDetail(work.id)">⋯</button>
          </div>
        </div>
      </div>
    </section>

    <p v-if="errorMessage" class="banner error-banner">{{ errorMessage }}</p>
    <p v-if="successMessage" class="banner success-banner">{{ successMessage }}</p>

    <div v-if="listModal.open" class="modal-backdrop" @click.self="closeListModal">
      <div class="modal list-modal">
        <div class="modal-header">
          <h3>{{ listTitle }}</h3>
          <button class="icon-btn" type="button" @click="closeListModal">×</button>
        </div>
        <div class="modal-body">
          <div v-if="listModal.loading" class="state">加载中...</div>
          <div v-else-if="listModal.error" class="state">{{ listModal.error }}</div>
          <template v-else>
            <div v-if="listModal.items.length === 0" class="state">暂无数据</div>
            <div v-else>
              <div v-if="listModal.type === 'likes'" class="modal-list">
                <div v-for="item in listModal.items" :key="item.id" class="list-row">
                  <div class="list-cover" :style="coverStyle(item)"></div>
                  <div class="list-text">
                    <div class="title">{{ item.title }}</div>
                    <div class="meta">点赞 {{ item.like_count ?? 0 }}</div>
                  </div>
                </div>
              </div>
              <div v-else class="modal-list">
                <div v-for="u in listModal.items" :key="u.id" class="list-row user-row" @click="goToUser(u)">
                  <div class="avatar-sm" :style="avatarStyle(u)">
                    <span v-if="!u.avatar_url">{{ (u.username || "").slice(0, 1).toUpperCase() }}</span>
                  </div>
                  <div class="list-text">
                    <div class="title">{{ u.username }}</div>
                    <div class="meta">粉丝 {{ u.followers ?? 0 }}</div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 作品编辑/更换封面模态框 -->
    <div v-if="showWorkModal" class="modal-backdrop" @click.self="closeWorkEditModal">
      <div class="modal">
        <div class="modal-header">
          <h3>编辑作品信息</h3>
          <button class="icon-btn" type="button" @click="closeWorkEditModal">✕</button>
        </div>
        <div class="modal-body">
          <label class="field">
            <span>封面图片</span>
            <div class="file-upload-wrapper">
              <button class="primary-btn small upload-btn" type="button" @click="$el.querySelector('.hidden-work-cover-input').click()">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
                </svg>
                <span>选择文件</span>
              </button>
              <input type="file" class="hidden-work-cover-input" accept="image/*" @change="onWorkCoverChange" style="display: none" />
              <span class="file-name" v-if="workEditForm.cover_url">已上传封面</span>
            </div>
            <div v-if="workEditForm.cover_url" class="cover-preview">
              <img :src="toAbsoluteUrl(workEditForm.cover_url)" alt="封面预览" />
            </div>
          </label>
          <label class="field">
            <span>作品名称</span>
            <input v-model="workEditForm.title" placeholder="请输入作品名称" />
          </label>
          <label class="field">
            <span>描述</span>
            <textarea v-model="workEditForm.description" rows="3" placeholder="作品描述"></textarea>
          </label>
        </div>
        <div class="modal-actions">
          <button class="ghost-btn" type="button" @click="closeWorkEditModal">取消</button>
          <button class="primary-btn" type="button" :disabled="savingWork" @click="submitWorkEdit">
            {{ savingWork ? "保存中..." : "保存修改" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { useUiStore } from "@/stores/ui";
import { fetchWorks, updateWork, uploadWorkCover } from "@/services/workApi";
import { toAbsoluteUrl } from "@/utils/url";
import { usePlayerStore } from "@/stores/player";
import { fetchFollowers, fetchFollowing, fetchLikedWorks, likeWork, unlikeWork } from "@/services/searchApi";
import SongImageCard from "@/views/components/SongImageCard.vue";
import { uploadAvatar } from "@/services/authApi";

const auth = useAuthStore();
const ui = useUiStore();
const player = usePlayerStore();
const router = useRouter();
const isLoggedIn = computed(() => auth.isLoggedIn);

const isEditing = ref(false);
const saving = ref(false);
const errorMessage = ref("");
const successMessage = ref("");
const toastMessage = ref("");
const toastType = ref("success"); // success | error
let toastTimer = null;
const originalSnapshot = ref(null);
const avatarInputRef = ref(null);
const avatarUploading = ref(false);

const form = reactive({
  name: "",
  email: "",
  bio: "",
  tags: []
});

const loadingWorks = ref(false);
const publishedWorks = ref([]);
const likedWorks = ref([]);
const loadingLikes = ref(false);
const likesError = ref("");

// Track liked work ids so the heart icon can reflect likes done in other pages.
// Source of truth: /api/social/likes/works (fetchLikedWorks).
const likedIds = ref(new Set());
watch(
  likedWorks,
  (list) => {
    const ids = Array.isArray(list) ? list.map((w) => w?.id).filter(Boolean) : [];
    likedIds.value = new Set(ids);
  },
  { immediate: true }
);

const likeLoadingId = ref(null);

const ensureLogin = () => {
  if (isLoggedIn.value) return true;
  triggerToast("请先登录后再操作", "error");
  ui.openLoginPanel();
  return false;
};

const isWorkLiked = (work) => {
  const id = work?.id;
  if (!id) return false;
  return likedIds.value.has(id);
};

const toggleLike = async (work) => {
  if (!ensureLogin() || !work?.id) return;
  if (likeLoadingId.value === work.id) return;

  // Backend rule: only public + published works can be liked.
  if ((work.visibility || "").toString() && work.visibility !== "public") {
    triggerToast("作品需设为公开才可点赞", "error");
    return;
  }
  if ((work.status || "").toString() && work.status !== "published") {
    triggerToast("作品需发布后才可点赞", "error");
    return;
  }

  likeLoadingId.value = work.id;
  const wasLiked = isWorkLiked(work);
  try {
    if (wasLiked) {
      await unlikeWork(work.id);
      // optimistic UI
      work.like_count = Math.max((work.like_count || 0) - 1, 0);
      work.liked = false;
      const next = new Set(likedIds.value);
      next.delete(work.id);
      likedIds.value = next;
      triggerToast("已取消点赞", "success");
    } else {
      await likeWork(work.id);
      // optimistic UI
      work.like_count = (work.like_count || 0) + 1;
      work.liked = true;
      likedIds.value = new Set([...likedIds.value, work.id]);
      triggerToast("点赞成功", "success");
    }

    // Best-effort: refresh dependent UI sections (stats + liked list)
    await auth.refreshProfile();
    await loadLikedWorks();
  } catch (err) {
    triggerToast(err?.message || "操作失败", "error");
  } finally {
    likeLoadingId.value = null;
  }
};

const listModal = reactive({
  open: false,
  type: "",
  loading: false,
  items: [],
  error: ""
});
const sampleCovers = [
  "linear-gradient(135deg, #1d2671 0%, #c33764 100%)",
  "linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%)",
  "linear-gradient(135deg, #1a2a6c 0%, #b21f1f 50%, #fdbb2d 100%)"
];

const statusText = computed(() => auth.user?.status || "已激活");
const userStats = computed(() => auth.user?.stats || {});

const totalPublishedPlays = computed(() => {
  // “总播放量”：仅统计已发布作品（status=published）的累计播放次数求和
  // 数据来自 /api/works?status=published 返回的 work.play_count（由 /api/works/{id}/play 累加）
  const list = Array.isArray(publishedWorks.value) ? publishedWorks.value : [];
  return list.reduce((sum, w) => {
    const v = Number(w?.play_count ?? w?.playCount ?? 0) || 0;
    return sum + v;
  }, 0);
});

const statItems = computed(() => {
  const stats = userStats.value;
  return [
    { label: "总生成次数", value: stats.generations ?? 0 },
    { label: "情绪识别次数", value: stats.emotionDetections ?? 0 },
    { label: "总点赞数", value: stats.likesReceived ?? 0 },
    // 需求：个人资料页把“本月播放”改为“总播放量”（仅已发布作品求和）
    { label: "总播放量", value: totalPublishedPlays.value ?? 0 }
  ];
});

const displayTags = computed(() => (Array.isArray(form.tags) ? form.tags : []));

const listTitle = computed(() => {
  if (listModal.type === "followers") return "粉丝列表";
  if (listModal.type === "following") return "关注列表";
  if (listModal.type === "likes") return "喜欢的音乐";
  return "列表";
});

const resetForm = () => {
  form.name = "";
  form.email = "";
  form.bio = "";
  form.tags = [];
};

const currentAvatarUrl = computed(() => toAbsoluteUrl(auth.user?.avatar || ""));
const avatarCircleStyle = computed(() => {
  const url = currentAvatarUrl.value;
  if (!url) return {};
  return {
    backgroundImage: `url(${url})`,
    backgroundSize: "cover",
    backgroundPosition: "center",
    color: "transparent"
  };
});

const triggerAvatarPick = () => {
  if (!isLoggedIn.value) {
    errorMessage.value = "请先登录后再上传头像";
    return;
  }
  if (avatarUploading.value) return;
  avatarInputRef.value?.click?.();
};

const onAvatarFileChange = async e => {
  const file = e?.target?.files?.[0];
  if (!file) return;
  if (!file.type?.startsWith?.("image/")) {
    errorMessage.value = "请上传图片文件";
    e.target.value = "";
    return;
  }

  errorMessage.value = "";
  successMessage.value = "";
  avatarUploading.value = true;
  try {
    const res = await uploadAvatar(file);
    const avatarPath = res?.avatar_path || res?.avatar_url;
    if (!avatarPath) throw new Error("头像上传失败");
    await auth.updateProfileAction({ avatar: avatarPath });
    await auth.refreshProfile();
    successMessage.value = "头像已更新";
  } catch (err) {
    errorMessage.value = err?.message || "头像上传失败";
  } finally {
    avatarUploading.value = false;
    e.target.value = "";
  }
};

const normalizeUsers = users =>
  Array.isArray(users)
    ? users.map(u => ({
        ...u,
        avatar_url: u?.avatar ? toAbsoluteUrl(u.avatar) : "",
        username: u?.username || u?.name || ""
      }))
    : [];

const normalizeWork = (work, index = 0) => {
  if (!work) return null;
  const title = work.title || work.name || `作品 ${index + 1}`;
  const coverUrl = work.cover_url || work.cover || "";
  const audioUrl = work.audio_url || work.url || "";
  return {
    ...work,
    title,
    name: title,
    cover_url: coverUrl,
    cover: coverUrl ? toAbsoluteUrl(coverUrl) : "",
    audio_url: audioUrl,
    url: audioUrl ? toAbsoluteUrl(audioUrl) : "",
    play_count: work.play_count ?? 0,
    liked: work.liked ?? false
  };
};

const playableWorks = computed(() => publishedWorks.value.filter(item => item?.url));
const playableLikedWorks = computed(() => likedWorks.value.filter(item => item?.url));

const fillForm = user => {
  resetForm();
  if (!user) return;
  form.name = user.name || user.nickname || "";
  form.email = user.email || "";
  form.bio = user.bio || "";
  form.tags = Array.isArray(user.tags) ? user.tags : [];
};

watch(
  () => auth.user,
  user => {
    fillForm(user);
    loadPublishedWorks();
    loadLikedWorks();
  },
  { immediate: true }
);

const startEdit = () => {
  errorMessage.value = "";
  successMessage.value = "";
  if (!isLoggedIn.value) {
    errorMessage.value = "请先登录后再编辑资料";
    triggerToast(errorMessage.value, "error");
    return;
  }
  originalSnapshot.value = JSON.parse(JSON.stringify(form));
  isEditing.value = true;
};

const cancelEdit = () => {
  if (!isEditing.value) return;
  errorMessage.value = "";
  successMessage.value = "";
  const snap = originalSnapshot.value;
  if (snap) {
    form.name = snap.name || "";
    form.email = snap.email || "";
    form.bio = snap.bio || "";
    form.tags = Array.isArray(snap.tags) ? snap.tags : [];
  } else {
    fillForm(auth.user);
  }
  isEditing.value = false;
};

const saveProfile = async () => {
  if (!isEditing.value) return;
  if (!isLoggedIn.value) {
    errorMessage.value = "请登录后再保存";
    triggerToast(errorMessage.value, "error");
    return;
  }
  errorMessage.value = "";
  successMessage.value = "";
  saving.value = true;
  try {
    const username = (form.name || "").trim();
    if (!username) {
      errorMessage.value = "用户名不能为空";
      triggerToast(errorMessage.value, "error");
      return;
    }
    if (username.length < 3) {
      errorMessage.value = "用户名：至少 3 位";
      triggerToast(errorMessage.value, "error");
      return;
    }
    if (username.length > 50) {
      errorMessage.value = "用户名：最多 50 位";
      triggerToast(errorMessage.value, "error");
      return;
    }
    const payload = {
      // 后端只支持更新 username / personal_profile / avatar
      username,
      personal_profile: form.bio
    };
    const user = await auth.updateProfileAction(payload);
    fillForm(user);
    successMessage.value = "保存成功";
    triggerToast(successMessage.value, "success");
    isEditing.value = false;
  } catch (err) {
    const msg = err?.message || "保存失败";
    // 明确提示用户名冲突
    if (msg.includes("用户名已存在")) {
      errorMessage.value = "用户名已存在，请更换一个";
    } else {
      errorMessage.value = msg;
    }
    triggerToast(errorMessage.value, "error");
  } finally {
    saving.value = false;
  }
};

const triggerToast = (message, type = "success", durationMs = 2200) => {
  toastMessage.value = message || "";
  toastType.value = type;
  if (toastTimer) clearTimeout(toastTimer);
  if (!toastMessage.value) return;
  toastTimer = setTimeout(() => {
    toastMessage.value = "";
    toastTimer = null;
  }, durationMs);
};

const handleWorkMore = item => {
  // 已发布作品的更多操作：更换封面
  openWorkEditModal(item);
};

const showWorkModal = ref(false);
const modalWorkItem = ref(null);
const workEditForm = reactive({
  title: "",
  description: "",
  visibility: "public",
  cover_url: ""
});
const savingWork = ref(false);

const openWorkEditModal = item => {
  modalWorkItem.value = item;
  workEditForm.title = item.title || "";
  workEditForm.description = item.description || "";
  workEditForm.visibility = item.visibility || "public";
  workEditForm.cover_url = item.cover_url || "";
  showWorkModal.value = true;
};

const closeWorkEditModal = () => {
  showWorkModal.value = false;
  modalWorkItem.value = null;
};

const onWorkCoverChange = async e => {
  const file = e.target.files?.[0];
  if (!file) return;
  try {
    const res = await uploadWorkCover(file);
    workEditForm.cover_url = res?.cover_url || "";
  } catch (err) {
    errorMessage.value = err?.message || "封面上传失败";
  }
};

const submitWorkEdit = async () => {
  if (!modalWorkItem.value) return;
  savingWork.value = true;
  try {
    await updateWork(modalWorkItem.value.id, {
      title: workEditForm.title,
      description: workEditForm.description,
      visibility: workEditForm.visibility,
      cover_url: workEditForm.cover_url || null
    });
    successMessage.value = "作品已更新";
    showWorkModal.value = false;
    await loadPublishedWorks(); // 重新加载以全站同步
  } catch (err) {
    errorMessage.value = err?.message || "保存失败";
  } finally {
    savingWork.value = false;
  }
};

async function loadPublishedWorks() {
  if (!isLoggedIn.value) {
    publishedWorks.value = [];
    return;
  }
  loadingWorks.value = true;
  try {
    const data = await fetchWorks({ status: "published" });
    publishedWorks.value = Array.isArray(data)
      ? data
          .map((item, index) => normalizeWork(item, index))
          .filter(Boolean)
      : [];
  } catch (err) {
    errorMessage.value = err?.message || "加载作品失败";
    publishedWorks.value = [];
  } finally {
    loadingWorks.value = false;
  }
}

async function loadLikedWorks() {
  if (!isLoggedIn.value) {
    likedWorks.value = [];
    return;
  }
  loadingLikes.value = true;
  likesError.value = "";
  try {
    const data = await fetchLikedWorks();
    likedWorks.value = Array.isArray(data)
      ? data.map((item, index) => normalizeWork(item, index)).filter(Boolean)
      : [];
  } catch (err) {
    likesError.value = err?.message || "加载喜欢的音乐失败";
    likedWorks.value = [];
  } finally {
    loadingLikes.value = false;
  }
}

const openList = async type => {
  if (!isLoggedIn.value) {
    errorMessage.value = "请先登录后查看";
    return;
  }
  const myId = auth.user?.id;
  if (!myId) {
    errorMessage.value = "用户信息未就绪，请刷新页面或重新登录后再试";
    return;
  }
  listModal.type = type;
  listModal.open = true;
  listModal.loading = true;
  listModal.error = "";
  try {
    if (type === "followers") {
      listModal.items = normalizeUsers(await fetchFollowers(myId));
    } else if (type === "following") {
      listModal.items = normalizeUsers(await fetchFollowing(myId));
    } else if (type === "likes") {
      listModal.items = await fetchLikedWorks();
    } else {
      listModal.items = [];
    }
  } catch (err) {
    listModal.error = err?.message || "加载失败";
    listModal.items = [];
  } finally {
    listModal.loading = false;
  }
};

const closeListModal = () => {
  listModal.open = false;
};

const playWork = work => {
  playFromList(work, playableWorks.value);
};

const playLikedWork = work => {
  playFromList(work, playableLikedWorks.value);
};

const goToWorkDetail = id => {
  router.push({ name: "songDetail", params: { id } });
};

const playFromList = (work, list) => {
  if (!work) return;
  // 清理上一次的提示，避免成功播放后仍然显示旧错误
  errorMessage.value = "";
  const index = Array.isArray(list) ? list.findIndex(item => item.id === work.id) : -1;
  if (index === -1) {
    // 找不到音频时不弹出全局错误 banner（体验不好），仅静默返回
    return;
  }
  player.setPlaylist(list, index);
  player.playTrack(index);
};

const coverStyle = work => {
  const url = work.cover || (work.cover_url ? toAbsoluteUrl(work.cover_url) : "");
  const bg = url ? `url(${url})` : sampleCovers[work.id % sampleCovers.length];
  return {
    backgroundImage: `linear-gradient(180deg, rgba(0,0,0,0.05) 0%, rgba(0,0,0,0.55) 100%), ${bg}`,
    backgroundSize: "cover",
    backgroundPosition: "center",
    backgroundColor: "#0f172a"
  };
};

const avatarStyle = user => {
  const url = user?.avatar_url;
  if (url) {
    return {
      backgroundImage: `url(${url})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
      color: "transparent"
    };
  }
  return {};
};

const goToUser = user => {
  if (!user?.id) return;
  closeListModal();
  router.push({ name: "userPublic", params: { id: user.id } });
};

onMounted(async () => {
  try {
    player.initAudio();
    await auth.refreshProfile();
    fillForm(auth.user);
    await loadPublishedWorks();
    await loadLikedWorks();
  } catch (err) {
    errorMessage.value = err?.message || "获取资料失败";
  }
});
</script>

<style scoped>
/* 模态框样式增强 */
.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field span {
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  font-weight: 600;
}

.field input,
.field textarea {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 10px 12px;
  color: #fff;
  outline: none;
  transition: border-color 0.2s;
}

.field input:focus,
.field textarea:focus {
  border-color: #3b82f6;
}

.cover-preview {
  width: 160px;
  height: 160px;
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.1);
  margin-top: 4px;
}

.cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.modal-actions {
  padding: 16px 20px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: grid;
  place-items: center;
  z-index: 3000;
}

.modal {
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  width: 420px;
  max-width: 90vw;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.modal-header {
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.profile-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(23, 37, 84, 0.4), rgba(8, 20, 46, 0.8));
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.eyebrow {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.55);
  margin-bottom: 4px;
}

h1 {
  font-size: 20px;
  margin: 0;
}

.muted {
  margin-top: 6px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.ghost-btn,
.primary-btn {
  height: 38px;
  padding: 0 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.ghost-btn {
  border: 1px solid rgba(148, 163, 184, 0.45);
  background: rgba(255, 255, 255, 0.04);
  color: #e5e7eb;
}

.ghost-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(148, 163, 184, 0.6);
}

.primary-btn {
  background: #3b82f6;
  color: #fff;
  border: none;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.primary-btn:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
}

.ghost-btn:disabled,
.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.primary-btn.small {
  height: 32px;
  padding: 0 12px;
  border-radius: 8px;
  font-size: 13px;
}

.upload-btn {
  background: #3b82f6;
}

.card {
  padding: 18px 20px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 16px 50px rgba(15, 23, 42, 0.7);
}

.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  font-weight: 600;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(34, 197, 94, 0.12);
  color: #a7f3d0;
  border-radius: 999px;
  border: 1px solid rgba(34, 197, 94, 0.25);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.dot.online {
  background: #22c55e;
  box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.14);
}

.base-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.base-grid {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 18px;
}

.avatar-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.avatar-circle {
  width: 96px;
  height: 96px;
  border-radius: 999px;
  background: linear-gradient(135deg, #4f46e5, #f97316);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  font-weight: 700;
  position: relative;
  overflow: hidden;
  transition: transform 0.16s ease-out, box-shadow 0.16s ease-out, border-color 0.16s ease-out;
}

.avatar-circle.editable {
  cursor: pointer;
}

.avatar-circle.editable:hover {
  transform: scale(1.02);
  box-shadow: 0 22px 55px rgba(0, 0, 0, 0.45);
  border-color: rgba(59, 130, 246, 0.55);
}

.avatar-hover {
  position: absolute;
  inset: 0;
  background: rgba(2, 6, 23, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.16s ease-out;
  color: rgba(255, 255, 255, 0.92);
  font-size: 12px;
  letter-spacing: 0.02em;
}

.avatar-circle.editable:hover .avatar-hover {
  opacity: 1;
}

.avatar-hover-inner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.25);
  backdrop-filter: blur(6px);
}

.avatar-hover-icon {
  font-size: 13px;
  opacity: 0.9;
}

.avatar-input {
  display: none;
}

.avatar-btn {
  width: fit-content;
  margin-top: 2px;
  height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
}

.avatar-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.follow-inline {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.count-chip {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 10px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.04);
  color: #e5e7eb;
  cursor: pointer;
  text-align: center;
}

.tag {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  font-size: 12px;
  color: #e5e7eb;
}

.tag.outline {
  background: rgba(59, 130, 246, 0.14);
  color: #bfdbfe;
  border: 1px solid rgba(59, 130, 246, 0.4);
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
}

.field-value {
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.field-value.multiline {
  min-height: 68px;
  line-height: 1.5;
}

.field input,
.field textarea,
.mini-input input,
.field select {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.04);
  color: #e5e7eb;
  outline: none;
}

.field textarea {
  resize: vertical;
}

.mini-input {
  width: 100%;
}

.span-2 {
  grid-column: span 2;
}

.tag-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.stats .stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.stat-item {
  padding: 14px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 6px;
}

.stat-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
}

.works-card .state {
  padding: 12px;
  color: rgba(255, 255, 255, 0.75);
}

.state {
  padding: 12px;
  color: rgba(255, 255, 255, 0.78);
}

.published-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
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

.banner {
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
}

.error-banner {
  background: rgba(248, 113, 113, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.4);
  color: #fecdd3;
}

.success-banner {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.35);
  color: #bbf7d0;
}

.toast {
  position: fixed;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 16px;
  border-radius: 12px;
  font-weight: 700;
  z-index: 10000;
  animation: toast-in 0.18s ease;
  letter-spacing: 0.02em;
  border: 1px solid transparent;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.35);
}

.toast-success {
  color: #071c12;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.96), rgba(52, 211, 153, 0.96));
  border-color: rgba(74, 222, 128, 0.4);
}

.toast-error {
  color: #fff;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.95), rgba(248, 113, 113, 0.9));
  border-color: rgba(248, 113, 113, 0.35);
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

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: grid;
  place-items: center;
  z-index: 2000;
}

.list-modal {
  width: 420px;
  max-width: 90vw;
  background: #0f1c32;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  box-shadow: 0 16px 60px rgba(0, 0, 0, 0.45);
  /* 固定弹窗整体大小（随 viewport 自适应上限），避免随着列表项数量无限变高 */
  max-height: 75vh;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.icon-btn {
  border: none;
  background: transparent;
  color: #e5e7eb;
  cursor: pointer;
  font-size: 18px;
}

/* 仅约束“粉丝/关注/喜欢”列表弹窗：其它弹窗（如作品编辑）不受影响 */
.list-modal .modal-body {
  padding: 14px 16px;
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.modal-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.list-row {
  display: grid;
  grid-template-columns: 60px 1fr;
  gap: 10px;
  padding: 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.avatar-sm {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: grid;
  place-items: center;
  color: #fff;
  font-weight: 700;
}

.list-cover {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  background-size: cover;
  background-position: center;
}

.list-text .title {
  font-weight: 700;
}

.list-text .meta {
  color: rgba(229, 231, 235, 0.75);
  font-size: 12px;
}

@media (max-width: 900px) {
  .base-grid {
    grid-template-columns: 1fr;
  }

  .field-grid {
    grid-template-columns: 1fr;
  }

  .span-2 {
    grid-column: span 1;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .liked-music-list {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1200px) {
  .published-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .published-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .published-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
