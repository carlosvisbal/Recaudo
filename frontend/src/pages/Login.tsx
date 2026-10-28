import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { ApiError } from "../api";

export function Login() {
  const { usuario, loading, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (!loading && usuario) return <Navigate to="/" replace />;

  return (
    <div className="login-wrap">
      <form
        className="login-card"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError("");
          try {
            await login(username, password);
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "No se pudo iniciar sesión.");
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="brand-mark">R</div>
        <div className="eyebrow">Control operativo</div>
        <h1>Bienvenido a Recaudo</h1>
        <p className="muted">Ingrese con el administrador para registrar pagos y emitir recibos.</p>
        {error ? <div className="error">{error}</div> : null}
        <div className="form" style={{ marginTop: 16 }}>
          <label>
            Usuario
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
          </label>
          <label>
            Contraseña
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          <button className="btn block" disabled={busy}>
            {busy ? "Ingresando…" : "Entrar"}
          </button>
        </div>
      </form>
    </div>
  );
}
