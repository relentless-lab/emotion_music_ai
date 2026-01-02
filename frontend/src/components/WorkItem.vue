<template>
  <div class="work-row">
    <div class="work-left">
      <div class="thumb">
        <img 
          v-if="coverUrl" 
          :src="coverUrl" 
          :alt="item.name || '作品封面'"
          class="cover-image"
        />
        <span v-else class="cover-icon">{{ displayIcon }}</span>
      </div>
      <div class="text">
        <div class="name">{{ item.name }}</div>
        <div class="meta-line">{{ metaLine }}</div>
      </div>
    </div>
    <div class="work-actions">
      <button class="action-btn action-primary" type="button" @click="$emit('publish', item)">
        <svg class="action-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
        </svg>
        <span>发布</span>
      </button>
      <button class="action-btn action-text" type="button" @click="$emit('edit', item)">
        <span>修改名称</span>
      </button>
      <button class="action-btn action-icon" type="button" title="播放" @click="$emit('play', item)">
        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
          <path d="M8 5v14l11-7z"/>
        </svg>
      </button>
      <button class="action-btn action-icon" type="button" title="下载" @click="$emit('download', item)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
      </button>
      <button
        class="action-btn action-icon action-danger"
        type="button"
        title="删除"
        :disabled="disableDelete"
        @click="$emit('delete', item)"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  item: {
    type: Object,
    required: true
  },
  disableDelete: {
    type: Boolean,
    default: false
  }
});

defineEmits(["delete", "play", "publish", "edit", "download"]);

const displayIcon = computed(() => props.item?.icon || "🎵");

const toAbsoluteUrl = (url) => {
  if (!url) return "";
  if (url.startsWith("http") || url.startsWith("blob:") || url.startsWith("data:")) return url;
  const base = import.meta.env.VITE_API_BASE_URL || window.location.origin;
  return url.startsWith("/") ? `${base.replace(/\/api$/, "")}${url}` : `${base.replace(/\/api$/, "")}/${url}`;
};

const coverUrl = computed(() => {
  const cover = props.item?.cover_url || props.item?.cover;
  return cover ? toAbsoluteUrl(cover) : null;
});

import { formatTime } from "@/utils/dateTime";

const metaLine = computed(() => {
  const parts = [];
  
  // 优先显示用户生成音乐时的需求 (mood)，如果没有则尝试显示描述 (description)
  // 如果都没有，则显示默认的来源说明
  let sourceText = props.item?.mood;
  if (!sourceText || sourceText === '无' || sourceText === '生成的音乐') {
    sourceText = props.item?.description;
  }
  
  const finalSource = sourceText && sourceText !== '无' 
    ? sourceText 
    : (props.item?.source || (props.item?.type?.includes("上传") ? "上传的音乐" : "生成的音乐"));
    
  if (finalSource) parts.push(finalSource);
  
  const time = formatTime(props.item?.createdAt);
  if (time) parts.push(time);
  
  const meta = (() => {
    const value = props.item;
    if (typeof value.meta === "string" && value.meta.trim()) {
      return value.meta.replace(/[,，|\\/]+/g, " · ").replace(/\s+/g, " ").trim();
    }
    if (Array.isArray(value.tags) && value.tags.length) {
      return value.tags.join(" · ");
    }
    return "";
  })();
  if (meta) parts.push(meta);
  return parts.join(" · ");
});
</script>

<style scoped>
.work-row {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  background: #0d182b;
  border: 1px solid rgba(255, 255, 255, 0.06);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.work-row:hover {
  transform: scale(1.01) translateY(-2px);
  background: #111e36;
  border-color: rgba(59, 130, 246, 0.3);
  box-shadow: 
    0 12px 24px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(59, 130, 246, 0.1);
  z-index: 1;
}

.work-left {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: center;
  min-width: 0;
}

.thumb {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.14);
  display: grid;
  place-items: center;
  font-size: 20px;
  color: #bfdbfe;
  overflow: hidden;
  flex-shrink: 0;
  position: relative;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  display: block;
}

.cover-icon {
  font-size: 20px;
  display: block;
}

.text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.name {
  font-weight: 800;
  font-size: 15px;
  color: #f4f7ff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta-line {
  color: #cbd5e1;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.work-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.action-btn {
  height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  backdrop-filter: blur(8px);
  position: relative;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(80, 160, 255, 0.4);
  box-shadow: 0 0 12px rgba(80, 160, 255, 0.25);
  transform: translateY(-1px);
}

.action-btn:active {
  transform: scale(0.98) translateY(0);
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
}

.action-btn:disabled:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
  box-shadow: none;
  transform: none;
}

/* 主操作按钮（发布） */
.action-primary {
  border-color: rgba(59, 130, 246, 0.3);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.1));
  color: #93c5fd;
}

.action-primary:hover {
  border-color: rgba(59, 130, 246, 0.5);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.25), rgba(139, 92, 246, 0.15));
  box-shadow: 0 0 16px rgba(59, 130, 246, 0.3);
}

/* 文字按钮（修改名称） */
.action-text {
  padding: 0 14px;
  border-style: dashed;
  border-color: rgba(255, 255, 255, 0.12);
}

/* 图标按钮（播放、下载、删除） */
.action-icon {
  width: 36px;
  padding: 0;
  min-width: 36px;
}

.action-icon .action-icon {
  width: 16px;
  height: 16px;
}

/* 危险操作（删除） */
.action-danger:hover {
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.1);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.25);
  color: #fca5a5;
}

@media (max-width: 960px) {
  .work-row {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .work-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
