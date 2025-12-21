import subprocess


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
