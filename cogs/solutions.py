import discord
from discord.ext import commands
from discord import app_commands
import logging

from utils import database_handler as db
from utils import embed_factory

class SolutionsCog(commands.Cog):
    """Handles solution marking and pinning functionality."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Add context menus to the bot
        self.ctx_menu_solution = app_commands.ContextMenu(
            name='Mark as Solution',
            callback=self.mark_as_solution,
        )
        self.ctx_menu_helpful = app_commands.ContextMenu(
            name='Mark as Helpful',
            callback=self.mark_as_helpful,
        )
        self.ctx_menu_unmark = app_commands.ContextMenu(
            name='Unmark Solution/Helpful',
            callback=self.unmark_solution,
        )
        
        self.bot.tree.add_command(self.ctx_menu_solution)
        self.bot.tree.add_command(self.ctx_menu_helpful)
        self.bot.tree.add_command(self.ctx_menu_unmark)

    async def cog_unload(self):
        """Remove context menus when cog is unloaded."""
        self.bot.tree.remove_command(self.ctx_menu_solution.name, type=discord.AppCommandType.message)
        self.bot.tree.remove_command(self.ctx_menu_helpful.name, type=discord.AppCommandType.message)
        self.bot.tree.remove_command(self.ctx_menu_unmark.name, type=discord.AppCommandType.message)

    async def can_mark_solutions(self, user: discord.Member, guild_id: int) -> bool:
        """Check if user has permission to mark solutions (must have support role)."""
        config = await db.get_guild_config(guild_id)
        if not config or not config.get('support_roles'):
            return False
        
        user_role_ids = {role.id for role in user.roles}
        support_role_ids = set(config['support_roles'])
        
        return not support_role_ids.isdisjoint(user_role_ids)

    async def is_monitored_thread(self, thread: discord.Thread) -> bool:
        """Check if the thread is in a monitored forum."""
        if not isinstance(thread, discord.Thread) or not thread.parent:
            return False
        
        config = await db.get_guild_config(thread.guild.id)
        if not config or not config.get('monitored_channels'):
            return False
        
        return thread.parent_id in config['monitored_channels']

    async def pin_solution_message(self, message: discord.Message) -> bool:
        """Pin a message and handle potential errors."""
        try:
            await message.pin(reason="Marked as solution by support team")
            return True
        except discord.HTTPException as e:
            if e.code == 30003:  # Too many pinned messages
                logging.warning(f"Cannot pin message {message.id} - too many pinned messages in channel")
                return False
            else:
                logging.error(f"Failed to pin message {message.id}: {e}")
                return False
        except discord.Forbidden:
            logging.error(f"Cannot pin message {message.id} - missing permissions")
            return False

    async def unpin_solution_message(self, message: discord.Message) -> bool:
        """Unpin a message and handle potential errors."""
        try:
            await message.unpin(reason="Solution unmarked by support team")
            return True
        except discord.HTTPException:
            logging.error(f"Failed to unpin message {message.id}")
            return False
        except discord.Forbidden:
            logging.error(f"Cannot unpin message {message.id} - missing permissions")
            return False

    async def suggest_thread_closure(self, thread: discord.Thread, solution_message: discord.Message):
        """Suggest to the OP that they can mark the thread as solved."""
        try:
            embed = embed_factory.solution_closure_suggestion_embed(solution_message)
            await thread.send(embed=embed)
        except discord.Forbidden:
            logging.warning(f"Cannot send closure suggestion in thread {thread.id} - missing permissions")
        except Exception as e:
            logging.error(f"Error sending closure suggestion in thread {thread.id}: {e}")

    async def mark_as_solution(self, interaction: discord.Interaction, message: discord.Message):
        """Mark a message as the solution to the thread."""
        await self._mark_solution(interaction, message, "solution", "Solution")

    async def mark_as_helpful(self, interaction: discord.Interaction, message: discord.Message):
        """Mark a message as helpful to the thread."""
        await self._mark_solution(interaction, message, "helpful", "Helpful")

    async def _mark_solution(self, interaction: discord.Interaction, message: discord.Message, category: str, display_name: str):
        """Internal method to handle solution marking."""
        # Check if user has permission
        if not await self.can_mark_solutions(interaction.user, interaction.guild_id):
            embed = embed_factory.error_embed("Permission Denied", 
                "Only support team members can mark solutions.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if message is in a monitored thread
        if not isinstance(message.channel, discord.Thread):
            embed = embed_factory.error_embed("Invalid Channel", 
                "Solutions can only be marked in forum threads.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        thread = message.channel
        if not await self.is_monitored_thread(thread):
            embed = embed_factory.error_embed("Not Monitored", 
                "This forum channel is not being monitored by ForumGuard.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if message is already marked as a solution
        existing_solutions = await db.get_thread_solutions(thread.id)
        if any(sol['message_id'] == message.id for sol in existing_solutions):
            embed = embed_factory.error_embed("Already Marked", 
                "This message is already marked as a solution.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Defer the response since we might take a while
        await interaction.response.defer(ephemeral=True)

        # Pin the message
        pinned = await self.pin_solution_message(message)
        
        # Add to database
        await db.add_thread_solution(thread.id, message.id, interaction.user.id, category)
        
        # Mark thread as managed by the bot if this is a full solution
        if category == "solution":
            await db.add_managed_solution_thread(thread.id, "context_menu")
        
        # Create success embed
        pin_status = "and pinned" if pinned else "(pinning failed - too many pins or missing permissions)"
        embed = embed_factory.success_embed(f"{display_name} Marked", 
            f"Message marked as {category} {pin_status}.\n\n"
            f"**Message:** {message.content[:100]}{'...' if len(message.content) > 100 else ''}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Send notification to thread about the solution
        try:
            notification_embed = embed_factory.solution_marked_embed(message, interaction.user, category)
            await thread.send(embed=notification_embed)
        except discord.Forbidden:
            pass  # Ignore if we can't send to thread
        
        # Suggest thread closure if this is a full solution (not just helpful)
        if category == "solution":
            await self.suggest_thread_closure(thread, message)
        
        logging.info(f"Message {message.id} marked as {category} by {interaction.user} in thread {thread.id}")

    async def unmark_solution(self, interaction: discord.Interaction, message: discord.Message):
        """Remove solution marking from a message."""
        # Check if user has permission
        if not await self.can_mark_solutions(interaction.user, interaction.guild_id):
            embed = embed_factory.error_embed("Permission Denied", 
                "Only support team members can unmark solutions.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if message is in a monitored thread
        if not isinstance(message.channel, discord.Thread):
            embed = embed_factory.error_embed("Invalid Channel", 
                "Solutions can only be unmarked in forum threads.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        thread = message.channel
        if not await self.is_monitored_thread(thread):
            embed = embed_factory.error_embed("Not Monitored", 
                "This forum channel is not being monitored by ForumGuard.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if message is actually marked as a solution
        existing_solutions = await db.get_thread_solutions(thread.id)
        solution = next((sol for sol in existing_solutions if sol['message_id'] == message.id), None)
        
        if not solution:
            embed = embed_factory.error_embed("Not Marked", 
                "This message is not marked as a solution.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Defer the response since we might take a while
        await interaction.response.defer(ephemeral=True)

        # Unpin the message
        await self.unpin_solution_message(message)
        
        # Remove from database
        await db.remove_thread_solution(thread.id, message.id)
        
        # If this was a full solution, check if there are any other solutions left
        # If not, remove from managed threads
        if solution['category'] == 'solution':
            remaining_solutions = await db.get_thread_solutions(thread.id)
            full_solutions = [sol for sol in remaining_solutions if sol['category'] == 'solution']
            if not full_solutions:
                await db.remove_managed_solution_thread(thread.id)
        
        # Create success embed
        category = solution['category']
        embed = embed_factory.success_embed("Solution Unmarked", 
            f"Message no longer marked as {category} and unpinned.")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logging.info(f"Message {message.id} unmarked as solution by {interaction.user} in thread {thread.id}")

async def setup(bot: commands.Bot):
    await bot.add_cog(SolutionsCog(bot))