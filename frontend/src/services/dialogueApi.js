import { api } from "./api";

export const chatWithDialogue = payload => api.post("/api/dialogues/chat", payload);

export const chatWithDialogueAsync = payload => api.post("/api/dialogues/chat-task", payload);

export const getMusicTaskStatus = taskId => api.get(`/api/music/generate/${taskId}`);

export const generateCoverForDialogue = payload => api.post("/api/dialogues/generate-cover", payload);

export const generateCoverOnly = payload => api.post("/api/music/generate-cover", payload);

export const getDialogueDetail = id => api.get(`/api/history/dialogues/${id}`);

// 音乐仿写（with prompt audio）：上传参考音频，返回 task_id，前端复用现有轮询接口即可
export const imitateMusicAsync = ({ file, prompt = "", duration_seconds = 60, instrumental = true, lyrics = null, style = null } = {}) => {
  const form = new FormData();
  form.append("file", file);
  form.append("prompt", prompt || "");
  form.append("duration_seconds", String(duration_seconds ?? 60));
  form.append("instrumental", instrumental ? "true" : "false");
  if (lyrics) form.append("lyrics", String(lyrics));
  if (style) form.append("style", String(style));
  return api.post("/api/music/imitate-task", form);
};
