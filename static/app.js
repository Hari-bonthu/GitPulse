/* ============================================
   GitPulse — Frontend Application
   Vanilla JS + Lucide Icons + Sonner-style Toasts
   ============================================ */

const API = '/api';

// --- State ---
const state = {
  repos: [],
  selectedRepoId: null,
  repoDetail: null,
  dashboard: null,
  settings: null,
  notifications: [],
  refreshTimer: null,
  autoRefreshEnabled: true,
  commitAction: 'commit', // 'commit' or 'commit-push'
  stagedFiles: new Set(),
  expandedDirs: new Set(),
};

// ============================================
// TOAST SYSTEM (Sonner-style)
// ============================================
const Toast = (() => {
  let toastId = 0;
  const MAX_TOASTS = 5;
  const container = () => document.getElementById('toast-container');

  const iconMap = {
    success: 'circle-check',
    error: 'circle-x',
    warning: 'alert-triangle',
    info: 'info',
    loading: 'loader-2',
  };

  function create(message, type = 'info', opts = {}) {
    const id = ++toastId;
    const duration = opts.duration ?? (type === 'loading' ? Infinity : 4000);
    const desc = opts.description || '';

    const el = document.createElement('div');
    el.className = 'toast';
    el.dataset.toastId = id;
    el.innerHTML = `
      <div class="toast-icon ${type}">
        <i data-lucide="${iconMap[type] || 'info'}" style="width:18px;height:18px;"></i>
      </div>
      <div class="toast-body">
        <div class="toast-title">${esc(message)}</div>
        ${desc ? `<div class="toast-desc">${esc(desc)}</div>` : ''}
      </div>
      <button class="toast-close" onclick="Toast.dismiss(${id})">
        <i data-lucide="x" style="width:14px;height:14px;"></i>
      </button>
    `;

    const c = container();
    c.appendChild(el);
    refreshIcons();

    // Remove old toasts
    const toasts = c.querySelectorAll('.toast:not(.removing)');
    if (toasts.length > MAX_TOASTS) {
      dismiss(parseInt(toasts[0].dataset.toastId));
    }

    if (duration !== Infinity) {
      setTimeout(() => dismiss(id), duration);
    }

    return id;
  }

  function dismiss(id) {
    const el = container().querySelector(`[data-toast-id="${id}"]`);
    if (!el || el.classList.contains('removing')) return;
    el.classList.add('removing');
    setTimeout(() => el.remove(), 200);
  }

  function update(id, message, type) {
    const el = container().querySelector(`[data-toast-id="${id}"]`);
    if (!el) return;
    const icon = el.querySelector('.toast-icon');
    const title = el.querySelector('.toast-title');
    if (icon) {
      icon.className = `toast-icon ${type}`;
      icon.innerHTML = `<i data-lucide="${iconMap[type]}" style="width:18px;height:18px;"></i>`;
    }
    if (title) title.textContent = message;
    refreshIcons();
    if (type !== 'loading') setTimeout(() => dismiss(id), 3000);
  }

  return {
    success: (msg, opts) => create(msg, 'success', opts),
    error: (msg, opts) => create(msg, 'error', opts),
    warning: (msg, opts) => create(msg, 'warning', opts),
    info: (msg, opts) => create(msg, 'info', opts),
    loading: (msg, opts) => create(msg, 'loading', { ...opts, duration: Infinity }),
    dismiss,
    update,
    promise: async (promise, msgs) => {
      const id = create(msgs.loading || 'Loading...', 'loading');
      try {
        const result = await promise;
        update(id, typeof msgs.success === 'function' ? msgs.success(result) : (msgs.success || 'Done'), 'success');
        return result;
      } catch (err) {
        update(id, typeof msgs.error === 'function' ? msgs.error(err) : (msgs.error || 'Failed'), 'error');
        throw err;
      }
    },
  };
})();

// Make Toast globally accessible
window.Toast = Toast;

