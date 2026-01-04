<template>
  <div class="works-page">
    <h2 class="page-title">我的作品</h2>

    <section class="list-card">
      <div v-if="loading" class="state">加载中...</div>
      <div v-else-if="!auth.isLoggedIn" class="state">请先进行注册/登录</div>
      <div v-else-if="displayWorks.length === 0" class="state">暂无作品</div>
      <div v-else class="work-list">
        <WorkItem
          v-for="item in displayWorks"
          :key="item.id"
          :item="item"
          @delete="handleDelete"
          @play="handlePlay"
          @publish="openPublishModal"
          @edit="openEditModal"
          @download="handleDownload"
        />
      </div>
    </section>

    <div v-if="showModal" class="modal-backdrop" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ modalTitle }}</h3>
          <button class="icon-btn" type="button" @click="closeModal">✕</button>
        </div>
        <div class="modal-body">
          <label class="field">
            <span>作品名称</span>
            <input v-model="form.title" placeholder="请输入作品名称" />
          </label>
          <template v-if="showPublishFields">
            <label class="field">
              <span>描述</span>
              <textarea v-model="form.description" rows="3" placeholder="创作初衷、情绪等"></textarea>
            </label>
            <label class="field">
              <span>可见性</span>
              <select v-model="form.visibility">
                <option value="public">公开</option>
                <option value="unlisted">不公开链接</option>
                <option value="private">仅自己</option>
              </select>
            </label>
            <label class="field">
              <span>封面图片</span>
              <input type="file" accept="image/*" @change="onCoverChange" />
              <div v-if="previewUrl" class="cover-preview">
                <img :src="previewUrl" alt="封面预览" />
              </div>
            </label>
          </template>
          <p v-if="error" class="error">{{ error }}</p>
        </div>
        <div class="modal-actions">
          <button class="ghost-btn" type="button" @click="closeModal">取消</button>
          <button class="primary-btn" type="button" :disabled="saving" @click="submitPublish">
            {{ actionLabel }}
          </button>
        </div>
      </div>
    </div>

    <!-- Toast 提示 -->
    <div v-if="toastMessage" :class="['toast', `toast-${toastType}`]">
      {{ toastMessage }}
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import WorkItem from "@/components/WorkItem.vue";
import { useWorksStore } from "@/stores/works";
import { usePlayerStore } from "@/stores/player";
import { useAuthStore } from "@/stores/auth";
import { uploadWorkCover } from "@/services/workApi";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

const worksStore = useWorksStore();
const playerStore = usePlayerStore();
const auth = useAuthStore();
const { list: works, loading } = storeToRefs(worksStore);

const displayWorks = computed(() => works.value || []);

// 避免切换账号/退出登录后短暂闪现上一用户的作品列表
worksStore.syncScope();

onMounted(() => {
  worksStore.loadWorks();
});

watch(
  () => auth.user?.id,
  () => {
    // 切换账号：立即清空旧数据并重新加载
    worksStore.syncScope();
    worksStore.loadWorks();
    closeModal();
  }
);

watch(
  () => auth.isLoggedIn,
  loggedIn => {
    if (!loggedIn) {
      worksStore.syncScope();
      closeModal();
    }
  }
);

const handleDelete = async item => {
  if (!confirm(`确定要删除作品「${item.title || item.name || "未命名"}」吗？此操作不可恢复。`)) {
    return;
  }
  
  try {
    await worksStore.removeWork(item.id);
    showToast("删除成功");
  } catch (err) {
    showToast(err?.message || "删除失败", "error");
  }
};

const handleDownload = async item => {
  if (!item.audio_url && !item.url) {
    showToast("音频文件不存在", "error");
    return;
  }
  
  try {
    const audioUrl = item.audio_url || item.url;
    const fullUrl = toAbsoluteUrl(audioUrl);
    
    // 获取文件名
    const fileName = `${item.title || item.name || "music"}.${getFileExtension(audioUrl)}`;
    
    // 创建临时链接并触发下载
    const link = document.createElement("a");
    link.href = fullUrl;
    link.download = fileName;
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast("下载已开始");
  } catch (err) {
    console.error("Download error:", err);
    showToast("下载失败", "error");
  }
};

const getFileExtension = url => {
  if (!url) return "wav";
  const match = url.match(/\.([a-zA-Z0-9]+)(\?|$)/);
  return match ? match[1] : "wav";
};

const showToast = (message, type = "success") => {
  toastMessage.value = message;
  toastType.value = type;
  setTimeout(() => {
    toastMessage.value = "";
  }, 3000);
};

