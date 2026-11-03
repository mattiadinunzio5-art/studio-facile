import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { dashboard, mockApi, modules } from './fixtures';
import { renderApp } from './render';

describe('navigation', () => {
  it('lists all eight modules in the sidebar with their phase', async () => {
    mockApi({ 'GET /api/dashboard': dashboard, 'GET /api/notifications': [], 'GET /api/system/status': new Response('{}', { status: 500 }) });
    renderApp('/');
    const nav = screen.getByRole('complementary', { name: 'Navigazione principale' });
    for (const label of ['Historical Intelligence', 'Financial Intelligence', 'Time Machine', 'Knowledge Graph', 'Research War Room', 'Economic Laboratory', 'Research Studio', 'NEXUS Business']) {
      expect(within(nav).getByRole('link', { name: new RegExp(label) })).toBeInTheDocument();
    }
    expect(within(nav).getByRole('link', { name: /Financial Intelligence/ })).toHaveAttribute('href', '/modules/financial');
  });

  it('opens a module page that declares it is in preparation', async () => {
    mockApi({ 'GET /api/modules/financial': modules[1], 'GET /api/notifications': [] });
    renderApp('/modules/financial');
    expect(await screen.findByRole('heading', { name: 'Modulo B' })).toBeInTheDocument();
    expect(screen.getByRole('note')).toHaveTextContent(/in preparazione/i);
    expect(screen.getByRole('note')).toHaveTextContent(/Nessuna funzione, dato o risultato viene simulato/);
    expect(screen.getByText('Funzione prevista B')).toBeInTheDocument();
    expect(screen.getByText(/Nessuna funzionalità di questo modulo è ancora implementata/)).toBeInTheDocument();
  });

  it('global search navigates to results and shows unavailable scopes', async () => {
    mockApi({
      'GET /api/dashboard': dashboard,
      'GET /api/notifications': [],
      'GET /api/search': { query: 'gold', hits: [{ type: 'project', id: '1', title: 'Gold standard', snippet: '', url: '/projects?id=1' }], searched_scopes: ['progetti'], unavailable_scopes: ['documenti (Fase 2)'] },
    });
    renderApp('/');
    await userEvent.type(screen.getByRole('searchbox', { name: 'Ricerca globale' }), 'gold{enter}');
    expect(await screen.findByText('Gold standard')).toBeInTheDocument();
    expect(screen.getByText(/Non ancora ricercabili: documenti \(Fase 2\)/)).toBeInTheDocument();
  });

  it('shows a not-found page for unknown routes', () => {
    mockApi({ 'GET /api/notifications': [] });
    renderApp('/nope');
    expect(screen.getByRole('heading', { name: 'Pagina non trovata' })).toBeInTheDocument();
  });
});
