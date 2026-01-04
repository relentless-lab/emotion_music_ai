<template>
  <div class="page-shell">
    <div v-if="showLoginPanel" class="login-modal" @click.self="ui.closeLoginPanel()">
      <section class="panel login-panel" :class="{ register: ui.authMode === 'register' }">
        <div class="login-header">
          <div class="login-title">
            {{ ui.authMode === "login" ? "登录您的账户" : "注册新用户账户" }}
          </div>
          <button class="close-btn" type="button" @click="ui.closeLoginPanel()">关闭</button>
        </div>

        <form
          v-if="ui.authMode === 'login'"
          class="auth-form"
          @submit.prevent="handleLogin"
        >
          <label class="field">
            <span>请输入用户名</span>
            <input
              v-model="loginForm.username"
              type="text"
              placeholder="请输入用户名"
              required
            />
          </label>
          <label class="field">
            <span>密码</span>
            <input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              required
            />
          </label>

          <button class="cta primary" type="submit" :disabled="auth.loading">
            {{ auth.loading ? "登录中..." : "登录" }}
          </button>
          <p v-if="registerSuccess && ui.authMode === 'login'" class="success-text">{{ registerSuccess }}</p>
          <p v-if="auth.error" class="error-text">{{ auth.error }}</p>
        </form>

        <form
          v-else
          class="auth-form register-form"
          @submit.prevent="handleRegister"
        >
          <label class="field">
            <span>用户名</span>
            <input v-model="registerForm.username" type="text" placeholder="请输入用户名" required />
          </label>
          <label class="field">
            <span>电子邮箱</span>
            <input v-model="registerForm.email" type="email" placeholder="请输入电子邮箱" required />
          </label>
          <label class="field code-field">
            <span>验证码</span>
            <div class="code-row">
              <input v-model="registerForm.code" type="text" placeholder="请输入邮箱验证码" required />
              <button 
                class="ghost-btn" 
                type="button"
                :disabled="countdown > 0 || isSendingCode || !registerForm.email"
                @click="handleGetVerificationCode"
              >
                {{ countdown > 0 ? `${countdown}秒后重新获取` : isSendingCode ? "发送中..." : "获取验证码" }}
              </button>
            </div>
          </label>
          <label class="field">
            <span>密码</span>
            <input v-model="registerForm.password" type="password" placeholder="请输入密码" required />
          </label>
          <label class="field">
            <span>确认密码</span>
            <input
              v-model="registerForm.confirm"
              type="password"
              placeholder="再次输入密码"
              required
            />
          </label>

          <div class="terms">
            <input type="checkbox" required />
            <span>我同意服务条款和隐私政策</span>
          </div>

          <button class="cta primary" type="submit" :disabled="auth.loading">
            {{ auth.loading ? "注册中..." : "注册" }}
          </button>
          <p v-if="auth.error && ui.authMode === 'register'" class="error-text">{{ auth.error }}</p>
        </form>

        <div class="register-row">
          <span
            v-if="ui.authMode === 'login'"
            class="register-link"
            @click="ui.openRegisterPanel()"
          >
            还没有账号？立即注册
          </span>
          <span
            v-else
            class="register-link"
            @click="ui.openLoginPanel()"
          >
            已有账号？立即登录
          </span>
        </div>
      </section>
    </div>

    <div v-if="showLoginSuccessToast" class="toast success-toast">登录成功</div>
    <div v-if="showCodeSuccessToast" class="toast success-toast">验证码已发送</div>

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
            @play="playHotSong"
            @card-click="gotoSongDetail"
          />
        </div>
        <div class="expand-section">
          <button class="expand-button">
            <span>展开</span>
            <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
              <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
            </svg>
          </button>
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
          <CreatorCard v-for="creator in creators" :key="creator.id" :creator="creator" />
        </div>
        <div class="expand-section">
          <button class="expand-button">
            <span>展开</span>
            <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
              <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
            </svg>
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import Carousel from "./components/Carousel.vue";
import SongImageCard from "./components/SongImageCard.vue";
import CreatorCard from "./components/CreatorCard.vue";
import { useAuthStore } from "../stores/auth";
import { useUiStore } from "../stores/ui";
import { sendVerificationCode } from "../services/authApi";
import SearchHeader from "@/components/SearchHeader.vue";
import { fetchHotSongs, fetchRecommendedCreators } from "@/services/uiApi";
import { usePlayerStore } from "@/stores/player";

const auth = useAuthStore();
const ui = useUiStore();
const router = useRouter();
const player = usePlayerStore();

// Convert backend-returned relative URLs (/static, /media, /uploads) to absolute URLs
// so HomeView works in dev / when VITE_API_BASE_URL is set (frontend-backend not same-origin).
const API_BASE_URL = ((import.meta.env.VITE_API_BASE_URL || "").trim()
  || (import.meta.env.DEV ? "http://127.0.0.1:8000" : window.location.origin))
  .replace(/\/+$/, "")
  .replace(/\/api$/, "");