// ============================================
// API LAYER
// ============================================
async function api(method, endpoint, body) {
  try {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API}${endpoint}`, opts);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Request failed');
    }
    return await res.json();
  } catch (err) {
    if (!err.message.includes('Failed to fetch')) {
      Toast.error(err.message);
    }
    throw err;
  }
}

// ============================================
// UTILITY
// ============================================
function esc(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function refreshIcons() {
  if (window.lucide) lucide.createIcons();
}

function statusIcon(health) {
  const map = {
    CLEAN: { icon: 'circle-check', cls: 'clean' },
    DIRTY: { icon: 'circle-alert', cls: 'dirty' },
    UNPUSHED: { icon: 'arrow-up-circle', cls: 'unpushed' },
    BEHIND: { icon: 'arrow-down-circle', cls: 'behind' },
    STALE: { icon: 'clock', cls: 'stale' },
  };
  const m = map[health] || map.DIRTY;
  return `<i data-lucide="${m.icon}" class="status-icon ${m.cls}" style="width:18px;height:18px;"></i>`;
}

function fileStatusIcon(status) {
  const map = {
    MODIFIED: { icon: 'file-pen', cls: 'modified' },
    ADDED: { icon: 'file-plus', cls: 'added' },
    DELETED: { icon: 'file-x', cls: 'deleted' },
    UNTRACKED: { icon: 'file-question', cls: 'untracked' },
    RENAMED: { icon: 'file-symlink', cls: 'renamed' },
    COPIED: { icon: 'file-plus', cls: 'added' },
  };
  const m = map[status] || map.MODIFIED;
  return `<i data-lucide="${m.icon}" class="tree-item-icon ${m.cls}" style="width:14px;height:14px;"></i>`;
}

// ============================================
// RENDERING
// ============================================

// --- Dashboard ---
function renderDashboard(data) {
  state.dashboard = data;

  // Summary bar
  $('#stat-total').textContent = data.total_repos;
  $('#stat-attention').textContent = data.repos_needing_attention;
  $('#stat-unpushed').textContent = data.repos_with_unpushed;
  $('#stat-stale').textContent = data.stale_repos;

  // Sidebar
  renderSidebar(data.repo_summaries);

  // Dashboard grid
  const grid = $('#dashboard-grid');
  if (data.repo_summaries.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1;">
        <i data-lucide="git-branch"></i>
        <div class="empty-state-title">No repositories tracked</div>
        <div class="empty-state-desc">Click "Add Repository" to start tracking your git projects.</div>
        <button class="btn btn-primary mt-4" onclick="openAddRepoModal()">
          <i data-lucide="folder-plus" style="width:14px;height:14px;"></i>
          Add Repository
        </button>
      </div>`;
    refreshIcons();
    return;
  }

  grid.innerHTML = data.repo_summaries.map((r, i) => `
    <div class="dash-card" style="animation-delay:${i * 50}ms" onclick="selectRepo('${esc(r.id)}')">
      <div class="dash-card-header">
        <div class="dash-card-title">
          ${statusIcon(r.health)}
          ${esc(r.name)}
        </div>
        ${r.stash_count > 0 ? `<span style="display:flex;align-items:center;gap:4px;font-size:12px;color:var(--text-muted);">
          <i data-lucide="archive" style="width:12px;height:12px;"></i>${r.stash_count}
        </span>` : ''}
      </div>
      <div class="dash-card-body">
        <div class="dash-card-stat">
          <i data-lucide="git-branch"></i>
          <span>${esc(r.branch_name)}</span>
        </div>
        ${r.changed_count > 0 ? `<div class="dash-card-stat">
          <i data-lucide="file-pen" style="color:var(--warning);"></i>
          <span>${r.changed_count} changed file${r.changed_count > 1 ? 's' : ''}</span>
        </div>` : ''}
        ${r.unpushed_count > 0 ? `<div class="dash-card-stat">
          <i data-lucide="arrow-up-circle" style="color:var(--error);"></i>
          <span>${r.unpushed_count} unpushed commit${r.unpushed_count > 1 ? 's' : ''}</span>
        </div>` : ''}
        ${r.health === 'CLEAN' ? `<div class="dash-card-stat">
          <i data-lucide="circle-check" style="color:var(--success);"></i>
          <span style="color:var(--success);">Clean</span>
        </div>` : ''}
      </div>
      <div class="dash-card-footer">
        ${r.last_commit_time ? `${esc(r.last_commit_time)}` : 'No commits'}
        ${r.last_commit_message ? ` — ${esc(r.last_commit_message.substring(0, 50))}` : ''}
      </div>
    </div>
  `).join('');

  refreshIcons();
}

