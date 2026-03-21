/*
 * File: GoogleSignInButton.jsx
 * Owner: KARDAM
 * Purpose: Render the official Google Sign-In button when a client ID is configured.
 * What it is: A thin wrapper around Google Identity Services for frontend auth entry.
 */
import { useEffect, useRef, useState } from "react";

const GOOGLE_SCRIPT_ID = "learnova-google-identity";

function decodeJwtPayload(credential) {
  const payload = credential.split(".")[1];
  return JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
}

export default function GoogleSignInButton({ onSuccess, onError }) {
  const buttonRef = useRef(null);
  const [isUnavailable, setIsUnavailable] = useState(false);
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId) {
      setIsUnavailable(true);
      return;
    }

    const initializeButton = () => {
      if (!window.google?.accounts?.id || !buttonRef.current) {
        return;
      }

      buttonRef.current.innerHTML = "";
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response) => {
          try {
            const payload = decodeJwtPayload(response.credential);
            onSuccess({
              name: payload.name,
              email: payload.email,
            });
          } catch {
            onError("Google sign-in could not decode the returned credential.");
          }
        },
      });

      window.google.accounts.id.renderButton(buttonRef.current, {
        type: "standard",
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "rectangular",
        width: 280,
      });
    };

    if (window.google?.accounts?.id) {
      initializeButton();
      return;
    }

    const existingScript = document.getElementById(GOOGLE_SCRIPT_ID);
    if (existingScript) {
      existingScript.addEventListener("load", initializeButton);
      return () => existingScript.removeEventListener("load", initializeButton);
    }

    const script = document.createElement("script");
    script.id = GOOGLE_SCRIPT_ID;
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = initializeButton;
    script.onerror = () => onError("Google Identity Services could not be loaded.");
    document.body.appendChild(script);

    return () => {
      script.onload = null;
      script.onerror = null;
    };
  }, [clientId, onError, onSuccess]);

  if (isUnavailable) {
    return (
      <div className="google-signin-fallback">
        <div className="google-signin-fallback-button">
          <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
            <path d="M21.8 12.2c0-.7-.1-1.4-.2-2h-9.4v3.8h5.4c-.2 1.2-.9 2.3-1.9 3v2.5h3.1c1.8-1.7 3-4.1 3-7.3Z" fill="#4285F4" />
            <path d="M12.2 22c2.7 0 5-1 6.6-2.6l-3.1-2.5c-.9.6-2 .9-3.5.9-2.7 0-4.9-1.8-5.7-4.2H3.3v2.6A9.9 9.9 0 0 0 12.2 22Z" fill="#34A853" />
            <path d="M6.5 13.6c-.2-.6-.4-1.2-.4-1.9s.1-1.3.4-1.9V7.2H3.3A9.9 9.9 0 0 0 2.2 11.7c0 1.6.4 3.1 1.1 4.5l3.2-2.6Z" fill="#FBBC05" />
            <path d="M12.2 5.6c1.5 0 2.8.5 3.8 1.5l2.8-2.8C17.2 2.8 14.9 2 12.2 2A9.9 9.9 0 0 0 3.3 7.2l3.2 2.6c.8-2.4 3-4.2 5.7-4.2Z" fill="#EA4335" />
          </svg>
          <span>Google Sign-In requires `VITE_GOOGLE_CLIENT_ID`.</span>
        </div>
      </div>
    );
  }

  return <div ref={buttonRef} className="google-signin-slot" />;
}
