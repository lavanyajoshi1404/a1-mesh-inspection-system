import React from 'react';
import { NAVIGATION_ITEMS } from '../../constants';

export default function NavRail({ activePage, onNavigate }) {
  return (
    <aside className="navigation-rail">
      <div className="nav-section">
        <div className="nav-group-title">Inspection Modules</div>
        <div className="nav-items" style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {NAVIGATION_ITEMS.map(item => (
            <button
              key={item.id}
              className={`nav-link ${activePage === item.id ? 'active' : ''}`}
              onClick={() => onNavigate(item.id)}
            >
              <item.icon style={{ width: 15, height: 15 }} />
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* System status */}
      <div
        className="nav-status"
        style={{ marginTop: 'auto', padding: '14px 10px', borderTop: '1px solid var(--border-organic)' }}
      >
        <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>
          System Status
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: 'var(--text-secondary)' }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', backgroundColor: 'var(--status-pass-border)' }} />
          <span>Pipeline Active &amp; Ready</span>
        </div>
      </div>
    </aside>
  );
}
