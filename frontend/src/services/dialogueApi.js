import { api } from "./api";

export const chatWithDialogue = payload => api.post("/api/dialogues/chat", payload);

export const chatWithDialogueAsync = payload => api.post("/api/dialogues/chat-task", payload);

export const getMusicTaskStatus = taskId => api.get(`/api/music/generate/${taskId}`);

export const generateCoverForDialogue = payload => api.post("/api/dialogues/generate-cover", payload);

export const generateCoverOnly = payload => api.post("/api/music/generate-cover", payload);

export const getDialogueDetail = id => api.get(`/api/history/dialogues/${id}`);
