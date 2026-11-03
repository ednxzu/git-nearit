import sys
from dataclasses import asdict

from git.exc import GitCommandError

from git_nearit.clients.base_vcs_client import BaseVCSClient
from git_nearit.clients.git_client import GitClient
from git_nearit.clients.gitea_client import GiteaClient
from git_nearit.clients.gitlab_client import GitLabClient
from git_nearit.models import Review
from git_nearit.utils import (
    commit_description,
    display_reviews_table,
    emit_json,
    get_pr_description,
    get_pr_title,
    is_interactive,
    setup_logging,
)


def _emit_error(message: str, json_output: bool) -> None:
    if json_output:
        emit_json({"error": message})


def _review_result(
    vcs_client: BaseVCSClient,
    review: Review,
    action: str,
    source_branch: str,
    target_branch: str,
) -> dict:
    return {
        "action": action,
        "number": review.number,
        "url": review.url,
        "title": vcs_client.strip_draft_prefix(review.title),
        "draft": vcs_client.is_draft_title(review.title),
        "source_branch": source_branch,
        "target_branch": target_branch,
    }


def _last_commit_description(git_client: GitClient) -> str:
    subject, body = git_client.get_last_commit_message()
    description = commit_description(subject, body)
    if not description:
        raise ValueError("Empty description: the last commit has no message")
    return description


def _require_create_options(
    title: str | None, description: str | None, no_edit: bool, json_output: bool
) -> None:
    """Without a TTY (or with --json), creating a review needs title and description flags."""
    if is_interactive(json_output):
        return
    missing = []
    if title is None:
        missing.append("--title")
    if description is None and not no_edit:
        missing.append("--message, --message-file or --no-edit")
    if missing:
        raise ValueError(
            f"missing {' and '.join(missing)}; required when not running interactively"
        )


def run_review(
    platform: str,
    target_branch: str | None = None,
    wip: bool = False,
    ready: bool = False,
    title: str | None = None,
    description: str | None = None,
    no_edit: bool = False,
    json_output: bool = False,
) -> None:
    logger = setup_logging(json_output=json_output)

    try:
        git_client = GitClient()
        logger.info("Initialized git client")

        if git_client.has_uncommitted_changes():
            message = (
                "You have uncommitted changes to tracked files. "
                "Please commit or stash them before running review."
            )
            logger.error(message)
            logger.info("Note: Untracked files are fine and will be preserved.")
            _emit_error(message, json_output)
            sys.exit(1)

        main_branch = git_client.get_main_branch()
        current_branch = git_client.get_current_branch()

        target = target_branch or main_branch

        if target_branch:
            logger.info(f"Targeting branch: {target}")
        else:
            logger.info(f"Targeting default branch: {target}")

        vcs_client: BaseVCSClient
        if platform == "gitea":
            vcs_client = GiteaClient(git_client.repo)
        else:  # lab
            vcs_client = GitLabClient(git_client.repo)

        # None keeps the current draft state of an existing review
        draft: bool | None = True if wip else (False if ready else None)

        # Missing options must be reported before anything is created, reset or pushed
        new_branch = git_client.is_on_main_branch() or current_branch == target
        existing_review: Review | None = None
        review_checked = False

        if new_branch:
            # A fresh change branch cannot have a review yet
            _require_create_options(title, description, no_edit, json_output)

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
        else:
            if current_branch.startswith("change/"):
                logger.info(f"Already on change branch: {current_branch}")
            else:
                logger.warning(f"On non-standard branch: {current_branch} (continuing anyway)")
            branch_name = current_branch

            logger.info("Checking for existing review...")
            existing_review = vcs_client.check_existing_review(branch_name, target)
            review_checked = True
            if not existing_review:
                _require_create_options(title, description, no_edit, json_output)

        logger.info(f"Pushing branch {branch_name}...")
        try:
            git_client.push_branch(branch_name)
            logger.info("Branch pushed successfully")
        except GitCommandError as e:
            message = f"Push failed: {e}"
            logger.error(message)
            _emit_error(message, json_output)
            sys.exit(1)

        if not review_checked:
            logger.info("Checking for existing review...")
            existing_review = vcs_client.check_existing_review(branch_name, target)

        if existing_review:
            logger.info(f"Review already exists: {existing_review.title}")
            logger.info(f"URL: {existing_review.url}")

            # Content is only updated on explicit flags, never prompted for
            if description is None and no_edit:
                description = _last_commit_description(git_client)

            if title is None and description is None and draft is None:
                if json_output:
                    emit_json(
                        _review_result(
                            vcs_client, existing_review, "unchanged", branch_name, target
                        )
                    )
                return

            logger.info("Updating review...")
            review = vcs_client.update_review(
                review=existing_review, title=title, description=description, draft=draft
            )

            if review is existing_review:
                action = "unchanged"
                logger.info("Review already up to date, nothing to change")
            else:
                action = "updated"
                if title is not None:
                    logger.info(f"Title replaced: {review.title}")
                if description is not None:
                    logger.info("Description replaced")
                if draft is not None:
                    logger.info("Review status updated successfully!")

            if json_output:
                emit_json(_review_result(vcs_client, review, action, branch_name, target))
            return

        logger.info("No existing review found, creating new one")

        if title is None:
            title = get_pr_title()
        logger.info(f"Title: {title}")

        if description is None:
            if no_edit:
                description = _last_commit_description(git_client)
            else:
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

        if json_output:
            emit_json(_review_result(vcs_client, review, "created", branch_name, target))

    except ValueError as e:
        logger.error(str(e))
        _emit_error(str(e), json_output)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error")
        _emit_error(f"Unexpected error: {e}", json_output)
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
    except Exception:
        logger.exception("Unexpected error")
        sys.exit(1)


def list_reviews(platform: str, base_branch: str | None = None, json_output: bool = False) -> None:
    logger = setup_logging(json_output=json_output)

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
        if json_output:
            emit_json([asdict(review) for review in reviews])
        else:
            display_reviews_table(reviews, base_branch)

    except ValueError as e:
        logger.error(str(e))
        _emit_error(str(e), json_output)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error")
        _emit_error(f"Unexpected error: {e}", json_output)
        sys.exit(1)
