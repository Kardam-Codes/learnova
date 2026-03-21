/*
 * File: AuthCard.jsx
 * Owner: KARDAM
 * Purpose: Wrap auth forms in a consistent card container.
 * What it is: A presentational shell for login, signup, and forgot-password content.
 */
export default function AuthCard({ title, subtitle, children, footer }) {
  return (
    <section className="auth-card">
      <div className="auth-card-header">
        <span className="eyebrow">Learnova Access</span>
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      <div className="auth-card-body">{children}</div>
      {footer ? <div className="auth-card-footer">{footer}</div> : null}
    </section>
  );
}
