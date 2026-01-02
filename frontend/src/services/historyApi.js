import { api } from "./api";

const buildQuery = params => {
  const search = new URLSearchParams(params || {}).toString();
  return search ? `?${search}` : "";
};

export const fetchHistory = async params => {
  try {
    return await api.get(`/api/history${buildQuery(params)}`);
  } catch (err) {
    if (err?.status === 404) return { items: [] };
    throw err;
  }
};
