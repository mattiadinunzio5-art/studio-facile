// Contratto con il backend (nexus/backend/nexus/api/schemas.py).

export type ModuleStatus = 'in_preparation' | 'partial' | 'available';

export interface Module {
  id: string;
  code: string;
  name: string;
  summary: string;
  phase: number;
  status: ModuleStatus;
  planned_features: string[];
  implemented_features: string[];
}

export type ProjectStatus = 'active' | 'archived';

export interface Project {
  id: number;
  title: string;
  description: string;
  status: ProjectStatus;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface Activity {
  id: number;
  actor: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  summary: string;
  created_at: string;
}

export interface Notification {
  id: number;
  level: 'info' | 'warning' | 'error';
  title: string;
  body: string;
  read_at: string | null;
  created_at: string;
}

export interface SearchQuery {
  id: number;
  query: string;
  results_count: number;
  created_at: string;
}

export interface SearchHit {
  type: 'project' | 'module';
  id: string;
  title: string;
  snippet: string;
  url: string;
}

export interface SearchResult {
  query: string;
  hits: SearchHit[];
  searched_scopes: string[];
  unavailable_scopes: string[];
}

export type ConnectorStatus = 'unknown' | 'reachable' | 'degraded' | 'unreachable';

export interface Connector {
  id: string;
  name: string;
  category: string;
  homepage: string;
  terms_url: string;
  requires_api_key: boolean;
  implemented: boolean;
  planned_phase: number;
  notes: string;
  last_status: ConnectorStatus;
  last_checked_at: string | null;
  last_http_status: number | null;
  last_latency_ms: number | null;
  last_error: string | null;
}

export interface AIProvider {
  id: string;
  name: string;
  kind: 'local' | 'remote';
  requires_credentials: boolean;
  implemented: boolean;
  notes: string;
}

export interface SystemStatus {
  version: string;
  environment: string;
  database: string;
  database_ok: boolean;
  ai_mode: 'local' | 'remote';
  ai_provider: AIProvider;
  ai_providers: AIProvider[];
  server_time: string;
}

export const WIDGET_IDS = [
  'modules',
  'sources',
  'searches',
  'projects',
  'indicators',
  'events',
  'reports',
  'ai',
  'notifications',
] as const;
export type WidgetId = (typeof WIDGET_IDS)[number];

export interface DashboardLayout {
  order: WidgetId[];
  hidden: WidgetId[];
}

export interface UnavailableSection {
  available: false;
  reason: string;
  planned_phase: number;
}

export interface Dashboard {
  generated_at: string;
  layout: DashboardLayout;
  modules: Module[];
  sources: {
    total: number;
    implemented: number;
    by_status: Partial<Record<ConnectorStatus, number>>;
    items: Connector[];
  };
  recent_searches: SearchQuery[];
  projects: { active_count: number; archived_count: number; items: Project[] };
  indicators: UnavailableSection;
  events: UnavailableSection;
  reports: UnavailableSection;
  ai: { mode: 'local' | 'remote'; provider: string; runs: unknown[]; note: string };
  notifications: { unread_count: number; items: Notification[] };
  recent_activity: Activity[];
}
