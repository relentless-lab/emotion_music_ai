<template>
  <div class="page">
    <!-- 左侧：音乐生成聊天面板 -->
    <div class="chat-container">
      <section class="panel chat-panel">
        <header class="panel-header">
          <div>
            <p class="eyebrow">音乐生成</p>
            <h2>{{ displayTitle ? `「${displayTitle}」` : "音乐创作对话" }}</h2>
          </div>
          <div class="dialogue-meta">
            <button class="ghost-btn small" type="button" @click="resetDialogue" :disabled="sending">
              新建对话
            </button>
          </div>
        </header>

        <div class="chat-scroll custom-scrollbar" id="chatScroll">
          <div v-if="messages.length === 0 && !messageInput.trim()" class="empty-state">
            <p class="hero-hint">👉 「请开启您的音乐生成之旅」</p>
          </div>

          <div v-else class="chat-flow">
            <div
              v-for="msg in messages"
              :key="msg.localId"
              class="chat-step"
              :class="msg.role"
            >
              <!-- 文本气泡 -->
              <div class="bubble">
                <div class="message-text">{{ msg.text }}</div>
              </div>
            </div>

            <div v-if="sending" class="status">
              <span class="pulse-dot"></span>
              等待系统回复...
            </div>
            <div v-if="error" class="error-line">{{ error }}</div>
          </div>
        </div>

        <div class="controls-area">
          <div class="input-wrapper">
            <div class="textarea-container">
              <textarea
                v-model="messageInput"
                :disabled="sending"
                @keydown.enter.exact.prevent="sendMessage"
                @keydown.shift.enter.exact.prevent="messageInput += '\n'"
              placeholder="例如：在雨夜街头的慢板爵士，带点复古氛围和萨克斯..."
                class="chat-input"
              ></textarea>

            <!-- 生成模式与操作：纯音乐 / 有人声 / 仿写 -->
            <div class="mode-row">
              <button
                class="mode-chip"
                type="button"
                :class="{ active: isInstrumental }"
                :disabled="sending"
                @click="isInstrumental = true"
              >
                纯音乐
              </button>
              <button
                class="mode-chip"
                type="button"
                :class="{ active: !isInstrumental }"
                :disabled="sending"
                @click="isInstrumental = false"
              >
                有人声 / 歌曲
              </button>

              <button
                class="mode-chip imitate-chip"
                type="button"
                :disabled="sending"
                @click="triggerImitatePick"
                title="请点击上传参考音频"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                  <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
                </svg>
                <span>音乐仿写</span>
              </button>
            </div>

            <div v-if="!isInstrumental" class="lyrics-section">
              <div class="section-label">歌词设置</div>
              <textarea
                v-model="lyricsInput"
                :disabled="sending"
                placeholder="输入你想要的歌词（支持 [verse]/[chorus] 结构），不填则自动生成"
                class="lyrics-input"
              ></textarea>
            </div>

            <div class="input-actions">
              <input
                ref="imitateFileInputRef"
                type="file"
                accept="audio/*"
                style="display:none"
                @change="onImitateFileChange"
              />
              <button
                class="send-btn"
                type="button"
                :disabled="sending || !messageInput.trim()"
                @click="sendMessage"
                :class="{ loading: sending }"
              >
                <svg v-if="!sending" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
                <span v-else class="loading-spinner"></span>
              </button>
            </div>
            </div>
          </div>

          <!-- 灵感来源区域 (Inspiration Chips) -->
          <div class="inspiration-container">
            <div class="inspiration-group">
              <span class="group-label">情绪：</span>
              <div class="chips-row">
                <button
                  v-for="preset in presets"
                  :key="preset.label"
                  class="insp-chip"
                  type="button"
                  @click="appendPreset(preset.text)"
                >
                  {{ preset.label }}
                </button>
              </div>
            </div>
            
            <div class="inspiration-group">
              <span class="group-label">乐器：</span>
              <div class="chips-row">
                <button v-for="inst in instruments" :key="inst" class="insp-chip" @click="appendPreset(inst)">{{ inst }}</button>
              </div>
            </div>

            <div class="inspiration-group">
              <span class="group-label">风格：</span>
              <div class="chips-row">
                <button v-for="style in styles" :key="style" class="insp-chip" @click="appendPreset(style)">{{ style }}</button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- 右侧：生成列表边栏 -->
    <GenerateMusicSidebar
      :tracks="generatedTracks"
      :current-playing-id="player.currentTrack?.id"
      :added-work-ids="addedWorkIds"
      :adding-work-id="addingWorkId"
      @play="playMusicFromSidebar"
      @add-to-works="addToWorks"
    />

    <!-- Toast 提示 -->
    <div v-if="toastMessage" :class="['toast', `toast-${toastType}`]">
      {{ toastMessage }}
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { 
  chatWithDialogue, 
  getDialogueDetail, 
  generateCoverOnly,
  chatWithDialogueAsync,
  getMusicTaskStatus,
  imitateMusicAsync
} from "@/services/dialogueApi";
import { createWork } from "@/services/workApi";
import { usePlayerStore } from "@/stores/player";
import GenerateMusicSidebar from "./components/GenerateMusicSidebar.vue";