const handlePlay = item => {
  const index = displayWorks.value.findIndex(w => w.id === item.id);
  if (index !== -1) {
    playerStore.setPlaylist(displayWorks.value, index);
    playerStore.playTrack(index);
  }
};

const showModal = ref(false);
const saving = ref(false);
const error = ref("");
const currentId = ref(null);
const modalMode = ref("publish"); // publish | rename
const form = reactive({
  title: "",
  description: "",
  visibility: "public",
  cover_url: ""
});

// Toast 提示
const toastMessage = ref("");
const toastType = ref("success"); // success | error

const toAbsoluteUrl = url => {
  if (!url) return "";
  if (url.startsWith("http") || url.startsWith("blob:") || url.startsWith("data:")) return url;
  const base = API_BASE_URL || window.location.origin;
  return url.startsWith("/") ? `${base}${url}` : `${base}/${url}`;
};

const previewUrl = computed(() => toAbsoluteUrl(form.cover_url));

const modalTitle = computed(() => {
  if (modalMode.value === "rename") return "修改名称";
  return currentId.value ? "发布/编辑作品" : "发布作品";
});

const actionLabel = computed(() => (modalMode.value === "rename" ? "保存" : saving.value ? "保存中..." : "发布"));
const showPublishFields = computed(() => modalMode.value === "publish");

const openPublishModal = item => {
  modalMode.value = "publish";
  currentId.value = item.id;
  form.title = item.title || item.name || "";
  form.description = item.description || "";
  form.visibility = item.visibility || "public";
  form.cover_url = item.cover_url || "";
  error.value = "";
  showModal.value = true;
};

const openEditModal = item => {
  modalMode.value = "rename";
  currentId.value = item.id;
  form.title = item.title || item.name || "";
  form.description = item.description || "";
  form.visibility = item.visibility || "public";
  form.cover_url = item.cover_url || "";
  error.value = "";
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
  saving.value = false;
  error.value = "";
};

const onCoverChange = async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const res = await uploadWorkCover(file);
    form.cover_url = res?.cover_url || "";
  } catch (err) {
    error.value = err?.message || "封面上传失败";
  }
};

const submitPublish = async () => {
  if (!currentId.value) return;
  if (!form.title?.trim()) {
    error.value = "作品名称不能为空";
    return;
  }
  saving.value = true;
  error.value = "";
  try {
    if (modalMode.value === "rename") {
      await worksStore.editWork(currentId.value, { title: form.title });
    } else {
      await worksStore.editWork(currentId.value, {
        title: form.title,
        description: form.description,
        visibility: form.visibility,
        cover_url: form.cover_url || null, // 明确传递 cover_url
        status: "published"
      });
    }
    closeModal();
    showToast(modalMode.value === "rename" ? "修改成功" : "发布成功");
  } catch (err) {
    error.value = err?.message || "保存失败";
  } finally {
    saving.value = false;
  }
};
</script>

<style scoped>
.works-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  color: #e5e7eb;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #e6ebf5;
}

.list-card {
  padding: 6px 6px 12px;
  border-radius: 12px;
  background: #0b1627;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.work-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.state {
  padding: 16px;
  text-align: center;
  color: rgba(255, 255, 255, 0.78);
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: grid;
  place-items: center;
  z-index: 2000;
}

.modal {
  width: 60vw;
  max-width: 840px;
  min-width: 320px;
  background: #0f1c32;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  box-shadow: 0 16px 60px rgba(0, 0, 0, 0.45);
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

.modal-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
}

.field input,
.field textarea,
.field select {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(255, 255, 255, 0.04);
  color: #e5e7eb;
}

.cover-preview {
  margin-top: 8px;
  width: 220px;
  max-width: 100%;
  height: 140px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.icon-btn {
  border: none;
  background: transparent;
  color: #e5e7eb;
  cursor: pointer;
  font-size: 16px;
}

.ghost-btn,
.primary-btn {
  height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.04);
  color: #e5e7eb;
  cursor: pointer;
}

.primary-btn {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  border: none;
}

.error {
  color: #fca5a5;
  font-size: 13px;
}

.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  z-index: 3000;
  animation: toastSlideIn 0.3s ease;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(12px);
}

.toast-success {
  background: rgba(34, 197, 94, 0.9);
  color: #fff;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.toast-error {
  background: rgba(239, 68, 68, 0.9);
  color: #fff;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

@keyframes toastSlideIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@media (max-width: 900px) {
  .modal {
    width: 90vw;
  }
}
</style>
