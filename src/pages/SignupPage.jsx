/*
 * File: SignupPage.jsx
 * Owner: KARDAM
 * Purpose: Render the learner signup page with validation rules from the auth structure.
 * What it is: A route-level auth page that creates a user locally and redirects to login.
 */
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import AuthLayout from "../components/AuthLayout";
import AuthCard from "../components/AuthCard";
import InputField from "../components/InputField";
import PasswordField from "../components/PasswordField";
import SelectField from "../components/SelectField";
import ErrorMessage from "../components/ErrorMessage";
import GoogleSignInButton from "../components/GoogleSignInButton";

const ROLE_OPTIONS = [
  { value: "learner", label: "Learner" },
  { value: "instructor", label: "Instructor" },
  { value: "admin", label: "Admin" },
];

export default function SignupPage() {
  const navigate = useNavigate();
  const { signup, loginWithGoogle, isAuthenticated } = useAuth();
  const [formValues, setFormValues] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    role: "learner",
  });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/my-courses" replace />;
  }

  const updateField = (fieldName, value) => {
    setFormValues((current) => ({ ...current, [fieldName]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
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

  const handleGoogleSuccess = (profile) => {
    const result = loginWithGoogle(profile, formValues.role);

    if (!result.ok) {
      setError(result.error);
      return;
    }

    navigate("/my-courses");
  };

  return (
    <AuthLayout>
      <AuthCard
        title="Sign Up"
        footer={
          <div className="auth-link-stack">
            <Link className="auth-link" to="/auth/login">
              Already have an account? Login
            </Link>
          </div>
        }
      >
        <form className="auth-form" onSubmit={handleSubmit}>
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
            placeholder="you@example.com"
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
          />
          <PasswordField
            id="signup-confirm-password"
            label="Re-enter Password"
            value={formValues.confirmPassword}
            onChange={(value) => updateField("confirmPassword", value)}
            placeholder="Re-enter your password"
          />
          <ErrorMessage message={error} />
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
