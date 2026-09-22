# Plan 004: Discard Changes UI & Complete Stash Creation UI

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
- **Risk**: MED — destructive discard actions need confirmation guards
- **Depends on**: `plans/003-discard-stash-backend.md`
- **Category**: direction
- **Planned at**: commit `28ee8c3`, 2026-09-22

## Why this matters

After Plan 003 provides the backend, developers still cannot discard changes
or create stashes from the GitPulse UI. This plan adds:

1. A **"Discard All" danger button** in the Changed Files section header.
2. A per-file **inline discard icon** on hover in the file tree.
3. A **"+ Stash Changes" button** in the Stash section header.
4. A **stash creation inline form** with optional message input.

All interactions follow the `emil-design-eng` design system: Lucide-only SVG
icons, tactile `scale(0.97)` active state, `var(--ease-out)` transitions,
Sonner-style Toast feedback, and confirmation dialogs for destructive actions.

## Current state

### Changed Files section header in `index.html` (lines 150-168):

```html
<div class="section-panel" id="tree-panel">
  <div class="section-header" data-section="tree">
    <div class="section-title">
      <i data-lucide="folder-tree" style="width:16px;height:16px;"></i>
      <span>Changed Files</span>
      <span class="section-badge" id="tree-count">0</span>
      <button class="btn btn-selection-toggle" id="toggle-stage-all-btn" onclick="event.stopPropagation(); toggleSelectAll();" title="Toggle selection of all files">
        <i data-lucide="check-square" id="toggle-stage-all-icon" style="width: 12px; height: 12px;"></i>
        <span id="toggle-stage-all-label">Select All</span>
      </button>
    </div>
    <div style="display:flex;align-items:center;gap:10px;">
      <span id="selected-files-summary" style="font-size:11px;color:var(--text-muted);"></span>
      <i data-lucide="chevron-down" style="width:14px;height:14px;color:var(--text-muted);"></i>
    </div>
  </div>
  <div class="section-content open" id="tree-content">
    <div class="git-tree" id="git-tree"></div>
  </div>
</div>
```

### File tree row rendering in `app.js` (lines 540-556):

```javascript
// Each file row:
return `
  <div class="tree-item" onclick="showFileDiff('${esc(node.path)}')" data-file="${esc(node.path)}">
    ${indent}
    <span class="custom-checkbox file-checkbox ${isChecked ? 'checked' : ''}" data-file="${esc(node.path)}" onclick="event.stopPropagation();toggleStageFile('${esc(node.path)}')" title="Select for commit">
      <i data-lucide="check" class="custom-checkbox-check"></i>
    </span>
    <i data-lucide="${icon}" class="tree-file-icon"></i>
    <span class="tree-item-name">${esc(node.name)}</span>
    <span class="git-status-badge ${statusCls}">${badge}</span>
  </div>
`;
```

### Stash section header in `index.html` (lines 191-203):

```html
<div class="section-panel" id="stash-panel">
  <div class="section-header" data-section="stash">
    <div class="section-title">
      <i data-lucide="archive"></i>
      <span>Stash</span>
      <span class="section-badge" id="stash-count">0</span>
    </div>
    <i data-lucide="chevron-down" style="width:14px;height:14px;color:var(--text-muted);"></i>
  </div>
  <div class="section-content" id="stash-content">
    <div id="stash-list"></div>
  </div>
</div>
```

### Existing `showConfirm` dialog in `app.js` (lines 1086-1091):

```javascript
function showConfirm(title, message, onConfirm) {
  $('#confirm-title').textContent = title;
  $('#confirm-message').textContent = message;
  confirmCallback = onConfirm;
  $('#confirm-dialog').classList.remove('hidden');
}
```

### Existing button classes in `styles.css`:

```css
.btn-danger { background: var(--error); color: white; }
.btn-danger:hover { background: #dc2626; }
.btn-sm { padding: 4px 10px; font-size: 12px; gap: 5px; }
.btn-ghost { background: transparent; color: var(--text-secondary); border: 1px solid transparent; }
.btn-ghost:hover { background: var(--bg-card-hover); color: var(--text-primary); }
```

## Commands you will need

| Purpose      | Command                                      | Expected on success     |
|--------------|----------------------------------------------|-------------------------|
| Server start | `python app.py`                              | Prints banner |
| Reload       | Browser hard refresh (`Ctrl+Shift+R`)        | Fresh UI                |

## Scope

**In scope** (the only files you should modify):
- `static/app.js`
- `static/index.html`
- `static/styles.css`

**Out of scope** (do NOT touch):
- `app.py`, `models.py`, `git_scanner.py` — backend is Plan 003
- `ai_commit.py`, `notifier.py`

