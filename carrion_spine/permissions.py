from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import discord
from discord import app_commands


@dataclass(slots=True, frozen=True)
class PermissionConfig:
    module_access_roles: tuple[int, ...]
    file_profile_roles: dict[str, tuple[int, ...]]


class PermissionService:
    """Role-based checks for module and profile-level access."""

    def __init__(self, config: PermissionConfig) -> None:
        self.config = config

    def has_module_access(self, member: discord.Member | discord.User) -> bool:
        if not isinstance(member, discord.Member):
            return False
        user_role_ids = {role.id for role in member.roles}
        return bool(user_role_ids.intersection(self.config.module_access_roles))

    def can_edit_profile(
        self,
        member: discord.Member | discord.User,
        profile_name: str | None,
    ) -> bool:
        if not isinstance(member, discord.Member):
            return False
        if not profile_name:
            return self.has_module_access(member)

        required_roles = self.config.file_profile_roles.get(profile_name, ())
        if not required_roles:
            return self.has_module_access(member)
        user_role_ids = {role.id for role in member.roles}
        return bool(user_role_ids.intersection(required_roles))


def require_module_access(permission_service: PermissionService):
    """Decorator-style app command guard."""

    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        if permission_service.has_module_access(member):
            return True
        raise app_commands.CheckFailure("You do not have Carrion: Spine module access.")

    return app_commands.check(predicate)