const route = useRoute();
const auth = useAuthStore();
const messageInput = ref("");
const dialogueId = ref(null);
const messages = ref([]);
const generatedTracks = ref([]);
const lastResponse = ref(null);
const sending = ref(false);
const error = ref("");
const modelIndex = ref(0);
// 默认生成时长：前端不再提供时长选择，避免“像被截断”的主观体验
const DEFAULT_DURATION_SECONDS = 120;
const isInstrumental = ref(true);
const lyricsInput = ref("");
const addingWorkId = ref(null);
const addedWorkIds = ref(new Set()); // 跟踪已保存的作品ID
const toastMessage = ref("");
const toastType = ref("success");
let toastTimer = null;
const imitateFileInputRef = ref(null);

// Prevent race conditions when users start a new conversation while an async generation request is in-flight.
// Late responses from previous conversations must not overwrite the current dialogueId/UI.
const sessionNonce = ref(0);
const bumpSessionNonce = () => {
  sessionNonce.value += 1;
};

// --- Pending generation tasks cache (per dialogue) ---
// Goal: if a generation is still in progress and the user creates a new dialogue,
// opening the previous dialogue from History should still show the pending card (cover/prompt/status).
const PENDING_TASKS_KEY = "pending_music_generation_tasks_v1";
const getPendingTasksStorageKey = () => {
  const uid = auth?.user?.id;
  if (!auth?.isLoggedIn || !uid) return null;
  return `${PENDING_TASKS_KEY}:user:${uid}`;
};

