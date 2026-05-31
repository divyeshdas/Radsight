import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("radsight_access_token") : null;
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const status = error.response?.status;
    if (status === 401 || status === 403) {
      const refresh = typeof window !== "undefined" ? localStorage.getItem("radsight_refresh_token") : null;
      if (refresh && !error.config?.url?.includes("/auth/refresh")) {
        try {
          const res = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, { refresh_token: refresh });
          const { access_token, refresh_token } = res.data;
          localStorage.setItem("radsight_access_token", access_token);
          localStorage.setItem("radsight_refresh_token", refresh_token);
          if (error.config && error.config.headers) {
            error.config.headers.Authorization = `Bearer ${access_token}`;
          }
          return axios(error.config!);
        } catch {
          localStorage.removeItem("radsight_access_token");
          localStorage.removeItem("radsight_refresh_token");
          window.location.href = "/login";
        }
      } else if (!refresh) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export function setAuthTokens(access: string, refresh: string) {
  localStorage.setItem("radsight_access_token", access);
  localStorage.setItem("radsight_refresh_token", refresh);
}

export function clearAuthTokens() {
  localStorage.removeItem("radsight_access_token");
  localStorage.removeItem("radsight_refresh_token");
}
