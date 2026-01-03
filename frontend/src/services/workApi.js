import { api } from "./api";

const buildQuery = params => {
  const search = new URLSearchParams(params || {}).toString();
  return search ? `?${search}` : "";
};

export const fetchWorks = async params => {
  try {
    return await api.get(`/api/works${buildQuery(params)}`);
  } catch (err) {
    if (err?.status === 404) return [];
    throw err;
  }
};

// 仅需传 music_file_id，其他字段可选
export const createWork = payload => api.post("/api/works/quick-save", payload);

export const updateWork = (id, payload) => api.put(`/api/works/${id}`, payload);

export const deleteWork = id => api.delete(`/api/works/${id}`);

export const uploadWorkCover = file => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/api/works/upload-cover", form);
};

// 播放埋点：匿名可用，用于热门榜单（近N天播放量）
export const recordWorkPlay = (id, payload = {}) => api.post(`/api/works/${id}/play`, payload);
