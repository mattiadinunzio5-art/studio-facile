import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { GraphData, Timeline } from '../api/types';
import { EventForm } from '../pages/History';
import { mockApi } from './fixtures';
import { renderApp } from './render';

describe('event form', () => {
  it('requires a start year and sends BCE years and lists correctly', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<EventForm onSubmit={onSubmit} onCancel={() => {}} />);
    await userEvent.type(screen.getByLabelText('Titolo'), 'Idi di marzo');
    const year = screen.getByLabelText(/Anno inizio/);
    await userEvent.clear(year);
    await userEvent.click(screen.getByRole('button', { name: 'Salva evento' }));
    expect(screen.getByRole('alert')).toHaveTextContent("L'anno iniziale è obbligatorio");
    await userEvent.type(year, '-44');
    await userEvent.type(screen.getByLabelText(/Paesi/), 'Roma, Italia');
    await userEvent.click(screen.getByLabelText('Imperi e potenze economiche'));
    await userEvent.click(screen.getByRole('button', { name: 'Salva evento' }));
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ start_year: -44, countries: ['Roma', 'Italia'], categories: ['empires'], end_year: null }));
  });
});

const timeline: Timeline = {
  as_of_year: 1931,
  hindsight: false,
  hidden_future_events: 2,
  notes: ['Vista rigorosa al 1931: nascosti eventi successivi.'],
  indicators: [],
  events: [{
    id: 1, title: 'Crollo di Wall Street', date_label: '24 ott 1929', start_year: 1929, end_year: 1929, status_at_date: 'concluded',
    countries: [], categories: [], reliability: 'established', description: 'Crollo della borsa.', consequences: null, consequences_hidden: true,
    known_then: [{ id: 1, content: 'Vendite di panico.', known_since_year: 1929, kind: 'contemporary', source_id: null }], known_later: [], hidden_later_count: 1, is_demo: false,
  }],
};

describe('time machine', () => {
  it('shows only contemporary knowledge and declares what is hidden', async () => {
    const { calls } = mockApi({ 'GET /api/notifications': [], 'GET /api/history/timeline': timeline });
    renderApp('/time-machine?year=1931');
    expect(await screen.findByText('Crollo di Wall Street')).toBeInTheDocument();
    expect(screen.getByText('Vendite di panico.')).toBeInTheDocument();
    expect(screen.getByText(/Nascosto: conseguenze, 1 informazioni successive/)).toBeInTheDocument();
    expect(screen.getByText(/2 eventi successivi alla data sono nascosti/)).toBeInTheDocument();
    expect(calls.find((c) => c.url.startsWith('/api/history/timeline'))?.url).toContain('as_of_year=1931');
  });
});

const graph: GraphData = {
  nodes: [
    { id: 1, name: 'Keynes', entity_type: 'person', x: -1, y: 0, degree: 1, betweenness: 0, is_focus: false },
    { id: 2, name: 'FMI', entity_type: 'institution', x: 1, y: 0, degree: 1, betweenness: 0, is_focus: false },
  ],
  edges: [{ id: 9, source_entity_id: 1, target_entity_id: 2, relation_type: 'influenced', provenance: 'ai_hypothesis', source_id: null, chunk_id: null, evidence_note: '', confidence: 'low', start_year: null, ai_run_id: 3, evidence_label: '', created_at: '' }],
  stats: { entities: 2, relations: 1, shown_nodes: 2, shown_edges: 1, components: 1, by_provenance: { sourced: 0, user_hypothesis: 0, ai_hypothesis: 1 } },
};

describe('knowledge graph', () => {
  it('renders nodes and edges with provenance stats', async () => {
    mockApi({ 'GET /api/notifications': [], 'GET /api/graph/entities': [], 'GET /api/sources': [], 'GET /api/graph': graph });
    renderApp('/graph');
    expect(await screen.findByRole('img', { name: 'Grafo con 2 entità e 1 relazioni' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Keynes' })).toBeInTheDocument();
    expect(screen.getByText(/ipotesi AI 1/)).toBeInTheDocument();
  });

  it('shows an explicit empty state', async () => {
    mockApi({ 'GET /api/notifications': [], 'GET /api/graph/entities': [], 'GET /api/sources': [], 'GET /api/graph': { ...graph, nodes: [], edges: [] } });
    renderApp('/graph');
    expect(await screen.findByText(/Il grafo è vuoto/)).toBeInTheDocument();
  });
});
