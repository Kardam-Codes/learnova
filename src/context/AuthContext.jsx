/*
 * File: AuthContext.jsx
 * Owner: KARDAM
 * Purpose: Hold frontend authentication state and auth actions for learner-side flows.
 * What it is: A backend-connected auth context that persists the active session in localStorage.
 */
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { loginRequest, meRequest, registerRequest } from "../utils/apiClient";

const AuthContext = createContext(null);

const AUTH_SESSION_KEY = "learnova-auth-session";
const ALLOWED_ROLES = ["learner", "instructor", "admin"];

export function normalizeUserRole(role) {
  return role === "super_admin" ? "admin" : role;
}

export function getDefaultRouteForRole(role) {
  if (!role) {
    return "/auth/login";
  }

  return normalizeUserRole(role) === "learner" ? "/my-courses" : "/instructor/courses";
}

function readStorage(key, fallback) {
  try {
    const value = window.localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

function writeStorage(key, value) {
  window.localStorage.setItem(key, JSON.stringify(value));
}

function normalizeSelectedRole(role) {
  return ALLOWED_ROLES.includes(role) ? role : "learner";
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => readStorage(AUTH_SESSION_KEY, null));
  const [isAuthReady, setIsAuthReady] = useState(false);

  const persistSession = (nextSession) => {
    setSession(nextSession);

    if (nextSession) {
      writeStorage(AUTH_SESSION_KEY, nextSession);
      return;
    }

    window.localStorage.removeItem(AUTH_SESSION_KEY);
  };

  useEffect(() => {
    const bootstrapSession = async () => {
      if (!session?.token) {
        setIsAuthReady(true);
        return;
      }

      try {
        const user = await meRequest(session.token);
        persistSession({
          user,
          token: session.token,
          isAuthenticated: true,
        });
      } catch {
        persistSession(null);
      } finally {
        setIsAuthReady(true);
      }
    };

    bootstrapSession();
    // This validation only needs to happen once on provider startup.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (email, password, selectedRole) => {
    const trimmedEmail = email.trim().toLowerCase();
    const trimmedPassword = password.trim();
    const normalizedRole = normalizeSelectedRole(selectedRole);

    if (!trimmedEmail || !trimmedPassword) {
      return { ok: false, error: "Email and password are required." };
    }

    try {
      const response = await loginRequest({
        email: trimmedEmail,
        password: trimmedPassword,
        role: normalizedRole,
      });

      persistSession({
        user: response.user,
        token: response.access_token,
        isAuthenticated: true,
      });

      return { ok: true };
    } catch (error) {
      return { ok: false, error: error.message };
    }
  };

  const signup = async ({ name, email, password, confirmPassword, role }) => {
    const trimmedName = name.trim();
    const trimmedEmail = email.trim().toLowerCase();
    const normalizedRole = normalizeSelectedRole(role);

    if (!trimmedName) {
      return { ok: false, error: "Name is required." };
    }

    if (password !== confirmPassword) {
      return { ok: false, error: "Passwords do not match." };
    }

    try {
      await registerRequest({
        name: trimmedName,
        email: trimmedEmail,
        password,
        role: normalizedRole,
      });
      return { ok: true };
    } catch (error) {
      return { ok: false, error: error.message };
    }
  };

  const loginWithGoogle = (profile, selectedRole) => {
    const normalizedRole = normalizeSelectedRole(selectedRole);

    // Google auth is still frontend-only until the backend verification flow is added.
    persistSession({
      user: {
        id: `google-${Date.now()}`,
        name: profile.name,
        email: profile.email,
        role: normalizedRole,
        provider: "google",
        is_active: true,
      },
      token: btoa(`${profile.email}:${Date.now()}`),
      isAuthenticated: true,
    });

    return { ok: true };
  };

  const logout = () => {
    persistSession(null);
  };

  const value = useMemo(() => {
    const normalizedRole = normalizeUserRole(session?.user?.role);

    return {
      user: session?.user ?? null,
      userRole: normalizedRole ?? null,
      defaultRoute: getDefaultRouteForRole(normalizedRole),
      token: session?.token ?? "",
      isAuthenticated: Boolean(session?.isAuthenticated),
      isAuthReady,
      login,
      signup,
      loginWithGoogle,
      logout,
    };
  }, [isAuthReady, session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }

  return context;
}
