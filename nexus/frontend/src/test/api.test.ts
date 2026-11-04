import { describe, expect, it, vi } from 'vitest';
import { api, ApiError } from '../api/client';
import { mockApi } from './fixtures';

describe('api client', () => {
  it('maps backend error payloads to ApiError', async () => {
    mockApi({
      'DELETE /api/projects/1': new Response(JSON.stringify({ error: { code: 'confirmation_required', message: 'Serve conferma' } }), { status: 409 }),
    });
    await expect(api.deleteProject(1)).rejects.toMatchObject({ status: 409, code: 'confirmation_required', message: 'Serve conferma' });
  });

  it('reports an unreachable backend as network_error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const err = await api.health().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe('network_error');
  });

  it('always sends confirm=true on explicit deletion and handles 204', async () => {
    const { calls } = mockApi({ 'DELETE /api/projects/3': undefined });
    await expect(api.deleteProject(3)).resolves.toBeUndefined();
    expect(calls[0].url).toBe('/api/projects/3?confirm=true');
  });
});