// --- Sidebar ---
function renderSidebar(repos) {
  state.repos = repos;
  const list = $('#sidebar-list');

  if (repos.length === 0) {
    list.innerHTML = `<div class="empty-state" style="padding:30px 10px;">
      <i data-lucide="inbox" style="width:24px;height:24px;"></i>
      <p style="font-size:12px;margin-top:8px;">No repos yet</p>
    </div>`;
    refreshIcons();
    return;
  }

  list.innerHTML = repos.map(r => `
    <div class="repo-card ${state.selectedRepoId === r.id ? 'active' : ''}" onclick="selectRepo('${esc(r.id)}')" data-repo-id="${esc(r.id)}">
      <div class="repo-card-status">${statusIcon(r.health)}</div>
      <div class="repo-card-info">
        <div class="repo-card-name">${esc(r.name)}</div>
        <div class="repo-card-meta">
          <i data-lucide="git-branch" style="width:12px;height:12px;"></i>
          <span>${esc(r.branch_name)}</span>
          ${r.changed_count > 0 ? `<span style="color:var(--warning);">${r.changed_count} changes</span>` : ''}
          ${r.unpushed_count > 0 ? `<span style="color:var(--error);">↑${r.unpushed_count}</span>` : ''}
        </div>
      </div>
    </div>
  `).join('');

  refreshIcons();
}

// --- Detail View ---
async function selectRepo(repoId) {
  state.selectedRepoId = repoId;

  // Update sidebar active state
  $$('.repo-card').forEach(c => c.classList.toggle('active', c.dataset.repoId === repoId));

  // Show detail view
  $('#dashboard-view').classList.add('hidden');
  $('#detail-view').classList.remove('hidden');

  // Load data
  try {
    const [status, tree, log, stash] = await Promise.all([
      api('GET', `/repos/${repoId}/status`),
      api('GET', `/repos/${repoId}/tree`),
      api('GET', `/repos/${repoId}/log`),
      api('GET', `/repos/${repoId}/stash`),
    ]);

    state.repoDetail = status;
    renderRepoDetail(status, tree, log, stash);
  } catch (err) {
    Toast.error('Failed to load repository details');
  }
}

function renderRepoDetail(status, tree, log, stash) {
  // Title
  $('#detail-title').innerHTML = `
    ${statusIcon(status.health)}
    <span>${esc(status.name)}</span>
    <button class="btn btn-danger btn-sm" onclick="confirmRemoveRepo('${esc(status.id)}')" style="margin-left:auto;">
      <i data-lucide="trash-2" style="width:12px;height:12px;"></i>
      Remove
    </button>
  `;

  // Branch bar
  $('#branch-bar').innerHTML = `
    <div class="branch-tag">
      <i data-lucide="git-branch" style="width:14px;height:14px;"></i>
      ${esc(status.branch.name)}
    </div>
    ${status.branch.remote_name ? `<span style="color:var(--text-muted);font-size:12px;">→ ${esc(status.branch.remote_name)}</span>` : ''}
    <div class="ahead-behind">
      ${status.branch.ahead > 0 ? `<span class="ahead">↑ ${status.branch.ahead} ahead</span>` : ''}
      ${status.branch.behind > 0 ? `<span class="behind">↓ ${status.branch.behind} behind</span>` : ''}
      ${status.branch.ahead === 0 && status.branch.behind === 0 ? `<span style="color:var(--success);">Up to date</span>` : ''}
    </div>
    <div style="flex:1;"></div>
    <span style="font-size:12px;color:var(--text-muted);">
      ${status.last_commit_time ? `Last commit: ${esc(status.last_commit_time)}` : 'No commits'}
    </span>
  `;

  // Tree
  renderGitTree(tree);
  $('#tree-count').textContent = status.changed_files.length;

  // Stash
  renderStashList(stash);
  $('#stash-count').textContent = stash.length;

  // History
  renderCommitHistory(log);

  // Reset diff
  $('#diff-viewer').innerHTML = `<div class="empty-state" style="padding:20px;">
    <p style="font-size:12px;color:var(--text-muted);">Click a file to view diff</p>
  </div>`;
  $('#diff-filename').textContent = '';

  refreshIcons();
}

