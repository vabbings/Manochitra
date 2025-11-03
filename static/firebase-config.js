// Firebase Configuration
// Replace these values with your actual Firebase project credentials
// Get these from: Firebase Console > Project Settings > Your apps > Web app

const firebaseConfig = {
    apiKey: "AIzaSyAYSMQZKCM3pfwBjX03I_qw8tKbhhpgPsg",
    authDomain: "manochitra2-4bde9.firebaseapp.com",
    projectId: "manochitra2-4bde9",
    storageBucket: "manochitra2-4bde9.firebasestorage.app",
    messagingSenderId: "354851602043",
    appId: "1:354851602043:web:926535cabbe046b54cacde"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Initialize Firebase Authentication
const auth = firebase.auth();

// Configure Google Auth Provider
const googleProvider = new firebase.auth.GoogleAuthProvider();
