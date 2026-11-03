import { vi } from 'vitest';
import type { Dashboard, Module, Project } from '../api/types';
import { WIDGET_IDS } from '../api/types';

export const modules: Module[] = 'ABCDEFGH'.split('').map((code, i) => ({
  id: ['historical', 'financial', 'time-machine', 'knowledge-graph', 'war-room', 'economic-lab', 'research-studio', 'business'][i],
  code,
  name: `Modulo ${code}`,
  summary: `Sommario ${code}`,
  phase: [3, 4, 3, 3, 5, 6, 7, 8][i],
  status: 'in_preparation',
  planned_features: [`Funzione prevista ${code}`],
  implemented_features: [],
}));

export const project: Project = {
  id: 7,
  title: 'Crisi del 1929',
  description: 'Origini',
  status: 'active',
  is_demo: false,
  created_at: '2026-11-01T10:00:00Z',
  updated_at: '2026-11-01T10:00:00Z',
};

export const dashboard: Dashboard = {
  generated_at: '2026-11-03T10:00:00Z',
  layout: { order: [...WIDGET_IDS], hidden: [] },
  modules,
  sources: { total: 1, implemented: 0, by_status: { unknown: 1 }, items: [
    { id: 'fred', name: 'FRED', category: 'macro', homepage: 'https://x', terms_url: 'https://x/t', requires_api_key: true, implemented: false, planned_phase: 4, notes: '', last_status: 'unknown', last_checked_at: null, last_http_status: null, last_latency_ms: null, last_error: null },
  ] },
  recent_searches: [],
  projects: { active_count: 1, archived_count: 0, items: [project] },
  indicators: { available: false, reason: 'Nessuna serie importata.', planned_phase: 4 },
  events: { available: false, reason: 'Archivio eventi non ancora disponibile.', planned_phase: 3 },
  reports: { available: false, reason: 'Rapporti non ancora disponibili.', planned_phase: 7 },
  ai: { mode: 'local', provider: 'Nessuno (modalità locale)', runs: [], note: 'Nessun modello AI eseguito.' },
  notifications: { unread_count: 0, items: [] },
  recent_activity: [],
};

type Handler = (url: string, init?: RequestInit) => unknown;

/** Sostituisce fetch con un router di risposte: chiave "METHOD /path" (prefisso). */
export function mockApi(routes: Record<string, Handler | unknown>) {
  const calls: { method: string; url: string; body?: unknown }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? 'GET').toUpperCase();
    calls.push({ method, url, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    const key = Object.keys(routes)
      .filter((k) => {
        const [m, p] = k.split(' ');
        return m === method && url.startsWith(p);
      })
      .sort((a, b) => b.length - a.length)[0];
    if (!key) return new Response(JSON.stringify({ error: { code: 'not_found', message: 'non mockato' } }), { status: 404 });
    const r = routes[key];
    const value = typeof r === 'function' ? (r as Handler)(url, init) : r;
    if (value instanceof Response) return value;
    if (value === undefined) return new Response(null, { status: 204 });
    return new Response(JSON.stringify(value), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);
  return { fetchMock, calls };
}
