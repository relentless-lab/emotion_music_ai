const getApiBase = () => {
  const envBase = (import.meta.env.VITE_API_BASE_URL || "").trim();
  if (envBase) return envBase;
  
  // 兜底逻辑：开发环境 8000，生产环境同源
  if (import.meta.env.DEV) {
    return "http://127.0.0.1:8000";
  }
  return window.location.origin;
};

const API_BASE = getApiBase();

/**
 * 将后端返回的相对路径或 OSS 路径转为前端可用的绝对 URL。
 * 统一处理 API_BASE_URL 可能包含 /api 后缀的情况。
 */
export const toAbsoluteUrl = (url) => {
  if (!url) return "";
  if (
    url.startsWith("http://") || 
    url.startsWith("https://") || 
    url.startsWith("data:") || 
    url.startsWith("blob:")
  ) {
    return url;
  }

  // 必须移除 /api 后缀，因为 /static 和 /media 是挂载在后端根路径下的
  const fileBase = API_BASE.replace(/\/+$/, "").replace(/\/api$/, "");
  
  if (url.startsWith("/")) {
    return `${fileBase}${url}`;
  }
  return `${fileBase}/${url}`;
};
