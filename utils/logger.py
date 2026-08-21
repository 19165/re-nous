import sys
import logging
from rich.logging import RichHandler
from rich.console import Console

# Ensure UTF-8 output encoding on Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Shared Rich Console
console = Console(force_terminal=True)

# Configure Rich Logger with markup=True so Rich tags ([bold green], [cyan], etc.) render properly
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(
            rich_tracebacks=True,
            show_path=False,
            console=console,
            markup=True,
        )
    ]
)

# Silence noisy HTTP client loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger("agentic_ai")
