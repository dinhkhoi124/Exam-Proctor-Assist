import {
  useState,
  useEffect,
  type ReactNode,
} from "react";
import { api } from "@/lib/api";
import { AuthContext, type AuthUser } from "@/context/auth";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem("access_token");
    const storedUser = localStorage.getItem("auth_user");

    if (storedToken) {
      setToken(storedToken);
    }

    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }

    setIsLoading(false);
  }, []);

  const login = (token: string, user?: AuthUser) => {
    localStorage.setItem("access_token", token);
    setToken(token);

    if (user) {
      localStorage.setItem("auth_user", JSON.stringify(user));
      setUser(user);
    }
  };

  const logout = async () => {
    try {
      if (token) {
        await api.post("/api/v1/auth/logout");
      }
    } catch (error) {
      console.error("Failed to call backend logout", error);
    } finally {
      setToken(null);
      setUser(null);

      localStorage.removeItem("access_token");
      localStorage.removeItem("auth_user");
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
