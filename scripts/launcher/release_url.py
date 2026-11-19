"""Open the installed UI without reusing a heuristically cached HTML entry point."""
from hashlib import sha256
from pathlib import Path


def current_release_url(base_url: str, runtime: Path) -> str:
    # Version the HTML, not business parameters. The existing launcher has already
    # verified this runtime and its served bytes before opening the browser.
    digest = sha256((runtime / "v2/frontend/dist/index.html").read_bytes()).hexdigest()[:16]
    return base_url.rstrip("/") + "/?epic_ui=" + digest
