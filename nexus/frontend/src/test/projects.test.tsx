import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ProjectForm } from '../pages/Projects';
import { mockApi, project } from './fixtures';
import { renderApp } from './render';

describe('ProjectForm', () => {
  it('rejects an empty title without calling the API', async () => {
    const onSubmit = vi.fn();
    render(<ProjectForm submitLabel="Crea" onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText('Titolo'), '   ');
    await userEvent.click(screen.getByRole('button', { name: 'Crea' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Il titolo è obbligatorio.');
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits trimmed values', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ProjectForm submitLabel="Crea" onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText('Titolo'), '  Bretton Woods ');
    await userEvent.click(screen.getByRole('button', { name: 'Crea' }));
    expect(onSubmit).toHaveBeenCalledWith({ title: 'Bretton Woods', description: '' });
  });

  it('shows backend validation errors', async () => {
    const { ApiError } = await import('../api/client');
    const onSubmit = vi.fn().mockRejectedValue(new ApiError(422, 'validation_error', 'Dati non validi.'));
    render(<ProjectForm submitLabel="Crea" onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText('Titolo'), 'X');
    await userEvent.click(screen.getByRole('button', { name: 'Crea' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Dati non validi.');
  });
});

describe('Projects page', () => {
  it('creates a project and reloads the list', async () => {
    let list = [] as (typeof project)[];
    const { calls } = mockApi({
      'GET /api/notifications': [],
      'GET /api/projects': () => list,
      'POST /api/projects': (_u: string, init?: RequestInit) => {
        const created = { ...project, ...JSON.parse(String(init?.body)) };
        list = [created];
        return created;
      },
    });
    renderApp('/projects');
    expect(await screen.findByText(/Nessun progetto attivo/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Nuovo progetto/ }));
    await userEvent.type(screen.getByLabelText('Titolo'), 'Debito pubblico');
    await userEvent.click(screen.getByRole('button', { name: 'Crea progetto' }));
    expect(await screen.findByRole('heading', { name: 'Debito pubblico' })).toBeInTheDocument();
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ title: 'Debito pubblico', description: '' });
  });

  it('requires explicit confirmation before deleting', async () => {
    const { calls } = mockApi({
      'GET /api/notifications': [],
      'GET /api/projects': [project],
      'DELETE /api/projects/7': undefined,
    });
    renderApp('/projects');
    await userEvent.click(await screen.findByRole('button', { name: 'Elimina Crisi del 1929' }));
    const dialog = screen.getByRole('alertdialog');
    expect(dialog).toHaveTextContent(/non è reversibile/);
    await userEvent.click(screen.getByRole('button', { name: 'Annulla' }));
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false);

    await userEvent.click(screen.getByRole('button', { name: 'Elimina Crisi del 1929' }));
    await userEvent.click(screen.getByRole('button', { name: 'Elimina definitivamente' }));
    expect(calls.find((c) => c.method === 'DELETE')?.url).toBe('/api/projects/7?confirm=true');
  });
});
