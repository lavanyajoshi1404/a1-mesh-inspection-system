import React from 'react';
import {
  RefreshCw, CheckCircle, AlertTriangle, XCircle, Activity, Target, Clock, Award, Trash2,
} from 'lucide-react';

export default function QCDashboard({ stats, historyData, fetchStats, resetStats }) {
  const total       = stats.total_inspected || 0;
  const passCount   = stats.pass_count      || 0;
  const reworkCount = stats.rework_count    || 0;
  const rejectCount = stats.reject_count    || 0;
  const passRate    = stats.pass_rate       != null ? stats.pass_rate  : null;
  const avgScore    = stats.avg_quality_score != null ? stats.avg_quality_score : null;
  const avgLatency  = stats.avg_latency_ms  || 0;

  const recent = [...historyData].reverse().slice(-20);

  // Stacked bar percentages
  const barTotal = Math.max(passCount + reworkCount + rejectCount, 1);
  const passW    = (passCount   / barTotal * 100).toFixed(1);
  const reworkW  = (reworkCount / barTotal * 100).toFixed(1);
  const rejectW  = (rejectCount / barTotal * 100).toFixed(1);

  // Trend arrays
  const scoreTrend   = recent.map(r => r.quality_score || 0);
  const latencyTrend = recent.map(r => r.latency_ms    || 0);
  const totalDefects = recent.reduce((s, r) => s + (r.defects_count || 0), 0);

  // Production health composite
  const healthScore = passRate != null && avgScore != null
    ? Math.round(passRate * 0.6 + avgScore * 0.4) : null;
  const healthColor = healthScore == null ? '#94A3B8'
    : healthScore >= 80 ? '#166534' : healthScore >= 60 ? '#9A3412' : '#991B1B';
  const healthBg = healthScore == null ? '#F1F5F9'
    : healthScore >= 80 ? '#DCFCE7' : healthScore >= 60 ? '#FFEDD5' : '#FEE2E2';

  // SVG area chart helper
  const AreaChart = ({ values, stroke, fill, h = 50, viewW = 400 }) => {
    if (!values || values.length < 2) return (
      <svg viewBox={`0 0 ${viewW} ${h}`} style={{ width: '100%', height: h }}>
        <text x={viewW / 2} y={h / 2} textAnchor="middle" fontSize="10" fill="#94A3B8">No data</text>
      </svg>
    );
    const min = Math.min(...values), max = Math.max(...values), range = max - min || 1;
    const pts = values.map((v, i) => {
      const x = (i / (values.length - 1)) * (viewW - 8) + 4;
      const y = (h - 6) - ((v - min) / range) * (h - 12);
      return `${x},${y}`;
    }).join(' ');
    const lastX = viewW - 4;
    const lastY = (h - 6) - ((values[values.length - 1] - min) / range) * (h - 12);
    return (
      <svg viewBox={`0 0 ${viewW} ${h}`} style={{ width: '100%', height: h }} preserveAspectRatio="none">
        <polygon points={`4,${h - 2} ${pts} ${lastX},${h - 2}`} fill={fill} />
        <polyline points={pts} fill="none" stroke={stroke} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={lastX} cy={lastY} r="3.5" fill={stroke} />
      </svg>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Page header */}
      <div className="page-sub-header">
        <div>
          <div className="page-title">Quality Check</div>
          <div className="page-meta">
            A-1 Fence Products Company &nbsp;·&nbsp; Quality Control Overview &nbsp;·&nbsp;
            {total > 0 ? ` ${total} inspections recorded` : ' Awaiting inspections'}
          </div>
        </div>
        <button onClick={fetchStats} className="btn-qc btn-qc-secondary" style={{ padding: '5px 12px', fontSize: 11.5 }}>
          <RefreshCw style={{ width: 13, height: 13 }} /> Refresh
        </button>
      </div>

      {/* ── Row 1: KPI tiles ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 12 }}>
        {[
          { label: 'Total Inspected',      value: total,      unit: '',   sub: 'panels processed',       icon: <Activity style={{ width: 16, height: 16, color: '#0F3D5E' }} />, iconBg: '#EBF1F5', valColor: '#1A2530' },
          { label: 'Pass Rate',            value: passRate != null ? `${passRate}%` : '—', unit: '', sub: `${passCount} passed of ${total}`, icon: <CheckCircle style={{ width: 16, height: 16, color: '#166534' }} />, iconBg: '#DCFCE7', valColor: '#166534', border: '#166534' },
          { label: 'Avg Quality Score',    value: avgScore != null ? `${Number(avgScore).toFixed(1)}%` : '—', unit: '', sub: 'mean across all runs', icon: <Target style={{ width: 16, height: 16, color: '#0284C7' }} />, iconBg: '#E0F2FE', valColor: '#0284C7', border: '#0284C7' },
          { label: 'Rework',              value: reworkCount, unit: '',   sub: `${total > 0 ? ((reworkCount / total) * 100).toFixed(1) : 0}% of total`, icon: <AlertTriangle style={{ width: 16, height: 16, color: '#9A3412' }} />, iconBg: '#FFEDD5', valColor: '#9A3412', border: '#9A3412' },
          { label: 'Rejected',            value: rejectCount, unit: '',   sub: `${total > 0 ? ((rejectCount / total) * 100).toFixed(1) : 0}% of total`, icon: <XCircle style={{ width: 16, height: 16, color: '#991B1B' }} />,       iconBg: '#FEE2E2', valColor: '#991B1B', border: '#991B1B' },
          { label: 'Avg Pipeline Latency', value: avgLatency > 0 ? avgLatency.toFixed(0) : '—', unit: avgLatency > 0 ? 'ms' : '', sub: 'per inspection run', icon: <Clock style={{ width: 16, height: 16, color: '#0F3D5E' }} />, iconBg: '#EBF1F5', valColor: '#1A2530' },
        ].map(({ label, value, unit, sub, icon, iconBg, valColor, border }) => (
          <div key={label} className="qc-card" style={{ padding: '14px 16px', borderLeft: border ? `3px solid ${border}` : undefined }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <div style={{ width: 32, height: 32, borderRadius: 7, background: iconBg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {icon}
              </div>
              <span style={{ fontSize: 10.5, fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
            </div>
            <div style={{ fontSize: 32, fontWeight: 800, color: valColor, fontFamily: "'JetBrains Mono', monospace", lineHeight: 1 }}>
              {value}
              {unit && <span style={{ fontSize: 13, fontWeight: 600, color: '#64748B', marginLeft: 4 }}>{unit}</span>}
            </div>
            <div style={{ fontSize: 11, color: '#64748B', marginTop: 4 }}>{sub}</div>
          </div>
        ))}
      </div>

      {/* ── Row 2: Verdict distribution + Health scorecard ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px', gap: 12 }}>

        {/* Verdict distribution */}
        <div className="qc-card">
          <div className="qc-card-header">
            <span className="qc-card-title">Verdict Distribution</span>
            <span style={{ fontSize: 11, color: '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>{total} total</span>
          </div>
          <div style={{ padding: '12px 16px 16px' }}>
            <div style={{ display: 'flex', height: 22, borderRadius: 6, overflow: 'hidden', marginBottom: 12, background: '#F1F5F9' }}>
              {passCount > 0   && <div style={{ width: `${passW}%`,   background: '#22C55E', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{parseFloat(passW) > 8   && <span style={{ fontSize: 10, fontWeight: 800, color: '#fff' }}>{passW}%</span>}</div>}
              {reworkCount > 0 && <div style={{ width: `${reworkW}%`, background: '#FB923C', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{parseFloat(reworkW) > 8 && <span style={{ fontSize: 10, fontWeight: 800, color: '#fff' }}>{reworkW}%</span>}</div>}
              {rejectCount > 0 && <div style={{ width: `${rejectW}%`, background: '#EF4444', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{parseFloat(rejectW) > 8 && <span style={{ fontSize: 10, fontWeight: 800, color: '#fff' }}>{rejectW}%</span>}</div>}
              {total === 0     && <div style={{ width: '100%', background: '#E2E8F0' }} />}
            </div>
            <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
              {[{ label: 'PASS', count: passCount, color: '#22C55E' }, { label: 'REWORK', count: reworkCount, color: '#FB923C' }, { label: 'REJECT', count: rejectCount, color: '#EF4444' }].map(({ label, count, color }) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: 2, background: color }} />
                  <span style={{ fontSize: 11.5, fontWeight: 700, color: '#475569' }}>{label}</span>
                  <span style={{ fontSize: 13, fontWeight: 800, fontFamily: "'JetBrains Mono', monospace", color }}>{count}</span>
                </div>
              ))}
            </div>
            {scoreTrend.length >= 2 && (
              <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid #F1F5F9' }}>
                <div style={{ fontSize: 10.5, fontWeight: 700, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
                  Quality Score Trend (last {scoreTrend.length} runs)
                </div>
                <AreaChart values={scoreTrend} stroke="#0284C7" fill="rgba(2,132,199,0.10)" h={50} />
              </div>
            )}
          </div>
        </div>

        {/* Production health scorecard */}
        <div className="qc-card">
          <div className="qc-card-header">
            <span className="qc-card-title">Production Health</span>
            <Award style={{ width: 15, height: 15, color: '#0F3D5E' }} />
          </div>
          <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
            <div style={{ width: 100, height: 100, borderRadius: '50%', background: healthBg, border: `4px solid ${healthColor}`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ fontSize: 26, fontWeight: 800, color: healthColor, fontFamily: "'JetBrains Mono', monospace", lineHeight: 1 }}>{healthScore ?? '—'}</div>
              {healthScore != null && <div style={{ fontSize: 10, fontWeight: 700, color: healthColor }}>/ 100</div>}
            </div>
            <div style={{ fontSize: 12, fontWeight: 700, color: healthColor, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              {healthScore == null ? 'No Data' : healthScore >= 80 ? 'Excellent Quality' : healthScore >= 60 ? 'Needs Attention' : 'Critical — Review'}
            </div>
            <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 8 }}>
              {[
                { label: 'Pass Rate',  value: passRate,  unit: '%', color: '#166534' },
                { label: 'Avg Score',  value: avgScore != null ? Number(avgScore).toFixed(1) : null, unit: '%', color: '#0284C7' },
                { label: 'Total Defects (recent)', value: totalDefects, unit: '', color: totalDefects > 0 ? '#9A3412' : '#166534' },
              ].map(({ label, value, unit, color }) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '5px 8px', background: '#F8FAFC', borderRadius: 5 }}>
                  <span style={{ fontSize: 11, color: '#64748B', fontWeight: 600 }}>{label}</span>
                  <span style={{ fontSize: 12, fontWeight: 800, color, fontFamily: "'JetBrains Mono', monospace" }}>{value != null ? `${value}${unit}` : '—'}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Row 3: Defect breakdown + Latency trend ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {/* Defect breakdown */}
        <div className="qc-card">
          <div className="qc-card-header">
            <span className="qc-card-title">Defect Category Breakdown</span>
            <span style={{ fontSize: 11, color: '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>last {recent.length} runs</span>
          </div>
          <div style={{ padding: '12px 16px' }}>
            {recent.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#94A3B8', fontSize: 12, padding: '20px 0' }}>No inspection data yet</div>
            ) : (() => {
              const weldDefects  = recent.reduce((s, r) => s + ((r.weld_missing || 0) + (r.weld_irregular || 0)), 0);
              const wireDefects  = recent.reduce((s, r) => s + ((r.wire_bent    || 0) + (r.wire_broken    || 0)), 0);
              const otherDefects = Math.max(0, totalDefects - weldDefects - wireDefects);
              const cats = [
                { label: 'Weld Defects',      count: weldDefects,  color: '#EF4444' },
                { label: 'Wire Deformations', count: wireDefects,  color: '#FB923C' },
                { label: 'Other / Geometry',  count: otherDefects, color: '#FBBF24' },
              ];
              const maxCount = Math.max(...cats.map(d => d.count), 1);
              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {cats.map(({ label, count, color }) => (
                    <div key={label}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontSize: 11.5, fontWeight: 600, color: '#475569' }}>{label}</span>
                        <span style={{ fontSize: 12, fontWeight: 800, color, fontFamily: "'JetBrains Mono', monospace" }}>{count}</span>
                      </div>
                      <div style={{ height: 10, borderRadius: 5, background: '#F1F5F9', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${(count / maxCount) * 100}%`, background: color, borderRadius: 5, transition: 'width 0.4s ease', minWidth: count > 0 ? 6 : 0 }} />
                      </div>
                    </div>
                  ))}
                  <div style={{ marginTop: 8, padding: '8px 10px', background: '#F8FAFC', borderRadius: 6, border: '1px solid #E2E8F0', display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>Total Defects</span>
                    <span style={{ fontSize: 13, fontWeight: 800, color: totalDefects > 0 ? '#991B1B' : '#166534', fontFamily: "'JetBrains Mono', monospace" }}>{totalDefects}</span>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>

        {/* Latency trend */}
        <div className="qc-card">
          <div className="qc-card-header">
            <span className="qc-card-title">Pipeline Latency Trend</span>
            <span style={{ fontSize: 11, color: '#64748B', fontFamily: "'JetBrains Mono', monospace" }}>{avgLatency > 0 ? `avg ${avgLatency.toFixed(0)} ms` : '—'}</span>
          </div>
          <div style={{ padding: '12px 16px' }}>
            {latencyTrend.length >= 2 ? (
              <>
                <AreaChart values={latencyTrend} stroke="#0F3D5E" fill="rgba(15,61,94,0.08)" h={80} />
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
                  <span style={{ fontSize: 10.5, color: '#94A3B8' }}>Earliest</span>
                  <span style={{ fontSize: 10.5, color: '#94A3B8' }}>Latest</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginTop: 10 }}>
                  {[
                    { label: 'Min', value: Math.min(...latencyTrend).toFixed(0) },
                    { label: 'Max', value: Math.max(...latencyTrend).toFixed(0) },
                    { label: 'Avg', value: (latencyTrend.reduce((a, b) => a + b, 0) / latencyTrend.length).toFixed(0) },
                  ].map(({ label, value }) => (
                    <div key={label} style={{ textAlign: 'center', padding: '6px 4px', background: '#F8FAFC', borderRadius: 5 }}>
                      <div style={{ fontSize: 10, fontWeight: 700, color: '#64748B', textTransform: 'uppercase' }}>{label}</div>
                      <div style={{ fontSize: 14, fontWeight: 800, color: '#1A2530', fontFamily: "'JetBrains Mono', monospace" }}>{value} ms</div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div style={{ textAlign: 'center', color: '#94A3B8', fontSize: 12, padding: '20px 0' }}>No latency data yet</div>
            )}
          </div>
        </div>
      </div>

      {/* ── Row 4: Batch log ── */}
      <div className="qc-card">
        <div className="qc-card-header">
          <span className="qc-card-title">Recent Batch Inspection Log</span>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: '#64748B' }}>{recent.length} records</span>
            <button onClick={resetStats} className="btn-qc btn-qc-secondary" style={{ padding: '3px 8px', fontSize: 11, color: '#991B1B', borderColor: '#FCA5A5' }}>
              <Trash2 style={{ width: 11, height: 11 }} /> Reset
            </button>
          </div>
        </div>
        {recent.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#94A3B8', fontSize: 12, padding: '24px 0' }}>
            No inspections recorded yet. Run an inspection to populate the log.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="qc-table">
              <thead>
                <tr>
                  <th>#</th><th>Inspection ID</th><th>Sample File</th><th>Profile</th>
                  <th>Decision</th><th style={{ textAlign: 'right' }}>Score</th>
                  <th style={{ textAlign: 'right' }}>Defects</th><th style={{ textAlign: 'right' }}>Latency</th>
                </tr>
              </thead>
              <tbody>
                {[...recent].reverse().map((rec, idx) => {
                  const v = rec.verdict || rec.classification || 'PASS';
                  const isP = v === 'PASS', isF = v === 'FAIL' || v === 'REJECT';
                  return (
                    <tr key={rec.inspection_id || idx}>
                      <td style={{ color: '#94A3B8', fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{recent.length - idx}</td>
                      <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11.5, fontWeight: 700, color: '#0F3D5E' }}>{rec.inspection_id || '—'}</td>
                      <td style={{ fontSize: 11.5, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{rec.filename || '—'}</td>
                      <td style={{ fontSize: 11.5 }}>{rec.profile_id || '—'}</td>
                      <td><span className={`badge-qc ${isP ? 'pass' : isF ? 'fail' : 'warning'}`} style={{ fontSize: 10, padding: '2px 7px' }}>{v}</span></td>
                      <td style={{ textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: isP ? '#166534' : isF ? '#991B1B' : '#9A3412' }}>{rec.quality_score ?? '—'}%</td>
                      <td style={{ textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", fontSize: 11.5, color: (rec.defects_count || 0) > 0 ? '#9A3412' : '#166534' }}>{rec.defects_count ?? 0}</td>
                      <td style={{ textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", fontSize: 11.5, color: '#64748B' }}>{rec.latency_ms ? `${Number(rec.latency_ms).toFixed(0)} ms` : '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