// --- Git Tree ---
function renderGitTree(nodes) {
  const container = $('#git-tree');
  if (!nodes || nodes.length === 0) {
    container.innerHTML = `<div class="empty-state" style="padding:20px;">
      <i data-lucide="circle-check" style="width:20px;height:20px;color:var(--success);"></i>
      <p style="font-size:12px;margin-top:8px;">No changes</p>
    </div>`;
    refreshIcons();
    return;
  }

  state.stagedFiles.clear();
  container.innerHTML = buildTreeHTML(nodes, 0);
  refreshIcons();
}

function buildTreeHTML(nodes, level) {
  return nodes.map(node => {
    const indent = `<span class="tree-indent" style="width:${level * 20}px;"></span>`;

    if (node.is_dir) {
      const isExpanded = state.expandedDirs.has(node.path);
      const childrenHTML = isExpanded ? buildTreeHTML(node.children || [], level + 1) : '';
      return `
        <div class="tree-item" onclick="toggleTreeDir('${esc(node.path)}')">
          ${indent}
          <i data-lucide="chevron-down" class="tree-toggle ${isExpanded ? '' : 'collapsed'}" style="width:14px;height:14px;"></i>
          <i data-lucide="folder${isExpanded ? '-open' : ''}" class="tree-item-icon dir" style="width:14px;height:14px;"></i>
          <span class="tree-item-name">${esc(node.name)}</span>
        </div>
        <div class="tree-children" data-dir="${esc(node.path)}">${childrenHTML}</div>
      `;
    } else {
      const statusCls = (node.status || 'MODIFIED').toLowerCase();
      return `
        <div class="tree-item" onclick="showFileDiff('${esc(node.path)}')" data-file="${esc(node.path)}">
          ${indent}
          <input type="checkbox" class="tree-item-checkbox" onclick="event.stopPropagation();toggleStageFile('${esc(node.path)}')" ${state.stagedFiles.has(node.path) ? 'checked' : ''}>
          ${fileStatusIcon(node.status)}
          <span class="tree-item-name ${statusCls}">${esc(node.name)}</span>
        </div>
      `;
    }
  }).join('');
}

window.toggleTreeDir = function(path) {
  if (state.expandedDirs.has(path)) {
    state.expandedDirs.delete(path);
  } else {
    state.expandedDirs.add(path);
  }
  // Re-render tree with current data
  if (state.selectedRepoId) {
    api('GET', `/repos/${state.selectedRepoId}/tree`).then(tree => renderGitTree(tree));
  }
};

window.toggleStageFile = function(path) {
  if (state.stagedFiles.has(path)) {
    state.stagedFiles.delete(path);
  } else {
    state.stagedFiles.add(path);
  }
};

// --- Diff ---
window.showFileDiff = async function(filePath) {
  if (!state.selectedRepoId) return;

  // Highlight selected file
  $$('.tree-item').forEach(el => el.classList.remove('selected'));
  const fileEl = document.querySelector(`.tree-item[data-file="${CSS.escape(filePath)}"]`);
  if (fileEl) fileEl.classList.add('selected');

  $('#diff-filename').textContent = filePath;

  try {
    const data = await api('GET', `/repos/${state.selectedRepoId}/diff?file=${encodeURIComponent(filePath)}`);
    renderDiff(data.diff);
  } catch {
    $('#diff-viewer').innerHTML = `<div class="empty-state" style="padding:20px;">
      <p style="font-size:12px;color:var(--error);">Failed to load diff</p>
    </div>`;
  }
};

