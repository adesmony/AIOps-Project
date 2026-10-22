import '@picocss/pico/css/pico.min.css';
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  BookOpen,
  Check,
  ChevronRight,
  CircleUserRound,
  Clock3,
  CloudCog,
  Database,
  FileKey,
  FileSearch,
  Gauge,
  LayoutDashboard,
  LogIn,
  LogOut,
  MessageSquare,
  Moon,
  Paperclip,
  RefreshCw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sun,
  UserPlus,
  createIcons,
} from 'lucide';
import { api } from './api/index.js';
import { readAttachment } from './attachments.js';
import './styles.css';

const app = document.querySelector('#app');
const iconSet = {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  BookOpen,
  Check,
  ChevronRight,
  CircleUserRound,
  Clock3,
  CloudCog,
  Database,
  FileKey,
  FileSearch,
  Gauge,
  LayoutDashboard,
  LogIn,
  LogOut,
  MessageSquare,
  Moon,
  Paperclip,
  RefreshCw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sun,
  UserPlus,
};

const state = {
  route: 'workspace',
  activeView: 'dashboard',
  user: null,
  metrics: null,
  metricsStatus: 'loading',
  messages: [{ role: 'assistant', text: 'Describe an incident and I will search the evidence database for a grounded response.' }],
  attachment: null,
  analysis: null,
  analysisStatus: 'loading',
  error: '',
  activeTab: 'evidence',
  theme: localStorage.getItem('app-theme') || 'system',
  preferences: JSON.parse(localStorage.getItem('incident-preferences') || '{"userType":"operator","responseStyle":"concise","source":"database"}'),
  form: {
    description: 'Checkout latency increased after the 14:00 release',
    service: 'checkout-api',
    timeWindow: 'Last 30 minutes',
  },
};

function icon(name, label = '') {
  const title = label ? ` aria-label="${label}"` : ' aria-hidden="true"';
  const iconName = name
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .replace(/([A-Za-z])(\d)/g, '$1-$2')
    .toLowerCase();
  return `<i data-lucide="${iconName}"${title}></i>`;
}

function refreshIcons() {
  createIcons({ icons: iconSet, attrs: { 'stroke-width': 1.8 } });
}

