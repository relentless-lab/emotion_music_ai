import { defineStore } from "pinia";
import { fetchWorks, createWork, updateWork, deleteWork } from "@/services/workApi";
import { useAuthStore } from "./auth";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

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
    list: [],
    loading: false,
    error: ""
  }),
  actions: {
    async loadWorks() {
      const auth = useAuthStore();
      this.loading = true;
      this.error = "";
      try {
        const data = await fetchWorks({ userId: auth.user?.id });
        this.list = Array.isArray(data) ? data.map(normalizeWork) : [];
      } catch (err) {
        this.error = err?.message || "加载失败";
        throw err;
      } finally {
        this.loading = false;
      }
    },
    async addWork(payload) {
      const item = await createWork(payload);
      if (item) {
        this.list.unshift(normalizeWork(item));
      }
    },
    async editWork(id, payload) {
      const updated = await updateWork(id, payload);
      const normalized = normalizeWork(updated);
      this.list = this.list.map(w => (w.id === id ? normalized : w));
    },
    async removeWork(id) {
      await deleteWork(id);
      this.list = this.list.filter(w => w.id !== id);
    }
  }
});
