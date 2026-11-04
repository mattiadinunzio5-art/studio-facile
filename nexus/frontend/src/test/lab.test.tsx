import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { SimulationRun } from '../api/types';
import { mockApi } from './fixtures';
import { renderApp } from './render';

const sim: SimulationRun = {
  id: 9, kind: 'debt', title: 'Dinamica del debito pubblico', params: {}, counterfactual: true, created_at: '2026-11-03T10:00:00Z',
  result: {
    kind: 'debt', title: 'Dinamica del debito pubblico', hypotheses: ['Nessun effetto di retroazione'], variables: { d: 'debito/PIL' }, parameters: { d0: 135 },
    method: 'd(t+1) = d(t)·(1+r)/(1+g) − pb', data_used: ["Parametri inseriti dall'utente"], limitations: ['Modello contabile'], counterfactual: true,
    label: 'Scenario ipotetico (controfattuale): non è una ricostruzione della storia.', warnings: [],
    results: { years: [0, 1], baseline: { debt: [135, 136] }, debt_stabilizing_primary_balance: 1.3 },
  },
};

describe('economic lab', () => {
  it('shows the counterfactual label and the full methodological record', async () => {
    mockApi({ 'GET /api/notifications': [], 'GET /api/lab/simulations/9': sim });
    renderApp('/lab/simulations/9');
    expect(await screen.findByRole('note')).toHaveTextContent('controfattuale');
    for (const t of ['Nessun effetto di retroazione', 'd(t+1) = d(t)·(1+r)/(1+g) − pb', "Parametri inseriti dall'utente", 'Modello contabile']) {
      expect(screen.getByText(t)).toBeInTheDocument();
    }
    expect(screen.getByText(/1,3% del PIL/)).toBeInTheDocument();
  });

  it('submits a debt simulation with an explicit rate shock', async () => {
    const { calls } = mockApi({ 'GET /api/notifications': [], 'GET /api/lab/simulations': [], 'GET /api/finance/series': [], 'POST /api/lab/simulations/debt': sim, 'GET /api/lab/simulations/9': sim });
    renderApp('/lab');
    await userEvent.click(await screen.findByRole('button', { name: /Esegui/ }));
    expect(await screen.findByRole('note')).toBeInTheDocument();
    const body = calls.find((c) => c.method === 'POST')?.body as Record<string, unknown>;
    expect(body).toMatchObject({ d0: 135, rate_shock: 0.01, crisis: null, stochastic: null, counterfactual: false });
  });
});
