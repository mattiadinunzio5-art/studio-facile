import type {
  Activity,
  Connector,
  Dashboard,
  DashboardLayout,
  Module,
  Notification,
  Project,
  ProjectStatus,
  SearchResult,
  SystemStatus,
} from './types';

/** Errore uniforme: riflette il formato {error: {code, message, details}} del backend. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const BASE = '/api';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      ...init,
      headers: init.body ? { 'Content-Type': 'application/json', ...init.headers } : init.headers,
    });
  } catch {
    throw new ApiError(0, 'network_error', 'Backend non raggiungibile. Verifica che il server NEXUS sia avviato.');
  }
  if (res.status === 204) return undefined as T;
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* risposta non JSON */
  }
  if (!res.ok) {
    const err = (body as { error?: { code?: string; message?: string; details?: unknown } } | null)?.error;
    throw new ApiError(res.status, err?.code ?? `http_${res.status}`, err?.message ?? `Errore HTTP ${res.status}`, err?.details);
  }
  return body as T;
}

const json = (method: string, data?: unknown): RequestInit => ({
  method,
  body: data === undefined ? undefined : JSON.stringify(data),
});

export const api = {
  health: () => request<{ status: 'ok'; version: string }>('/health'),
  systemStatus: () => request<SystemStatus>('/system/status'),

  modules: () => request<Module[]>('/modules'),
  module: (id: string) => request<Module>(`/modules/${encodeURIComponent(id)}`),

  dashboard: () => request<Dashboard>('/dashboard'),
  saveLayout: (layout: DashboardLayout) => request<DashboardLayout>('/dashboard/layout', json('PUT', layout)),

  projects: (status?: ProjectStatus) => request<Project[]>(`/projects${status ? `?status=${status}` : ''}`),
  createProject: (data: { title: string; description: string }) => request<Project>('/projects', json('POST', data)),
  updateProject: (id: number, data: Partial<Pick<Project, 'title' | 'description' | 'status'>>) =>
    request<Project>(`/projects/${id}`, json('PATCH', data)),
  deleteProject: (id: number) => request<void>(`/projects/${id}?confirm=true`, { method: 'DELETE' }),

  activity: (limit = 50, offset = 0) => request<Activity[]>(`/activity?limit=${limit}&offset=${offset}`),

  notifications: (unreadOnly = false) => request<Notification[]>(`/notifications${unreadOnly ? '?unread_only=true' : ''}`),
  markRead: (id: number) => request<Notification>(`/notifications/${id}/read`, { method: 'POST' }),
  markAllRead: () => request<{ updated: number }>('/notifications/read-all', { method: 'POST' }),

  connectors: () => request<Connector[]>('/connectors'),
  checkConnector: (id: string) => request<Connector>(`/connectors/${encodeURIComponent(id)}/check`, { method: 'POST' }),

  search: (q: string) => request<SearchResult>(`/search?q=${encodeURIComponent(q)}`),
};
