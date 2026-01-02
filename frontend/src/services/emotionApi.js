import { api } from "./api";

const normalizeAnalysisResponse = (resp) => {
  if (!resp) {
    throw new Error("后端未返回数据");
  }

  const extra = resp.extra && typeof resp.extra === "object" ? resp.extra : resp;
  const merged = { ...extra };

  if (resp.analysis_id !== undefined) merged.analysis_id = resp.analysis_id;
  if (resp.music_file_id !== undefined) merged.music_file_id = resp.music_file_id;
  if (resp.emotion !== undefined) merged.emotion = resp.emotion;
  if (resp.confidence !== undefined) merged.confidence = resp.confidence;
  if (resp.created_at !== undefined) merged.created_at = resp.created_at;
  if (resp.summary !== undefined) merged.summary = resp.summary;
  // 兼容后端可能返回的拼写错误字段
  if (merged.summary === undefined && resp.summry !== undefined) merged.summary = resp.summry;
  if (merged.summary === undefined && merged.summry !== undefined) merged.summary = merged.summry;
  merged.raw_response = resp;

  return merged;
};

export async function analyzeMusic(file) {
  if (!file) {
    throw new Error("请选择音频文件");
  }

  const formData = new FormData();
  formData.append("file", file);

  const res = await api.post("/api/emotion/analyze", formData);
  return normalizeAnalysisResponse(res);
}

export async function analyzeMusicTask(file) {
  if (!file) {
    throw new Error("请选择音频文件");
  }
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/api/emotion/analyze-task", formData);
}

export async function getEmotionTaskStatus(taskId) {
  if (!taskId) throw new Error("缺少任务 ID");
  return api.get(`/api/emotion/analyze-task/${taskId}`);
}



export async function fetchEmotionDetail(id) {
  if (!id) {
    throw new Error("缺少情绪分析记录 ID");
  }
  // 历史详情：后端用 /api/history/{id} 返回 EmotionDetailResponse
  return api.get(`/api/history/emotions/${id}`);
}

// 兼容旧命名
export const analyzeAudio = analyzeMusic;
