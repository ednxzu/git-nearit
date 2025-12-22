# git-nearit

A streamlined Git review workflow tool for **Gitea** and **GitLab**, inspired by Gerrit's `git-review`.

## What is it?

`git-nearit` simplifies the pull request workflow by automating branch creation, pushing, and PR management. Instead of manually creating branches, pushing with the right flags, and navigating to your Git hosting UI, you can submit reviews with a single command.

**Key features:**

- One-command review submission
- Download and checkout pull requests locally
- List active review for a repository

## Why use it?

**Traditional workflow:**
```bash
git checkout -b feature/my-change
# ... make changes ...
git add .
git commit -m "fix: improve performance"
git push -u origin feature/my-change
# Navigate to Gitea/GitLab UI
# Click "New Pull Request"
# Fill in title and description
```

**With git-nearit:**
```bash
git add .
# yes, on the main branch ! Or the branch you want to submit to
git commit -m "fix: improve performance"
git tea-review
# That's it! Branch created, pushed, and PR opened
```

## Installation

### Prerequisites
- Python 3.11 or higher
- Git
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Using uv (recommended)

```bash
git clone https://github.com/yourusername/git-nearit.git
cd git-nearit
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync
uv pip install -e .
```

### Using pip

```bash
git clone https://github.com/yourusername/git-nearit.git
cd git-nearit
pip install -e .
```

## Configuration

### Gitea

Configure your Gitea access token:

```bash
# Store token directly
git config nearit.gitea.git.example.com.token YOUR_TOKEN

# Or use environment variable (more secure)
git config nearit.gitea.git.example.com.token env(GITEA_TOKEN)
export GITEA_TOKEN="your-token-here"
```

**Obtaining a token:**
1. Go to your Gitea instance → Settings → Applications
2. Generate a new token with `repo` permissions
3. Copy and configure as shown above

### GitLab

```bash
# Store token directly
git config nearit.gitlab.gitlab.com.token YOUR_TOKEN

# Or use environment variable
git config nearit.gitlab.gitlab.com.token env(GITLAB_TOKEN)
export GITLAB_TOKEN="your-token-here"
```

**Obtaining a token:**
1. Go to GitLab → Preferences → Access Tokens
2. Create a token with `api` scope
3. Copy and configure as shown above

### Custom base URLs

If your Gitea/GitLab instance uses a custom URL:

```bash
git config nearit.gitea.git.example.com.url https://git.example.com:8443
```

## Usage

### Submit a review

**For Gitea:**
```bash
# From any branch (creates timestamped change branch if needed)
git tea-review

# Target a specific branch
git tea-review develop
```

**For GitLab:**
```bash
git lab-review

# Target a specific branch
git lab-review develop
```

**Workflow:**
1. Ensures no uncommitted changes to tracked files
2. Creates a `change/YYYYMMDDHHmmss` branch if on main
3. Pushes with `--force-with-lease` and `--set-upstream`
4. Prompts for PR title and description
5. Creates the pull/merge request

### Download a review

Want to review someone's PR locally?

```bash
# Download and checkout PR #42
git tea-review -d 42

# For GitLab
git lab-review -d 42
```

This fetches the PR's branch and checks it out locally, ready for review.

## How it works

### Branch naming

`git-nearit` creates timestamped branches in the format `change/YYYYMMDDHHmmss`:
- Ensures uniqueness
- Easy to identify when changes were made
- Sorts chronologically

### Safe pushing

Uses `git push --force-with-lease` instead of `--force`:
- Prevents accidentally overwriting others' work
- Only force-pushes if your local ref matches the remote
- Safer for collaborative workflows

### Main branch detection

Automatically detects your repository's main branch:
1. Checks `origin/HEAD` symbolic ref
2. Falls back to `master` if not set

You can also specify a target branch explicitly with `git tea-review <branch>`.

## Development

### Setup

```bash
git clone https://github.com/yourusername/git-nearit.git
cd git-nearit
uv venv
source .venv/bin/activate
uv sync --all-extras
```

### Running tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=git_nearit --cov-report=term-missing

# Specific test file
uv run pytest tests/unit/test_git_client.py -v
```

### Code quality

```bash
# Format code
uv run ruff format

# Lint
uv run ruff check

# Fix auto-fixable issues
uv run ruff check --fix
```

### Project structure

```
git-nearit/
├── git_nearit/
│   ├── cli.py                  # CLI entry points and workflow
│   ├── config.py               # Git config parsing
│   ├── utils.py                # UI utilities (prompts, editor)
│   └── clients/
│       ├── git_client.py       # Local Git operations
│       ├── gitea_client.py     # Gitea API client
│       ├── gitlab_client.py    # GitLab API client (WIP)
│       └── base_vcs_client.py  # Abstract base class
├── tests/
│   ├── base.py                 # Test utilities
│   └── unit/                   # Unit tests
└── pyproject.toml              # Project configuration
```

## Troubleshooting

### "No Gitea token found"

Make sure you've configured your token for the specific hostname:
```bash
git config nearit.gitea.YOUR_HOSTNAME.token YOUR_TOKEN
```

### "You have uncommitted changes"

`git-nearit` prevents running with uncommitted changes to tracked files (untracked files are fine):
```bash
# Commit your changes
git add . && git commit -m "Your message"

# Or stash them
git stash
```

### "Not a git repository"

Run the command from inside a Git repository:
```bash
cd /path/to/your/repo
git tea-review
```

## Roadmap

- [x] Gitea support
- [x] Download PR for review/edit (`-d` flag)
- [ ] Complete GitLab client implementation
- [ ] GitHub support
- [ ] Interactive rebase workflow
- [ ] Draft PR support

## License

[Your license here]

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Acknowledgments

Inspired by [git-review](https://opendev.org/opendev/git-review) from the OpenStack project.