function effectiveTheme() {
  if (state.theme !== 'system') return state.theme;
  return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme() {
  document.documentElement.dataset.theme = effectiveTheme();
}

function cycleTheme() {
  const themes = ['system', 'light', 'dark'];
  state.theme = themes[(themes.indexOf(state.theme) + 1) % themes.length];
  localStorage.setItem('app-theme', state.theme);
  applyTheme();
  render();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function confidenceLabel(value) {
  if (value >= 0.85) return 'High';
  if (value >= 0.7) return 'Moderate';
  return 'Low';
}

function header() {
  const themeIcon = effectiveTheme() === 'dark' ? 'Sun' : 'Moon';
  return `
    <header class="app-header">
      <nav class="header-nav container-fluid" aria-label="Application">
        <ul>
          <li class="brand-mark">${icon('Activity')}<strong>Incident Analysis</strong></li>
          <li><span class="environment-badge">READ ONLY</span></li>
        </ul>
        <ul>
          <li>
            <button class="icon-button secondary outline" id="theme-toggle" title="Theme: ${state.theme}" aria-label="Change color theme">
              ${icon(themeIcon)}
            </button>
          </li>
          <li class="user-summary">
            ${icon('CircleUserRound')}
            <span><strong>${escapeHtml(state.user.name)}</strong><small>${escapeHtml(state.user.role)}</small></span>
          </li>
          <li><button class="secondary outline compact-button" id="logout-button">${icon('LogOut')} Log out</button></li>
        </ul>
      </nav>
    </header>`;
}

function incidentForm() {
  const descriptionLength = state.form.description.trim().length;
  const valid = descriptionLength >= 20;
  return `
    <article class="incident-panel">
      <header class="panel-heading">
        <span class="section-icon">${icon('FileSearch')}</span>
        <hgroup>
          <h1>Analyze incident evidence</h1>
          <p>Retrieve bounded runbooks and operational signals for a read-only diagnosis.</p>
        </hgroup>
      </header>
      <form id="incident-form" novalidate>
        <label for="description">Incident description</label>
        <textarea id="description" name="description" rows="4" aria-invalid="${valid ? 'false' : 'true'}" aria-describedby="description-help">${escapeHtml(state.form.description)}</textarea>
        <small id="description-help" class="validation-message ${valid ? 'valid' : 'invalid'}">
          ${icon(valid ? 'Check' : 'AlertTriangle')} ${valid ? 'Description is ready for analysis.' : 'Enter at least 20 characters.'}
        </small>

        <div class="filter-grid">
          <label for="service">Service
            <select id="service" name="service">
              <option value="checkout-api" ${state.form.service === 'checkout-api' ? 'selected' : ''}>checkout-api</option>
              <option value="payments-worker" ${state.form.service === 'payments-worker' ? 'selected' : ''}>payments-worker</option>
              <option value="catalog-api" ${state.form.service === 'catalog-api' ? 'selected' : ''}>catalog-api</option>
            </select>
          </label>
          <label for="time-window">Time window
            <select id="time-window" name="timeWindow">
              <option ${state.form.timeWindow === 'Last 30 minutes' ? 'selected' : ''}>Last 30 minutes</option>
              <option ${state.form.timeWindow === 'Last 45 minutes' ? 'selected' : ''}>Last 45 minutes</option>
              <option ${state.form.timeWindow === 'Last 2 hours' ? 'selected' : ''}>Last 2 hours</option>
            </select>
          </label>
        </div>
        <button type="submit" ${valid ? '' : 'disabled'}>${icon('Search')} Analyze cited evidence</button>
      </form>
      <footer class="safety-note">
        ${icon('ShieldCheck')}
        <span><strong>Human-in-the-loop</strong> This workspace retrieves and recommends. It cannot execute remediation.</span>
      </footer>
    </article>`;
}

function loadingState() {
  return `
    <article class="state-panel" aria-live="polite" aria-busy="true">
      <progress></progress>
      <h2>Retrieving runbooks and operational evidence</h2>
      <p>Correlating bounded sources for ${escapeHtml(state.form.service)}. No action is being executed.</p>
      <div class="skeleton-lines" aria-hidden="true"><span></span><span></span><span></span></div>
    </article>`;
}

function errorState() {
  return `
    <article class="state-panel error-panel" role="alert">
      <span class="state-icon">${icon('AlertTriangle')}</span>
      <h2>Analysis unavailable</h2>
      <p>${escapeHtml(state.error)}</p>
      <button id="retry-button" class="outline">${icon('RefreshCw')} Retry evidence analysis</button>
    </article>`;
}

function emptyState() {
  return `
    <article class="state-panel empty-panel">
      <span class="state-icon">${icon('FileSearch')}</span>
      <h2>No related incidents found</h2>
      <p>No evidence matched the selected service/window. Broaden the time window or clarify the incident description.</p>
      <button id="broaden-button" class="outline">${icon('Clock3')} Use last 2 hours</button>
    </article>`;
}

function citationIcon(type) {
  return type === 'runbook' ? 'BookOpen' : type === 'metric' ? 'Gauge' : 'CloudCog';
}

function evidenceContent(analysis) {
  if (!analysis.citations.length) {
    return `<div class="inline-empty">${icon('FileSearch')} No cited evidence is available for this preview case.</div>`;
  }
  return `
    <div class="citation-list">
      ${analysis.citations.map((citation) => `
        <article class="citation-row">
          <span class="citation-type-icon">${icon(citationIcon(citation.type))}</span>
          <div>
            <header>
              <a href="#citation-${escapeHtml(citation.id)}" id="citation-${escapeHtml(citation.id)}">${escapeHtml(citation.id)}</a>
              <span class="source-type">${escapeHtml(citation.type)}</span>
              <small>${escapeHtml(citation.observedAt)}</small>
            </header>
            <strong>${escapeHtml(citation.source)}</strong>
            <p><code>${escapeHtml(citation.evidence)}</code></p>
          </div>
        </article>`).join('')}
    </div>`;
}

function patternsContent() {
  const patterns = [
    ['checkout-api', 'Last 30 minutes', 'PostgreSQL connection-pool saturation is queuing requests during traffic bursts', '0.87'],
    ['payments-worker', 'Last 2 hours', 'Message processing exceeds the lock-renewal window and redelivers in-flight events', '0.79'],
    ['catalog-api', 'Last 45 minutes', 'Recent configuration drift reduced healthy upstream endpoints below expected capacity', '0.72'],
  ];
  return `
    <figure class="patterns-table">
      <table>
        <thead><tr><th>Service</th><th>Window</th><th>Representative diagnosis</th><th>Confidence</th></tr></thead>
        <tbody>${patterns.map(([service, window, diagnosis, confidence]) => `
          <tr><td><code>${service}</code></td><td>${window}</td><td>${diagnosis}</td><td>${confidence}</td></tr>`).join('')}
        </tbody>
      </table>
    </figure>`;
}

function dataState() {
  const analysis = state.analysis;
  const percentage = Math.round(analysis.confidence * 100);
  return `
    <section class="analysis-result" aria-live="polite">
      <article class="diagnosis-panel">
        <header class="result-meta">
          <span class="status-chip">${icon('Check')} Analysis complete</span>
          <span>Request ID <code>${escapeHtml(analysis.requestId)}</code></span>
        </header>
        <div class="diagnosis-grid">
          <div>
            <p class="eyebrow">Structured diagnosis</p>
            <h2>${escapeHtml(analysis.diagnosis)}</h2>
          </div>
          <aside class="confidence-block" aria-label="Confidence ${percentage} percent">
            <span>${confidenceLabel(analysis.confidence)}</span>
            <strong>${analysis.confidence.toFixed(2)}</strong>
            <progress value="${percentage}" max="100"></progress>
            <small>Confidence</small>
          </aside>
        </div>
      </article>

      <article class="evidence-panel">
        <nav class="tabs" aria-label="Analysis detail">
          <button role="tab" data-tab="evidence" aria-selected="${state.activeTab === 'evidence'}">${icon('Database')} Citations <span>${analysis.citations.length}</span></button>
          <button role="tab" data-tab="patterns" aria-selected="${state.activeTab === 'patterns'}">${icon('Activity')} Incident patterns</button>
        </nav>
        <div class="tab-content">${state.activeTab === 'evidence' ? evidenceContent(analysis) : patternsContent()}</div>
      </article>

      <article class="recommendations-panel">
        <header>
          <span class="recommendation-icon">${icon('AlertTriangle')}</span>
          <div><p class="eyebrow">Human review required</p><h2>Recommended human actions - not executed.</h2></div>
        </header>
        <ol>${analysis.recommendedHumanActions.map((action) => `<li>${escapeHtml(action)}</li>`).join('')}</ol>
        ${analysis.prevention?.length ? `<h3>Prevention</h3><ul>${analysis.prevention.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : ''}
        <div class="limitations"><strong>Limitations</strong><ul>${analysis.limitations.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div>
      </article>
    </section>`;
}

function resultsPanel() {
  if (state.analysisStatus === 'loading') return loadingState();
  if (state.analysisStatus === 'error') return errorState();
  if (state.analysisStatus === 'empty') return emptyState();
  return dataState();
}

function sidebar() {
  const items = [
    ['dashboard', 'LayoutDashboard', 'Dashboard'],
    ['chat', 'MessageSquare', 'Chat'],
    ['settings', 'Settings', 'Settings'],
  ];
  return `
    <aside class="app-sidebar">
      <div class="sidebar-brand">${icon('Activity')}<span>Incident<br /><strong>Analysis</strong></span></div>
      <nav aria-label="Workspace">
        ${items.map(([view, iconName, label]) => `
          <button class="nav-item" data-view="${view}" aria-current="${state.activeView === view ? 'page' : 'false'}">
            ${icon(iconName)}<span>${label}</span>
          </button>`).join('')}
      </nav>
      <div class="sidebar-footer">
        <div class="sidebar-user">${icon('CircleUserRound')}<span><strong>${escapeHtml(state.user.name)}</strong><small>${escapeHtml(state.user.role)}</small></span></div>
        <button class="nav-item logout-nav" id="logout-button">${icon('LogOut')}<span>Logout</span></button>
      </div>
    </aside>`;
}

function dashboardView() {
  if (state.metricsStatus === 'loading') return `<section class="dashboard-view"><div class="view-heading"><p class="eyebrow">Operational overview</p><h1>Dashboard</h1></div>${loadingState()}</section>`;
  if (state.metricsStatus === 'error') return `<section class="dashboard-view"><div class="view-heading"><p class="eyebrow">Operational overview</p><h1>Dashboard</h1></div><article class="state-panel error-panel"><span class="state-icon">${icon('AlertTriangle')}</span><h2>Metrics unavailable</h2><p>${escapeHtml(state.error)}</p><button id="metrics-retry" class="outline">${icon('RefreshCw')} Retry</button></article></section>`;
  const metrics = state.metrics;
  return `
    <section class="dashboard-view">
      <div class="view-heading"><div><p class="eyebrow">Operational overview</p><h1>Dashboard</h1><p>Database-backed request and incident activity.</p></div><span class="live-indicator"><i></i> Live database</span></div>
      <div class="metric-grid">
        <article class="metric-card"><span>${icon('BarChart3')}</span><small>Total API requests</small><strong>${metrics.totalApiRequests.toLocaleString()}</strong><p>Completed analysis requests</p></article>
        <article class="metric-card incident-metric"><span>${icon('AlertTriangle')}</span><small>Incidents identified</small><strong>${metrics.totalIncidents.toLocaleString()}</strong><p>Evidence or confidence detected</p></article>
        <article class="metric-card clear-metric"><span>${icon('Check')}</span><small>Non-errors identified</small><strong>${metrics.totalNonErrors.toLocaleString()}</strong><p>No incident signal found</p></article>
      </div>
      <article class="chart-panel">
        <header><div><p class="eyebrow">Request volume</p><h2>Requests over time</h2></div><span>Last 12 active hours</span></header>
        <div class="chart-wrap"><canvas id="requests-chart" aria-label="Line chart of requests over time" role="img"></canvas></div>
      </article>
    </section>`;
}

function chatMessage(message) {
  const isUser = message.role === 'user';
  return `<div class="chat-row ${isUser ? 'user-message' : 'assistant-message'}">
    <span class="message-avatar">${icon(isUser ? 'CircleUserRound' : 'Activity')}</span>
    <div><strong>${isUser ? 'You' : 'Incident analyst'}</strong><p>${escapeHtml(message.text)}</p>${message.meta ? `<small>${escapeHtml(message.meta)}</small>` : ''}
    ${message.image ? `<img src="${escapeHtml(message.image)}" alt="Attached incident screenshot" style="max-width:100%;max-height:240px;object-fit:contain" />` : ''}
    ${message.analysis ? `
      <details><summary>Cited evidence (${message.analysis.citations.length})</summary>${evidenceContent(message.analysis)}</details>
      ${message.analysis.recommendedHumanActions.length ? `<h3>Recommended Human Actions</h3><ul>${message.analysis.recommendedHumanActions.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : ''}
      ${message.analysis.prevention?.length ? `<h3>Prevention</h3><ul>${message.analysis.prevention.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : ''}
      <details><summary>Limitations</summary><ul>${message.analysis.limitations.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul></details>
    ` : ''}</div>
  </div>`;
}

function chatView() {
  return `
    <section class="chat-view">
      <div class="view-heading"><div><p class="eyebrow">Database-grounded assistant</p><h1>Incident chat</h1><p>Historical knowledge and cited operational evidence.</p></div><span class="source-pill">${icon('Database')} Database only</span></div>
      <article class="chat-panel">
        <div class="message-list" id="message-list">${state.messages.map(chatMessage).join('')}</div>
        <form id="chat-form" class="chat-composer">
          ${state.error ? `<p class="form-error" role="alert">${escapeHtml(state.error)}</p>` : ''}
          ${state.attachment ? `<div class="attachment-chip">${icon('Paperclip')} <span>${escapeHtml(state.attachment.name)}</span><button type="button" id="remove-attachment" aria-label="Remove attachment">&times;</button></div>` : ''}
          ${state.attachment?.isImage ? `<img src="${escapeHtml(state.attachment.dataUrl)}" alt="Screenshot preview" style="max-width:100%;max-height:180px;object-fit:contain" />` : ''}
          <textarea id="chat-prompt" name="prompt" rows="3" maxlength="4000" placeholder="Describe the incident, symptoms, service, and time window..." required></textarea>
          <div class="composer-actions">
            <label class="upload-button" for="incident-file" title="Attach incident report">${icon('Paperclip')}<span>Attach report</span></label>
            <input id="incident-file" type="file" accept=".json,.csv,.txt,.log,image/jpeg,image/png" hidden />
            <small>JSON, CSV, TXT, LOG, JPEG or PNG</small>
            <button type="submit" class="send-button">${icon('Send')} Send</button>
          </div>
        </form>
      </article>
    </section>`;
}

function settingsView() {
  return `
    <section class="settings-view">
      <div class="view-heading"><div><p class="eyebrow">Personalization</p><h1>Settings</h1><p>Control response detail and approved retrieval sources.</p></div></div>
      <form id="settings-form" class="settings-grid">
        <article class="settings-section"><header>${icon('CircleUserRound')}<div><h2>User type</h2><p>Tailor terminology and recommendations to your role.</p></div></header>
          <label for="user-type">Role<select id="user-type" name="userType"><option value="operator" ${state.preferences.userType === 'operator' ? 'selected' : ''}>Operations engineer</option><option value="developer" ${state.preferences.userType === 'developer' ? 'selected' : ''}>Application developer</option><option value="manager" ${state.preferences.userType === 'manager' ? 'selected' : ''}>Incident manager</option></select></label>
        </article>
        <article class="settings-section"><header>${icon('MessageSquare')}<div><h2>Response handling</h2><p>Choose the amount of detail in generated responses.</p></div></header>
          <label for="response-style">Response style<select id="response-style" name="responseStyle"><option value="concise" ${state.preferences.responseStyle === 'concise' ? 'selected' : ''}>Concise</option><option value="detailed" ${state.preferences.responseStyle === 'detailed' ? 'selected' : ''}>Detailed</option><option value="executive" ${state.preferences.responseStyle === 'executive' ? 'selected' : ''}>Executive summary</option></select></label>
        </article>
        <article class="settings-section source-settings"><header>${icon('Database')}<div><h2>Retrieval source</h2><p>Restrict where supporting evidence may be retrieved.</p></div></header>
          <label class="radio-row"><input type="radio" name="source" value="database" checked /><span><strong>Database only</strong><small>Use approved runbooks, logs, and metrics.</small></span></label>
          <label class="radio-row disabled-option"><input type="radio" name="source" value="internet" disabled /><span><strong>Database and public internet</strong><small>Unavailable until an approved web-search provider is configured.</small></span></label>
        </article>
        <div class="settings-actions"><span id="settings-status" aria-live="polite"></span><button type="submit">${icon('Check')} Save settings</button></div>
      </form>
    </section>`;
}

function activeView() {
  if (state.activeView === 'chat') return chatView();
  if (state.activeView === 'settings') return settingsView();
  return dashboardView();
}

function workspace() {
  return `
    <div class="admin-shell">
      ${sidebar()}
      <main class="admin-main">
        <header class="admin-header"><div><span class="environment-badge">READ ONLY</span><span>Human approval required for operational changes</span></div><button class="icon-button secondary outline" id="theme-toggle" title="Theme: ${state.theme}" aria-label="Change color theme">${icon(effectiveTheme() === 'dark' ? 'Sun' : 'Moon')}</button></header>
        <div class="admin-content">${activeView()}</div>
      </main>
    </div>`;
}

function authShell(content) {
  return `
    <main class="auth-shell">
      <section class="auth-context">
        <span class="auth-brand">${icon('Activity')} Incident Analysis</span>
        <div>
          <p class="eyebrow">Read-only operations workspace</p>
          <h1>Diagnose with evidence.<br />Act with human judgment.</h1>
          <p>Bounded runbooks, logs, and metrics remain visible beside every recommendation.</p>
        </div>
        <small>${icon('ShieldCheck')} No remediation capability</small>
      </section>
      <article class="auth-panel">${content}</article>
    </main>`;
}

function loginView() {
  return authShell(`
    <header><span class="section-icon">${icon('LogIn')}</span><h1>Sign in</h1><p>Use your operations account to continue.</p></header>
    ${state.error ? `<p class="form-error" role="alert">${icon('AlertTriangle')} ${escapeHtml(state.error)}</p>` : ''}
    <form id="login-form">
      <label for="login-email">Email<input id="login-email" name="email" type="email" autocomplete="email" value="morgan.lee@example.com" required /></label>
      <label for="login-password">Password<input id="login-password" name="password" type="password" autocomplete="current-password" value="incident-demo" required /></label>
      <button type="submit">${icon('LogIn')} Sign in to incident workspace</button>
    </form>
    <hr />
    <button id="show-create-account" class="secondary outline">${icon('UserPlus')} Create account</button>`);
}

function createAccountView() {
  return authShell(`
    <header><span class="section-icon">${icon('UserPlus')}</span><h1>Create account</h1><p>Register an operator identity for this local preview.</p></header>
    ${state.error ? `<p class="form-error" role="alert">${icon('AlertTriangle')} ${escapeHtml(state.error)}</p>` : ''}
    <form id="create-account-form" novalidate>
      <label for="account-name">Full name<input id="account-name" name="name" autocomplete="name" required minlength="2" /></label>
      <label for="account-email">Email<input id="account-email" name="email" type="email" autocomplete="email" required /></label>
      <label for="account-password">Password<input id="account-password" name="password" type="password" autocomplete="new-password" required minlength="12" aria-describedby="password-help" /></label>
      <small id="password-help">Use at least 12 characters.</small>
      <button type="submit">${icon('UserPlus')} Create operator account</button>
    </form>
    <button id="back-to-login" class="secondary outline">${icon('ArrowLeft')} Back to sign in</button>`);
}

function bindWorkspaceEvents() {
  document.querySelector('#theme-toggle')?.addEventListener('click', cycleTheme);
  document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => {
    state.activeView = button.dataset.view;
    state.error = '';
    render();
  }));
  document.querySelector('#logout-button')?.addEventListener('click', async () => {
    await api.logout();
    state.user = null;
    state.route = 'login';
    state.error = '';
    render();
  });

  document.querySelector('#metrics-retry')?.addEventListener('click', loadMetrics);
  document.querySelector('#incident-file')?.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      state.attachment = await readAttachment(file);
      state.error = '';
    } catch (error) {
      state.attachment = null;
      state.error = error instanceof Error ? error.message : 'Unable to read attachment.';
    }
    render();
  });
  document.querySelector('#remove-attachment')?.addEventListener('click', () => {
    state.attachment = null;
    render();
  });
  document.querySelector('#chat-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    await submitChat(String(formData.get('prompt')).trim());
  });
  document.querySelector('#settings-form')?.addEventListener('submit', (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    state.preferences = {
      userType: String(formData.get('userType')),
      responseStyle: String(formData.get('responseStyle')),
      source: 'database',
    };
    localStorage.setItem('incident-preferences', JSON.stringify(state.preferences));
    const status = document.querySelector('#settings-status');
    status.textContent = 'Settings saved';
  });
}

function bindAuthEvents() {
  document.querySelector('#show-create-account')?.addEventListener('click', () => {
    state.route = 'create-account';
    state.error = '';
    render();
  });
  document.querySelector('#back-to-login')?.addEventListener('click', () => {
    state.route = 'login';
    state.error = '';
    render();
  });
  document.querySelector('#login-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    state.error = '';
    const formData = new FormData(event.currentTarget);
    try {
      state.user = await api.login({
        email: String(formData.get('email')),
        password: String(formData.get('password')),
      });
      state.route = 'workspace';
      await loadMetrics();
    } catch (error) {
      state.error = error instanceof Error ? error.message : 'Unable to sign in.';
      render();
    }
  });
  document.querySelector('#create-account-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    state.error = '';
    const formData = new FormData(form);
    try {
      state.user = await api.createAccount({
        name: String(formData.get('name')),
        email: String(formData.get('email')),
        password: String(formData.get('password')),
      });
      state.route = 'workspace';
      await loadMetrics();
    } catch (error) {
      state.error = error instanceof Error ? error.message : 'Unable to create account.';
      render();
    }
  });
}

function render() {
  app.innerHTML = state.user
    ? workspace()
    : state.route === 'create-account'
      ? createAccountView()
      : loginView();
  refreshIcons();
  if (state.user) {
    bindWorkspaceEvents();
    if (state.activeView === 'dashboard' && state.metrics) requestAnimationFrame(drawChart);
  }
  else bindAuthEvents();
}

function drawChart() {
  const canvas = document.querySelector('#requests-chart');
  if (!canvas || !state.metrics) return;
  const points = state.metrics.requestsOverTime;
  const scale = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = width * scale;
  canvas.height = height * scale;
  const context = canvas.getContext('2d');
  context.scale(scale, scale);
  const styles = getComputedStyle(document.documentElement);
  const lineColor = styles.getPropertyValue('--pico-primary').trim();
  const gridColor = styles.getPropertyValue('--ops-border').trim();
  context.strokeStyle = gridColor;
  context.lineWidth = 1;
  for (let row = 1; row < 5; row += 1) {
    const y = (height / 5) * row;
    context.beginPath();
    context.moveTo(36, y);
    context.lineTo(width - 16, y);
    context.stroke();
  }
  if (!points.length) {
    context.fillStyle = styles.getPropertyValue('--ops-muted').trim();
    context.font = '14px IBM Plex Sans';
    context.fillText('No request history yet', 36, height / 2);
    return;
  }
  const max = Math.max(...points.map((point) => point.count), 1);
  const step = (width - 64) / Math.max(points.length - 1, 1);
  context.strokeStyle = lineColor;
  context.lineWidth = 3;
  context.beginPath();
  points.forEach((point, index) => {
    const x = 36 + index * step;
    const y = height - 38 - (point.count / max) * (height - 72);
    if (index === 0) context.moveTo(x, y);
    else context.lineTo(x, y);
  });
  context.stroke();
  context.fillStyle = lineColor;
  points.forEach((point, index) => {
    const x = 36 + index * step;
    const y = height - 38 - (point.count / max) * (height - 72);
    context.beginPath();
    context.arc(x, y, 4, 0, Math.PI * 2);
    context.fill();
    context.font = '11px IBM Plex Sans';
    context.fillText(point.label, x - 14, height - 14);
  });
}

async function loadMetrics() {
  state.metricsStatus = 'loading';
  render();
  try {
    state.metrics = await api.getMetrics();
    state.metricsStatus = 'data';
  } catch (error) {
    state.metricsStatus = 'error';
    state.error = error instanceof Error ? error.message : 'Unable to load metrics.';
  }
  render();
}

async function submitChat(prompt) {
  if (!prompt) return;
  state.error = '';
  const attachment = state.attachment;
  const attachmentText = attachment?.content ? `\n\nAttached report (${attachment.name}):\n${attachment.content}` : '';
  const description = `${prompt}${attachmentText}`.slice(0, 4000);
  state.messages.push({ role: 'user', text: prompt, meta: attachment ? `Attached: ${attachment.name}` : '',
    image: attachment?.isImage ? attachment.dataUrl : null });
  state.messages.push({ role: 'assistant', text: 'Searching approved evidence...', pending: true });
  state.attachment = null;
  render();
  try {
    const result = await api.analyzeIncident({
      description,
      service: null,
      timeWindow: 'Last 2 hours',
      userType: state.preferences.userType,
      responseStyle: state.preferences.responseStyle,
      ...(attachment?.isImage ? { image: { dataUrl: attachment.dataUrl } } : {}),
    });
    state.messages.pop();
    state.messages.push({
      role: 'assistant',
      text: result.diagnosis,
      analysis: result,
      meta: `${result.citations.length} citations · ${Math.round(result.confidence * 100)}% confidence`,
    });
    state.metrics = await api.getMetrics();
    state.metricsStatus = 'data';
  } catch (error) {
    state.messages.pop();
    state.messages.push({ role: 'assistant', text: error instanceof Error ? error.message : 'Analysis failed.' });
  }
  render();
  document.querySelector('#message-list')?.scrollTo({ top: 999999, behavior: 'smooth' });
}

async function runAnalysis() {
  state.analysis = null;
  state.error = '';
  state.analysisStatus = 'loading';
  render();
  try {
    const result = await api.analyzeIncident(state.form);
    state.analysis = result;
    state.analysisStatus = result ? 'data' : 'empty';
  } catch (error) {
    state.analysisStatus = 'error';
    state.error = error instanceof Error ? error.message : 'Analysis failed.';
  }
  render();
}

async function initialize() {
  applyTheme();
  const mediaQuery = matchMedia('(prefers-color-scheme: dark)');
  mediaQuery.addEventListener('change', () => {
    if (state.theme === 'system') {
      applyTheme();
      render();
    }
  });
  window.addEventListener('api:unauthorized', () => {
    state.user = null;
    state.route = 'login';
    state.error = 'Your session has ended. Sign in again.';
    render();
  });
  state.user = await api.getCurrentUser();
  state.route = state.user ? 'workspace' : 'login';
  render();
  if (state.user) await loadMetrics();
}

initialize();