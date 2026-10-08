/*
 * File: SignupPage.jsx
 * Owner: KARDAM
 * Purpose: Render the learner signup page with validation rules from the auth structure.
 * What it is: A route-level auth page that creates a user locally and redirects to login.
 */
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useState } from "react";
import { getDefaultRouteForRole, useAuth } from "../context/AuthContext";
import AuthLayout from "../components/AuthLayout";
import AuthCard from "../components/AuthCard";
import InputField from "../components/InputField";
import PasswordField from "../components/PasswordField";
import SelectField from "../components/SelectField";
import GoogleSignInButton from "../components/GoogleSignInButton";
import StatusBanner from "../components/StatusBanner";

const ROLE_OPTIONS = [
  { value: "learner", label: "Learner" },
  { value: "instructor", label: "Instructor" },
  { value: "admin", label: "Admin" },
];

export default function SignupPage() {
  const navigate = useNavigate();
  const { signup, loginWithGoogle, checkEmailAvailability, isAuthenticated, defaultRoute } = useAuth();
  const [formValues, setFormValues] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    role: "learner",
  });
  const [error, setError] = useState("");
  const [emailStatus, setEmailStatus] = useState({
    message: "",
    isAvailable: null,
    isChecking: false,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to={defaultRoute} replace />;
  }

  const updateField = (fieldName, value) => {
    setFormValues((current) => ({ ...current, [fieldName]: value }));
    if (fieldName === "email") {
      setEmailStatus({
        message: "",
        isAvailable: null,
        isChecking: false,
      });
    }
  };

  const passwordChecks = {
    hasMinLength: formValues.password.length >= 8,
    hasUpper: /[A-Z]/.test(formValues.password),
    hasLower: /[a-z]/.test(formValues.password),
    hasSpecial: /[^A-Za-z0-9]/.test(formValues.password),
    matches: formValues.password && formValues.password === formValues.confirmPassword,
  };

  const passwordGuidance = [
    `${passwordChecks.hasMinLength ? "✓" : "•"} 8+ characters`,
    `${passwordChecks.hasUpper ? "✓" : "•"} one uppercase letter`,
    `${passwordChecks.hasLower ? "✓" : "•"} one lowercase letter`,
    `${passwordChecks.hasSpecial ? "✓" : "•"} one special character`,
  ].join(" | ");

  const confirmGuidance =
    formValues.confirmPassword && !passwordChecks.matches
      ? "Passwords do not match yet."
      : formValues.confirmPassword && passwordChecks.matches
        ? "Passwords match."
        : "";

  const handleEmailBlur = async () => {
    if (!formValues.email.trim()) {
      return;
    }

    setEmailStatus({
      message: "Checking email availability...",
      isAvailable: null,
      isChecking: true,
    });
    const result = await checkEmailAvailability(formValues.email);
    if (!result.ok) {
      setEmailStatus({
        message: result.error,
        isAvailable: null,
        isChecking: false,
      });
      return;
    }

    setEmailStatus({
      message: result.message,
      isAvailable: result.isAvailable,
      isChecking: false,
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    let currentEmailStatus = emailStatus;
    if (emailStatus.isAvailable === null && formValues.email.trim()) {
      setEmailStatus({
        message: "Checking email availability...",
        isAvailable: null,
        isChecking: true,
      });
      const availabilityResult = await checkEmailAvailability(formValues.email);
      if (!availabilityResult.ok) {
        setEmailStatus({
          message: availabilityResult.error,
          isAvailable: null,
          isChecking: false,
        });
        setError(availabilityResult.error);
        return;
      }
      currentEmailStatus = {
        message: availabilityResult.message,
        isAvailable: availabilityResult.isAvailable,
        isChecking: false,
      };
      setEmailStatus(currentEmailStatus);
    }

    if (currentEmailStatus.isAvailable === false) {
      setError("This email already has an account. Try logging in instead.");
      return;
    }
    setIsSubmitting(true);
    const result = await signup(formValues);
    setIsSubmitting(false);

    if (!result.ok) {
      setError(result.error);
      return;
    }

    setError("");
    navigate("/auth/login");
  };

  const handleGoogleSuccess = async (credential) => {
    const result = await loginWithGoogle(credential, formValues.role);

    if (!result.ok) {
      setError(result.error);
      return;
    }

    navigate(getDefaultRouteForRole(formValues.role));
  };

  return (
    <AuthLayout>
      <AuthCard
        title="Sign Up"
        subtitle="Create your Learnova account and choose the workspace that matches your role."
        footer={
          <div className="auth-link-stack">
            <Link className="auth-link" to="/auth/login">
              Already have an account? Login
            </Link>
          </div>
        }
      >
        <form className="auth-form" onSubmit={handleSubmit}>
          <StatusBanner tone="error" message={error} onClose={() => setError("")} />
          <InputField
            id="signup-name"
            label="Name"
            value={formValues.name}
            onChange={(value) => updateField("name", value)}
            placeholder="Enter full name"
          />
          <InputField
            id="signup-email"
            label="Email"
            type="email"
            value={formValues.email}
            onChange={(value) => updateField("email", value)}
            onBlur={handleEmailBlur}
            placeholder="you@example.com"
            helperText={emailStatus.isAvailable === true || emailStatus.isChecking ? emailStatus.message : ""}
            errorText={emailStatus.isAvailable === false ? emailStatus.message : ""}
          />
          <SelectField
            id="signup-role"
            label="Role"
            value={formValues.role}
            onChange={(value) => updateField("role", value)}
            options={ROLE_OPTIONS}
          />
          <PasswordField
            id="signup-password"
            label="Password"
            value={formValues.password}
            onChange={(value) => updateField("password", value)}
            placeholder="Create a strong password"
            helperText={passwordGuidance}
          />
          <PasswordField
            id="signup-confirm-password"
            label="Re-enter Password"
            value={formValues.confirmPassword}
            onChange={(value) => updateField("confirmPassword", value)}
            placeholder="Re-enter your password"
            helperText={confirmGuidance}
            errorText={formValues.confirmPassword && !passwordChecks.matches ? "Passwords do not match." : ""}
          />
          <button type="submit" className="auth-primary-button" disabled={isSubmitting}>
            {isSubmitting ? "Signing Up..." : "Sign Up"}
          </button>
        </form>

        <div className="auth-divider">
          <span>OR</span>
        </div>

        <GoogleSignInButton onSuccess={handleGoogleSuccess} onError={setError} />
      </AuthCard>
    </AuthLayout>
  );
}
