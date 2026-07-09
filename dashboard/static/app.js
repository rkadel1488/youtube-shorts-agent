function togglePlatformFields() {
  const platform = document.getElementById('new-platform').value;
  document.getElementById('youtube-fields').classList.toggle('hidden', platform !== 'youtube');
  document.getElementById('meta-fields').classList.toggle('hidden', platform !== 'meta');
}

async function addAccount() {
  const platform = document.getElementById('new-platform').value;
  const label = document.getElementById('new-label').value.trim();
  const errEl = document.getElementById('add-account-error');
  errEl.textContent = '';
  if (!label) { errEl.textContent = 'Label is required'; return; }

  const form = new FormData();
  form.set('platform', platform);
  form.set('label', label);
  if (platform === 'youtube') {
    form.set('youtube_token_json', document.getElementById('new-youtube-token').value);
  } else {
    form.set('meta_access_token', document.getElementById('new-meta-token').value);
    form.set('post_to_instagram', document.getElementById('new-post-ig').checked);
    form.set('post_to_facebook', document.getElementById('new-post-fb').checked);
  }

  const resp = await fetch('/api/accounts', { method: 'POST', body: form });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    errEl.textContent = data.detail || 'Failed to add account';
    return;
  }
  document.getElementById('add-account-form').classList.add('hidden');
  document.getElementById('new-label').value = '';
  document.getElementById('new-youtube-token').value = '';
  document.getElementById('new-meta-token').value = '';
  await loadAccounts();
}

async function toggleAccount(id) {
  await fetch(`/api/accounts/${id}/toggle`, { method: 'POST' });
  await loadAccounts();
}

async function deleteAccount(id) {
  if (!confirm('Remove this account? It will stop posting immediately.')) return;
  await fetch(`/api/accounts/${id}`, { method: 'DELETE' });
  await loadAccounts();
}

async function testAccount(id, btn) {
  btn.textContent = 'Testing...';
  const resp = await fetch(`/api/accounts/${id}/test`, { method: 'POST' });
  const data = await resp.json();
  alert(data.ok ? `✓ ${data.detail}` : `✗ ${data.detail}`);
  btn.textContent = 'Test';
}

function platformBadge(platform) {
  const colors = { youtube: 'bg-red-900 text-red-300', meta: 'bg-blue-900 text-blue-300' };
  const label = { youtube: 'YouTube', meta: 'Meta (IG+FB)' };
  return `<span class="text-xs px-2 py-0.5 rounded-full ${colors[platform] || ''}">${label[platform] || platform}</span>`;
}

async function loadAccounts() {
  const accounts = await (await fetch('/api/accounts')).json();
  const tbody = document.getElementById('accounts-table');
  tbody.innerHTML = accounts.map(a => `
    <tr class="border-t border-slate-800">
      <td class="py-2">${platformBadge(a.platform)}</td>
      <td class="py-2">${a.label}</td>
      <td class="py-2">${a.enabled ? '<span class="text-emerald-400">● enabled</span>' : '<span class="text-slate-500">○ disabled</span>'}</td>
      <td class="py-2 space-x-2">
        <button onclick="testAccount(${a.id}, this)" class="text-xs bg-slate-700 hover:bg-slate-600 rounded px-2 py-1">Test</button>
        <button onclick="toggleAccount(${a.id})" class="text-xs bg-slate-700 hover:bg-slate-600 rounded px-2 py-1">${a.enabled ? 'Disable' : 'Enable'}</button>
        <button onclick="deleteAccount(${a.id})" class="text-xs bg-red-900 hover:bg-red-800 rounded px-2 py-1">Delete</button>
      </td>
    </tr>`).join('') || '<tr><td class="py-2 text-slate-500" colspan="4">No accounts yet — add one above.</td></tr>';

  const checkboxHtml = accounts.map(a =>
    `<label class="text-sm bg-slate-800 rounded-lg px-3 py-1.5"><input type="checkbox" class="acc-cb mr-1" value="${a.id}" ${a.enabled ? 'checked' : ''}>${a.label}</label>`
  ).join('') || '<span class="text-slate-500 text-sm">No accounts configured.</span>';
  document.getElementById('run-checkboxes').innerHTML = checkboxHtml;
  document.getElementById('clip-checkboxes').innerHTML = checkboxHtml.replaceAll('acc-cb', 'clip-cb');
}

async function runNow() {
  const ids = [...document.querySelectorAll('.acc-cb:checked')].map(cb => cb.value);
  if (!ids.length) { alert('Select at least one account'); return; }
  const form = new FormData();
  form.set('account_ids', ids.join(','));
  await fetch('/api/jobs/run-now', { method: 'POST', body: form });
  alert('Job started — check Job history below in a few minutes.');
  setTimeout(loadJobs, 3000);
}

async function runClip() {
  const url = document.getElementById('clip-url').value.trim();
  const ids = [...document.querySelectorAll('.clip-cb:checked')].map(cb => cb.value);
  if (!url) { alert('Paste a YouTube URL'); return; }
  if (!ids.length) { alert('Select at least one account'); return; }
  const form = new FormData();
  form.set('youtube_url', url);
  form.set('account_ids', ids.join(','));
  await fetch('/api/jobs/clip', { method: 'POST', body: form });
  alert('Clip job started — check Job history below in a few minutes.');
  setTimeout(loadJobs, 3000);
}

async function viewJobLog(jobId) {
  const job = await (await fetch(`/api/jobs/${jobId}`)).json();
  document.getElementById('log-modal-content').textContent =
    (job.log || '(no log captured)') + '\n\n--- result_json ---\n' + (job.result_json || '(none)');
  document.getElementById('log-modal').classList.remove('hidden');
}

function closeLogModal() {
  document.getElementById('log-modal').classList.add('hidden');
}

function resultSummary(job) {
  if (!job.result_json) return '';
  try {
    const r = JSON.parse(job.result_json);
    if (!r.results) return job.status === 'failed' ? (r.error || '').slice(0, 120) : '';
    return r.results.map(x => {
      if (x.platform === 'youtube') return `YT: ${x.status}`;
      if (x.platform === 'meta') return `IG: ${x.instagram || '-'}, FB: ${x.facebook || '-'}`;
      return '';
    }).join(' · ');
  } catch { return ''; }
}

async function loadJobs() {
  const jobs = await (await fetch('/api/jobs')).json();
  document.getElementById('jobs-table').innerHTML = jobs.map(j => `
    <tr class="border-t border-slate-800">
      <td class="py-2 text-xs text-slate-400">${j.created_at}</td>
      <td class="py-2">${j.kind}</td>
      <td class="py-2 max-w-xs truncate" title="${j.source || ''}">${j.source || '-'}</td>
      <td class="py-2">${j.status === 'success' ? '<span class="text-emerald-400">success</span>' : j.status === 'failed' ? '<span class="text-red-400">failed</span>' : '<span class="text-amber-400">running</span>'}</td>
      <td class="py-2 text-xs text-slate-400">${resultSummary(j)}</td>
      <td class="py-2"><button onclick="viewJobLog(${j.id})" class="text-xs bg-slate-700 hover:bg-slate-600 rounded px-2 py-1">View log</button></td>
    </tr>`).join('') || '<tr><td class="py-2 text-slate-500" colspan="5">No jobs yet.</td></tr>';
}

togglePlatformFields();
loadAccounts();
loadJobs();
setInterval(loadJobs, 15000);
