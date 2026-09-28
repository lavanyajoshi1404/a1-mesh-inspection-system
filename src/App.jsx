import React, { useState, useEffect, useRef } from 'react';

// ── Hooks ──────────────────────────────────────────────────────
import { useInspection } from './hooks/useInspection';
import { useCamera     } from './hooks/useCamera';

// ── Layout ────────────────────────────────────────────────────
import AppHeader from './components/layout/AppHeader';
import NavRail   from './components/layout/NavRail';

// ── Pages ──────────────────────────────────────────────────────
import QCDashboard      from './pages/QCDashboard';
import VisualInspection from './pages/VisualInspection';
import Measurements     from './pages/Measurements';
import Analytics        from './pages/Analytics';
import Products         from './pages/Products';
import Report           from './pages/Report';

export default function App({ user, onSignOut }) {
  const [activePage,     setActivePage]     = useState('qcdashboard');
  const [visualMode,     setVisualMode]     = useState('GRID');
  const [activeInputTab, setActiveInputTab] = useState('dataset');

  const initialLoadRef = useRef(false);

  // ── Inspection state + API ─────────────────────────────────
  const inspection = useInspection();

  // ── Camera — wired to inspection's state setters ──────────
  const camera = useCamera({
    selectedProfile:     inspection.selectedProfile,
    setInspectionResult: inspection._setInspectionResult,
    setInspectionError:  inspection._setInspectionError,
    fetchStats:          inspection.fetchStats,
  });

  // ── Initial data load (strict-mode safe) ───────────────────
  useEffect(() => {
    if (initialLoadRef.current) return;
    initialLoadRef.current = true;
    inspection.fetchDataset();
    inspection.fetchStats();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Resolved display image ─────────────────────────────────
  const currentImage =
    inspection.inspectionResult?.images?.[visualMode] ||
    inspection.inspectionResult?.images?.ORIGINAL ||
    (activeInputTab === 'dataset' && inspection.selectedDatasetFile
      ? `/api/dataset_image/${inspection.selectedDatasetFile}`
      : null) ||
    inspection.uploadedPreview;

  // ── Page router ────────────────────────────────────────────
  const renderPage = () => {
    switch (activePage) {

      case 'qcdashboard':
        return (
          <QCDashboard
            stats={inspection.stats}
            historyData={inspection.historyData}
            fetchStats={inspection.fetchStats}
            resetStats={inspection.resetStats}
          />
        );

      case 'visual':
        return (
          <VisualInspection
            // UI state
            visualMode={visualMode}         setVisualMode={setVisualMode}
            activeInputTab={activeInputTab}  setActiveInputTab={setActiveInputTab}
            // Inspection
            datasetFiles={inspection.datasetFiles}
            selectedDatasetFile={inspection.selectedDatasetFile}
            inspecting={inspection.inspecting}
            inspectionResult={inspection.inspectionResult}
            inspectionError={inspection.inspectionError}
            currentImage={currentImage}
            uploadedPreview={inspection.uploadedPreview}
            uploadedFile={inspection.uploadedFile}
            fileInputRef={inspection.fileInputRef}
            handleFileUpload={inspection.handleFileUpload}
            previewDatasetFile={inspection.previewDatasetFile}
            inspectDatasetFile={inspection.inspectDatasetFile}
            runCustomInspection={inspection.runCustomInspection}
            // Camera
            cameraActive={camera.cameraActive}
            autoScan={camera.autoScan}       setAutoScan={camera.setAutoScan}
            cameraError={camera.cameraError}
            videoRef={camera.videoRef}       canvasRef={camera.canvasRef}
            toggleCamera={camera.toggleCamera}
            captureCameraFrame={camera.captureCameraFrame}
          />
        );

      case 'measurements':
        return (
          <Measurements
            inspectionResult={inspection.inspectionResult}
            selectedProfile={inspection.selectedProfile}
            exportQCReport={inspection.exportQCReport}
          />
        );

      case 'analytics':
        return (
          <Analytics
            stats={inspection.stats}
            historyData={inspection.historyData}
            resetStats={inspection.resetStats}
          />
        );

      case 'products':
        return (
          <Products
            selectedProfile={inspection.selectedProfile}
            setSelectedProfile={inspection.setSelectedProfile}
            onNavigate={setActivePage}
          />
        );

      case 'report':
        return (
          <Report
            inspectionResult={inspection.inspectionResult}
            selectedProfile={inspection.selectedProfile}
            exportQCReport={inspection.exportQCReport}
          />
        );

      default:
        return (
          <QCDashboard
            stats={inspection.stats}
            historyData={inspection.historyData}
            fetchStats={inspection.fetchStats}
            resetStats={inspection.resetStats}
          />
        );
    }
  };

  return (
    <div className="app-container">
      <AppHeader
        user={user}
        onSignOut={onSignOut}
        selectedProfile={inspection.selectedProfile}
        stats={inspection.stats}
        onRefresh={inspection.fetchStats}
      />

      <div className="workspace-container">
        <NavRail activePage={activePage} onNavigate={setActivePage} />
        <main className="inspection-workspace">
          {renderPage()}
        </main>
      </div>
    </div>
  );
}