## Git workflow

- Branch: `feat/phase2-discard-stash-ui`
- Commit style: `feat(ui): add discard changes and stash creation controls`

## Steps

### Step 1: Add CSS for discard and stash-create UI components

Append the following to `static/styles.css` (after any branch-picker styles
added by Plan 002, or at the end of the component section):

```css
/* --- Discard Button (inline per-file) --- */
.tree-item .tree-discard-btn {
  opacity: 0;
  padding: 2px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 3px;
  margin-left: auto;
  flex-shrink: 0;
  transition: all 0.12s var(--ease-out);
}
.tree-item:hover .tree-discard-btn {
  opacity: 1;
}
.tree-item .tree-discard-btn:hover {
  color: var(--error);
  background: var(--error-muted);
}
.tree-item .tree-discard-btn:active {
  transform: scale(0.9);
}

/* --- Stash Create Inline Form --- */
.stash-create-form {
  display: flex;
  gap: 6px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
}
.stash-create-form input {
  flex: 1;
  padding: 6px 10px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 12px;
  outline: none;
  transition: border-color 0.15s var(--ease-out);
}
.stash-create-form input:focus {
  border-color: var(--accent);
}
.stash-create-form input::placeholder {
  color: var(--text-muted);
}

/* --- Discard All Button --- */
.btn-discard-all {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 11px;
  font-weight: 500;
  transition: all 0.15s var(--ease-out);
}
.btn-discard-all:hover {
  border-color: var(--error);
  color: var(--error);
  background: var(--error-muted);
}
.btn-discard-all:active {
  transform: scale(0.97);
}
```

**Verify**: CSS file parses without errors.

### Step 2: Add "Discard All" button to the Changed Files section header

In `static/index.html`, find the `<div style="display:flex;align-items:center;gap:10px;">` inside `#tree-panel`'s `.section-header` (line 161). Add a "Discard All" button before the `<span id="selected-files-summary">`:

Change lines 161-164 from:
```html
<div style="display:flex;align-items:center;gap:10px;">
  <span id="selected-files-summary" style="font-size:11px;color:var(--text-muted);"></span>
  <i data-lucide="chevron-down" style="width:14px;height:14px;color:var(--text-muted);"></i>
</div>
```

To:
```html
<div style="display:flex;align-items:center;gap:10px;">
  <button class="btn-discard-all" id="discard-all-btn" onclick="event.stopPropagation(); handleDiscardAll();" title="Discard all uncommitted changes">
    <i data-lucide="undo-2" style="width:11px;height:11px;"></i>
    <span>Discard All</span>
  </button>
  <span id="selected-files-summary" style="font-size:11px;color:var(--text-muted);"></span>
  <i data-lucide="chevron-down" style="width:14px;height:14px;color:var(--text-muted);"></i>
</div>
```

**Verify**: Check browser — the "Discard All" button appears in the Changed
Files section header, right of the title area. It should be subtle (muted
text) and turn red on hover.

### Step 3: Add "+ Stash Changes" button to the Stash section header

In `static/index.html`, find the stash `.section-header` (around line 192).
Add a "Stash Changes" button inside the `.section-title` div, after the
`#stash-count` badge:

Change lines 193-197 from:
```html
<div class="section-title">
  <i data-lucide="archive"></i>
  <span>Stash</span>
  <span class="section-badge" id="stash-count">0</span>
</div>
```

To:
```html
<div class="section-title">
  <i data-lucide="archive"></i>
  <span>Stash</span>
  <span class="section-badge" id="stash-count">0</span>
  <button class="btn btn-selection-toggle" id="stash-create-btn" onclick="event.stopPropagation(); toggleStashCreateForm();" title="Stash current changes">
    <i data-lucide="plus" style="width:12px;height:12px;"></i>
    <span>Stash Changes</span>
  </button>
</div>
```

Also, add a stash creation form container inside `#stash-content`, BEFORE
`#stash-list`. Change lines 200-202 from:

```html
<div class="section-content" id="stash-content">
  <div id="stash-list"></div>
</div>
```

To:
```html
<div class="section-content" id="stash-content">
  <div id="stash-create-form-container" class="hidden"></div>
  <div id="stash-list"></div>
</div>
```

**Verify**: Check browser — "+ Stash Changes" button appears in the stash
section header. It should match the "Select All" button styling.

### Step 4: Add per-file discard icon to the file tree builder in `app.js`

In `static/app.js`, find the file row template in `buildTreeHTML` (around
lines 545-555). Add a discard button after the `.git-status-badge`:

