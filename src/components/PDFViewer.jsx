/*
 * File: PDFViewer.jsx
 * Owner: KARDAM
 * Purpose: Render PDF course documents with PDF.js inside the learner player.
 * What it is: An in-app PDF viewer with loading state, paging, zoom, and download support.
 */
import { useEffect, useRef, useState } from "react";
import { GlobalWorkerOptions, getDocument } from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";

GlobalWorkerOptions.workerSrc = pdfWorker;

function ZoomInIcon() {
  return (
    <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
      <path d="M12 7v10M7 12h10" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

function ZoomOutIcon() {
  return (
    <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
      <path d="M7 12h10" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

function ChevronLeftIcon() {
  return (
    <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
      <path d="M14.5 5 7.5 12l7 7" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
      <path d="M9.5 5 16.5 12l-7 7" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
      <path d="M12 4v10M8 10l4 4 4-4M5 19h14" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function FullscreenEnterIcon() {
  return (
    <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
      <path d="M8 4H4v4M16 4h4v4M20 16v4h-4M8 20H4v-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function FullscreenExitIcon() {
  return (
    <svg viewBox="0 0 24 24" className="inline-icon" aria-hidden="true">
      <path d="M9 4H4v5M15 4h5v5M20 15v5h-5M4 15v5h5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function PDFViewer({ fileUrl, title }) {
  const viewerRef = useRef(null);
  const canvasRef = useRef(null);
  const renderTaskRef = useRef(null);
  const [pdfDocument, setPdfDocument] = useState(null);
  const [pageCount, setPageCount] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [zoom, setZoom] = useState(1.1);
  const [status, setStatus] = useState("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [isFullscreen, setIsFullscreen] = useState(false);

  const goToPreviousPage = () => {
    setPageNumber((current) => Math.max(current - 1, 1));
  };

  const goToNextPage = () => {
    setPageNumber((current) => Math.min(current + 1, pageCount || 1));
  };

  const zoomOut = () => {
    setZoom((current) => Math.max(current - 0.15, 0.7));
  };

  const zoomIn = () => {
    setZoom((current) => Math.min(current + 0.15, 2.4));
  };

  const resetZoom = () => {
    setZoom(1.1);
  };

  const toggleFullscreen = async () => {
    if (!viewerRef.current) {
      return;
    }

    if (document.fullscreenElement === viewerRef.current) {
      await document.exitFullscreen();
      return;
    }

    await viewerRef.current.requestFullscreen();
  };

  useEffect(() => {
    let isMounted = true;
    setStatus("loading");
    setErrorMessage("");
    setPageNumber(1);

    const loadingTask = getDocument(fileUrl);
    loadingTask.promise
      .then((document) => {
        if (!isMounted) {
          void document.destroy();
          return;
        }

        setPdfDocument(document);
        setPageCount(document.numPages);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }

        setPdfDocument(null);
        setPageCount(0);
        setStatus("error");
        setErrorMessage("This PDF could not be loaded.");
      });

    return () => {
      isMounted = false;
      void loadingTask.destroy();
    };
  }, [fileUrl]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement === viewerRef.current);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  useEffect(() => {
    if (!pdfDocument || !canvasRef.current) {
      return undefined;
    }

    let isCancelled = false;
    setStatus("rendering");

    pdfDocument.getPage(pageNumber).then((page) => {
      if (isCancelled || !canvasRef.current) {
        return;
      }

      const viewport = page.getViewport({ scale: zoom });
      const canvas = canvasRef.current;
      const context = canvas.getContext("2d");

      canvas.width = viewport.width;
      canvas.height = viewport.height;

      renderTaskRef.current?.cancel();
      const renderTask = page.render({ canvasContext: context, viewport });
      renderTaskRef.current = renderTask;

      renderTask.promise
        .then(() => {
          if (!isCancelled) {
            setStatus("ready");
          }
        })
        .catch((error) => {
          if (!isCancelled && error?.name !== "RenderingCancelledException") {
            setStatus("error");
            setErrorMessage("This PDF page could not be rendered.");
          }
        });
    });

    return () => {
      isCancelled = true;
      renderTaskRef.current?.cancel();
    };
  }, [pageNumber, pdfDocument, zoom]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      const activeTag = document.activeElement?.tagName;
      if (activeTag === "INPUT" || activeTag === "TEXTAREA" || event.metaKey || event.ctrlKey || event.altKey) {
        return;
      }

      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goToPreviousPage();
        return;
      }

      if (event.key === "ArrowRight") {
        event.preventDefault();
        goToNextPage();
        return;
      }

      if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        zoomIn();
        return;
      }

      if (event.key === "-" || event.key === "_") {
        event.preventDefault();
        zoomOut();
        return;
      }

      if (event.key === "0") {
        event.preventDefault();
        resetZoom();
        return;
      }

      if (event.key.toLowerCase() === "f") {
        event.preventDefault();
        void toggleFullscreen();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [pageCount]);

  return (
    <div
      ref={viewerRef}
      className={`pdf-viewer-shell ${isFullscreen ? "is-fullscreen" : ""}`}
      tabIndex={0}
    >
      <div className="pdf-toolbar">
        <div className="pdf-toolbar-group">
          <button
            type="button"
            className="pdf-toolbar-button"
            onClick={goToPreviousPage}
            disabled={pageNumber <= 1 || !pdfDocument}
            aria-label="Previous PDF page"
            title="Previous page (Left Arrow)"
          >
            <ChevronLeftIcon />
          </button>
          <span className="pdf-toolbar-label">
            Page {pageNumber} / {pageCount || 1}
          </span>
          <button
            type="button"
            className="pdf-toolbar-button"
            onClick={goToNextPage}
            disabled={!pdfDocument || pageNumber >= pageCount}
            aria-label="Next PDF page"
            title="Next page (Right Arrow)"
          >
            <ChevronRightIcon />
          </button>
        </div>

        <div className="pdf-toolbar-group">
          <button
            type="button"
            className="pdf-toolbar-button"
            onClick={zoomOut}
            disabled={!pdfDocument}
            aria-label="Zoom out PDF"
            title="Zoom out (-)"
          >
            <ZoomOutIcon />
          </button>
          <span className="pdf-toolbar-label">{Math.round(zoom * 100)}%</span>
          <button
            type="button"
            className="pdf-toolbar-button"
            onClick={zoomIn}
            disabled={!pdfDocument}
            aria-label="Zoom in PDF"
            title="Zoom in (+)"
          >
            <ZoomInIcon />
          </button>
          <button
            type="button"
            className="pdf-toolbar-button"
            onClick={resetZoom}
            disabled={!pdfDocument}
            aria-label="Reset PDF zoom"
            title="Reset zoom (0)"
          >
            <span className="pdf-toolbar-reset">1:1</span>
          </button>
          <button
            type="button"
            className="pdf-toolbar-button"
            onClick={() => void toggleFullscreen()}
            disabled={!pdfDocument}
            aria-label={isFullscreen ? "Exit full screen PDF view" : "Enter full screen PDF view"}
            title={isFullscreen ? "Exit full screen (F)" : "Full screen (F)"}
          >
            {isFullscreen ? <FullscreenExitIcon /> : <FullscreenEnterIcon />}
          </button>
          <a
            className="pdf-toolbar-button is-link"
            href={fileUrl}
            target="_blank"
            rel="noreferrer"
            aria-label={`Open ${title} in a new tab`}
            title="Open PDF in a new tab"
          >
            <DownloadIcon />
          </a>
        </div>
      </div>

      <div className="pdf-canvas-shell">
        {status === "loading" || status === "rendering" ? (
          <div className="pdf-viewer-state">Loading PDF...</div>
        ) : null}

        {status === "error" ? <div className="pdf-viewer-state is-error">{errorMessage}</div> : null}

        <canvas
          ref={canvasRef}
          className={`pdf-canvas ${status === "ready" ? "is-visible" : ""}`}
          aria-label={title}
        />
      </div>
    </div>
  );
}
