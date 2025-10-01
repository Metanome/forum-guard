import discord
from discord.ext import commands, tasks
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from utils import database_handler as db
from utils import embed_factory

class EscalationCog(commands.Cog):
    """Handles stale thread escalation with tier-based alerts."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_stale_threads.start()

    def cog_unload(self):
        self.check_stale_threads.cancel()

    async def is_monitored_thread(self, thread: discord.Thread) -> bool:
        """Check if the thread is in a monitored forum."""
        if not isinstance(thread, discord.Thread) or not thread.parent:
            return False
        
        config = await db.get_guild_config(thread.guild.id)
        if not config or not config.get('monitored_channels'):
            return False
        
        return thread.parent_id in config['monitored_channels']

    async def get_thread_from_id(self, guild: discord.Guild, thread_id: int) -> Optional[discord.Thread]:
        """Get a thread object from its ID."""
        try:
            # Try to get the thread directly
            thread = guild.get_thread(thread_id)
            if thread:
                return thread
            
            # If not found, try to fetch it
            thread = await self.bot.fetch_channel(thread_id)
            if isinstance(thread, discord.Thread):
                return thread
        except (discord.NotFound, discord.Forbidden):
            pass
        return None

    async def execute_tier_1_escalation(self, thread: discord.Thread, settings: dict):
        """Execute tier 1 escalation - ping support roles in thread."""
        try:
            role_id = settings['tier_1_role_id']
            guild = thread.guild
            role = guild.get_role(role_id)
            
            if not role:
                logging.warning(f"Tier 1 role {role_id} not found in guild {guild.id}")
                return False
            
            embed = discord.Embed(
                title="⏰ Thread Needs Attention - Tier 1",
                description=(
                    f"This thread has been waiting for a response for "
                    f"**{settings['tier_1_hours']} hours** without any support team replies.\\n\\n"
                    f"Please review and assist if needed."
                ),
                color=embed_factory.INFO_COLOR
            )
            embed.add_field(name="Thread", value=f"[{thread.name}]({thread.jump_url})", inline=False)
            embed.add_field(name="Created", value=f"<t:{int(thread.created_at.timestamp())}>", inline=True)
            embed.add_field(name="Last Activity", value=f"<t:{int(time.time())}>", inline=True)
            
            # Send role ping OUTSIDE the embed
            await thread.send(content=f"{role.mention}", embed=embed)
            await db.mark_escalation_tier_executed(thread.id, 1)
            
            logging.info(f"Executed tier 1 escalation for thread {thread.id}")
            return True
            
        except discord.Forbidden:
            logging.error(f"Cannot send tier 1 escalation in thread {thread.id} - missing permissions")
            return False
        except Exception as e:
            logging.error(f"Error executing tier 1 escalation for thread {thread.id}: {e}")
            return False

    async def execute_tier_2_escalation(self, thread: discord.Thread, settings: dict):
        """Execute tier 2 escalation - ping role in escalation channel."""
        try:
            role_id = settings['tier_2_role_id']
            channel_id = settings['escalation_channel_id']
            guild = thread.guild
            
            role = guild.get_role(role_id)
            channel = guild.get_channel(channel_id)
            
            if not role:
                logging.warning(f"Tier 2 role {role_id} not found in guild {guild.id}")
                return False
            
            if not channel:
                logging.warning(f"Escalation channel {channel_id} not found in guild {guild.id}")
                return False
            
            embed = discord.Embed(
                title="🚨 Thread Escalation - Tier 2",
                description=(
                    f"**Urgent:** Thread requires immediate attention!\\n\\n"
                    f"This thread has been waiting for "
                    f"**{settings['tier_2_hours']} hours** without support team responses."
                ),
                color=embed_factory.ERROR_COLOR
            )
            
            embed.add_field(name="Thread", value=f"[{thread.name}]({thread.jump_url})", inline=False)
            embed.add_field(name="Forum", value=thread.parent.mention if thread.parent else "Unknown", inline=True)
            embed.add_field(name="Author", value=thread.owner.mention if thread.owner else "Unknown", inline=True)
            embed.add_field(name="Created", value=f"<t:{int(thread.created_at.timestamp())}>", inline=True)
            
            # Send role ping OUTSIDE the embed for proper notifications
            await channel.send(content=f"{role.mention}", embed=embed)
            await db.mark_escalation_tier_executed(thread.id, 2)
            
            logging.info(f"Executed tier 2 escalation for thread {thread.id}")
            return True
            
        except discord.Forbidden:
            logging.error(f"Cannot send tier 2 escalation for thread {thread.id} - missing permissions")
            return False
        except Exception as e:
            logging.error(f"Error executing tier 2 escalation for thread {thread.id}: {e}")
            return False

    @tasks.loop(hours=1)  # Check every hour
    async def check_stale_threads(self):
        """Background task to check for stale threads and execute escalations."""
        try:
            current_time = time.time()
            
            # Get all guilds that might need escalation
            for guild in self.bot.guilds:
                # Get guild-wide escalation settings
                escalation_settings = await db.get_guild_escalation_settings(guild.id)
                
                if not escalation_settings or not escalation_settings.get('enabled'):
                    continue
                
                # Get monitored forums for this guild
                config = await db.get_guild_config(guild.id)
                if not config or not config.get('monitored_channels'):
                    continue
                
                # Check each monitored forum
                for forum_id in config['monitored_channels']:
                    forum = guild.get_channel(forum_id)
                    
                    if not forum or not isinstance(forum, discord.ForumChannel):
                        continue
                    
                    # Check each active thread in the forum
                    for thread in forum.threads:
                        if thread.archived or thread.locked:
                            continue
                        
                        await self.check_thread_for_escalation(thread, escalation_settings, current_time)
                        
        except Exception as e:
            logging.error(f"Error in stale thread check task: {e}")

    async def check_thread_for_escalation(self, thread: discord.Thread, settings: dict, current_time: float):
        """Check a specific thread for escalation needs."""
        try:
            # Get thread escalation state
            state = await db.get_thread_escalation_state(thread.id)
            
            # If no state exists (thread reset or first time), create default state
            if not state:
                state = {'tier_1_executed': False, 'tier_2_executed': False}
            
            # Check if support has ever replied to this thread
            has_support_reply = await self.has_support_ever_replied(thread, settings)
            
            if has_support_reply:
                return  # Support has replied, no escalation needed
            
            # Since support hasn't replied, escalate based on thread age
            thread_age_hours = (current_time - thread.created_at.timestamp()) / 3600
            
            # Check tier 2 escalation (higher priority)
            if (not state.get('tier_2_executed', False) and 
                thread_age_hours >= settings['tier_2_hours']):
                logging.info(f"Escalating thread {thread.id} to tier 2 (age: {thread_age_hours:.1f}h)")
                await self.execute_tier_2_escalation(thread, settings)
            
            # Check tier 1 escalation
            elif (not state.get('tier_1_executed', False) and 
                  thread_age_hours >= settings['tier_1_hours']):
                logging.info(f"Escalating thread {thread.id} to tier 1 (age: {thread_age_hours:.1f}h)")
                await self.execute_tier_1_escalation(thread, settings)
                
        except Exception as e:
            logging.error(f"Error checking thread {thread.id} for escalation: {e}")

    async def has_support_ever_replied(self, thread: discord.Thread, settings: dict) -> bool:
        """Check if support has ever replied to this thread."""
        try:
            # Get support roles for permission checking
            config = await db.get_guild_config(thread.guild.id)
            support_role_ids = set(config.get('support_roles', [])) if config else set()
            
            if not support_role_ids:
                return False  # No support roles configured
            
            async for message in thread.history(limit=None):  # Check all messages
                # Skip OP and bot messages
                if message.author.id == thread.owner_id or message.author.bot:
                    continue
                
                # Check if author has support role
                if hasattr(message.author, 'roles'):
                    author_role_ids = {role.id for role in message.author.roles}
                    if not support_role_ids.isdisjoint(author_role_ids):
                        return True  # Found support reply
            
            return False  # No support replies found
            
        except discord.Forbidden:
            logging.error(f"Cannot read history of thread {thread.id} - missing permissions")
            return False
        except discord.NotFound:
            logging.error(f"Thread {thread.id} not found - may have been deleted")
            return False
        except Exception as e:
            logging.error(f"Error checking support replies for thread {thread.id}: {e}")
            return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Track messages to reset escalation state when support replies."""
        if not isinstance(message.channel, discord.Thread):
            return
        
        thread = message.channel
        
        # Check if this is a monitored thread
        if not await self.is_monitored_thread(thread):
            return
        
        # Skip OP and bot messages
        if message.author.id == thread.owner_id or message.author.bot:
            return
        
        # Get support roles
        config = await db.get_guild_config(thread.guild.id)
        if not config:
            return
        
        support_role_ids = set(config.get('support_roles', []))
        
        # Check if message author has support role
        if hasattr(message.author, 'roles'):
            author_role_ids = {role.id for role in message.author.roles}
            is_support_member = not support_role_ids.isdisjoint(author_role_ids)
            
            if is_support_member:
                # Support member responded - reset escalation state completely
                await db.reset_thread_escalation_state(thread.id)

    @check_stale_threads.before_loop
    async def before_check_stale_threads(self):
        """Wait for bot to be ready before starting the task."""
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(EscalationCog(bot))
