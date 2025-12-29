import sys
from typing import Optional

from git_nearit.clients.git_client import GitClient
from git_nearit.clients.gitea_client import GiteaClient
from git_nearit.clients.gitlab_client import GitLabClient
from git_nearit.utils import display_reviews_table, get_pr_description, get_pr_title, setup_logging


def run_review(
    platform: str, target_branch: Optional[str] = None, wip: bool = False, ready: bool = False
) -> None:
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

        target = target_branch or main_branch

        if target_branch:
            logger.info(f"Targeting branch: {target}")
        else:
            logger.info(f"Targeting default branch: {target}")

        if git_client.is_on_main_branch() or current_branch == target:
            if git_client.is_on_main_branch():
                logger.info(f"On main branch ({main_branch}), creating new change branch")
            else:
                logger.info(f"On target branch ({target}), creating new change branch")

            branch_name = git_client.create_change_branch()
            logger.info(f"Created branch: {branch_name}")

            current_to_reset = main_branch if git_client.is_on_main_branch() else target
            git_client.repo.git.checkout(current_to_reset)
            git_client.repo.git.reset("--hard", f"origin/{current_to_reset}")
            logger.info(f"Reset {current_to_reset} to origin/{current_to_reset}")

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

        if platform == "gitea":
            vcs_client = GiteaClient(git_client.repo)
        else:  # lab
            vcs_client = GitLabClient(git_client.repo)

        logger.info("Checking for existing review...")
        existing_review = vcs_client.check_existing_review(branch_name, target)

        if existing_review:
            logger.info(f"Review already exists: {existing_review.title}")
            logger.info(f"URL: {existing_review.url}")
            if not wip and not ready:
                return
            else:
                logger.info("Updating review state...")
                vcs_client.update_review_status(review=existing_review, draft=wip)
                logger.info("Review status updated successfully!")
                return

        logger.info("No existing review found, creating new one")

        title = get_pr_title()
        logger.info(f"Title: {title}")

        subject, body = git_client.get_last_commit_message()
        description = get_pr_description(subject, body)

        if wip:
            logger.info("Creating review as draft...")
        else:
            logger.info("Creating review as ready...")
        review = vcs_client.create_review(
            title=title,
            description=description,
            source_branch=branch_name,
            target_branch=target,
            draft=wip,
        )
        logger.info("Review created successfully!")
        logger.info(f"URL: {review.url}")

    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


def download_review(platform: str, pr_id: int) -> None:
    logger = setup_logging()

    try:
        git_client = GitClient()
        logger.info("Initialized git client")

        if git_client.has_uncommitted_changes():
            logger.error(
                "You have uncommitted changes to tracked files. "
                "Please commit or stash them before downloading a review."
            )
            logger.info("Note: Untracked files are fine and will be preserved.")
            sys.exit(1)

        if platform == "gitea":
            vcs_client = GiteaClient(git_client.repo)
        else:  # lab
            vcs_client = GitLabClient(git_client.repo)

        logger.info(f"Fetching pull request #{pr_id}...")
        pr = vcs_client.get_review(pr_id)

        if not pr.source_branch:
            logger.error(f"Could not determine branch name for PR #{pr_id}")
            sys.exit(1)

        logger.info(f"PR #{pr.number}: {pr.title}")
        logger.info(f"Branch: {pr.source_branch}")

        logger.info(f"Fetching and checking out branch {pr.source_branch}...")
        git_client.fetch_and_checkout_branch(pr.source_branch)
        logger.info(f"Successfully checked out branch: {pr.source_branch}")

    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


def list_reviews(platform: str, base_branch: Optional[str] = None) -> None:
    logger = setup_logging()

    try:
        git_client = GitClient()
        logger.info("Initialized git client")

        if base_branch is None or base_branch == "":
            base_branch = git_client.get_main_branch()
            logger.info(f"Listing reviews for default branch: {base_branch}")
        else:
            logger.info(f"Listing reviews for branch: {base_branch}")

        if platform == "gitea":
            vcs_client = GiteaClient(git_client.repo)
        else:  # lab
            vcs_client = GitLabClient(git_client.repo)

        reviews = vcs_client.list_reviews(base_branch)
        display_reviews_table(reviews, base_branch)

    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
