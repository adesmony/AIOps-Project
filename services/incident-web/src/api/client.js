const apiBaseUrl = (import.meta.env.API_BASE_URL || '').replace(/\/$/, '');

async function request(path, options = {}, notifyUnauthorized = true) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      ...(options.body ? { 'content-type': 'application/json' } : {}),
      ...options.headers,
    },
  });

  if (response.status === 401 && notifyUnauthorized && typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('api:unauthorized'));
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const details = Array.isArray(body?.error?.details) ? body.error.details : [];
    const validationMessages = details
      .filter((detail) => typeof detail.message === 'string')
      .map((detail) => `${detail.field || 'Request'}: ${detail.message}`);
    const message = body?.error?.message || `Request failed with status ${response.status}`;
    const error = new Error(validationMessages.length ? `${message}. ${validationMessages.join('; ')}` : message);
    error.status = response.status;
    throw error;
  }

  return response.status === 204 ? null : response.json();
}

function mapUser(user) {
  return {
    id: user.id,
    name: user.displayName,
    email: user.email,
    role: 'Operator',
  };
}

function mapAnalysis(analysis) {
  return {
    ...analysis,
    citations: analysis.citations.map((citation) => ({
      id: citation.id,
      type: citation.sourceType,
      source: citation.source,
      evidence: citation.excerpt,
      observedAt: citation.observedAt || 'Not timestamped',
      rowId: citation.rowId,
      issueId: citation.issueId,
      relevance: citation.relevance,
    })),
  };
}

/** @type {import('./types.js').ApiClient} */
export const liveClient = {
  async createAccount(input) {
    const user = await request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        displayName: input.name,
        email: input.email,
        password: input.password,
      }),
    });
    return mapUser(user);
  },

  async login(input) {
    const user = await request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(input),
    });
    return mapUser(user);
  },

  async logout() {
    await request('/api/auth/logout', { method: 'POST' });
  },

  async getCurrentUser() {
    try {
      return mapUser(await request('/api/auth/me', {}, false));
    } catch (error) {
      if (error instanceof Error && error.status === 401) return null;
      throw error;
    }
  },

  async analyzeIncident(input) {
    return mapAnalysis(await request('/api/incidents/analyze', {
      method: 'POST',
      body: JSON.stringify(input),
    }));
  },

  async getMetrics() {
    return request('/api/incidents/metrics');
  },

  async getHealth() {
    return request('/api/health');
  },
};