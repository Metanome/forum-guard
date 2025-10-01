import discord
from discord.ext import commands
import logging

from utils import database_handler as db
from utils import embed_factory

class LifecycleCog(commands.Cog):
    """Handles thread lifecycle management including auto-archiving solved threads."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def can_mark_solved(self, user: discord.Member, guild_id: int) -> bool:
        """Check if user has permission to mark threads as solved (must have support role)."""
        config = await db.get_guild_config(guild_id)
        if not config or not config.get('support_roles'):
            return False
        
        user_role_ids = {role.id for role in user.roles}
        support_role_ids = set(config['support_roles'])
        
        return not support_role_ids.isdisjoint(user_role_ids)

    async def get_thread_permissions(self, thread: discord.Thread) -> tuple[bool, bool]:
        """Returns (can_archive, can_manage) permissions for the bot in the thread."""
        permissions = thread.permissions_for(thread.guild.me)
        can_archive = permissions.manage_threads
        can_manage = permissions.manage_messages and permissions.send_messages
        return can_archive, can_manage

    async def archive_thread(self, thread: discord.Thread, user: discord.Member):
        """Archives and locks a thread, posting a closure message."""
        can_archive, can_manage = await self.get_thread_permissions(thread)
        
        if not can_archive:
            logging.error(f"Cannot archive thread {thread.id} - missing Manage Threads permission")
            return False
        
        try:
            # Post closure message if we can
            if can_manage:
                embed = embed_factory.thread_closed_embed(user)
                await thread.send(embed=embed)
            
            # Archive and lock the thread
            await thread.edit(archived=True, locked=True)
            logging.info(f"Archived and locked thread '{thread.name}' ({thread.id}) marked as solved by {user}")
            return True
            
        except discord.Forbidden:
            logging.error(f"Failed to archive thread {thread.id} - forbidden")
            return False
        except Exception as e:
            logging.error(f"Error archiving thread {thread.id}: {e}")
            return False

    async def unarchive_thread(self, thread: discord.Thread):
        """Unarchives and unlocks a thread."""
        can_archive, can_manage = await self.get_thread_permissions(thread)
        
        if not can_archive:
            logging.error(f"Cannot unarchive thread {thread.id} - missing Manage Threads permission")
            return False
        
        try:
            # Unarchive and unlock the thread
            await thread.edit(archived=False, locked=False)
            
            # Post reopening message if we can
            if can_manage:
                embed = embed_factory.thread_reopened_embed()
                await thread.send(embed=embed)
            
            logging.info(f"Unarchived and unlocked thread '{thread.name}' ({thread.id})")
            return True
            
        except discord.Forbidden:
            logging.error(f"Failed to unarchive thread {thread.id} - forbidden")
            return False
        except Exception as e:
            logging.error(f"Error unarchiving thread {thread.id}: {e}")
            return False

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        """Handles thread updates, specifically tag changes for solution management."""
        # Only process threads in monitored forums
        config = await db.get_guild_config(after.guild.id)
        if not config or not config.get('monitored_channels'):
            return
        
        if after.parent_id not in config['monitored_channels']:
            return
        
        # Get solution tags for this forum
        solution_tag_ids = await db.get_forum_solution_tags(after.guild.id, after.parent_id)
        if not solution_tag_ids:
            return  # No solution tags configured for this forum
        
        # Check for tag changes
        before_tag_ids = {tag.id for tag in before.applied_tags}
        after_tag_ids = {tag.id for tag in after.applied_tags}
        
        # Check if a solution tag was added
        added_tags = after_tag_ids - before_tag_ids
        solution_tags_added = added_tags.intersection(solution_tag_ids)
        
        # Check if a solution tag was removed
        removed_tags = before_tag_ids - after_tag_ids
        solution_tags_removed = removed_tags.intersection(solution_tag_ids)
        
        if solution_tags_added:
            # Thread was marked as solved - mark it as managed and archive
            await db.add_managed_solution_thread(after.id, "tag_added")
            # We need to find who made this change - this is tricky with thread updates
            # For now, we'll use the bot user, but this could be enhanced with audit logs
            await self.archive_thread(after, after.guild.me)
            
        elif solution_tags_removed:
            # Thread was unmarked as solved - only respond if we were managing it
            if await db.is_thread_managed(after.id):
                await self.unarchive_thread(after)
                # Remove from managed threads since it's no longer solved
                await db.remove_managed_solution_thread(after.id)

async def setup(bot: commands.Bot):
    await bot.add_cog(LifecycleCog(bot))