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

        return str(value)
    except Exception:
        return default


def _parse_config_key(key: str) -> tuple[str, str]:
    # Git config splits on the LAST dot:
    # "nearit.gitea.git.ednz.fr.token" -> section="nearit.gitea.git.ednz.fr", option="token"
    # Git stores multi-part sections as: nearit "gitea.git.ednz.fr"
    parts = key.rsplit(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid config key: {key}")

    section_parts = parts[0].split(".", 1)
    if len(section_parts) == 2:
        # nearit.gitea.git.ednz.fr -> nearit "gitea.git.ednz.fr"
        section = f'{section_parts[0]} "{section_parts[1]}"'
    else:
        # Simple section without subsection
        section = section_parts[0]

    option = parts[1]
    return section, option
