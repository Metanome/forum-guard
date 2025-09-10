import discord
from discord.ext import commands
from discord import app_commands, ForumChannel, Role

from utils import database_handler as db
from utils import embed_factory

class SettingsCog(commands.Cog):
    """Handles all slash command interactions for configuring the bot."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    guard = app_commands.Group(name="guard", description="Configure ForumGuard moderation settings.", default_permissions=discord.Permissions(manage_guild=True))

    @guard.command(name="help", description="Shows a list of all available commands.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="ForumGuard Commands",
            description="Here is a list of available commands to configure the bot. You must have `Manage Server` permissions to use them.",
            color=embed_factory.INFO_COLOR
        )

        embed.add_field(name="`/guard channel add <channel>`", value="Starts moderating a forum channel.", inline=False)
        embed.add_field(name="`/guard channel remove <channel>`", value="Stops moderating a forum channel.", inline=False)
        embed.add_field(name="`/guard role add <role>`", value="Adds a role that can reply in monitored threads.", inline=False)
        embed.add_field(name="`/guard role remove <role>`", value="Removes a support role.", inline=False)
        embed.add_field(name="`/guard settings dms <enabled>`", value="Enable or disable DM notifications for deleted messages.", inline=False)
        embed.add_field(name="`/guard settings view`", value="Displays the current bot configuration for this server.", inline=False)
        embed.add_field(name="`/guard help`", value="Shows this help message.", inline=False)

        embed.set_footer(text="Developed by Dr. Skinner • ForumGuard | A specialized bot for moderating forum channel replies.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @guard.command(name="channel_add", description="Start moderating a forum channel.")
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

    @guard.command(name="channel_remove", description="Stop moderating a forum channel.")
    @app_commands.describe(channel="The forum channel to remove.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_channel(self, interaction: discord.Interaction, channel: ForumChannel):
        success = await db.remove_monitored_channel(interaction.guild_id, channel.id)
        if success:
            # Invalidate the cache for this guild
            moderation_cog = self.bot.get_cog('ModerationCog')
            if moderation_cog:
                moderation_cog.clear_guild_cache(interaction.guild.id)
            embed = embed_factory.success_embed("Channel Removed", f"Successfully removed {channel.mention} from the list.")
        else:
            embed = embed_factory.error_embed("Not Found", f"{channel.mention} was not on the list of monitored channels.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @guard.command(name="role_add", description="Add a role that can reply to any monitored thread.")
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

    @guard.command(name="role_remove", description="Remove a support role.")
    @app_commands.describe(role="The support role to remove.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def remove_role(self, interaction: discord.Interaction, role: Role):
        success = await db.remove_support_role(interaction.guild_id, role.id)
        if success:
            # Invalidate the cache for this guild
            moderation_cog = self.bot.get_cog('ModerationCog')
            if moderation_cog:
                moderation_cog.clear_guild_cache(interaction.guild.id)
            embed = embed_factory.success_embed("Role Removed", f"Successfully removed {role.mention} from support roles.")
        else:
            embed = embed_factory.error_embed("Not Found", f"{role.mention} was not a support role.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @guard.command(name="settings_dms", description="Enable or disable DM notifications for users whose messages are deleted.")
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

    @guard.command(name="settings_view", description="Display the current configuration for ForumGuard.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view_settings(self, interaction: discord.Interaction):
        config = await db.get_guild_config(interaction.guild_id)
        if not config:
            await db.add_guild_if_not_exists(interaction.guild_id)
            config = await db.get_guild_config(interaction.guild_id)
        
        embed = embed_factory.view_settings_embed(interaction.guild, config)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
