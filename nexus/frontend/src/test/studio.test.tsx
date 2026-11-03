import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { Briefing, Report } from '../api/types';
import { mockApi } from './fixtures';
import { renderApp } from './render';

const keys = ['abstract', 'introduction', 'methodology', 'analysis', 'evidence', 'counterarguments', 'conclusions', 'limitations'];
const report: Report = {
  id: 2, title: 'Debito pubblico', subtitle: '', author: '', status: 'draft', project_id: null, source_ids: [], origin: 'manual', contains_ai_text: false,
  created_at: '', updated_at: '2026-11-03T10:00:00Z',
  sections: keys.map((k, i) => ({ id: i + 1, ordinal: i, key: k, title: k, body: k === 'analysis' ? 'Testo [@1]' : '', embeds: [] })),
};
const check = { ready: false, empty_sections: ['abstract'], invalid_citations: [7], unverified_sources: [], cited_sources: 1, bibliography_size: 1, embed_problems: [], warnings: [] };

describe('research studio', () => {
  it('saves an edited section and blocks approval with a readable error', async () => {
    const { calls } = mockApi({
      'GET /api/notifications': [], 'GET /api/sources': [], 'GET /api/reports/2/check': check, 'GET /api/reports/2': report,
      'PUT /api/reports/2/sections/1': { ...report, sections: report.sections.map((s) => (s.id === 1 ? { ...s, body: 'Nuovo abstract' } : s)) },
      'POST /api/reports/2/status': new Response(JSON.stringify({ error: { code: 'validation_error', message: 'Il rapporto non può essere approvato.' } }), { status: 422 }),
    });
    renderApp('/studio/reports/2');
    const abstract = await screen.findByTestId('section-abstract');
    await userEvent.type(within(abstract).getByRole('textbox'), 'Nuovo abstract');
    await userEvent.click(within(abstract).getByRole('button', { name: 'Salva sezione' }));
    expect(calls.find((c) => c.method === 'PUT')?.body).toEqual({ body: 'Nuovo abstract', embeds: [] });
    await userEvent.click(screen.getByRole('button', { name: 'Approva' }));
    expect(await screen.findByText('Il rapporto non può essere approvato.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /PDF/ })).toHaveAttribute('href', '/api/reports/2/export/pdf');
  });

  it('renders a briefing with dates, sources and explicit empty sections', async () => {
    const b: Briefing = { id: 1, trigger: 'manual', created_at: '', content: { date: '2026-11-03', generated_at: '', refresh: [], notes: [], sections: [
      { key: 'macro', title: 'Indicatori macroeconomici', empty_reason: null, items: [{ title: 'Inflazione Italia', value: 1.5, unit: '%', date: '2025-01-01', source: 'World Bank', flags: ['Ultimo dato del 2025-01-01: la serie potrebbe non essere aggiornata.'] }] },
      { key: 'geopolitics', title: 'Eventi geopolitici', items: [], empty_reason: 'NEXUS non dispone di una fonte di notizie correnti.' },
    ] } };
    mockApi({ 'GET /api/notifications': [], 'GET /api/briefings': [b] });
    renderApp('/briefing');
    const el = await screen.findByTestId('briefing');
    expect(within(el).getByText(/Fonte: World Bank/)).toBeInTheDocument();
    expect(within(el).getByText(/Data: 2025-01-01/)).toBeInTheDocument();
    expect(within(el).getByText(/potrebbe non essere aggiornata/)).toBeInTheDocument();
    expect(within(el).getByText('NEXUS non dispone di una fonte di notizie correnti.')).toBeInTheDocument();
  });
});
