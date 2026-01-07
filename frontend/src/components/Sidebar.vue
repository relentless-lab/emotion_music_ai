<template>
  <aside class="sidebar">
    <div class="logo">
      <div class="logo-icon">🎵</div>
      <div>
        <div class="logo-text">AI 音乐工坊</div>
        <div class="logo-sub">让灵感秒变成声音</div>
      </div>
    </div>

    <div class="sidebar-section-title">导航</div>
    <nav class="nav-list">
      <RouterLink
        v-for="item in sidebarItems"
        :key="item.key"
        :to="item.path"
        class="nav-item"
        :class="{ active: route.path === item.path }"
        @click="ui.closeSidebar()"
      >
        <div class="nav-icon">
          <span>{{ item.icon }}</span>
        </div>
        <div class="nav-label">{{ item.label }}</div>
        <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
      </RouterLink>
    </nav>

    <div class="sidebar-spacer"></div>
  </aside>
</template>

<script setup>
import { useRoute } from "vue-router";
import { useUiStore } from "@/stores/ui";

const route = useRoute();
const ui = useUiStore();

const sidebarItems = [
  { key: "home", label: "首页", icon: "🏠", path: "/" },
  { key: "generate", label: "音乐生成", icon: "🎹", path: "/generate", badge: "AI" },
  { key: "emotion", label: "情绪识别", icon: "💡", path: "/emotion" },
  { key: "works", label: "我的作品", icon: "🎧", path: "/works" },
  { key: "history", label: "历史记录", icon: "🕒", path: "/history" }
];
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width, 168px);
  background: rgba(3, 7, 20, 0.96);
  border-right: 1px solid rgba(255, 255, 255, 0.04);
  padding: 20px 10px 20px 6px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* When used inside the drawer (mobile / large zoom), let it fill the drawer width. */
@media (max-width: 980px) {
  .sidebar {
    width: 100%;
  }
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.logo-icon {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  background: linear-gradient(135deg, #ff4b92, #ffcc4b);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
}

.logo-text {
  font-weight: 600;
  font-size: 16px;
}

.logo-sub {
  font-size: 11px;
  opacity: 0.6;
}

.sidebar-section-title {
  margin-top: 8px;
  margin-bottom: 6px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.45);
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 6px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  color: #a2a7b8;
  transition: all 0.16s ease-out;
  text-decoration: none;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.nav-item.active {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  color: #fff;
}

.nav-icon {
  width: 18px;
  height: 18px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.nav-label {
  flex: 1;
}

.nav-badge {
  min-width: 16px;
  height: 16px;
  border-radius: 999px;
  background: rgba(234, 179, 8, 0.14);
  color: #facc15;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 4px;
}

.sidebar-spacer {
  flex: 1;
}

.sidebar-footer {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
</style>