function renderDiff(diffText) {
  const viewer = $('#diff-viewer');
  if (!diffText) {
    viewer.innerHTML = `<div class="empty-state" style="padding:20px;">
      <p style="font-size:12px;color:var(--text-muted);">No diff available (new or untracked file)</p>
    </div>`;
    return;
  }

  const lines = diffText.split('\n');
  let lineNum = 0;

  viewer.innerHTML = lines.map(line => {
    let cls = '';
    if (line.startsWith('+++') || line.startsWith('---')) {
      return `<div class="diff-file-header">${esc(line)}</div>`;
    }
    if (line.startsWith('@@')) {
      const match = line.match(/@@ -\d+(?:,\d+)? \+(\d+)/);
      if (match) lineNum = parseInt(match[1]) - 1;
      return `<div class="diff-line hunk"><span class="diff-line-num"></span><span class="diff-line-content">${esc(line)}</span></div>`;
    }
    if (line.startsWith('+')) {
      lineNum++;
      cls = 'added';
    } else if (line.startsWith('-')) {
      cls = 'removed';
    } else {
      lineNum++;
    }
    return `<div class="diff-line ${cls}"><span class="diff-line-num">${cls === 'removed' ? '' : lineNum}</span><span class="diff-line-content">${esc(line)}</span></div>`;
  }).join('');
}

// --- Stash ---
function renderStashList(stashes) {
  const list = $('#stash-list');
  if (stashes.length === 0) {
    list.innerHTML = `<div class="empty-state" style="padding:20px;">
      <p style="font-size:12px;color:var(--text-muted);">No stash entries</p>
    </div>`;
    return;
  }

  list.innerHTML = stashes.map(s => `
    <div class="stash-item">
      <div class="stash-info">
        <i data-lucide="archive" style="width:14px;height:14px;"></i>
        <span class="stash-message">stash@{${s.index}}: ${esc(s.message)}</span>
        <span style="font-size:11px;color:var(--text-muted);">(${esc(s.branch)})</span>
      </div>
      <div class="stash-actions">
        <button class="btn btn-ghost btn-sm" onclick="handleStash('apply',${s.index})" title="Apply">
          <i data-lucide="check" style="width:12px;height:12px;"></i>
        </button>
        <button class="btn btn-ghost btn-sm" onclick="handleStash('pop',${s.index})" title="Pop">
          <i data-lucide="archive-restore" style="width:12px;height:12px;"></i>
        </button>
        <button class="btn btn-ghost btn-sm" onclick="handleStash('drop',${s.index})" title="Drop" style="color:var(--error);">
          <i data-lucide="trash-2" style="width:12px;height:12px;"></i>
        </button>
      </div>
    </div>
  `).join('');

  refreshIcons();
}

// --- Commit History ---
function renderCommitHistory(commits) {
  const list = $('#history-list');
  if (commits.length === 0) {
    list.innerHTML = `<div class="empty-state" style="padding:20px;">
      <p style="font-size:12px;color:var(--text-muted);">No commit history</p>
    </div>`;
    return;
  }

  list.innerHTML = commits.map(c => `
    <div class="commit-item">
      <span class="commit-hash">${esc(c.hash)}</span>
      <span class="commit-msg">${esc(c.message)}</span>
      <span class="commit-meta">${esc(c.author)} · ${esc(c.timestamp)}</span>
    </div>
  `).join('');
}

// ============================================
// ACTIONS
// ============================================

// --- Back to Dashboard ---
window.backToDashboard = function() {
  state.selectedRepoId = null;
  state.repoDetail = null;
  state.stagedFiles.clear();
  state.expandedDirs.clear();
  $('#detail-view').classList.add('hidden');
  $('#dashboard-view').classList.remove('hidden');
  $$('.repo-card').forEach(c => c.classList.remove('active'));
  refreshAll();
};

