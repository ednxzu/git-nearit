import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import questionary
from questionary import Style
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from git_nearit.models import ReviewListItem

console = Console()
err_console = Console(stderr=True)

PR_TYPES = ["feat", "fix", "chore", "docs", "ci", "test"]
PR_TITLE_DESC_PATTERN = re.compile(r"[a-z0-9-]{1,30}")
PR_TITLE_PATTERN = re.compile(rf"^({'|'.join(PR_TYPES)})/{PR_TITLE_DESC_PATTERN.pattern}$")

custom_style = Style(
    [
        ("qmark", ""),
        ("question", "bold"),
        ("answer", ""),
        ("pointer", ""),
        ("highlighted", "bold cyan"),
        ("selected", ""),
        ("separator", ""),
        ("instruction", ""),
        ("text", ""),
        ("disabled", "fg:#858585 italic"),
    ]
)


def setup_logging(json_output: bool = False) -> logging.Logger:
    """Configure the git-nearit logger.

    With json_output, logs go to stderr so stdout only carries the JSON result.
    """
    logger = logging.getLogger("git-nearit")
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    handler = RichHandler(
        console=err_console if json_output else console,
        show_time=False,
        show_path=False,
        show_level=True,
        markup=True,
        rich_tracebacks=True,
        omit_repeated_times=False,
    )

    logger.addHandler(handler)
    return logger


def emit_json(data: Any) -> None:
    """Write exactly one JSON document to stdout."""
    sys.stdout.write(json.dumps(data) + "\n")
    sys.stdout.flush()


def select_from_menu(prompt: str, choices: list[str]) -> str:
    logger = logging.getLogger("git-nearit")
    logger.info(prompt)
    result = questionary.select(
        message="",
        choices=choices,
        style=custom_style,
        qmark="",
        use_shortcuts=True,
    ).ask()
    if result is None:
        logger.error("Selection cancelled")
        sys.exit(1)
    logger.info(f"Selected: {result}")
    return result


def get_text_input(prompt: str, validate: Callable | None = None) -> str:
    logger = logging.getLogger("git-nearit")
    logger.info(prompt)
    result = questionary.text(
        message="> ",
        validate=validate,
        style=custom_style,
        qmark="",
    ).ask()
    if result is None:
        logger.error("Input cancelled")
        sys.exit(1)
    return result


def edit_in_editor(initial_content: str, prefix: str = "git-nearit") -> str:
    HEADER = "# ---- EDIT BELOW THIS LINE ----"
    FOOTER = "# ---- EDIT ABOVE THIS LINE ----"

    full_content = f"{HEADER}\n\n{initial_content}\n\n{FOOTER}"

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", prefix=prefix, delete=False) as tmp:
        tmp.write(full_content)
        tmp_path = Path(tmp.name)

    editor = os.getenv("EDITOR", "vi")
    subprocess.run([editor, str(tmp_path)], check=False)

    content = tmp_path.read_text()
    tmp_path.unlink()

    lines = content.split("\n")

    try:
        header_idx = lines.index(HEADER)
        lines = lines[header_idx + 1 :]
    except ValueError:
        pass

    try:
        footer_idx = lines.index(FOOTER)
        lines = lines[:footer_idx]
    except ValueError:
        pass

    result = "\n".join(lines).strip()

    return result


def validate_pr_title(title: str) -> str | None:
    """Return an error message if title is not a valid PR/MR title, None otherwise."""
    pr_type, sep, desc = title.partition("/")
    if not sep or pr_type not in PR_TYPES:
        return f"Invalid type. Title must start with one of: {', '.join(PR_TYPES)}, then '/'"
    if not PR_TITLE_DESC_PATTERN.fullmatch(desc):
        return "Invalid format. Use lowercase a-z, 0-9, and dashes only (max 30 chars)"
    if not PR_TITLE_PATTERN.fullmatch(title):
        return f"Invalid title. Expected format: {PR_TITLE_PATTERN.pattern}"
    return None


def get_pr_title() -> str:
    pr_type = select_from_menu("Select PR/MR type:", PR_TYPES)

    desc = get_text_input(
        "Enter short description (max 30 chars, lowercase, dash-separated): ",
        validate=lambda text: validate_pr_title(f"{pr_type}/{text}") or True,
    )

    return f"{pr_type}/{desc}"


def is_interactive(json_output: bool = False) -> bool:
    """Prompts are only allowed on a TTY and never when stdout carries JSON."""
    return sys.stdin.isatty() and not json_output


def commit_description(commit_subject: str, commit_body: str) -> str:
    return f"{commit_subject}\n\n{commit_body}".strip()


def read_message_file(path: str) -> str:
    """Read a description from path, '-' meaning stdin."""
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text()


def get_pr_description(commit_subject: str, commit_body: str) -> str:
    initial_content = commit_description(commit_subject, commit_body)

    description = edit_in_editor(initial_content)

    if not description:
        console.print("[ERROR] PR/MR creation aborted: empty description", style="bold red")
        sys.exit(1)

    return description


def format_relative_time(iso_timestamp: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt

        if diff.days > 365:
            years = diff.days // 365
            return f"{years}y ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months}mo ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "just now"
    except ValueError:
        return iso_timestamp


def display_reviews_table(reviews: list[ReviewListItem], base_branch: str) -> None:
    if not reviews:
        console.print(f"[yellow]No open reviews found for branch '{base_branch}'[/yellow]")
        return

    table = Table(
        title=f"Reviews for '{base_branch}'", show_header=True, header_style="bold magenta"
    )
    table.add_column("PR #", style="cyan", justify="right", width=6)
    table.add_column("Title", style="white", width=50)
    table.add_column("Author", style="green", width=15)
    table.add_column("State", style="yellow", width=8)
    table.add_column("Draft", justify="center", width=5)
    table.add_column("Created", style="blue", width=10)
    table.add_column("Updated", style="blue", width=10)

    for review in reviews:
        number = str(review.number if review.number else "?")
        title = review.title or ""
        if len(title) > 47:
            title = title[:44] + "..."

        # Add hyperlink to title if URL is available
        if review.url:
            title = f"[link={review.url}]{title}[/link]"

        author = review.author or "unknown"
        state = review.state or "unknown"

        if state == "open":
            state_str = "[green]open[/green]"
        elif state == "closed":
            state_str = "[red]closed[/red]"
        elif state == "merged":
            state_str = "[blue]merged[/blue]"
        else:
            state_str = state

        draft = "✓" if review.draft else ""

        created_at = format_relative_time(review.created_at or "")
        updated_at = format_relative_time(review.updated_at or "")

        table.add_row(number, title, author, state_str, draft, created_at, updated_at)

    console.print(table)
