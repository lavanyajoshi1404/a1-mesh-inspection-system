import { useState, useRef } from 'react';
import { PRODUCT_PROFILES } from '../constants';

const INITIAL_STATS = {
  total_inspected: 0,
  pass_rate: null,
  pass_count: 0,
  rework_count: 0,
  reject_count: 0,
  avg_quality_score: null,
  avg_latency_ms: 0.0,
};

export function useInspection() {
  const [datasetFiles, setDatasetFiles]         = useState([]);
  const [selectedDatasetFile, setSelectedDatasetFile] = useState(null);
  const [inspecting, setInspecting]             = useState(false);
  const [inspectionResult, setInspectionResult] = useState(null);
  const [inspectionError, setInspectionError]   = useState('');
  const [uploadedPreview, setUploadedPreview]   = useState(null);
  const [uploadedFile, setUploadedFile]         = useState(null);
  const [selectedProfile, setSelectedProfile]   = useState(PRODUCT_PROFILES[0]);
  const [stats, setStats]                       = useState(INITIAL_STATS);
  const [historyData, setHistoryData]           = useState([]);

  const fileInputRef = useRef(null);

  // ── API: load dataset file list ───────────────────────────────
  const fetchDataset = async () => {
    try {
      const res  = await fetch('/api/dataset');
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || `Dataset request failed (${res.status})`);
      if (data.files?.length > 0) {
        setDatasetFiles(data.files);
        setSelectedDatasetFile(data.files[0]);
      } else {
        setDatasetFiles([]);
        setSelectedDatasetFile(null);
      }
    } catch (e) {
      console.error('Dataset fetch error:', e);
      setInspectionError(e.message || 'Could not load sample dataset.');
    }
  };

  // ── API: load aggregated stats + history ──────────────────────
  const fetchStats = async () => {
    try {
      const [sRes, hRes] = await Promise.all([
        fetch('/api/stats'),
        fetch('/api/history?n=20'),
      ]);
      const [sData, hData] = await Promise.all([sRes.json(), hRes.json()]);
      if (!sRes.ok || !hRes.ok) throw new Error('Could not refresh inspection analytics.');
      setStats(sData);
      setHistoryData(Array.isArray(hData.history) ? hData.history : []);
    } catch (e) {
      console.error('Stats fetch error:', e);
    }
  };

  // ── API: reset all stats ──────────────────────────────────────
  const resetStats = async () => {
    try {
      const res = await fetch('/api/reset_stats', { method: 'POST' });
      if (res.ok) { setHistoryData([]); fetchStats(); }
    } catch (e) {
      console.error('Reset stats error:', e);
    }
  };

  // ── Preview a dataset file without running the CV pipeline ────
  const previewDatasetFile = (filename) => {
    setSelectedDatasetFile(filename);
    setInspectionResult(null);
    setInspectionError('');
  };

  // ── Run CV pipeline on a dataset file ────────────────────────
  const inspectDatasetFile = async (filename) => {
    const target = filename || selectedDatasetFile;
    if (!target) return;
    setSelectedDatasetFile(target);
    setInspecting(true);
    setInspectionError('');
    try {
      const res = await fetch('/api/inspect_dataset_item', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: target, profile_id: selectedProfile.id }),
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Inspection failed');
      setInspectionResult(data);
      fetchStats();
    } catch (e) {
      console.error('Inspection error:', e);
      setInspectionError(e.message || 'Sample image analysis failed.');
    } finally {
      setInspecting(false);
    }
  };

  // ── Handle file-picker change, auto-run inspection ────────────
  const handleFileUpload = (e, setActiveInputTab) => {
    const file = e.target.files[0];
    if (!file) return;
    setActiveInputTab('upload');
    setInspectionError('');
    const reader = new FileReader();
    reader.onload = (ev) => {
      setUploadedPreview(ev.target.result);
      setUploadedFile(file);
      runCustomInspection(file);
    };
    reader.onerror = () => setInspectionError('The selected photo could not be read.');
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  // ── Run CV pipeline on an uploaded file ──────────────────────
  const runCustomInspection = async (file) => {
    const target = file || uploadedFile;
    if (!target) { setInspectionError('Please choose an image first.'); return; }
    if (!target.type.startsWith('image/')) {
      setInspectionError('Please choose a valid JPG or PNG image file.');
      return;
    }
    setInspecting(true);
    setInspectionError('');
    const formData = new FormData();
    formData.append('file', target);
    formData.append('profile_id', selectedProfile.id);
    try {
      const res  = await fetch('/api/inspect', { method: 'POST', body: formData });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Upload inspection failed');
      setInspectionResult(data);
      fetchStats();
    } catch (e) {
      console.error('Custom file inspection error:', e);
      setInspectionError(e.message || 'The selected photo could not be analyzed.');
    } finally {
      setInspecting(false);
    }
  };

  // ── Generate and print a full-page PDF certificate ───────────
  const exportQCReport = () => {
    if (!inspectionResult) return;
    const r   = inspectionResult;
    const wa  = r.weld_analysis        || {};
    const wra = r.wire_analysis        || {};
    const ad  = r.automatic_decision   || {};
    const vm2 = r.view_model           || {};
    const sp  = selectedProfile;
    const verdict2    = r.verdict || 'PASS';
    const isPass2     = verdict2 === 'PASS';
    const isFail2     = verdict2 === 'FAIL' || verdict2 === 'REJECT';
    const verdictColor = isPass2 ? '#166534' : isFail2 ? '#991B1B' : '#9A3412';
    const verdictBg    = isPass2 ? '#DCFCE7' : isFail2 ? '#FEE2E2' : '#FFEDD5';
    const score  = r.quality_score ?? 100;
    const now    = new Date();
    const dateStr = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'long', year: 'numeric' });
    const timeStr = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

    const passedRows = (ad.passed_checks || []).map(c =>
      `<tr><td style="padding:4px 8px;color:#166534;">✓</td><td style="padding:4px 8px;color:#166534;">${c}</td></tr>`
    ).join('');
    const failRows = (ad.reasons || []).map(r2 =>
      `<tr><td style="padding:4px 8px;color:#991B1B;">✗</td><td style="padding:4px 8px;color:#991B1B;">${r2}</td></tr>`
    ).join('');

    const html = `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<title>QC Certificate — ${r.inspection_id || 'INSP'}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Plus Jakarta Sans',Arial,sans-serif;font-size:12px;color:#1A2530;background:#fff;padding:40px 48px}
.cert-header{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:3px solid #0F3D5E;padding-bottom:16px;margin-bottom:20px}
.cert-logo-box{display:flex;align-items:center;gap:12px}
.cert-logo-icon{width:44px;height:44px;background:#0F3D5E;color:#fff;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:800}
.cert-company{font-size:17px;font-weight:800;color:#0F3D5E}.cert-sub{font-size:11px;color:#64748B;margin-top:2px}
.cert-meta{text-align:right;font-size:11px;color:#64748B;line-height:1.7}.cert-meta strong{color:#1A2530;font-weight:700}
.cert-title-band{background:#0F3D5E;color:#fff;padding:10px 16px;border-radius:6px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center}
.cert-title-band h1{font-size:14px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase}
.verdict-badge{display:inline-block;padding:6px 18px;border-radius:6px;font-size:15px;font-weight:800;background:${verdictBg};color:${verdictColor};border:2px solid ${verdictColor}}
.section-title{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;color:#64748B;margin:18px 0 6px;border-bottom:1px solid #E2E8F0;padding-bottom:4px}
.kv-table{width:100%;border-collapse:collapse}.kv-table td{padding:5px 8px;font-size:12px;border-bottom:1px solid #F1F5F9}
.kv-table td:first-child{color:#64748B;font-weight:600;width:50%;text-transform:uppercase;font-size:10.5px}
.kv-table td:last-child{font-weight:700;color:#1A2530;text-align:right;font-family:'Courier New',monospace}
.score-row{display:flex;align-items:center;justify-content:space-between;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:10px 16px;margin-bottom:12px}
.score-label{font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:0.06em}
.score-value{font-size:28px;font-weight:800;font-family:'Courier New',monospace;color:${verdictColor}}
.data-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.checks-table{width:100%;border-collapse:collapse;font-size:11.5px}.checks-table td{padding:4px 8px;border-bottom:1px solid #F8FAFC}
.cert-footer{margin-top:28px;padding-top:14px;border-top:2px solid #E2E8F0;display:flex;justify-content:space-between;align-items:flex-end}
.cert-footer p{font-size:10px;color:#94A3B8;line-height:1.6;max-width:60%}
.sig-block{text-align:right}.sig-line{border-bottom:1px solid #1A2530;width:160px;margin-bottom:4px;height:28px}.sig-label{font-size:10px;color:#64748B}
@media print{body{padding:20px 28px}@page{margin:0;size:A4}}
</style></head><body>
<div class="cert-header">
  <div class="cert-logo-box"><div class="cert-logo-icon">A1</div><div><div class="cert-company">A-1 FENCE PRODUCTS COMPANY</div><div class="cert-sub">Automated Vision Inspection Metrology Station</div></div></div>
  <div class="cert-meta"><div>Date: <strong>${dateStr}</strong></div><div>Time: <strong>${timeStr}</strong></div><div>ID: <strong>${r.inspection_id || 'PENDING'}</strong></div></div>
</div>
<div class="cert-title-band"><h1>Quality Compliance Certificate</h1><span>Automated Computer-Vision Inspection Report</span></div>
<div class="score-row">
  <div><div class="score-label">Overall Quality Score</div><div class="score-value">${score}%</div></div>
  <div style="text-align:right"><div class="score-label" style="margin-bottom:6px">Inspection Decision</div><div class="verdict-badge">${verdict2}</div></div>
</div>
<div class="data-grid">
  <div><div class="section-title">Product Profile</div>
  <table class="kv-table"><tr><td>Profile</td><td>${sp.name} (${sp.id})</td></tr><tr><td>Standard</td><td>${sp.standards}</td></tr><tr><td>Coating</td><td>${sp.coating}</td></tr><tr><td>Wire Diameter</td><td>${sp.wire_diameter_mm} mm</td></tr><tr><td>Aperture H</td><td>${sp.aperture_h_mm} mm</td></tr><tr><td>Aperture V</td><td>${sp.aperture_v_mm} mm</td></tr></table></div>
  <div><div class="section-title">Measurement Summary</div>
  <table class="kv-table"><tr><td>Grid Classification</td><td>${vm2.grid || '—'}</td></tr><tr><td>Classification</td><td>${vm2.classification || '—'}</td></tr><tr><td>Horizontal Wires</td><td>${vm2.h_wires ?? '—'}</td></tr><tr><td>Vertical Wires</td><td>${vm2.v_wires ?? '—'}</td></tr><tr><td>Total Junctions</td><td>${vm2.intersections ?? '—'}</td></tr><tr><td>Processing Time</td><td>${r.elapsed_ms ? r.elapsed_ms.toFixed(0) + ' ms' : '—'}</td></tr></table></div>
</div>
<div class="section-title">Weld Integrity Analysis</div>
<table class="kv-table">
  <tr><td>Missing / Unwelded Junctions</td><td style="color:${(wa.missing_welds_count||0)>0?'#991B1B':'#166534'}">${wa.missing_welds_count??0}</td></tr>
  <tr><td>Weak / Irregular Welds</td><td style="color:${(wa.irregular_welds_count||0)>0?'#9A3412':'#166534'}">${wa.irregular_welds_count??0}</td></tr>
  <tr><td>Total Weld Junctions Detected</td><td>${wa.total_junctions??'—'}</td></tr>
  <tr><td>Weld Status</td><td style="color:${wa.status==='PASS'?'#166534':'#991B1B'};font-weight:800">${wa.status||'—'}</td></tr>
</table>
<div class="section-title">Wire Deformation Analysis</div>
<table class="kv-table">
  <tr><td>Bent Wires</td><td style="color:${(wra.bent_wires_count||0)>0?'#9A3412':'#166534'}">${wra.bent_wires_count??0}</td></tr>
  <tr><td>Broken / Missing Wires</td><td style="color:${(wra.broken_wires_count||0)>0?'#991B1B':'#166534'}">${wra.broken_wires_count??0}</td></tr>
  <tr><td>Wire Deformation Status</td><td style="color:${wra.status==='PASS'?'#166534':'#991B1B'};font-weight:800">${wra.status||'—'}</td></tr>
</table>
<div class="section-title">Inspection Checks</div>
<table class="checks-table">${failRows}${passedRows}</table>
<div class="section-title">Inspection Notice</div>
<p style="font-size:11px;color:#475569;line-height:1.7;padding:8px 0">Automated computer-vision inspection verifies wire grid geometry, weld intersection integrity, and pitch dimensions against the declared product profile tolerances.</p>
<div class="cert-footer">
  <p>A-1 Fence Products Company · Automated Vision Inspection System<br/>Certificate generated: ${dateStr} at ${timeStr}<br/>Inspection Reference: ${r.inspection_id||'PENDING'}</p>
  <div class="sig-block"><div class="sig-line"></div><div class="sig-label">Authorised QC Officer</div></div>
</div>
</body></html>`;

    const win = window.open('', '_blank');
    if (!win) { alert('Please allow pop-ups to download the certificate.'); return; }
    win.document.write(html);
    win.document.close();
    win.focus();
    setTimeout(() => win.print(), 600);
  };

  return {
    // state
    datasetFiles, selectedDatasetFile, inspecting,
    inspectionResult, inspectionError,
    uploadedPreview, uploadedFile, fileInputRef,
    selectedProfile, setSelectedProfile,
    stats, historyData,
    // actions
    fetchDataset, fetchStats, resetStats,
    previewDatasetFile, inspectDatasetFile,
    handleFileUpload, runCustomInspection,
    exportQCReport,
    // private setters exposed for useCamera wiring
    _setInspectionResult: setInspectionResult,
    _setInspectionError:  setInspectionError,
  };
}
