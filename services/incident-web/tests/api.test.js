import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../src/api/index.js';

afterEach(() => vi.unstubAllGlobals());

function response(body, status = 200) {
  return new Response(body === null ? null : JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

describe('live API contract', () => {
  it('maps backend users and cited evidence to the UI boundary', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({
        id: 'b4dce92a-39b3-4695-b22b-6cb86b15b7ec',
        displayName: 'Morgan Lee',
        email: 'morgan.lee@example.com',
      }))
      .mockResolvedValueOnce(response({
        requestId: 'req-7f42a9',
        diagnosis: 'Connection saturation',
        confidence: 0.87,
        citations: [{
          id: 'RB-042',
          sourceType: 'runbook',
          source: 'Database connections',
          excerpt: 'Compare active connections with pool limits.',
          observedAt: null,
        }],
        recommendedHumanActions: ['Review pool limits.'],
        limitations: [],
      }));
    vi.stubGlobal('fetch', fetchMock);

    const user = await api.getCurrentUser();
    const analysis = await api.analyzeIncident({
      description: 'Checkout latency increased after the 14:00 release',
      service: 'checkout-api',
      timeWindow: 'Last 30 minutes',
    });

    expect(user).toMatchObject({ name: 'Morgan Lee', role: 'Operator' });
    expect(analysis.requestId).toBe('req-7f42a9');
    expect(analysis.citations[0]).toMatchObject({
      id: 'RB-042',
      type: 'runbook',
      evidence: 'Compare active connections with pool limits.',
      observedAt: 'Not timestamped',
    });
    expect(fetchMock).toHaveBeenLastCalledWith('/api/incidents/analyze', expect.objectContaining({
      credentials: 'include',
      method: 'POST',
    }));
  });

  it('uses structured backend error messages', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
      error: { code: 'UNAUTHORIZED', message: 'Email or password is incorrect.', details: null },
      requestId: 'req-auth',
    }, 401)));

    await expect(api.login({ email: 'morgan.lee@example.com', password: 'incorrect-pass' }))
      .rejects.toThrow('Email or password is incorrect.');
  });

  it('treats an unauthenticated current-user response as a signed-out session', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
      error: { code: 'UNAUTHORIZED', message: 'Authentication required', details: null },
      requestId: 'req-session',
    }, 401)));

    await expect(api.getCurrentUser()).resolves.toBeNull();
  });
});