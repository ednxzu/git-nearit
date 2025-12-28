from typing import Optional

import click

from git_nearit.cli import download_review, list_reviews, run_review


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
def tea_review(
    target_branch: Optional[str],
    download: Optional[int],
    list: bool,
    wip: bool,
) -> None:
    handle_review(
        backend="gitea", target_branch=target_branch, download=download, list=list, wip=wip
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
def lab_review(
    target_branch: Optional[str],
    download: Optional[int],
    list: bool,
    wip: bool,
) -> None:
    handle_review(
        backend="gitlab", target_branch=target_branch, download=download, list=list, wip=wip
    )


def handle_review(
    backend: str,
    target_branch: Optional[str],
    download: Optional[int],
    list: bool,
    wip: bool,
) -> None:
    download_mode: bool = download is not None
    list_mode: bool = list
    submit_mode: bool = not download_mode and not list_mode

    if sum([download_mode, list_mode, submit_mode]) != 1:
        raise click.UsageError("You must use exactly one mode: submit, --download, or --list.")

    if download_mode and target_branch is not None:
        raise click.UsageError("--download cannot be used with TARGET_BRANCH")

    if wip and not submit_mode:
        raise click.UsageError("--wip can only be used in submit mode")

    if download_mode and isinstance(download, int):
        download_review(backend, download)
    elif list_mode:
        list_reviews(backend, target_branch)
    else:
        run_review(backend, target_branch, wip)
