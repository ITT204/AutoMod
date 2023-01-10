# type: ignore

import discord
from discord.ext import commands
from discord import AuditLogAction

import asyncio
import topgg
import discordspy
import os
from ...__obj__ import TypeHintedToolboxObject as Object
from typing import Callable, Union, Tuple, TypeVar, Optional, List, Dict
import logging; log = logging.getLogger()

from .. import AutoModPluginBlueprint, ShardedBotInstance
from .._processor import LogProcessor
from ...schemas import GuildConfig
from ...types import Embed



T = TypeVar("T")


SERVER_LOG_EVENTS = {
    "role_created": {
        "emote": "CREATE",
        "color": 0x43b582,
        "audit_log_action": AuditLogAction.role_create,
        "text": "Role created"
    },
    "role_deleted": {
        "emote": "DELETE",
        "color": 0xff5c5c,
        "audit_log_action": AuditLogAction.role_delete,
        "text": "Role deleted"
    },
    "role_updated": {
        "emote": "UPDATE",
        "color": 0xffdc5c,
        "audit_log_action": AuditLogAction.role_update,
        "text": "Role updated",
        "extra_text": "**Change:** {change}"
    },

    "channel_created": {
        "emote": "CREATE",
        "color": 0x43b582,
        "audit_log_action": AuditLogAction.channel_create,
        "text": "Channel created",
        "extra_text": "**Type:** {_type}"
    },
    "channel_deleted": {
        "emote": "DELETE",
        "color": 0xff5c5c,
        "audit_log_action": AuditLogAction.channel_delete,
        "text": "Channel deleted",
        "extra_text": "**Type:** {_type}"
    },
    "channel_updated": {
        "emote": "UPDATE",
        "color": 0xffdc5c,
        "audit_log_action": AuditLogAction.channel_update,
        "text": "Channel updated",
        "extra_text": "**Type:** {_type} \n**Change:** {change} "
    },

    "thread_created": {
        "emote": "CREATE",
        "color": 0x43b582,
        "audit_log_action": AuditLogAction.thread_create,
        "text": "Thread created"
    },
    "thread_deleted": {
        "emote": "DELETE",
        "color": 0xff5c5c,
        "audit_log_action": AuditLogAction.thread_delete,
        "text": "Thread deleted"
    },
    "thread_updated": {
        "emote": "UPDATE",
        "color": 0xffdc5c,
        "audit_log_action": AuditLogAction.thread_update,
        "text": "Thread updated",
        "extra_text": "**Change:** {change}"
    },

    "emoji_created": {
        "emote": "CREATE",
        "color": 0x43b582,
        "audit_log_action": AuditLogAction.emoji_create,
        "text": "Emoji created",
        "extra_text": "**Showcase:** {showcase}"
    },
    "emoji_deleted": {
        "emote": "DELETE",
        "color": 0xff5c5c,
        "audit_log_action": AuditLogAction.emoji_delete,
        "text": "Emoji deleted"
    },

    "sticker_created": {
        "emote": "CREATE",
        "color": 0x43b582,
        "audit_log_action": AuditLogAction.sticker_create,
        "text": "Sticker created",
        "extra_text": "**Showcase:** {showcase}"
    },
    "sticker_deleted": {
        "emote": "DELETE",
        "color": 0xff5c5c,
        "audit_log_action": AuditLogAction.sticker_delete,
        "text": "Sticker deleted"
    },

    "nick_added": {
        "emote": "CREATE",
        "color": 0x43b582,
        "audit_log_action": AuditLogAction.member_update,
        "text": "Nickname added",
        "extra_text": "**New:** {change}"
    },
    "nick_removed": {
        "emote": "DELETE",
        "color": 0xff5c5c,
        "audit_log_action": AuditLogAction.member_update,
        "text": "Nickname removed",
        "extra_text": "**Old:** {change}"
    },
    "nick_updated": {
        "emote": "UPDATE",
        "color": 0xffdc5c,
        "audit_log_action": AuditLogAction.member_update,
        "text": "Nickname updated",
        "extra_text": "**Change:** {change}"
    },
    "added_role": {
        "emote": "CREATE",
        "color": 0x43b582,
        "audit_log_action": AuditLogAction.member_role_update,
        "text": "Role added",
        "extra_text": "**Role:** {change}"
    },
    "removed_role": {
        "emote": "DELETE",
        "color": 0xff5c5c,
        "audit_log_action": AuditLogAction.member_role_update,
        "text": "Role removed",
        "extra_text": "**Role:** {change}"
    },
    "username_updated": {
        "emote": "UPDATE",
        "color": 0xffdc5c,
        "audit_log_action": AuditLogAction.member_update,
        "text": "Username updated",
        "extra_text": "**Change:** {change}"
    },

    "joined_voice": {
        "emote": "CREATE",
        "color": 0x43b582,
        "audit_log_action": AuditLogAction.member_move,
        "text": "Joined voice channel",
        "extra_text": "**Channel:** <#{channel}>"
    },
    "left_voice": {
        "emote": "DELETE",
        "color": 0xff5c5c,
        "audit_log_action": AuditLogAction.member_move,
        "text": "Left voice channel",
        "extra_text": "**Channel:** <#{channel}>"
    },
    "switched_voice": {
        "emote": "SWITCH",
        "color": 0xffdc5c,
        "audit_log_action": AuditLogAction.member_move,
        "text": "Switched voice channel",
        "extra_text": "**Change:** <#{before}> → <#{after}>"
    },

    "bot_added": {
        "emote": "ROBOT",
        "color": 0x43b582,
        "audit_log_action": AuditLogAction.bot_add,
        "text": "Bot added",
    }
}


