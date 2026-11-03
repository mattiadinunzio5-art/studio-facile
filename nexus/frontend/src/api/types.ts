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
  type: 'project' | 'module' | 'document' | 'event' | 'entity' | 'series' | 'report';
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
  indicators: DataSection | UnavailableSection;
  events: DataSection | UnavailableSection;
  reports: DataSection | UnavailableSection;
  ai: { mode: 'local' | 'remote'; provider: string; runs: unknown[]; note: string };
  notifications: { unread_count: number; items: Notification[] };
  recent_activity: Activity[];
}

// --- Fase 2: Research Core ---------------------------------------------------

export type VerificationStatus = 'unverified' | 'verified_user' | 'verified_registry' | 'not_found';

export interface Source {
  id: number;
  source_type: string;
  title: string;
  authors: string[];
  year: number | null;
  publisher: string;
  container: string;
  pages: string;
  doi: string;
  isbn: string;
  url: string;
  accessed_at: string;
  notes: string;
  verification_status: VerificationStatus;
  verification_note: string;
  verified_at: string | null;
  is_demo: boolean;
  citation: string;
  created_at: string;
}

export type SourceInput = Omit<Source, 'id' | 'verification_status' | 'verification_note' | 'verified_at' | 'is_demo' | 'citation' | 'created_at'>;

export interface DocumentInfo {
  id: number;
  title: string;
  filename: string;
  kind: string;
  category: 'source_material' | 'user_work' | 'dataset';
  origin: string;
  origin_url: string;
  license_note: string;
  author: string;
  year: number | null;
  sha256: string;
  size_bytes: number;
  page_count: number | null;
  char_count: number;
  chunk_count: number;
  status: string;
  error: string | null;
  flagged_chunks: number;
  project_id: number | null;
  source_id: number | null;
  is_demo: boolean;
  created_at: string;
}

export interface Chunk {
  id: number;
  ordinal: number;
  page: number | null;
  locator: string;
  text: string;
  injection_flag: boolean;
}

export type Support = 'strong' | 'partial' | 'weak' | 'none';

export interface RetrievalHit {
  chunk_id: number;
  document_id: number;
  document_title: string;
  page: number | null;
  locator: string;
  text: string;
  score: number;
  support: Support;
  injection_flag: boolean;
  source_label: string;
}

export interface RetrievalResult {
  query: string;
  mode: 'hybrid' | 'text' | 'semantic';
  semantic_engine: string;
  hits: RetrievalHit[];
}

export type ClaimType = 'documented_fact' | 'interpretation' | 'hypothesis' | 'estimate' | 'missing';

export interface Claim {
  type: ClaimType;
  text: string;
  support: Support;
  coverage: number;
  evidence: number[];
  note: string;
}

export interface AskResult {
  question: string;
  mode: 'local_extractive' | 'ai_grounded';
  provider: string;
  claims: Claim[];
  passages: RetrievalHit[];
  disclaimer: string;
}

// --- Fase 3: Historical Intelligence / Time Machine / Knowledge Graph -------------

export const CATEGORIES = {
  economic: 'Storia economica',
  monetary: 'Storia monetaria',
  banking: 'Storia bancaria',
  industrial: 'Storia industriale',
  war_geopolitics: 'Guerre e geopolitica',
  revolution: 'Rivoluzioni',
  financial_crisis: 'Crisi finanziarie',
  empires: 'Imperi e potenze economiche',
  capitalism: 'Evoluzione del capitalismo',
} as const;
export type Category = keyof typeof CATEGORIES;

export const RELIABILITY = {
  established: 'Consolidata',
  probable: 'Probabile',
  disputed: 'Controversa',
  unverified: 'Non verificata',
} as const;
export type Reliability = keyof typeof RELIABILITY;

export const KNOWLEDGE_KINDS = {
  contemporary: "Nota all'epoca",
  later_discovery: 'Scoperta successiva',
  archival_release: "Apertura d'archivio",
  historiography: 'Storiografia',
} as const;

export interface KnowledgeItem {
  id: number;
  content: string;
  known_since_year: number;
  kind: keyof typeof KNOWLEDGE_KINDS;
  source_id: number | null;
}

export interface EventInput {
  title: string;
  start_year: number;
  start_month: number | null;
  start_day: number | null;
  end_year: number | null;
  end_month: number | null;
  end_day: number | null;
  period: string;
  region: string;
  countries: string[];
  categories: Category[];
  description: string;
  causes: string;
  consequences: string;
  people: string[];
  institutions: string[];
  economic_implications: string;
  reliability: Reliability;
  reliability_note: string;
}

export interface HistoricalEvent extends EventInput {
  id: number;
  date_label: string;
  is_demo: boolean;
  sources: { source_id: number; citation: string; verification_status: VerificationStatus; pages: string; note: string }[];
  knowledge: KnowledgeItem[];
  entity_id: number | null;
  source_warning: string | null;
  created_at: string;
  updated_at: string;
}

export interface TimelineEvent {
  id: number;
  title: string;
  date_label: string;
  start_year: number;
  end_year: number | null;
  status_at_date: 'concluded' | 'ongoing' | 'not_applicable';
  countries: string[];
  categories: Category[];
  reliability: Reliability;
  description: string;
  consequences: string | null;
  consequences_hidden: boolean;
  known_then: KnowledgeItem[];
  known_later: KnowledgeItem[];
  hidden_later_count: number;
  is_demo: boolean;
}

