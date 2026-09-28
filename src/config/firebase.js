// Re-export firebase services from the root firebase.js
// This config layer lets pages/hooks import from a stable path.
export { auth, db, analytics } from '../firebase';
