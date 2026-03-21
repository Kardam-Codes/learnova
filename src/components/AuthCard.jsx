/*
 * File: AuthCard.jsx
 * Owner: KARDAM
 * Purpose: Wrap auth forms in a consistent card container.
 * What it is: A presentational shell for login, signup, and forgot-password content.
 */
export default function AuthCard({ title, children, footer }) {
  return (
    <section className="auth-card">
      <h1>{title}</h1>
      <div className="auth-card-body">{children}</div>
      {footer ? <div className="auth-card-footer">{footer}</div> : null}
    </section>
  );
}
