export function waitForTarget(path: string, selector: string, signal: AbortSignal): Promise<HTMLElement> {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + 15000;
    let stable: HTMLElement | null = null;
    const stop = () => { clearInterval(timer); signal.removeEventListener("abort", abort); };
    const abort = () => { stop(); reject(new DOMException("Interrompido", "AbortError")); };
    const timer = window.setInterval(() => {
      const nodes = document.querySelectorAll<HTMLElement>(selector);
      const el = nodes.length === 1 ? nodes[0] : null;
      const errors = document.querySelector('#main-content [data-testid="pdf-error"], #main-content .notice--danger');
      if (errors?.textContent?.trim()) {
        stop(); reject(new Error(`A tela apresentou um erro: ${errors.textContent.trim()}`)); return;
      }
      if (window.location.pathname + window.location.search + window.location.hash === path && el && el.getBoundingClientRect().height > 0 && el.textContent?.trim()) {
        if (stable === el) { stop(); resolve(el); return; }
        stable = el;
      } else stable = null;
      if (Date.now() >= deadline) { stop(); reject(new Error("A tela ou o elemento esperado não ficou disponível. O tour foi interrompido; confira a aplicação e use Continuar ou o roteiro manual.")); }
    }, 150);
    signal.addEventListener("abort", abort, { once: true });
    if (signal.aborted) abort();
  });
}
