import React from 'react';
import { Trash2 } from 'lucide-react';

export default function Analytics({ stats, historyData, resetStats }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="page-sub-header">
        <div>
          <div className="page-title">Production Yield Analytics</div>
          <div className="page-meta">Aggregated quality performance across batch inspections</div>
        </div>
        <button onClick={resetStats} className="btn-qc btn-qc-secondary" style={{ color: 'var(--status-fail-text)' }}>
          <Trash2 style={{ width: 13, height: 13 }} /> Reset Stats
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        {[
          { label: 'Total Inspected',        value: stats.total_inspected,                                              color: 'var(--text-primary)' },
          { label: 'Pass Rate',              value: stats.pass_rate == null ? 'N/A' : `${stats.pass_rate}%`,            color: 'var(--status-pass-text)' },
          { label: 'Mean Quality Index',     value: stats.avg_quality_score == null ? 'N/A' : `${stats.avg_quality_score}%`, color: 'var(--text-primary)' },
          { label: 'Avg Pipeline Latency',   value: `${stats.avg_latency_ms} ms`,                                       color: 'var(--text-secondary)' },
          { label: 'Review / Rework',        value: stats.rework_count,                                                 color: 'var(--status-warning-text)' },
          { label: 'Rejected',               value: stats.reject_count,                                                 color: 'var(--status-fail-text)' },
        ].map(({ label, value, color }) => (
          <div key={label} className="qc-card" style={{ padding: 18 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>{label}</div>
            <div className="font-tabular" style={{ fontSize: 28, fontWeight: 800, color, marginTop: 4 }}>{value}</div>
          </div>
        ))}
      </div>

      <div className="qc-card">
        <div className="qc-card-header">
          <span className="qc-card-title">Recent Inspection Records</span>
          <span className="badge-sage font-tabular">{historyData.length} shown</span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="qc-table">
            <thead>
              <tr>
                <th>Inspection</th><th>Sample</th><th>Profile</th><th>Decision</th>
                <th style={{ textAlign: 'right' }}>Score</th>
                <th style={{ textAlign: 'right' }}>Defects</th>
                <th style={{ textAlign: 'right' }}>Latency</th>
              </tr>
            </thead>
            <tbody>
              {historyData.length ? historyData.slice().reverse().map((rec, idx) => (
                <tr key={rec.inspection_id || `${rec.timestamp}-${idx}`}>
                  <td className="font-tabular">{rec.inspection_id || '—'}</td>
                  <td>{rec.filename || '—'}</td>
                  <td>{rec.profile_id || '—'}</td>
                  <td>{rec.verdict || rec.classification || '—'}</td>
                  <td className="font-tabular" style={{ textAlign: 'right' }}>{rec.quality_score ?? '—'}%</td>
                  <td className="font-tabular" style={{ textAlign: 'right' }}>{rec.defects_count ?? '—'}</td>
                  <td className="font-tabular" style={{ textAlign: 'right' }}>{rec.latency_ms ?? '—'} ms</td>
                </tr>
              )) : (
                <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No inspection records yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
