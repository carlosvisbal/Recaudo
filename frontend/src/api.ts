export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

function readCookie(name: string): string {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

async function ensureCsrf(): Promise<string> {
  let token = readCookie("csrftoken");
  if (!token) {
    await fetch("/api/auth/csrf/", { credentials: "include" });
    token = readCookie("csrftoken");
  }
  return token;
}

function flattenError(body: unknown): string {
  if (!body) return "No se pudo completar la operación.";
  if (typeof body === "string") return body;
  if (typeof body === "object") {
    const data = body as Record<string, unknown>;
    if (typeof data.detail === "string") return data.detail;
    const parts: string[] = [];
    for (const [key, value] of Object.entries(data)) {
      if (Array.isArray(value)) parts.push(`${key}: ${value.join(" ")}`);
      else if (typeof value === "string") parts.push(value);
    }
    if (parts.length) return parts.join(" ");
  }
  return "No se pudo completar la operación.";
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  const isForm = options.body instanceof FormData;
  if (!isForm && !headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (options.method && options.method !== "GET") {
    headers.set("X-CSRFToken", await ensureCsrf());
  }
  const response = await fetch(path, { ...options, headers, credentials: "include" });
  if (response.status === 401 || response.status === 403) {
    if (!path.includes("/auth/login") && !path.includes("/auth/csrf")) {
      const errBody = await response.json().catch(() => null);
      if (response.status === 403 && errBody && (errBody as { detail?: string }).detail) {
        throw new ApiError(flattenError(errBody), response.status, errBody);
      }
      if (response.status === 401 || (errBody && String((errBody as { detail?: string }).detail || "").includes("autentic"))) {
        throw new ApiError("Sesión expirada", response.status, errBody);
      }
    }
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(flattenError(body), response.status, body);
  }
  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return response.json() as Promise<T>;
  return response as unknown as T;
}

export type Padrino = {
  id: string;
  nombre_completo: string;
  telefono: string;
  correo: string;
  estado: "activo" | "inactivo";
  familias_activas?: number;
};

export type Familia = {
  id: string;
  nombre: string;
  contacto_principal: string;
  telefono: string;
  correo: string;
  padrino: string;
  padrino_nombre: string;
  observaciones: string;
  estado: "activo" | "inactivo";
};

export type Actividad = {
  id: string;
  nombre: string;
  descripcion: string;
  fecha_inicio: string;
  fecha_fin: string;
  estado: "programada" | "activa" | "cerrada";
  total_recaudado?: string | null;
  cantidad_recaudos?: number;
};

export type Recaudo = {
  id: string;
  numero: number;
  numero_formateado: string;
  fecha: string;
  actividad: string;
  actividad_nombre: string;
  padrino: string;
  padrino_nombre: string;
  familia: string | null;
  familia_nombre: string;
  aportante_nombre: string;
  valor: string;
  valor_formato: string;
  valor_en_letras?: string;
  medio_pago: "efectivo" | "transferencia";
  medio_pago_display: string;
  concepto: string;
  referencia_consignacion: string;
  estado: "confirmado" | "anulado";
  estado_display: string;
  usuario_nombre: string;
  soportes_count?: number;
  soportes?: { id: string; nombre_original: string; content_type: string; tamano: number }[];
  recibo?: { generado_en: string } | null;
  motivo_anulacion?: string;
  organizacion_nombre?: string;
  familia_telefono?: string;
  creado_en: string;
};

export type TotalFila = {
  id?: string | null;
  nombre: string;
  fecha?: string;
  total: string;
  total_formato?: string;
  cantidad: number;
};

export type CruzadoFila = {
  padrino_id: string;
  padrino_nombre: string;
  actividad_id: string;
  actividad_nombre: string;
  total: string;
  total_formato?: string;
  cantidad: number;
  familias_asignadas: number;
  familias_pagaron: number;
  familias_pendientes: number;
};

export type PendienteFila = {
  familia_id: string;
  familia_nombre: string;
  telefono: string;
  padrino_id: string;
  padrino_nombre: string;
  actividad_id: string;
  actividad_nombre: string;
};

export type Totales = {
  total_confirmado: string;
  total_confirmado_formato: string;
  cantidad_confirmados: number;
  cantidad_anulados: number;
  por_actividad: TotalFila[];
  por_padrino: TotalFila[];
  por_familia: TotalFila[];
  por_fecha?: TotalFila[];
  por_padrino_actividad?: CruzadoFila[];
  pendientes?: {
    count: number;
    page?: number;
    page_size?: number;
    pages?: number;
    familias_asignadas: number;
    familias_al_dia: number;
    results: PendienteFila[];
  };
};

export type Compartir = {
  mensaje: string;
  whatsapp_url: string;
  whatsapp_url_destino: string;
  telefono_destino: string | null;
  familia_id: string | null;
  familia_nombre: string;
  tiene_telefono_familia: boolean;
  mailto: string;
  destinatario_sugerido: string | null;
  smtp_configurado: boolean;
  aviso_whatsapp: string;
  aviso_correo: string;
};

export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  page: number;
  page_size: number;
  pages: number;
  results: T[];
};

export function unwrapList<T>(data: { results?: T[]; resultados?: T[] } | T[] | null | undefined): T[] {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  return data.results || data.resultados || [];
}

export function parsePage<T>(data: unknown, fallbackSize = 20): Page<T> {
  if (data && typeof data === "object" && ("results" in data || "resultados" in data || "count" in data)) {
    const d = data as {
      count?: number;
      next?: string | null;
      previous?: string | null;
      page?: number;
      page_size?: number;
      pages?: number;
      results?: T[];
      resultados?: T[];
    };
    const results = d.results || d.resultados || [];
    const count = d.count ?? results.length;
    const pageSize = d.page_size || fallbackSize;
    return {
      count,
      next: d.next ?? null,
      previous: d.previous ?? null,
      page: d.page ?? 1,
      page_size: pageSize,
      pages: d.pages ?? Math.max(1, Math.ceil(count / Math.max(pageSize, 1))),
      results,
    };
  }
  const results = unwrapList<T>(data as T[]);
  return {
    count: results.length,
    next: null,
    previous: null,
    page: 1,
    page_size: results.length || fallbackSize,
    pages: 1,
    results,
  };
}

export function cop(value: string | number | null | undefined): string {
  const n = Number(value ?? 0);
  if (Number.isNaN(n)) return "$0";
  return n.toLocaleString("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
}
