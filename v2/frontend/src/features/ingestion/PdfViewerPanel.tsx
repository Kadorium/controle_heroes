import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "../../ui";
import { occurrenceContentUrl, parseLocator, type Locator } from "./ingestionApi";

/** Legacy build: polyfills Map.getOrInsertComputed (Chrome <145 / Cursor Chromium). */
import * as pdfjs from "pdfjs-dist/legacy/build/pdf.mjs";
import pdfWorkerSrc from "pdfjs-dist/legacy/build/pdf.worker.min.mjs?url";

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerSrc;

type PdfDoc = {
  numPages: number;
  getPage: (n: number) => Promise<{
    getViewport: (opts: { scale: number }) => { width: number; height: number };
    render: (params: Record<string, unknown>) => { promise: Promise<void>; cancel: () => void };
  }>;
  destroy?: () => Promise<void>;
};

type Props = {
  occurrenceId: number;
  activeLocator: Locator | null;
  onPageChange?: (page: number) => void;
  /** Ordine: esconde ruído "Sem locator ativo" / coords técnicas. */
  compactChrome?: boolean;
};

export function PdfViewerPanel({ occurrenceId, activeLocator, onPageChange, compactChrome = false }: Props) {
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [numPages, setNumPages] = useState(1);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [useIframeFallback, setUseIframeFallback] = useState(false);
  const [retryToken, setRetryToken] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const pdfRef = useRef<PdfDoc | null>(null);
  const renderTaskRef = useRef<{ cancel: () => void } | null>(null);

  const iframeSrc = useMemo(() => {
    const base = occurrenceContentUrl(occurrenceId);
    return `${base}#page=${page}`;
  }, [occurrenceId, page]);

  function setPageSafe(n: number) {
    const next = Math.max(1, Math.min(numPages, n));
    setPage(next);
    onPageChange?.(next);
  }

  function bumpZoom(delta: number) {
    setZoom((z) => {
      const next = Math.round((z + delta) * 10) / 10;
      return Math.min(2.5, Math.max(0.5, next));
    });
  }

  function retryCanvas() {
    pdfRef.current = null;
    setUseIframeFallback(false);
    setPdfError(null);
    setRetryToken((t) => t + 1);
  }

  // Load PDF document once per occurrence (not on every zoom).
  useEffect(() => {
    if (useIframeFallback) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let loadingTask: any = null;

    void (async () => {
      setLoading(true);
      setPdfError(null);
      pdfRef.current = null;
      try {
        const res = await fetch(occurrenceContentUrl(occurrenceId), { credentials: "include" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.arrayBuffer();
        loadingTask = pdfjs.getDocument({ data });
        const pdf = await loadingTask.promise;
        if (cancelled) {
          void pdf.destroy();
          return;
        }
        pdfRef.current = pdf as unknown as PdfDoc;
        setNumPages(pdf.numPages);
        setLoading(false);
      } catch (e) {
        if (!cancelled) {
          setPdfError(e instanceof Error ? e.message : "Falha PDF.js");
          setUseIframeFallback(true);
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
      void loadingTask?.destroy();
      const cur = pdfRef.current;
      pdfRef.current = null;
      void cur?.destroy?.();
    };
  }, [occurrenceId, useIframeFallback, retryToken]);

  // Re-render page when page/zoom change (uses cached pdf).
  useEffect(() => {
    if (useIframeFallback || loading) return;
    const pdf = pdfRef.current;
    if (!pdf) return;
    let cancelled = false;

    void (async () => {
      try {
        const pageIndex = Math.min(page, pdf.numPages);
        const pdfPage = await pdf.getPage(pageIndex);
        if (cancelled) return;
        const canvas = canvasRef.current;
        if (!canvas) throw new Error("Canvas PDF indisponível");
        const viewport = pdfPage.getViewport({ scale: zoom * 1.25 });
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const ctx = canvas.getContext("2d");
        if (!ctx) throw new Error("Contexto 2D indisponível");
        if (renderTaskRef.current) {
          try {
            renderTaskRef.current.cancel();
          } catch {
            /* ignore */
          }
        }
        const task = pdfPage.render({
          canvasContext: ctx,
          viewport,
          canvas,
        });
        renderTaskRef.current = task;
        await task.promise;
      } catch (e) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : String(e);
          if (/cancel/i.test(msg)) return;
          setPdfError(msg);
          setUseIframeFallback(true);
        }
      }
    })();

    return () => {
      cancelled = true;
      try {
        renderTaskRef.current?.cancel();
      } catch {
        /* ignore */
      }
    };
  }, [page, zoom, loading, useIframeFallback, retryToken, occurrenceId]);

  const highlight =
    activeLocator &&
    (activeLocator.page == null || activeLocator.page === page) &&
    activeLocator.x != null &&
    activeLocator.y != null;

  return (
    <div className="ingestion-pdf-viewer" data-testid="ingestion-pdf-viewer">
      <div className="ingestion-pdf-toolbar" role="toolbar" aria-label="Controles do PDF">
        <Button
          type="button"
          variant="ghost"
          onClick={() => setPageSafe(page - 1)}
          disabled={page <= 1}
          data-testid="pdf-prev-page"
        >
          Página ant.
        </Button>
        <span data-testid="pdf-page-label">
          Pág. {page}
          {numPages > 1 ? ` / ${numPages}` : ""}
        </span>
        <Button
          type="button"
          variant="ghost"
          onClick={() => setPageSafe(page + 1)}
          disabled={page >= numPages}
          data-testid="pdf-next-page"
        >
          Página próx.
        </Button>
        <Button type="button" variant="ghost" onClick={() => bumpZoom(-0.1)} data-testid="pdf-zoom-out">
          −
        </Button>
        <button
          type="button"
          className="ui-button ui-button--ghost"
          onClick={() => setZoom(1)}
          data-testid="pdf-zoom-reset"
          title="Voltar a 100%"
        >
          <span data-testid="pdf-zoom-label">{Math.round(zoom * 100)}%</span>
        </button>
        <Button type="button" variant="ghost" onClick={() => bumpZoom(0.1)} data-testid="pdf-zoom-in">
          +
        </Button>
        {useIframeFallback ? (
          <>
            <span className="notice notice--warning ingestion-pdf-fallback-warn" data-testid="pdf-fallback-warning">
              Visualização aproximada (iframe) — highlight de locator pode divergir.
            </span>
            <Button type="button" variant="ghost" onClick={retryCanvas} data-testid="pdf-retry-canvas">
              Tentar PDF.js
            </Button>
          </>
        ) : (
          <span className="muted" data-testid="pdf-engine-label">
            PDF.js (legacy)
          </span>
        )}
        {activeLocator ? (
          <span className="muted" data-testid="pdf-locator-hint">
            {compactChrome
              ? `Página ${activeLocator.page ?? page}`
              : `Locator: p${activeLocator.page ?? page} ${
                  activeLocator.x != null
                    ? `(${activeLocator.x},${activeLocator.y},${activeLocator.w ?? "?"},${activeLocator.h ?? "?"})`
                    : ""
                }`}
          </span>
        ) : compactChrome ? null : (
          <span className="muted">Sem locator ativo</span>
        )}
      </div>

      {loading && !useIframeFallback ? (
        <p className="muted" data-testid="pdf-loading">
          Carregando PDF…
        </p>
      ) : null}

      {pdfError && useIframeFallback ? (
        <p className="muted ingestion-pdf-error" data-testid="pdf-error">
          {pdfError}
        </p>
      ) : null}

      <div
        ref={wrapRef}
        className="ingestion-pdf-frame-wrap"
        style={
          useIframeFallback
            ? {
                transform: `scale(${zoom})`,
                transformOrigin: "top left",
                width: `${100 / zoom}%`,
              }
            : undefined
        }
      >
        {useIframeFallback ? (
          <iframe
            title="Pré-visualização PDF quarantine"
            src={iframeSrc}
            className="ingestion-pdf-frame"
            data-testid="pdf-iframe"
          />
        ) : (
          <canvas ref={canvasRef} className="ingestion-pdf-canvas" data-testid="pdf-canvas" />
        )}
        {highlight ? (
          <div
            className="ingestion-pdf-highlight"
            data-testid="pdf-highlight"
            style={{
              left: `${(activeLocator!.x ?? 0) * 100}%`,
              top: `${(activeLocator!.y ?? 0) * 100}%`,
              width: `${(activeLocator!.w ?? 0.05) * 100}%`,
              height: `${(activeLocator!.h ?? 0.02) * 100}%`,
            }}
          />
        ) : null}
      </div>
    </div>
  );
}

export { parseLocator };