export interface Timeline {
  as_of_year: number | null;
  hindsight: boolean;
  events: TimelineEvent[];
  indicators: { series_id: number; name: string; unit: string; source: string; last_date: string; last_value: number; caveat: string }[];
  hidden_future_events: number;
  notes: string[];
}

export const ENTITY_TYPES = {
  person: 'Persona',
  state: 'Stato',
  company: 'Azienda',
  bank: 'Banca',
  institution: 'Istituzione',
  event: 'Evento',
  document: 'Documento',
  theory: 'Teoria economica',
  indicator: 'Indicatore',
} as const;
export type EntityType = keyof typeof ENTITY_TYPES;

export const RELATION_TYPES = {
  caused: 'Ha causato',
  influenced: 'Ha influenzato',
  contemporary_of: 'È contemporaneo a',
  related_to: 'È collegato a',
  financed: 'Ha finanziato',
  involved_in: 'È stato coinvolto in',
  replaced: 'Ha sostituito',
  preceded: 'Ha preceduto',
} as const;
export type RelationType = keyof typeof RELATION_TYPES;

export const PROVENANCE = {
  sourced: 'Documentata',
  user_hypothesis: "Ipotesi dell'utente",
  ai_hypothesis: "Ipotesi AI (da verificare)",
} as const;
export type Provenance = keyof typeof PROVENANCE;

export interface Entity {
  id: number;
  entity_type: EntityType;
  name: string;
  description: string;
  aliases: string[];
  start_year: number | null;
  end_year: number | null;
  event_id: number | null;
  document_id: number | null;
  is_demo: boolean;
}

export interface Relation {
  id: number;
  source_entity_id: number;
  target_entity_id: number;
  relation_type: RelationType;
  provenance: Provenance;
  source_id: number | null;
  chunk_id: number | null;
  evidence_note: string;
  confidence: 'low' | 'medium' | 'high';
  start_year: number | null;
  ai_run_id: number | null;
  evidence_label: string;
  created_at: string;
}

export interface GraphNode {
  id: number;
  name: string;
  entity_type: EntityType;
  x: number;
  y: number;
  degree: number;
  betweenness: number;
  is_focus: boolean;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: Relation[];
  stats: { entities: number; relations: number; shown_nodes: number; shown_edges: number; components: number; by_provenance: Record<Provenance, number> };
}

export interface DataItem {
  id: string;
  title: string;
  subtitle: string;
  date: string;
  url: string;
  is_demo: boolean;
}

export interface DataSection {
  available: true;
  total: number;
  items: DataItem[];
  note: string;
}

// --- Fase 4: Financial Intelligence ---------------------------------------------------

export const SERIES_CATEGORIES = {
  stocks: 'Azioni', indices: 'Indici', bonds: 'Obbligazioni', commodities: 'Materie prime', precious_metals: 'Oro e metalli preziosi',
  fx: 'Valute', crypto: 'Criptovalute', rates: "Tassi d'interesse", inflation: 'Inflazione', public_debt: 'Debito pubblico',
  gdp: 'PIL', unemployment: 'Disoccupazione', trade_balance: 'Bilance commerciali', other: 'Altro',
} as const;
export type SeriesCategory = keyof typeof SERIES_CATEGORIES;
export type Frequency = 'D' | 'W' | 'M' | 'Q' | 'A';
export const FREQUENCY_LABEL: Record<Frequency, string> = { D: 'Giornaliera', W: 'Settimanale', M: 'Mensile', Q: 'Trimestrale', A: 'Annuale' };

export interface SeriesInfo {
  id: number;
  name: string;
  category: SeriesCategory;
  country: string;
  connector: string;
  source_series_id: string;
  source_label: string;
  source_url: string;
  license_note: string;
  unit: string;
  frequency: Frequency;
  start_date: string | null;
  end_date: string | null;
  source_last_updated: string;
  retrieved_at: string | null;
  from_cache: boolean;
  observation_count: number;
  missing_count: number;
  description: string;
  is_demo: boolean;
  last_value: number | null;
  last_date: string | null;
  created_at: string;
}

export interface Point { date: string; value: number | null }

export interface SeriesDetail extends SeriesInfo {
  observations: Point[];
  import_warnings: string[];
}

export interface Preset { connector: string; label: string; category: SeriesCategory; params: Record<string, unknown> }

export interface Analysis {
  series_id: number;
  frequency: Frequency;
  metrics_basis: 'levels' | 'rates';
  summary: Record<string, number | string | null>;
  returns?: Record<string, number | string | null>;
  changes?: Record<string, number | string | null>;
  drawdown?: { max_drawdown: number; peak_date: string; trough_date: string; recovery_date: string | null };
  drawdown_series?: Point[];
  returns_series: Point[];
  moving_averages: Record<string, Point[]>;
  anomalies: { date: string; change: number; z: number }[];
  timeseries: { linear_trend?: { slope_per_period: number }; adf?: { statistic: number; p_value: number; interpretation: string; nobs: number }; acf?: number[]; note?: string };
  warnings: string[];
  source: { label: string; url: string; unit: string; frequency: Frequency; last_updated: string; retrieved_at: string | null };
}

export interface Comparison {
  frequency: Frequency;
  common_observations: number;
  basis: 'returns' | 'levels';
  period: { start: string; end: string };
  procedure: string[];
  correlation: Record<string, Record<string, number | null>>;
  aligned: Record<string, Point[]>;
  rebased_100: Record<string, Point[] | null>;
  notes: string[];
  series: { id: number; name: string; unit: string; frequency: Frequency; source: string }[];
}

export interface CredentialInfo { provider: string; configured: boolean; hint: string; config: Record<string, string>; updated_at: string | null }
