/*
 * File: ErrorMessage.jsx
 * Owner: KARDAM
 * Purpose: Surface auth validation and submission errors clearly.
 * What it is: A lightweight message block for auth form failures.
 */
export default function ErrorMessage({ message }) {
  if (!message) {
    return null;
  }

  return <div className="auth-error-message">{message}</div>;
}