class InternalPlugin(AutoModPluginBlueprint):
    """Plugin for internal/log events"""
    def __init__(self, bot: ShardedBotInstance) -> None:
        super().__init__(bot)
        self.log_processor = LogProcessor(bot)
        if bot.config.top_gg_token != "":
            self.topgg = topgg.DBLClient(
                bot,
                bot.config.top_gg_token,
                autopost=True,
                post_shard_count=True
            )
            self.topgg_webhook = topgg.WebhookManager(bot).dbl_webhook("/dblwebhook", bot.config.top_gg_password)
            self.topgg_webhook.run(bot.config.top_gg_port)
        if bot.config.discords_token != "":
            self.discords = discordspy.Client(
                self.bot,
                bot.config.discords_token,
                post=discordspy.Post.auto()
            )


    async def _find_in_audit_log(self, guild: discord.Guild, action: discord.AuditLogAction, check: Callable) -> Optional[discord.AuditLogEntry]:
        try:
            if guild.me == None: return None

            e = None
            if guild.me.guild_permissions.view_audit_log:
                try:
                    async for _e in guild.audit_logs(
                        action=action,
                        limit=10
                    ): 
                        if check(_e) == True:
                            if e == None or _e.id > e.id:
                                e = _e
                except discord.Forbidden:
                    pass
            
            if e != None:
                return e
            else:
                return None
        except (
            asyncio.TimeoutError, 
            asyncio.CancelledError
        ): return None


    async def find_in_audit_log(self, guild: discord.Guild, action: discord.AuditLogAction, check: Callable) -> Optional[discord.AuditLogEntry]:
        try:
            return await asyncio.wait_for(
                self._find_in_audit_log(guild, action, check),
                timeout=10
            )
        except (
            asyncio.TimeoutError, 
            asyncio.CancelledError
        ): return None


    async def server_log_embed(self, action: discord.AuditLogAction, guild: discord.Guild, obj: T, check_for_audit: Union[Callable, bool], **text_kwargs) -> Embed:
        data = Object(SERVER_LOG_EVENTS[action])
        e = Embed(
            None,
            color=data.color
        )
        if check_for_audit != False:
            mod = await self.find_in_audit_log(
                guild,
                data.audit_log_action,
                check_for_audit
            )
            
            by_field = ""
            if mod != None:
                mod = guild.get_member(mod.user.id)
                if mod != None:
                    if mod.guild_permissions.manage_messages == True:
                        by_field = "Moderator"
                    else:
                        rid = self.db.configs.get(guild.id, "mod_role")
                        if rid != "":
                            if int(rid) in [x.id for x in mod.roles]:
                                by_field = "Moderator"
                            else:
                                by_field = "User"
                        else:
                            by_field = "User"
                else:
                    by_field = "User"
            else:
                by_field = "User"

            e.description = "{} **{}:** {} ({}) \n\n**{}:** {}\n{}".format(
                self.bot.emotes.get(data.emote),
                data.text,
                obj.name if not hasattr(obj, "banner") else obj.mention,
                obj.id,
                by_field,
                f"{mod.mention} ({mod.id})" if mod != None else "Unknown",
                str(data.extra_text).format(**text_kwargs) if len(text_kwargs) > 0 else ""
            )
        else:
            e.description = "{} **{}:** {} ({}) \n\n{}".format(
                self.bot.emotes.get(data.emote),
                data.text,
                obj.name if not hasattr(obj, "banner") else obj.mention,
                obj.id,
                str(data.extra_text).format(**text_kwargs) if len(text_kwargs) > 0 else ""
            )

        return e


    def get_ignored_roles_channels(self, guild: discord.Guild) -> Tuple[List[str], List[str]]:
        roles, channels = self.db.configs.get(guild.id, "ignored_roles_log"), self.db.configs.get(guild.id, "ignored_channels_log")
        return roles, channels

    
    def get_message(self, guild: discord.Guild, payload: Union[discord.RawMessageDeleteEvent, discord.RawMessageUpdateEvent]) -> Optional[discord.Message]:
        if payload.cached_message != None: 
            return payload.cached_message
        else:
            return self.bot.message_cache.get(guild, payload.message_id)


    def _c(self,inp: str) -> str:
        return discord.utils.escape_markdown(inp)


    @AutoModPluginBlueprint.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        log.info(f"[Events] Joined guild: {guild.name} ({guild.id})", extra={"loc": f"Shard {guild.shard_id}"})

        try:
            await self.bot.chunk_guild(guild)
        except Exception as ex:
            log.warn(f"[Events] Failed to chunk members for guild {guild.id} upon joining - {ex}", extra={"loc": f"Shard {guild.shard_id}"})
        finally:
            if not self.db.configs.exists(guild.id):
                self.db.configs.insert(GuildConfig(guild, self.config.default_prefix))


    @AutoModPluginBlueprint.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        if guild == None: return
        log.info(f"[Events] Removed from guild: {guild.name} ({guild.id})", extra={"loc": f"Shard {guild.shard_id}"})
        if self.db.configs.exists(guild.id):
            self.db.cases.multi_delete({"guild": f"{guild.id}"})
            self.db.configs.delete(guild.id)

    
    @AutoModPluginBlueprint.listener()
    async def on_message(self, msg: discord.Message) -> None:
        if msg.guild == None: return
        if msg.type != discord.MessageType.default: return
        self.bot.message_cache.insert(msg.guild, msg)


    @AutoModPluginBlueprint.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        if payload.guild_id == None: return
        self.bot.message_cache.delete(payload.guild_id, payload.message_id)

        guild = self.bot.get_guild(payload.guild_id)
        if guild == None: return

        msg: discord.Message = self.get_message(guild, payload)
        if msg == None: return

        await asyncio.sleep(0.3) # wait a bit before checking ignore_for_events
        if msg.id in self.bot.ignore_for_events:
            return self.bot.ignore_for_events.remove(msg.id)
        
        # I hate this
        cfg = self.db.configs.get_doc(msg.guild.id)
        if cfg["message_log"] == "" \
        or not isinstance(msg.channel, discord.TextChannel) \
        or msg.author.id == self.bot.user.id \
        or msg.author.bot == True:
            return

        if guild.chunked == False: await self.bot.chunk_guild(guild)
        author = guild.get_member(msg.author.id)

        roles, channels = self.get_ignored_roles_channels(msg.guild)
        if author != None:
            if any(x in [i.id for i in msg.author.roles] for x in roles): return
        if msg.channel.id in channels: return
        
        content = msg.content
        e = Embed(
            None,
            color=0xff5c5c,
            description=content[:4096] if content != None or content != "" else None
        )
        e.add_field(
            name="Attachments",
            value=f"{len(msg.attachments)}"
        )

        no = self.bot.emotes.get("NO")
        yes = self.bot.emotes.get("YES")
        for i, _e in enumerate(msg.embeds[:23]):
            e.add_field(
                name=f"Embed ({i+1}/{len(msg.embeds)})",
                value="**• Title:** {} \n**• Description:** {} \n**• Fields:** {} \n**• Thumbnail:** {} \n**• Image:** {} \n**• Footer:** {}".format(
                    self._c(_e.title) if _e.title else no,
                    yes if _e.description else no,
                    len(_e.fields),
                    f"{yes}" if _e.thumbnail else no,
                    f"{yes}" if _e.image else no,
                    yes if _e.footer else no
                )
            )
        
        e.set_author(
            name="Message deleted by {0.name}#{0.discriminator} ({0.id})".format(msg.author),
            icon_url=msg.author.display_avatar
        )
        e.set_footer(
            text="#{}".format(msg.channel.name)
        )

        await self.log_processor.execute(msg.guild, "message_deleted", **{
            "_embed": e
        })


    @AutoModPluginBlueprint.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent) -> None:
        if payload.guild_id == None: return

        guild = self.bot.get_guild(payload.guild_id)
        if guild == None: return

        msg = self.get_message(guild, payload)
        if msg == None: return

        content = payload.data.get("content", None)
        if content == None: return

        cfg = self.db.configs.get_doc(msg.guild.id)
        if cfg["message_log"] == "" \
        or not isinstance(msg.channel, discord.TextChannel) \
        or msg.author.id == self.bot.user.id \
        or msg.author.bot == True \
        or msg.type != discord.MessageType.default:
            return

        roles, channels = self.get_ignored_roles_channels(msg.guild)
        if msg.channel.id in channels: return
        if any(x in [i.id for i in msg.author.roles] for x in roles): return
        
        if msg.content != content and len(content) > 0:
            e = Embed(
                None,
                color=0xffdc5c
            )
            e.set_author(
                name="Message edited by {0.name}#{0.discriminator} ({0.id})".format(msg.author),
                icon_url=msg.author.display_avatar,
                url=msg.jump_url
            )
            e.add_field(
                name="Before",
                value=msg.content
            )
            e.add_field(
                name="After",
                value=content
            )
            e.set_footer(
                text="#{}".format(msg.channel.name)
            )

            await self.log_processor.execute(msg.guild, "message_edited", **{
                "_embed": e
            })


    @AutoModPluginBlueprint.listener()
    async def on_member_join(self, user: discord.Member) -> None:
        if user.bot:
            embed = await self.server_log_embed(
                "bot_added",
                user.guild,
                user,
                lambda x: x.target.id == user.id
            )

            await self.log_processor.execute(user.guild, "bot_added", **{
                "_embed": embed
            })
        else:
            self.bot.dispatch("join_role", user)
            e = Embed(
                None,
                color=0x43b582,
                description=self.locale.t(user.guild, "user_joined", profile=user.mention, created=round(user.created_at.timestamp()))
            )
            e.set_thumbnail(
                url=user.display_avatar
            )
            e.set_footer(
                text=f"User joined | {user.name}#{user.discriminator}"
            )
            await self.log_processor.execute(user.guild, "user_joined", **{
                "_embed": e
            })


    @AutoModPluginBlueprint.listener()
    async def on_member_remove(self, user: discord.Member) -> None:
        await asyncio.sleep(0.3)
        if user.id in self.bot.ignore_for_events:
            return self.bot.ignore_for_events.remove(user.id)
        if user.id == self.bot.user.id: return
        
        roles = [x.mention for x in user.roles if str(x.id) != str(user.guild.default_role.id)]
        e = Embed(
            None,
            color=0x2f3136,
            description=self.locale.t(
                user.guild, 
                "user_left", 
                profile=user.mention, 
                joined=round(user.joined_at.timestamp()),
                roles=", ".join(roles) if len(roles) < 15 and len(roles) > 0 else len(roles) if len(roles) > 15 else "None"
            )
        )
        e.set_thumbnail(
            url=user.display_avatar
        )
        e.set_footer(
            text=f"User left | {user.name}#{user.discriminator}"
        )
        await self.log_processor.execute(user.guild, "user_left", **{
            "_embed": e
        })

    
    @AutoModPluginBlueprint.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        embed = await self.server_log_embed(
            "role_created",
            role.guild,
            role,
            lambda x: x.target.id == role.id
        )

        await self.log_processor.execute(role.guild, "role_created", **{
            "_embed": embed
        })


    @AutoModPluginBlueprint.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        embed = await self.server_log_embed(
            "role_deleted",
            role.guild,
            role,
            lambda x: x.target.id == role.id
        )

        await self.log_processor.execute(role.guild, "role_deleted", **{
            "_embed": embed
        })


    @AutoModPluginBlueprint.listener()
    async def on_guild_role_update(self, b: discord.Role, a: discord.Role) -> None:
        roles, _ = self.get_ignored_roles_channels(a.guild)
        if a.id in roles: return

        change = ""
        if b.name != a.name:
            change += "Name (``{}`` → ``{}``)".format(
                a.name,
                b.name
            )

        if b.color != a.color:
            new = "Color ([{}](https://www.color-hex.com/color/{}) → [{}](https://www.color-hex.com/color/{}))".format(
                b.color,
                str(b.color)[1:],
                a.color,
                str(a.color)[1:]
            )
            if len(change) < 1: change += new
            else: change += f" & {new}"
        
        if b.hoist != a.hoist:
            if b.hoist == False and a.hoist == True:
                new = "Hoisted"
            elif b.hoist == True and a.hoist == False:
                new = "Unhoisted"
            if len(change) < 1: change += new
            else: change += f" & {new}"
        
        if b.mentionable != a.mentionable:
            if b.mentionable == False and a.mentionable == True:
                new = "Mentionable"
            elif b.mentionable == True and a.mentionable == False:
                new = "Unmentionable"
            if len(change) < 1: change += new
            else: change += f" & {new}"
        
        if len(change) < 1: return

        embed = await self.server_log_embed(
            "role_updated",
            a.guild,
            b,
            lambda x: x.target.id == a.id,
            change=change
        )

        await self.log_processor.execute(a.guild, "role_updated", **{
            "_embed": embed
        })


    @AutoModPluginBlueprint.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        embed = await self.server_log_embed(
            "channel_created",
            channel.guild,
            channel,
            lambda x: x.target.id == channel.id,
            _type=str(channel.type).replace("_", " ").title()
        )

        await self.log_processor.execute(channel.guild, "channel_created", **{
            "_embed": embed
        })


    @AutoModPluginBlueprint.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        _, channels = self.get_ignored_roles_channels(channel.guild)
        if channel.id in channels: return

        embed = await self.server_log_embed(
            "channel_deleted",
            channel.guild,
            channel,
            lambda x: x.target.id == channel.id,
            _type=str(channel.type).replace("_", " ").title()
        )

        await self.log_processor.execute(channel.guild, "channel_deleted", **{
            "_embed": embed
        })


    @AutoModPluginBlueprint.listener()
    async def on_guild_channel_update(self, b: discord.abc.GuildChannel, a: discord.abc.GuildChannel) -> None:
        await asyncio.sleep(0.3)
        _, channels = self.get_ignored_roles_channels(b.guild)
        if a.id in channels: return

        if a.position != b.position: return

        change = ""
        if b.name != a.name:
            change += "Name (``{}`` → ``{}``)".format(
                b.name,
                a.name
            )

        if hasattr(b, "slowmode_delay") and hasattr(a, "slowmode_delay"):
            if b.slowmode_delay != a.slowmode_delay:
                if len(change) < 1:
                    change = "Slowmode (``{}s`` → ``{}s``)".format(
                        b.slowmode_delay,
                        a.slowmode_delay
                    )
                else:
                    change += " & Slowmode (``{}s`` → ``{}s``)".format(
                        b.slowmode_delay,
                        a.slowmode_delay
                    )
                
        
        if hasattr(b, "nsfw") and hasattr(a, "nsfw"):
            if b.nsfw != a.nsfw:
                if b.nsfw == False and a.nsfw == True:
                    new = "NSFW enabled"
                elif b.nsfw == True and a.nsfw == False:
                    new = "NSFW disabled"
                if len(change) < 1: change += new
                else: change += f" & {new}"

        if hasattr(b, "topic") and hasattr(b, "topic"):
            if b.topic != a.topic:
                new = "Topic (``{}`` → ``{}``)".format(
                    a.topic, 
                    b.topic
                )
                if len(change) < 1: change += new
                else: change += f" & {new}"
        
        if len(change) < 1: return

        embed = await self.server_log_embed(
            "channel_updated",
            a.guild,
            a,
            lambda x: x.target.id == b.id,
            change=change,
            _type=str(a.type).replace("_", " ").title()
        )

        await self.log_processor.execute(a.guild, "channel_updated", **{
            "_embed": embed
        })

    
    @AutoModPluginBlueprint.listener()
    async def on_guild_emojis_update(self, _, b: List[discord.Emoji], a: List[discord.Emoji]) -> None:
        if len(b) > len(a):
            action = "emoji_deleted"
            emoji = [x for x in b if x not in a][0]
            extra_text = {}
        elif len(b) < len(a):
            action = "emoji_created"
            emoji = [x for x in a if x not in b][0]
            extra_text = {"showcase": f"<{'a' if emoji.animated else ''}:{emoji.name}:{emoji.id}>"}
        else:
            return

        if emoji.guild == None: return

        embed = await self.server_log_embed(
            action,
            emoji.guild,
            emoji,
            lambda x: x.target.id == emoji.id,
            **extra_text
        )

        await self.log_processor.execute(emoji.guild, action, **{
            "_embed": embed
        })


    @AutoModPluginBlueprint.listener()
    async def on_guild_stickers_update(self, _, b: List[discord.GuildSticker], a: List[discord.GuildSticker]) -> None:
        if len(b) > len(a):
            action = "sticker_deleted"
            sticker = [x for x in b if x not in a][0]
            extra_text = {}
        elif len(b) < len(a):
            action = "sticker_created"
            sticker = [x for x in a if x not in b][0]
            extra_text = {"showcase": f"[Here]({sticker.url})"}
        else:
            return

        if sticker.guild == None: return

        embed = await self.server_log_embed(
            action,
            sticker.guild,
            sticker,
            lambda x: x.target.id == sticker.id,
            **extra_text
        )

        await self.log_processor.execute(sticker.guild, action, **{
            "_embed": embed
        })


    @AutoModPluginBlueprint.listener()
    async def on_thread_create(self, thread: discord.Thread) -> None:
        _, channels = self.get_ignored_roles_channels(thread.guild)
        if thread.parent.id in channels: return

        embed = await self.server_log_embed(
            "thread_created",
            thread.guild,
            thread,
            lambda x: x.target.id == thread.id
        )

        await self.log_processor.execute(thread.guild, "thread_created", **{
            "_embed": embed
        })
        await self.bot.join_thread(thread)

    
    @AutoModPluginBlueprint.listener()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        _, channels = self.get_ignored_roles_channels(thread.guild)
        if thread.parent.id in channels:
            return

        embed = await self.server_log_embed(
            "thread_deleted",
            thread.guild,
            thread,
            lambda x: x.target.id == thread.id
        )

        await self.log_processor.execute(thread.guild, "thread_deleted", **{
            "_embed": embed
        })


    @AutoModPluginBlueprint.listener()
    async def on_thread_update(self, b: discord.Thread, a: discord.Thread) -> None:
        _, channels = self.get_ignored_roles_channels(b.guild)
        if b.parent.id in channels or a.parent.id in channels: return

        change = ""
        if b.name != a.name:
            change += "Name (``{}`` → ``{}``)".format(
                b.name,
                a.name
            )
        if b.archived != a.archived:
            new = "Archived" if a.archived == True else "Unarchived"
            if len(change) < 1:
                change += new
            else:
                change += f" & {new}"
        
        if len(change) < 1: return

        embed = await self.server_log_embed(
            "thread_updated",
            a.guild,
            a,
            lambda x: x.target.id == a.id,
            change=change
        )

        await self.log_processor.execute(a.guild, "thread_updated", **{
            "_embed": embed
        })


    @AutoModPluginBlueprint.listener()
    async def on_member_update(self, b: discord.Member, a: discord.Member) -> None:
        if not a.guild.chunked: await self.bot.chunk_guild(a.guild)

        roles, _ = self.get_ignored_roles_channels(a.guild)
        if any(x in [i.id for i in a.roles] for x in roles): return
        for r in [*b.roles, *a.roles]:
            if r.id in roles: return

        key = ""
        change = ""
        check_audit = False
        if b.nick != a.nick:
            if b.nick == None and a.nick != None:
                change += "``{}``".format(
                    a.nick
                )
                key = "nick_added"
            elif b.nick != None and a.nick == None:
                change += "``{}``".format(
                    b.nick
                )
                key = "nick_removed"
            else:
                change += "``{}`` → ``{}``".format(
                    b.nick,
                    a.nick
                )
                key = "nick_updated"
            
        if b.roles != a.roles:
            check_audit = True
            added_roles = [x.mention for x in a.roles if x not in b.roles]
            removed_roles = [x.mention for x in b.roles if x not in a.roles]


            if len(added_roles) > 0:
                key = "added_role"
                change = ", ".join(added_roles)
            elif len(removed_roles) > 0:
                key = "removed_role"
                change = ", ".join(removed_roles)
        
        if key == "": return

        embed = await self.server_log_embed(
            key,
            a.guild,
            a,
            False if check_audit == False else lambda x: x.target.id == a.id,
            change=change
        )

        await self.log_processor.execute(a.guild, "member_updated", **{
            "_embed": embed
        })


    @AutoModPluginBlueprint.listener()
    async def on_user_update(self, b: discord.User, a: discord.User) -> None:
        change = ""
        if b.name != a.name or b.discriminator != a.discriminator:
            change += "``{}`` → ``{}``".format(
                f"{b.name}#{b.discriminator}",
                f"{a.name}#{a.discriminator}"
            )
        
        if len(change) < 1: return

        for guild in self.bot.guilds:
            m = guild.get_member(a.id)
            if m != None:
                roles, _ = self.get_ignored_roles_channels(m.guild)
                if any(x in [i.id for i in m.roles] for x in roles): return

                embed = await self.server_log_embed(
                    "username_updated",
                    guild,
                    a,
                    False,
                    change=change
                )

                await self.log_processor.execute(guild, "member_updated", **{
                    "_embed": embed
                })
        

    @AutoModPluginBlueprint.listener()
    async def on_voice_state_update(self, user: discord.Member, b: discord.VoiceState, a: discord.VoiceState) -> None:
        if user.guild == None: return

        roles, channels = self.get_ignored_roles_channels(user.guild)
        if any(x in [i.id for i in user.roles] for x in roles): return

        key = ""
        text = {}
        if b.channel != a.channel:
            if b.channel == None and a.channel != None:
                if a.channel.id not in channels:
                    key = "joined_voice"
                    text.update({
                        "channel": a.channel.id
                    })
            elif b.channel != None and a.channel == None:
                if b.channel.id not in channels:
                    key = "left_voice"
                    text.update({
                        "channel": b.channel.id
                    })
            elif b.channel != None and a.channel != None:
                if b.channel.id not in channels and a.channel.id not in channels:
                    key = "switched_voice"
                    text.update({
                        "before": b.channel.id,
                        "after": a.channel.id
                    })
            else:
                pass
            if key != "":
                embed = await self.server_log_embed(
                    key,
                    user.guild,
                    user,
                    False,
                    **text
                )

                await self.log_processor.execute(user.guild, key, **{
                    "_embed": embed
                })


    @AutoModPluginBlueprint.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User) -> None:
        await asyncio.sleep(0.3) # wait a bit before checking ignore_for_events
        if user.id in self.bot.ignore_for_events:
            return self.bot.ignore_for_events.remove(user.id)

        entry = await self.find_in_audit_log(
            guild,
            discord.AuditLogAction.unban,
            lambda x: x.target.id == user.id
        )

        await self.log_processor.execute(guild, "manual_unban", **{
            "user": user,
            "user_id": user.id,
            "mod": entry.user if entry != None else "Unknown#0000",
            "mod_id": entry.user.id if entry != None else 0
        })


    @AutoModPluginBlueprint.listener()
    async def on_member_ban(self, guild: discord.Guild, user: Union[discord.Member,discord.User]) -> None:
        await asyncio.sleep(0.3)
        if user.id in self.bot.ignore_for_events:
            return self.bot.ignore_for_events.remove(user.id)

        entry = await self.find_in_audit_log(
            guild,
            discord.AuditLogAction.ban,
            lambda x: x.target.id == user.id
        )

        await self.log_processor.execute(guild, "manual_ban", **{
            "user": user,
            "user_id": user.id,
            "mod": entry.user if entry != None else "Unknown#0000",
            "mod_id": entry.user.id if entry != None else 0,
            "reason": entry.reason if entry != None else "No reason"
        })


    @AutoModPluginBlueprint.listener()
    async def on_join_role(self, user: discord.Member) -> None:
        if user.guild == None: return
        if not user.guild.chunked: await self.bot.chunk_guild(user.guild)
        
        rid = self.db.configs.get(user.guild.id, "join_role")
        if rid != "":
            role = user.guild.get_role(int(rid))
            if role != None:
                if user.pending == False:
                    try:
                        await user.add_roles(role)
                    except (
                        discord.Forbidden,
                        discord.HTTPException
                    ):
                        pass

    
    @AutoModPluginBlueprint.listener(name="on_member_update")
    async def on_membership_screening(self, b: discord.Member, a: discord.Member) -> None:
        if a.guild == None: return
        if not a.guild.chunked: await self.bot.chunk_guild(a.guild)
        
        if b.pending == True and a.pending == False:
            rid = self.db.configs.get(a.guild.id, "join_role")
            if rid != "":
                role = a.guild.get_role(int(rid))
                if role != None:
                    try:
                        await a.add_roles(role)
                    except (
                        discord.Forbidden,
                        discord.HTTPException
                    ):
                        pass


    @AutoModPluginBlueprint.listener()
    async def on_autopost_success(self) -> None:
        log.info(f"[Events] Posted server count ({self.topgg.guild_count}) and shard count ({len(self.bot.shards)}) to Top.GG", extra={"loc": f"PID {os.getpid()}"})


    @AutoModPluginBlueprint.listener()
    async def on_discords_server_post(self, status: int) -> None:
        if status == 200: 
            log.info(f"[Events] Posted server count ({self.discords.servers()}) to discords.com", extra={"loc": f"PID {os.getpid()}"})
        else:
            log.info(f"[Events] Failed to post stats to discords.com ({status})", extra={"loc": f"PID {os.getpid()}"})


    @AutoModPluginBlueprint.listener()
    async def on_dbl_vote(self, data: Dict[str, str]) -> None:
        guild = self.bot.get_guild(int(self.config.support_server))
        if guild == None: return

        channel = self.bot.get_channel(int(self.config.vote_channel))
        if channel != None:
            try:
                e = Embed(
                    None,
                    description=f"{self.bot.emotes.get('PARTY')} Thanks for voting, <@{data.get('user')}>! \n\nhttps://top.gg/bot/{self.bot.user.id}/vote"
                )
                e.credits()
                await channel.send(embed=e)
            except Exception:
                pass


async def setup(bot: ShardedBotInstance) -> None: 
    await bot.register_plugin(InternalPlugin(bot))