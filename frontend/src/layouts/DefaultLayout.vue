<template>
  <div class="app">
    <!-- Fixed sidebar (desktop). Hidden on narrow widths/large zoom. -->
    <div class="sidebar-shell">
      <Sidebar />
    </div>

    <main class="main">
      <TopBar />

      <section class="content">
        <div class="bg-blur"></div>
        <slot />
      </section>

      <StickyPlayer />
    </main>

    <!-- Drawer sidebar (mobile / large zoom). -->
    <div v-if="ui.sidebarOpen" class="drawer-backdrop" @click.self="ui.closeSidebar()">
      <aside class="drawer" role="dialog" aria-label="导航菜单">
        <div class="drawer-header">
          <div class="drawer-title">导航</div>
          <button class="drawer-close" type="button" @click="ui.closeSidebar()">×</button>
        </div>
        <Sidebar class="drawer-sidebar" />
      </aside>
    </div>
  </div>
</template>

<script setup>
import { watch } from "vue";
import { useRoute } from "vue-router";
import Sidebar from "../components/Sidebar.vue";
import TopBar from "../components/TopBar.vue";
import StickyPlayer from "../components/StickyPlayer.vue";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const route = useRoute();

// When route changes, close the drawer to avoid covering the new page.
watch(
  () => route.fullPath,
  () => ui.closeSidebar()
);
</script>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  background: radial-gradient(circle at top left, #283a6f 0, #050816 45%, #000 100%);
  color: #fff;
  overflow: hidden;
}

.sidebar-shell {
  flex: 0 0 auto;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(12px);
  position: relative;
  min-height: 0;
  overflow: hidden;
}

.content {
  flex: 1;
  padding: 12px 24px 120px;
  position: relative;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.45) transparent;
  overscroll-behavior: contain;
}

.bg-blur {
  position: absolute;
  inset: -80px -160px auto auto;
  background:
    radial-gradient(circle at 10% 20%, rgba(129, 140, 248, 0.55), transparent 55%),
    radial-gradient(circle at 80% 10%, rgba(248, 113, 113, 0.6), transparent 55%),
    radial-gradient(circle at 50% 80%, rgba(56, 189, 248, 0.4), transparent 55%);
  opacity: 0.6;
  filter: blur(10px);
  z-index: -1;
  pointer-events: none;
}

.content::-webkit-scrollbar {
  width: 10px;
}

.content::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.45);
  border-radius: 999px;
}

.content::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.65);
}

.content::-webkit-scrollbar-track {
  background: transparent;
}

/* Suno-like: when viewport is narrow (including zoomed-in), hide fixed sidebar
   and rely on the topbar drawer menu instead. */
@media (max-width: 980px) {
  .sidebar-shell {
    display: none;
  }
  .content {
    padding: 12px 14px 120px;
  }
}

.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  z-index: 3000;
  display: flex;
}

.drawer {
  width: min(320px, 82vw);
  height: 100%;
  background: rgba(3, 7, 20, 0.98);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 18px 0 50px rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  animation: drawer-in 0.16s ease-out;
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.drawer-title {
  font-weight: 800;
  letter-spacing: 0.02em;
}

.drawer-close {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: #e5e7eb;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
}

.drawer-close:hover {
  border-color: rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.1);
}

.drawer-sidebar {
  width: 100% !important;
  border-right: none !important;
}

@keyframes drawer-in {
  from {
    transform: translateX(-10px);
    opacity: 0.6;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
</style>

