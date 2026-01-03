// api.js：所有 API 请求的底层核心引擎
// 生产环境默认走同源（window.location.origin）配合 Nginx `/api` 反代，避免“前端域名/IP 与 API 域名不一致”导致的 CORS 问题。
// 如确需跨域（独立 API 域名），再通过 VITE_API_BASE_URL 显式指定。
const RAW_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").trim();
const FALLBACK_BASE_URL =
  import.meta.env.DEV
    ? "http://127.0.0.1:8000"
    : (typeof window !== "undefined" ? window.location.origin : "");

const BASE_URL = (RAW_BASE_URL || FALLBACK_BASE_URL)
  .replace(/\/+$/, "")
  // 防呆：有人会把 VITE_API_BASE_URL 配成 `http(s)://host/api`，而我们的 path 已经以 `/api/...` 开头
  .replace(/\/api$/, "");

function getToken() {
  return localStorage.getItem("auth_token");
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  // 如果 body 不是 FormData，则默认为 JSON 请求
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  // BASE_URL 为空时会变成相对路径请求（同源），例如 `/api/login`
  const res = await fetch(`${BASE_URL}${path}`, {
    headers,
    ...options
  });

  if (!res.ok) {
    const text = await res.text();
    let message = text;
    try {
      const data = JSON.parse(text || "{}");
      message = data.message || data.error || data.detail || message;
    } catch {
      // ignore JSON parse errors, fall back to raw text
    }
    if (!message) {
      message = `HTTP ${res.status}`;
    }
    const err = new Error(message || `HTTP ${res.status}`);
    err.status = res.status;
    throw err;
  }

  const text = await res.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch (e) {
    const err = new Error("解析响应失败");
    err.cause = e;
    throw err;
  }
}

export const api = {
  get: path => request(path),
  post: (path, body) => request(path, {
    method: "POST",
    body: body instanceof FormData ? body : JSON.stringify(body)
  }),
  put: (path, body) => request(path, {
    method: "PUT",
    body: body instanceof FormData ? body : JSON.stringify(body)
  }),
  delete: path => request(path, { method: "DELETE" })
};

