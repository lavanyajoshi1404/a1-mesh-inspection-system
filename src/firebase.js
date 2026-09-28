import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getAnalytics } from 'firebase/analytics';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: "AIzaSyBfT9mF6dVWi_a-xioAxxnxEH_hoycsZTo",
  authDomain: "a1-mesh-inspection-system.firebaseapp.com",
  projectId: "a1-mesh-inspection-system",
  storageBucket: "a1-mesh-inspection-system.firebasestorage.app",
  messagingSenderId: "191891159724",
  appId: "1:191891159724:web:f60098af6806de700b3d09",
  measurementId: "G-RNN44KP7PP"
};

const app = initializeApp(firebaseConfig);

export const analytics = getAnalytics(app);
export const auth = getAuth(app);
export const db = getFirestore(app);
