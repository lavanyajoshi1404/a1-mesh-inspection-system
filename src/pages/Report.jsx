import React from 'react';
import { Download } from 'lucide-react';

export default function Report({ inspectionResult, selectedProfile, exportQCReport }) {
  const weldAnalysis = inspectionResult?.weld_analysis || {};
  const wireAnalysis = inspectionResult?.wire_analysis || {};
  const verdict      = inspectionResult?.verdict       || 'PASS';
  const isPass       = verdict === 'PASS';
  const isFail       = verdict === 'FAIL' || verdict === 'REJECT';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="page-sub-header">
        <div>
          <div className="page-title">Compliance Certificate</div>
          <div className="page-meta">Quality Assurance Audit Record</div>
        </div>
        <button onClick={exportQCReport} disabled={!inspectionResult} className="btn-qc btn-qc-primary">
          <Download style={{ width: 13, height: 13 }} /> Download Certificate
        </button>
      </div>

      <div className="qc-card" style={{ maxWidth: 840 }}>
        <div className="qc-card-body" style={{ padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-organic)', paddingBottom: 14, marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 17, fontWeight: 800, color: 'var(--text-primary)' }}>A-1 FENCE PRODUCTS COMPANY</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Automated Vision Inspection Metrology Station</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="font-tabular" style={{ fontSize: 12, color: 'var(--text-muted)' }}>DATE: {new Date().toLocaleDateString()}</div>
              <div className="font-tabular" style={{ fontSize: 12, color: 'var(--text-muted)' }}>ID: {inspectionResult?.inspection_id || 'PENDING'}</div>
            </div>
          </div>

          <table className="qc-table" style={{ marginBottom: 18 }}>
            <tbody>
              <tr><td>Target Profile</td><td style={{ textAlign: 'right', fontWeight: 700, color: 'var(--text-primary)' }}>{selectedProfile.name}</td></tr>
              <tr><td>Applicable Standard</td><td style={{ textAlign: 'right', color: 'var(--text-primary)' }}>{selectedProfile.standards}</td></tr>
              <tr>
                <td>Automatic Inspection Decision</td>
                <td style={{ textAlign: 'right' }}><span className={`badge-qc ${isPass ? 'pass' : isFail ? 'fail' : 'warning'}`}>{verdict}</span></td>
              </tr>
              <tr><td>Quality Score Index</td><td className="font-tabular" style={{ textAlign: 'right', fontWeight: 800, color: 'var(--text-primary)' }}>{inspectionResult?.quality_score ?? '—'}%</td></tr>
              <tr><td>Weld Defects (Missing / Irregular)</td><td className="font-tabular" style={{ textAlign: 'right', color: 'var(--text-primary)' }}>{(weldAnalysis.missing_welds_count || 0) + (weldAnalysis.irregular_welds_count || 0)} defects</td></tr>
              <tr><td>Wire Deformations (Bent / Broken)</td><td className="font-tabular" style={{ textAlign: 'right', color: 'var(--text-primary)' }}>{(wireAnalysis.bent_wires_count || 0) + (wireAnalysis.broken_wires_count || 0)} defects</td></tr>
            </tbody>
          </table>

          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.6, borderTop: '1px solid var(--border-organic)', paddingTop: 14 }}>
            <strong>Inspection Notice:</strong> Automated computer-vision inspection verifies wire grid geometry, weld intersection integrity, and pitch dimensions.
          </div>
        </div>
      </div>
    </div>
  );
}
