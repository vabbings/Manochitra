// Firebase setup and authentication handlers for login.html
// This file is a JavaScript module loaded via <script type="module" src="./auth.js"></script>

// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.5.0/firebase-app.js";
import {
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  sendPasswordResetEmail,
  signOut
} from "https://www.gstatic.com/firebasejs/12.5.0/firebase-auth.js";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyAYSMQZKCM3pfwBjX03I_qw8tKbhhpgPsg",
  authDomain: "manochitra2-4bde9.firebaseapp.com",
  projectId: "manochitra2-4bde9",
  storageBucket: "manochitra2-4bde9.firebasestorage.app",
  messagingSenderId: "354851602043",
  appId: "1:354851602043:web:926535cabbe046b54cacde"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

// Elements
const loginForm = document.getElementById('loginForm');
const messageArea = document.getElementById('messageArea');
const forgotPasswordLink = document.getElementById('forgotPasswordLink');
const googleButton = document.getElementById('googleSignIn');
const signUpLink = document.getElementById('signUpLink');

function showMessage(text, tone = 'info') {
  if (!messageArea) return;
  messageArea.textContent = text;
  messageArea.classList.remove('hidden', 'text-gray-600', 'text-red-600', 'text-green-600');
  if (tone === 'error') messageArea.classList.add('text-red-600');
  else if (tone === 'success') messageArea.classList.add('text-green-600');
  else messageArea.classList.add('text-gray-600');
}

function handleAuthError(err) {
  const code = err && err.code ? err.code : '';
  if (code === 'auth/unauthorized-domain') {
    const origin = window.location.origin || '(unknown origin)';
    showMessage(`Unauthorized domain: ${origin}. Add this host in Firebase → Authentication → Settings → Authorized domains.`, 'error');
    console.error('Firebase unauthorized-domain for origin:', origin);
  } else {
    showMessage((err && (err.message || err.toString())) || 'Authentication error', 'error');
  }
}

// Email/password sign in
if (loginForm) {
  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const email = document.getElementById('email')?.value.trim();
    const password = document.getElementById('password')?.value;
    showMessage('Signing in...');
    try {
      await signInWithEmailAndPassword(auth, email, password);
      showMessage('Success! Redirecting...', 'success');
      setTimeout(() => { window.location.href = '/'; }, 600);
    } catch (err) {
      handleAuthError(err);
    }
  });
}

// Google sign in
if (googleButton) {
  googleButton.addEventListener('click', async (e) => {
    e.preventDefault();
    showMessage('Opening Google sign-in...');
    try {
      await signInWithPopup(auth, googleProvider);
      showMessage('Signed in with Google. Redirecting...', 'success');
      setTimeout(() => { window.location.href = '/'; }, 600);
    } catch (err) {
      if (err && err.code === 'auth/popup-blocked') {
        // Fallback to redirect if the browser blocked the popup
        showMessage('Popup blocked. Switching to redirect sign-in...', 'error');
        try {
          await signInWithRedirect(auth, googleProvider);
        } catch (e2) {
          handleAuthError(e2);
        }
      } else {
        handleAuthError(err);
      }
    }
  });
}

// Forgot password
if (forgotPasswordLink) {
  forgotPasswordLink.addEventListener('click', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email')?.value.trim();
    if (!email) { showMessage('Enter your email above to reset password.', 'error'); return; }
    showMessage('Sending password reset email...');
    try {
      await sendPasswordResetEmail(auth, email);
      showMessage('Password reset email sent.', 'success');
    } catch (err) {
      handleAuthError(err);
    }
  });
}

// Simple signup via link (creates account with current form fields)
if (signUpLink) {
  signUpLink.addEventListener('click', async (e) => {
    e.preventDefault();
    const email = document.getElementById('email')?.value.trim();
    const password = document.getElementById('password')?.value;
    if (!email || !password) { showMessage('Enter email and password to sign up.', 'error'); return; }
    showMessage('Creating your account...');
    try {
      await createUserWithEmailAndPassword(auth, email, password);
      showMessage('Account created. Redirecting...', 'success');
      setTimeout(() => { window.location.href = '/'; }, 600);
    } catch (err) {
      handleAuthError(err);
    }
  });
}

// Observe auth state (optional)
onAuthStateChanged(auth, () => {
  // Hook for future UI changes on login/logout if needed
});

// Complete redirect flow if it was used
(async () => {
  try {
    const result = await getRedirectResult(auth);
    if (result && result.user) {
      showMessage('Signed in with Google (redirect). Redirecting...', 'success');
      setTimeout(() => { window.location.href = '/'; }, 600);
    }
  } catch (err) {
    handleAuthError(err);
  }
})();

// Optional: expose a signOut helper for future use
window.manochitraSignOut = async () => {
  try {
    await signOut(auth);
    showMessage('Signed out.');
  } catch (err) {
    handleAuthError(err);
  }
};

// Helpful console output
console.info('Auth origin:', window.location.origin);
if (window.location.protocol === 'file:') {
  showMessage('Open this page over http:// (not file://). Example: npx serve -l 5173', 'error');
}


