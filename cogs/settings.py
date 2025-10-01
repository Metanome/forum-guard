import discord
from discord.ext import commands
from discord import app_commands, ForumChannel, Role
import logging
import re

from utils import database_handler as db
from utils import embed_factory

class SettingsCog(commands.Cog):
    """Handles all slash command interactions for configuring the bot."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def parse_time_to_hours(self, time_str: str) -> int:
        """Parse time string like '1h', '30m', '2d' to hours."""
        time_str = time_str.lower().strip()
        
        # Match patterns like: 1h, 30m, 2d, 1.5h, etc.
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([smhd])$', time_str)
        
        if not match:
            # If no unit provided, assume hours
            try:
                return int(float(time_str))
            except ValueError:
                raise ValueError(f"Invalid time format: '{time_str}'. Use formats like '1h', '30m', '2d'")
        
        value, unit = match.groups()
        value = float(value)
        
        # Convert to hours
        if unit == 's':  # seconds
            return max(1, int(value / 3600))  # Minimum 1 hour
        elif unit == 'm':  # minutes
            return max(1, int(value / 60))    # Minimum 1 hour
        elif unit == 'h':  # hours
            return max(1, int(value))         # Minimum 1 hour
        elif unit == 'd':  # days
            return int(value * 24)
        
        raise ValueError(f"Invalid time unit: '{unit}'. Use s, m, h, or d")

    forum = app_commands.Group(name="forum", description="Configure ForumGuard moderation settings.", default_permissions=discord.Permissions(manage_guild=True))

    # Nested command groups
    channel_group = app_commands.Group(name="channel", description="Manage monitored forum channels.", parent=forum)
    role_group = app_commands.Group(name="role", description="Manage support roles.", parent=forum)
    settings_group = app_commands.Group(name="settings", description="Manage bot settings.", parent=forum)
    tags_group = app_commands.Group(name="tags", description="Manage solution tags for forums.", parent=forum)
    solutions_group = app_commands.Group(name="solutions", description="Manage thread solutions.", parent=forum)
    escalation_group = app_commands.Group(name="escalation", description="Manage thread escalation settings.", parent=forum)

    @forum.command(name="help", description="Shows a list of all available commands.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="ForumGuard Commands",
            description="Here is a list of available commands to configure the bot. You must have `Manage Server` permissions to use them.",
            color=embed_factory.INFO_COLOR
        )

        embed.add_field(name="`/forum channel add <channel>`", value="Starts moderating a forum channel.", inline=False)
        embed.add_field(name="`/forum channel remove <channel>`", value="Stops moderating a forum channel.", inline=False)
        embed.add_field(name="`/forum role add <role>`", value="Adds a role that can reply in monitored threads.", inline=False)
        embed.add_field(name="`/forum role remove <role>`", value="Removes a support role.", inline=False)
        embed.add_field(name="`/forum tags add <forum> <tag>`", value="Adds a solution tag for a forum channel.", inline=False)
        embed.add_field(name="`/forum tags remove <forum> <tag>`", value="Removes a solution tag from a forum channel.", inline=False)
        embed.add_field(name="`/forum solutions view <thread>`", value="Shows all marked solutions in a thread.", inline=False)
        embed.add_field(name="`/forum escalation setup <tier1_time> <tier1_role> <tier2_time> <tier2_role> <channel> [behavior] [delay_hours]`", value="Configure thread escalation for all monitored forums (supports 1h, 30m, 2d formats).", inline=False)
        embed.add_field(name="`/forum escalation view`", value="View current escalation settings for the server.", inline=False)
        embed.add_field(name="`/forum escalation reset confirm:CONFIRM`", value="Reset escalation state for ALL threads in the server.", inline=False)
        embed.add_field(name="`/forum settings dms <enabled>`", value="Enable or disable DM notifications for deleted messages.", inline=False)
        embed.add_field(name="`/forum settings view`", value="Displays the current bot configuration for this server.", inline=False)
        embed.add_field(name="`/forum help`", value="Shows this help message.", inline=False)

        embed.set_footer(text="Developed by Dr. Skinner • ForumGuard | A specialized bot for moderating forum channel replies.\n💡 Context Menus: Right-click messages to mark as Solution/Helpful or Unmark")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def monitored_channel_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete function for currently monitored forum channels."""
        try:
            # Get guild configuration
            config = await db.get_guild_config(interaction.guild_id)
            
            if not config or not config.get('monitored_channels'):
                return [app_commands.Choice(name="No monitored channels configured", value="no_channels")]
            
            # Get monitored forum channels and filter by current input
            choices = []
            for channel_id in config['monitored_channels']:
                channel = interaction.guild.get_channel(channel_id)
                if channel and isinstance(channel, discord.ForumChannel):
                    # Show all channels if current input is empty or very short (0-1 chars)
                    # Otherwise filter by channels that contain the current input
                    if len(current) <= 1 or current.lower() in channel.name.lower():
                        choices.append(app_commands.Choice(name=channel.name, value=str(channel.id)))
            
            # If no matches found, show all monitored channels anyway
            if not choices and len(current) > 1:
                for channel_id in config['monitored_channels']:
                    channel = interaction.guild.get_channel(channel_id)
                    if channel and isinstance(channel, discord.ForumChannel):
                        choices.append(app_commands.Choice(name=channel.name, value=str(channel.id)))
            
            # Limit to 25 choices (Discord limit)
            return choices[:25]
            
        except Exception as e:
            return [app_commands.Choice(name=f"Error: {str(e)}", value="error")]

    async def configured_role_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete function for currently configured support roles."""
        try:
            # Get guild configuration
            config = await db.get_guild_config(interaction.guild_id)
            
            if not config or not config.get('support_roles'):
                return [app_commands.Choice(name="No support roles configured", value="no_roles")]
            
            # Get support roles and filter by current input
            choices = []
            for role_id in config['support_roles']:
                role = interaction.guild.get_role(role_id)
                if role:
                    # Show all roles if current input is empty or very short (0-1 chars)
                    # Otherwise filter by roles that contain the current input
                    if len(current) <= 1 or current.lower() in role.name.lower():
                        choices.append(app_commands.Choice(name=role.name, value=str(role.id)))
            
            # If no matches found, show all configured roles anyway
            if not choices and len(current) > 1:
                for role_id in config['support_roles']:
                    role = interaction.guild.get_role(role_id)
                    if role:
                        choices.append(app_commands.Choice(name=role.name, value=str(role.id)))
            
            # Limit to 25 choices (Discord limit)
            return choices[:25]
            
        except Exception as e:
            return [app_commands.Choice(name=f"Error: {str(e)}", value="error")]

    @channel_group.command(name="add", description="Start moderating a forum channel.")
    @app_commands.describe(channel="The forum channel to add.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_channel(self, interaction: discord.Interaction, channel: ForumChannel):
        success = await db.add_monitored_channel(interaction.guild_id, channel.id)
        if success:
            # Invalidate the cache for this guild
            moderation_cog = self.bot.get_cog('ModerationCog')
            if moderation_cog:
                moderation_cog.clear_guild_cache(interaction.guild.id)
            embed = embed_factory.success_embed("Channel Added", f"Successfully added {channel.mention} to the list of monitored channels.")
        else:
            embed = embed_factory.error_embed("Already Added", f"{channel.mention} is already being monitored.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @channel_group.command(name="remove", description="Stop moderating a forum channel.")
    @app_commands.describe(channel="The forum channel to remove.")
    @app_commands.autocomplete(channel=monitored_channel_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_channel(self, interaction: discord.Interaction, channel: str):
        # Convert channel ID to channel object
        try:
            channel_id = int(channel)
            channel_obj = interaction.guild.get_channel(channel_id)
            if not channel_obj or not isinstance(channel_obj, discord.ForumChannel):
                embed = embed_factory.error_embed("Invalid Channel", "Selected channel is not a valid forum channel.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        except ValueError:
            embed = embed_factory.error_embed("Invalid Selection", "Please select a valid channel from the autocomplete.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        success = await db.remove_monitored_channel(interaction.guild_id, channel_obj.id)
        if success:
            # Invalidate the cache for this guild
            moderation_cog = self.bot.get_cog('ModerationCog')
            if moderation_cog:
                moderation_cog.clear_guild_cache(interaction.guild.id)
            embed = embed_factory.success_embed("Channel Removed", f"Successfully removed {channel_obj.mention} from the list.")
        else:
            embed = embed_factory.error_embed("Not Found", f"{channel_obj.mention} was not on the list of monitored channels.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @role_group.command(name="add", description="Add a role that can reply to any monitored thread.")
    @app_commands.describe(role="The support role to add.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_role(self, interaction: discord.Interaction, role: Role):
        success = await db.add_support_role(interaction.guild_id, role.id)
        if success:
            # Invalidate the cache for this guild
            moderation_cog = self.bot.get_cog('ModerationCog')
            if moderation_cog:
                moderation_cog.clear_guild_cache(interaction.guild.id)
            embed = embed_factory.success_embed("Role Added", f"Successfully added {role.mention} as a support role.")
        else:
            embed = embed_factory.error_embed("Already Added", f"{role.mention} is already a support role.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @role_group.command(name="remove", description="Remove a support role.")
    @app_commands.describe(role="The support role to remove.")
    @app_commands.autocomplete(role=configured_role_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_role(self, interaction: discord.Interaction, role: str):
        # Convert role ID to role object
        try:
            role_id = int(role)
            role_obj = interaction.guild.get_role(role_id)
            if not role_obj:
                embed = embed_factory.error_embed("Invalid Role", "Selected role is not valid or was deleted.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        except ValueError:
            embed = embed_factory.error_embed("Invalid Selection", "Please select a valid role from the autocomplete.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        success = await db.remove_support_role(interaction.guild_id, role_obj.id)
        if success:
            # Invalidate the cache for this guild
            moderation_cog = self.bot.get_cog('ModerationCog')
            if moderation_cog:
                moderation_cog.clear_guild_cache(interaction.guild.id)
            embed = embed_factory.success_embed("Role Removed", f"Successfully removed {role_obj.mention} from support roles.")
        else:
            embed = embed_factory.error_embed("Not Found", f"{role_obj.mention} was not a support role.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @settings_group.command(name="dms", description="Enable or disable DM notifications for users whose messages are deleted.")
    @app_commands.describe(enabled="Set to True to enable DMs, False to disable.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def settings_dms(self, interaction: discord.Interaction, enabled: bool):
        await db.set_dm_notifications(interaction.guild_id, enabled)
        # Invalidate the cache for this guild
        moderation_cog = self.bot.get_cog('ModerationCog')
        if moderation_cog:
            moderation_cog.clear_guild_cache(interaction.guild.id)
        status = "enabled" if enabled else "disabled"
        embed = embed_factory.success_embed("Settings Updated", f"DM notifications have been {status}.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @settings_group.command(name="view", description="Display the current configuration for ForumGuard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view_settings(self, interaction: discord.Interaction):
        config = await db.get_guild_config(interaction.guild_id)
        if not config:
            await db.add_guild_if_not_exists(interaction.guild_id)
            config = await db.get_guild_config(interaction.guild_id)
        
        embed = embed_factory.view_settings_embed(interaction.guild, config)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def tag_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete function for forum tags."""
        try:
            forum_param = None
            
            # Try to get the forum parameter from the namespace
            namespace_forum = getattr(interaction.namespace, 'forum', None)
            
            if namespace_forum:
                # If it's a discord.Object, get the ID and convert to channel
                if hasattr(namespace_forum, 'id'):
                    forum_id = namespace_forum.id
                    forum_param = interaction.guild.get_channel(forum_id)
                elif isinstance(namespace_forum, discord.ForumChannel):
                    forum_param = namespace_forum
                else:
                    # Try to convert directly to int
                    try:
                        forum_id = int(namespace_forum)
                        forum_param = interaction.guild.get_channel(forum_id)
                    except (ValueError, TypeError):
                        pass
            
            # If not available from namespace, try the old method as fallback
            if not forum_param:
                for option in interaction.data.get("options", []):
                    if option["name"] == "forum":
                        forum_id = int(option["value"])
                        forum_param = interaction.guild.get_channel(forum_id)
                        break
            
            if not forum_param:
                return [app_commands.Choice(name="Please select a forum channel first", value="no_forum")]
            
            if not isinstance(forum_param, discord.ForumChannel):
                return [app_commands.Choice(name=f"Not a forum channel: {type(forum_param).__name__}", value="not_forum")]
            
            # Check if forum has any tags
            if not forum_param.available_tags:
                return [app_commands.Choice(name="This forum has no tags configured", value="no_tags")]
            
            # Get available tags and filter by current input
            choices = []
            for tag in forum_param.available_tags:
                # Show all tags if current input is empty or very short (0-1 chars)
                # Otherwise filter by tags that contain the current input
                if len(current) <= 1 or current.lower() in tag.name.lower():
                    choices.append(app_commands.Choice(name=tag.name, value=tag.name))
            
            # If no matches found, show all tags anyway
            if not choices and len(current) > 1:
                for tag in forum_param.available_tags:
                    choices.append(app_commands.Choice(name=tag.name, value=tag.name))
            
            # Limit to 25 choices (Discord limit)
            return choices[:25]
            
        except Exception as e:
            # Log the error for debugging but don't crash
            return [app_commands.Choice(name=f"Error: {str(e)}", value="error")]

    async def configured_tag_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete function for configured solution tags only."""
        try:
            forum_param = None
            
            # Try to get the forum parameter from the namespace
            namespace_forum = getattr(interaction.namespace, 'forum', None)
            
            if namespace_forum:
                # If it's a discord.Object, get the ID and convert to channel
                if hasattr(namespace_forum, 'id'):
                    forum_id = namespace_forum.id
                    forum_param = interaction.guild.get_channel(forum_id)
                elif isinstance(namespace_forum, discord.ForumChannel):
                    forum_param = namespace_forum
                else:
                    # Try to convert directly to int
                    try:
                        forum_id = int(namespace_forum)
                        forum_param = interaction.guild.get_channel(forum_id)
                    except (ValueError, TypeError):
                        pass
            
            # If not available from namespace, try the old method as fallback
            if not forum_param:
                for option in interaction.data.get("options", []):
                    if option["name"] == "forum":
                        forum_id = int(option["value"])
                        forum_param = interaction.guild.get_channel(forum_id)
                        break
            
            if not forum_param:
                return [app_commands.Choice(name="Please select a forum channel first", value="no_forum")]
            
            if not isinstance(forum_param, discord.ForumChannel):
                return [app_commands.Choice(name=f"Not a forum channel: {type(forum_param).__name__}", value="not_forum")]
            
            # Get configured solution tags for this forum
            configured_tag_ids = await db.get_forum_solution_tags(interaction.guild_id, forum_param.id)
            
            if not configured_tag_ids:
                return [app_commands.Choice(name="No solution tags configured for this forum", value="no_tags")]
            
            # Get the actual tag objects and filter by current input
            choices = []
            available_tags = {tag.id: tag for tag in forum_param.available_tags}
            
            for tag_id in configured_tag_ids:
                if tag_id in available_tags:
                    tag = available_tags[tag_id]
                    # Show all tags if current input is empty or very short (0-1 chars)
                    # Otherwise filter by tags that contain the current input
                    if len(current) <= 1 or current.lower() in tag.name.lower():
                        choices.append(app_commands.Choice(name=tag.name, value=tag.name))
            
            # If no matches found, show all configured tags anyway
            if not choices and len(current) > 1:
                for tag_id in configured_tag_ids:
                    if tag_id in available_tags:
                        tag = available_tags[tag_id]
                        choices.append(app_commands.Choice(name=tag.name, value=tag.name))
            
            # Limit to 25 choices (Discord limit)
            return choices[:25]
            
        except Exception as e:
            # Log the error for debugging but don't crash
            return [app_commands.Choice(name=f"Error: {str(e)}", value="error")]

    @tags_group.command(name="add", description="Add a solution tag for a forum channel.")
    @app_commands.describe(forum="The forum channel to configure.", tag="The tag that marks threads as solved.")
    @app_commands.autocomplete(tag=tag_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def add_solution_tag(self, interaction: discord.Interaction, forum: ForumChannel, tag: str):
        # Get available tags from the forum
        available_tags = {t.name.lower(): t for t in forum.available_tags}
        
        if tag.lower() not in available_tags:
            embed = embed_factory.error_embed("Tag Not Found", 
                f"The tag `{tag}` doesn't exist in {forum.mention}.\n"
                f"Available tags: {', '.join([f'`{t.name}`' for t in forum.available_tags]) if forum.available_tags else 'None'}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        tag_obj = available_tags[tag.lower()]
        success = await db.add_solution_tag(interaction.guild_id, forum.id, tag_obj.id, tag_obj.name)
        
        if success:
            embed = embed_factory.success_embed("Solution Tag Added", 
                f"The tag `{tag_obj.name}` in {forum.mention} will now mark threads as solved.")
        else:
            embed = embed_factory.error_embed("Already Added", 
                f"The tag `{tag_obj.name}` is already configured as a solution tag for {forum.mention}.")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tags_group.command(name="remove", description="Remove a solution tag from a forum channel.")
    @app_commands.describe(forum="The forum channel to configure.", tag="The solution tag to remove.")
    @app_commands.autocomplete(tag=configured_tag_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_solution_tag(self, interaction: discord.Interaction, forum: ForumChannel, tag: str):
        # Get available tags from the forum
        available_tags = {t.name.lower(): t for t in forum.available_tags}
        
        if tag.lower() not in available_tags:
            embed = embed_factory.error_embed("Tag Not Found", 
                f"The tag `{tag}` doesn't exist in {forum.mention}.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        tag_obj = available_tags[tag.lower()]
        success = await db.remove_solution_tag(interaction.guild_id, forum.id, tag_obj.id)
        
        if success:
            embed = embed_factory.success_embed("Solution Tag Removed", 
                f"The tag `{tag_obj.name}` in {forum.mention} will no longer mark threads as solved.")
        else:
            embed = embed_factory.error_embed("Not Found", 
                f"The tag `{tag_obj.name}` was not configured as a solution tag for {forum.mention}.")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tags_group.command(name="list", description="List all solution tags for forum channels.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def list_solution_tags(self, interaction: discord.Interaction):
        solution_tags = await db.get_guild_solution_tags(interaction.guild_id)
        
        if not solution_tags:
            embed = embed_factory.info_embed("No Solution Tags", 
                "No solution tags have been configured for any forum channels.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Solution Tags Configuration",
            description="Solution tags configured for forum channels in this server:",
            color=embed_factory.INFO_COLOR
        )
        
        for forum_id, tags in solution_tags.items():
            forum_channel = interaction.guild.get_channel(forum_id)
            forum_name = forum_channel.mention if forum_channel else f"Unknown Forum (ID: {forum_id})"
            tag_names = [f"`{tag['tag_name']}`" for tag in tags]
            embed.add_field(name=forum_name, value=", ".join(tag_names), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @solutions_group.command(name="view", description="View all marked solutions in a thread.")
    @app_commands.describe(thread="The thread to view solutions for.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view_thread_solutions(self, interaction: discord.Interaction, thread: discord.Thread):
        if not isinstance(thread, discord.Thread):
            embed = embed_factory.error_embed("Invalid Thread", "Please provide a valid forum thread.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        solutions = await db.get_thread_solutions(thread.id)
        
        if not solutions:
            embed = embed_factory.info_embed("No Solutions", 
                f"No solutions have been marked in the thread `{thread.name}`.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Solutions in '{thread.name}'",
            description=f"Found {len(solutions)} marked solution(s):",
            color=embed_factory.INFO_COLOR
        )

        for solution in solutions:
            try:
                message = await thread.fetch_message(solution['message_id'])
                marked_by = interaction.guild.get_member(solution['marked_by'])
                marked_by_name = marked_by.display_name if marked_by else f"Unknown User (ID: {solution['marked_by']})"
                
                category_emoji = "✅" if solution['category'] == 'solution' else "💡"
                message_preview = message.content[:100] + "..." if len(message.content) > 100 else message.content
                
                embed.add_field(
                    name=f"{category_emoji} {solution['category'].title()}",
                    value=f"**Message:** {message_preview}\n"
                          f"**Link:** [Jump to message]({message.jump_url})\n"
                          f"**Marked by:** {marked_by_name}\n"
                          f"**Date:** <t:{int(solution['marked_at'])}>",
                    inline=False
                )
            except discord.NotFound:
                embed.add_field(
                    name=f"❌ Deleted {solution['category'].title()}",
                    value=f"Message ID: {solution['message_id']} (message deleted)\n"
                          f"**Marked by:** Unknown\n"
                          f"**Date:** <t:{int(solution['marked_at'])}>",
                    inline=False
                )
            except Exception as e:
                logging.error(f"Error fetching solution message {solution['message_id']}: {e}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @escalation_group.command(name="setup", description="Configure thread escalation for all monitored forums.")
    @app_commands.describe(
        tier1_time="Time before tier 1 escalation (e.g., '1h', '30m', '2d').",
        tier1_role="Role to ping for tier 1 escalation.",
        tier2_time="Time before tier 2 escalation (e.g., '2h', '48h', '2d').",
        tier2_role="Role to ping for tier 2 escalation.",
        escalation_channel="Channel to send tier 2 escalation alerts.",
        behavior="How community responses affect escalation (default: support_only).",
        delay_hours="Hours community responses delay escalation (hybrid mode only, default: 12h)."
    )
    @app_commands.choices(behavior=[
        app_commands.Choice(name="Support Only - Only support team responses prevent escalation", value="support_only"),
        app_commands.Choice(name="Community Friendly - Any response prevents escalation", value="community_friendly"),
        app_commands.Choice(name="Hybrid - Community responses delay, support responses prevent", value="hybrid")
    ])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_escalation(self, interaction: discord.Interaction, 
                              tier1_time: str, tier1_role: Role, tier2_time: str, 
                              tier2_role: Role, escalation_channel: discord.TextChannel,
                              behavior: app_commands.Choice[str] = None, delay_hours: str = "12h"):
        
        # Set default behavior if not provided
        if behavior is None:
            behavior_value = "support_only"
            behavior_name = "Support Only"
        else:
            behavior_value = behavior.value
            behavior_name = behavior.name.split(" - ")[0]
        
        # Parse time strings to hours
        try:
            tier1_hours = self.parse_time_to_hours(tier1_time)
            tier2_hours = self.parse_time_to_hours(tier2_time)
        except ValueError as e:
            embed = embed_factory.error_embed("Invalid Time Format", str(e))
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Parse delay hours (validate even if not used, for better error messages)
        community_delay_hours = 12  # default
        try:
            community_delay_hours = self.parse_time_to_hours(delay_hours)
        except ValueError as e:
            embed = embed_factory.error_embed("Invalid Delay Time", str(e))
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # For non-hybrid modes, delay_hours is ignored but we'll inform the user
        delay_ignored = behavior_value != "hybrid" and delay_hours != "12h"
        
        # Validation
        if tier1_hours <= 0 or tier2_hours <= 0:
            embed = embed_factory.error_embed("Invalid Hours", "Escalation times must be positive.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if tier2_hours <= tier1_hours:
            embed = embed_factory.error_embed("Invalid Configuration", 
                f"Tier 2 time ({tier2_time} = {tier2_hours}h) must be greater than tier 1 time ({tier1_time} = {tier1_hours}h).")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if guild has any monitored forums
        config = await db.get_guild_config(interaction.guild_id)
        if not config or not config.get('monitored_channels'):
            embed = embed_factory.error_embed("No Monitored Forums", 
                "No forums are being monitored by ForumGuard. Add some first with `/forum channel add`.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Save guild-wide escalation settings
        await db.set_guild_escalation_settings(
            interaction.guild_id, tier1_hours, tier1_role.id, 
            tier2_hours, tier2_role.id, escalation_channel.id, True,
            behavior_value, community_delay_hours
        )
        
        # Create behavior description
        behavior_descriptions = {
            "support_only": "Only support team responses prevent escalation",
            "community_friendly": "Any community response prevents escalation", 
            "hybrid": f"Community responses delay escalation by {delay_hours} ({community_delay_hours}h), support responses prevent it"
        }
        
        # Get list of monitored forums for display
        monitored_forum_names = []
        for forum_id in config['monitored_channels']:
            forum = interaction.guild.get_channel(forum_id)
            if forum:
                monitored_forum_names.append(forum.mention)
        
        # Build success message
        success_message = (
            f"Thread escalation configured for **all monitored forums**:\n"
            f"{', '.join(monitored_forum_names)}\n\n"
            f"**Tier 1:** After {tier1_time} ({tier1_hours}h) → Ping {tier1_role.mention} in thread\n"
            f"**Tier 2:** After {tier2_time} ({tier2_hours}h) → Ping {tier2_role.mention} in {escalation_channel.mention}\n"
            f"**Behavior:** {behavior_descriptions[behavior_value]}"
        )
        
        # Add note if delay_hours was provided but ignored
        if delay_ignored:
            success_message += f"\n\n*Note: Delay time `{delay_hours}` was ignored (only used in Hybrid mode)*"
        
        embed = embed_factory.success_embed("Escalation Configured", success_message)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @escalation_group.command(name="view", description="View escalation settings for the server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view_escalation(self, interaction: discord.Interaction):
        settings = await db.get_guild_escalation_settings(interaction.guild_id)
        
        if not settings:
            embed = embed_factory.info_embed("No Escalation Settings", 
                "Escalation has not been configured for this server.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get monitored forums for display
        config = await db.get_guild_config(interaction.guild_id)
        monitored_forums = []
        if config and config.get('monitored_channels'):
            for forum_id in config['monitored_channels']:
                forum = interaction.guild.get_channel(forum_id)
                if forum:
                    monitored_forums.append(forum.mention)
        
        embed = discord.Embed(
            title="Thread Escalation Settings",
            description="Guild-wide escalation configuration:",
            color=embed_factory.INFO_COLOR
        )
        
        tier1_role = interaction.guild.get_role(settings['tier_1_role_id'])
        tier2_role = interaction.guild.get_role(settings['tier_2_role_id'])
        escalation_channel = interaction.guild.get_channel(settings['escalation_channel_id'])
        
        tier1_role_name = tier1_role.mention if tier1_role else f"Unknown Role (ID: {settings['tier_1_role_id']})"
        tier2_role_name = tier2_role.mention if tier2_role else f"Unknown Role (ID: {settings['tier_2_role_id']})"
        channel_name = escalation_channel.mention if escalation_channel else f"Unknown Channel (ID: {settings['escalation_channel_id']})"
        
        status = "✅ Enabled" if settings['enabled'] else "❌ Disabled"
        behavior = settings.get('escalation_behavior', 'support_only')
        
        behavior_text = {
            'support_only': '🎯 Support Only',
            'community_friendly': '🤝 Community Friendly', 
            'hybrid': f"⚖️ Hybrid (delay: {settings.get('community_delay_hours', 12)}h)"
        }.get(behavior, behavior)
        
        escalation_info = (
            f"**Status:** {status}\n"
            f"**Behavior:** {behavior_text}\n"
            f"**Tier 1:** {settings['tier_1_hours']}h → {tier1_role_name}\n"
            f"**Tier 2:** {settings['tier_2_hours']}h → {tier2_role_name} in {channel_name}"
        )
        
        embed.add_field(name="Escalation Configuration", value=escalation_info, inline=False)
        
        if monitored_forums:
            embed.add_field(name="Applies to Forums", value="\n".join(monitored_forums), inline=False)
        else:
            embed.add_field(name="Applies to Forums", value="*No forums being monitored*", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @escalation_group.command(name="reset", description="Reset escalation state for all threads in the server.")
    @app_commands.describe(confirm="Type 'CONFIRM' to reset escalation state for ALL threads in the server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def reset_escalation(self, interaction: discord.Interaction, confirm: str):
        """Reset escalation state for all threads in the server."""
        try:
            if confirm != "CONFIRM":
                embed = embed_factory.warning_embed("Confirmation Required", 
                    "To reset escalation state for **ALL threads** in this server, please run:\n"
                    "`/forum escalation reset confirm:CONFIRM`\n\n"
                    "⚠️ This will clear escalation state for every thread, allowing them to be escalated again.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Perform global reset
            reset_count = await db.reset_all_escalation_states(interaction.guild_id)
            
            if reset_count == 0:
                embed = embed_factory.info_embed("No Escalations to Reset", 
                    "No threads currently have escalation state to reset.")
            else:
                embed = embed_factory.success_embed("Global Escalation Reset", 
                    f"Successfully reset escalation state for **{reset_count} threads** in this server.\n\n"
                    f"**Status:** All threads can now be escalated again if they become stale.")
                
            await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except Exception as e:
            logging.error(f"Error resetting escalation: {e}")
            embed = embed_factory.error_embed("Reset Failed", 
                "An error occurred while resetting escalation state. Please try again.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))