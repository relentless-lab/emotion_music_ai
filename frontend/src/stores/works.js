import { defineStore } from "pinia";
import { fetchWorks, createWork, updateWork, deleteWork } from "@/services/workApi";
import { useAuthStore } from "./auth";

const API_BASE_URL = ((import.meta.env.VITE_API_BASE_URL || "").trim()
  || (import.meta.env.DEV ? "http://127.0.0.1:8000" : (typeof window !== "undefined" ? window.location.origin : "")))
  .replace(/\/+$/, "")
  .replace(/\/api$/, "");

const toAbsoluteUrl = url => {
  if (!url) return "";
  if (/^https?:\/\//i.test(url) || url.startsWith("blob:") || url.startsWith("data:")) return url;
  const base = (API_BASE_URL || (typeof window !== "undefined" ? window.location.origin : "")).replace(/\/$/, "");
  const normalized = url.startsWith("/") ? url : `/${url}`;
  return `${base}${normalized}`;
};

const normalizeWork = work => {
  if (!work) return work;
  const title = work.title || work.name || "未命名作品";
  const coverUrl = work.cover_url || work.cover || "";
  const normalizedCover = coverUrl ? toAbsoluteUrl(coverUrl) : "";
  const audioUrl = work.audio_url || work.url || "";
  const normalizedAudio = audioUrl ? toAbsoluteUrl(audioUrl) : "";
  return {
    ...work,
    title,
    name: title,
    cover_url: coverUrl,
    cover: normalizedCover || coverUrl,
    audio_url: audioUrl,
    url: normalizedAudio
  };
};

export const useWorksStore = defineStore("works", {
  state: () => ({
    // 用于隔离不同登录用户 / 游客的数据，避免切换账号后看到上一位用户的作品列表
    scopeKey: "guest", // "guest" | `user:${id}`
    list: [],
    loading: false,
    error: ""
  }),
  actions: {
    getCurrentScopeKey() {
      const auth = useAuthStore();
      const id = auth.user?.id;
      return id ? `user:${id}` : "guest";
    },
    syncScope() {
      const next = this.getCurrentScopeKey();
      if (this.scopeKey !== next) {
        this.scopeKey = next;
        this.list = [];
        this.loading = false;
        this.error = "";
      }
    },
    reset() {
      this.scopeKey = "guest";
      this.list = [];
      this.loading = false;
      this.error = "";
    },
    async loadWorks() {
      const auth = useAuthStore();
      this.syncScope();
      this.loading = true;
      this.error = "";
      try {
        // 未登录：不拉取作品，直接清空，避免残留上个用户的数据
        if (!auth.token) {
          this.list = [];
          this.error = "请先进行注册/登录";
          return [];
        }
        const data = await fetchWorks({ userId: auth.user?.id });
        this.list = Array.isArray(data) ? data.map(normalizeWork) : [];
      } catch (err) {
        // 401：通常是未登录或 token 失效，清空列表避免展示旧数据
        if (err?.status === 401) {
          this.list = [];
        }
        this.error = err?.message || "加载失败";
        throw err;
      } finally {
        this.loading = false;
      }
    },
    async addWork(payload) {
      this.syncScope();
      const item = await createWork(payload);
      if (item) {
        this.list.unshift(normalizeWork(item));
      }
    },
    async editWork(id, payload) {
      this.syncScope();
      const updated = await updateWork(id, payload);
      const normalized = normalizeWork(updated);
      this.list = this.list.map(w => (w.id === id ? normalized : w));
    },
    async removeWork(id) {
      this.syncScope();
      await deleteWork(id);
      this.list = this.list.filter(w => w.id !== id);
    }
  }
});
