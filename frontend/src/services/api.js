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

function prettifyFieldName(field) {
  const map = {
    username: "用户名",
    password: "密码",
    email: "邮箱",
    code: "验证码"
  };
  return map[field] || field || "";
}

function prettifyPydanticMsg(msg) {
  // 这里只处理“字符串”消息；对象/数组由上层格式化函数处理，避免出现 [object Object]
  if (msg == null) return "";
  if (typeof msg !== "string") {
    // 允许 number/bool 兜底成字符串；对象/数组返回空，让上层走结构化格式化
    if (typeof msg === "number" || typeof msg === "boolean") return String(msg);
    return "";
  }
  const m = msg;
  // 常见 pydantic/fastapi 英文校验提示，尽量转成更自然的中文
  // e.g. "String should have at least 6 characters"
  const atLeast = m.match(/should have at least (\d+) characters?/i);
  if (atLeast) return `至少 ${atLeast[1]} 位`;
  const atMost = m.match(/should have at most (\d+) characters?/i);
  if (atMost) return `最多 ${atMost[1]} 位`;
  if (/field required/i.test(m)) return "必填";
  if (/value is not a valid email address/i.test(m)) return "邮箱格式不正确";
  return m;
}

function formatFastApiDetail(detail) {
  if (!detail) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map(item => {
        if (!item) return "";
        if (typeof item === "string") return item;
        // 兼容 pydantic v2 的校验项：{ loc, msg, type, ... }
        const loc = Array.isArray(item.loc) ? item.loc : [];
        const field = loc.length ? loc[loc.length - 1] : "";
        const prettyField = prettifyFieldName(field);

        const msgRaw = item.msg ?? item.message ?? item.detail;
        const prettyMsg =
          prettifyPydanticMsg(msgRaw)
          || formatFastApiDetail(msgRaw) // msgRaw 可能是对象/数组
          || "";
        return prettyField ? `${prettyField}${prettyMsg ? `：${prettyMsg}` : ""}` : (prettyMsg || "");
      })
      .filter(Boolean);
    // 去重 + 合并
    return Array.from(new Set(parts)).join("；");
  }
  if (typeof detail === "object") {
    // 兼容 detail 为单个 pydantic 错误项（对象而非数组）
    if (detail.loc && (detail.msg || detail.message || detail.detail)) {
      const loc = Array.isArray(detail.loc) ? detail.loc : [];
      const field = loc.length ? loc[loc.length - 1] : "";
      const prettyField = prettifyFieldName(field);
      const msgRaw = detail.msg ?? detail.message ?? detail.detail;
      const prettyMsg =
        prettifyPydanticMsg(msgRaw)
        || formatFastApiDetail(msgRaw)
        || "";
      return prettyField ? `${prettyField}${prettyMsg ? `：${prettyMsg}` : ""}` : (prettyMsg || "");
    }

    // 兼容 detail 为 dict：{ password: "...", email: "..."} 或更深层嵌套
    const entries = Object.entries(detail);
    if (entries.length) {
      const parts = entries
        .map(([k, v]) => {
          const prettyField = prettifyFieldName(k);
          const msg = formatFastApiDetail(v) || prettifyPydanticMsg(v) || (v == null ? "" : String(v));
          return prettyField ? `${prettyField}${msg ? `：${msg}` : ""}` : msg;
        })
        .filter(Boolean);
      if (parts.length) return Array.from(new Set(parts)).join("；");
    }

    // 兜底：尝试提取常见字段
    const msg = detail.msg ?? detail.message ?? detail.detail;
    return formatFastApiDetail(msg) || prettifyPydanticMsg(msg) || JSON.stringify(detail);
  }
  return (detail || "").toString();
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
      // FastAPI 常见：{detail: ...}；也兼容 {message: ...}/{error: ...} 且它们可能是对象/数组
      message =
        formatFastApiDetail(data.detail)
        || formatFastApiDetail(data.message)
        || formatFastApiDetail(data.error)
        || message;
    } catch {
      // ignore JSON parse errors, fall back to raw text
    }
    // 统一 401 未登录提示文案，提升用户体验
    if (res.status === 401) {
      const m = (message || "").toString();
      if (m.includes("缺少访问令牌") || m.includes("Not authenticated")) {
        message = "请先进行注册/登录";
      }
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