const loadPendingTasks = () => {
  const key = getPendingTasksStorageKey();
  if (!key) return [];
  try {
    const raw = localStorage.getItem(key);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
};

const savePendingTasks = (tasks) => {
  const key = getPendingTasksStorageKey();
  if (!key) return;
  try {
    localStorage.setItem(key, JSON.stringify(Array.isArray(tasks) ? tasks : []));
  } catch {
    // ignore
  }
};

const upsertPendingTask = (patch) => {
  if (!auth?.isLoggedIn) return;
  const tasks = loadPendingTasks();
  const taskKey = patch?.taskId ? `task:${patch.taskId}` : null;
  const tempKey = patch?.tempId ? `temp:${patch.tempId}` : null;
  const draftKey = patch?.draftNonce !== undefined && patch?.draftNonce !== null ? `draft:${patch.draftNonce}` : null;

  const idx = tasks.findIndex(t => {
    if (taskKey && t?.taskId && `task:${t.taskId}` === taskKey) return true;
    if (tempKey && t?.tempId && `temp:${t.tempId}` === tempKey && (draftKey ? t?.draftNonce === patch.draftNonce : true)) return true;
    return false;
  });

  const next = {
    ...(idx >= 0 ? tasks[idx] : {}),
    ...patch,
    updatedAt: Date.now()
  };

  if (idx >= 0) tasks[idx] = next;
  else tasks.unshift(next);

  // Keep the cache small
  const trimmed = tasks.slice(0, 80);
  savePendingTasks(trimmed);
};

const prunePendingTasksForDialogue = (dialogueIdToPrune, completedPrompts = []) => {
  if (!auth?.isLoggedIn) return;
  const tasks = loadPendingTasks();
  const completed = new Set((completedPrompts || []).map(s => (s || "").trim()).filter(Boolean));
  const next = tasks.filter(t => {
    if (!t) return false;
    if (t.dialogueId !== dialogueIdToPrune) return true;
    const p = (t.prompt || "").trim();
    // If server already has a completed message for this prompt, drop the pending entry to avoid duplicates.
    if (p && completed.has(p)) return false;
    return true;
  });
  if (next.length !== tasks.length) savePendingTasks(next);
};

const showToast = (message, type = "success", durationMs = 2200) => {
  toastMessage.value = message || "";
  toastType.value = type;
  if (toastTimer) {
    clearTimeout(toastTimer);
    toastTimer = null;
  }
  if (!toastMessage.value) return;
  toastTimer = setTimeout(() => {
    toastMessage.value = "";
    toastTimer = null;
  }, durationMs);
};

// 灵感标签配置
const instruments = ["钢琴", "吉他", "萨克斯", "小提琴", "架子鼓", "合成器"];
const styles = ["爵士", "流行", "古典", "电子", "摇滚", "低保真(Lo-fi)", "电影感"];
const seasons = ["春季", "夏季", "秋季", "冬季"];

const presets = [
  { label: "高兴", tone: "warm", text: "高兴" },
  { label: "伤心", tone: "calm", text: "伤心" },
  { label: "兴奋", tone: "vivid", text: "兴奋" },
  { label: "平静", tone: "calm", text: "平静" }
];

const player = usePlayerStore();

// --- 状态持久化逻辑 ---
// 注意：必须按用户隔离，避免“游客/其他账号”看到上一位用户的会话
const BASE_STORAGE_KEY = "latest_music_generation_session_v2";

const getStorageKey = () => {
  const uid = auth?.user?.id;
  if (!auth?.isLoggedIn || !uid) return `${BASE_STORAGE_KEY}:guest`;
  return `${BASE_STORAGE_KEY}:user:${uid}`;
};

const saveSessionToStorage = () => {
  // 游客不做持久化：每次进入都应该是新的界面
  if (!auth?.isLoggedIn) {
    try {
      localStorage.removeItem(`${BASE_STORAGE_KEY}:guest`);
    } catch {
      // ignore
    }
    return;
  }
  try {
    // Avoid localStorage quota issues by limiting payload size.
    const safeMessages = Array.isArray(messages.value) ? messages.value.slice(-80) : [];
    const safeTracks = Array.isArray(generatedTracks.value)
      ? generatedTracks.value.slice(0, 80).map(t => {
          // strip runtime-only fields
          const { _polling, ...rest } = (t || {});
          return rest;
        })
      : [];

    const sessionData = {
      owner_user_id: auth?.user?.id ?? null,
      dialogueId: dialogueId.value,
      messages: safeMessages,
      generatedTracks: safeTracks,
      lastResponse: lastResponse.value,
      timestamp: Date.now()
    };
    localStorage.setItem(getStorageKey(), JSON.stringify(sessionData));
  } catch (e) {
    // Best-effort persistence; should not break core generation flow.
    console.warn("保存会话到本地失败:", e);
  }
};

// 监听关键数据变化，自动保存到 localStorage
watch([messages, generatedTracks, dialogueId, lastResponse], () => {
  saveSessionToStorage();
}, { deep: true });

const restoreSessionFromStorage = () => {
  // 游客不恢复：每次进入都是新的界面
  if (!auth?.isLoggedIn) return false;

  // 清理旧版本全局 key，避免串号（v1 没有用户隔离）
  try {
    localStorage.removeItem("latest_music_generation_session");
  } catch {
    // ignore
  }

  const saved = localStorage.getItem(getStorageKey());
  if (!saved) return false;

  try {
    const data = JSON.parse(saved);
    // 安全校验：必须是当前用户自己的会话
    if ((data?.owner_user_id ?? null) !== (auth?.user?.id ?? null)) {
      try {
        localStorage.removeItem(getStorageKey());
      } catch {
        // ignore
      }
      return false;
    }
    // 只恢复 24 小时内的会话，防止数据过旧
    if (Date.now() - data.timestamp > 86400000) {
      localStorage.removeItem(getStorageKey());
      return false;
    }

    dialogueId.value = data.dialogueId;
    messages.value = data.messages || [];
    generatedTracks.value = data.generatedTracks || [];
    lastResponse.value = data.lastResponse;

    // If there are pending tracks without cover (e.g., user navigated away before cover call finished),
    // try to regenerate cover on restore so cards can show real cover ASAP.
    generatedTracks.value.forEach(track => {
      if (track?.status === "generating" && !track.cover && (track.prompt || track.mood)) {
        const prompt = track.prompt || track.mood;
        generateCoverOnly({ prompt })
          .then(res => res?.cover_url)
          .then(coverUrl => {
            if (!coverUrl) return;
            const t = generatedTracks.value.find(x => x.id === track.id);
            if (t && !t.cover) {
              t.cover = toAbsoluteUrl(coverUrl);
            }
          })
          .catch(() => {});
      }
    });

    // 自动重启正在生成中任务的轮询
    generatedTracks.value.forEach(track => {
      if (track.status === 'generating' && track.taskId) {
        pollTaskStatus(track.taskId, track.id);
      }
    });

    return true;
  } catch (e) {
    console.error("恢复会话失败:", e);
    return false;
  }
};

const resetSessionState = () => {
  bumpSessionNonce();
  // 清理生成中的轮询（避免账号切换后继续轮询旧任务）
  try {
    generatedTracks.value.forEach(t => {
      if (t && t._pollingTimer) clearInterval(t._pollingTimer);
    });
  } catch {
    // ignore
  }
  dialogueId.value = null;
  messages.value = [];
  generatedTracks.value = [];
  lastResponse.value = null;
  error.value = "";
};

// 账号切换时：不允许串号，直接重置并恢复当前用户自己的会话
watch(
  () => (auth?.isLoggedIn ? auth?.user?.id : null),
  () => {
    resetSessionState();
    // 若有 query.dialogueId，则优先加载历史（保持原逻辑）
    if (route.query.dialogueId) return;
    const restored = restoreSessionFromStorage();
    if (restored) scrollToBottom();
  }
);

const pollTaskStatus = async (taskId, tempId) => {
  // 防止重复轮询同一个 taskId
  const track = generatedTracks.value.find(t => t.id === tempId);
  if (!track || track._polling) return;
  track._polling = true;

  const timer = setInterval(async () => {
    try {
      const res = await getMusicTaskStatus(taskId);
      
      const currentTrackIndex = generatedTracks.value.findIndex(t => t.id === tempId);
      if (currentTrackIndex === -1) {
        clearInterval(timer);
        return;
      }

      if (res.status === 'completed' && res.result) {
        clearInterval(timer);
        const result = res.result;

        const existingTrack = generatedTracks.value[currentTrackIndex] || {};
        
        // 更新卡片状态为 ready
        generatedTracks.value[currentTrackIndex] = {
          ...existingTrack,
          ...result,
          status: 'ready',
          taskId: taskId,
          // Prefer backend-generated title; fallback to existing pending title.
          title: result.title || existingTrack.title || "AI 生成作品",
          // Prefer pre-generated cover (Suno cover-first). Only fallback to backend cover if we never got one.
          cover: existingTrack.cover || toAbsoluteUrl(result.cover) || "",
          // Ensure url becomes absolute.
          url: toAbsoluteUrl(result.url) || existingTrack.url || "",
          createdAt: result.created_at || existingTrack.createdAt || new Date().toISOString()
        };
        // Once completed, drop the pending cache entry to avoid "generating" cards lingering in History.
        try {
          prunePendingTasksForDialogue(result.dialogue_id || dialogueId.value, [existingTrack.prompt || existingTrack.mood || ""]);
        } catch {
          // ignore
        }

        // 同时更新聊天区域中的 AI 回复：用 pendingTrackId 精准定位这次生成的占位消息
        const msgIdx = messages.value.findIndex(
          m => m.role === "assistant" && m.pendingTrackId === tempId
        );
        if (msgIdx !== -1) {
          messages.value[msgIdx].text = result.reply || "音乐已生成完毕，请试听。";
          messages.value[msgIdx].messageId = result.message_id || messages.value[msgIdx].messageId;
          messages.value[msgIdx].music = {
            ...result,
            title: result.title || generatedTracks.value[currentTrackIndex]?.title || "AI 生成作品",
            url: toAbsoluteUrl(result.url),
            cover: toAbsoluteUrl(result.cover) || generatedTracks.value[currentTrackIndex]?.cover || ""
          };
          messages.value[msgIdx].pendingTrackId = null;
        }
        
        showToast("音乐生成完毕！");
        scrollToBottom();
      } else if (res.status === 'failed') {
        clearInterval(timer);
        generatedTracks.value.splice(currentTrackIndex, 1);
        error.value = "音乐生成失败: " + (res.message || "未知错误");
        showToast("音乐生成失败", "error");
      }
      // 正在 processing 则继续轮询
    } catch (e) {
      console.error("轮询任务失败:", e);
      // 如果报错太多次可以考虑停止，这里先简单继续
    }
  }, 3000);
};

onMounted(async () => {
  player.initAudio();
  
  // 1. 优先尝试从 URL query 恢复（指定对话历史）
  if (route.query.dialogueId) {
    await loadDialogue(route.query.dialogueId);
  } else {
    // 2. 否则尝试从 localStorage 恢复最近一次活跃会话
    const restored = restoreSessionFromStorage();
    if (restored) {
      scrollToBottom();
    }
  }
  
});

onUnmounted(() => {
});

const loadDialogue = async id => {
  bumpSessionNonce();
  const loadNonce = sessionNonce.value;
  try {
    const data = await getDialogueDetail(id);
    // If user switched conversations while this request was in-flight, ignore the stale response.
    if (loadNonce !== sessionNonce.value) return;
    dialogueId.value = id;
    const dialogueTitle = data?.dialogue_title || data?.dialogueTitle || "";

    const restoredMessages = [];
    const tracks = [];
    const completedPrompts = [];
    if (Array.isArray(data?.messages)) {
      data.messages.forEach(msg => {
        const created = msg.created_at || new Date().toISOString();
        const order = msg.message_order || null;
        if (msg.user_input) {
          restoredMessages.push({
            localId: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
            role: "user",
            text: msg.user_input,
            createdAt: created,
            order
          });
        }
        if (msg.reply) {
          // 检查是否有对应的音乐
          const musicData = msg.music_url
            ? {
                id: msg.music_file_id || msg.id,
                music_file_id: msg.music_file_id || msg.id,
                // 优先使用对话标题（后端可能已生成/保存 AI 歌名），兜底到用户输入
                title: dialogueTitle || msg.user_input || msg.reply || "AI 生成作品",
                artist: "AI Composer",
                url: toAbsoluteUrl(msg.music_url),
                duration: msg.duration_seconds ?? 0,
                format: "wav",
                cover: msg.cover_url ? toAbsoluteUrl(msg.cover_url) : ""
              }
            : null;
          
          restoredMessages.push({
            localId: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
            role: "assistant",
            text: msg.reply,
            createdAt: created,
            order,
            music: musicData
          });
          
          if (musicData) {
            if (msg.user_input) completedPrompts.push(msg.user_input);
            tracks.push({
              ...musicData,
              mood: msg.user_input || "",
              createdAt: created
            });
          }
        }
      });
    }

    // Merge "pending generation" cards for this dialogue (if any) so History opening isn't empty.
    const pending = loadPendingTasks().filter(t => t?.dialogueId === id);
    prunePendingTasksForDialogue(id, completedPrompts);
    const stillPending = pending.filter(t => {
      const p = (t?.prompt || "").trim();
      return !(p && completedPrompts.includes(p));
    });
    stillPending.forEach(t => {
      tracks.push({
        id: t.taskId ? `task:${t.taskId}` : (t.tempId ? `temp:${t.tempId}` : `pending:${Date.now()}`),
        music_file_id: null,
        title: t.title || (t.prompt ? `${t.prompt}`.slice(0, 20) + (t.prompt.length > 20 ? "..." : "") : "AI 生成作品"),
        artist: "AI Composer",
        url: "",
        duration: 0,
        format: "wav",
        cover: t.cover ? toAbsoluteUrl(t.cover) : "",
        mood: t.prompt || "",
        prompt: t.prompt || "",
        status: "generating",
        taskId: t.taskId || null,
        createdAt: t.createdAt || new Date().toISOString()
      });
    });

    messages.value = restoredMessages;
    generatedTracks.value = [];
    tracks.forEach((track, idx) => addTrack(track, idx + 1, track.createdAt));
    
    // 自动滚动到底部
    scrollToBottom();
  } catch (err) {
    console.error("加载对话详情失败:", err);
    error.value = "加载历史对话失败";
  }
};

const scrollToBottom = () => {
  setTimeout(() => {
    const el = document.getElementById('chatScroll');
    if (el) el.scrollTop = el.scrollHeight;
  }, 100);
};

const selectedModel = computed(() => null);
const displayTitle = computed(() => lastResponse.value?.title || "");
const currentTrack = computed(() =>
  generatedTracks.value.length ? generatedTracks.value[generatedTracks.value.length - 1] : null
);
const nextOrder = computed(() => {
  const maxOrder = messages.value.reduce((max, item) => Math.max(max, item.order || 0), 0);
  return (maxOrder || 0) + 1;
});

const appendPreset = (text) => {
  if (messageInput.value && !messageInput.value.endsWith(' ')) {
    messageInput.value += ' ' + text;
  } else {
    messageInput.value += text;
  }
};

const applyPreset = text => (messageInput.value = text);

const resetDialogue = () => {
  bumpSessionNonce();
  dialogueId.value = null;
  messages.value = [];
  generatedTracks.value = [];
  lastResponse.value = null;
  error.value = "";
  messageInput.value = "";
  modelIndex.value = 0;
  // Persist cleared session so navigating away/back won't resurrect the previous in-progress chat.
  saveSessionToStorage();
};

const addMessage = (role, text, meta = {}) => {
  const entry = {
    localId: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    text,
    createdAt: meta.createdAt || new Date().toISOString(),
    messageId: meta.messageId ?? null,
    order: meta.order ?? null,
    music: meta.music || null,
    // Used to bind an assistant placeholder message to a pending track generation.
    pendingTrackId: meta.pendingTrackId ?? null
  };
  messages.value.push(entry);
  scrollToBottom();
  return entry;
};

const addTrack = (track, order, createdAt) => {
  const normalized = {
    id: track.music_file_id || track.id || `${Date.now()}`,
    music_file_id: track.music_file_id || track.id || null,
    title: track.title || "AI 生成作品",
    artist: track.artist || "AI Composer",
    album: track.album || "",
    cover: track.cover || "",
    url: track.url,
    duration: track.duration || 0,
    mood: track.mood || track.genre || "",
    format: track.format || "",
    order: order || null,
    createdAt: createdAt || new Date().toISOString()
  };
  
  // 检查是否已存在，避免重复加载时添加
  const exists = generatedTracks.value.some(t => t.id === normalized.id);
  if (!exists) {
    generatedTracks.value = [...generatedTracks.value, normalized];
  }
};

const toAbsoluteUrl = url => {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;

  // Keep consistent with `src/services/api.js` default in dev.
  const rawBase = (
    (import.meta.env.VITE_API_BASE_URL || "").trim() ||
    (import.meta.env.DEV ? "http://127.0.0.1:8000" : window.location.origin)
  )
    .replace(/\/+$/, "")
    .replace(/\/api$/, "");

  if (url.startsWith("/static")) {
    const fileBase = rawBase.replace(/\/api$/, "");
    return `${fileBase}${url}`;
  }

  return `${rawBase}${url.startsWith("/") ? "" : "/"}${url}`;
};

const normalizeResponse = payload => {
  const data =
    payload && typeof payload === "object" && "data" in payload && payload.data
      ? payload.data
      : payload || {};

  const trackUrl = data.music_url || data.musicUrl;
  const track = trackUrl
    ? {
        id: data.music_file_id || data.music_id || data.id || data.message_id || `${Date.now()}`,
        music_file_id: data.music_file_id || data.music_id || null,
        // 标题统一规则：优先后端生成标题（title/dialogue_title），再兜底用户输入
        title: data.title || data.dialogue_title || data.user_input || data.message || "AI 生成作品",
        artist: "AI Composer",
        album: "",
        cover: data.cover_url ? toAbsoluteUrl(data.cover_url) : "",
        url: toAbsoluteUrl(trackUrl),
        duration: data.duration_seconds ?? data.duration ?? 0,
        mood: data.user_input || "",
        format: data.format || ""
      }
    : null;

  return {
    dialogueId: data.dialogue_id ?? data.dialogueId ?? null,
    messageId: data.message_id ?? data.id ?? null,
    userMessage: data.user_input ?? data.message ?? data.user_message ?? "",
    systemReply: data.reply ?? data.system_reply ?? "",
    order: data.message_order ?? data.order ?? null,
    title: data.dialogue_title ?? data.title ?? "",
    createdAt: data.created_at ?? null,
    track
  };
};

const sendMessage = async () => {
  const requestNonce = sessionNonce.value;
  const text = messageInput.value.trim();
  if (!text) {
    error.value = "请先输入要生成的描述";
    return;
  }

  const provisionalOrder = nextOrder.value;
  const now = new Date().toISOString();
  
  // 1. 立即在 UI 中显示用户的消息
  addMessage("user", text, { order: provisionalOrder, createdAt: now });
  messageInput.value = "";

  // 2. 创建一个临时的“生成中”条目，立即展示在右侧边栏
  const tempId = `temp-${Date.now()}`;
  const pendingTrack = {
    id: tempId,
    title: text.substring(0, 20) + (text.length > 20 ? "..." : ""),
    mood: text,
    prompt: text,
    instrumental: isInstrumental.value,
    lyrics: isInstrumental.value ? null : (lyricsInput.value || "").trim() || null,
    status: 'generating', // 这会让 sidebar 里的 MusicGenerationCard 显示 is-generating 状态
    createdAt: now,
    startedAt: now,
    cover: null,
    duration: 0
  };
  // 插入到列表顶部（参考 Suno 逻辑，最新生成的在最上面）
  generatedTracks.value = [pendingTrack, ...generatedTracks.value];
  // Immediately persist pending task (even before we have dialogueId/taskId) so History can show it.
  upsertPendingTask({
    dialogueId: dialogueId.value || null,
    draftNonce: requestNonce,
    tempId,
    taskId: null,
    prompt: text,
    title: pendingTrack.title,
    cover: null,
    createdAt: now,
    status: "generating"
  });
  saveSessionToStorage();

  sending.value = true;
  error.value = "";

  try {
    const body = { message: text };
    if (dialogueId.value) body.dialogue_id = dialogueId.value;
    body.instrumental = !!isInstrumental.value;
    body.lyrics = isInstrumental.value ? null : (lyricsInput.value || "").trim() || null;

    // 3) 封面生成与任务创建并行：
    // - 任务（taskId）必须尽快拿到，保证离开页面也能恢复
    // - 封面异步返回后再更新卡片（满足“cover first”视觉反馈）
    generateCoverOnly({ prompt: text })
      .then(res => res?.cover_url)
      .then(coverUrl => {
        if (!coverUrl) return;
        const track = generatedTracks.value.find(t => t.id === tempId);
        if (track) {
          track.cover = toAbsoluteUrl(coverUrl);
        }
        upsertPendingTask({
          tempId,
          draftNonce: requestNonce,
          cover: coverUrl
        });
        saveSessionToStorage();
      })
      .catch((coverErr) => {
        console.error("封面先行生成失败:", coverErr);
      });

    // 4) 提交异步生成任务 (chatWithDialogueAsync)
    const res = await chatWithDialogueAsync(body);
    // If user started a new conversation while we were waiting, ignore this late response.
    if (requestNonce !== sessionNonce.value) {
      return;
    }
    const taskId = res.task_id;
    dialogueId.value = res.dialogue_id;

    // 更新本地 pending 记录，存入真正的 taskId
    const track = generatedTracks.value.find(t => t.id === tempId);
    if (track) {
      track.taskId = taskId;
    }
    // Now that we have dialogueId/taskId, bind the pending task to this dialogue.
    upsertPendingTask({
      dialogueId: res.dialogue_id,
      draftNonce: requestNonce,
      tempId,
      taskId,
      prompt: text,
      title: track?.title || pendingTrack.title,
      cover: track?.cover || null,
      createdAt: now,
      status: "generating"
    });
    saveSessionToStorage();

    // 5. 立即开启任务状态轮询
    pollTaskStatus(taskId, tempId);

    // 6. 添加一个临时的 AI 回复气泡，提示正在生成
    addMessage("assistant", "正在为您精心编排旋律，请稍候...", {
      order: provisionalOrder,
      createdAt: now,
      music: null,
      pendingTrackId: tempId
    });

  } catch (err) {
    error.value = err?.message || "请求发送失败，请稍后重试";
    // 移除占位条目
    const idx = generatedTracks.value.findIndex(t => t.id === tempId);
    if (idx !== -1) generatedTracks.value.splice(idx, 1);
    // 同步移除对应的占位 assistant 消息（避免残留）
    const msgIdx = messages.value.findIndex(m => m.role === "assistant" && m.pendingTrackId === tempId);
    if (msgIdx !== -1) messages.value.splice(msgIdx, 1);
    sending.value = false;
  } finally {
    sending.value = false;
  }
};

const triggerImitatePick = () => {
  if (sending.value) return;
  if (imitateFileInputRef.value) {
    imitateFileInputRef.value.value = ""; // allow picking same file again
    imitateFileInputRef.value.click();
  }
};

const onImitateFileChange = async (e) => {
  const file = e?.target?.files?.[0];
  if (!file) return;
  await sendImitate(file);
};

const sendImitate = async (file) => {
  const text = (messageInput.value || "").trim(); // 可为空：纯仿写只靠参考音频
  const now = new Date().toISOString();
  const tempId = `temp-imitate-${Date.now()}`;

  // 创建一个临时“生成中”条目
  const pendingTrack = {
    id: tempId,
    title: text ? (text.substring(0, 20) + (text.length > 20 ? "..." : "")) : (file.name || "音乐仿写"),
    mood: text || "音乐仿写",
    prompt: text || "",
    instrumental: isInstrumental.value,
    lyrics: isInstrumental.value ? null : (lyricsInput.value || "").trim() || null,
    status: 'generating',
    createdAt: now,
    startedAt: now,
    cover: null,
    duration: 0,
    can_save: false
  };
  generatedTracks.value = [pendingTrack, ...generatedTracks.value];

  sending.value = true;
  error.value = "";

  try {
    // 封面先行（可选）
    if (text) {
      generateCoverOnly({ prompt: text })
        .then(res => res?.cover_url)
        .then(coverUrl => {
          if (!coverUrl) return;
          const track = generatedTracks.value.find(t => t.id === tempId);
          if (track) track.cover = toAbsoluteUrl(coverUrl);
        })
        .catch(() => {});
    }

    const res = await imitateMusicAsync({
      file,
      prompt: text,
      duration_seconds: DEFAULT_DURATION_SECONDS,
      instrumental: !!isInstrumental.value,
      lyrics: isInstrumental.value ? null : (lyricsInput.value || "").trim() || null
    });
    const taskId = res.task_id;

    const track = generatedTracks.value.find(t => t.id === tempId);
    if (track) track.taskId = taskId;

    pollTaskStatus(taskId, tempId);

    // 添加一个临时 assistant 气泡
    addMessage("assistant", "正在根据你的参考音频进行音乐仿写，请稍候...", {
      order: nextOrder.value,
      createdAt: now,
      music: null,
      pendingTrackId: tempId
    });
  } catch (err) {
    error.value = err?.message || "仿写请求失败，请稍后重试";
    const idx = generatedTracks.value.findIndex(t => t.id === tempId);
    if (idx !== -1) generatedTracks.value.splice(idx, 1);
    const msgIdx = messages.value.findIndex(m => m.role === "assistant" && m.pendingTrackId === tempId);
    if (msgIdx !== -1) messages.value.splice(msgIdx, 1);
  } finally {
    sending.value = false;
  }
};

const playMusicFromSidebar = track => {
  const trackIndex = generatedTracks.value.findIndex(t => t.id === track.id);
  if (trackIndex >= 0) {
    player.setPlaylist(generatedTracks.value, trackIndex);
    player.playTrack(trackIndex);
  }
};

const addToWorks = async track => {
  if (!track) return;
  const musicFileId = track.music_file_id || track.id;
  if (!musicFileId) {
    error.value = "找不到音乐文件ID，无法保存作品";
    return;
  }
  
  if (addedWorkIds.value.has(musicFileId)) return;
  if (addingWorkId.value) return;
  
  addingWorkId.value = musicFileId;
  error.value = "";
  try {
    await createWork({
      music_file_id: musicFileId,
      title: track.title || track.mood || "AI 生成作品",
      description: "", // 保持描述为空，除非用户之后手动编辑发布
      mood: track.prompt || track.mood || "", // 将生成需求（Prompt）存储在 mood 字段中
      cover_url: track.cover || null,
    });
    addedWorkIds.value.add(musicFileId);
    showToast("已加入本地作品");
  } catch (err) {
    error.value = err?.message || "添加到作品失败";
  } finally {
    addingWorkId.value = null;
  }
};
</script>

<style scoped>
:global(body) {
  font-family: "Inter", system-ui, -apple-system, "Microsoft YaHei", sans-serif;
}

.page {
  display: flex;
  height: calc(100vh - 100px); /* Adjust based on your header/player height */
  gap: 0;
  padding: 0;
  color: #e2e8f0;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 20px;
}

.panel {
  background: rgba(17, 24, 39, 0.4);
  backdrop-filter: blur(18px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 12px 30px rgba(0, 0, 0, 0.2);
}

.chat-panel {
  flex: 1;
  overflow: hidden;
  padding: 0;
}

.panel-header {
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.panel-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #f1f5f9;
}

.eyebrow {
  margin: 0 0 4px;
  font-size: 12px;
  letter-spacing: 0.1em;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
}

.chat-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chat-flow {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.chat-step {
  display: flex;
  width: 100%;
}

.chat-step.user {
  justify-content: flex-end;
}

.chat-step.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.6;
}

.chat-step.user .bubble {
  background: #3b82f6;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-step.assistant .bubble {
  background: rgba(255, 255, 255, 0.08);
  color: #e2e8f0;
  border-bottom-left-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.controls-area {
  padding: 20px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(0, 0, 0, 0.2);
}

.textarea-container {
  position: relative;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 12px;
  transition: all 0.2s ease;
}

.textarea-container:focus-within {
  border-color: rgba(59, 130, 246, 0.5);
  background: rgba(255, 255, 255, 0.08);
}

.chat-input {
  width: 100%;
  background: transparent;
  border: none;
  color: #f1f5f9;
  font-size: 15px;
  line-height: 1.6;
  resize: none;
  min-height: 80px;
  max-height: 200px;
  outline: none;
  padding: 0;
  margin-bottom: 8px;
}

.chat-input::placeholder {
  color: rgba(255, 255, 255, 0.2);
}

.mode-row {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.mode-chip {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.6);
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.mode-chip:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.mode-chip.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #fff;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.imitate-chip {
  border-style: dashed;
  color: #93c5fd;
}

.imitate-chip:hover {
  border-style: solid;
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
}

.mode-chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.lyrics-section {
  margin-top: 16px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 12px;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.section-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
  font-weight: 600;
}

.lyrics-input {
  width: 100%;
  background: transparent;
  border: none;
  color: #e2e8f0;
  padding: 0;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
  min-height: 80px;
  outline: none;
}

.lyrics-input::placeholder {
  color: rgba(255, 255, 255, 0.2);
}

.input-actions {
  position: absolute;
  bottom: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Inspiration Chips */
.inspiration-container {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.inspiration-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.group-label {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
  min-width: 40px;
}

.chips-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.insp-chip {
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  color: #94a3b8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.insp-chip:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(59, 130, 246, 0.4);
  color: #f1f5f9;
  transform: translateY(-1px);
}

.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #3b82f6;
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.duration-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: #94a3b8;
  cursor: pointer;
  font-size: 11px;
}

.duration-popover {
  position: absolute;
  bottom: 50px;
  right: 0;
  background: #1e293b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 16px;
  width: 240px;
  z-index: 100;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

.toast {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  z-index: 1000;
  animation: slideDown 0.3s ease;
}

.toast-success {
  background: #10b981;
  color: #fff;
}

@keyframes slideDown {
  from { transform: translateX(-50%) translateY(-20px); opacity: 0; }
  to { transform: translateX(-50%) translateY(0); opacity: 1; }
}

.status {
  font-size: 13px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 8px;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  background: #3b82f6;
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.95); opacity: 0.5; }
  50% { transform: scale(1.05); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.5; }
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
}

@media (max-width: 1024px) {
  .page {
    flex-direction: column;
    height: auto;
    overflow: auto;
  }
  .chat-container {
    height: 600px;
  }
}
</style>
