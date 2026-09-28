import React, { useState } from 'react';
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  updateProfile,
} from 'firebase/auth';
import { doc, setDoc, serverTimestamp } from 'firebase/firestore';
import { auth, db } from './firebase';
import {
  ShieldCheck, LogIn, UserPlus, Eye, EyeOff,
  User, Briefcase, Hash, Phone, Building2, Mail, Lock, BadgeCheck,
} from 'lucide-react';

const DEPARTMENTS = [
  'Quality Control',
  'Production',
  'Engineering',
  'Maintenance',
  'Management',
  'R&D',
  'Logistics',
  'IT / Systems',
];

const ROLES = [
  'QC Inspector',
  'Senior QC Inspector',
  'QC Supervisor',
  'Production Engineer',
  'Shift Manager',
  'Plant Manager',
  'System Administrator',
];

export default function Auth() {
  const [mode, setMode] = useState('login');

  // ── Login fields
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');

  // ── Register fields
  const [fullName,       setFullName]       = useState('');
  const [employeeId,     setEmployeeId]     = useState('');
  const [designation,    setDesignation]    = useState('');
  const [department,     setDepartment]     = useState('');
  const [phone,          setPhone]          = useState('');
  const [regEmail,       setRegEmail]       = useState('');
  const [regPassword,    setRegPassword]    = useState('');
  const [confirmPwd,     setConfirmPwd]     = useState('');

  const [showPwd,    setShowPwd]    = useState(false);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState('');
  const [success,    setSuccess]    = useState('');

  const reset = () => { setError(''); setSuccess(''); };

  // ── Validation ──────────────────────────────────────────────
  const validateRegister = () => {
    if (!fullName.trim())    return 'Full name is required.';
    if (!employeeId.trim())  return 'Employee ID is required.';
    if (!/^[A-Za-z0-9\-]+$/.test(employeeId.trim()))
      return 'Employee ID may only contain letters, numbers, and hyphens.';
    if (!designation)        return 'Please select a role / designation.';
    if (!department)         return 'Please select a department.';
    if (phone && !/^\+?[\d\s\-]{7,15}$/.test(phone.trim()))
      return 'Enter a valid phone number.';
    if (!regEmail.trim())    return 'Email address is required.';
    if (!regPassword)        return 'Password is required.';
    if (regPassword.length < 6) return 'Password must be at least 6 characters.';
    if (regPassword !== confirmPwd) return 'Passwords do not match.';
    return null;
  };

  // ── Submit ──────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();
    reset();

    if (mode === 'login') {
      if (!email || !password) { setError('Email and password are required.'); return; }
    } else {
      const err = validateRegister();
      if (err) { setError(err); return; }
    }

    setLoading(true);
    try {
      if (mode === 'login') {
        await signInWithEmailAndPassword(auth, email, password);
      } else {
        // 1. Create Firebase Auth user
        const cred = await createUserWithEmailAndPassword(auth, regEmail.trim(), regPassword);

        // 2. Set display name
        await updateProfile(cred.user, { displayName: fullName.trim() });

        // 3. Save extended profile to Firestore
        await setDoc(doc(db, 'admin_users', cred.user.uid), {
          uid:         cred.user.uid,
          full_name:   fullName.trim(),
          employee_id: employeeId.trim().toUpperCase(),
          designation,
          department,
          phone:       phone.trim() || null,
          email:       regEmail.trim(),
          role:        'admin',
          created_at:  serverTimestamp(),
        });

        setSuccess(`Account created for ${fullName.trim()}. Welcome to A-1 Mesh Inspection System.`);
      }
    } catch (err) {
      const messages = {
        'auth/user-not-found':        'No account found with this email.',
        'auth/wrong-password':        'Incorrect password.',
        'auth/invalid-credential':    'Invalid email or password.',
        'auth/email-already-in-use':  'An account with this email already exists.',
        'auth/invalid-email':         'Please enter a valid email address.',
        'auth/too-many-requests':     'Too many attempts. Please try again later.',
        'auth/network-request-failed':'Network error. Check your connection.',
      };
      setError(messages[err.code] || err.message || 'Authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  // ── Styles ──────────────────────────────────────────────────
  const input = {
    width: '100%', padding: '9px 12px 9px 36px',
    borderRadius: 6, border: '1px solid #CBD5E1',
    fontSize: 13, color: '#1A2530', outline: 'none',
    background: '#F8FAFC', fontFamily: 'inherit',
    transition: 'border-color 0.15s',
  };
  const inputNoIcon = { ...input, paddingLeft: 12 };
  const label = {
    fontSize: 11, fontWeight: 700, color: '#64748B',
    textTransform: 'uppercase', letterSpacing: '0.06em',
    marginBottom: 5, display: 'block',
  };
  const iconWrap = {
    position: 'absolute', left: 10, top: '50%',
    transform: 'translateY(-50%)', pointerEvents: 'none',
    color: '#94A3B8',
  };
  const field = (mb = 14) => ({ marginBottom: mb, position: 'relative' });

  return (
    <div style={{
      minHeight: '100vh', width: '100vw', background: '#F4F7F9',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      padding: '24px 16px',
    }}>
      <div style={{
        width: '100%', maxWidth: mode === 'register' ? 520 : 420,
        background: '#FFFFFF', borderRadius: 12,
        border: '1px solid #E2E8F0',
        boxShadow: '0 4px 24px rgba(0,0,0,0.07)',
        overflow: 'hidden',
        transition: 'max-width 0.3s ease',
      }}>

        {/* ── Header ── */}
        <div style={{ background: '#0F3D5E', padding: '24px 32px 20px', textAlign: 'center' }}>
          <div style={{
            width: 48, height: 48, background: 'rgba(255,255,255,0.15)',
            borderRadius: 10, display: 'inline-flex', alignItems: 'center',
            justifyContent: 'center', marginBottom: 10,
          }}>
            <ShieldCheck style={{ width: 26, height: 26, color: '#FFFFFF' }} />
          </div>
          <div style={{ fontSize: 17, fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.01em' }}>
            A-1 MESH INSPECTION SYSTEM
          </div>
          <div style={{ fontSize: 11.5, color: 'rgba(255,255,255,0.65)', marginTop: 3 }}>
            Admin Access Portal · A-1 Fence Products Company
          </div>
        </div>

        {/* ── Tab switcher ── */}
        <div style={{ display: 'flex', borderBottom: '1px solid #E2E8F0', background: '#F8FAFC' }}>
          {[
            { key: 'login',    label: 'Sign In',        Icon: LogIn    },
            { key: 'register', label: 'Register Admin', Icon: UserPlus },
          ].map(({ key, label: lbl, Icon }) => (
            <button key={key} onClick={() => { setMode(key); reset(); }} style={{
              flex: 1, padding: '12px 0', fontSize: 12.5,
              fontWeight: mode === key ? 800 : 600,
              color: mode === key ? '#0F3D5E' : '#64748B',
              background: mode === key ? '#FFFFFF' : 'transparent',
              border: 'none',
              borderBottom: mode === key ? '2px solid #0F3D5E' : '2px solid transparent',
              cursor: 'pointer', display: 'flex', alignItems: 'center',
              justifyContent: 'center', gap: 6, transition: 'all 0.15s',
              fontFamily: 'inherit',
            }}>
              <Icon style={{ width: 14, height: 14 }} />
              {lbl}
            </button>
          ))}
        </div>

        {/* ── Form ── */}
        <form onSubmit={handleSubmit} style={{ padding: '22px 32px 26px' }}>

          {/* Banners */}
          {error && (
            <div style={{ marginBottom: 14, padding: '9px 12px', borderRadius: 6, background: '#FEE2E2', color: '#991B1B', fontSize: 12, fontWeight: 600, border: '1px solid #FCA5A5' }}>
              {error}
            </div>
          )}
          {success && (
            <div style={{ marginBottom: 14, padding: '9px 12px', borderRadius: 6, background: '#DCFCE7', color: '#166534', fontSize: 12, fontWeight: 600, border: '1px solid #86EFAC' }}>
              {success}
            </div>
          )}

          {/* ════════════════ LOGIN FIELDS ════════════════ */}
          {mode === 'login' && (
            <>
              <div style={field(14)}>
                <label style={label}>Email Address</label>
                <div style={{ position: 'relative' }}>
                  <span style={iconWrap}><Mail style={{ width: 14, height: 14 }} /></span>
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                    placeholder="admin@a1fence.com" style={input} autoComplete="email" required />
                </div>
              </div>
              <div style={field(24)}>
                <label style={label}>Password</label>
                <div style={{ position: 'relative' }}>
                  <span style={iconWrap}><Lock style={{ width: 14, height: 14 }} /></span>
                  <input type={showPwd ? 'text' : 'password'} value={password}
                    onChange={e => setPassword(e.target.value)} placeholder="••••••••"
                    style={{ ...input, paddingRight: 40 }} autoComplete="current-password" required />
                  <button type="button" onClick={() => setShowPwd(p => !p)} tabIndex={-1} style={{
                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: '#94A3B8', padding: 2,
                  }}>
                    {showPwd ? <EyeOff style={{ width: 16, height: 16 }} /> : <Eye style={{ width: 16, height: 16 }} />}
                  </button>
                </div>
              </div>
            </>
          )}

          {/* ════════════════ REGISTER FIELDS ════════════════ */}
          {mode === 'register' && (
            <>
              {/* Section: Personal Info */}
              <div style={{ fontSize: 10, fontWeight: 800, color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10, paddingBottom: 5, borderBottom: '1px solid #F1F5F9' }}>
                Personal Information
              </div>

              {/* Full Name */}
              <div style={field()}>
                <label style={label}>Full Name</label>
                <div style={{ position: 'relative' }}>
                  <span style={iconWrap}><User style={{ width: 14, height: 14 }} /></span>
                  <input type="text" value={fullName} onChange={e => setFullName(e.target.value)}
                    placeholder="e.g. Lavanya Sharma" style={input} required />
                </div>
              </div>

              {/* Employee ID + Phone — 2 col */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
                <div>
                  <label style={label}>Employee ID</label>
                  <div style={{ position: 'relative' }}>
                    <span style={iconWrap}><Hash style={{ width: 14, height: 14 }} /></span>
                    <input type="text" value={employeeId} onChange={e => setEmployeeId(e.target.value)}
                      placeholder="e.g. A1-EMP-042" style={input} required />
                  </div>
                </div>
                <div>
                  <label style={label}>Phone (optional)</label>
                  <div style={{ position: 'relative' }}>
                    <span style={iconWrap}><Phone style={{ width: 14, height: 14 }} /></span>
                    <input type="tel" value={phone} onChange={e => setPhone(e.target.value)}
                      placeholder="+91 98765 43210" style={input} />
                  </div>
                </div>
              </div>

              {/* Section: Work Details */}
              <div style={{ fontSize: 10, fontWeight: 800, color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10, paddingBottom: 5, borderBottom: '1px solid #F1F5F9' }}>
                Work Details
              </div>

              {/* Designation + Department — 2 col */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
                <div>
                  <label style={label}>Role / Designation</label>
                  <div style={{ position: 'relative' }}>
                    <span style={iconWrap}><BadgeCheck style={{ width: 14, height: 14 }} /></span>
                    <select value={designation} onChange={e => setDesignation(e.target.value)}
                      style={{ ...input, paddingLeft: 34, appearance: 'none', cursor: 'pointer' }} required>
                      <option value="">Select role…</option>
                      {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label style={label}>Department</label>
                  <div style={{ position: 'relative' }}>
                    <span style={iconWrap}><Building2 style={{ width: 14, height: 14 }} /></span>
                    <select value={department} onChange={e => setDepartment(e.target.value)}
                      style={{ ...input, paddingLeft: 34, appearance: 'none', cursor: 'pointer' }} required>
                      <option value="">Select dept…</option>
                      {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                </div>
              </div>

              {/* Section: Account Credentials */}
              <div style={{ fontSize: 10, fontWeight: 800, color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10, paddingBottom: 5, borderBottom: '1px solid #F1F5F9' }}>
                Account Credentials
              </div>

              {/* Email */}
              <div style={field()}>
                <label style={label}>Email Address</label>
                <div style={{ position: 'relative' }}>
                  <span style={iconWrap}><Mail style={{ width: 14, height: 14 }} /></span>
                  <input type="email" value={regEmail} onChange={e => setRegEmail(e.target.value)}
                    placeholder="admin@a1fence.com" style={input} autoComplete="email" required />
                </div>
              </div>

              {/* Password + Confirm — 2 col */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 22 }}>
                <div>
                  <label style={label}>Password</label>
                  <div style={{ position: 'relative' }}>
                    <span style={iconWrap}><Lock style={{ width: 14, height: 14 }} /></span>
                    <input type={showPwd ? 'text' : 'password'} value={regPassword}
                      onChange={e => setRegPassword(e.target.value)} placeholder="min 6 chars"
                      style={{ ...input, paddingRight: 36 }} autoComplete="new-password" required />
                    <button type="button" onClick={() => setShowPwd(p => !p)} tabIndex={-1} style={{
                      position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)',
                      background: 'none', border: 'none', cursor: 'pointer', color: '#94A3B8', padding: 2,
                    }}>
                      {showPwd ? <EyeOff style={{ width: 14, height: 14 }} /> : <Eye style={{ width: 14, height: 14 }} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label style={label}>Confirm Password</label>
                  <div style={{ position: 'relative' }}>
                    <span style={iconWrap}><Lock style={{ width: 14, height: 14 }} /></span>
                    <input type={showPwd ? 'text' : 'password'} value={confirmPwd}
                      onChange={e => setConfirmPwd(e.target.value)} placeholder="repeat password"
                      style={input} autoComplete="new-password" required />
                  </div>
                </div>
              </div>
            </>
          )}

          {/* ── Submit button ── */}
          <button type="submit" disabled={loading} style={{
            width: '100%', padding: '11px 0', borderRadius: 7,
            background: loading ? '#CBD5E1' : '#0F3D5E',
            color: '#FFFFFF', fontSize: 13.5, fontWeight: 700,
            border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            letterSpacing: '0.02em', fontFamily: 'inherit', transition: 'background 0.15s',
          }}>
            {loading ? (
              <>
                <span style={{
                  width: 15, height: 15, border: '2px solid rgba(255,255,255,0.4)',
                  borderTop: '2px solid #fff', borderRadius: '50%',
                  display: 'inline-block', animation: 'spin 0.7s linear infinite',
                }} />
                {mode === 'login' ? 'Signing in…' : 'Creating account…'}
              </>
            ) : mode === 'login' ? (
              <><LogIn style={{ width: 15, height: 15 }} /> Sign In</>
            ) : (
              <><UserPlus style={{ width: 15, height: 15 }} /> Create Admin Account</>
            )}
          </button>
        </form>

        {/* ── Footer ── */}
        <div style={{
          padding: '10px 32px 16px', borderTop: '1px solid #F1F5F9',
          textAlign: 'center', fontSize: 11, color: '#94A3B8',
        }}>
          A-1 Fence Products Company · Automated Inspection System
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
