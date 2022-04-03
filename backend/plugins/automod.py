import discord
from discord.ext import commands

import re
from toolbox import S as Object
from urllib.parse import urlparse
import logging; log = logging.getLogger()

from . import AutoModPlugin
from .processor import ActionProcessor, LogProcessor, DMProcessor



INVITE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord(?:\.| |\[?\(?\"?'?dot'?\"?\)?\]?)?(?:gg|io|me|li)|discord(?:app)?\.com/invite)/+((?:(?!https?)[\w\d-])+)"
)
LINK_RE = re.compile(
    r"((?:https?://)[a-z0-9]+(?:[-._][a-z0-9]+)*\.[a-z]{2,5}(?::[0-9]{1,5})?(?:/[^ \n<>]*)?)", 
    re.IGNORECASE
)
MENTION_RE = re.compile(
    r"<@[!&]?\\d+>"
)
ALLOWED_FILE_FORMATS = [
    # plain text/markdown
    "txt",
    "md",

    # image
    "jpg",
    "jpeg",
    "png",
    "webp",
    "gif",

    # video
    "mov",
    "mp4",
    "flv",
    "mkv",

    # audio
    "mp3",
    "wav",
    "m4a"
]
ZALGO = [
    u'\u030d',
    u'\u030e',
    u'\u0304',
    u'\u0305',
    u'\u033f',
    u'\u0311',
    u'\u0306',
    u'\u0310',
    u'\u0352',
    u'\u0357',
    u'\u0351',
    u'\u0307',
    u'\u0308',
    u'\u030a',
    u'\u0342',
    u'\u0343',
    u'\u0344',
    u'\u034a',
    u'\u034b',
    u'\u034c',
    u'\u0303',
    u'\u0302',
    u'\u030c',
    u'\u0350',
    u'\u0300',
    u'\u030b',
    u'\u030f',
    u'\u0312',
    u'\u0313',
    u'\u0314',
    u'\u033d',
    u'\u0309',
    u'\u0363',
    u'\u0364',
    u'\u0365',
    u'\u0366',
    u'\u0367',
    u'\u0368',
    u'\u0369',
    u'\u036a',
    u'\u036b',
    u'\u036c',
    u'\u036d',
    u'\u036e',
    u'\u036f',
    u'\u033e',
    u'\u035b',
    u'\u0346',
    u'\u031a',
    u'\u0315',
    u'\u031b',
    u'\u0340',
    u'\u0341',
    u'\u0358',
    u'\u0321',
    u'\u0322',
    u'\u0327',
    u'\u0328',
    u'\u0334',
    u'\u0335',
    u'\u0336',
    u'\u034f',
    u'\u035c',
    u'\u035d',
    u'\u035e',
    u'\u035f',
    u'\u0360',
    u'\u0362',
    u'\u0338',
    u'\u0337',
    u'\u0361',
    u'\u0489',
    u'\u0316',
    u'\u0317',
    u'\u0318',
    u'\u0319',
    u'\u031c',
    u'\u031d',
    u'\u031e',
    u'\u031f',
    u'\u0320',
    u'\u0324',
    u'\u0325',
    u'\u0326',
    u'\u0329',
    u'\u032a',
    u'\u032b',
    u'\u032c',
    u'\u032d',
    u'\u032e',
    u'\u032f',
    u'\u0330',
    u'\u0331',
    u'\u0332',
    u'\u0333',
    u'\u0339',
    u'\u033a',
    u'\u033b',
    u'\u033c',
    u'\u0345',
    u'\u0347',
    u'\u0348',
    u'\u0349',
    u'\u034d',
    u'\u034e',
    u'\u0353',
    u'\u0354',
    u'\u0355',
    u'\u0356',
    u'\u0359',
    u'\u035a',
    u'\u0323',
]
ZALGO_RE = re.compile(u'|'.join(ZALGO))


LOG_DATA = {
    "invites": {
        "rule": "Anti-Invites"
    },
    "links": {
        "rule": "Anti-Links"
    },
    "files": {
        "rule": "Anti-Files"
    },
    "zalgo": {
        "rule": "Anti-Zalgo"
    },
    "regex": {
        "rule": "Regex-Filter"
    }
}


class AutomodPlugin(AutoModPlugin):
    """Plugin for enforcing automoderator rules"""
    def __init__(self, bot):
        super().__init__(bot)
        self.action_processor = ActionProcessor(bot)
        self.log_processor = LogProcessor(bot)
        self.dm_processor = DMProcessor(bot)


    def can_act(self, guild, mod, target):
        mod = guild.get_member(mod.id)
        target = guild.get_member(target.id)
        if mod == None or target == None: return False

        rid = self.bot.db.configs.get(guild.id, "mod_role")
        if rid != "":
            r = guild.get_role(int(rid))
            if r != None:
                if r in target.roles:
                    return True

        return mod.id != target.id \
            and target.id != guild.owner.id \
            and (target.guild_permissions.kick_members == False or target.guild_permissions.kick_members == False)


    def parse_filter(self, words):
        normal = []
        wildcards = []

        for i in words:
            i = i.replace("*", "", (i.count("*") - 1)) # remove multiple wildcards
            if i.endswith("*"):
                wildcards.append(i.replace("*", ".+"))
            else:
                normal.append(i)

        try:
            return re.compile(r"|".join([*normal, *wildcards]))
        except Exception:
            return None


    def parse_regex(self, regex):
        try:
            parsed = re.compile(regex)
        except Exception:
            return None
        else:
            return parsed


    async def delete_msg(self, rule, found, msg, warns, reason, pattern_or_filter=None, pattern=None):
        try:
            await msg.delete()
        except (discord.NotFound, discord.Forbidden):
            pass
        else:
            self.bot.ignore_for_events.append(msg.id)
        finally:
            if warns > 0:
                await self.action_processor.execute(
                    msg, 
                    msg.guild.me,
                    msg.author,
                    warns, 
                    reason
                )
            else:
                data = Object(LOG_DATA[rule])

                self.dm_processor.execute(
                    msg,
                    "automod_rule_triggered",
                    msg.author,
                    **{
                        "guild_name": msg.guild.name,
                        "rule": data.rule,
                        "_emote": "SHIELD"
                    }
                )
                if rule not in ["filter", "regex"]:
                    await self.log_processor.execute(
                        msg.guild,
                        "automod_rule_triggered",
                        **{
                            "rule": data.rule,
                            "found": found,
                            "user_id": msg.author.id,
                            "user": msg.author,
                            "mod_id": msg.guild.me.id,
                            "mod": msg.guild.me
                        }
                    )
                else:
                    await self.log_processor.execute(
                        msg.guild,
                        f"{rule}_triggered",
                        **{
                            "pattern": f"{pattern_or_filter} (``{pattern}``)",
                            "found": found,
                            "user_id": msg.author.id,
                            "user": msg.author,
                            "mod_id": msg.guild.me.id,
                            "mod": msg.guild.me
                        }
                    )


    async def enforce_rules(self, msg):
        content = msg.content.replace("\\", "")

        config = Object(self.db.configs.get_doc(msg.guild.id))
        rules = config.automod
        filters = config.filters
        regexes = config.regexes

        if len(rules) < 1: return

        if len(filters) > 0:
            for name in filters:
                f = filters[name]
                parsed = self.parse_filter(f["words"])
                if parsed != None:
                    found = parsed.findall(content)
                    if found:
                        return await self.delete_msg(
                            "filter",
                            ", ".join(found),
                            msg, 
                            int(f["warns"]), 
                            f"Triggered filter '{name}' with '{', '.join(found)}'"
                        )
        
        if len(regexes) > 0:
            for name, data in regexes.items():
                parsed = self.parse_regex(data["regex"])
                if parsed != None:
                    found = parsed.findall(content)
                    if found:
                        return await self.delete_msg(
                            "regex",
                            ", ".join(found),
                            msg, 
                            int(data["warns"]), 
                            f"Triggered regex '{name}' with '{', '.join(found)}'",
                            name,
                            data["regex"]
                        )
        
        if hasattr(rules, "invites"):
            found = INVITE_RE.findall(content)
            if found:
                for inv in found:
                    try:
                        invite: discord.Invite = await self.bot.fetch_invite(inv)
                    except discord.NotFound:
                        return await self.delete_msg(
                            "invites",
                            inv,
                            msg, 
                            rules.invites.warns, 
                            f"Advertising ({inv})"
                        )
                    if invite.guild == None:
                        return await self.delete_msg(
                            "invites",
                            inv,
                            msg, 
                            rules.invites.warns, 
                            f"Advertising ({inv})"
                        )
                    else:
                        if invite.guild == None \
                            or (
                                not invite.guild.id in config.allowed_invites \
                                and invite.guild.id != msg.guild.id
                            ):
                                return await self.delete_msg(
                                    "invites",
                                    inv,
                                    msg, 
                                    rules.invites.warns, 
                                    f"Advertising ({inv})"
                                )
        
        if hasattr(rules, "links"):
            found = LINK_RE.findall(content)
            if found:
                for link in found:
                    url = urlparse(link)
                    if url.hostname in config.black_listed_links:
                        return await self.delete_msg(
                            "links", 
                            url.hostname,
                            msg, 
                            rules.links.warns, 
                            f"Forbidden link ({url.hostname})"
                        )

        if hasattr(rules, "files"):
            if len(msg.attachments) > 0:
                try:
                    forbidden = [
                        x.url.split(".")[-1] for x in msg.attachments \
                        if not x.url.split(".")[-1].lower() in ALLOWED_FILE_FORMATS
                    ]
                except Exception:
                    forbidden = []
                if len(forbidden) > 0:
                    return await self.delete_msg(
                        "files", 
                        ", ".join(forbidden), 
                        msg, 
                        rules.files.warns, 
                        f"Forbidden attachment type ({', '.join(forbidden)})"
                    )

        if hasattr(rules, "zalgo"):
            found = ZALGO_RE.search(content)
            if found:
                return await self.delete_msg(
                    "zalgo", 
                    found, 
                    msg, 
                    rules.zalgo.warns, 
                    "Zalgo found"
                )

        if hasattr(rules, "mentions"):
            found = len(MENTION_RE.findall(content))
            if found >= rules.mentions.threshold:
                return await self.delete_msg(
                    "mentions", 
                    found, 
                    msg, 
                    abs(rules.mentions.threshold - found), 
                    f"Spamming mentions ({found})"
                )
    

    @AutoModPlugin.listener()
    async def on_message(self, msg: discord.Message):
        if msg.guild == None: return
        if not msg.guild.chunked: await msg.guild.chunk(cache=True)
        if not self.can_act(msg.guild, msg.guild.me, msg.author): return

        await self.enforce_rules(msg)


    @AutoModPlugin.listener()
    async def on_message_edit(self, _, msg: discord.Message):
        if msg.guild == None: return
        if not msg.guild.chunked: await msg.guild.chunk(cache=True)
        if not self.can_act(msg.guild, msg.guild.me, msg.author): return

        await self.enforce_rules(msg)


async def setup(bot): await bot.register_plugin(AutomodPlugin(bot))