Change the file row return from:
```javascript
return `
  <div class="tree-item" onclick="showFileDiff('${esc(node.path)}')" data-file="${esc(node.path)}">
    ${indent}
    <span class="custom-checkbox file-checkbox ${isChecked ? 'checked' : ''}" data-file="${esc(node.path)}" onclick="event.stopPropagation();toggleStageFile('${esc(node.path)}')" title="Select for commit">
      <i data-lucide="check" class="custom-checkbox-check"></i>
    </span>
    <i data-lucide="${icon}" class="tree-file-icon"></i>
    <span class="tree-item-name">${esc(node.name)}</span>
    <span class="git-status-badge ${statusCls}">${badge}</span>
  </div>
`;
```

To:
```javascript
return `
  <div class="tree-item" onclick="showFileDiff('${esc(node.path)}')" data-file="${esc(node.path)}">
    ${indent}
    <span class="custom-checkbox file-checkbox ${isChecked ? 'checked' : ''}" data-file="${esc(node.path)}" onclick="event.stopPropagation();toggleStageFile('${esc(node.path)}')" title="Select for commit">
      <i data-lucide="check" class="custom-checkbox-check"></i>
    </span>
    <i data-lucide="${icon}" class="tree-file-icon"></i>
    <span class="tree-item-name">${esc(node.name)}</span>
    <span class="git-status-badge ${statusCls}">${badge}</span>
    <button class="tree-discard-btn" onclick="event.stopPropagation(); handleDiscardFile('${esc(node.path)}')" title="Discard changes to this file">
      <i data-lucide="undo-2" style="width:12px;height:12px;"></i>
    </button>
  </div>
`;
```

**Verify**: In browser, hover over a file in the tree. A subtle undo icon
should appear on the right, turning red on hover.

### Step 5: Add discard handler functions in `app.js`

Add the following after the existing `handleStash` function (or after the
branch picker / fetch/pull handlers from Plan 002):

```javascript
// --- Discard Changes ---
window.handleDiscardFile = function(filePath) {
  if (!state.selectedRepoId) return;
  const id = state.selectedRepoId;

  showConfirm(
    'Discard Changes',
    `Discard all changes to "${filePath}"? This cannot be undone.`,
    async () => {
      try {
        await Toast.promise(
          api('POST', `/repos/${id}/discard`, { files: [filePath] }),
          { loading: 'Discarding...', success: 'Changes discarded', error: (e) => e.message }
        );
        state.stagedFiles.delete(filePath);
        selectRepo(id);
      } catch {}
    }
  );
};

window.handleDiscardAll = function() {
  if (!state.selectedRepoId) return;
  const id = state.selectedRepoId;

  const count = state.repoDetail?.changed_files?.length || 0;
  if (count === 0) {
    Toast.info('No changes to discard');
    return;
  }

  showConfirm(
    'Discard All Changes',
    `This will permanently discard ALL ${count} changed and untracked file(s). This action CANNOT be undone.\n\nAre you sure?`,
    async () => {
      try {
        await Toast.promise(
          api('POST', `/repos/${id}/discard`, {}),
          { loading: 'Discarding all changes...', success: 'All changes discarded', error: (e) => e.message }
        );
        state.stagedFiles.clear();
        selectRepo(id);
      } catch {}
    }
  );
};
```

**Verify**: Click the discard icon on a file row. Confirm dialog appears.
Click "Discard All" in section header. Confirm dialog appears with file count.

### Step 6: Add stash creation toggle and submit handler in `app.js`

Add the following after the discard handlers:

```javascript
// --- Stash Creation ---
window.toggleStashCreateForm = function() {
  const container = document.getElementById('stash-create-form-container');
  if (!container) return;

  if (container.classList.contains('hidden')) {
    container.classList.remove('hidden');
    container.innerHTML = `
      <div class="stash-create-form">
        <input type="text" id="stash-message-input" placeholder="Stash message (optional)..." />
        <label style="display:flex;align-items:center;gap:4px;font-size:11px;color:var(--text-secondary);white-space:nowrap;cursor:pointer;">
          <input type="checkbox" id="stash-include-untracked" checked style="accent-color:var(--accent);" />
          Untracked
        </label>
        <button class="btn btn-primary btn-sm" id="stash-submit-btn" style="white-space:nowrap;">
          <i data-lucide="archive" style="width:12px;height:12px;"></i>
          Stash
        </button>
      </div>
    `;
    refreshIcons();

    const input = document.getElementById('stash-message-input');
    if (input) input.focus();

    // Bind submit
    document.getElementById('stash-submit-btn')?.addEventListener('click', submitStash);
    input?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') submitStash();
    });
  } else {
    container.classList.add('hidden');
    container.innerHTML = '';
  }
};

async function submitStash() {
  if (!state.selectedRepoId) return;
  const id = state.selectedRepoId;

  const messageInput = document.getElementById('stash-message-input');
  const untrackedCheckbox = document.getElementById('stash-include-untracked');
  const message = messageInput?.value.trim() || null;
  const includeUntracked = untrackedCheckbox?.checked ?? true;

  try {
    await Toast.promise(
      api('POST', `/repos/${id}/stash`, {
        message: message,
        include_untracked: includeUntracked,
      }),
      { loading: 'Stashing changes...', success: (r) => r.message, error: (e) => e.message }
    );

    // Hide the form and refresh
    const container = document.getElementById('stash-create-form-container');
    if (container) {
      container.classList.add('hidden');
      container.innerHTML = '';
    }
    state.stagedFiles.clear();
    selectRepo(id);
  } catch {}
}
```

