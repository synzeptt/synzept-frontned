from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.connected_app import ConnectedAppAccount, GitHubCommit, GitHubIssue, GitHubPullRequest, GitHubRelease, GitHubRepository
from app.models.learning import LearningObservation
from app.models.user import User
from app.services.connected_apps.connected_app_action_service import ConnectedAppActionPreparationService
from app.services.connected_apps.oauth_lifecycle import ConnectedAppOAuthLifecycle

PROVIDER = "github"
AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
API_URL = "https://api.github.com"
GRAPHQL_URL = f"{API_URL}/graphql"
logger = logging.getLogger(__name__)

REPOSITORY_QUERY = """
query SynzeptRepositories($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on Repository {
      id databaseId nameWithOwner visibility isArchived updatedAt pushedAt
      defaultBranchRef {
        name
        target { ... on Commit { history(first: 50) { nodes { oid messageHeadline committedDate author { user { login } } } } } }
      }
      refs(refPrefix: "refs/heads/", first: 50) { nodes { name target { ... on Commit { oid committedDate } } } }
      issues(first: 50, orderBy: {field: UPDATED_AT, direction: DESC}) {
        nodes { number title state createdAt updatedAt closedAt milestone { dueOn } labels(first: 20) { nodes { name } } assignees(first: 10) { nodes { login } } }
      }
      pullRequests(first: 50, orderBy: {field: UPDATED_AT, direction: DESC}) {
        nodes { number title state isDraft merged mergedAt createdAt updatedAt closedAt reviewDecision reviews(first: 20) { totalCount nodes { state } } reviewRequests(first: 10) { totalCount } }
      }
      releases(first: 10, orderBy: {field: CREATED_AT, direction: DESC}) {
        nodes { id databaseId name tagName isDraft isPrerelease publishedAt }
      }
    }
  }
}
"""


@dataclass
class GitHubSyncResult:
    synced: int = 0
    updated: int = 0
    cancelled: int = 0
    observations: int = 0
    status: str = "connected"


