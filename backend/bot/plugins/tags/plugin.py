# type: ignore

import discord
from discord.ext import commands

from toolbox import S as Object
import datetime
from typing import Literal
import re
import logging; log = logging.getLogger()

from .. import AutoModPluginBlueprint, ShardedBotInstance
from ...schemas import Tag
from ...types import Embed, E
from ...modals import CommandCreateModal



class TagsPlugin(AutoModPluginBlueprint):
    """Plugin for tags (custom commands)"""
    def __init__(
        self, 
        bot: ShardedBotInstance
    ) -> None:
        super().__init__(bot)
        self._tags = {}
        self._cached_from_api = {}
        self.bot.loop.create_task(self.cache_tags())


    async def custom_callback(
        self,
        ctx: discord.Interaction
    ) -> None:
        if ctx.guild_id in self._tags:
            data = self._tags[ctx.guild_id].get(
                ctx.command.qualified_name.lower(),
                None
            )
            if data != None:
                cmd = Object(data)
                self.update_uses(f"{ctx.guild_id}-{ctx.command.qualified_name.lower()}")
                return await ctx.response.send_message(
                    cmd.content,
                    ephemeral=cmd.ephemeral
                )
        

    def add_tag(
        self, 
        ctx: discord.Interaction, 
        name: str, 
        content: str,
        description: str,
        ephemeral: bool
    ) -> None:
        try:
            self.bot.tree.add_command(
                discord.app_commands.Command(
                    name=name,
                    description=description,
                    callback=self.custom_callback,
                    guild_ids=[ctx.guild_id]
                )
            )
        except Exception as ex:
            return ex
        else:
            data = {
                name: {
                    "content": content,
                    "author": ctx.user.id,
                    "ephemeral": ephemeral,
                    "description": description
                }
            }
            if not ctx.guild.id in self._tags:
                self._tags[ctx.guild.id] = data
            else:
                self._tags[ctx.guild.id].update(data)

            self.db.tags.insert(Tag(ctx, name, content, ephemeral, description))
            return None


    def remove_tag(
        self, 
        guild: discord.Guild, 
        name: str
    ) -> None:
        try:
            self.bot.tree.remove_command(
                name,
                guild=guild
            )
        except Exception as ex:
            return ex
        else:
            self._tags[guild.id].pop(name)
            self.db.tags.delete(f"{guild.id}-{name}")
            return None


    def update_tag(
        self, 
        ctx: discord.Interaction, 
        name: str, 
        content: str,
        ephemeral: bool
    ) -> None:
        self._tags[ctx.guild.id][name].update({
            "content": content,
            "ephemeral": ephemeral
        })
        self.db.tags.multi_update(f"{ctx.guild.id}-{name}", {
            "content": content,
            "editor": f"{ctx.user.id}",
            "edited": datetime.datetime.now(),
            "ephemeral": ephemeral
        })


    async def cache_tags(
        self
    ) -> None:
        _ = True
        while _:
            _ = False
            needs_sync = {}
            for e in self.db.tags.find({}):
                _id = int(e["id"].split("-")[0])
                if "name" in e:
                    data = {
                        e["name"]: {
                            "content": e["content"],
                            "author": int(e["author"]),
                            "ephemeral": e.get("ephemeral", False),
                            "description": e["description"]
                        }
                    }
                else: # migration bs
                    data = {
                        "-".join(e["id"].split("-")[1:]): {
                            "content": e["reply"],
                            "author": int(e["author"]),
                            "ephemeral": e.get("ephemeral", False),
                            "description": e["description"]
                        }
                    }
                
                if self.validate_name(list(data.keys())[0]):
                    if not _id in self._tags:
                        self._tags[_id] = data
                    else:
                        self._tags[_id].update(data)
                    
                    try:
                        self.bot.tree.add_command(
                            discord.app_commands.Command(
                                name=e["name"] if "name" in e else "-".join(e["id"].split("-")[1:]),
                                description=e["description"],
                                callback=self.custom_callback,
                                guild_ids=[int(e["id"].split("-")[0])]
                            )
                        )
                    except Exception:
                        pass
                    else:
                        g = self.bot.get_guild(int(e["id"].split("-")[0]))
                        if g != None:
                            if g.id not in needs_sync:
                                needs_sync.update({
                                    g.id: g
                                })

            for _, v in needs_sync.items():
                try: await self.bot.tree.sync(guild=v)
                except Exception: pass


    def update_uses(
        self, 
        _id: str
    ) -> None:
        self.bot.used_tags += 1
        cur = self.db.tags.get(_id, "uses")
        if cur == None:
            self.db.tags.update(_id, "uses", 1)
        else:
            self.db.tags.update(_id, "uses", cur+1)


    def validate_name(
        self,
        name: str
    ) -> bool:
        for c in name:
            if c == "-" or c == "_":
                pass
            else:
                if re.compile(r"^[a-zA-Z]+$").match(c) or c.isdigit():
                    pass
                else:
                    return False
        return True


    async def get_tags(
        self,
        guild: discord.Guild,
        raw: dict
    ) -> dict:
        pre_cached = self._cached_from_api.get(guild.id, [])
        for e in raw:
            if e not in pre_cached:
                re_cache = await self.bot.tree.fetch_commands(guild=guild)
                self._cached_from_api.update({
                    guild.id: {x.name: x.id for x in re_cache}
                })
                return self._cached_from_api[guild.id]
        return self._cached_from_api[guild.id]

    
    _commands = discord.app_commands.Group(
        name="commands",
        description="📝 Manage custom slash commands",
        default_permissions=discord.Permissions(manage_messages=True)
    )
    @_commands.command(
        name="list",
        description="📝 Shows a list of all custom commands"
    )
    async def custom_commands(
        self, 
        ctx: discord.Interaction
    ) -> None:
        """
        commands_show_help
        examples:
        -commands list
        """
        if ctx.guild.id in self._tags:
            tags = await self.get_tags(ctx.guild, self._tags[ctx.guild.id])
            if len(tags) > 0:
                e = Embed(
                    ctx,
                    title="Custom Slash Commands",
                    description="{}".format(", ".join([f"</{name}:{cid}>" for name, cid in tags.items()]))
                )
                await ctx.response.send_message(embed=e)
            else:
                await ctx.response.send_message(embed=E(self.locale.t(ctx.guild, "no_tags", _emote="NO"), 0))
        else:
            await ctx.response.send_message(embed=E(self.locale.t(ctx.guild, "no_tags", _emote="NO"), 0))

    
    @_commands.command(
        name="add",
        description="✅ Creates a new custom slash command"
    )
    @discord.app_commands.default_permissions(manage_messages=True)
    async def addcom(
        self, 
        ctx: discord.Interaction
    ) -> None:
        """
        commands_add_help
        examples:
        -commands add
        """
        async def callback(
            i: discord.Interaction
        ) -> None:
            name, content, description = self.bot.extract_args(i, "name", "content", "description")

            if len(name) > 30: return await i.response.send_message(embed=E(self.locale.t(i.guild, "name_too_long", _emote="NO"), 0))
            if len(content) > 1900: return await i.response.send_message(embed=E(self.locale.t(i.guild, "content_too_long", _emote="NO"), 0))
            if len(description) > 50: return await i.response.send_message(embed=E(self.locale.t(i.guild, "description_too_long", _emote="NO"), 0))

            if self.validate_name(name.lower()) == False:
                return await i.response.send_message(embed=E(self.locale.t(i.guild, "invalid_name", _emote="NO"), 0))

            if len(self._tags.get(i.guild_id, [])) > 40:
                return await i.response.send_message(embed=E(self.locale.t(i.guild, "max_commands", _emote="NO"), 0))

            name = name.lower()
            for p in [
                self.bot.get_plugin(x) for x in [
                    "ConfigPlugin",
                    "AutomodPlugin",
                    "ModerationPlugin",
                    "UtilityPlugin",
                    "TagsPlugin",
                    "CasesPlugin",
                    "ReactionRolesPlugin",
                    "FilterPlugin"
                ]
            ]:
                if p != None:
                    for cmd in p.__cog_app_commands__:
                        if cmd.qualified_name.lower() == name:
                            return await i.response.send_message(embed=E(self.locale.t(i.guild, "tag_has_cmd_name", _emote="NO"), 0))

            if i.guild.id in self._tags:
                if name in self._tags[i.guild.id]:
                    return await i.response.send_message(embed=E(self.locale.t(i.guild, "tag_alr_exists", _emote="NO"), 0))

            r = self.add_tag(i, name, content, description, False)
            if r != None:
                await i.response.send_message(embed=E(self.locale.t(i.guild, "fail", _emote="NO", exc=r), 0))
            else:
                await self.bot.tree.sync(guild=i.guild)
                await i.response.send_message(embed=E(self.locale.t(i.guild, "tag_added", _emote="YES", tag=name), 1))

        modal = CommandCreateModal(self.bot, "Create Slash Command", callback)
        await ctx.response.send_modal(modal)


    @_commands.command(
        name="delete",
        description="❌ Deletes the given custom slash command"
    )
    @discord.app_commands.describe(
        name="Name of the custom command",
    )
    @discord.app_commands.default_permissions(manage_messages=True)
    async def delcom(
        self, 
        ctx: discord.Interaction, 
        name: str
    ) -> None:
        """
        commands_delete_help
        examples:
        -commands delete test_command
        """
        name = name.lower()
        if ctx.guild.id in self._tags:
            if not name in self._tags[ctx.guild.id]:
                await ctx.response.send_message(embed=E(self.locale.t(ctx.guild, "tag_doesnt_exists", _emote="NO"), 0))
            else:
                r = self.remove_tag(ctx.guild, name)
                if r != None:
                    await ctx.response.send_message(embed=E(self.locale.t(ctx.guild, "fail", _emote="NO", exc=r), 0))
                else:
                    await self.bot.tree.sync(guild=ctx.guild)
                    await ctx.response.send_message(embed=E(self.locale.t(ctx.guild, "tag_removed", _emote="YES"), 1))
        else:
            await ctx.response.send_message(embed=E(self.locale.t(ctx.guild, "no_tags", _emote="NO"), 0))


    @_commands.command(
        name="edit",
        description="🔀 Edits an existing custom slash command"
    )
    @discord.app_commands.describe(
        name="Name of the custom command",
        content="Content of the output",
        ephemeral="Whether the response should be ephemeral, meaning only the user can see it"
    )
    @discord.app_commands.default_permissions(manage_messages=True)
    async def editcom(
        self, 
        ctx: discord.Interaction, 
        name: str, 
        content: str,
        ephemeral: Literal[
            "True",
            "False"
        ] = None
    ) -> None:
        """
        commands_edit_help
        examples:
        -commands edit test_cmd This is the new content
        """
        if len(content) > 1900:
            return await ctx.response.send_message(embed=E(self.locale.t(ctx.guild, "content_too_long", _emote="NO"), 0))

        name = name.lower()
        if ctx.guild.id in self._tags:
            if not name in self._tags[ctx.guild.id]:
                await ctx.response.send_message(embed=E(self.locale.t(ctx.guild, "tag_doesnt_exists", _emote="NO"), 0))
            else:
                if ephemeral == None:
                    ephemeral = self._tags[ctx.guild.id][name].get("ephemeral", False)
                else:
                    if ephemeral == "True":
                        ephemeral = True
                    else:
                        ephemeral = False
                
                self.update_tag(ctx, name, content, ephemeral)
                await ctx.response.send_message(embed=E(self.locale.t(ctx.guild, "tag_updated", _emote="YES"), 1))
        else:
            await ctx.response.send_message(embed=E(self.locale.t(ctx.guild, "no_tags", _emote="NO"), 0))


    @_commands.command(
        name="info",
        description="📌 Shows some info about a custom slash command"
    )
    @discord.app_commands.describe(
        name="Name of the custom command",
    )
    @discord.app_commands.default_permissions(manage_messages=True)
    async def infocom(
        self, 
        ctx: discord.Interaction, 
        name: str
    ) -> None:
        """
        commands_info_help
        examples:
        -commands info test_cmd
        """
        name = name.lower()
        if ctx.guild.id in self._tags:
            if not name in self._tags[ctx.guild.id]:
                await ctx.response.send_message(embed=E(self.locale.t(ctx.guild, "tag_doesnt_exists", _emote="NO"), 0))
            else:
                data = Object(self.db.tags.get_doc(f"{ctx.guild.id}-{name}"))
                y = self.bot.emotes.get("YES")
                n = self.bot.emotes.get("NO")

                e = Embed(
                    ctx,
                    title=f"/{name}"
                )
                e.add_fields([
                    {
                        "name": "**__Content__**",
                        "value": f"```\n{data.content}\n```",
                        "inline": False
                    },
                    {
                        "name": "**__Description__**",
                        "value": f"```\n{data.description}\n```",
                        "inline": False
                    },
                    {
                        "name": "**__Ephemeral__**",
                        "value": f"{y if data.ephemeral == True else n}",
                        "inline": True
                    },
                    e.blank_field(True, 6),
                    {
                        "name": "**__Uses__**",
                        "value": f"{data.uses}",
                        "inline": True
                    },
                    {
                        "name": "**__Creator__**",
                        "value": f"<@{data.author}> \n(<t:{round(data.created.timestamp())}>)",
                        "inline": True
                    }
                ])
                if data.edited != None:
                    e.add_fields([
                        e.blank_field(True),
                        {
                            "name": "**__Editor__**",
                            "value": f"<@{data.editor}> \n(<t:{round(data.edited.timestamp())}>)",
                            "inline": True
                        }
                    ])

                await ctx.response.send_message(embed=e)
        else:
            await ctx.response.send_message(embed=E(self.locale.t(ctx.guild, "no_tags", _emote="NO"), 0))


async def setup(
    bot: ShardedBotInstance
) -> None: await bot.register_plugin(TagsPlugin(bot))