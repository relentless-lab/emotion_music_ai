<template>
  <div class="history-page">
    <header class="page-header">
      <div>
        <h2>历史记录</h2>
        <div class="tabs" role="tablist" aria-label="历史记录分类">
          <button
            class="tab"
            :class="{ active: activeTab === 'dialogue' }"
            type="button"
            role="tab"
            :aria-selected="activeTab === 'dialogue'"
            @click="activeTab = 'dialogue'"
          >
            音乐对话
            <span class="badge">{{ dialogueCount }}</span>
          </button>
          <button
            class="tab"
            :class="{ active: activeTab === 'emotion' }"
            type="button"
            role="tab"
            :aria-selected="activeTab === 'emotion'"
            @click="activeTab = 'emotion'"
          >
            情绪识别
            <span class="badge">{{ emotionCount }}</span>
          </button>
        </div>
      </div>
    </header>

    <section class="list-card">
      <div v-if="loading" class="state">加载中...</div>
      <div v-else-if="error" class="state error">
        <span>{{ error }}</span>
        <button class="ghost" @click="refresh">重试</button>
      </div>
      <div v-else-if="filteredList.length === 0" class="state">暂无记录</div>
      <div v-else class="history-list">
        <HistoryItem v-for="item in filteredList" :key="item.id" :item="item" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useHistoryStore } from "@/stores/history";
import { useAuthStore } from "@/stores/auth";
import HistoryItem from "@/components/HistoryItem.vue";

const historyStore = useHistoryStore();
const auth = useAuthStore();
const { items, loading, error } = storeToRefs(historyStore);

const historyList = computed(() => items.value || []);
const activeTab = ref("dialogue"); // "dialogue" | "emotion"

const isEmotion = item => {
  const t = (item?.type || "").toString().toLowerCase();
  return t.includes("emotion") || t.includes("情绪") || t.includes("识别");
};

const dialogueList = computed(() => historyList.value.filter(i => !isEmotion(i)));
const emotionList = computed(() => historyList.value.filter(i => isEmotion(i)));

const dialogueCount = computed(() => dialogueList.value.length);
const emotionCount = computed(() => emotionList.value.length);

const filteredList = computed(() => {
  return activeTab.value === "emotion" ? emotionList.value : dialogueList.value;
});

const refresh = () => historyStore.loadHistory();

onMounted(() => {
  historyStore.syncScope();
  refresh();
});

// 退出登录 / 切换账号后：立即清空历史列表，避免计数残留（7/1 等）
watch(
  () => auth.token,
  token => {
    // token 变化（登录/退出）时都同步 scope；退出时会强制清空 items，使 badge 归零
    historyStore.syncScope();
    if (token) refresh();
  }
);

</script>

<style scoped>
.history-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 10px 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  color: #f1f5f9;
}

.tabs {
  margin-top: 16px;
  display: flex;
  gap: 32px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0;
  background: transparent;
  border: none;
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 12px 4px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-weight: 600;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  outline: none;
}

.tab:hover {
  color: #e2e8f0;
}

.tab.active {
  color: #3b82f6;
  font-weight: 700;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: #3b82f6;
  box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
  border-radius: 2px;
}

.badge {
  font-size: 12px;
  font-weight: 500;
  opacity: 0.6;
  background: rgba(255, 255, 255, 0.1);
  padding: 1px 6px;
  border-radius: 6px;
  margin-left: 2px;
}

.tab.active .badge {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
  opacity: 1;
}

.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #e6ebf5;
}

.list-card {
  padding: 0;
  background: transparent;
  border: none;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.state {
  padding: 16px;
  text-align: center;
  color: rgba(255, 255, 255, 0.78);
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed rgba(148, 163, 184, 0.25);
  border-radius: 12px;
}

.state.error {
  color: #fca5a5;
  background: rgba(248, 113, 113, 0.08);
  border-color: rgba(248, 113, 113, 0.3);
}

.ghost {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(148, 163, 184, 0.3);
  color: #e5e7eb;
  padding: 8px 12px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ghost:hover {
  border-color: rgba(59, 130, 246, 0.6);
  box-shadow: 0 10px 22px rgba(59, 130, 246, 0.25);
}

@media (max-width: 820px) {
  .tabs {
    width: 100%;
    justify-content: space-between;
  }
  .tab {
    flex: 1;
    justify-content: center;
  }
}
</style>