class GitHubService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.oauth = ConnectedAppOAuthLifecycle(session)

    async def status(self, user_id: UUID) -> dict:
        return self._status_out(await self.oauth.account(user_id, PROVIDER))

    async def authorization_url(self, user: User) -> dict:
        self._require_config()
        account = await self.oauth.ensure_account(user.id, PROVIDER, ["github_app_installation:read-only"])
        account.status = "connecting"
        account.last_error_code = None
        account.last_error_message = None
        state = self._encode_state(user.id)
        params = {"client_id": self.settings.github_client_id, "redirect_uri": self._redirect_uri(), "state": state, "allow_signup": "true"}
        return {"authorizationUrl": f"{AUTHORIZE_URL}?{urlencode(params)}"}

    async def handle_callback(self, code: str | None, state: str | None, error: str | None, expected_user_id: UUID | None = None) -> str:
        frontend = self.settings.frontend_url.rstrip("/")
        user_id = self._decode_state(state or "")
        if expected_user_id is not None and user_id != expected_user_id:
            raise AppError("Invalid GitHub OAuth state", status_code=400, code="invalid_oauth_state")
        account = await self.oauth.ensure_account(user_id, PROVIDER, ["github_app_installation:read-only"])
        if error:
            await self._set_error(account, "oauth_cancelled", "GitHub connection was cancelled.")
            return f"{frontend}/connected-apps?github=cancelled"
        if not code:
            await self._set_error(account, "oauth_missing_code", "GitHub did not return an authorization code.")
            return f"{frontend}/connected-apps?github=error"
        try:
            tokens = await self._exchange_code(code)
            access = str(tokens.get("access_token") or "")
            if not access:
                raise AppError("GitHub did not return an access token", status_code=400, code="missing_access_token")
            account.encrypted_access_token = self.oauth.encrypt(access)
            refresh = tokens.get("refresh_token")
            account.encrypted_refresh_token = self.oauth.encrypt(str(refresh)) if refresh else None
            expires_in = int(tokens.get("expires_in") or 28_800)
            account.access_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(60, expires_in - 60))
            account.scopes = ["github_app_installation:read-only"]
            await self._load_profile(account, access)
            account.status = "connected"
            account.last_error_code = None
            account.last_error_message = None
            await self.session.flush()
            await self.sync(user_id)
            return f"{frontend}/connected-apps?github=connected"
        except AppError as exc:
            await self._set_error(account, exc.code or "oauth_exchange_failed", exc.user_message or "GitHub could not connect.")
            return f"{frontend}/connected-apps?github=error"

    async def sync(self, user_id: UUID) -> GitHubSyncResult:
        account = await self.oauth.required_account(user_id, PROVIDER)
        if not account.encrypted_access_token and not account.encrypted_refresh_token:
            await self._set_error(account, "permission_revoked", "GitHub needs to be reconnected.", "permission_revoked")
            return GitHubSyncResult(status="permission_revoked")
        account.status = "syncing"
        await self.session.flush()
        try:
            access = await self._access_token(account)
            result = await self._sync_engineering(account, access)
            result.observations = await self._create_observations(account)
            if result.observations:
                await ConnectedAppActionPreparationService(self.session).prepare_for_provider(
                    user_id=account.user_id,
                    provider=PROVIDER,
                    observations_created=result.observations,
                    account_metadata=account.app_metadata,
                )
            account.status = "connected"
            account.last_synced_at = datetime.now(timezone.utc)
            account.last_error_code = None
            account.last_error_message = None
            await self.session.flush()
            return result
        except AppError as exc:
            status = "permission_revoked" if exc.code in {"permission_revoked", "token_expired"} else "error"
            await self._set_error(account, exc.code or "sync_failed", exc.user_message or "GitHub sync failed.", status)
            return GitHubSyncResult(status=status)

    async def disconnect(self, user_id: UUID) -> dict:
        account = await self.oauth.required_account(user_id, PROVIDER)
        access = self.oauth.try_decrypt(account.encrypted_access_token)
        if access:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.delete(
                        f"{API_URL}/applications/{self.settings.github_client_id}/token",
                        auth=(self.settings.github_client_id, self.settings.github_client_secret),
                        json={"access_token": access},
                        headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
                    )
            except Exception:
                logger.warning("GitHub remote token revocation did not complete user_id=%s", user_id)
        self.oauth.clear_tokens(account)
        await self.session.flush()
        return self._status_out(account)

    async def sync_if_due(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        accounts = list((await self.session.execute(select(ConnectedAppAccount).where(ConnectedAppAccount.provider == PROVIDER, ConnectedAppAccount.status.in_(("connected", "error"))))).scalars())
        synced = 0
        for account in accounts:
            last_sync = self._aware(account.last_synced_at) if account.last_synced_at else None
            if last_sync and last_sync >= cutoff:
                continue
            try:
                result = await self.sync(account.user_id)
                synced += int(result.status == "connected")
            except Exception:
                logger.exception("Scheduled GitHub sync failed user_id=%s", account.user_id)
        return synced

    async def _sync_engineering(self, account: ConnectedAppAccount, access: str) -> GitHubSyncResult:
        metadata = account.app_metadata or {}
        raw_repositories, repository_etag, not_modified = await self._repository_catalog(access, metadata.get("repositories_etag"))
        if not_modified:
            return GitHubSyncResult()
        existing_repositories = {row.provider_repository_id: row for row in (await self.session.execute(select(GitHubRepository).where(GitHubRepository.user_id == account.user_id))).scalars()}
        result = GitHubSyncResult()
        watermark = self._datetime(metadata.get("github_watermark"))
        changed_node_ids: list[str] = []
        for raw in raw_repositories:
            provider_id = str(raw.get("id") or "")
            node_id = str(raw.get("node_id") or "")
            if not provider_id or not node_id:
                continue
            repository = existing_repositories.get(provider_id)
            created = repository is None
            if repository is None:
                repository = GitHubRepository(user_id=account.user_id, connected_account_id=account.id, provider_repository_id=provider_id)
                self.session.add(repository)
                existing_repositories[provider_id] = repository
            repository.node_id = node_id
            repository.full_name = str(raw.get("full_name") or "")[:500]
            repository.visibility = str(raw.get("visibility") or ("private" if raw.get("private") else "public"))[:40]
            repository.default_branch = str(raw.get("default_branch") or "")[:300]
            repository.last_activity_at = self._datetime(raw.get("pushed_at") or raw.get("updated_at"))
            repository.archived = bool(raw.get("archived"))
            repository.repository_metadata = {**(repository.repository_metadata or {}), "language": raw.get("language"), "topics": raw.get("topics") or []}
            updated_at = self._datetime(raw.get("updated_at"))
            if created or not watermark or (updated_at and updated_at > watermark):
                changed_node_ids.append(node_id)
            result.synced += int(created)
            result.updated += int(not created)
        await self.session.flush()

        for start in range(0, len(changed_node_ids), 10):
            nodes = await self._repository_nodes(changed_node_ids[start : start + 10], access)
            for node in nodes:
                repository = next((row for row in existing_repositories.values() if row.node_id == str(node.get("id") or "")), None)
                if repository:
                    created, updated = await self._upsert_repository_details(account, repository, node)
                    result.synced += created
                    result.updated += updated

        now = datetime.now(timezone.utc)
        repositories = list(existing_repositories.values())
        open_issues = list((await self.session.execute(select(GitHubIssue).where(GitHubIssue.user_id == account.user_id, GitHubIssue.state == "OPEN"))).scalars())
        open_prs = list((await self.session.execute(select(GitHubPullRequest).where(GitHubPullRequest.user_id == account.user_id, GitHubPullRequest.state == "OPEN"))).scalars())
        commits = list((await self.session.execute(select(GitHubCommit).where(GitHubCommit.user_id == account.user_id))).scalars())
        account.app_metadata = {
            **metadata,
            "repositories_etag": repository_etag or metadata.get("repositories_etag"),
            "github_watermark": now.isoformat(),
            "repositories_count": len(repositories),
            "active_repositories_count": sum(1 for repo in repositories if repo.last_activity_at and self._aware(repo.last_activity_at) >= now - timedelta(days=14) and not repo.archived),
            "open_issues_count": len(open_issues),
            "open_pull_requests_count": len(open_prs),
            "recent_commits_count": sum(1 for commit in commits if commit.committed_at and self._aware(commit.committed_at) >= now - timedelta(days=30)),
            "repository_names": [repo.full_name for repo in sorted(repositories, key=lambda repo: self._aware(repo.last_activity_at or datetime.min), reverse=True)[:10]],
        }
        return result

    async def _repository_catalog(self, access: str, etag: Any) -> tuple[list[dict[str, Any]], str | None, bool]:
        headers = self._headers(access)
        if etag:
            headers["If-None-Match"] = str(etag)
        url: str | None = f"{API_URL}/user/repos"
        params: dict[str, Any] | None = {"affiliation": "owner,collaborator,organization_member", "sort": "pushed", "direction": "desc", "per_page": 100}
        repositories: list[dict[str, Any]] = []
        first_etag: str | None = None
        async with httpx.AsyncClient(timeout=25) as client:
            while url:
                response = await client.get(url, params=params, headers=headers)
                if response.status_code == 304:
                    return [], str(etag) if etag else None, True
                self._raise_github(response)
                first_etag = first_etag or response.headers.get("ETag")
                repositories.extend(response.json())
                url = self._next_link(response.headers.get("Link"))
                params = None
                headers.pop("If-None-Match", None)
        return repositories, first_etag, False

    async def _repository_nodes(self, node_ids: list[str], access: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(GRAPHQL_URL, json={"query": REPOSITORY_QUERY, "variables": {"ids": node_ids}}, headers=self._headers(access))
        self._raise_github(response)
        payload = response.json()
        if payload.get("errors"):
            raise AppError("GitHub GraphQL sync failed", status_code=400, code="sync_failed", user_message="GitHub repository details could not be synchronized.")
        return [node for node in (payload.get("data") or {}).get("nodes") or [] if node]

    async def _upsert_repository_details(self, account: ConnectedAppAccount, repository: GitHubRepository, raw: dict[str, Any]) -> tuple[int, int]:
        repository.default_branch = str(((raw.get("defaultBranchRef") or {}).get("name") or repository.default_branch))[:300]
        repository.visibility = str(raw.get("visibility") or repository.visibility).lower()[:40]
        repository.archived = bool(raw.get("isArchived", repository.archived))
        repository.last_activity_at = self._datetime(raw.get("pushedAt") or raw.get("updatedAt")) or repository.last_activity_at
        branches = []
        for branch in ((raw.get("refs") or {}).get("nodes") or []):
            target = branch.get("target") or {}
            branches.append({"name": str(branch.get("name") or "")[:300], "sha": target.get("oid"), "committedAt": target.get("committedDate")})
        repository.repository_metadata = {**(repository.repository_metadata or {}), "branches": branches}
        created = updated = 0

        issues = {(row.number): row for row in (await self.session.execute(select(GitHubIssue).where(GitHubIssue.repository_id == repository.id))).scalars()}
        for raw_issue in ((raw.get("issues") or {}).get("nodes") or []):
            number = int(raw_issue.get("number") or 0)
            if not number:
                continue
            issue = issues.get(number)
            is_new = issue is None
            if issue is None:
                issue = GitHubIssue(user_id=account.user_id, repository_id=repository.id, number=number)
                self.session.add(issue)
                issues[number] = issue
            issue.title = str(raw_issue.get("title") or "")[:500]
            issue.state = str(raw_issue.get("state") or "OPEN")[:40]
            issue.labels = [str(item.get("name") or "")[:120] for item in ((raw_issue.get("labels") or {}).get("nodes") or []) if item.get("name")]
            issue.assignees = [str(item.get("login") or "")[:200] for item in ((raw_issue.get("assignees") or {}).get("nodes") or []) if item.get("login")]
            issue.due_at = self._datetime((raw_issue.get("milestone") or {}).get("dueOn"))
            issue.provider_created_at = self._datetime(raw_issue.get("createdAt"))
            issue.provider_updated_at = self._datetime(raw_issue.get("updatedAt"))
            issue.closed_at = self._datetime(raw_issue.get("closedAt"))
            created += int(is_new)
            updated += int(not is_new)

        pulls = {row.number: row for row in (await self.session.execute(select(GitHubPullRequest).where(GitHubPullRequest.repository_id == repository.id))).scalars()}
        for raw_pr in ((raw.get("pullRequests") or {}).get("nodes") or []):
            number = int(raw_pr.get("number") or 0)
            if not number:
                continue
            pull = pulls.get(number)
            is_new = pull is None
            if pull is None:
                pull = GitHubPullRequest(user_id=account.user_id, repository_id=repository.id, number=number)
                self.session.add(pull)
                pulls[number] = pull
            review_states = [str(item.get("state") or "") for item in ((raw_pr.get("reviews") or {}).get("nodes") or [])]
            pull.title = str(raw_pr.get("title") or "")[:500]
            pull.state = str(raw_pr.get("state") or "OPEN")[:40]
            pull.draft = bool(raw_pr.get("isDraft"))
            pull.merged = bool(raw_pr.get("merged"))
            pull.review_count = int((raw_pr.get("reviews") or {}).get("totalCount") or len(review_states))
            pull.review_status = self._review_status(raw_pr.get("reviewDecision"), review_states, int((raw_pr.get("reviewRequests") or {}).get("totalCount") or 0))
            pull.provider_created_at = self._datetime(raw_pr.get("createdAt"))
            pull.provider_updated_at = self._datetime(raw_pr.get("updatedAt"))
            pull.merged_at = self._datetime(raw_pr.get("mergedAt"))
            pull.closed_at = self._datetime(raw_pr.get("closedAt"))
            created += int(is_new)
            updated += int(not is_new)

        commits = {row.sha: row for row in (await self.session.execute(select(GitHubCommit).where(GitHubCommit.repository_id == repository.id))).scalars()}
        history = ((((raw.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}).get("nodes") or [])
        for raw_commit in history:
            sha = str(raw_commit.get("oid") or "")
            if not sha:
                continue
            commit = commits.get(sha)
            is_new = commit is None
            if commit is None:
                commit = GitHubCommit(user_id=account.user_id, repository_id=repository.id, sha=sha)
                self.session.add(commit)
                commits[sha] = commit
            commit.message = str(raw_commit.get("messageHeadline") or "")[:500]
            commit.author_login = str((((raw_commit.get("author") or {}).get("user") or {}).get("login") or ""))[:200]
            commit.committed_at = self._datetime(raw_commit.get("committedDate"))
            created += int(is_new)
            updated += int(not is_new)

        releases = {row.provider_release_id: row for row in (await self.session.execute(select(GitHubRelease).where(GitHubRelease.repository_id == repository.id))).scalars()}
        for raw_release in ((raw.get("releases") or {}).get("nodes") or []):
            provider_id = str(raw_release.get("databaseId") or raw_release.get("id") or "")
            if not provider_id:
                continue
            release = releases.get(provider_id)
            is_new = release is None
            if release is None:
                release = GitHubRelease(user_id=account.user_id, repository_id=repository.id, provider_release_id=provider_id)
                self.session.add(release)
                releases[provider_id] = release
            release.name = str(raw_release.get("name") or "")[:500]
            release.tag_name = str(raw_release.get("tagName") or "")[:300]
            release.draft = bool(raw_release.get("isDraft"))
            release.prerelease = bool(raw_release.get("isPrerelease"))
            release.published_at = self._datetime(raw_release.get("publishedAt"))
            created += int(is_new)
            updated += int(not is_new)
        await self.session.flush()
        return created, updated

    async def _create_observations(self, account: ConnectedAppAccount) -> int:
        now = datetime.now(timezone.utc)
        repositories = list((await self.session.execute(select(GitHubRepository).where(GitHubRepository.user_id == account.user_id))).scalars())
        pulls = list((await self.session.execute(select(GitHubPullRequest).where(GitHubPullRequest.user_id == account.user_id))).scalars())
        issues = list((await self.session.execute(select(GitHubIssue).where(GitHubIssue.user_id == account.user_id))).scalars())
        observations = []
        for repository in repositories:
            repo_pulls = [pull for pull in pulls if pull.repository_id == repository.id]
            repo_issues = [issue for issue in issues if issue.repository_id == repository.id]
            if repository.last_activity_at and self._aware(repository.last_activity_at) >= now - timedelta(days=14):
                observations.append(f"GitHub evidence: {repository.full_name} is an active engineering repository.")
            if repository.last_activity_at and self._aware(repository.last_activity_at) < now - timedelta(days=30) and any(item.state == "OPEN" for item in [*repo_pulls, *repo_issues]):
                observations.append(f"GitHub evidence: {repository.full_name} has open engineering work but no repository activity for over 30 days.")
            long_running = sum(1 for pull in repo_pulls if pull.state == "OPEN" and pull.provider_created_at and self._aware(pull.provider_created_at) < now - timedelta(days=14))
            if long_running:
                observations.append(f"GitHub evidence: {repository.full_name} has {long_running} pull request{'s' if long_running != 1 else ''} open for over 14 days.")
            reviews = sum(pull.review_count for pull in repo_pulls if pull.provider_updated_at and self._aware(pull.provider_updated_at) >= now - timedelta(days=30))
            if reviews >= 5:
                observations.append(f"GitHub evidence: {repository.full_name} has frequent pull-request review activity ({reviews} reviews in recent synced data).")
        workload = sum(1 for issue in issues if issue.state == "OPEN") + sum(1 for pull in pulls if pull.state == "OPEN")
        if workload >= 10:
            observations.append(f"GitHub evidence: {workload} open issues and pull requests indicate a high visible engineering workload.")
        existing = {row.content for row in (await self.session.execute(select(LearningObservation).where(LearningObservation.user_id == account.user_id, LearningObservation.source == PROVIDER))).scalars()}
        created = 0
        for content in observations:
            if content not in existing:
                self.session.add(LearningObservation(user_id=account.user_id, source=PROVIDER, content=content, status="observed"))
                created += 1
        await self.session.flush()
        return created

    async def _access_token(self, account: ConnectedAppAccount) -> str:
        if account.encrypted_refresh_token:
            return await self.oauth.access_token(account, label="GitHub", token_url=TOKEN_URL, client_id=self.settings.github_client_id, client_secret=self.settings.github_client_secret, headers={"Accept": "application/json"})
        if account.encrypted_access_token:
            return self.oauth.decrypt(account.encrypted_access_token)
        raise AppError("GitHub authorization expired", status_code=409, code="token_expired", user_message="Reconnect GitHub to continue syncing.")

    async def _exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(TOKEN_URL, data={"client_id": self.settings.github_client_id, "client_secret": self.settings.github_client_secret, "code": code, "redirect_uri": self._redirect_uri()}, headers={"Accept": "application/json"})
        if response.status_code >= 400:
            raise AppError("GitHub OAuth exchange failed", status_code=400, code="oauth_exchange_failed", user_message="GitHub could not complete authorization.")
        payload = response.json()
        if payload.get("error"):
            raise AppError("GitHub OAuth exchange failed", status_code=400, code="oauth_exchange_failed", user_message="GitHub could not complete authorization.")
        return payload

    async def _load_profile(self, account: ConnectedAppAccount, access: str) -> None:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{API_URL}/user", headers=self._headers(access))
        self._raise_github(response)
        payload = response.json()
        account.provider_account_id = str(payload.get("id") or "")[:240] or None
        account.app_metadata = {**(account.app_metadata or {}), "account_login": str(payload.get("login") or "")[:200], "account_name": str(payload.get("name") or "")[:300]}

    async def _set_error(self, account: ConnectedAppAccount, code: str, message: str, status: str = "error") -> None:
        account.status = status
        account.last_error_code = code
        account.last_error_message = message
        await self.session.flush()

    def _status_out(self, account: ConnectedAppAccount | None) -> dict:
        status = account.status if account else "not_connected"
        return {"provider": PROVIDER, "status": status, "connected": status == "connected", "lastSyncedAt": account.last_synced_at if account else None, "lastErrorCode": account.last_error_code if account else None, "lastErrorMessage": account.last_error_message if account else None, "permissions": ["Read repository metadata, issues, pull requests, commits, branches, and releases"] if account else [], "scopes": account.scopes if account else [], "privacy": {"why": "GitHub helps Synzept understand engineering progress, momentum, review load, and stalled work.", "reads": "Repository metadata, visibility, branches, issues, pull requests, reviews, recent commits, and releases.", "usage": "Engineering evidence becomes an observation and requires approval before changing understanding.", "ignored": "Synzept does not read source file contents and cannot push commits, merge pull requests, create issues, or modify repositories."}}

    def _encode_state(self, user_id: UUID) -> str:
        return jwt.encode({"sub": str(user_id), "provider": PROVIDER, "nonce": secrets.token_urlsafe(12), "exp": datetime.now(timezone.utc) + timedelta(minutes=15), "type": "github_oauth_state"}, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm)

    def _decode_state(self, state: str) -> UUID:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret_key, algorithms=[self.settings.jwt_algorithm])
            if payload.get("type") != "github_oauth_state" or payload.get("provider") != PROVIDER:
                raise ValueError
            return UUID(str(payload["sub"]))
        except (JWTError, ValueError, KeyError) as exc:
            raise AppError("Invalid GitHub OAuth state", status_code=400, code="invalid_oauth_state") from exc

    def _require_config(self) -> None:
        if not self.settings.github_client_id or not self.settings.github_client_secret:
            raise AppError("GitHub is not configured", status_code=503, code="github_not_configured", user_message="GitHub is not configured for this Synzept environment yet.")

    def _redirect_uri(self) -> str:
        return self.settings.github_redirect_uri or f"{self.settings.frontend_url.rstrip('/').replace('localhost:3000', 'localhost:8000')}/api/connected-apps/github/callback"

    @staticmethod
    def _headers(access: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {access}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    @staticmethod
    def _next_link(value: str | None) -> str | None:
        for item in (value or "").split(","):
            parts = item.strip().split(";")
            if len(parts) > 1 and 'rel="next"' in parts[1]:
                return parts[0].strip().strip("<>")
        return None

    @staticmethod
    def _raise_github(response: httpx.Response) -> None:
        if response.status_code == 401:
            raise AppError("GitHub permission expired", status_code=409, code="permission_revoked", user_message="GitHub authorization expired. Reconnect to continue.")
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            raise AppError("GitHub rate limit reached", status_code=429, code="github_rate_limited", user_message="GitHub asked Synzept to slow down. Sync again after the rate limit resets.")
        if response.status_code == 403:
            raise AppError("GitHub read permission denied", status_code=403, code="github_permission_denied", user_message="The GitHub App does not have the required read permission for this repository.")
        if response.status_code >= 500:
            raise AppError("GitHub unavailable", status_code=503, code="github_unavailable", user_message="GitHub is unavailable right now.")
        if response.status_code >= 400:
            raise AppError("GitHub sync failed", status_code=400, code="sync_failed", user_message="GitHub sync failed.")

    @staticmethod
    def _review_status(decision: Any, states: list[str], requested: int) -> str:
        if str(decision or "") == "CHANGES_REQUESTED" or "CHANGES_REQUESTED" in states:
            return "changes_requested"
        if str(decision or "") == "APPROVED" or "APPROVED" in states:
            return "approved"
        if requested:
            return "review_requested"
        return "review_required"

    @staticmethod
    def _datetime(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
