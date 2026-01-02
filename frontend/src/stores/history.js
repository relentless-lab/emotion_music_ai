import { defineStore } from "pinia";
import { fetchHistory } from "@/services/historyApi";

export const useHistoryStore = defineStore("history", {
  state: () => ({
    items: [],
    loading: false,
    error: ""
  }),
  actions: {
    async loadHistory() {
      this.loading = true;
      this.error = "";
      try {
        const payload = await fetchHistory();
        const items = Array.isArray(payload?.items)
          ? payload.items
          : Array.isArray(payload)
          ? payload
          : [];
        this.items = items;
      } catch (err) {
        // 后端 404 表示暂无记录时，视为空列表而不是报错
        if (err?.status === 404) {
          this.items = [];
          this.error = "";
          return;
        }
        this.error = err?.message || "加载失败";
        throw err;
      } finally {
        this.loading = false;
      }
    }
  }
});
