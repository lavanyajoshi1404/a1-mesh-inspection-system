import React from 'react';
import { PRODUCT_PROFILES } from '../constants';

export default function Products({ selectedProfile, setSelectedProfile, onNavigate }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="page-sub-header">
        <div>
          <div className="page-title">Standard Product Profiles</div>
          <div className="page-meta">Calibrated tolerances and engineering pitch requirements</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 18 }}>
        {PRODUCT_PROFILES.map(profile => {
          const isSelected = selectedProfile.id === profile.id;
          return (
            <div
              key={profile.id}
              className="qc-card"
              style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', border: isSelected ? '2px solid var(--accent-primary)' : '1px solid var(--border-organic)' }}
            >
              <div>
                <div className="qc-card-header">
                  <span className="qc-card-title">{profile.name}</span>
                  <span className="badge-sage font-tabular">{profile.id}</span>
                </div>
                <div className="qc-card-body">
                  <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginBottom: 14, lineHeight: 1.5 }}>{profile.description}</p>
                  <table className="qc-table">
                    <tbody>
                      <tr><td>Wire Diameter</td><td className="font-tabular" style={{ textAlign: 'right', color: 'var(--text-primary)' }}>{profile.wire_diameter_mm} mm</td></tr>
                      <tr><td>Nominal Pitch H</td><td className="font-tabular" style={{ textAlign: 'right', color: 'var(--text-primary)' }}>{profile.aperture_h_mm} mm</td></tr>
                      <tr><td>Nominal Pitch V</td><td className="font-tabular" style={{ textAlign: 'right', color: 'var(--text-primary)' }}>{profile.aperture_v_mm} mm</td></tr>
                      <tr><td>Standard</td><td style={{ textAlign: 'right', fontSize: 11.5, color: 'var(--text-primary)' }}>{profile.standards}</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <div style={{ padding: '0 18px 18px' }}>
                <button
                  onClick={() => { setSelectedProfile(profile); onNavigate('visual'); }}
                  className={`btn-qc ${isSelected ? 'btn-qc-primary' : 'btn-qc-secondary'}`}
                  style={{ width: '100%' }}
                >
                  {isSelected ? '✓ Active Target Profile' : 'Select Profile'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
