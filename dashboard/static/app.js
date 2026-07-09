async function submitYoutube() {
  const url = document.getElementById('yt-url').value.trim();
  if (!url) { alert('Paste a YouTube URL first'); return; }
  const form = new FormData();
  form.set('youtube_url', url);
  await fetch('/api/render/youtube', { method: 'POST', body: form });
  document.getElementById('yt-url').value = '';
  loadRenders();
  setTimeout(loadRenders, 4000);
}

async function submitUpload() {
  const fileInput = document.getElementById('upload-file');
  const start = parseFloat(document.getElementById('upload-start').value);
  const end = parseFloat(document.getElementById('upload-end').value);
  if (!fileInput.files.length) { alert('Choose a video file first'); return; }
  if (!(end > start)) { alert('End time must be after start time'); return; }

  const form = new FormData();
  form.set('file', fileInput.files[0]);
  form.set('start_seconds', start);
  form.set('end_seconds', end);
  form.set('mode', document.getElementById('upload-mode').value);

  const resp = await fetch('/api/render/upload', { method: 'POST', body: form });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    alert(data.detail || 'Upload failed');
    return;
  }
  fileInput.value = '';
  loadRenders();
  setTimeout(loadRenders, 4000);
}

let _errorsById = {};

function viewError(renderId) {
  const content = _errorsById[renderId] || '(no details)';
  document.getElementById('log-modal-content').textContent = content;
  document.getElementById('log-modal').classList.remove('hidden');
}

function closeLogModal() {
  document.getElementById('log-modal').classList.add('hidden');
}

function statusBadge(status) {
  if (status === 'success') return '<span class="text-emerald-400">✓ done</span>';
  if (status === 'failed') return '<span class="text-red-400">✗ failed</span>';
  return '<span class="text-amber-400">⏳ rendering...</span>';
}

async function loadRenders() {
  const renders = await (await fetch('/api/renders')).json();
  _errorsById = {};
  renders.forEach(r => { if (r.error) _errorsById[r.id] = r.error; });
  document.getElementById('renders-table').innerHTML = renders.map(r => `
    <tr class="border-t border-slate-800">
      <td class="py-2 text-xs text-slate-400">${r.created_at}</td>
      <td class="py-2 max-w-[180px] truncate" title="${r.source || ''}">${r.kind === 'youtube' ? '🔗 ' : '📁 '}${r.source || '-'}</td>
      <td class="py-2 max-w-[160px] truncate">${r.hook_title || '-'}</td>
      <td class="py-2">${statusBadge(r.status)}</td>
      <td class="py-2">
        ${r.status === 'success'
          ? `<a href="/api/renders/${r.id}/download" class="text-xs bg-emerald-700 hover:bg-emerald-600 rounded px-2 py-1">Download</a>`
          : r.status === 'failed'
            ? `<button onclick="viewError(${r.id})" class="text-xs bg-red-900 hover:bg-red-800 rounded px-2 py-1">View error</button>`
            : '<span class="text-xs text-slate-500">—</span>'}
      </td>
    </tr>`).join('') || '<tr><td class="py-2 text-slate-500" colspan="5">No renders yet — try one above.</td></tr>';
}

loadRenders();
setInterval(loadRenders, 6000);
