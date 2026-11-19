import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
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
    document.addEventListener("keydown", close);
    return () => { observer?.disconnect(); document.removeEventListener("keydown", close); };
  }, []);
  function action(item: RecordAction, main = false) {
    const props = { className: main ? "ui-button record-primary" : "ui-button ui-button--secondary", "data-testid": item.testId, "data-record-primary": main || undefined };
    const activate = () => { if (menu.current) menu.current.open = false; item.onClick?.(); };
    return <div key={item.label} className="record-action">
      {item.href && !item.disabled ? <Link {...props} to={item.href} onClick={activate}>{item.label}</Link>
        : <button {...props} type="button" disabled={item.disabled} onClick={activate} aria-describedby={item.reason ? `record-reason-${main ? "primary" : item.testId ?? item.label.replace(/\s/g,"-")}` : undefined}>{item.label}</button>}
      {item.reason && <span className="record-action-reason" id={`record-reason-${main ? "primary" : item.testId ?? item.label.replace(/\s/g,"-")}`}>{item.reason}</span>}
    </div>;
  }
  return <>
    <div ref={sentinel} className="record-sentinel" aria-hidden="true" />
    <header ref={header} className={`record-work-header ${compact ? "is-compact" : ""}`} data-testid="record-work-header">
      <div className="record-identity"><div className="record-title"><h1>{title}</h1>{status}</div>{context && <p>{context}</p>}</div>
      <div className="record-actions">{primary && action(primary, true)}{secondary && action(secondary)}
        {more.length > 0 && <details ref={menu} className="record-more"><summary>Mais ações <span aria-hidden="true">⋯</span></summary><div className="record-more-list">{more.map(item => action(item))}</div></details>}
      </div>
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
