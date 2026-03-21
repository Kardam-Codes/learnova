/*
 * File: AuthContext.jsx
 * Owner: KARDAM
 * Purpose: Hold frontend authentication state and auth actions for learner-side flows.
 * What it is: A localStorage-backed auth context used until backend auth APIs are connected.
 */
import { createContext, useContext, useMemo, useState } from "react";

const AuthContext = createContext(null);

const AUTH_USERS_KEY = "learnova-auth-users";
const AUTH_SESSION_KEY = "learnova-auth-session";
const ALLOWED_ROLES = ["learner", "instructor", "admin"];

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

function validatePassword(password) {
  if (password.length < 8) {
    return "Password must be at least 8 characters.";
  }

  if (!/[A-Z]/.test(password)) {
    return "Password must contain at least one uppercase letter.";
  }

  if (!/[a-z]/.test(password)) {
    return "Password must contain at least one lowercase letter.";
  }

  if (!/[^A-Za-z0-9]/.test(password)) {
    return "Password must contain at least one special character.";
  }

  return "";
}

function createToken(email) {
  return btoa(`${email}:${Date.now()}`);
}

function normalizeSelectedRole(role) {
  return ALLOWED_ROLES.includes(role) ? role : "learner";
}

function normalizeStoredRole(role) {
  return role === "super_admin" ? "admin" : normalizeSelectedRole(role);
}

function upsertGoogleUser(users, profile, selectedRole) {
  const existingUser = users.find(
    (user) => user.email.toLowerCase() === profile.email.toLowerCase(),
  );

  if (existingUser) {
    if (normalizeStoredRole(existingUser.role) !== normalizeSelectedRole(selectedRole)) {
      return {
        users,
        user: null,
        error: `This Google account is registered as ${normalizeStoredRole(existingUser.role)}.`,
      };
    }

    return { users, user: existingUser, error: "" };
  }

  const requestedRole = normalizeSelectedRole(selectedRole);
  const role = users.length === 0 && requestedRole === "admin" ? "super_admin" : requestedRole;
  const newUser = {
    id: `user-${Date.now()}`,
    name: profile.name,
    email: profile.email,
    password: "",
    role,
    createdAt: new Date().toISOString(),
    provider: "google",
  };

  return {
    users: [...users, newUser],
    user: newUser,
    error: "",
  };
}

export function AuthProvider({ children }) {
  const [users, setUsers] = useState(() => readStorage(AUTH_USERS_KEY, []));
  const [session, setSession] = useState(() => readStorage(AUTH_SESSION_KEY, null));

  const persistUsers = (nextUsers) => {
    setUsers(nextUsers);
    writeStorage(AUTH_USERS_KEY, nextUsers);
  };

  const persistSession = (nextSession) => {
    setSession(nextSession);
    writeStorage(AUTH_SESSION_KEY, nextSession);
  };

  const login = (email, password, selectedRole) => {
    const trimmedEmail = email.trim().toLowerCase();
    const trimmedPassword = password.trim();
    const normalizedRole = normalizeSelectedRole(selectedRole);

    if (!trimmedEmail || !trimmedPassword) {
      return { ok: false, error: "Email and password are required." };
    }

    const matchedUser = users.find(
      (user) =>
        user.email.toLowerCase() === trimmedEmail &&
        user.password === trimmedPassword,
    );

    if (!matchedUser) {
      return { ok: false, error: "Invalid Email or Password" };
    }

    if (normalizeStoredRole(matchedUser.role) !== normalizedRole) {
      return { ok: false, error: "Selected role does not match this account." };
    }

    const nextSession = {
      user: matchedUser,
      token: createToken(matchedUser.email),
      isAuthenticated: true,
    };

    persistSession(nextSession);
    return { ok: true };
  };

  const signup = ({ name, email, password, confirmPassword, role }) => {
    const trimmedName = name.trim();
    const trimmedEmail = email.trim().toLowerCase();
    const normalizedRole = normalizeSelectedRole(role);

    if (!trimmedName) {
      return { ok: false, error: "Name is required." };
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      return { ok: false, error: "Enter a valid email address." };
    }

    if (users.some((user) => user.email.toLowerCase() === trimmedEmail)) {
      return { ok: false, error: "Email already exists." };
    }

    const passwordError = validatePassword(password);
    if (passwordError) {
      return { ok: false, error: passwordError };
    }

    if (password !== confirmPassword) {
      return { ok: false, error: "Passwords do not match." };
    }

    const newUser = {
      id: `user-${Date.now()}`,
      name: trimmedName,
      email: trimmedEmail,
      password,
      role: users.length === 0 && normalizedRole === "admin" ? "super_admin" : normalizedRole,
      createdAt: new Date().toISOString(),
      provider: "local",
    };

    persistUsers([...users, newUser]);
    return { ok: true };
  };

  const loginWithGoogle = (profile, selectedRole) => {
    const { users: nextUsers, user, error } = upsertGoogleUser(
      users,
      profile,
      selectedRole,
    );

    if (error) {
      return { ok: false, error };
    }

    persistUsers(nextUsers);

    const nextSession = {
      user,
      token: createToken(user.email),
      isAuthenticated: true,
    };

    persistSession(nextSession);
    return { ok: true };
  };

  const logout = () => {
    persistSession(null);
  };

  const value = useMemo(() => {
    return {
      user: session?.user ?? null,
      token: session?.token ?? "",
      isAuthenticated: Boolean(session?.isAuthenticated),
      users,
      login,
      signup,
      loginWithGoogle,
      logout,
    };
  }, [session, users]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }

  return context;
}
