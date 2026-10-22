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
  it('transports screenshot bytes and preferences with authenticated requests', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ citations: [] }));
    vi.stubGlobal('fetch', fetchMock);
    const input = { description: 'Inspect the attached error',
      image: { dataUrl: 'data:image/png;base64,cG5n' },
      userType: 'developer', responseStyle: 'detailed' };
    await api.analyzeIncident(input);
    const options = fetchMock.mock.calls[0][1];
    expect(options.credentials).toBe('include');
    expect(JSON.parse(options.body)).toEqual(input);
  });
  it('shows field-specific validation details', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
      error: { code: 'VALIDATION_ERROR', message: 'Request validation failed',
        details: [{ field: 'description', message: 'String should have at least 10 characters' }] },
      requestId: 'validation-test',
    }, 422)));
    await expect(api.analyzeIncident({ description: 'timeout' }))
      .rejects.toThrow('description: String should have at least 10 characters');
  });
  it('preserves knowledge provenance, prevention and limitations', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
      requestId: 'csv-test', diagnosis: 'Timeout', confidence: 0.4,
      citations: [{ id: 'csv-1', sourceType: 'knowledge', source: 'errors.csv / row 1 / ISSUE-1',
        excerpt: 'root_cause: timeout', rowId: '1', issueId: 'ISSUE-1', relevance: 0.05 }],
      recommendedHumanActions: ['Review'], prevention: ['Monitor'], limitations: ['Historical example'],
    })));
    const result = await api.analyzeIncident({ description: 'A timeout occurred' });
    expect(result.citations[0]).toMatchObject({ type: 'knowledge', rowId: '1', issueId: 'ISSUE-1' });
    expect(result.prevention).toEqual(['Monitor']);
    expect(result.limitations).toEqual(['Historical example']);
  });
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