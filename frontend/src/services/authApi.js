import { api } from "./api";


export function login(payload) {
  return api.post("/api/login", payload);
}



export function register(payload) {
  return api.post("/api/register", payload);
}

export function sendVerificationCode(email) {
  return api.post("/api/send-verification-code", { email });
}



export function fetchProfile() {
  return api.get("/api/profile");
}

export function updateProfile(payload) {
  return api.put("/api/profile", payload);
}

export function uploadAvatar(file) {
  const form = new FormData();
  form.append("file", file);
  return api.post("/api/upload-avatar", form);
}

export function deleteAccount() {
  return api.delete("/api/account");
}
