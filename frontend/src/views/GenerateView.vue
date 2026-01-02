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

            <!-- 生成模式：纯音乐 / 有人声 -->
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
            </div>

            <div v-if="!isInstrumental" class="lyrics-container">
              <textarea
                v-model="lyricsInput"
                :disabled="sending"
                placeholder="可选：输入你想要的歌词（支持 [verse]/[chorus] 结构）。不填则会用上面的描述作为歌词。"
                class="lyrics-input"
              ></textarea>
            </div>

              <div class="input-actions">
                <button
                  class="duration-btn"
                  type="button"
                  :disabled="sending"
                  @click="showDurationPopover = !showDurationPopover"
                  title="生成时长"
                >
                  <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
                  </svg>
                  <span class="duration-badge">{{ duration }}s</span>
                </button>
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
              <div v-if="showDurationPopover" class="duration-popover" @click.stop>
                <div class="popover-header">
                  <span>生成时长</span>
                  <button class="popover-close" @click="showDurationPopover = false">×</button>
                </div>
                <div class="popover-options">
                  <button
                    v-for="opt in durationOptions"
                    :key="opt"
                    class="duration-option"
                    :class="{ active: duration === opt }"
                    @click="duration = opt; showDurationPopover = false"
                  >
                    {{ opt }} 秒
                  </button>
                </div>
                <div class="popover-slider">
                  <input
                    type="range"
                    min="30"
                    max="300"
                    step="10"
                    v-model.number="duration"
                    :disabled="sending"
                  />
                  <div class="slider-labels">
                    <span>30s</span>
                    <span>300s</span>
                  </div>
                </div>
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
import { 
  chatWithDialogue, 
  getDialogueDetail, 
  generateCoverOnly,
  chatWithDialogueAsync,
  getMusicTaskStatus
} from "@/services/dialogueApi";
import { createWork } from "@/services/workApi";
import { usePlayerStore } from "@/stores/player";
import GenerateMusicSidebar from "./components/GenerateMusicSidebar.vue";

const route = useRoute();
const messageInput = ref("");
const dialogueId = ref(null);
const messages = ref([]);
const generatedTracks = ref([]);
const lastResponse = ref(null);
const sending = ref(false);
const error = ref("");
const modelIndex = ref(0);
const duration = ref(60);
const isInstrumental = ref(true);
const lyricsInput = ref("");
const addingWorkId = ref(null);
const addedWorkIds = ref(new Set()); // 跟踪已保存的作品ID
const showDurationPopover = ref(false);
const durationOptions = [30, 40, 60, 90, 120, 180, 300];
const toastMessage = ref("");
const toastType = ref("success");
let toastTimer = null;

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
const STORAGE_KEY = 'latest_music_generation_session';

const saveSessionToStorage = () => {
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
      dialogueId: dialogueId.value,
      messages: safeMessages,
      generatedTracks: safeTracks,
      lastResponse: lastResponse.value,
      timestamp: Date.now()
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessionData));
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
  const saved = localStorage.getItem(STORAGE_KEY);
  if (!saved) return false;

  try {
    const data = JSON.parse(saved);
    // 只恢复 24 小时内的会话，防止数据过旧
    if (Date.now() - data.timestamp > 86400000) {
      localStorage.removeItem(STORAGE_KEY);
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

const handleClickOutside = (e) => {
  if (showDurationPopover.value && !e.target.closest('.duration-btn') && !e.target.closest('.duration-popover')) {
    showDurationPopover.value = false;
  }
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
  
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

const loadDialogue = async id => {
  try {
    const data = await getDialogueDetail(id);
    dialogueId.value = id;

    const restoredMessages = [];
    const tracks = [];
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
                title: msg.user_input || msg.reply || "AI 生成作品",
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
            tracks.push({
              ...musicData,
              mood: msg.user_input || "",
              createdAt: created
            });
          }
        }
      });
    }
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
  dialogueId.value = null;
  messages.value = [];
  generatedTracks.value = [];
  lastResponse.value = null;
  error.value = "";
  messageInput.value = "";
  modelIndex.value = 0;
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
    (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")
  ).replace(/\/+$/, "");

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
        title: data.user_input || data.message || data.dialogue_title || data.title || "AI 生成作品",
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

  sending.value = true;
  error.value = "";

  try {
    const body = { message: text };
    body.duration_seconds = duration.value;
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
      })
      .catch((coverErr) => {
        console.error("封面先行生成失败:", coverErr);
      });

    // 4) 提交异步生成任务 (chatWithDialogueAsync)
    const res = await chatWithDialogueAsync(body);
    const taskId = res.task_id;
    dialogueId.value = res.dialogue_id;

    // 更新本地 pending 记录，存入真正的 taskId
    const track = generatedTracks.value.find(t => t.id === tempId);
    if (track) {
      track.taskId = taskId;
    }

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
  font-size: 14px;
  resize: none;
  min-height: 60px;
  max-height: 150px;
  outline: none;
  padding: 0;
  padding-right: 100px;
}

.mode-row {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  padding-right: 100px; /* 给右下角按钮留空间 */
  flex-wrap: wrap;
}

.mode-chip {
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  color: #cbd5e1;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.mode-chip.active {
  border-color: rgba(59, 130, 246, 0.6);
  background: rgba(59, 130, 246, 0.18);
  color: #93c5fd;
}

.mode-chip:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.lyrics-container {
  margin-top: 10px;
  padding-right: 100px; /* 给右下角按钮留空间 */
}

.lyrics-input {
  width: 100%;
  background: rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  resize: vertical;
  min-height: 70px;
  outline: none;
}

.lyrics-input:focus {
  border-color: rgba(59, 130, 246, 0.5);
}

.input-actions {
  position: absolute;
  bottom: 10px;
  right: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
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
