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
    HEADER = "# ---- EDIT BELOW THIS LINE ----"
    FOOTER = "# ---- EDIT ABOVE THIS LINE ----"

    full_content = f"{HEADER}\n{initial_content}\n{FOOTER}"

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", prefix=prefix, delete=False) as tmp:
        tmp.write(full_content)
        tmp_path = Path(tmp.name)

    editor = os.getenv("EDITOR", "vi")
    subprocess.run([editor, str(tmp_path)], check=False)

    content = tmp_path.read_text()
    tmp_path.unlink()

    lines = content.split("\n")

    if lines and lines[0] == HEADER:
        lines = lines[1:]

    if lines and lines[-1] == FOOTER:
        lines = lines[:-1]

    result = "\n".join(lines).strip()

    return result


def get_pr_title() -> str:
    import re

    types = ["feat", "fix", "chore", "docs", "ci", "test"]
    pr_type = select_from_menu("Select PR/MR type:", types)

    desc = get_text_input(
        "Enter short description (max 30 chars, lowercase, dash-separated): ",
        validate=lambda text: (
            bool(re.match(r"^[a-z0-9-]{1,30}$", text))
            or "Invalid format. Use lowercase a-z, 0-9, and dashes only (max 30 chars)"
        ),
    )

    return f"{pr_type}/{desc}"


def get_pr_description(commit_subject: str, commit_body: str) -> str:
    initial_content = f"{commit_subject}\n\n{commit_body}".strip()

    description = edit_in_editor(initial_content)

    if not description:
        console.print("[ERROR] PR/MR creation aborted: empty description", style="bold red")
        sys.exit(1)

    return description
