
import discord
from discord.ext import commands, tasks
import logging
from collections import defaultdict
import time

from utils import database_handler as db
from utils import embed_factory

CACHE_EXPIRY_SECONDS = 300  # 5 minutes

class ModerationCog(commands.Cog):
    """Handles the core moderation logic of the bot."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_cache = defaultdict(lambda: {'expiry': 0, 'data': None})
        self.cleanup_cache.start()

    def clear_guild_cache(self, guild_id: int):
        """Clears the configuration cache for a specific guild."""
        if guild_id in self.guild_cache:
            del self.guild_cache[guild_id]
            logging.info(f"Cache cleared for guild ID: {guild_id}")

    async def get_cached_config(self, guild_id: int) -> dict:
        """Retrieves guild configuration from cache or database."""
        cache_entry = self.guild_cache[guild_id]
        if cache_entry['expiry'] > time.time():
            return cache_entry['data']

        config = await db.get_guild_config(guild_id)
        if config:
            self.guild_cache[guild_id] = {'expiry': time.time() + CACHE_EXPIRY_SECONDS, 'data': config}
            return config
        return None

    @tasks.loop(minutes=10)
    async def cleanup_cache(self):
        """Periodically cleans up expired entries from the cache."""
        current_time = time.time()
        expired_guilds = [gid for gid, data in self.guild_cache.items() if data['expiry'] <= current_time]
        for guild_id in expired_guilds:
            del self.guild_cache[guild_id]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 1. Pre-flight Checks
        if message.author.bot or not message.guild or not isinstance(message.channel, discord.Thread):
            return

        # 2. Configuration Cache & Lookup
        config = await self.get_cached_config(message.guild.id)
        if not config or not config.get('monitored_channels'):
            return

        thread: discord.Thread = message.channel
        if thread.parent_id not in config['monitored_channels']:
            return

        # 3. Permission Validation
        # Condition 1: Author is the thread owner (OP)
        if message.author.id == thread.owner_id:
            return

        # Condition 2: Author has a designated support role
        support_role_ids = set(config.get('support_roles', []))
        author_role_ids = {role.id for role in message.author.roles}
        if not support_role_ids.isdisjoint(author_role_ids):
            return

        # 4. Execution
        try:
            await message.delete()
            logging.info(f"Deleted message from {message.author} ({message.author.id}) in thread #{thread.name} ({thread.id}). Content: \"{message.content}\"\n")
        except discord.Forbidden:
            logging.error(f"Failed to delete message in {thread.id}. Missing Permissions.")
            return # Can't delete, so no point trying to notify
        except discord.NotFound:
            return # Message was already deleted, do nothing

        if config.get('dm_notifications_enabled', True):
            try:
                embed = embed_factory.dm_notification_embed(thread)
                await message.author.send(embed=embed)
            except discord.Forbidden:
                logging.warning(f"Could not send DM to {message.author} ({message.author.id}). DMs are disabled.")
            except Exception as e:
                logging.error(f"An unexpected error occurred when trying to DM {message.author}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))