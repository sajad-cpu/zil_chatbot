import { useState } from "react";
import { signup, login } from "../api.js";

export default function AuthPage({ onAuthSuccess }) {
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const email_val = email.trim();
      const password_val = password.trim();

      if (!email_val || !password_val) {
        throw new Error("Email and password are required");
      }

      let response;
      if (isSignup) {
        response = await signup(email_val, password_val);
      } else {
        response = await login(email_val, password_val);
      }

      // Save token and notify parent
      localStorage.setItem("auth_token", response.access_token);
      onAuthSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h1>Zil Chat</h1>
          <p className="auth-subtitle">
            {isSignup ? "Create an account" : "Sign in to your account"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              disabled={loading}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={loading}
              required
            />
          </div>

          {error && <div className="auth-error">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="auth-submit"
          >
            {loading
              ? "..."
              : isSignup
              ? "Sign Up"
              : "Sign In"}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            {isSignup ? "Already have an account?" : "Don't have an account?"}
            {" "}
            <button
              type="button"
              onClick={() => {
                setIsSignup(!isSignup);
                setError("");
                setEmail("");
                setPassword("");
              }}
              className="auth-toggle"
            >
              {isSignup ? "Sign In" : "Sign Up"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
