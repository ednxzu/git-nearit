import subprocess
from enum import Enum


class OutputStyle(str, Enum):
    PLAIN = "plain"
    EMOJI = "emoji"


def get_git_config(key: str, default: str = "") -> str:
    try:
        result = subprocess.run(
            ["git", "config", "--get", key],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return default
    except Exception:
        return default


def get_output_style(platform: str = "tea") -> OutputStyle:
    config_key = f"{platform}-review.style"
    style = get_git_config(config_key, "plain").lower()

    if style == "emoji":
        return OutputStyle.EMOJI
    return OutputStyle.PLAIN