// --- Refresh ---
async function refreshAll() {
  try {
    const data = await api('GET', '/dashboard');
    renderDashboard(data);
  } catch {
    // silently fail on refresh
  }
}

// --- Add Repo ---
window.openAddRepoModal = function() {
  $('#add-repo-modal').classList.remove('hidden');
  $('#repo-path-input').value = '';
  $('#repo-path-error').classList.add('hidden');
  $('#repo-path-input').focus();
};

function closeAddRepoModal() {
  $('#add-repo-modal').classList.add('hidden');
}

async function addRepo() {
  const path = $('#repo-path-input').value.trim();
  if (!path) {
    $('#repo-path-error').textContent = 'Please enter a path';
    $('#repo-path-error').classList.remove('hidden');
    return;
  }

  try {
    await Toast.promise(
      api('POST', '/repos', { path }),
      { loading: 'Adding repository...', success: 'Repository added!', error: (e) => e.message }
    );
    closeAddRepoModal();
    await refreshAll();
  } catch {
    // error shown by toast
  }
}

// --- Remove Repo ---
window.confirmRemoveRepo = function(repoId) {
  showConfirm('Remove Repository', 'Are you sure you want to stop tracking this repository? This will not delete any files.', async () => {
    try {
      await Toast.promise(
        api('DELETE', `/repos/${repoId}`),
        { loading: 'Removing...', success: 'Repository removed', error: 'Failed to remove' }
      );
      backToDashboard();
    } catch {}
  });
};

// --- Stash Actions ---
window.handleStash = async function(action, index) {
  if (!state.selectedRepoId) return;
  const id = state.selectedRepoId;

  const actionMap = {
    apply: { method: 'POST', endpoint: `/repos/${id}/stash/apply?index=${index}`, msg: 'Stash applied' },
    pop: { method: 'POST', endpoint: `/repos/${id}/stash/pop?index=${index}`, msg: 'Stash popped' },
    drop: { method: 'DELETE', endpoint: `/repos/${id}/stash/${index}`, msg: 'Stash dropped' },
  };

  const a = actionMap[action];
  if (action === 'drop') {
    showConfirm('Drop Stash', `Drop stash@{${index}}? This cannot be undone.`, async () => {
      try {
        await Toast.promise(api(a.method, a.endpoint), { loading: 'Working...', success: a.msg, error: 'Failed' });
        selectRepo(id);
      } catch {}
    });
  } else {
    try {
      await Toast.promise(api(a.method, a.endpoint), { loading: 'Working...', success: a.msg, error: 'Failed' });
      selectRepo(id);
    } catch {}
  }
};

// --- Commit ---
window.handleCommit = async function() {
  if (!state.selectedRepoId) return;
  const message = $('#commit-message').value.trim();
  if (!message) {
    Toast.warning('Please enter a commit message');
    $('#commit-message').focus();
    return;
  }

  const files = state.stagedFiles.size > 0 ? Array.from(state.stagedFiles) : null;
  const id = state.selectedRepoId;

  if (state.commitAction === 'commit-push') {
    try {
      await Toast.promise(
        api('POST', `/repos/${id}/commit-push`, { message, files }),
        { loading: 'Committing & pushing...', success: 'Committed & pushed!', error: (e) => e.message }
      );
      $('#commit-message').value = '';
      state.stagedFiles.clear();
      selectRepo(id);
    } catch {}
  } else {
    try {
      await Toast.promise(
        api('POST', `/repos/${id}/commit`, { message, files }),
        { loading: 'Committing...', success: 'Committed!', error: (e) => e.message }
      );
      $('#commit-message').value = '';
      state.stagedFiles.clear();
      selectRepo(id);
    } catch {}
  }
};

