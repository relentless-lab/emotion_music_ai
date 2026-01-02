<template>
  <div class="history-row">
    <div class="row-header">
      <div class="title">{{ item.title || "未命名记录" }}</div>
      <button class="action-btn" type="button" @click="handleViewDetail">
        <span class="action-icon">🔎</span>
        查看详情
      </button>
    </div>
    <div class="row-body">
      <div class="icon-box">{{ icon }}</div>
      <div class="meta-line">
        <span class="meta">{{ typeLabel }}</span>
        <span class="dot">·</span>
        <span class="meta">{{ formattedTime || "时间未知" }}</span>
        <span v-if="detailText" class="dot">·</span>
        <span v-if="detailText" class="meta">{{ detailText }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";

const props = defineProps({
  item: {
    type: Object,
    required: true
  }
});

const router = useRouter();

const handleViewDetail = () => {
  const type = (props.item?.type || "").toLowerCase();
  const historyId = props.item?.id || props.item?.historyId || props.item?.history_id;
  const dialogueId = props.item?.dialogueId || props.item?.dialogue_id || historyId;

  if (type.includes("emotion")) {
    router.push({ name: "emotion", query: { historyId, title: props.item?.title } });
    return;
  }

  if (type.includes("dialogue") && dialogueId) {
    router.push({ name: "generate", query: { dialogueId, title: props.item?.title } });
    return;
  }

  console.log("查看详情:", props.item);
};

import { formatTime } from "@/utils/dateTime";

const formattedTime = computed(() => {
  const value = props.item?.createdAt || props.item?.created_at || props.item?.updated_at;
  if (!value) return "时间未知";
  return formatTime(value) || "时间未知";
});

const typeLabel = computed(() => props.item?.type || "记录");

const icon = computed(() => {
  const type = (props.item?.type || "").toLowerCase();
  if (type.includes("emotion") || type.includes("情绪") || type.includes("识别")) return "🎧";
  if (type.includes("dialogue") || type.includes("对话")) return "💬";
  if (type.includes("下载") || type.includes("download")) return "⬇️";
  return "📄";
});

const detailText = computed(() => props.item?.detail || props.item?.description || "");
</script>

<style scoped>
.history-row {
  background: #0d182b;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.history-row:hover {
  transform: scale(1.01) translateY(-2px);
  background: #111e36;
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 
    0 12px 24px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(59, 130, 246, 0.1);
  z-index: 1;
}

.row-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.title {
  font-weight: 800;
  font-size: 15px;
  color: #f8fafc;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #e5e7eb;
  padding: 6px 12px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  font-size: 12px;
  transition: all 0.15s ease;
}

.action-btn:hover {
  border-color: rgba(96, 165, 250, 0.7);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.2);
}

.action-icon {
  font-size: 14px;
}

.row-body {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: center;
}

.icon-box {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 16px;
  background: rgba(96, 165, 250, 0.16);
  color: #bfdbfe;
}

.meta-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  color: #cbd5e1;
  font-size: 13px;
}

.meta {
  color: #cbd5e1;
}

.dot {
  color: rgba(255, 255, 255, 0.4);
}

@media (max-width: 720px) {
  .row-header {
    align-items: flex-start;
  }
}
</style>
