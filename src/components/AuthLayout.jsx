/*
 * File: AuthLayout.jsx
 * Owner: KARDAM
 * Purpose: Provide the shared dark auth-page shell for login and signup.
 * What it is: A centered auth layout with the Learnova wordmark on top and a single auth card in the middle.
 */
export default function AuthLayout({ children }) {
  return (
    <main className="auth-layout">
      <div className="auth-logo-lockup">
        <strong className="auth-logo-wordmark">Learnova</strong>
        <p className="auth-logo-tagline">Clean for learning, structured for teams, engaging for growth.</p>
      </div>
      <div className="auth-layout-center">{children}</div>
    </main>
  );
}
