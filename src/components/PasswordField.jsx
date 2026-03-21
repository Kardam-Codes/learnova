/*
 * File: PasswordField.jsx
 * Owner: KARDAM
 * Purpose: Render a password input field with show/hide support.
 * What it is: A reusable auth field specialized for password entry.
 */
import { useState } from "react";

function EyeIcon({ visible }) {
  return (
    <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
      <path
        d="M2.5 12s3.6-6 9.5-6 9.5 6 9.5 6-3.6 6-9.5 6-9.5-6-9.5-6Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      />
      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="2" />
      {!visible ? (
        <path d="M4 20 20 4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      ) : null}
    </svg>
  );
}

export default function PasswordField({ id, label, value, onChange, placeholder }) {
  const [visible, setVisible] = useState(false);

  return (
    <label className="auth-field" htmlFor={id}>
      <span>{label}</span>
      <div className="password-field-shell">
        <input
          id={id}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
        />
        <button type="button" className="password-toggle" onClick={() => setVisible((state) => !state)}>
          <EyeIcon visible={visible} />
        </button>
      </div>
    </label>
  );
}