const toAbsoluteUrl = url => {
  if (!url) return "";
  if (url.startsWith("http") || url.startsWith("data:") || url.startsWith("blob:")) return url;
  const base = API_BASE_URL || window.location.origin;
  const fileBase = base.replace(/\/api$/, "");
  return url.startsWith("/") ? `${fileBase}${url}` : `${fileBase}/${url}`;
};

const loginForm = reactive({
  username: "",
  password: ""
});

const registerForm = reactive({
  username: "",
  email: "",
  code: "",
  password: "",
  confirm: ""
});

const registerSuccess = ref("");
const showLoginSuccessToast = ref(false);
let loginSuccessTimer;
const searchKeyword = ref("");

// 验证码相关状态
const countdown = ref(0);
const isSendingCode = ref(false);
const showCodeSuccessToast = ref(false);
let countdownTimer = null;
let codeSuccessTimer = null;

const triggerLoginSuccessToast = () => {
  if (loginSuccessTimer) {
    clearTimeout(loginSuccessTimer);
  }
  showLoginSuccessToast.value = true;
  loginSuccessTimer = setTimeout(() => {
    showLoginSuccessToast.value = false;
  }, 1000);
};

const handleLogin = async () => {
  auth.error = "";
  registerSuccess.value = "";
  const username = loginForm.username.trim();
  const password = loginForm.password;
  if (!username || !password) {
    auth.error = "请填写用户名和密码";
    return;
  }
  try {
    await auth.loginAction({ username, password });
    triggerLoginSuccessToast();
    loginForm.password = "";
    ui.closeLoginPanel();
  } catch (err) {
    // error 已写入 store
  }
};

const handleGetVerificationCode = async () => {
  const email = registerForm.email.trim();
  if (!email) {
    auth.error = "请先输入邮箱地址";
    return;
  }
  
  // 简单的邮箱格式验证
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    auth.error = "请输入有效的邮箱地址";
    return;
  }
  
  isSendingCode.value = true;
  auth.error = "";
  
  try {
    await sendVerificationCode(email);
    // 显示成功提示
    showCodeSuccessToast.value = true;
    if (codeSuccessTimer) {
      clearTimeout(codeSuccessTimer);
    }
    codeSuccessTimer = setTimeout(() => {
      showCodeSuccessToast.value = false;
    }, 2000);
    
    // 开始倒计时
    countdown.value = 60;
    if (countdownTimer) {
      clearInterval(countdownTimer);
    }
    countdownTimer = setInterval(() => {
      countdown.value--;
      if (countdown.value <= 0) {
        clearInterval(countdownTimer);
        countdownTimer = null;
      }
    }, 1000);
  } catch (err) {
    // 错误信息已在api.js中处理，这里可以显示具体错误
    if (err.response?.data?.detail) {
      auth.error = err.response.data.detail;
    } else {
      auth.error = "验证码发送失败，请稍后重试";
    }
  } finally {
    isSendingCode.value = false;
  }
};

const handleRegister = async () => {
  auth.error = "";
  registerSuccess.value = "";
  const username = registerForm.username.trim();
  const email = registerForm.email.trim();
  const password = registerForm.password;
  const confirm = registerForm.confirm;

  if (!username || !email || !password || !confirm) {
    auth.error = "请完整填写注册信息";
    return;
  }
  if (password !== confirm) {
    auth.error = "两次密码不一致";
    return;
  }
  if (!registerForm.code) {
    auth.error = "请输入验证码";
    return;
  }

  try {
    await auth.registerAction({
      username,
      email,
      code: registerForm.code,
      password
    });
    registerSuccess.value = "注册成功，请登录";
    loginForm.username = username;
    ui.setAuthMode("login");
  } catch (err) {
    // error ��д�� store
  }
};

const showLoginPanel = computed(() => ui.showLoginPanel && !auth.isLoggedIn);

const gotoSearch = () => {
  const q = searchKeyword.value.trim();
  if (!q) return;
  router.push({ name: "search", query: { q, type: "all" } });
};

onMounted(() => {
  auth.refreshProfile();
});

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

const loadHotSongs = async () => {
  try {
    const res = await fetchHotSongs({ limit: 8, window_days: 3 });
    if (Array.isArray(res) && res.length) {
      songs.value = res.map(item => ({
        id: item.id,
        title: item.title,
        authorName: item.author_name || "AI Composer",
        // StickyPlayer 读取 currentTrack.cover / currentTrack.artist
        artist: item.author_name || "AI Composer",
        cover_url: item.cover_url || "",
        coverImage: toAbsoluteUrl(item.cover_url || ""),
        cover: toAbsoluteUrl(item.cover_url || ""),
        play_count: item.play_count ?? 0,
        playCount: item.play_count ?? 0,
        like_count: item.like_count ?? 0,
        audio_url: item.audio_url || "",
        url: toAbsoluteUrl(item.audio_url || ""),
        tags: item.tags || "",
        mood: item.mood || "",
        // 用于 player 上报过滤
        status: "published",
        visibility: "public"
      }));
    }
  } catch {
    // ignore
  }
};

