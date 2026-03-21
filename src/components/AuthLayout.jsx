/*
 * File: AuthLayout.jsx
 * Owner: KARDAM
 * Purpose: Provide the shared dark auth-page shell for login and signup.
 * What it is: A centered auth layout with logo on top and a single auth card in the middle.
 */
export default function AuthLayout({ children }) {
  return (
    <main className="auth-layout">
      <div className="auth-logo-lockup">
        <div className="auth-logo-mark">L</div>
        <strong>Learnova</strong>
      </div>
      <div className="auth-layout-center">{children}</div>
    </main>
  );
}
