import os
import re

from git import GitConfigParser


def get_git_config(key: str, default: str = "") -> str:
    try:
        config = GitConfigParser()
        section, option = _parse_config_key(key)

        value = config.get_value(section, option, default=default)

        # Support env(ENV_VAR) syntax
        if isinstance(value, str):
            env_match = re.match(r"^env\(([A-Z_][A-Z0-9_]*)\)$", value)
            if env_match:
                env_var = env_match.group(1)
                return os.getenv(env_var, default)

        return value
    except Exception:
        return default


def _parse_config_key(key: str) -> tuple[str, str]:
    # Handle keys like "nearit.gitea.hostname" -> section="nearit.gitea", option="hostname"
    # Or "nearit.gitea.git.ednz.fr" -> section='nearit "gitea"', option='git.ednz.fr'
    parts = key.split(".")
    if len(parts) < 2:
        raise ValueError(f"Invalid config key: {key}")

    # For keys like nearit.gitea.hostname -> (nearit.gitea, hostname)
    if len(parts) == 3:
        section = f"{parts[0]}.{parts[1]}"
        option = parts[2]
    # For keys like nearit.gitea.git.ednz.fr -> (nearit "gitea", git.ednz.fr)
    else:
        section = f'{parts[0]} "{parts[1]}"'
        option = ".".join(parts[2:])

    return section, option