const loadRecommendedCreators = async () => {
  try {
    const res = await fetchRecommendedCreators({ limit: 9 });
    if (Array.isArray(res) && res.length) {
      creators.value = res.map(item => ({
        id: item.id,
        name: item.name,
        followers: item.followers,
        handle: item.handle,
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
  if (loginSuccessTimer) {
    clearTimeout(loginSuccessTimer);
  }
  if (countdownTimer) {
    clearInterval(countdownTimer);
  }
  if (codeSuccessTimer) {
    clearTimeout(codeSuccessTimer);
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
    avatar: "/avatars/02567c1fd7d6e84c7bc3f5eb83fbb20b.jpg"
  },
  {
    id: 2,
    name: "Brutus",
    followers: "17K followers",
    handle: "@brutus",
    avatar: "/avatars/13b2894291a2545053b7b80245b3ad49.jpg"
  },
  {
    id: 3,
    name: "EvilTyremancer",
    followers: "14K followers",
    handle: "@eviltyremancer",
    avatar: "/avatars/2dc212f966be73e8ff964aac88208167.jpg"
  },
  {
    id: 4,
    name: "MusicMaster",
    followers: "23K followers",
    handle: "@musicmaster",
    avatar: "/avatars/32b72fbc42357a2646642f721e3557fe.jpg"
  },
  {
    id: 5,
    name: "BeatMaker",
    followers: "8.7K followers",
    handle: "@beatmaker",
    avatar: "/avatars/b5e9f4ec3ba35ebf2ef7aaf134f63072_0.jpg"
  },
  {
    id: 6,
    name: "SoundWave",
    followers: "12.5K followers",
    handle: "@soundwave",
    avatar: "/avatars/bfd6dd67f27836dbe2df91b7b70daeae_0.jpg"
  },
  {
    id: 7,
    name: "MelodyMaker",
    followers: "9.8K followers",
    handle: "@melodymaker",
    avatar: "/avatars/c9fa4c3f8bb8e93a7e8512ad6b101bb0_0.jpg"
  },
  {
    id: 8,
    name: "RhythmKing",
    followers: "15.3K followers",
    handle: "@rhythmking",
    avatar: "/avatars/e294b24b73ddf1aaa579391c508ae5a8.jpg"
  },
  {
    id: 9,
    name: "Harmony",
    followers: "11.2K followers",
    handle: "@harmony",
    avatar: "/avatars/f29a797b0989af458f4903f961f1b9b4.jpg"
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

.login-modal {
  position: fixed;
  inset: 0;
  background: rgba(3, 7, 18, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 16px;
}

.login-panel {
  padding: 24px 24px 28px;
  max-width: 420px;
  width: 100%;
  margin-left: -20px;
}

.login-panel.register {
  max-width: 420px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 18px;
}

.auth-form .field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.auth-form .field span {
  color: #f9fafb;
  font-weight: 600;
  font-size: 14px;
}

.auth-form input {
  height: 40px;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(12, 16, 26, 0.95);
  color: #f3f4f6;
  padding: 0 12px;
  outline: none;
}

.auth-form input:focus {
  border-color: rgba(79, 133, 255, 0.9);
  box-shadow: 0 0 0 2px rgba(79, 133, 255, 0.35);
}

.register-form {
  gap: 10px;
}

.code-field .code-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: center;
}

.ghost-btn {
  height: 40px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(255, 255, 255, 0.06);
  color: #e5e7eb;
  cursor: pointer;
  font-weight: 600;
}

.ghost-btn:hover:not(:disabled) {
  border-color: rgba(79, 133, 255, 0.8);
}

.ghost-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cta {
  height: 42px;
  padding: 0 14px;
  border-radius: 10px;
  border: none;
  color: #f8fafc;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: 0 10px 22px rgba(59, 130, 246, 0.3);
}

.cta.primary {
  background: #4f85ff;
}

.login-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.cta:hover {
  transform: translateY(-1px);
}

.login-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.login-title {
  text-align: center;
  font-weight: 700;
}

.error-text {
  color: #f87171;
  font-size: 13px;
}

.success-text {
  color: #10b981;
  font-size: 13px;
}

.close-btn {
  background: none;
  border: none;
  color: rgba(229, 231, 235, 0.9);
  cursor: pointer;
  font-weight: 600;
  padding: 6px 8px;
  border-radius: 8px;
  transition: background 0.15s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.04);
}

.register-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 14px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
}

.register-link {
  cursor: pointer;
}

.register-link:hover {
  color: #9cbcff;
}

.terms {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: rgba(229, 231, 235, 0.85);
}

.terms input {
  width: 14px;
  height: 14px;
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
