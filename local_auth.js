// Local (SQLite + Flask) authentication for login.html
// Expects elements with ids: loginForm, messageArea, forgotPasswordLink, googleSignIn (ignored), signUpLink

const loginForm = document.getElementById('loginForm');
const messageArea = document.getElementById('messageArea');
const forgotPasswordLink = document.getElementById('forgotPasswordLink');
const signUpLink = document.getElementById('signUpLink');

function showMessage(text, tone = 'info') {
    if (!messageArea) return;
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

if (loginForm) {
    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const email = document.getElementById('email')?.value.trim();
        const password = document.getElementById('password')?.value;
        showMessage('Signing in...');
        try {
            await api('/api/login', { email, password });
            showMessage('Success! Redirecting...', 'success');
            setTimeout(() => { window.location.href = '/frontpage.html'; }, 600);
        } catch (e) {
            showMessage(e.message || 'Login failed', 'error');
        }
    });
}

// Do not intercept the Sign Up link; it should navigate to /signup.html

if (forgotPasswordLink) {
    forgotPasswordLink.addEventListener('click', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email')?.value.trim();
        if (!email) { showMessage('Enter your email above to reset password.', 'error'); return; }
        showMessage('Processing password reset (demo)...');
        try {
            await api('/api/forgot', { email });
            showMessage('If this were production, a reset link would be emailed.', 'success');
        } catch (e3) {
            showMessage(e3.message || 'Unable to process reset', 'error');
        }
    });
}

console.info('Local auth ready');


