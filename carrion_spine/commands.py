from __future__ import annotations

import asyncio
import io
from datetime import UTC, datetime
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from .apply import apply_edit
from .config import CarrionSpineSettings
from .database import ConfigRecord, Database
from .diffing import generate_unified_diff, write_diff_attachment
from .discovery import SUPPORTED_EXTENSIONS, ConfigRoot, scan_configs
from .permissions import PermissionConfig, PermissionService
from .sessions import SessionManager
from .validation import ValidationService


class EditDecisionView(discord.ui.View):
    """Apply/Cancel controls shown after validation + diff preview."""

    def __init__(self, cog: "CarrionSpineConfigCog", session_id: str, owner_user_id: int) -> None:
        super().__init__(timeout=30 * 60)
        self.cog = cog
        self.session_id = session_id
        self.owner_user_id = owner_user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_user_id:
            await interaction.response.send_message("Only the session owner can act on this edit.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Apply", style=discord.ButtonStyle.success)
    async def apply_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.cog.handle_apply(interaction, self.session_id)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.cog.handle_cancel(interaction, self.session_id)


class CarrionSpineConfigCog(commands.Cog):
    """Carrion: Spine Discord-first Config Editor scaffold."""

    mm_group = app_commands.Group(name="mm", description="Carrion: Spine config tools")
    config_group = app_commands.Group(name="config", description="Config index actions", parent=mm_group)

    def __init__(
        self,
        bot: commands.Bot,
        *,
        db: Database,
        settings: CarrionSpineSettings,
    ) -> None:
        self.bot = bot
        self.db = db
        self.settings = settings
        self.validation = ValidationService()
        self.permission_service = PermissionService(
            PermissionConfig(
                module_access_roles=tuple(settings.module_access_roles),
                file_profile_roles={
                    key: tuple(value) for key, value in settings.file_profile_roles.items()
                },
            )
        )
        self.sessions = SessionManager(
            db=self.db,
            upload_dir=Path("./data/mm_uploads"),
            max_upload_bytes=settings.max_upload_bytes,
        )
        self.diff_dir = Path("./data/mm_diffs")

    async def cog_load(self) -> None:
        await self.db.initialize()

    @config_group.command(name="pull", description="Scan roots and update config index.")
    async def config_pull(self, interaction: discord.Interaction) -> None:
        if not self.permission_service.has_module_access(interaction.user):
            await interaction.response.send_message("You do not have module access.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)

        roots = [ConfigRoot(token=Path(root).name.lower(), path=Path(root)) for root in self.settings.config_roots]
        records = await scan_configs(roots)
        await self.db.replace_index_records(records)
        await interaction.followup.send(f"Indexed {len(records)} config files.", ephemeral=True)

    @config_group.command(name="list", description="List indexed configs.")
    async def config_list(self, interaction: discord.Interaction, root_filter: str | None = None) -> None:
        if not self.permission_service.has_module_access(interaction.user):
            await interaction.response.send_message("You do not have module access.", ephemeral=True)
            return
        records = await self.db.list_configs(root_filter=root_filter)
        if not records:
            await interaction.response.send_message("No indexed configs found.", ephemeral=True)
            return

        lines: list[str] = []
        for row in records[:100]:
            rel = self._relative_display_path(Path(row.full_path), row.root_token)
            lines.append(f"`{row.nickname}` -> `{rel}`")
        suffix = "\n...truncated..." if len(records) > 100 else ""
        await interaction.response.send_message("\n".join(lines) + suffix, ephemeral=True)

    @mm_group.command(name="edit", description="Start attachment-based edit session.")
    async def edit_start(self, interaction: discord.Interaction, nickname: str) -> None:
        if not self.permission_service.has_module_access(interaction.user):
            await interaction.response.send_message("You do not have module access.", ephemeral=True)
            return
        config = await self.db.get_config_by_nickname(nickname)
        if not config:
            await interaction.response.send_message("Unknown nickname.", ephemeral=True)
            return

        live_path = Path(config.full_path)
        if not live_path.exists():
            await interaction.response.send_message("Indexed file no longer exists.", ephemeral=True)
            return
        content = await asyncio.to_thread(live_path.read_bytes)
        session = await self.sessions.create_pending_session(
            user_id=interaction.user.id,
            nickname=nickname,
            original_hash=config.file_hash,
        )
        message = (
            f"Edit session created: `{session.session_id}`\n"
            "Download, modify, and upload the file in this channel with message text:\n"
            f"`mm-session:{session.session_id}`"
        )
        await interaction.response.send_message(
            message,
            file=discord.File(fp=io.BytesIO(content), filename=live_path.name),
            ephemeral=True,
        )

    @commands.Cog.listener("on_message")
    async def on_edit_upload(self, message: discord.Message) -> None:
        """
        Attachment handler.

        Expected format:
        - one attachment
        - message contains `mm-session:<id>`
        """
        if message.author.bot or not message.attachments:
            return
        marker = "mm-session:"
        if marker not in message.content:
            return
        session_id = message.content.split(marker, 1)[1].strip().split()[0]
        session = await self.db.get_session(session_id)
        if not session or session.status != "pending":
            await message.reply("Invalid or non-pending session id.")
            return
        if message.author.id != session.user_id:
            await message.reply("Only session owner can upload edits.")
            return

        config = await self.db.get_config_by_nickname(session.nickname)
        if not config:
            await message.reply("Config no longer indexed.")
            return

        attachment = message.attachments[0]
        extension_type = SUPPORTED_EXTENSIONS.get(Path(attachment.filename).suffix.lower())
        if extension_type != config.file_type:
            await message.reply("Upload type mismatch for this config.")
            return
        try:
            uploaded_path = await self.sessions.store_upload(session_id, attachment)
            edited_bytes = await asyncio.to_thread(uploaded_path.read_bytes)
        except ValueError as exc:
            await self._audit(
                user_id=message.author.id,
                config=config,
                diff_summary=None,
                status="validation_failed",
                validation_result=str(exc),
            )
            await message.reply(f"Upload rejected: {exc}")
            return

        live_path = Path(config.full_path)
        original_text = await asyncio.to_thread(live_path.read_text, encoding="utf-8")
        try:
            edited_text = edited_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            await message.reply("Edited file must be UTF-8 encoded text.")
            return

        validation = self.validation.validate(
            file_type=config.file_type,
            path=live_path,
            content=edited_bytes,
        )
        if not validation.ok:
            await self._audit(
                user_id=message.author.id,
                config=config,
                diff_summary=None,
                status="validation_failed",
                validation_result=validation.message,
            )
            await message.reply(f"Validation failed: {validation.message}")
            return
        if not self.permission_service.can_edit_profile(message.author, validation.profile_name):
            await message.reply("You do not have role access for this file profile.")
            return

        diff_result = generate_unified_diff(
            old_text=original_text,
            new_text=edited_text,
            old_label=f"{config.nickname}:original",
            new_label=f"{config.nickname}:edited",
        )
        view = EditDecisionView(self, session_id=session_id, owner_user_id=message.author.id)
        content = f"Validation passed ({validation.profile_name or 'format-only'}). Diff: {diff_result.summary.as_text()}"
        files: list[discord.File] = []
        if diff_result.is_truncated:
            diff_path = write_diff_attachment(diff_result.full_text, self.diff_dir / f"{session_id}.diff")
            files.append(discord.File(str(diff_path), filename=f"{session_id}.diff"))
            content += f"\n```diff\n{diff_result.excerpt_text}\n```"
        else:
            content += f"\n```diff\n{diff_result.excerpt_text}\n```"
        await message.reply(content, view=view, files=files)

    async def handle_apply(self, interaction: discord.Interaction, session_id: str) -> None:
        if not self.permission_service.has_module_access(interaction.user):
            await interaction.response.send_message("You do not have module access.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        session = await self.db.get_session(session_id)
        if not session or session.status != "pending":
            await interaction.followup.send("Session is not pending.", ephemeral=True)
            return
        config = await self.db.get_config_by_nickname(session.nickname)
        if not config:
            await interaction.followup.send("Config is no longer indexed.", ephemeral=True)
            return
        if not session.uploaded_path:
            await interaction.followup.send("No uploaded file found for session.", ephemeral=True)
            return

        uploaded_bytes = await asyncio.to_thread(Path(session.uploaded_path).read_bytes)
        result = await apply_edit(
            live_path=Path(config.full_path),
            edited_payload=uploaded_bytes,
            expected_hash=session.original_hash,
            allowed_roots=[Path(p) for p in self.settings.config_roots],
            backup_dir=self.settings.backup_dir,
            backup_keep=self.settings.backup_keep,
        )
        status = "applied" if result.ok else "apply_failed"
        await self._audit(
            user_id=interaction.user.id,
            config=config,
            diff_summary=result.message,
            status=status,
            validation_result="ok" if result.ok else result.message,
        )
        if result.ok:
            await self.sessions.mark_applied(session_id)
        await interaction.followup.send(result.message, ephemeral=True)

    async def handle_cancel(self, interaction: discord.Interaction, session_id: str) -> None:
        if not self.permission_service.has_module_access(interaction.user):
            await interaction.response.send_message("You do not have module access.", ephemeral=True)
            return
        await self.sessions.cancel_session(session_id)
        session = await self.db.get_session(session_id)
        if session:
            config = await self.db.get_config_by_nickname(session.nickname)
            if config:
                await self._audit(
                    user_id=interaction.user.id,
                    config=config,
                    diff_summary=None,
                    status="cancelled",
                    validation_result="n/a",
                )
        await interaction.response.send_message("Edit cancelled.", ephemeral=True)

    def _relative_display_path(self, full_path: Path, root_token: str) -> str:
        for root in self.settings.config_roots:
            root_path = Path(root)
            try:
                rel = full_path.relative_to(root_path)
                return f"{root_token}/{rel.as_posix()}"
            except ValueError:
                continue
        return full_path.as_posix()

    async def _audit(
        self,
        *,
        user_id: int,
        config: ConfigRecord,
        diff_summary: str | None,
        status: str,
        validation_result: str,
    ) -> None:
        await self.db.insert_audit(
            user_id=user_id,
            nickname=config.nickname,
            full_path=config.full_path,
            timestamp=datetime.now(UTC).isoformat(),
            diff_summary=diff_summary,
            status=status,
            validation_result=validation_result,
        )


async def setup(bot: commands.Bot) -> None:
    """
    Example extension setup.

    TODO: Load settings from environment/config file.
    """
    db = Database(Path("./data/carrion_spine.sqlite3"))
    settings = CarrionSpineSettings(
        config_roots=[Path("/srv/7dtd")],
        module_access_roles=[],
        file_profile_roles={},
    )
    await bot.add_cog(CarrionSpineConfigCog(bot, db=db, settings=settings))

