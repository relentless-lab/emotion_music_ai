import { defineStore } from "pinia";
import { fetchHistory } from "@/services/historyApi";
import { useAuthStore } from "./auth";

export const useHistoryStore = defineStore("history", {
  state: () => ({
    // 用于隔离不同登录用户 / 游客的数据，避免切换账号后看到上一位用户的历史记录
    scopeKey: "guest", // "guest" | `user:${id}`
    items: [],
    loading: false,
    error: ""
  }),
  actions: {
    getCurrentScopeKey() {
      const auth = useAuthStore();
      // 退出登录后有些页面可能仍保留旧的 user 对象/缓存，
      // 这里必须以 token 为准：没 token 就是 guest，确保能清空残留数据。
      if (!auth.token) return "guest";
      const id = auth.user?.id;
      if (id) return `user:${id}`;
      const email = auth.user?.email;
      if (email) return `user:email:${email}`;
      const name = auth.user?.name || auth.user?.username;
      if (name) return `user:name:${name}`;
      return "user:loggedIn";
    },
    syncScope() {
      const auth = useAuthStore();
      // 未登录：无条件清空，避免数字残留（7/1 等）
      if (!auth.token) {
        this.scopeKey = "guest";
        this.items = [];
        this.loading = false;
        this.error = "";
        return;
      }

      const next = this.getCurrentScopeKey();
      if (this.scopeKey !== next) {
        this.scopeKey = next;
        this.items = [];
        this.loading = false;
        this.error = "";
      }
    },
    reset() {
      this.scopeKey = "guest";
      this.items = [];
      this.loading = false;
      this.error = "";
    },
    async loadHistory() {
      const auth = useAuthStore();
      this.syncScope();

      // 未登录：直接清空，确保标签数字为 0，且不显示报错
      if (!auth.token) {
        this.items = [];
        this.loading = false;
        this.error = "";
        return { items: [] };
      }

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
          return { items: [] };
        }
        // 401：通常是未登录或 token 失效，清空列表避免展示旧数据/残留计数
        if (err?.status === 401) {
          this.items = [];
          this.error = "";
          return { items: [] };
        }
        this.error = err?.message || "加载失败";
        throw err;
      } finally {
        this.loading = false;
      }
    }
  }
});
