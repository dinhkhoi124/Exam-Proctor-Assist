import axios from "axios";

export const AUTH_NOTICE_STORAGE_KEY = "auth_notice";

export function getAuthenticationNotice(data: unknown): string | null {
  if (typeof data !== "object" || data === null || !("detail" in data)) return null;
  const detail = data.detail;
  if (typeof detail !== "object" || detail === null) return null;
  if (
    "code" in detail && detail.code === "SESSION_REPLACED" &&
    "message" in detail && typeof detail.message === "string"
  ) {
    return detail.message;
  }
  return null;
}

const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();

export const API_BASE_URL = (
  configuredApiUrl || window.location.origin
).replace(/\/+$/, "");

export function buildApiUrl(path: string) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export function getAdminWebSocketUrl() {
  const url = new URL(API_BASE_URL, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws/admin";
  url.search = "";
  url.hash = "";
  return url.toString();
}

export const api = axios.create({
  baseURL: API_BASE_URL,
});

// Tự động gắn token vào header
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// Tự động xử lý khi token hết hạn (401)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      const notice = getAuthenticationNotice(error.response.data);
      if (notice) sessionStorage.setItem(AUTH_NOTICE_STORAGE_KEY, notice);

      // Clear all locally cached authentication state.
      localStorage.removeItem("access_token");
      localStorage.removeItem("auth_user");
      
      // Chuyển hướng về trang đăng nhập nếu chưa ở đó
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
