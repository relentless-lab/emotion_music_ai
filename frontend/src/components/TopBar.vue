<template>
  <header class="topbar">
    <div class="row row-top">
      <div class="top-left">
        <!-- Menu button shown when sidebar is hidden (mobile / large zoom) -->
        <button class="menu-btn" type="button" title="菜单" @click="ui.toggleSidebar()">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 6h16" />
            <path d="M4 12h16" />
            <path d="M4 18h16" />
          </svg>
        </button>
        <div class="title-stack">
          <div class="logo-title">音乐创作工作台</div>
          <div class="top-subtitle">{{ currentNavName }} · 让每一次点击都长出一小段旋律</div>
        </div>
      </div>
      <nav class="top-actions">
        <RouterLink to="/notifications" class="top-btn" title="通知">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 9a6 6 0 0 1 12 0c0 3.5 1 5 2 6H4c1-1 2-2.5 2-6Z" />
            <path d="M10 19a2 2 0 0 0 4 0" />
          </svg>
          <span>通知</span>
        </RouterLink>
        <RouterLink v-if="auth.isLoggedIn" to="/account" class="top-btn" title="账户设置">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path
              d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9c0 .7.6 1.3 1.3 1.3H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.4.7Z"
            />
          </svg>
          <span>账户设置</span>
        </RouterLink>
        <button v-else class="top-btn" type="button" title="账户设置" @click="openAccountSettings">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="3" />
            <path
              d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 0 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9c0 .7.6 1.3 1.3 1.3H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.4.7Z"
            />
          </svg>
          <span>账户设置</span>
        </button>
        <RouterLink v-if="auth.isLoggedIn" to="/profile" class="top-btn" title="个人资料">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="8" r="4" />
            <path d="M6 20c0-2.2 2.7-4 6-4s6 1.8 6 4" />
          </svg>
          <span>个人资料</span>
        </RouterLink>
        <button v-else class="top-btn" type="button" title="登录" @click="ui.openLoginPanel()">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
            <path d="m10 17 5-5-5-5" />
            <path d="M15 12H3" />
          </svg>
          <span>登录</span>
        </button>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";

const route = useRoute();
const auth = useAuthStore();
const ui = useUiStore();

const openAccountSettings = () => {
  // 文案展示在 AuthModal 内（auth.error）
  auth.error = "请先进行登录";
  ui.openLoginPanel();
};

const routeNameMap = {
  "/": "首页",
  "/generate": "音乐生成",
  "/emotion": "情绪识别",
  "/works": "我的作品",
  "/history": "历史记录",
  "/notifications": "通知",
  "/profile": "个人资料",
  "/account": "账户设置"
};

const currentNavName = computed(() => {
  if (route.name === "search") return "搜索";
  if (route.name === "songDetail") return "歌曲详情";
  if (route.name === "userPublic") return "用户主页";
  return routeNameMap[route.path] ?? "首页";
});
</script>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 1000;
  padding: 8px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  background: linear-gradient(to right, rgba(3, 7, 18, 0.98), rgba(3, 7, 18, 0.9));
}

.row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.row-top {
  justify-content: space-between;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.top-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.06);
  color: #e5e7eb;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.16s ease-out;
}

.top-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.16);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.4);
  background: rgba(255, 255, 255, 0.1);
}

.top-btn svg {
  width: 16px;
  height: 16px;
  stroke: rgba(255, 255, 255, 0.8);
  fill: none;
  stroke-width: 1.8;
}

.top-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.title-stack {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.menu-btn {
  display: none;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.06);
  color: #e5e7eb;
  cursor: pointer;
  transition: all 0.16s ease-out;
}

.menu-btn:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.16);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.4);
  background: rgba(255, 255, 255, 0.1);
}

.menu-btn svg {
  width: 18px;
  height: 18px;
  stroke: rgba(255, 255, 255, 0.85);
  fill: none;
  stroke-width: 2.2;
}

.logo-title {
  flex-shrink: 0;
}

.top-subtitle {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Show hamburger when sidebar is hidden */
@media (max-width: 980px) {
  .menu-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
}

.logo-title {
  font-size: 16px;
  font-weight: 700;
}

.top-title {
  font-size: 16px;
  font-weight: 600;
}

.top-subtitle {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
}
</style>
