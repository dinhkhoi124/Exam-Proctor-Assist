import axios from "axios";

export const api = axios.create({
  baseURL: "http://127.0.0.1:8000", // backend fastapi
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
      // Clear expired token
      localStorage.removeItem("access_token");
      
      // Chuyển hướng về trang đăng nhập nếu chưa ở đó
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
