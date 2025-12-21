import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import questionary
from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("git-nearit")
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        show_level=True,
        markup=True,
        rich_tracebacks=True,
        omit_repeated_times=False,
    )

    logger.addHandler(handler)
    return logger


def select_from_menu(prompt: str, choices: list[str]) -> str:
    result = questionary.select(prompt, choices=choices).ask()
    if result is None:
        console.print("[ERROR] Selection cancelled", style="bold red")
        sys.exit(1)
    return result


def get_text_input(prompt: str, validate: Optional[callable] = None) -> str:
    result = questionary.text(prompt, validate=validate).ask()
    if result is None:
        console.print("[ERROR] Input cancelled", style="bold red")
        sys.exit(1)
    return result


def edit_in_editor(initial_content: str, prefix: str = "git-nearit") -> str:
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", prefix=prefix, delete=False) as tmp:
        tmp.write(initial_content)
        tmp_path = Path(tmp.name)

    editor = os.getenv("EDITOR", "vi")
    subprocess.run([editor, str(tmp_path)], check=False)

    content = tmp_path.read_text()

    tmp_path.unlink()

    lines = [
        line for line in content.split("\n") if not line.strip().startswith("#") and line.strip()
    ]

    return "\n".join(lines)
