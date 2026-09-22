# Plan 002: Interactive Branch Switcher Popover & Pull/Fetch/Sync UI in Branch Bar

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 28ee8c3..HEAD -- static/app.js static/index.html static/styles.css`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: L (full day)
- **Risk**: MED — significant DOM injection; must follow existing design patterns exactly
- **Depends on**: `plans/001-branch-management-backend.md`
- **Category**: direction
- **Planned at**: commit `28ee8c3`, 2026-09-22

## Why this matters

After Plan 001 provides the backend endpoints, the branch bar remains static
text. Developers still can't switch branches, create new branches, fetch
remote updates, or pull changes without leaving the app. This plan transforms
the branch bar into a fully interactive command center that matches the
existing `emil-design-eng` design system (Emil Kowalski motion curves,
Lucide-only SVG icons, `.custom-dropdown` popover pattern, Sonner-style
Toast feedback).

## Current state

### Branch bar rendering in `app.js` (lines 390-414):

```javascript
// app.js:390-414 — renderRepoDetail
const hasRemote = Boolean(status.branch.remote_name);
$('#branch-bar').innerHTML = `
  <div class="branch-tag">
    <i data-lucide="git-branch" style="width:14px;height:14px;"></i>
    ${esc(status.branch.name)}
  </div>
  ${hasRemote ? `<span style="color:var(--text-muted);font-size:12px;">→ ${esc(status.branch.remote_name)}</span>` : `
    <button class="btn btn-primary btn-sm" onclick="openPublishModal()" ...>
      <i data-lucide="cloud-upload" ...></i>
      <span>Publish to GitHub</span>
    </button>
  `}
  ${hasRemote ? `
    <div class="ahead-behind">
      ${status.branch.ahead > 0 ? `<span class="ahead">↑ ${status.branch.ahead} ahead</span>` : ''}
      ${status.branch.behind > 0 ? `<span class="behind">↓ ${status.branch.behind} behind</span>` : ''}
      ${status.branch.ahead === 0 && status.branch.behind === 0 ? `<span style="color:var(--success);">Up to date</span>` : ''}
    </div>
  ` : ''}
  <div style="flex:1;"></div>
  <span style="font-size:12px;color:var(--text-muted);">
    ${status.last_commit_time ? `Last commit: ${esc(status.last_commit_time)}` : 'No commits'}
  </span>
`;
```

### Branch bar HTML container in `index.html` (line 147):
```html
<div class="branch-bar" id="branch-bar"></div>
```

### Branch bar CSS in `styles.css` (lines 563-597):
```css
.branch-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px; background: var(--bg-card);
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  margin-bottom: 16px; font-size: 13px;
}
.branch-tag {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--accent-muted); color: var(--accent);
  padding: 4px 10px; border-radius: 20px; font-weight: 600;
  font-size: 12px;
}
.ahead-behind { display: flex; align-items: center; gap: 10px; font-size: 12px; }
.ahead { color: var(--success); }
.behind { color: var(--warning); }
```

### Existing custom dropdown popover pattern in `styles.css` (lines 1157-1246):
```css
.custom-dropdown { position: relative; }
.custom-dropdown-btn {
  display: flex; align-items: center; gap: 4px;
  padding: 3px 8px; border-radius: var(--radius-sm);
  border: 1px solid var(--border); background: var(--bg-card);
  color: var(--text-secondary); cursor: pointer;
  font-size: 12px; transition: all 0.15s var(--ease-out);
}
.custom-dropdown-menu {
  position: absolute; top: calc(100% + 6px); right: 0;
  min-width: 120px; background: var(--bg-card);
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  box-shadow: 0 8px 24px rgba(0,0,0,0.3); z-index: 100;
  animation: popoverDown 160ms var(--ease-out);
}
.custom-dropdown-item {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; cursor: pointer; font-size: 12px;
  color: var(--text-secondary);
  transition: background 0.1s var(--ease-out);
}
.custom-dropdown-item:hover { background: var(--bg-card-hover); color: var(--text-primary); }
```

### API layer in `app.js` (lines 127-146):
```javascript
async function api(method, endpoint, body) {
  try {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API}${endpoint}`, opts);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Request failed');
    }
    return await res.json();
  } catch (err) {
    if (!err.message.includes('Failed to fetch')) Toast.error(err.message);
    throw err;
  }
}
```

### Toast pattern (used everywhere for async actions):
```javascript
await Toast.promise(api('POST', endpoint, body), {
  loading: 'Working...', success: 'Done', error: (e) => e.message
});
```

## Commands you will need

| Purpose      | Command                                      | Expected on success     |
|--------------|----------------------------------------------|-------------------------|
| Server start | `python app.py`                              | Prints banner, port 8765 |
| Reload       | Browser hard refresh (`Ctrl+Shift+R`)        | UI reloads clean         |
| Verify icons | Check browser console for Lucide errors      | No errors                |

## Scope

**In scope** (the only files you should modify):
- `static/app.js`
- `static/styles.css`

**Out of scope** (do NOT touch):
- `static/index.html` — no HTML changes needed; all DOM is injected via JS
- `app.py`, `models.py`, `git_scanner.py` — backend is Plan 001
- Any modal HTML — no new modals needed; branch creation uses an inline
  popover input, not a full modal

## Git workflow

- Branch: `feat/phase1-branch-sync-ui`
- Commit style: `feat(ui): add interactive branch switcher and pull/fetch buttons`

## Steps

### Step 1: Add CSS for the branch picker popover and sync buttons

Append the following CSS to `static/styles.css` immediately after the
existing `.ahead-behind .behind` rule (around line 597):

```css
/* --- Branch Picker Popover --- */
.branch-picker {
  position: relative;
}

.branch-picker-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--accent-muted);
  color: var(--accent);
  padding: 4px 10px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 12px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.15s var(--ease-out);
}
.branch-picker-trigger:hover {
  border-color: var(--accent);
  background: rgba(59, 130, 246, 0.25);
}
.branch-picker-trigger:active {
  transform: scale(0.97);
}

.branch-picker-popover {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  width: 280px;
  max-height: 360px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
  z-index: 200;
  display: flex;
  flex-direction: column;
  animation: popoverDown 160ms var(--ease-out);
}

.branch-picker-search {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
}
.branch-picker-search input {
  width: 100%;
  padding: 6px 10px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 12px;
  outline: none;
  transition: border-color 0.15s var(--ease-out);
}
.branch-picker-search input:focus {
  border-color: var(--accent);
}
.branch-picker-search input::placeholder {
  color: var(--text-muted);
}

.branch-picker-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.branch-picker-group-label {
  padding: 6px 12px 3px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}

.branch-picker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
  transition: background 0.1s var(--ease-out);
}
.branch-picker-item:hover {
  background: var(--bg-card-hover);
  color: var(--text-primary);
}
.branch-picker-item.active {
  color: var(--accent);
  font-weight: 600;
}
.branch-picker-item .check-icon {
  width: 12px;
  flex-shrink: 0;
}

.branch-picker-create {
  padding: 8px 12px;
  border-top: 1px solid var(--border);
}
.branch-picker-create-row {
  display: flex;
  gap: 6px;
}
.branch-picker-create input {
  flex: 1;
  padding: 5px 8px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 12px;
  outline: none;
}
.branch-picker-create input:focus {
  border-color: var(--accent);
}

/* --- Sync Button Group --- */
.sync-btn-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-sync {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s var(--ease-out);
}
.btn-sync:hover {
  border-color: var(--border-hover);
  background: var(--bg-card-hover);
  color: var(--text-primary);
}
.btn-sync:active {
  transform: scale(0.97);
}
.btn-sync.pull-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.btn-sync.fetch-btn:hover {
  border-color: var(--text-muted);
}
```

**Verify**: Open the CSS file, confirm it parses without syntax errors.

### Step 2: Replace the branch bar renderer in `app.js`

Replace the existing branch-bar innerHTML block (lines 391-414 in
`renderRepoDetail`) with the new interactive version:

```javascript
  // Branch bar
  const hasRemote = Boolean(status.branch.remote_name);
  $('#branch-bar').innerHTML = `
    <div class="branch-picker" id="branch-picker">
      <button class="branch-picker-trigger" id="branch-picker-trigger" type="button" title="Switch branch">
        <i data-lucide="git-branch" style="width:14px;height:14px;"></i>
        ${esc(status.branch.name)}
        <i data-lucide="chevron-down" style="width:12px;height:12px;opacity:0.6;"></i>
      </button>
    </div>
    ${hasRemote ? `<span style="color:var(--text-muted);font-size:12px;">→ ${esc(status.branch.remote_name)}</span>` : `
      <button class="btn btn-primary btn-sm" onclick="openPublishModal()" style="gap:6px;padding:3px 9px;" title="Publish this local repository to GitHub">
        <i data-lucide="cloud-upload" style="width:13px;height:13px;"></i>
        <span>Publish to GitHub</span>
      </button>
    `}
    ${hasRemote ? `
      <div class="ahead-behind">
        ${status.branch.ahead > 0 ? `<span class="ahead">↑ ${status.branch.ahead} ahead</span>` : ''}
        ${status.branch.behind > 0 ? `<span class="behind">↓ ${status.branch.behind} behind</span>` : ''}
        ${status.branch.ahead === 0 && status.branch.behind === 0 ? `<span style="color:var(--success);">Up to date</span>` : ''}
      </div>
    ` : ''}
    <div style="flex:1;"></div>
    ${hasRemote ? `
      <div class="sync-btn-group">
        <button class="btn-sync fetch-btn" onclick="handleFetch()" title="Fetch latest from remote">
          <i data-lucide="refresh-cw" style="width:12px;height:12px;"></i>
          Fetch
        </button>
        ${status.branch.behind > 0 ? `
          <button class="btn-sync pull-btn" onclick="handlePull()" title="Pull ${status.branch.behind} commit${status.branch.behind > 1 ? 's' : ''} from remote">
            <i data-lucide="arrow-down-to-line" style="width:12px;height:12px;"></i>
            Pull
          </button>
        ` : ''}
      </div>
    ` : ''}
    <span style="font-size:12px;color:var(--text-muted);">
      ${status.last_commit_time ? `Last commit: ${esc(status.last_commit_time)}` : 'No commits'}
    </span>
  `;
```

After the `refreshIcons()` call at the end of `renderRepoDetail`, add event
binding for the branch picker trigger:

```javascript
  // Bind branch picker
  const trigger = document.getElementById('branch-picker-trigger');
  if (trigger) {
    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleBranchPicker();
    });
  }
```

**Verify**: Start server, select a repo. The branch bar should show the
branch name as a clickable pill with a chevron, plus Fetch/Pull buttons
if a remote is configured.

### Step 3: Add branch picker popover logic in `app.js`

Add the following functions to `app.js` after the existing `handleStash`
function (after line 888):

```javascript
// --- Branch Picker ---
window.toggleBranchPicker = async function() {
  const existing = document.getElementById('branch-picker-popover');
  if (existing) {
    existing.remove();
    return;
  }

  if (!state.selectedRepoId) return;
  const id = state.selectedRepoId;

  // Fetch branches from API
  let branches;
  try {
    branches = await api('GET', `/repos/${id}/branches`);
  } catch {
    Toast.error('Failed to load branches');
    return;
  }

  const localBranches = branches.filter(b => !b.is_remote);
  const remoteBranches = branches.filter(b => b.is_remote);

  const picker = document.getElementById('branch-picker');
  if (!picker) return;

  const popover = document.createElement('div');
  popover.className = 'branch-picker-popover';
  popover.id = 'branch-picker-popover';

  popover.innerHTML = `
    <div class="branch-picker-search">
      <input type="text" id="branch-search-input" placeholder="Search or filter branches..." autocomplete="off" />
    </div>
    <div class="branch-picker-list" id="branch-picker-list">
      ${localBranches.length > 0 ? `
        <div class="branch-picker-group-label">Local Branches</div>
        ${localBranches.map(b => `
          <div class="branch-picker-item ${b.is_active ? 'active' : ''}" data-branch="${esc(b.name)}" data-remote="false">
            <span class="check-icon">${b.is_active ? '<i data-lucide="check" style="width:12px;height:12px;"></i>' : ''}</span>
            <span>${esc(b.name)}</span>
            ${b.tracking ? `<span style="font-size:10px;color:var(--text-muted);margin-left:auto;">${esc(b.tracking)}</span>` : ''}
          </div>
        `).join('')}
      ` : ''}
      ${remoteBranches.length > 0 ? `
        <div class="branch-picker-group-label">Remote Branches</div>
        ${remoteBranches.map(b => {
          const shortName = b.name.includes('/') ? b.name.split('/').slice(1).join('/') : b.name;
          return `
            <div class="branch-picker-item" data-branch="${esc(b.name)}" data-remote="true">
              <span class="check-icon"></span>
              <span>${esc(shortName)}</span>
              <span style="font-size:10px;color:var(--text-muted);margin-left:auto;">${esc(b.name.split('/')[0])}</span>
            </div>
          `;
        }).join('')}
      ` : ''}
    </div>
    <div class="branch-picker-create">
      <div class="branch-picker-create-row">
        <input type="text" id="new-branch-input" placeholder="New branch name..." />
        <button class="btn btn-primary btn-sm" id="create-branch-btn" style="white-space:nowrap;padding:4px 10px;">
          <i data-lucide="plus" style="width:12px;height:12px;"></i>
          Create
        </button>
      </div>
    </div>
  `;

  picker.appendChild(popover);
  refreshIcons();

  // Focus search
  const searchInput = document.getElementById('branch-search-input');
  if (searchInput) {
    searchInput.focus();
    searchInput.addEventListener('input', () => {
      const query = searchInput.value.toLowerCase().trim();
      popover.querySelectorAll('.branch-picker-item').forEach(item => {
        const name = (item.dataset.branch || '').toLowerCase();
        item.style.display = name.includes(query) ? '' : 'none';
      });
    });
  }

  // Checkout on click
  popover.querySelectorAll('.branch-picker-item').forEach(item => {
    item.addEventListener('click', async () => {
      const branchName = item.dataset.branch;
      if (item.classList.contains('active')) {
        popover.remove();
        return;
      }

      // Warn if dirty working tree
      if (state.repoDetail?.changed_files?.length > 0) {
        const proceed = confirm(`You have ${state.repoDetail.changed_files.length} uncommitted change(s). Switching branch may lose them.\n\nProceed?`);
        if (!proceed) return;
      }

      try {
        await Toast.promise(
          api('POST', `/repos/${id}/branches/checkout`, { branch_name: branchName }),
          { loading: `Switching to ${branchName}...`, success: (r) => r.message, error: (e) => e.message }
        );
        popover.remove();
        selectRepo(id);
      } catch {}
    });
  });

  // Create branch
  const createBtn = document.getElementById('create-branch-btn');
  const newBranchInput = document.getElementById('new-branch-input');
  if (createBtn && newBranchInput) {
    const doCreate = async () => {
      const name = newBranchInput.value.trim();
      if (!name) {
        Toast.warning('Enter a branch name');
        newBranchInput.focus();
        return;
      }
      // Validate branch name (basic)
      if (!/^[a-zA-Z0-9._\/-]+$/.test(name)) {
        Toast.error('Invalid branch name. Use alphanumeric, dots, hyphens, underscores, or slashes.');
        return;
      }
      try {
        await Toast.promise(
          api('POST', `/repos/${id}/branches/checkout`, { branch_name: name, create: true }),
          { loading: `Creating branch '${name}'...`, success: (r) => r.message, error: (e) => e.message }
        );
        popover.remove();
        selectRepo(id);
      } catch {}
    };
    createBtn.addEventListener('click', doCreate);
    newBranchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') doCreate();
    });
  }

  // Close on outside click
  const closeHandler = (e) => {
    if (!popover.contains(e.target) && e.target !== document.getElementById('branch-picker-trigger')) {
      popover.remove();
      document.removeEventListener('click', closeHandler);
    }
  };
  // Delay to avoid immediate close from the trigger click
  setTimeout(() => document.addEventListener('click', closeHandler), 10);
};
```

**Verify**: Click the branch pill in the detail view. The popover should
appear with local/remote branches, a search input, and a create-branch
input at the bottom.

### Step 4: Add fetch and pull handler functions in `app.js`

Add these after the branch picker code:

```javascript
// --- Fetch & Pull ---
window.handleFetch = async function() {
  if (!state.selectedRepoId) return;
  const id = state.selectedRepoId;
  try {
    await Toast.promise(
      api('POST', `/repos/${id}/fetch`),
      { loading: 'Fetching remote...', success: (r) => r.message, error: (e) => e.message }
    );
    // Refresh the detail view to update ahead/behind counts
    selectRepo(id);
  } catch {}
};

window.handlePull = async function() {
  if (!state.selectedRepoId) return;
  const id = state.selectedRepoId;

  // Warn if there are uncommitted changes
  if (state.repoDetail?.changed_files?.length > 0) {
    const proceed = confirm(
      `You have ${state.repoDetail.changed_files.length} uncommitted change(s). ` +
      `Pulling may cause merge conflicts.\n\nProceed with pull?`
    );
    if (!proceed) return;
  }

  try {
    await Toast.promise(
      api('POST', `/repos/${id}/pull`),
      { loading: 'Pulling from remote...', success: (r) => r.message, error: (e) => e.message }
    );
    selectRepo(id);
  } catch {}
};
```

**Verify**: With a repo that has a remote, click "Fetch" — expect a toast
confirming fetch. If the repo is behind, the "Pull" button should appear and
pulling should update the ahead/behind counts.

### Step 5: Increment the CSS version cache-buster in `index.html`

In `static/index.html` line 11, change the version query parameter:

```html
<link rel="stylesheet" href="/static/styles.css?v=3.0">
```

**Verify**: Hard refresh in browser. New styles load without stale cache.

## Test plan

Manual verification checklist (no test framework exists):

1. **Branch Picker Opens**: Click branch pill → popover appears with
   branches, search input, and create input.
2. **Search Filters**: Type in search → branches filter by name.
3. **Checkout Local Branch**: Click a non-active local branch → toast shows
   "Switched to branch 'X'" → view refreshes with new branch.
4. **Checkout Remote Branch**: Click a remote branch → creates local tracking
   branch → view refreshes.
5. **Create Branch**: Type a name in the create input → click "Create" →
   toast shows "Created and switched" → view refreshes.
6. **Duplicate Guard**: Try creating a branch that already exists → error
   toast "Branch 'X' already exists".
7. **Dirty Tree Warning**: With uncommitted changes, try switching → confirm
   dialog appears.
8. **Fetch Button**: Click "Fetch" → toast "Fetched from 'origin'" → ahead/
   behind counts may update.
9. **Pull Button**: When `behind > 0`, "Pull" button appears → click → toast
   shows result → behind count drops to 0.
10. **Outside Click Close**: Click outside popover → popover closes.
11. **Escape Key**: Press `Escape` → popover closes (via existing global
    Escape handler that closes modals/popovers).
12. **No Remote**: For repos without a remote, "Publish to GitHub" button
    still shows; Fetch/Pull buttons do not appear.

## Done criteria

- [ ] Branch pill in branch bar is clickable and opens the popover
- [ ] Popover shows local branches, remote branches (grouped), search, create
- [ ] Clicking a branch switches to it (with dirty-tree warning)
- [ ] Creating a branch works and auto-switches
- [ ] "Fetch" button calls `POST /repos/{id}/fetch` and refreshes counts
- [ ] "Pull" button appears when `behind > 0` and calls `POST /repos/{id}/pull`
- [ ] All buttons use `Toast.promise` for loading/success/error feedback
- [ ] No Lucide icon errors in browser console
- [ ] No files outside in-scope list are modified (`git status`)

## STOP conditions

Stop and report back (do not improvise) if:

- `GET /api/repos/{id}/branches` returns 404 or is not available — Plan 001
  has not been executed yet.
- The existing `renderRepoDetail` function structure has changed from the
  excerpts in "Current state".
- The popover DOM injection causes layout shifts or overlaps with the sidebar.
- `refreshIcons()` fails or Lucide icons don't render inside the popover.

## Maintenance notes

- The branch picker popover is injected into DOM on each click and removed
  on close. This avoids stale state issues — each open fetches fresh branches.
- Remote branches are displayed with the short name (after the `/`), with
  the remote name (before the `/`) shown as muted trailing text.
- When fetching or pulling, the entire `selectRepo(id)` is called to reload
  all data. This is intentional — a fetch/pull can change the file tree,
  ahead/behind counts, and stash state simultaneously.
- Future enhancement: the "Pull" button could offer a dropdown with "Pull
  (merge)" vs "Pull (rebase)" options. This plan keeps it simple.
