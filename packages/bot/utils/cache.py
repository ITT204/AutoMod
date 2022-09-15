# type: ignore

import discord

from typing import Union



class MessageCache(object):
    def __init__(
        self
    ) -> None:
        self.__store = {}
        self._MAX_SIZE_PER_GUILD = 1500
        self._MAX_CACHE_SIZE = 30000


    def insert(
        self, 
        guild: discord.Guild, 
        msg: discord.Message
    ) -> None:
        if self.__len__() > self._MAX_CACHE_SIZE: self.flush()
        if not guild.id in self.__store:
            self.__store[guild.id] = {
                msg.id: msg
            }
        else:
            self.__store[guild.id].update(
                {
                    msg.id: msg
                }
            )
            if len(self.__store[guild.id]) > self._MAX_SIZE_PER_GUILD:
                self.__store[guild.id].popitem()


    def delete(
        self, 
        guild_id: int, 
        msg_id: int
    ) -> None:
        if guild_id in self.__store:
            if msg_id in self.__store[guild_id]:
                del self.__store[guild_id][msg_id]


    def update(
        self, 
        guild: discord.Guild, 
        msg: discord.Message
    ) -> None:
        if msg.id in self.__store[guild.id]:
            self.__store[guild.id].update(
                {
                    msg.id: msg
                }
            )


    def get(
        self, 
        guild: discord.Guild, 
        msg_id: int
    ) -> Union[
        None, 
        discord.Message
    ]:
        if not guild.id in self.__store: 
            return None
        else:
            return self.__store[guild.id].get(msg_id, None)


    def flush(
        self
    ) -> None:
        self.__store.clear()


    def __len__(
        self
    ) -> int:
        return sum([len(x) for _, x in self.__store.items()])