// --- AI Generate ---
window.handleGenerateAI = async function() {
  if (!state.selectedRepoId) return;
  const btn = $('#ai-generate-btn');
  btn.disabled = true;

  try {
    const result = await Toast.promise(
      api('POST', '/ai/generate-commit', { repo_id: state.selectedRepoId }),
      { loading: 'Generating commit message...', success: (r) => `Generated via ${r.provider}`, error: (e) => e.message }
    );
    $('#commit-message').value = result.message;
    $('#commit-message').focus();
  } catch {} finally {
    btn.disabled = false;
  }
};

// --- Settings ---
function openSettings() {
  $('#settings-modal').classList.remove('hidden');
  if (state.settings) {
    $('#setting-staleness').value = state.settings.staleness_threshold_days;
    $('#setting-ai-provider').value = state.settings.ai_provider;
    $('#setting-quiet-start').value = state.settings.notification_quiet_start || '22:00';
    $('#setting-quiet-end').value = state.settings.notification_quiet_end || '08:00';
    $('#setting-theme').value = state.settings.theme;
  }
}

async function saveSettings() {
  const settings = {
    staleness_threshold_days: parseInt($('#setting-staleness').value) || 3,
    auto_refresh_seconds: parseInt($('#refresh-interval').value) || 60,
    ai_provider: $('#setting-ai-provider').value,
    notification_quiet_start: $('#setting-quiet-start').value,
    notification_quiet_end: $('#setting-quiet-end').value,
    theme: $('#setting-theme').value,
  };

  try {
    await Toast.promise(
      api('PUT', '/settings', settings),
      { loading: 'Saving...', success: 'Settings saved', error: 'Failed to save' }
    );
    state.settings = settings;
    applyTheme(settings.theme);
    $('#settings-modal').classList.add('hidden');
    refreshAll();
  } catch {}
}

function applyTheme(theme) {
  const html = document.documentElement;
  html.classList.remove('theme-dark', 'theme-light');
  if (theme === 'light') {
    html.classList.add('theme-light');
  } else if (theme === 'dark') {
    html.classList.add('theme-dark');
  } else {
    // System
    if (window.matchMedia('(prefers-color-scheme: light)').matches) {
      html.classList.add('theme-light');
    } else {
      html.classList.add('theme-dark');
    }
  }
}

// --- Confirm Dialog ---
let confirmCallback = null;

function showConfirm(title, message, onConfirm) {
  $('#confirm-title').textContent = title;
  $('#confirm-message').textContent = message;
  $('#confirm-dialog').classList.remove('hidden');
  confirmCallback = onConfirm;
}

// --- Auto Refresh ---
function startAutoRefresh() {
  stopAutoRefresh();
  if (!state.autoRefreshEnabled) return;
  const interval = parseInt($('#refresh-interval').value) * 1000;
  state.refreshTimer = setInterval(() => {
    if (state.selectedRepoId) {
      selectRepo(state.selectedRepoId);
    } else {
      refreshAll();
    }
  }, interval);
}

function stopAutoRefresh() {
  if (state.refreshTimer) {
    clearInterval(state.refreshTimer);
    state.refreshTimer = null;
  }
}

// --- Notifications ---
async function fetchNotifications() {
  try {
    const data = await api('GET', '/notifications');
    state.notifications = data || [];
    const countEl = $('#notification-count');
    if (state.notifications.length > 0) {
      countEl.textContent = state.notifications.length;
      countEl.classList.remove('hidden');
    } else {
      countEl.classList.add('hidden');
    }
  } catch {}
}

// --- Section Toggle ---
function setupSectionToggles() {
  $$('.section-header').forEach(header => {
    header.addEventListener('click', () => {
      const content = header.nextElementSibling;
      if (content && content.classList.contains('section-content')) {
        content.classList.toggle('open');
        const chevron = header.querySelector('[data-lucide="chevron-down"], [data-lucide="chevron-up"]');
        if (chevron) {
          const isOpen = content.classList.contains('open');
          chevron.setAttribute('data-lucide', isOpen ? 'chevron-down' : 'chevron-up');
          refreshIcons();
        }
      }
    });
  });
}

