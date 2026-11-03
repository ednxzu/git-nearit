import click

from git_nearit.cli import download_review, list_reviews, run_review
from git_nearit.utils import emit_json, read_message_file, validate_pr_title


@click.command()
@click.argument("target_branch", required=False)
@click.option(
    "-d",
    "--download",
    type=int,
    metavar="PR_ID",
    help="Download and checkout a pull request by ID",
)
@click.option(
    "-l",
    "--list",
    is_flag=True,
    help="List open pull requests (optionally for TARGET_BRANCH)",
)
@click.option(
    "-w",
    "--wip",
    is_flag=True,
    help="Create pull request as draft (adds 'WIP:' prefix to title)",
)
@click.option(
    "-r",
    "--ready",
    is_flag=True,
    help="Create pull request as ready (removes 'WIP:' prefix to title)",
)
@click.option(
    "-t",
    "--title",
    metavar="TEXT",
    help="Pull request title (type/short-desc, e.g. feat/add-cli-desc), skips the prompt",
)
@click.option(
    "-m",
    "--message",
    metavar="TEXT",
    help="Pull request description, skips the editor",
)
@click.option(
    "-F",
    "--message-file",
    type=click.Path(dir_okay=False, allow_dash=True),
    help="Read the pull request description from a file ('-' for stdin)",
)
@click.option(
    "--no-edit",
    is_flag=True,
    help="Use the last commit subject and body as description, skips the editor",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Print a machine-readable JSON result on stdout (submit and list mode)",
)
def tea_review(
    target_branch: str | None,
    download: int | None,
    list: bool,
    wip: bool,
    ready: bool,
    title: str | None,
    message: str | None,
    message_file: str | None,
    no_edit: bool,
    json_output: bool,
) -> None:
    handle_review(
        backend="gitea",
        target_branch=target_branch,
        download=download,
        list=list,
        wip=wip,
        ready=ready,
        title=title,
        message=message,
        message_file=message_file,
        no_edit=no_edit,
        json_output=json_output,
    )


@click.command()
@click.argument("target_branch", required=False)
@click.option(
    "-d",
    "--download",
    type=int,
    metavar="MR_ID",
    help="Download and checkout a merge request by ID",
)
@click.option(
    "-l",
    "--list",
    is_flag=True,
    help="List open merge requests (optionally for TARGET_BRANCH)",
)
@click.option(
    "-w",
    "--wip",
    is_flag=True,
    help="Create merge request as draft (adds '[Draft]' prefix to title)",
)
@click.option(
    "-r",
    "--ready",
    is_flag=True,
    help="Create merge request as ready (removes '[Draft]' prefix to title)",
)
@click.option(
    "-t",
    "--title",
    metavar="TEXT",
    help="Merge request title (type/short-desc, e.g. feat/add-cli-desc), skips the prompt",
)
@click.option(
    "-m",
    "--message",
    metavar="TEXT",
    help="Merge request description, skips the editor",
)
@click.option(
    "-F",
    "--message-file",
    type=click.Path(dir_okay=False, allow_dash=True),
    help="Read the merge request description from a file ('-' for stdin)",
)
@click.option(
    "--no-edit",
    is_flag=True,
    help="Use the last commit subject and body as description, skips the editor",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Print a machine-readable JSON result on stdout (submit and list mode)",
)
def lab_review(
    target_branch: str | None,
    download: int | None,
    list: bool,
    wip: bool,
    ready: bool,
    title: str | None,
    message: str | None,
    message_file: str | None,
    no_edit: bool,
    json_output: bool,
) -> None:
    handle_review(
        backend="gitlab",
        target_branch=target_branch,
        download=download,
        list=list,
        wip=wip,
        ready=ready,
        title=title,
        message=message,
        message_file=message_file,
        no_edit=no_edit,
        json_output=json_output,
    )


def handle_review(
    backend: str,
    target_branch: str | None,
    download: int | None,
    list: bool,
    wip: bool,
    ready: bool,
    title: str | None = None,
    message: str | None = None,
    message_file: str | None = None,
    no_edit: bool = False,
    json_output: bool = False,
) -> None:
    try:
        description = _validate_review_args(
            target_branch=target_branch,
            download=download,
            list=list,
            wip=wip,
            ready=ready,
            title=title,
            message=message,
            message_file=message_file,
            no_edit=no_edit,
            json_output=json_output,
        )
    except click.UsageError as e:
        if json_output:
            emit_json({"error": e.format_message()})
        raise

    if download is not None:
        download_review(backend, download)
    elif list:
        list_reviews(backend, target_branch, json_output=json_output)
    else:
        run_review(
            backend,
            target_branch,
            wip,
            ready,
            title=title,
            description=description,
            no_edit=no_edit,
            json_output=json_output,
        )


def _validate_review_args(
    target_branch: str | None,
    download: int | None,
    list: bool,
    wip: bool,
    ready: bool,
    title: str | None,
    message: str | None,
    message_file: str | None,
    no_edit: bool,
    json_output: bool,
) -> str | None:
    """Enforce flag rules and return the description given by -m/-F, if any."""
    download_mode: bool = download is not None
    list_mode: bool = list
    submit_mode: bool = not download_mode and not list_mode

    if sum([download_mode, list_mode, submit_mode]) != 1:
        raise click.UsageError("You must use exactly one mode: submit, --download, or --list.")

    if download_mode and target_branch is not None:
        raise click.UsageError("--download cannot be used with TARGET_BRANCH")

    if wip and not submit_mode:
        raise click.UsageError("--wip can only be used in submit mode")

    if ready and not submit_mode:
        raise click.UsageError("--ready can only be used in submit mode")

    if ready and wip:
        raise click.UsageError("--ready and --wip are mutually exclusive flags")

    if json_output and download_mode:
        raise click.UsageError("--json can only be used in submit or list mode")

    description_sources = [
        name
        for name, given in (
            ("--message", message is not None),
            ("--message-file", message_file is not None),
            ("--no-edit", no_edit),
        )
        if given
    ]
    if len(description_sources) > 1:
        raise click.UsageError(f"{', '.join(description_sources)} are mutually exclusive flags")

    if not submit_mode:
        submit_only = (["--title"] if title is not None else []) + description_sources
        if submit_only:
            raise click.UsageError(f"{submit_only[0]} can only be used in submit mode")
        return None

    if title is not None:
        error = validate_pr_title(title)
        if error:
            raise click.UsageError(f"Invalid --title '{title}': {error}")

    if message_file is not None:
        try:
            message = read_message_file(message_file)
        except OSError as e:
            raise click.UsageError(f"Could not read --message-file '{message_file}': {e}") from e

    if message is not None:
        message = message.strip()
        if not message:
            raise click.UsageError("Empty description: refusing to submit an empty review")

    return message
