import { api } from "./api";

const buildQuery = params => {
  const search = new URLSearchParams(params || {}).toString();
  return search ? `?${search}` : "";
};

export const searchAll = params => api.get(`/api/search${buildQuery(params)}`);

export const fetchPublicWork = id => api.get(`/api/works/public/${id}`);
export const fetchPublicWorksByUser = (userId, params) =>
  api.get(`/api/works/public/by-user/${userId}${buildQuery(params)}`);

export const likeWork = id => api.post(`/api/social/works/${id}/like`, {});
export const unlikeWork = id => api.delete(`/api/social/works/${id}/like`);

export const followUser = id => api.post(`/api/social/users/${id}/follow`, {});
export const unfollowUser = id => api.delete(`/api/social/users/${id}/follow`);

export const fetchPublicUser = id => api.get(`/api/social/users/${id}`);
export const fetchFollowers = id => api.get(`/api/social/users/${id}/followers`);
export const fetchFollowing = id => api.get(`/api/social/users/${id}/following`);
export const fetchLikedWorks = () => api.get("/api/social/likes/works");
