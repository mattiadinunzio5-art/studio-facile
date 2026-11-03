import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { SeriesDetail } from '../api/types';
import { mergePoints, TimeChart } from '../components/charts';
import { mockApi } from './fixtures';
import { renderApp } from './render';

const series: SeriesDetail = {
  id: 3, name: 'Inflation, consumer prices (annual %) — Italy', category: 'inflation', country: 'Italy', connector: 'world-bank',
  source_series_id: 'FP.CPI.TOTL.ZG:ITA', source_label: 'World Bank, WDI', source_url: 'https://data.worldbank.org', license_note: 'CC BY 4.0 (verificare)',
  unit: 'annual %', frequency: 'A', start_date: '2022-01-01', end_date: '2024-01-01', source_last_updated: '2026-10-08', retrieved_at: '2026-11-03T10:00:00Z',
  from_cache: true, observation_count: 3, missing_count: 1, description: '', is_demo: false, last_value: 0.98, last_date: '2024-01-01', created_at: '',
  observations: [{ date: '2022-01-01', value: 8.2 }, { date: '2023-01-01', value: null }, { date: '2024-01-01', value: 0.98 }], import_warnings: [],
};

describe('charts', () => {
  it('merges series by date and offers a table view with missing values shown as —', async () => {
    const rows = mergePoints({ a: [{ date: '2020', value: 1 }], b: [{ date: '2020', value: 2 }, { date: '2021', value: null }] });
    expect(rows).toEqual([{ date: '2020', a: 1, b: 2 }, { date: '2021', b: null }]);
    render(<TimeChart data={rows} series={[{ key: 'a', label: 'A' }, { key: 'b', label: 'B' }]} ariaLabel="test" />);
    await userEvent.click(screen.getByRole('button', { name: 'Mostra tabella' }));
    const table = screen.getByRole('table');
    expect(within(table).getAllByRole('row')).toHaveLength(3);
    expect(within(table).getAllByText('—').length).toBeGreaterThan(0);
  });
});

describe('financial pages', () => {
  it('shows provenance, cache warning and analysis warnings', async () => {
    mockApi({
      'GET /api/notifications': [],
      'GET /api/finance/series/3/analysis': {
        series_id: 3, frequency: 'A', metrics_basis: 'rates', summary: { valid: 2, missing: 1, mean: 4.59, min: 0.98, max: 8.2, std: 5.1 },
        changes: { count: 1, mean: -7.22, std: null }, returns_series: [], moving_averages: {}, anomalies: [], timeseries: { note: 'Test ADF e autocorrelazione richiedono almeno 12 osservazioni.' },
        warnings: ['1 osservazioni mancanti: escluse dai calcoli, non interpolate.'], source: { label: '', url: '', unit: '', frequency: 'A', last_updated: '', retrieved_at: null },
      },
      'GET /api/finance/series/3': series,
    });
    renderApp('/financial/series/3');
    expect(await screen.findByRole('heading', { name: series.name })).toBeInTheDocument();
    expect(await screen.findByText(/escluse dai calcoli, non interpolate/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Apri pannello contestuale' }));
    const panel = screen.getByRole('complementary', { name: 'Pannello contestuale' });
    expect(within(panel).getByText(/servito dalla cache/)).toBeInTheDocument();
    expect(within(panel).getByText('2026-10-08')).toBeInTheDocument();
    expect(screen.getByText(/richiedono almeno 12 osservazioni/)).toBeInTheDocument();
  });

  it('imports a preset series', async () => {
    const { calls } = mockApi({
      'GET /api/notifications': [],
      'GET /api/finance/series': [],
      'GET /api/finance/presets': [{ connector: 'world-bank', label: 'Inflazione — Italia', category: 'inflation', params: { indicator: 'FP.CPI.TOTL.ZG', country: 'ITA' } }],
      'POST /api/finance/series/import': series,
    });
    renderApp('/financial');
    await userEvent.click(await screen.findByRole('button', { name: 'Importa serie' }));
    await userEvent.selectOptions(await screen.findByLabelText(/^Serie/), '0');
    await userEvent.click(screen.getAllByRole('button', { name: 'Importa serie' }).at(-1)!);
    expect(await screen.findByText(/dalla cache: fonte non raggiungibile/)).toBeInTheDocument();
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ connector: 'world-bank', category: 'inflation', indicator: 'FP.CPI.TOTL.ZG', country: 'ITA' });
  });

  it('surfaces the explicit-resampling requirement when comparing', async () => {
    mockApi({
      'GET /api/notifications': [],
      'GET /api/finance/series': [series, { ...series, id: 4, name: 'Mensile', frequency: 'M' }],
      'POST /api/finance/compare': new Response(JSON.stringify({ error: { code: 'validation_error', message: 'Le serie hanno frequenze diverse (A, M). Scegli esplicitamente una frequenza comune.' } }), { status: 422 }),
    });
    renderApp('/financial/compare');
    for (const cb of await screen.findAllByRole('checkbox')) await userEvent.click(cb);
    await userEvent.click(screen.getByRole('button', { name: 'Confronta' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/frequenze diverse \(A, M\)/);
  });
});

describe('credentials', () => {
  it('never displays a stored secret, only its hint', async () => {
    mockApi({
      'GET /api/notifications': [],
      'GET /api/system/status': { version: '0.1', environment: 'test', database: 'SQLite', database_ok: true, ai_mode: 'local', ai_provider: { id: 'none', name: 'Nessuno', kind: 'local', requires_credentials: false, implemented: true, notes: '' }, ai_providers: [], server_time: '' },
      'GET /api/credentials': [{ provider: 'fred', configured: true, hint: '…7890', config: {}, updated_at: '' }],
    });
    renderApp('/settings');
    expect(await screen.findByText('Configurata …7890')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Modifica' }));
    expect(screen.getByLabelText('Chiave API')).toHaveValue('');
    expect(screen.getByLabelText('Chiave API')).toHaveAttribute('type', 'password');
  });
});
