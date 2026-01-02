<template>
  <div class="app">
    <Sidebar />

    <main class="main">
      <TopBar />

      <section class="content">
        <div class="bg-blur"></div>
        <slot />
      </section>

      <StickyPlayer />
    </main>
  </div>
</template>

<script setup>
import Sidebar from "../components/Sidebar.vue";
import TopBar from "../components/TopBar.vue";
import StickyPlayer from "../components/StickyPlayer.vue";
</script>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  background: radial-gradient(circle at top left, #283a6f 0, #050816 45%, #000 100%);
  color: #fff;
  overflow: hidden;
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
</style>