**Verify**: Click "+ Stash Changes" button. An inline form appears with a
message input, an "Untracked" checkbox, and a "Stash" button. Enter a message
and click "Stash" — the form disappears, the stash list updates, and the
changed files list clears.

### Step 7: Increment CSS cache-buster version

In `static/index.html` line 11 (or wherever the CSS version is), update:
```html
<link rel="stylesheet" href="/static/styles.css?v=3.1">
```

(Or `v=3.1` if Plan 002 already set it to `v=3.0`.)

**Verify**: Hard refresh shows updated UI.

## Test plan

Manual verification checklist:

1. **Per-File Discard (tracked modified file)**:
   - Modify a tracked file. Hover the file in the tree. Click the undo icon.
   - Confirm dialog appears. Click OK.
   - File reverts to HEAD state. Toast: "Changes discarded".

2. **Per-File Discard (untracked file)**:
   - Create a new file. Click discard on it.
   - File is deleted from disk. Toast: "Changes discarded".

3. **Discard All**:
   - Make multiple modifications and create untracked files.
   - Click "Discard All" in section header.
   - Confirm dialog shows file count. Click OK.
   - All changes discarded. Tree shows "No changes". Toast: "All changes discarded".

4. **Discard All on clean repo**:
   - With no changes, click "Discard All".
   - Toast: "No changes to discard" (no dialog).

5. **Create Stash (with message)**:
   - Make changes. Click "+ Stash Changes".
   - Enter "WIP feature". Click "Stash".
   - Toast: "Changes stashed as: WIP feature".
   - Changed files list clears. Stash count increments.

6. **Create Stash (empty working tree)**:
   - On clean repo, click "+ Stash Changes" → "Stash".
   - Toast error: "No changes to stash".

7. **Create Stash (toggle untracked)**:
   - Create an untracked file. Open stash form.
   - Uncheck "Untracked". Stash.
   - The untracked file should remain.

8. **Stash Apply/Pop/Drop still works**:
   - Existing stash buttons continue to work alongside new creation UI.

9. **Toggle stash form**:
   - Click "+ Stash Changes" to open. Click again to close.

10. **Keyboard Submit**:
    - In stash message input, press Enter → submits.

## Done criteria

- [ ] Per-file discard icon appears on hover, confirms, and discards
- [ ] "Discard All" button in section header confirms and discards all changes
- [ ] "+ Stash Changes" button toggles inline creation form
- [ ] Stash creation with message works and refreshes the list
- [ ] Stash creation on clean repo shows appropriate error
- [ ] All buttons use `showConfirm` for destructive actions
- [ ] All async actions use `Toast.promise` for feedback
- [ ] No Lucide icon console errors
- [ ] No files outside in-scope list are modified (`git status`)

## STOP conditions

Stop and report back (do not improvise) if:

- `POST /api/repos/{id}/discard` or `POST /api/repos/{id}/stash` returns
  404 — Plan 003 has not been executed yet.
- The file tree row template in `buildTreeHTML` has changed structure.
- The stash section HTML in `index.html` has changed.
- `showConfirm` function is not available (renamed or removed).
- The discard button overlaps or clips with the status badge in the tree row.

## Maintenance notes

- The per-file discard button uses `opacity: 0` + `.tree-item:hover opacity: 1`
  to show only on hover. This is the same pattern used by VS Code's Source
  Control view. On touch devices, all buttons should always be visible —
  consider a `@media (hover: none)` rule that sets `opacity: 1` always.
- The stash creation form is injected into `#stash-create-form-container`
  on toggle and cleared on close. This avoids stale state.
- "Discard All" sends `{}` (empty object) to the discard endpoint, which
  triggers `discard_all_changes` on the backend. Sending `{ files: null }`
  would also work — the backend treats both the same.
- Future: a "Discard Selected" button could discard only the files in
  `state.stagedFiles`, using `{ files: [...stagedFiles] }`.
