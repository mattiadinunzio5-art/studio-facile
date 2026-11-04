import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { AskResult } from '../api/types';
import { AskResultView } from '../pages/ResearchArchive';
import { mockApi } from './fixtures';
import { renderApp } from './render';

const result: AskResult = {
  question: 'q',
  mode: 'local_extractive',
  provider: 'none',
  disclaimer: 'Modalità locale: nessun modello AI è stato usato.',
  claims: [
    { type: 'documented_fact', text: 'Il dollaro era convertibile in oro.', support: 'strong', coverage: 1, evidence: [11], note: '' },
    { type: 'missing', text: 'Nessun dato sul 1950.', support: 'none', coverage: 0, evidence: [], note: '' },
  ],
  passages: [{ chunk_id: 11, document_id: 1, document_title: 'Storia BW', page: 2, locator: 'p. 2', text: 'Il dollaro era convertibile in oro.', score: 1, support: 'strong', injection_flag: true, source_label: 'Storia BW [documento senza scheda bibliografica]' }],
};

describe('archive Q&A', () => {
  it('labels claim types, support and links evidence to passages', () => {
    render(<AskResultView result={result} />);
    expect(screen.getByText('Fatto documentato')).toBeInTheDocument();
    expect(screen.getByText('Dato mancante')).toBeInTheDocument();
    expect(screen.getAllByText('[1]').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('«Il dollaro era convertibile in oro.»')).toBeInTheDocument();
    expect(screen.getByText(/Possibili istruzioni nel testo/)).toBeInTheDocument();
    expect(screen.getByText(/nessun modello AI/)).toBeInTheDocument();
  });

  it('uploads a document as multipart form data', async () => {
    const { calls, fetchMock } = mockApi({
      'GET /api/notifications': [],
      'GET /api/documents': [],
      'POST /api/documents': { id: 1, title: 'Atlante', chunk_count: 4 },
    });
    renderApp('/documents');
    const file = new File(['testo'], 'atlante.txt', { type: 'text/plain' });
    await userEvent.upload(screen.getByLabelText(/File \(PDF/), file);
    await userEvent.selectOptions(screen.getAllByRole('combobox')[0], 'user_work');
    await userEvent.click(screen.getByRole('button', { name: /Importa$/ }));
    expect(await screen.findByText(/4 segmenti indicizzati/)).toBeInTheDocument();
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST');
    const body = post?.[1]?.body as FormData;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get('category')).toBe('user_work');
    expect(calls.length).toBeGreaterThan(0);
  });

  it('shows backend validation errors on the source form', async () => {
    mockApi({
      'GET /api/notifications': [],
      'GET /api/sources': [],
      'POST /api/sources': new Response(JSON.stringify({ error: { code: 'validation_error', message: 'Dati non validi.', details: [{ loc: ['body', 'doi'], msg: 'DOI non valido' }] } }), { status: 422 }),
    });
    renderApp('/bibliography');
    await userEvent.click(await screen.findByRole('button', { name: /Nuova fonte/ }));
    await userEvent.type(screen.getByLabelText('Titolo'), 'Un libro');
    await userEvent.type(screen.getByLabelText(/^DOI/), 'abc');
    await userEvent.click(screen.getByRole('button', { name: 'Salva fonte' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('DOI non valido');
  });
});
