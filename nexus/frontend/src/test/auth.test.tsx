import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { dashboard, mockApi } from './fixtures';
import { renderApp } from './render';

const user = { id: 1, email: 'anna@example.org', display_name: 'Anna', role: 'admin', plan: 'free', is_local: false };

describe('authentication (multi-user mode)', () => {
  it('shows the login screen, logs in and sends the CSRF header', async () => {
    let logged = false;
    const { fetchMock } = mockApi({
      'GET /api/auth/config': { mode: 'multi', allow_registration: true },
      'GET /api/me': () => (logged ? user : new Response(JSON.stringify({ error: { code: 'unauthorized', message: 'Accesso richiesto.' } }), { status: 401 })),
      'POST /api/auth/login': () => { logged = true; return user; },
      'GET /api/dashboard': dashboard,
      'GET /api/notifications': [],
    });
    renderApp('/');
    expect(await screen.findByRole('heading', { name: 'Accedi al tuo account' })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Email'), 'anna@example.org');
    await userEvent.type(screen.getByLabelText('Password'), 'Archivio-Storico-2026');
    await userEvent.click(screen.getByRole('button', { name: 'Accedi' }));
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Amministrazione/ })).toBeInTheDocument();
    const loginCall = fetchMock.mock.calls.find(([u, i]) => String(u) === '/api/auth/login' && i?.method === 'POST');
    expect((loginCall?.[1]?.headers as Record<string, string>)['X-Nexus-Client']).toBe('web');
  });

  it('shows a readable error on wrong credentials', async () => {
    mockApi({
      'GET /api/auth/config': { mode: 'multi', allow_registration: false },
      'GET /api/me': new Response('{}', { status: 401 }),
      'POST /api/auth/login': new Response(JSON.stringify({ error: { code: 'unauthorized', message: 'Email o password non corretti.' } }), { status: 401 }),
    });
    renderApp('/');
    await userEvent.type(await screen.findByLabelText('Email'), 'x@example.org');
    await userEvent.type(screen.getByLabelText('Password'), 'sbagliata');
    await userEvent.click(screen.getByRole('button', { name: 'Accedi' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Email o password non corretti.');
    expect(screen.queryByText(/Registrati/)).not.toBeInTheDocument();
  });
});
