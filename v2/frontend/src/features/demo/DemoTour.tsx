import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { PdfViewerPanel } from "../ingestion/PdfViewerPanel";
import { demoSteps } from "./demoSteps";
import { readJson, validateManifest, type DemoManifest } from "./demoManifest";
import { waitForTarget } from "./demoWait";
import "./demo.css";

type Phase = "idle" | "validating" | "loading" | "running" | "paused" | "error" | "complete";

export function DemoTour() {
  const navigate = useNavigate(), location = useLocation();
  const [available, setAvailable] = useState(false);
  const [manifest, setManifest] = useState<DemoManifest | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [index, setIndex] = useState(0), [seconds, setSeconds] = useState(50);
  const [remaining, setRemaining] = useState(50), [message, setMessage] = useState("");
  const [documentOpen, setDocumentOpen] = useState(false);
  const [ready, setReady] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const panelRef = useRef<HTMLElement>(null);
  const work = useRef<AbortController | null>(null), timer = useRef<number>();
  const highlight = useRef<HTMLElement | null>(null), expectedPath = useRef<string | null>(null);
  const phaseRef = useRef<Phase>("idle"), remainingRef = useRef(50), secondsRef = useRef(50);
  const startButton = useRef<HTMLButtonElement>(null), exitButton = useRef<HTMLButtonElement>(null);
  const restoreFocus = useRef(false);
  const steps = manifest ? demoSteps(manifest) : [];
  const step = steps[index], active = phase !== "idle";

  function positionTarget(el: HTMLElement, first = false) {
    if (first) { window.scrollTo({ top: 0, behavior: "instant" }); return; }
    const wide = document.body.classList.contains("demo-wide");
    const top = wide ? 16 : (panelRef.current?.getBoundingClientRect().height ?? 0) + 16;
    const bounds = el.getBoundingClientRect(), usableHeight = window.innerHeight - top - 24;
    if (bounds.top < top || bounds.bottom > window.innerHeight - 16) {
      const offset = bounds.height < usableHeight ? Math.max(0, (usableHeight - bounds.height) / 2) : 0;
      window.scrollTo({ top: Math.max(0, window.scrollY + bounds.top - top - offset), behavior: "instant" });
    }
  }

  function changePhase(value: Phase) { phaseRef.current = value; setPhase(value); }
  function cancelWork() {
    work.current?.abort(); work.current = null;
    clearInterval(timer.current);
    highlight.current?.classList.remove("demo-highlight"); highlight.current = null;
  }
  function pause(reason = "Pausado. Você tem o controle da aplicação.") {
    cancelWork(); changePhase("paused"); setMessage(reason);
  }
  function exit() {
    cancelWork(); expectedPath.current = null; setDocumentOpen(false);
    restoreFocus.current = true; changePhase("idle"); setMessage("");
  }
  async function visit(next: number, data: DemoManifest, duration = secondsRef.current) {
    cancelWork();
    const controller = new AbortController(); work.current = controller;
    const selected = demoSteps(data)[next];
    setIndex(next); setMessage(""); setReady(false); changePhase("loading");
    remainingRef.current = duration; setRemaining(duration);
    setDocumentOpen(Boolean(selected.pdf)); expectedPath.current = selected.path;
    navigate(selected.path);
    try {
      const el = await waitForTarget(selected.path, selected.target, controller.signal);
      if (controller.signal.aborted) return;
      highlight.current = el; el.classList.add("demo-highlight");
      positionTarget(el, next === 0);
      setReady(true); changePhase("running");
      timer.current = window.setInterval(() => {
        // Readiness is retained throughout the reading period, not only at entry.
        if (!el.isConnected || !document.querySelector(selected.target)) {
          pause("O elemento apresentado deixou de estar disponível. Confira a tela antes de continuar."); return;
        }
        remainingRef.current = Math.max(0, remainingRef.current - 1); setRemaining(remainingRef.current);
        if (remainingRef.current === 0) {
          clearInterval(timer.current);
          if (next + 1 < demoSteps(data).length) void visit(next + 1, data);
          else { cancelWork(); changePhase("complete"); setMessage("Roteiro concluído. Nenhuma operação de negócio foi executada pelo tour."); }
        }
      }, 1000);
    } catch (error) {
      if (controller.signal.aborted) return;
      cancelWork(); changePhase("error"); setMessage(error instanceof Error ? error.message : String(error));
    }
  }
  async function start() {
    cancelWork(); setManifest(null); setReady(false); setMessage(""); changePhase("validating");
    const controller = new AbortController(); work.current = controller;
    const timeout = window.setTimeout(() => {
      controller.abort(); changePhase("error"); setMessage("A validação demorou mais que o esperado. Confira o servidor e tente novamente; nenhum dado foi preparado automaticamente.");
    }, 20000);
    try {
      const data = await validateManifest(controller.signal);
      if (controller.signal.aborted) return;
      setManifest(data); void visit(0, data);
    } catch (error) {
      if (controller.signal.aborted) return;
      changePhase("error"); setManifest(null); setMessage(error instanceof Error ? error.message : String(error));
    } finally { clearTimeout(timeout); }
  }

  useEffect(() => {
    const controller = new AbortController();
    if (["127.0.0.1", "localhost"].includes(window.location.hostname)) {
      void readJson("/api/health", controller.signal).then(h => {
        setAvailable(h.app_env === "test" && h.logical_database === "epic_v2_test" && h.schema_ok);
      }).catch(() => setAvailable(false));
    }
    return () => { controller.abort(); cancelWork(); };
  }, []);
  useEffect(() => {
    if (active && expectedPath.current && location.pathname + location.search + location.hash !== expectedPath.current) {
      pause("Navegação manual detectada. O tour não disputará o controle; Continuar retorna à etapa escolhida.");
      setDocumentOpen(false); setReady(false); expectedPath.current = null;
    }
  }, [location.pathname, location.search, location.hash]);
  useEffect(() => {
    document.body.classList.toggle("demo-active", active);
    if (active) exitButton.current?.focus();
    else if (restoreFocus.current) { restoreFocus.current = false; startButton.current?.focus(); }
    return () => document.body.classList.remove("demo-active");
  }, [active]);
  useEffect(() => {
    if (!active) return;
    let frame = 0;
    const measure = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const shell = document.querySelector(".shell"), sidebar = document.querySelector(".shell-sidebar"), main = document.querySelector(".shell-main");
        const style = main ? getComputedStyle(main) : null;
        const gutters = style ? parseFloat(style.paddingLeft) + parseFloat(style.paddingRight) : 48;
        const availableWidth = Math.min(shell?.getBoundingClientRect().width ?? window.innerWidth, window.innerWidth) - (sidebar?.getBoundingClientRect().width ?? 220) - gutters;
        // Reserve 340px only if the application retains >=1000px of useful width.
        const wide = availableWidth - 340 >= 1000;
        document.body.classList.toggle("demo-wide", wide);
        const mainBounds = main?.getBoundingClientRect();
        document.documentElement.style.setProperty("--demo-panel-left", `${(mainBounds?.left ?? 220) + (style ? parseFloat(style.paddingLeft) : 24)}px`);
        document.documentElement.style.setProperty("--demo-panel-width", `${Math.max(240, (mainBounds?.width ?? availableWidth + gutters) - gutters)}px`);
        document.documentElement.style.setProperty("--demo-panel-offset", `${wide ? 0 : (panelRef.current?.getBoundingClientRect().height ?? 0) + 16}px`);
        if (highlight.current) positionTarget(highlight.current, expectedPath.current === "/dashboard");
      });
    };
    const observer = new ResizeObserver(measure);
    for (const el of [document.querySelector(".shell"), document.querySelector(".shell-sidebar"), panelRef.current]) if (el) observer.observe(el);
    window.addEventListener("resize", measure); measure();
    return () => { observer.disconnect(); window.removeEventListener("resize", measure); cancelAnimationFrame(frame); document.body.classList.remove("demo-wide"); for (const key of ["offset", "left", "width"]) document.documentElement.style.removeProperty(`--demo-panel-${key}`); };
  }, [active]);
  useEffect(() => {
    const key = (event: KeyboardEvent) => { if (event.key === "Escape" && phaseRef.current !== "idle") exit(); };
    const interact = (event: PointerEvent) => {
      if (["running", "loading"].includes(phaseRef.current) && event.target instanceof Element && !event.target.closest(".demo-panel,.demo-entry")) {
        pause("Interação manual detectada. A automação foi pausada para você explorar a aplicação.");
      }
    };
    const hidden = () => { if (document.hidden && ["running", "loading"].includes(phaseRef.current)) pause("Pausado porque a aplicação deixou de estar visível."); };
    window.addEventListener("keydown", key); document.addEventListener("visibilitychange", hidden); document.addEventListener("pointerdown", interact, true);
    return () => { window.removeEventListener("keydown", key); document.removeEventListener("visibilitychange", hidden); document.removeEventListener("pointerdown", interact, true); };
  }, []);

  if (!available) return null;
  return <>
    <div className="demo-entry">
      <button className="ui-button" ref={startButton} onClick={() => void start()} disabled={active} data-testid="demo-start">Iniciar demonstração</button>
      <span>Ambiente de demonstração · tour de leitura</span>
      <details><summary>Informações técnicas</summary><p>Revisão {import.meta.env.VITE_BUILD_ID || "local"}. O tour não executa operações de negócio. O administrador continua podendo operar manualmente.</p></details>
    </div>
    {active && <aside ref={panelRef} className={`demo-panel${collapsed ? " demo-panel--collapsed" : ""}`} aria-label="Demonstração executiva" data-testid="demo-panel" data-phase={phase} data-step={index + 1}>
      <div className="demo-panel-top"><strong>Tour de leitura · {index + 1}/8</strong><button className="ui-button ui-button--ghost" aria-expanded={!collapsed} onClick={() => setCollapsed(v => !v)}>{collapsed ? "Expandir" : "Recolher"}</button></div>
      <p className="demo-progress" aria-live="polite">{phase === "validating" ? "Validando ambiente, registros e documentos…" : phase === "loading" ? "Aguardando tela e elemento…" : phase === "running" ? `Automático · próxima etapa em ${remaining}s` : phase === "complete" ? "Concluído" : phase === "error" ? "Interrompido" : "Pausado"}</p>
      {message && <p role="status" className="demo-message">{message}</p>}
      <div className="demo-controls">
        {["loading", "running", "validating"].includes(phase) ? <button className="ui-button" onClick={() => pause()}>Pausar</button> : manifest && phase !== "complete" ? <button className="ui-button" onClick={() => void visit(index, manifest, Math.max(1, remainingRef.current))}>Continuar</button> : <button className="ui-button" onClick={() => void start()}>Reiniciar</button>}
        <button className="ui-button" disabled={!manifest || index === 0 || phase === "validating"} onClick={() => manifest && void visit(index - 1, manifest)}>Anterior</button>
        <button className="ui-button" disabled={!manifest || index === 7 || phase === "validating"} onClick={() => manifest && void visit(index + 1, manifest)}>Próximo</button>
        <label className="demo-step-label"><span className="sr-only">Escolher etapa</span><select aria-label="Escolher etapa" value={index} disabled={!manifest || phase === "validating"} onChange={e => manifest && void visit(Number(e.target.value), manifest)}>{steps.map((s, n) => <option key={s.path} value={n}>{n + 1}. {s.title}</option>)}</select></label>
        <button className="ui-button ui-button--ghost" ref={exitButton} onClick={exit}>Sair do tour</button>
      </div>
      {step && <div className="demo-copy">
        {ready && ["running", "paused", "complete"].includes(phase) && <div data-testid="demo-narrative">
          <h3>{step.question}</h3><p>{step.see}</p><p className="demo-next">{step.next}</p>
        </div>}
      </div>}
      <details className="demo-settings"><summary>Ritmo e informações</summary>
      {step && <><p>{step.action}</p><p>{step.decision}</p><p>{step.next}</p></>}
      <label>Tempo por etapa<select value={seconds} onChange={e => { const n = Number(e.target.value); secondsRef.current = n; setSeconds(n); remainingRef.current = n; setRemaining(n); }}><option value={50}>50s · roteiro de 6–8 min</option><option value={40}>40s · conciso</option><option value={60}>60s · detalhado</option><option value={2}>2s · ensaio técnico</option></select></label>
      <p className="demo-footnote">Sair/Esc cancela a automação e devolve o foco. Interação manual pausa. O administrador pode operar manualmente. Revisão {import.meta.env.VITE_BUILD_ID || "local"}.</p>
      </details>
    </aside>}
    {active && <div className="demo-spacer" aria-hidden="true" />}
    {documentOpen && manifest && <section className="demo-document" data-demo-document>
      <h2>Documento do pedido · {manifest.scenario_id}</h2>
      <p>Documento sintético vinculado por API; não é resultado de ingestão.</p>
      <PdfViewerPanel contentUrl={`/api/documents/${manifest.ids.commercial_document}/content`} activeLocator={null} compactChrome />
    </section>}
  </>;
}
