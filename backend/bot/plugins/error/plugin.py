# type: ignore

import discord
from discord.ext import commands

import logging; log = logging.getLogger()
import traceback
from typing import TypeVar

from .. import AutoModPluginBlueprint, ShardedBotInstance
from ...types import Embed, E



T = TypeVar("T")


class PostParseError(commands.BadArgument):
    def __init__(self, type: T, error: Exception) -> None:
        super().__init__(None)
        self.type = type
        self.error = error


class ErrorPlugin(AutoModPluginBlueprint):
    """Plugin to handle command/event errors"""
    def __init__(self, bot: ShardedBotInstance) -> None:
        super().__init__(bot)


    @AutoModPluginBlueprint.listener()
    async def on_command_error(self, ctx: discord.Interaction, error: Exception) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.NotOwner):
            await ctx.send(f"{self.bot.emotes.get('NO')} You can't use this command")
        elif isinstance(error, commands.MissingPermissions):
            perms = ", ".join([f"``{x.replace('_', ' ').title()}``" for x in error.missing_permissions]) 
            e = Embed(
                ctx,
                description=self.locale.t(ctx.guild, "missing_user_perms", _emote="LOCK", perms=perms)
            )
            await ctx.response.send_message(embed=e)
        
        elif isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join([f"``{x}``" for x in error.missing_permissions])
            e = Embed(
                ctx,
                description=self.locale.t(ctx.guild, "missing_bot_perms", _emote="LOCK", perms=perms)
            )
            await ctx.response.send_message(embed=e)
        
        elif isinstance(error, commands.CheckFailure):
            if len(ctx.command.checks) < 1:
                e = Embed(
                    ctx,
                    description=self.locale.t(ctx.guild, "check_fail", _emote="LOCK")
                )
                await ctx.response.send_message(embed=e)
            else:
                await ctx.command.checks[0](ctx) # this raises a 'commands.MissingPermissions'
        
        elif isinstance(error, commands.CommandOnCooldown):
            e = Embed(
                ctx,
                description=self.locale.t(
                    ctx.guild, 
                    "on_cooldown", 
                    _emote="NO", 
                    retry_after=round(error.retry_after), 
                    plural="" if round(error.retry_after) == 1 else "s"
                )
            )
            await ctx.response.send_message(embed=e)
        
        elif isinstance(error.__cause__, discord.Forbidden):
            e = Embed(
                ctx,
                description=self.locale.t(ctx.guild, "forbidden", _emote="NO", exc=error)
            )
            await ctx.response.send_message(embed=e)

        elif isinstance(error, commands.MissingRequiredArgument):
            param = list(ctx.command._params.values())[min(len(ctx.data["options"]), len(ctx.command._params)) - 1]
            usage = f"""{
                "/"
            }{
                ctx.command.qualified_name
            } {
                " ".join(
                    [
                        *[f"<{x}>" for x, y in ctx.command._params.items() if y.required],
                        *[f"[{x}]" for x, y in ctx.command._params.items() if not y.required]
                    ]
                )
            }"""
            info = f"/help {ctx.command.qualified_name}"

            e = Embed(
                ctx,
                description=self.locale.t(ctx.guild, "missing_arg", _emote="NO", param=param._name)
            )
            e.add_fields([
                {
                    "name": "❯ __Usage__",
                    "value": f"``{usage}``"
                },
                {
                    "name": "❯ __Info__",
                    "value": f"``{info}``"
                }
            ])
            await ctx.response.send_message(embed=e)
        
        elif isinstance(error, PostParseError):
            usage = f"""{
                "/"
            }{
                ctx.command.qualified_name
            } {
                " ".join(
                    [
                        *[f"<{x}>" for x, y in ctx.command._params.items() if y.required],
                        *[f"[{x}]" for x, y in ctx.command._params.items() if not y.required]
                    ]
                )
            }"""
            info = f"/help {ctx.command.qualified_name}"

            e = Embed(
                ctx,
                description=self.locale.t(ctx.guild, "bad_arg", _emote="NO", param=error.type, error=error.error)
            )
            e.add_fields([
                {
                    "name": "❯ __Usage__",
                    "value": f"``{usage}``"
                },
                {
                    "name": "❯ __Info__",
                    "value": f"``{info}``"
                }
            ])
            await ctx.response.send_message(embed=e)

        elif isinstance(error, commands.BadArgument) or isinstance(error, commands.BadUnionArgument):
            usage = f"""{
                "/"
            }{
                ctx.command.qualified_name
            } {
                " ".join(
                    [
                        *[f"<{x}>" for x, y in ctx.command._params.items() if y.required],
                        *[f"[{x}]" for x, y in ctx.command._params.items() if not y.required]
                    ]
                )
            }"""
            info = f"/help {ctx.command.qualified_name}"

            e = Embed(ctx)
            e.add_fields([
                {
                    "name": "❯ __Usage__",
                    "value": f"``{usage}``"
                },
                {
                    "name": "❯ __Info__",
                    "value": f"``{info}``"
                }
            ])
            try:
                param = list(ctx.command._params.values())[min(len(ctx.data["options"]), len(ctx.command._params)) - 1]
            except IndexError:
                e.description = self.locale.t(ctx.guild, "bad_arg_no_param", _emote="NO", error=error)
            else:
                e.description = self.locale.t(ctx.guild, "bad_arg", _emote="NO", param=param.name, error=error)
            finally:
                await ctx.response.send_message(embed=e)

        else:
            log.error(f"[Commands] Error in command {ctx.command} - {''.join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__))}", extra={"loc": f"Shard {ctx.guild.shard_id}"})

            try:
                await ctx.response.send_message(embed=E(self.bot.locale.t(ctx.guild, "fail", _emote="NO", exc=error), 0), ephemeral=True)
            except Exception:
                pass
            finally:
                e = Embed(
                    ctx,
                    color=0xff6464,
                    title="Uncaught error",
                    description="```py\n{}\n```".format(("".join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__)))[:4000])
                )
                e.add_fields([
                    {
                        "name": "❯ __Command__",
                        "value": f"**•** {ctx.command.qualified_name}" if ctx.command != None else "Unknown",
                        "inline": True
                    },
                    {
                        "name": "❯ __Location__",
                        "value": f"**•** {ctx.guild.name} ({ctx.guild.id})" if ctx.guild != None else "Unknown",
                        "inline": True
                    }
                ])

                if self.bot.error_log == None:
                    try:
                        cid = int(self.bot.config.error_channel)
                    except (
                        AttributeError, 
                        ValueError
                    ):
                        return
                    else:
                        try:
                            clog = await self.bot.fetch_channel(cid)
                        except discord.NotFound:
                            return
                        else:
                            if clog != None:
                                try:
                                    await clog.send(embed=e)
                                except Exception:
                                    return
                                else:
                                    self.bot.error_log = clog
                else:
                    try:
                        await self.bot.error_log.send(embed=e)
                    except Exception:
                        self.bot.error_log = None


async def setup(bot: ShardedBotInstance) -> None: 
    await bot.register_plugin(ErrorPlugin(bot))