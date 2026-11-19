import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { fitRecordActions } from "./recordActionLayout";
import "./recordWorkHeader.css";

export type RecordTopic = {
  id: string; label: string; state: string; result: string; href: string;
  tone: "complete" | "partial" | "blocked" | "attention" | "info" | "empty" | "loading" | "error";
};
export type RecordAction = { label: string; href?: string; onClick?: () => void; disabled?: boolean; reason?: string; testId?: string };

/** Navigation only: reveal the section, scroll below the sticky identity and move focus. */
export function focusRecordSection(id: string) {
  const target = document.getElementById(id.replace(/^#/, ""));
  if (!target) return;
  let parent: HTMLElement | null = target;
  while (parent) { if (parent instanceof HTMLDetailsElement) parent.open = true; parent = parent.parentElement; }
  target.setAttribute("tabindex", "-1");
  target.scrollIntoView({ block: "start", behavior: "auto" });
  target.focus({ preventScroll: true });
}

export function RecordWorkHeader({ title, context, status, primary, secondary, more = [], topics }: {
  title: string; context?: string; status?: ReactNode; primary?: RecordAction; secondary?: RecordAction;
  more?: RecordAction[]; topics: RecordTopic[];
}) {
  const sentinel = useRef<HTMLDivElement>(null), header = useRef<HTMLElement>(null), menu = useRef<HTMLDetailsElement>(null);
  const [compact, setCompact] = useState(false);
  // Caller order is the screen's order: primary, secondary, then the existing actions.
  const actions = [primary, secondary, ...more].filter((item): item is RecordAction => !!item);
  const [visibleCount, setVisibleCount] = useState(actions.length);
  const [stacked, setStacked] = useState(false);
  const [identityWidth, setIdentityWidth] = useState<number>();
  const pointerActive = useRef(false), measureNow = useRef(() => {});
  const signature = actions.map(a => `${a.testId || a.label}:${a.disabled}:${a.reason || ""}`).join("|");
  useLayoutEffect(() => {
    const root = header.current;
    if (!root || typeof ResizeObserver === "undefined") return;
    let frame = 0, cancelled = false;
    const measure = () => {
      const title = root.querySelector("h1")!, metric = root.querySelector<HTMLElement>(".record-title-measure")!;
      const font = getComputedStyle(title); metric.style.font = font.font; metric.style.letterSpacing = font.letterSpacing;
      const badge = root.querySelector<HTMLElement>(".record-title .status-badge");
      const naturalIdentity = metric.getBoundingClientRect().width + (badge ? badge.getBoundingClientRect().width + 12 : 0);
      const widths = [...root.querySelectorAll<HTMLElement>("[data-action-measure]")].map(e => e.getBoundingClientRect().width);
      const trigger = root.querySelector<HTMLElement>(".record-trigger-measure")!.getBoundingClientRect().width;
      const available = root.clientWidth;
      if (available <= 0) return; // Hidden/unlaid-out host: wait for an actual measurement.
      const minimumActions = (primary ? widths[0] || 0 : 0) + (actions.length > (primary ? 1 : 0) ? trigger + (primary ? 8 : 0) : 0);
      const nextStacked = naturalIdentity + minimumActions + 18 > available;
      setStacked(nextStacked); setIdentityWidth(nextStacked ? undefined : Math.ceil(naturalIdentity));
      const actionBudget = nextStacked ? available : available - Math.ceil(naturalIdentity) - 16;
      // Never reparent/remove a focused or activating control. During a resize the
      // current controls may wrap; redistribute when the interaction leaves them.
      const focused = root.querySelector(".record-actions")?.contains(document.activeElement);
      if (!pointerActive.current && !focused && !menu.current?.open) {
        setVisibleCount(fitRecordActions(widths, actionBudget, trigger, !!primary));
      }
    };
    const schedule = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(measure); };
    measureNow.current = schedule;
    const observer = new ResizeObserver(schedule); observer.observe(root);
    root.querySelectorAll("[data-action-measure],.record-title-measure,.record-title .status-badge").forEach(e => observer.observe(e));
    void document.fonts?.ready.then(() => { if (!cancelled) schedule(); });
    measure();
    return () => { cancelled = true; cancelAnimationFrame(frame); observer.disconnect(); };
  }, [signature, title, compact, !!primary]);
  useEffect(() => {
    const observer = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(([entry]) => setCompact(!entry.isIntersecting));
    if (sentinel.current) observer?.observe(sentinel.current);
    return () => observer?.disconnect();
  }, []);
  useEffect(() => {
    const measure = () => document.documentElement.style.setProperty("--record-header-height", `${header.current?.getBoundingClientRect().height ?? 90}px`);
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(measure);
    if (header.current) observer?.observe(header.current); measure();
    const close = (event: KeyboardEvent) => { if (event.key === "Escape" && menu.current?.open) { menu.current.open = false; menu.current.querySelector("summary")?.focus(); } };
    const releasePointer = () => { if (pointerActive.current) { pointerActive.current = false; measureNow.current(); } };
    document.addEventListener("keydown", close);
    // A resize can move the control away from the pointer before release.
    window.addEventListener("pointerup", releasePointer); window.addEventListener("pointercancel", releasePointer);
    return () => { observer?.disconnect(); document.removeEventListener("keydown", close); window.removeEventListener("pointerup", releasePointer); window.removeEventListener("pointercancel", releasePointer); };
  }, []);
  function action(item: RecordAction, main = false) {
    const props = { className: main ? "ui-button record-primary" : "ui-button ui-button--secondary", "data-testid": item.testId, "data-record-primary": main || undefined, "data-record-action": item.testId || item.label };
    const activate = () => { if (menu.current) menu.current.open = false; item.onClick?.(); };
    return <div key={item.label} className="record-action">
      {item.href && !item.disabled ? <Link {...props} to={item.href} onClick={activate}>{item.label}</Link>
        : <button {...props} type="button" disabled={item.disabled} onClick={activate} aria-describedby={item.reason ? `record-reason-${main ? "primary" : item.testId ?? item.label.replace(/\s/g,"-")}` : undefined}>{item.label}</button>}
      {item.reason && <span className="record-action-reason" id={`record-reason-${main ? "primary" : item.testId ?? item.label.replace(/\s/g,"-")}`}>{item.reason}</span>}
    </div>;
  }
  return <>
    <div ref={sentinel} className="record-sentinel" aria-hidden="true" />
    <header ref={header} className={`record-work-header ${compact ? "is-compact" : ""} ${stacked ? "actions-stacked" : ""}`} data-testid="record-work-header">
      <div className="record-identity" style={{width:identityWidth}}><div className="record-title"><h1>{title}</h1>{status}</div>{context && <p>{context}</p>}</div>
      <div className="record-actions" onBlur={() => requestAnimationFrame(() => measureNow.current())}
        onPointerDownCapture={() => { pointerActive.current = true; }}>
        {actions.slice(0,visibleCount).map(item => action(item,item === primary))}
        {visibleCount < actions.length && <details ref={menu} className="record-more" onToggle={() => measureNow.current()}><summary>Mais ações <span aria-hidden="true">⋯</span></summary><div className="record-more-list">{actions.slice(visibleCount).map(item => action(item))}</div></details>}
      </div>
      <div className="record-measures" aria-hidden="true"><span className="record-title-measure">{title}</span>{actions.map(item => <span key={item.testId || item.label} data-action-measure className={item === primary ? "ui-button record-primary" : "ui-button ui-button--secondary"}>{item.label}</span>)}<span className="record-trigger-measure">Mais ações <span>⋯</span></span></div>
    </header>
    {topics.length > 0 && <nav className="record-topics" aria-label="Situação por assunto" data-testid="record-topics">
      {topics.map(topic => <Link key={topic.id} to={topic.href} className={`record-topic tone-${topic.tone}`} data-testid={`record-topic-${topic.id}`}
        onClick={event => { if (topic.href.startsWith("#")) { event.preventDefault(); focusRecordSection(topic.href); } }}>
        <span className="record-topic-label">{topic.label}<span aria-hidden="true">↗</span></span>
        <strong><span className="record-topic-mark" aria-hidden="true">{topic.tone === "complete" ? "✓" : topic.tone === "attention" || topic.tone === "error" ? "!" : "•"}</span>{topic.state}</strong>
        <span className="record-topic-result">{topic.result}</span>
      </Link>)}
    </nav>}
  </>;
}
