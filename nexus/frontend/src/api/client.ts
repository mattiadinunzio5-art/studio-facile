import type {
  EntityType,
  Entity,
  EventInput,
  GraphData,
  HistoricalEvent,
  KnowledgeItem,
  Relation,
  Timeline,
  AskResult,
  Chunk,
  DocumentInfo,
  RetrievalResult,
  Source,
  SourceInput,
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

/** Query string dai soli parametri valorizzati. */
export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : '';
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      ...init,
      credentials: 'same-origin',
      headers:
        init.body && !(init.body instanceof FormData)
          ? { 'Content-Type': 'application/json', ...init.headers }
          : init.headers,
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

  // Fase 2
  documents: (params: { project_id?: number; category?: string } = {}) => request<DocumentInfo[]>(`/documents${qs(params)}`),
  document: (id: number) => request<DocumentInfo>(`/documents/${id}`),
  uploadDocument: (form: FormData) => request<DocumentInfo>('/documents', { method: 'POST', body: form }),
  importGutenberg: (data: { ebook_id: number; title: string; author: string }) =>
    request<DocumentInfo>('/documents/gutenberg', json('POST', data)),
  updateDocument: (id: number, data: Partial<DocumentInfo>) => request<DocumentInfo>(`/documents/${id}`, json('PATCH', data)),
  deleteDocument: (id: number) => request<void>(`/documents/${id}?confirm=true`, { method: 'DELETE' }),
  chunks: (id: number, offset = 0, limit = 50) => request<Chunk[]>(`/documents/${id}/chunks?offset=${offset}&limit=${limit}`),
  documentFileUrl: (id: number) => `${BASE}/documents/${id}/file`,

  sources: (q?: string) => request<Source[]>(`/sources${qs({ q })}`),
  createSource: (data: Partial<SourceInput>) => request<Source>('/sources', json('POST', data)),
  updateSource: (id: number, data: Partial<SourceInput>) => request<Source>(`/sources/${id}`, json('PUT', data)),
  verifySource: (id: number, method: 'user' | 'registry', note = '') =>
    request<Source>(`/sources/${id}/verify`, json('POST', { method, note })),
  deleteSource: (id: number) => request<void>(`/sources/${id}?confirm=true`, { method: 'DELETE' }),

  researchSearch: (q: string, mode = 'hybrid', limit = 10) =>
    request<RetrievalResult>(`/research/search${qs({ q, mode, limit })}`),
  ask: (question: string, document_ids?: number[]) => request<AskResult>('/research/ask', json('POST', { question, document_ids })),

  // Fase 3
  events: (params: Record<string, string | number | undefined> = {}) => request<HistoricalEvent[]>(`/history/events${qs(params)}`),
  event: (id: number) => request<HistoricalEvent>(`/history/events/${id}`),
  createEvent: (data: EventInput) => request<HistoricalEvent>('/history/events', json('POST', data)),
  updateEvent: (id: number, data: EventInput) => request<HistoricalEvent>(`/history/events/${id}`, json('PUT', data)),
  deleteEvent: (id: number) => request<void>(`/history/events/${id}?confirm=true`, { method: 'DELETE' }),
  linkEventSource: (id: number, source_id: number, pages = '') => request<HistoricalEvent>(`/history/events/${id}/sources`, json('POST', { source_id, pages })),
  unlinkEventSource: (id: number, source_id: number) => request<HistoricalEvent>(`/history/events/${id}/sources/${source_id}`, { method: 'DELETE' }),
  addKnowledge: (id: number, data: Omit<KnowledgeItem, 'id'>) => request<HistoricalEvent>(`/history/events/${id}/knowledge`, json('POST', data)),
  deleteKnowledge: (id: number, itemId: number) => request<HistoricalEvent>(`/history/events/${id}/knowledge/${itemId}`, { method: 'DELETE' }),
  linkEvents: (id: number, data: Record<string, unknown>) => request<Relation>(`/history/events/${id}/links`, json('POST', data)),
  timeline: (params: Record<string, string | number | boolean | undefined>) => request<Timeline>(`/history/timeline${qs(params)}`),

  graph: (params: { focus?: number; depth?: number; relation_types?: string[]; provenance?: string[]; entity_types?: string[] }) => {
    const p = new URLSearchParams();
    if (params.focus) p.set('focus', String(params.focus));
    if (params.depth) p.set('depth', String(params.depth));
    for (const k of ['relation_types', 'provenance', 'entity_types'] as const) for (const v of params[k] ?? []) p.append(k, v);
    const s = p.toString();
    return request<GraphData>(`/graph${s ? `?${s}` : ''}`);
  },
  graphPath: (source: number, target: number) => request<{ found: boolean; entity_ids: number[]; relations: Relation[] }>(`/graph/path?source=${source}&target=${target}`),
  entities: (q?: string, entity_type?: EntityType) => request<Entity[]>(`/graph/entities${qs({ q, entity_type })}`),
  entity: (id: number) => request<Entity>(`/graph/entities/${id}`),
  createEntity: (data: Partial<Entity>) => request<Entity>('/graph/entities', json('POST', data)),
  deleteEntity: (id: number) => request<void>(`/graph/entities/${id}?confirm=true`, { method: 'DELETE' }),
  entityRelations: (id: number) => request<Relation[]>(`/graph/entities/${id}/relations`),
  createRelation: (data: Record<string, unknown>) => request<Relation>('/graph/relations', json('POST', data)),
  deleteRelation: (id: number) => request<void>(`/graph/relations/${id}`, { method: 'DELETE' }),
};
