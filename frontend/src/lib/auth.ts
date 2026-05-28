import { api, setAuthTokens, clearAuthTokens } from "./api";
import type { AuthTokens, User } from "@/types";

export async function login(email: string, password: string): Promise<User> {
  const res = await api.post<AuthTokens>("/auth/login", { email, password });
  setAuthTokens(res.data.access_token, res.data.refresh_token);
  const me = await api.get<User>("/auth/me");
  return me.data;
}

export async function logout(): Promise<void> {
  try {
    await api.post("/auth/logout");
  } finally {
    clearAuthTokens();
  }
}

export async function getMe(): Promise<User> {
  const res = await api.get<User>("/auth/me");
  return res.data;
}

export function isAuthenticated(): boolean {
  return typeof window !== "undefined" && !!localStorage.getItem("radsight_access_token");
}
