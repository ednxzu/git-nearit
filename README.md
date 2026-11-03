# git-nearit

A small `git-review`-style tool for **Gitea** and **GitLab**. You commit, run one command, and it
pushes your work to a change branch and opens the pull or merge request for you.

```bash
git commit -m "fix: improve performance"   # on main, or on the branch you want to target
git lab-review                             # or git tea-review for Gitea
```

That replaces creating a branch, pushing it with the right flags and filling in the form in the web
UI.

## Installation

You need Python 3.11+ and git. Install it with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install git+https://github.com/ednxzu/git-nearit
```

This puts `git-tea-review` and `git-lab-review` on your `PATH`, so git picks them up as
`git tea-review` and `git lab-review`. To upgrade later:

```bash
uv tool upgrade git-nearit
```

## Configuration

Tokens are read from git config, keyed by the hostname of your `origin` remote.

Gitea needs a token with `repo` permissions (Settings → Applications):

```bash
git config nearit.gitea.git.example.com.token YOUR_TOKEN
```

GitLab needs a token with the `api` scope (Preferences → Access Tokens):

```bash
git config nearit.gitlab.gitlab.com.token YOUR_TOKEN
```

To keep the token out of your git config, point it at an environment variable instead:

```bash
git config nearit.gitlab.gitlab.com.token 'env(GITLAB_TOKEN)'
export GITLAB_TOKEN="your-token-here"
```

If the API isn't served from `https://<hostname>`, set the base URL:

```bash
git config nearit.gitea.git.example.com.url https://git.example.com:8443
```

## Usage

The commands are the same for both platforms: `git tea-review` for Gitea and `git lab-review` for
GitLab.

### Submit a review

```bash
git lab-review            # target the default branch
git lab-review develop    # target another branch
git lab-review -w         # open it as a draft; -r marks it ready again
```

If you run it from the target branch, it moves your commits to a new `change/YYYYMMDDHHmmss`
branch and resets the target branch to its `origin` state. It then pushes, asks for a title and
opens your editor for the description. If a review already exists for the branch, it just pushes
the new commits.

### Download a review

```bash
git lab-review -d 42
```

This fetches the review's branch and checks it out.

### List open reviews

```bash
git lab-review -l            # for the default branch
git lab-review -l develop    # for another branch
```

### Non-interactive / agent usage

Scripts and AI agents can pass everything on the command line:

| Option | Meaning |
|---|---|
| `-t, --title TEXT` | Full title, `type/short-desc` with type one of `feat`, `fix`, `chore`, `docs`, `ci`, `test` and a description of at most 30 chars of `a-z`, `0-9` and `-` (e.g. `feat/add-cli-desc`). No draft prefix: use `--wip`/`--ready`. |
| `-m, --message TEXT` | Description given inline. |
| `-F, --message-file PATH` | Description read from a file, `-` for stdin. |
| `--no-edit` | Description is the last commit subject and body, no editor. |
| `--json` | Machine-readable result on stdout, logs on stderr (submit and list mode). |

`-m`, `-F` and `--no-edit` can't be combined. It never prompts when stdin isn't a terminal or
`--json` is set. In that case, creating a review without a title or description fails before
anything is pushed, and the error names the missing option.

```bash
git lab-review --json -t feat/add-cli-desc -F - <<'EOF'
## Summary
...
EOF
```

```json
{"action": "created", "number": 42, "url": "https://gitlab.example.com/group/repo/-/merge_requests/42", "title": "feat/add-cli-desc", "draft": false, "source_branch": "change/20261103120000", "target_branch": "main"}
```

An existing review only changes when you ask: `-t` replaces the title and keeps the draft state
unless `--wip` or `--ready` is given. `-m`, `-F` and `--no-edit` replace the description. For
example, after amending a commit:

```bash
git commit --amend
git lab-review -t fix/new-name --no-edit
```

`action` is `created`, `updated` or `unchanged`. With `--json`, `-l` prints a JSON array instead
of the table.

## Development

```bash
git clone https://github.com/ednxzu/git-nearit
cd git-nearit
uv sync --group test
uv run pytest
uv run ruff check .
```

Development is not done on GitHub, which is simply a mirror of the code hosted on [my own GitLab](https://gitlab.ednz.fr/ednz-cloud/git-nearit). Pull requests on GitHub will not be merged.
Please contact me for development-related questions on this project.

## Contributing

Write commits as [conventional commits](https://www.conventionalcommits.org/), since releases and
the changelog are generated with commitizen. Add tests for what you change, and submit it with the
tool itself: `git lab-review` or `git tea-review` :)

## License

MIT

## Acknowledgments

Inspired by [git-review](https://opendev.org/opendev/git-review) from the OpenStack project.
