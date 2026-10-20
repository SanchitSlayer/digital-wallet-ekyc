import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { fetchCurrentUser, login as loginRequest, type LoginRequest, type UserResponse } from "../../api/auth";
import { setUnauthorizedHandler } from "../../api/client";
import { clearToken, getToken, saveToken } from "./session";

interface AuthState {
  user: UserResponse | null;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<UserResponse>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(getToken() !== null);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (getToken() === null) {
      return;
    }
    // A token survives a page refresh in sessionStorage, so the user behind it is reloaded instead of logging out.
    fetchCurrentUser()
      .then(setUser)
      .catch(logout)
      .finally(() => setIsLoading(false));
  }, [logout]);

  const login = useCallback(async (credentials: LoginRequest) => {
    const token = await loginRequest(credentials);
    saveToken(token.access_token);
    const currentUser = await fetchCurrentUser();
    setUser(currentUser);
    return currentUser;
  }, []);

  const value = useMemo(() => ({ user, isLoading, login, logout }), [user, isLoading, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
