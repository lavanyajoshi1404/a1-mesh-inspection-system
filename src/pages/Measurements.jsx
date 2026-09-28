import React from 'react';
import { Download } from 'lucide-react';

export default function Measurements({ inspectionResult, selectedProfile, exportQCReport }) {
  const vm           = inspectionResult?.view_model         || {};
  const weldAnalysis = inspectionResult?.weld_analysis      || {};
  const wireAnalysis = inspectionResult?.wire_analysis      || {};
  const verdict      = inspectionResult?.verdict            || 'PASS';
  const isPass       = verdict === 'PASS';
  const isFail       = verdict === 'FAIL' || verdict === 'REJECT';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="page-sub-header">
        <div>
          <div className="page-title">Measurements &amp; Findings</div>
          <div className="page-meta">{inspectionResult?.inspection_id || 'INSP-PENDING'} &nbsp;·&nbsp; {inspectionResult?.filename || 'sample.jpg'}</div>
        </div>
        <span className={`badge-qc ${isPass ? 'pass' : isFail ? 'fail' : 'warning'}`}>{vm.classification || 'REVIEW'}</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, alignItems: 'start' }}>
        {/* Left */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="qc-card">
            <div className="qc-card-header"><span className="qc-card-title">Image / Processing</span></div>
            <table className="evidence-kv-table"><tbody>
              <tr><td className="evidence-kv-key">Source Dimensions</td><td className="evidence-kv-val">{vm.image || '—'}</td></tr>
              <tr><td className="evidence-kv-key">Processed Dimensions</td><td className="evidence-kv-val">{vm.processing || '—'}</td></tr>
              <tr><td className="evidence-kv-key">Scale</td><td className="evidence-kv-val">{vm.resize_scale != null ? Number(vm.resize_scale).toFixed(3) : '—'}</td></tr>
              <tr><td className="evidence-kv-key">Otsu Threshold</td><td className="evidence-kv-val">{vm.otsu || '—'}</td></tr>
              <tr><td className="evidence-kv-key">Acquisition</td><td className="evidence-kv-val">{vm.source_type || 'UPLOAD'}</td></tr>
            </tbody></table>
          </div>

          <div className="qc-card">
            <div className="qc-card-header">
              <span className="qc-card-title">Grid &amp; Wire Geometry</span>
              <span className={`badge-qc ${wireAnalysis.status === 'PASS' ? 'pass' : wireAnalysis.status === 'FAIL' ? 'fail' : 'warning'}`}>{wireAnalysis.status || 'PARALLEL'}</span>
            </div>
            <table className="evidence-kv-table"><tbody>
              <tr><td className="evidence-kv-key">Horizontal Wires</td><td className="evidence-kv-val">{vm.num_horizontal ?? '—'}</td></tr>
              <tr><td className="evidence-kv-key">Vertical Wires</td><td className="evidence-kv-val">{vm.num_vertical ?? '—'}</td></tr>
              <tr><td className="evidence-kv-key">Bent / Deformed Wires Count</td><td className="evidence-kv-val" style={{ color: wireAnalysis.bent_wires_count > 0 ? 'var(--status-fail-text)' : 'var(--text-primary)' }}>{wireAnalysis.bent_wires_count ?? 0}</td></tr>
              <tr><td className="evidence-kv-key">Angle Deviation H / V</td><td className="evidence-kv-val">{vm.angle_h || '—'} / {vm.angle_v || '—'}</td></tr>
              <tr><td className="evidence-kv-key">Intersection Completeness</td><td className="evidence-kv-val">{vm.intersections ? `${vm.intersections} (${vm.completeness || '100%'})` : '—'}</td></tr>
            </tbody></table>
          </div>

          <div className="qc-card">
            <div className="qc-card-header">
              <span className="qc-card-title">Weld Defects Analysis</span>
              <span className={`badge-qc ${weldAnalysis.status === 'PASS' ? 'pass' : weldAnalysis.status === 'FAIL' ? 'fail' : 'warning'}`}>{weldAnalysis.status || 'NORMAL'}</span>
            </div>
            <table className="evidence-kv-table"><tbody>
              <tr><td className="evidence-kv-key">Missing Welds Count</td><td className="evidence-kv-val" style={{ color: weldAnalysis.missing_welds_count > 0 ? 'var(--status-fail-text)' : 'var(--text-primary)' }}>{weldAnalysis.missing_welds_count ?? 0}</td></tr>
              <tr><td className="evidence-kv-key">Irregular / Weak Welds Count</td><td className="evidence-kv-val" style={{ color: weldAnalysis.irregular_welds_count > 0 ? 'var(--status-warning-text)' : 'var(--text-primary)' }}>{weldAnalysis.irregular_welds_count ?? 0}</td></tr>
              <tr><td className="evidence-kv-key">Normal Welds Count</td><td className="evidence-kv-val">{weldAnalysis.normal_welds_count ?? 0}</td></tr>
              <tr><td className="evidence-kv-key">Insufficient Evidence</td><td className="evidence-kv-val">{vm.insufficient_evidence ?? '0'}</td></tr>
            </tbody></table>
          </div>
        </div>

        {/* Right */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="qc-card">
            <div className="qc-card-header"><span className="qc-card-title">Spacing &amp; Metrology</span></div>
            <table className="evidence-kv-table"><tbody>
              <tr><td className="evidence-kv-key">Vertical Spacing</td><td className="evidence-kv-val">{vm.vertical_spacing_display ? `${vm.vertical_spacing_display} (${vm.vertical_spacing_px || ''})` : '—'}</td></tr>
              <tr><td className="evidence-kv-key">Horizontal Spacing</td><td className="evidence-kv-val">{vm.horizontal_spacing_display ? `${vm.horizontal_spacing_display} (${vm.horizontal_spacing_px || ''})` : '—'}</td></tr>
              <tr><td className="evidence-kv-key">Vertical Calibration</td><td className="evidence-kv-val">{vm.vertical_calibration || 'UNVALIDATED ESTIMATE'}</td></tr>
              <tr><td className="evidence-kv-key">Horizontal Calibration</td><td className="evidence-kv-val">{vm.horizontal_calibration || 'UNCALIBRATED'}</td></tr>
              <tr><td className="evidence-kv-key">Profile</td><td className="evidence-kv-val">{vm.profile || selectedProfile.name}</td></tr>
              <tr><td className="evidence-kv-key">Tolerance</td><td className="evidence-kv-val">{vm.tolerance_display || 'NOT CONFIGURED'}</td></tr>
            </tbody></table>
            {vm.spacing_rows?.length > 0 && (
              <div style={{ padding: '12px 14px', borderTop: '1px solid var(--border-organic)' }}>
                <table className="qc-table">
                  <thead><tr><th>Axis</th><th>Interval</th><th style={{ textAlign: 'right' }}>Pixel Pitch</th><th style={{ textAlign: 'right' }}>Measured Pitch</th><th style={{ textAlign: 'right' }}>Calibration</th></tr></thead>
                  <tbody>
                    {vm.spacing_rows.map((r, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 700 }}>{r.Axis}</td>
                        <td className="font-tabular">{r.Interval}</td>
                        <td className="font-tabular" style={{ textAlign: 'right' }}>{r['Pixel pitch']}</td>
                        <td className="font-tabular" style={{ textAlign: 'right' }}>{r['Measured pitch']}</td>
                        <td style={{ textAlign: 'right', fontSize: 11 }}>{r.Calibration}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="qc-card">
            <div className="qc-card-header">
              <span className="qc-card-title">Defects &amp; Findings Log</span>
              <button onClick={exportQCReport} disabled={!inspectionResult} className="btn-qc btn-qc-secondary" style={{ padding: '4px 8px', fontSize: 11.5 }}>
                <Download style={{ width: 12, height: 12 }} /> Download Certificate
              </button>
            </div>
            <div style={{ padding: '8px 14px 4px' }}>
              <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginBottom: 8 }}>Itemized defect analysis for welds, wire deformation, and geometric alignment.</div>
            </div>
            <div style={{ maxHeight: 260, overflowY: 'auto', padding: '0 14px 14px' }}>
              {inspectionResult?.defects?.length > 0 ? (
                <table className="qc-table">
                  <thead><tr><th>Category</th><th>Severity</th><th>Description</th><th>Location</th></tr></thead>
                  <tbody>
                    {inspectionResult.defects.map((d, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{d.category || d.type}</td>
                        <td><span className={`badge-qc ${d.severity === 'CRITICAL' ? 'fail' : d.severity === 'MAJOR' ? 'warning' : 'pass'}`}>{d.severity}</span></td>
                        <td style={{ fontSize: 11.5 }}>{d.description}</td>
                        <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>{d.location || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div style={{ textAlign: 'center', padding: 20, color: 'var(--text-muted)', fontSize: 13 }}>✓ Zero defects detected in current optical frame.</div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="evidence-status-bar">
        <div>AUTOMATIC DECISION: <strong>{verdict}</strong></div>
        <div>WELD DEFECTS: <strong>{(weldAnalysis.missing_welds_count || 0) + (weldAnalysis.irregular_welds_count || 0)}</strong></div>
        <div>WIRE DEFORMATIONS: <strong>{(wireAnalysis.bent_wires_count || 0) + (wireAnalysis.broken_wires_count || 0)}</strong></div>
      </div>
    </div>
  );
}
