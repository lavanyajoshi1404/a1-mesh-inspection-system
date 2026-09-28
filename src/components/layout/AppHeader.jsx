import React from 'react';
import { RefreshCw, ShieldCheck, LogOut } from 'lucide-react';

export default function AppHeader({ user, onSignOut, selectedProfile, stats, onRefresh }) {
  return (
    <header className="master-header">
      {/* Brand */}
      <div className="brand-badge">
        <div className="brand-icon">A1</div>
        <div>
          <div className="brand-title">A-1 MESH INSPECTION SYSTEM</div>
          <div className="brand-subtitle">Automated Robot Vision &amp; Metrology Station</div>
        </div>
      </div>

      {/* Right controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        {/* Live stats */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 12.5 }}>
          <div style={{ display: 'flex', gap: 5 }}>
            <span style={{ color: 'var(--text-muted)' }}>Profile:</span>
            <strong style={{ color: 'var(--text-primary)' }}>{selectedProfile.name}</strong>
          </div>
          <div style={{ display: 'flex', gap: 5 }}>
            <span style={{ color: 'var(--text-muted)' }}>Pass Yield:</span>
            <span className="font-tabular" style={{ color: 'var(--status-pass-text)', fontWeight: 700 }}>
              {stats.pass_rate == null ? 'N/A' : `${stats.pass_rate}%`}
            </span>
          </div>
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={onRefresh} className="btn-qc btn-qc-secondary" title="Refresh Statistics">
            <RefreshCw style={{ width: 13, height: 13 }} />
          </button>

          {user && (
            <>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '4px 10px', borderRadius: 6,
                background: '#EBF1F5', border: '1px solid #CBD5E1',
                fontSize: 11.5, fontWeight: 600, color: '#0F3D5E',
                maxWidth: 200, overflow: 'hidden',
              }}>
                <ShieldCheck style={{ width: 13, height: 13, flexShrink: 0 }} />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user.email}
                </span>
              </div>
              <button
                onClick={onSignOut}
                className="btn-qc btn-qc-secondary"
                title="Sign Out"
                style={{ color: '#991B1B', borderColor: '#FCA5A5' }}
              >
                <LogOut style={{ width: 13, height: 13 }} /> Sign Out
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
