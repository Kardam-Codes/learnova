/*
 * File: LoginPage.jsx
 * Owner: KARDAM
 * Purpose: Render the learner login page with local and Google sign-in options.
 * What it is: A route-level auth page that validates login input and redirects to My Courses on success.
 */
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { getDefaultRouteForRole, useAuth } from "../context/AuthContext";
import AuthLayout from "../components/AuthLayout";
import AuthCard from "../components/AuthCard";
import InputField from "../components/InputField";
import PasswordField from "../components/PasswordField";
import SelectField from "../components/SelectField";
import ErrorMessage from "../components/ErrorMessage";
import Modal from "../components/Modal";
import GoogleSignInButton from "../components/GoogleSignInButton";

const ROLE_OPTIONS = [
  { value: "learner", label: "Learner" },
  { value: "instructor", label: "Instructor" },
  { value: "admin", label: "Admin" },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loginWithGoogle, isAuthenticated, user, defaultRoute } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("learner");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const showForgotPassword = location.pathname === "/auth/forgot-password";

  if (isAuthenticated) {
    return <Navigate to={defaultRoute} replace />;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    const result = await login(email, password, role);
    setIsSubmitting(false);

    if (!result.ok) {
      setError(result.error);
      return;
    }

    setError("");
    navigate(getDefaultRouteForRole(role));
  };

  const handleGoogleSuccess = (profile) => {
    const result = loginWithGoogle(profile, role);

    if (!result.ok) {
      setError(result.error);
      return;
    }

    navigate(getDefaultRouteForRole(user?.role ?? role));
  };

  return (
    <AuthLayout>
      <AuthCard
        title="Login"
        footer={
          <div className="auth-link-stack">
            <Link className="auth-link" to="/auth/forgot-password">
              Forgot Password?
            </Link>
            <Link className="auth-link" to="/auth/signup">
              Sign Up
            </Link>
          </div>
        }
      >
        <form className="auth-form" onSubmit={handleSubmit}>
          <InputField
            id="login-email"
            label="Email"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="you@example.com"
          />
          <PasswordField
            id="login-password"
            label="Password"
            value={password}
            onChange={setPassword}
            placeholder="Enter your password"
          />
          <SelectField
            id="login-role"
            label="Role"
            value={role}
            onChange={setRole}
            options={ROLE_OPTIONS}
          />
          <ErrorMessage message={error} />
          <button type="submit" className="auth-primary-button" disabled={isSubmitting}>
            {isSubmitting ? "Signing In..." : "Sign In"}
          </button>
        </form>

        <div className="auth-divider">
          <span>OR</span>
        </div>

        <GoogleSignInButton onSuccess={handleGoogleSuccess} onError={setError} />
      </AuthCard>

      {showForgotPassword ? (
        <Modal title="Forgot Password" onClose={() => navigate("/auth/login")}>
          <div className="forgot-password-content">
            <InputField
              id="forgot-email"
              label="Email"
              type="email"
              value={forgotEmail}
              onChange={setForgotEmail}
              placeholder="Enter your registered email"
            />
            <p>
              Backend email reset wiring will be connected later.
            </p>
            <button type="button" className="auth-primary-button" onClick={() => navigate("/auth/login")}>
              Send Reset Link
            </button>
          </div>
        </Modal>
      ) : null}
    </AuthLayout>
  );
}
