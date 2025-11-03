// Handles registration from signup.html against Flask + SQLite

const form = document.getElementById('signupForm');
const messageArea = document.getElementById('messageArea');

function showMessage(text, tone = 'info') {
  messageArea.textContent = text;
  messageArea.classList.remove('hidden', 'text-gray-600', 'text-red-600', 'text-green-600');
  if (tone === 'error') messageArea.classList.add('text-red-600');
  else if (tone === 'success') messageArea.classList.add('text-green-600');
  else messageArea.classList.add('text-gray-600');
}

async function api(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {})
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.ok === false) {
    const err = (data && (data.error || data.message)) || `Request failed (${res.status})`;
    throw new Error(err);
  }
  return data;
}

form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fullName = document.getElementById('fullName')?.value.trim();
  const email = document.getElementById('email')?.value.trim();
  const password = document.getElementById('password')?.value;
  const confirm = document.getElementById('confirm')?.value;
  if (!email || !password || !confirm) { showMessage('Fill all required fields.', 'error'); return; }
  if (password !== confirm) { showMessage('Passwords do not match.', 'error'); return; }
  if (password.length < 6) { showMessage('Password must be at least 6 characters.', 'error'); return; }
  showMessage('Creating account...');
  try {
    await api('/api/register', { email, password, fullName });
    showMessage('Account created. Redirecting to login...', 'success');
    setTimeout(() => { window.location.href = '/login.html'; }, 800);
  } catch (err) {
    showMessage(err.message || 'Sign up failed', 'error');
  }
});


