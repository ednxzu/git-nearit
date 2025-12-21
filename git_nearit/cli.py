import sys

import typer

from git_nearit.clients.git_client import GitClient
from git_nearit.clients.gitea_client import GiteaClient
from git_nearit.clients.gitlab_client import GitLabClient
from git_nearit.utils import get_pr_description, get_pr_title, setup_logging

app = typer.Typer()


def run_review(platform: str) -> None:
    logger = setup_logging()

    try:
        git_client = GitClient()
        logger.info("Initialized git client")

        if git_client.has_uncommitted_changes():
            logger.error(
                "You have uncommitted changes to tracked files. "
                "Please commit or stash them before running review."
            )
            logger.info("Note: Untracked files are fine and will be preserved.")
            sys.exit(1)

        main_branch = git_client.get_main_branch()
        current_branch = git_client.get_current_branch()

        if git_client.is_on_main_branch():
            logger.info(f"On main branch ({main_branch}), creating new change branch")

            branch_name = git_client.create_change_branch()
            logger.info(f"Created branch: {branch_name}")

            git_client.reset_main_to_origin()
            logger.info(f"Reset {main_branch} to origin/{main_branch}")

            git_client.repo.git.checkout(branch_name)
        elif current_branch.startswith("change/"):
            logger.info(f"Already on change branch: {current_branch}")
            branch_name = current_branch
        else:
            logger.warning(f"On non-standard branch: {current_branch} (continuing anyway)")
            branch_name = current_branch

        logger.info(f"Pushing branch {branch_name}...")
        try:
            git_client.push_branch(branch_name)
            logger.info("Branch pushed successfully")
        except Exception as e:
            logger.error(f"Push failed: {e}")
            sys.exit(1)

        if platform == "tea":
            vcs_client = GiteaClient(git_client.repo)
        else:  # lab
            vcs_client = GitLabClient(git_client.repo)

        logger.info("Checking for existing pull/merge request...")
        existing_pr = vcs_client.check_existing_pr(branch_name, main_branch)

        if existing_pr:
            logger.info(f"Pull/Merge request already exists: {existing_pr.title}")
            logger.info(f"URL: {existing_pr.url}")
            return

        logger.info("No existing pull/merge request found, creating new one")

        title = get_pr_title()
        logger.info(f"Title: {title}")

        subject, body = git_client.get_last_commit_message()
        description = get_pr_description(subject, body)

        logger.info("Creating pull/merge request...")
        pr = vcs_client.create_pr(title, description, branch_name, main_branch)
        logger.info("Pull/Merge request created successfully!")
        logger.info(f"URL: {pr.url}")

    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


def tea_review() -> None:
    """Entry point for git-tea-review command."""
    run_review("tea")


def lab_review() -> None:
    """Entry point for git-lab-review command."""
    run_review("lab")


if __name__ == "__main__":
    app()
