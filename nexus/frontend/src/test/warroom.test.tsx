import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { ResearchRun } from '../api/types';
import { mockApi } from './fixtures';
import { renderApp } from './render';

const run: ResearchRun = {
  id: 5, question: 'Cosa stabilì Bretton Woods?', status: 'awaiting_approval', mode: 'local', provider: 'none', model: '', project_id: null,
  plan: { method: 'estrazione dei termini (locale)' },
  evidence: [{ id: 'E1', kind: 'passage', label: 'bw, § 1', text: 'Il dollaro era convertibile in oro.', source: 'bw [senza scheda]', injection_flag: false, ref: { chunk_id: 1 } }],
  result: {
    abstract: '', method: 'Dossier compilato localmente (nessun testo generato).', limitations: ['Tutti i passaggi provengono da un solo documento.'],
    claims: [{ type: 'documented_fact', text: 'Il dollaro era convertibile in oro.', support: 'strong', coverage: 1, evidence: [1], note: '' }],
    proposed_relations: [{ source: 'Bretton Woods', target: 'FMI', relation_type: 'caused', evidence: ['E1'], rationale: 'creazione' }],
  },
  error: null, decision_note: '', decided_at: null, finished_at: '2026-11-03T10:00:00Z', created_at: '2026-11-03T10:00:00Z',
  steps: [
    { ordinal: 1, agent: 'planner', status: 'executed', executor: 'local', provider: 'nexus-local', model: '', summary: 'Query: x', output: {}, issues: [], error: null, duration_ms: 1, input_tokens: null, output_tokens: null },
    { ordinal: 2, agent: 'economist', status: 'skipped', executor: 'none', provider: '', model: '', summary: 'Non eseguito: richiede un provider AI configurato.', output: {}, issues: [], error: null, duration_ms: 0, input_tokens: null, output_tokens: null },
    { ordinal: 3, agent: 'skeptic', status: 'executed', executor: 'local', provider: 'nexus-local', model: '', summary: 'Controanalisi a regole', output: { rule_checks: ['Fonte unica.'] }, issues: [], error: null, duration_ms: 1, input_tokens: null, output_tokens: null },
  ],
};

describe('war room', () => {
  it('labels local, skipped and rule-based steps honestly', async () => {
    mockApi({ 'GET /api/notifications': [], 'GET /api/research/runs/5': run });
    renderApp('/war-room/runs/5');
    const econ = await screen.findByTestId('step-economist');
    expect(within(econ).getByText('Non eseguito')).toBeInTheDocument();
    expect(within(screen.getByTestId('step-planner')).getByText('Motore locale')).toBeInTheDocument();
    expect(screen.getByText('Fonte unica.')).toBeInTheDocument();
    expect(screen.getByText(/nessun testo generato/)).toBeInTheDocument();
  });

  it('sends the approval with the selected AI relation proposals', async () => {
    const { calls } = mockApi({
      'GET /api/notifications': [],
      'GET /api/research/runs/5': run,
      'POST /api/research/runs/5/decision': { ...run, status: 'approved', decided_at: '2026-11-03T11:00:00Z' },
    });
    renderApp('/war-room/runs/5');
    await userEvent.click(await screen.findByRole('checkbox'));
    await userEvent.click(screen.getByRole('button', { name: 'Approva' }));
    expect(await screen.findByText('Approvata')).toBeInTheDocument();
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ decision: 'approve', note: '', accepted_relations: [0] });
  });
});
