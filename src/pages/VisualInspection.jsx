import React from 'react';
import { Camera, Upload, Database, Zap } from 'lucide-react';
import { VISUALIZATION_MODES } from '../constants';

export default function VisualInspection({
  visualMode, setVisualMode,
  activeInputTab, setActiveInputTab,
  datasetFiles, selectedDatasetFile,
  inspecting, inspectionResult, inspectionError,
  currentImage,
  uploadedPreview, uploadedFile,
  fileInputRef, handleFileUpload,
  previewDatasetFile, inspectDatasetFile, runCustomInspection,
  // camera
  cameraActive, autoScan, setAutoScan, cameraError,
  videoRef, canvasRef, toggleCamera, captureCameraFrame,
}) {
  const vm           = inspectionResult?.view_model          || {};
  const weldAnalysis = inspectionResult?.weld_analysis       || {};
  const wireAnalysis = inspectionResult?.wire_analysis       || {};
  const autoDecision = inspectionResult?.automatic_decision  || {};
  const currentEvidence = inspectionResult?.evidence_by_mode?.[visualMode] || { rows: [], notes: [] };
  const verdict = inspectionResult?.verdict || 'PASS';
  const isPass  = verdict === 'PASS';
  const isFail  = verdict === 'FAIL' || verdict === 'REJECT';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Sub Header */}
      <div className="page-sub-header">
        <div>
          <div className="page-title">Visual Inspection &amp; Defect Detector</div>
          <div className="page-meta">
            {inspectionResult?.inspection_id || 'INSP-PENDING'} &nbsp;·&nbsp;
            {vm.classification || 'AWAITING RUN'} &nbsp;·&nbsp; {vm.grid || '—'}
          </div>
        </div>
      </div>

      {/* Mode + Source selector */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div className="radio-mode-group" style={{ margin: 0 }}>
          <span className="radio-mode-label">Visualization Mode</span>
          {VISUALIZATION_MODES.map(mode => (
            <div key={mode} className={`radio-mode-item ${visualMode === mode ? 'active' : ''}`} onClick={() => setVisualMode(mode)}>
              <span className="radio-dot" /><span>{mode}</span>
            </div>
          ))}
        </div>
        <div className="segmented-control">
          <button className={`segmented-item ${activeInputTab === 'dataset' ? 'active' : ''}`} onClick={() => setActiveInputTab('dataset')}><Database style={{ width: 12, height: 12 }} /> Archive</button>
          <button className={`segmented-item ${activeInputTab === 'camera'  ? 'active' : ''}`} onClick={() => setActiveInputTab('camera')} ><Camera   style={{ width: 12, height: 12 }} /> Live Camera</button>
          <button className={`segmented-item ${activeInputTab === 'upload'  ? 'active' : ''}`} onClick={() => setActiveInputTab('upload')} ><Upload   style={{ width: 12, height: 12 }} /> Upload</button>
        </div>
      </div>

      {/* Main grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 320px', gap: 10, alignItems: 'start' }}>
        {/* Left: Viewport */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0, overflow: 'hidden' }}>
          <div className="qc-card">
            <div className="qc-card-header">
              <span className="qc-card-title">{visualMode} View</span>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                {inspecting && <span className="badge-sage font-tabular">Analyzing...</span>}
                {activeInputTab === 'camera' && autoScan && (
                  <span className="badge-sage font-tabular" style={{ color: 'var(--status-pass-text)', background: 'var(--status-pass-bg)' }}>⦿ AUTO SCAN</span>
                )}
                {activeInputTab === 'upload' && uploadedPreview && (
                  <button onClick={() => fileInputRef.current?.click()} className="btn-qc btn-qc-secondary" style={{ padding: '4px 10px', fontSize: 11, fontWeight: 600 }}>
                    <Upload style={{ width: 12, height: 12 }} /> Choose Another
                  </button>
                )}
                {activeInputTab !== 'camera' && (
                  <button
                    onClick={() => activeInputTab === 'dataset' ? inspectDatasetFile(selectedDatasetFile) : runCustomInspection()}
                    disabled={inspecting || (activeInputTab === 'dataset' && !selectedDatasetFile) || (activeInputTab === 'upload' && !uploadedFile)}
                    className="btn-qc btn-qc-primary" style={{ padding: '4px 10px', fontSize: 11, fontWeight: 700 }}
                  >
                    <Zap style={{ width: 12, height: 12 }} /> {inspecting ? 'Analyzing...' : 'Run Inspection'}
                  </button>
                )}
              </div>
            </div>

            <div style={{ position: 'relative', height: 'calc(100vh - 270px)', minHeight: 320, backgroundColor: '#FAFAFA', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', padding: 0 }}>
              {inspecting && <div className="optical-scan-indicator" />}

              {/* Dataset tab */}
              {activeInputTab === 'dataset' && (
                currentImage
                  ? <img src={currentImage} alt={`${visualMode} View`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  : <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No dataset image loaded.</div>
              )}

              {/* Camera tab */}
              {activeInputTab === 'camera' && (
                <div style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 12 }}>
                  <canvas ref={canvasRef} style={{ display: 'none' }} />
                  {cameraError && (
                    <div role="alert" style={{ width: '100%', marginBottom: 8, padding: '6px 10px', borderRadius: 6, background: 'var(--status-warning-bg)', color: 'var(--status-warning-text)', fontSize: 11 }}>
                      {cameraError}
                    </div>
                  )}
                  {!cameraActive ? (
                    <div style={{ textAlign: 'center', padding: 20 }}>
                      <Camera style={{ width: 34, height: 34, color: 'var(--accent-secondary)', margin: '0 auto 8px' }} />
                      <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Optical Sensor Disconnected</div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 14 }}>Connect camera sensor to run real-time mesh inspection.</div>
                      <button onClick={toggleCamera} className="btn-qc btn-qc-primary"><Camera style={{ width: 13, height: 13 }} /> Start Camera</button>
                    </div>
                  ) : (
                    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'center' }}>
                      <div style={{ position: 'relative', width: '100%', height: 'calc(100vh - 350px)', minHeight: 280, maxHeight: 380, display: 'flex', justifyContent: 'center', alignItems: 'center', backgroundColor: '#0F172A', borderRadius: 6, overflow: 'hidden' }}>
                        <video ref={videoRef} autoPlay playsInline muted
                          onLoadedMetadata={() => setTimeout(() => captureCameraFrame(), 400)}
                          style={{ position: 'absolute', width: '100%', height: '100%', objectFit: 'contain', zIndex: 1, opacity: (visualMode !== 'ORIGINAL' && inspectionResult?.images?.[visualMode]) ? 0.001 : 1 }}
                        />
                        {visualMode !== 'ORIGINAL' && inspectionResult?.images?.[visualMode] && (
                          <img src={inspectionResult.images[visualMode]} alt={`Live ${visualMode} Augmented View`} style={{ position: 'relative', zIndex: 2, width: '100%', height: '100%', objectFit: 'contain' }} />
                        )}
                        <div style={{ position: 'absolute', top: 8, left: 8, zIndex: 10, background: 'rgba(15,23,42,0.85)', color: '#fff', fontSize: 10.5, fontWeight: 700, padding: '3px 8px', borderRadius: 4, display: 'flex', alignItems: 'center', gap: 6, backdropFilter: 'blur(4px)' }}>
                          <span style={{ width: 7, height: 7, borderRadius: '50%', backgroundColor: autoScan ? '#4ADE80' : '#FBBF24', animation: autoScan ? 'pulse 1.2s infinite' : 'none' }} />
                          <span>{visualMode === 'ORIGINAL' ? (autoScan ? 'LIVE FEED (AUTO SCAN)' : 'LIVE FEED') : `LIVE ${visualMode}${inspecting ? ' · SCANNING...' : ''}`}</span>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'center', marginTop: 2 }}>
                        <button onClick={() => captureCameraFrame()} disabled={inspecting} className="btn-qc btn-qc-secondary" style={{ padding: '4px 10px', fontSize: 11 }}><Zap style={{ width: 12, height: 12 }} /> {inspecting ? 'Analyzing...' : 'Capture Once'}</button>
                        <button onClick={() => setAutoScan(p => !p)} className={`btn-qc ${autoScan ? 'btn-qc-primary' : 'btn-qc-secondary'}`} style={{ padding: '4px 10px', fontSize: 11 }}>{autoScan ? '⏸ Pause Auto' : '▶ Resume Auto'}</button>
                        <button onClick={toggleCamera} className="btn-qc btn-qc-secondary" style={{ color: 'var(--status-fail-text)', padding: '4px 10px', fontSize: 11 }}>Disconnect</button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Upload tab */}
              {activeInputTab === 'upload' && (
                <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                  <input type="file" ref={fileInputRef} onChange={e => handleFileUpload(e, setActiveInputTab)} accept="image/*" style={{ display: 'none' }} />
                  {uploadedPreview
                    ? <img src={currentImage || uploadedPreview} alt={`${visualMode} View`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    : (
                      <div style={{ padding: 24, textAlign: 'center' }}>
                        <Upload style={{ width: 34, height: 34, color: 'var(--accent-secondary)', margin: '0 auto 10px' }} />
                        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Manual Image Ingestion</div>
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 14 }}>Upload a JPG or PNG frame to inspect mesh defects immediately.</div>
                        <button onClick={() => fileInputRef.current?.click()} className="btn-qc btn-qc-primary"><Upload style={{ width: 13, height: 13 }} /> Browse Local File</button>
                      </div>
                    )
                  }
                </div>
              )}
            </div>

            {/* Thumbnail carousel */}
            {activeInputTab === 'dataset' && datasetFiles.length > 0 && (
              <div style={{ padding: '6px 12px', borderTop: '1px solid var(--border-organic)', backgroundColor: '#FAFAFA' }}>
                <div style={{ fontSize: 9.5, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>
                  Sample Archive ({datasetFiles.length} images) — Click thumbnail to preview
                </div>
                <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 2 }}>
                  {datasetFiles.map(file => (
                    <button key={file} onClick={() => previewDatasetFile(file)} title={`Preview: ${file}`}
                      style={{ flexShrink: 0, width: 40, height: 40, borderRadius: 4, overflow: 'hidden', padding: 0, cursor: 'pointer', background: '#FFFFFF', border: `2px solid ${selectedDatasetFile === file ? 'var(--accent-primary)' : 'transparent'}`, opacity: selectedDatasetFile === file ? 1 : 0.65, transition: 'all 0.15s ease' }}>
                      <img src={`/api/dataset_image/${file}`} alt={file} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Defect cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {/* Automatic decision */}
          <div className="qc-card">
            <div className="qc-card-header">
              <span className="qc-card-title">Automatic Inspection Decision</span>
              <span className={`badge-qc ${isPass ? 'pass' : isFail ? 'fail' : 'warning'}`}>{verdict}</span>
            </div>
            <div className="qc-card-body" style={{ padding: '8px 12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Overall Quality Score</div>
                <div className="font-tabular" style={{ fontSize: 18, fontWeight: 800, color: isPass ? 'var(--status-pass-text)' : isFail ? 'var(--status-fail-text)' : 'var(--status-warning-text)' }}>
                  {inspectionResult?.quality_score ?? 100}%
                </div>
              </div>
              {autoDecision.reasons?.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
                  {autoDecision.reasons.map((r, i) => (
                    <div key={i} style={{ fontSize: 11, color: isFail ? 'var(--status-fail-text)' : 'var(--status-warning-text)', display: 'flex', gap: 5 }}><span>•</span><span>{r}</span></div>
                  ))}
                </div>
              )}
              {autoDecision.passed_checks?.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4, borderTop: '1px solid #F1F5F9', paddingTop: 4 }}>
                  {autoDecision.passed_checks.map((c, i) => (
                    <div key={i} style={{ fontSize: 11, color: 'var(--status-pass-text)', display: 'flex', gap: 5 }}><span>✓</span><span>{c}</span></div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Weld integrity */}
          <div className="qc-card">
            <div className="qc-card-header">
              <span className="qc-card-title">Weld Integrity Detector</span>
              <span className={`badge-qc ${weldAnalysis.status === 'PASS' ? 'pass' : weldAnalysis.status === 'FAIL' ? 'fail' : 'warning'}`}>{weldAnalysis.status || 'NORMAL'}</span>
            </div>
            <table className="evidence-kv-table"><tbody>
              <tr><td className="evidence-kv-key">Missing / Unwelded Junctions</td><td className="evidence-kv-val" style={{ color: weldAnalysis.missing_welds_count > 0 ? 'var(--status-fail-text)' : 'var(--text-primary)' }}>{weldAnalysis.missing_welds_count ?? 0}</td></tr>
              <tr><td className="evidence-kv-key">Weak / Irregular Welds</td><td className="evidence-kv-val" style={{ color: weldAnalysis.irregular_welds_count > 0 ? 'var(--status-warning-text)' : 'var(--text-primary)' }}>{weldAnalysis.irregular_welds_count ?? 0}</td></tr>
              <tr><td className="evidence-kv-key">Normal Welds Detected</td><td className="evidence-kv-val">{weldAnalysis.normal_welds_count ?? 0}</td></tr>
              <tr><td className="evidence-kv-key">Expected Grid Intersections</td><td className="evidence-kv-val">{weldAnalysis.expected_intersections ?? 0}</td></tr>
            </tbody></table>
          </div>

          {/* Wire geometry */}
          <div className="qc-card">
            <div className="qc-card-header">
              <span className="qc-card-title">Wire Geometry &amp; Bending Detector</span>
              <span className={`badge-qc ${wireAnalysis.status === 'PASS' ? 'pass' : wireAnalysis.status === 'FAIL' ? 'fail' : 'warning'}`}>{wireAnalysis.status || 'PARALLEL'}</span>
            </div>
            <table className="evidence-kv-table"><tbody>
              <tr><td className="evidence-kv-key">Bent / Deformed Wires</td><td className="evidence-kv-val" style={{ color: wireAnalysis.bent_wires_count > 0 ? 'var(--status-fail-text)' : 'var(--text-primary)' }}>{wireAnalysis.bent_wires_count ?? 0}</td></tr>
              <tr><td className="evidence-kv-key">Broken / Unconnected Extents</td><td className="evidence-kv-val" style={{ color: wireAnalysis.broken_wires_count > 0 ? 'var(--status-warning-text)' : 'var(--text-primary)' }}>{wireAnalysis.broken_wires_count ?? 0}</td></tr>
              <tr><td className="evidence-kv-key">Grid Parallelism Deviation</td><td className="evidence-kv-val">{wireAnalysis.grid_parallelism_dev_deg != null ? `${wireAnalysis.grid_parallelism_dev_deg.toFixed(2)}°` : '0.00°'}</td></tr>
              <tr><td className="evidence-kv-key">Detected Wire Lines (H × V)</td><td className="evidence-kv-val">{wireAnalysis.num_horizontal ?? 0} H × {wireAnalysis.num_vertical ?? 0} V</td></tr>
            </tbody></table>
          </div>

          {/* Mode evidence */}
          <div className="qc-card">
            <div className="qc-card-header"><span className="qc-card-title">Mode Evidence ({visualMode})</span></div>
            <div className="qc-card-body" style={{ padding: '8px 12px' }}>
              <table className="evidence-kv-table"><tbody>
                {currentEvidence.rows?.length > 0
                  ? currentEvidence.rows.map(([k, v], i) => <tr key={i}><td className="evidence-kv-key">{k}</td><td className="evidence-kv-val">{v}</td></tr>)
                  : <tr><td colSpan={2} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 6 }}>No evidence rows available.</td></tr>
                }
              </tbody></table>
              {currentEvidence.notes?.map((note, i) => <div key={i} className="evidence-note">{note}</div>)}
            </div>
          </div>
        </div>
      </div>

      {/* Status bar */}
      <div className="evidence-status-bar">
        <div>DECISION: <strong>{verdict}</strong></div>
        <div>MISSING/IRREGULAR WELDS: <strong>{(weldAnalysis.missing_welds_count || 0) + (weldAnalysis.irregular_welds_count || 0)}</strong></div>
        <div>BENT/BROKEN WIRES: <strong>{(wireAnalysis.bent_wires_count || 0) + (wireAnalysis.broken_wires_count || 0)}</strong></div>
      </div>
    </div>
  );
}
