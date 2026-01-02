<template>
  <div class="search-header">
    <div class="search-wrapper">
      <span class="icon">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="11" cy="11" r="6" />
          <path d="m20 20-3.5-3.5" />
        </svg>
      </span>
      <input
        :value="modelValue"
        :placeholder="placeholder"
        type="text"
        @input="onInput"
        @keyup.enter="onSearch"
      />
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, default: "" },
  placeholder: { type: String, default: "搜索歌曲 / 用户（回车或点击）" }
});
const emit = defineEmits(["update:modelValue", "search"]);

const onInput = event => emit("update:modelValue", event.target.value);
const onSearch = () => emit("search", (props.modelValue || "").trim());
</script>

<style scoped>
.search-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  padding: 6px 16px;
  min-height: 48px;
  max-height: 56px;
}

.search-wrapper {
  width: min(520px, 60vw);
  min-width: 280px;
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 8px;
  padding: 0 10px;
  height: 40px;
  line-height: 40px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: none;
}

.search-wrapper .icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.search-wrapper .icon svg {
  width: 18px;
  height: 18px;
  stroke: rgba(255, 255, 255, 0.65);
  fill: none;
  stroke-width: 1.8;
}

.search-wrapper input {
  background: transparent;
  border: none;
  outline: none;
  color: #e5e7eb;
  font-size: 14px;
  height: 100%;
  line-height: 40px;
  padding: 0;
}
</style>
