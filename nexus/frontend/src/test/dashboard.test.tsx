import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { dashboard, mockApi } from './fixtures';
import { renderApp } from './render';

const base = { 'GET /api/notifications': [], 'GET /api/system/status': new Response('{}', { status: 500 }) };

describe('dashboard', () => {
  it('renders every widget, with unavailable sections declared explicitly', async () => {
    mockApi({ ...base, 'GET /api/dashboard': dashboard });
    renderApp('/');
    expect(await screen.findByTestId('widget-modules')).toBeInTheDocument();
    for (const id of ['sources', 'searches', 'projects', 'indicators', 'events', 'reports', 'ai', 'notifications']) {
      expect(screen.getByTestId(`widget-${id}`)).toBeInTheDocument();
    }
    expect(within(screen.getByTestId('widget-indicators')).getByText('Non disponibile — previsto in Fase 4')).toBeInTheDocument();
    expect(within(screen.getByTestId('widget-events')).getByText('Non disponibile — previsto in Fase 3')).toBeInTheDocument();
    expect(within(screen.getByTestId('widget-reports')).getByText('Non disponibile — previsto in Fase 7')).toBeInTheDocument();
    expect(within(screen.getByTestId('widget-projects')).getByText('Crisi del 1929')).toBeInTheDocument();
    expect(within(screen.getByTestId('widget-modules')).getAllByText(/In preparazione · Fase/)).toHaveLength(8);
    expect(within(screen.getByTestId('widget-ai')).getByText(/Esecuzioni AI registrate: 0/)).toBeInTheDocument();
  });

  it('hides widgets listed as hidden in the saved layout', async () => {
    mockApi({ ...base, 'GET /api/dashboard': { ...dashboard, layout: { ...dashboard.layout, hidden: ['events'] } } });
    renderApp('/');
    await screen.findByTestId('widget-modules');
    expect(screen.queryByTestId('widget-events')).not.toBeInTheDocument();
  });

  it('shows an error with retry when the backend is offline', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    renderApp('/');
    expect(await screen.findByText(/Backend non raggiungibile/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Riprova' })).toBeInTheDocument();
    expect(await screen.findByText('Backend offline')).toBeInTheDocument();
  });

  it('saves a customised layout to the backend', async () => {
    const { calls } = mockApi({
      ...base,
      'GET /api/dashboard': dashboard,
      'PUT /api/dashboard/layout': (_u: string, init?: RequestInit) => JSON.parse(String(init?.body)),
    });
    renderApp('/');
    await userEvent.click(await screen.findByRole('button', { name: /Personalizza/ }));
    const editor = screen.getByTestId('layout-editor');
    await userEvent.click(within(editor).getByRole('button', { name: 'Nascondi Eventi storici' }));
    await userEvent.click(within(editor).getByRole('button', { name: 'Sposta giù Aree di NEXUS' }));
    await userEvent.click(within(editor).getByRole('button', { name: 'Salva layout' }));
    const put = calls.find((c) => c.method === 'PUT');
    expect(put?.body).toMatchObject({ hidden: ['events'] });
    expect((put?.body as { order: string[] }).order.slice(0, 2)).toEqual(['sources', 'modules']);
    expect(screen.queryByTestId('widget-events')).not.toBeInTheDocument();
  });
});
