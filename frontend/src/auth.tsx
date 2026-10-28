import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "./api";

type Usuario = { username: string; nombre: string; email: string };
type Organizacion = { nombre: string; nit: string; ciudad: string; telefono: string; correo: string };

type AuthState = {
  loading: boolean;
  usuario: Usuario | null;
  organizacion: Organizacion | null;
  smtp: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [organizacion, setOrganizacion] = useState<Organizacion | null>(null);
  const [smtp, setSmtp] = useState(false);

  const refresh = async () => {
    try {
      await api("/api/auth/csrf/");
      const me = await api<{ usuario: Usuario; organizacion: Organizacion; smtp_configurado: boolean }>(
        "/api/auth/me/"
      );
      setUsuario(me.usuario);
      setOrganizacion(me.organizacion);
      setSmtp(me.smtp_configurado);
    } catch {
      setUsuario(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      loading,
      usuario,
      organizacion,
      smtp,
      refresh,
      login: async (username, password) => {
        await api("/api/auth/csrf/");
        const data = await api<{ usuario: Usuario }>("/api/auth/login/", {
          method: "POST",
          body: JSON.stringify({ username, password }),
        });
        setUsuario(data.usuario);
        await refresh();
      },
      logout: async () => {
        try {
          await api("/api/auth/logout/", { method: "POST" });
        } catch (error) {
          if (!(error instanceof ApiError)) throw error;
        }
        setUsuario(null);
      },
    }),
    [loading, usuario, organizacion, smtp]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("AuthProvider requerido");
  return ctx;
}
