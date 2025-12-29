## v0.5.0 (2025-12-29)

### Feat

- **cli**: improve cli output

### Fix

- **cli**: improve cli output

## v0.4.0 (2025-12-28)

### Feat

- **cli**: add wip flag to create draft reviews

## v0.3.0 (2025-12-27)

### Feat

- **cli**: add hyperlink to review page on listing
- **models**: introduce new data structures for consistency in clients
- **models**: improve datastructures for review objects
- **models**: introduce GitRepository datastructure for high level objects

## v0.2.0 (2025-12-24)

### Feat

- **client/gitlab**: add gitlab client

## v0.1.0 (2025-12-22)

### Feat

- add list option for reviews
- use proper typer commands in cli
- introduce -d flag for downloading reviews
- allow review on non-default branch
- add gitea client
- support passing environment variables in gitconfig
- split some input functions to utils
- **GitClient**: keep untracked files safe from hard reset
- add initial GitClient and cli scaffholding

### Fix

- type expression in utils functions
- enforce type returned from git config entries
- correctly parse gitconfig ouput
- rename operations to review to stay agnostic
- drop emoji option for logging

### Refactor

- move all review handling to vcs clients