// --- Commit Dropdown ---
function setupCommitDropdown() {
  const toggle = $('#commit-toggle-btn');
  const menu = $('#commit-menu');
  const mainBtn = $('#commit-main-btn');
  const label = $('#commit-btn-label');

  toggle.addEventListener('click', (e) => {
    e.stopPropagation();
    menu.classList.toggle('hidden');
  });

  mainBtn.addEventListener('click', handleCommit);

  menu.addEventListener('click', (e) => {
    const item = e.target.closest('.dropdown-item');
    if (!item) return;
    const action = item.dataset.action;
    state.commitAction = action;
    label.textContent = action === 'commit-push' ? 'Commit & Push' : 'Commit';
    menu.classList.add('hidden');
    handleCommit();
  });

  // Close on outside click
  document.addEventListener('click', () => menu.classList.add('hidden'));
}

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', async () => {
  // Load settings
  try {
    state.settings = await api('GET', '/settings');
    applyTheme(state.settings.theme);
  } catch {}

  // Initial load
  await refreshAll();
  await fetchNotifications();

  // Event listeners
  $('#back-to-dashboard').addEventListener('click', backToDashboard);
  $('#refresh-btn').addEventListener('click', () => {
    Toast.info('Refreshing...');
    if (state.selectedRepoId) selectRepo(state.selectedRepoId);
    else refreshAll();
  });
  $('#settings-btn').addEventListener('click', openSettings);
  $('#notification-btn').addEventListener('click', () => {
    $('#notification-panel').classList.toggle('hidden');
  });

  // Add repo
  $('#add-repo-btn').addEventListener('click', openAddRepoModal);
  $('#close-add-modal').addEventListener('click', closeAddRepoModal);
  $('#cancel-add-repo').addEventListener('click', closeAddRepoModal);
  $('#confirm-add-repo').addEventListener('click', addRepo);
  $('#repo-path-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') addRepo(); });

  // Settings
  $('#close-settings-modal').addEventListener('click', () => $('#settings-modal').classList.add('hidden'));
  $('#cancel-settings').addEventListener('click', () => $('#settings-modal').classList.add('hidden'));
  $('#save-settings').addEventListener('click', saveSettings);

  // Confirm dialog
  $('#confirm-cancel').addEventListener('click', () => {
    $('#confirm-dialog').classList.add('hidden');
    confirmCallback = null;
  });
  $('#confirm-ok').addEventListener('click', () => {
    $('#confirm-dialog').classList.add('hidden');
    if (confirmCallback) confirmCallback();
    confirmCallback = null;
  });

  // AI Generate
  $('#ai-generate-btn').addEventListener('click', handleGenerateAI);

  // Auto refresh
  $('#auto-refresh-toggle').addEventListener('change', (e) => {
    state.autoRefreshEnabled = e.target.checked;
    if (state.autoRefreshEnabled) startAutoRefresh();
    else stopAutoRefresh();
  });
  $('#refresh-interval').addEventListener('change', () => { if (state.autoRefreshEnabled) startAutoRefresh(); });

  // Section toggles
  setupSectionToggles();

  // Commit dropdown
  setupCommitDropdown();

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
    if (e.key === 'Escape') {
      // Close modals
      $$('.modal-overlay').forEach(m => m.classList.add('hidden'));
      $('#notification-panel').classList.add('hidden');
      if (state.selectedRepoId) backToDashboard();
    }
    if (e.key === 'r') { refreshAll(); Toast.info('Refreshed'); }
    if (e.key === 'n') { $('#notification-panel').classList.toggle('hidden'); }
  });

  // Close notification panel on outside click
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.notification-badge')) {
      $('#notification-panel').classList.add('hidden');
    }
  });

  // Close modals on overlay click
  $$('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.classList.add('hidden');
    });
  });

  // Start auto refresh
  startAutoRefresh();

  // Refresh icons
  refreshIcons();

  // Periodic notification check
  setInterval(fetchNotifications, 60000);
});

// Make functions globally accessible for inline onclick handlers
window.selectRepo = selectRepo;
window.openAddRepoModal = openAddRepoModal;
