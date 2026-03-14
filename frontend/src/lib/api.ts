// import axios from "axios";

// export const api = axios.create({
//   baseURL: "http://127.0.0.1:8000", // backend fastapi
// });

// // Tự động gắn token vào header
// api.interceptors.request.use((config) => {
//   const token = localStorage.getItem("access_token");

//   if (token) {
//     config.headers.Authorization = `Bearer ${token}`;
//   }

//   return config;
// });

import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000", // URL của backend
});

// Thêm token vào header Authorization
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token"); // Lấy token từ localStorage
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export { api };
