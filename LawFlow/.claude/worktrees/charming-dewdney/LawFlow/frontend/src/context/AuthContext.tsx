import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  changePassword,
  getMe,
  login as loginRequest,
  refresh as refreshRequest,
  register as registerRequest,
  updateProfile as updateProfileRequest,
} from "@/api/auth";
import {
  clearAuthSession,
  getAccessToken,
  getRefreshToken,
  getStoredUser,
  saveAuthSession,
  type AuthUser,
} from "@/lib/authStorage";

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isPro: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
  refreshSession: () => Promise<boolean>;
  updateProfile: (payload: { display_name?: string; avatar_url?: string }) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => getStoredUser());
  const [isLoading, setIsLoading] = useState(true);

  const refreshSession = useCallback(async (): Promise<boolean> => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;
    try {
      const data = await refreshRequest(refreshToken);
      saveAuthSession({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user: data.user,
      });
      setUser(data.user);
      return true;
    } catch {
      clearAuthSession();
      setUser(null);
      return false;
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    async function bootstrapAuth() {
      const accessToken = getAccessToken();
      if (!accessToken) {
        if (mounted) setIsLoading(false);
        return;
      }

      try {
        const me = await getMe();
        if (mounted) setUser(me);
      } catch {
        await refreshSession();
      } finally {
        if (mounted) setIsLoading(false);
      }
    }
    void bootstrapAuth();
    return () => {
      mounted = false;
    };
  }, [refreshSession]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await loginRequest({ email, password });
    saveAuthSession({
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: data.user,
    });
    setUser(data.user);
  }, []);

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      const data = await registerRequest({
        email,
        password,
        display_name: displayName,
      });
      saveAuthSession({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user: data.user,
      });
      setUser(data.user);
    },
    []
  );

  const logout = useCallback(() => {
    clearAuthSession();
    setUser(null);
  }, []);

  const updateProfile = useCallback(async (payload: { display_name?: string; avatar_url?: string }) => {
    const updated = await updateProfileRequest(payload);
    const refreshToken = getRefreshToken();
    const accessToken = getAccessToken();
    if (refreshToken && accessToken) {
      saveAuthSession({
        accessToken,
        refreshToken,
        user: updated,
      });
    }
    setUser(updated);
  }, []);

  const updatePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    await changePassword({
      current_password: currentPassword,
      new_password: newPassword,
    });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isPro: (user?.tier ?? "free") === "pro",
      isLoading,
      login,
      register,
      logout,
      refreshSession,
      updateProfile,
      changePassword: updatePassword,
    }),
    [user, isLoading, login, register, logout, refreshSession, updateProfile, updatePassword]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
