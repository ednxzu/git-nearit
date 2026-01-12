# git-nearit

A streamlined Git review workflow tool for **Gitea** and **GitLab**, inspired by Gerrit's `git-review`.

## What is it?

`git-nearit` simplifies the pull request workflow by automating branch creation, pushing, and PR management. Instead of manually creating branches, pushing with the right flags, and navigating to your Git hosting UI, you can submit reviews with a single command.

**Key features:**

- One-command review submission
- Download and checkout pull requests locally
- List active reviews for a repository

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
# yes, on the main branch! Or the branch you want to submit to
git commit -m "fix: improve performance"
git tea-review
# That's it! Branch created, pushed, and PR opened
```

## Installation

### Prerequisites
- Python 3.11 or higher
- Git
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

```bash
git clone https://github.com/yourusername/git-nearit.git
cd git-nearit
# if using uv
uv sync
uv tool install . -e
# if using pip
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

Creates timestamped `change/YYYYMMDDHHmmss` branches when submitting from main, prompts for title/description, and opens the PR automatically.

### Download a review

```bash
git tea-review -d 42    # Gitea
git lab-review -d 42    # GitLab
```

### List active reviews

```bash
git tea-review -l       # List reviews for main branch
git tea-review -l develop  # List for specific branch
```

## Development

```bash
git clone https://github.com/yourusername/git-nearit.git
cd git-nearit
uv sync --all-extras
uv run pytest -xvs
```

## Troubleshooting

- **"No token found"**: Configure token for your hostname: `git config nearit.gitea.YOUR_HOSTNAME.token YOUR_TOKEN`
- **"Uncommitted changes"**: Commit or stash tracked file changes (untracked files are fine)
- **"Not a git repository"**: Run from inside a git repository

## Roadmap

- [x] Gitea support
- [x] Download PR for review/edit (`-d` flag)
- [x] Complete GitLab client implementation
- [ ] GitHub support
- [ ] Interactive rebase workflow
- [ ] Draft PR support

## License

MIT

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Acknowledgments

Inspired by [git-review](https://opendev.org/opendev/git-review) from the OpenStack project.
