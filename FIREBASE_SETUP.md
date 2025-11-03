# Firebase Authentication Setup Guide

This guide will walk you through setting up Firebase Authentication for the Manochitra application.

## Step 1: Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **"Add project"** or select an existing project
3. Enter your project name (e.g., "Manochitra")
4. Follow the setup wizard (you can disable Google Analytics if not needed)
5. Click **"Create project"**

## Step 2: Enable Authentication Methods

1. In your Firebase project, click on **"Authentication"** in the left sidebar
2. Click on **"Get started"** if this is your first time
3. Go to the **"Sign-in method"** tab
4. Enable the following providers:

### Email/Password Authentication
- Click on **"Email/Password"**
- Toggle **"Enable"** to ON
- Click **"Save"**

### Google Authentication
- Click on **"Google"**
- Toggle **"Enable"** to ON
- Enter a project support email
- Click **"Save"**

## Step 3: Register Your Web App

1. In the Firebase Console, click on the **gear icon** (⚙️) next to "Project Overview"
2. Select **"Project settings"**
3. Scroll down to **"Your apps"** section
4. Click on the **Web icon** (`</>`) to add a web app
5. Enter an app nickname (e.g., "Manochitra Web")
6. Check **"Also set up Firebase Hosting"** if you want (optional)
7. Click **"Register app"**

## Step 4: Get Your Firebase Configuration

After registering your app, you'll see a configuration object that looks like this:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  authDomain: "your-project-id.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-project-id.appspot.com",
  messagingSenderId: "123456789012",
  appId: "1:123456789012:web:abcdef1234567890"
};
```

## Step 5: Update Your Firebase Configuration File

1. Open `static/firebase-config.js` in your project
2. Replace the placeholder values with your actual Firebase configuration:

```javascript
const firebaseConfig = {
    apiKey: "YOUR_ACTUAL_API_KEY",
    authDomain: "YOUR_ACTUAL_PROJECT_ID.firebaseapp.com",
    projectId: "YOUR_ACTUAL_PROJECT_ID",
    storageBucket: "YOUR_ACTUAL_PROJECT_ID.appspot.com",
    messagingSenderId: "YOUR_ACTUAL_MESSAGING_SENDER_ID",
    appId: "YOUR_ACTUAL_APP_ID"
};
```

## Step 6: Configure Authorized Domains

1. In Firebase Console, go to **Authentication** > **Settings** > **Authorized domains**
2. Add your development domain:
   - `localhost` (should already be there)
   - `127.0.0.1` (add if not present)
3. When deploying to production, add your production domain here

## Step 7: Test Your Setup

1. Start your Flask application:
   ```bash
   python app.py
   ```

2. Open your browser and go to `http://127.0.0.1:5000`

3. Try the following:
   - **Sign Up**: Create a new account with email/password
   - **Google Sign-In**: Sign in with your Google account
   - **Login**: Log in with your created credentials
   - **Profile**: Check if your profile appears in the top right corner on the frontpage
   - **Logout**: Test the logout functionality

## Step 8: Verify Users in Firebase Console

1. Go to **Authentication** > **Users** in Firebase Console
2. You should see all registered users listed here
3. You can manage users, disable accounts, or delete users from this panel

## Features Implemented

### ✅ Email/Password Authentication
- User registration with email and password
- Login with email and password
- Password reset via email
- Form validation and error handling

### ✅ Google OAuth Authentication
- One-click Google Sign-In
- Automatic profile picture from Google account
- Seamless authentication flow

### ✅ User Profile Display
- User avatar in top right corner (photo or initials)
- Display name and email
- Dropdown menu with profile options
- Logout functionality

### ✅ Protected Routes
- Automatic redirect to login if not authenticated
- Automatic redirect to frontpage if already logged in
- Session persistence across page refreshes

## Security Best Practices

1. **Never commit your Firebase config to public repositories** if it contains sensitive data
2. Set up **Firebase Security Rules** for production
3. Enable **Email Verification** for new users (optional but recommended)
4. Configure **Password Requirements** in Firebase Console
5. Set up **Rate Limiting** to prevent abuse
6. Use **Environment Variables** for sensitive configuration in production

## Troubleshooting

### Issue: "Firebase not defined"
- Make sure Firebase SDK scripts are loaded before your custom scripts
- Check browser console for any loading errors

### Issue: "Popup blocked" for Google Sign-In
- Allow popups for your domain in browser settings
- Or use redirect method instead of popup

### Issue: "User not redirecting to frontpage"
- Check browser console for JavaScript errors
- Verify Firebase configuration is correct
- Make sure `auth.onAuthStateChanged` listener is working

### Issue: "CORS errors"
- Add your domain to Authorized Domains in Firebase Console
- Check if you're using the correct protocol (http/https)

## Next Steps

1. **Add Email Verification**: Require users to verify their email before accessing the dashboard
2. **Implement Password Strength Meter**: Show users how strong their password is
3. **Add Social Login Providers**: Facebook, Twitter, GitHub, etc.
4. **User Profile Management**: Allow users to update their profile information
5. **Backend Verification**: Verify Firebase tokens on the Flask backend for API security

## Support

For more information, visit:
- [Firebase Authentication Documentation](https://firebase.google.com/docs/auth)
- [Firebase Web SDK Reference](https://firebase.google.com/docs/reference/js/auth)
