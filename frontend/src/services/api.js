//api.js：所有 API 请求的底层核心引擎
// Dev 默认指向本机后端，避免因未配置 VITE_API_BASE_URL 导致整个前端不可用
const BASE_URL = ((import.meta.env.VITE_API_BASE_URL || "").trim()
  || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")).replace(/\/+$/, "");

function getToken() {
  return localStorage.getItem("auth_token");
}

async function request(path, options = {}) {
  if (!BASE_URL) {
    throw new Error("后端地址未配置");
  }
  const token = getToken();
  const headers = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  // 如果 body 不是 FormData，则默认为 JSON 请求
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

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

