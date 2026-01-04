import { api } from "./api";

const buildQuery = params => {
  const search = new URLSearchParams(params || {}).toString();
  return search ? `?${search}` : "";
};

export const fetchHotSongs = (params = {}) => api.get(`/api/ui/hot-songs${buildQuery(params)}`);

export const fetchRecommendedCreators = (params = {}) =>
  api.get(`/api/ui/recommended-creators${buildQuery(params)}`);
