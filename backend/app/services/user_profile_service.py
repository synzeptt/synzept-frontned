"""User intelligence profile CRUD."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_profile import UserProfile


class UserProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, user_id: UUID) -> UserProfile:
        result = await self.session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if profile:
            return profile
        user = await self.session.get(User, user_id)
        profile = UserProfile(
            user_id=user_id,
            display_name=user.display_name if user else None,
            avatar_url=user.avatar_url if user else None,
            onboarding_completed=False,
            communication_style="balanced",
            timezone=user.timezone if user else "UTC",
            profile_metadata={},
        )
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def ensure_for_user(self, user: User) -> UserProfile:
        return await self.get_or_create(user.id)

    async def update_avatar(self, user: User, avatar_url: str | None) -> UserProfile:
        cleaned = avatar_url.strip() if avatar_url else None
        user.avatar_url = cleaned
        profile = await self.get_or_create(user.id)
        profile.avatar_url = cleaned
        return profile

    def format_for_context(self, profile: UserProfile | None, user: User | None) -> str:
        """Build a concise profile block for prompt assembly."""
        parts: list[str] = []
        if user and user.display_name:
            parts.append(f"Name: {user.display_name}")
        if user and user.profile_summary:
            parts.append(user.profile_summary)
        if not profile:
            return "\n".join(parts)

        if profile.summary:
            parts.append(profile.summary)
        if profile.goals:
            parts.append("Goals: " + "; ".join(str(g) for g in profile.goals[:5]))
        if profile.productivity_style:
            parts.append(f"Productivity style: {profile.productivity_style}")
        comm = profile.communication_preferences or {}
        if comm.get("style"):
            parts.append(f"Communication: {comm['style']}")
        if comm.get("response_depth"):
            parts.append(f"Preferred depth: {comm['response_depth']}")
        return "\n".join(parts)
