import discord
from typing import List

SUCCESS_COLOR = discord.Color.green()
ERROR_COLOR = discord.Color.red()
INFO_COLOR = discord.Color.blue()

def simple_embed(title: str, message: str, color: discord.Color) -> discord.Embed:
    """Creates a simple, standardized embed."""
    embed = discord.Embed(title=title, description=message, color=color)
    return embed

def success_embed(title: str, message: str) -> discord.Embed:
    """Creates a success-themed embed."""
    return simple_embed(f":white_check_mark: {title}", message, SUCCESS_COLOR)

def error_embed(title: str, message: str) -> discord.Embed:
    """Creates an error-themed embed."""
    return simple_embed(f":x: {title}", message, ERROR_COLOR)

def info_embed(title: str, message: str) -> discord.Embed:
    """Creates an info-themed embed."""
    return simple_embed(f":information_source: {title}", message, INFO_COLOR)

def view_settings_embed(guild: discord.Guild, config: dict) -> discord.Embed:
    """Creates a detailed embed to display a guild's current settings."""
    embed = discord.Embed(
        title=f"ForumGuard Settings for {guild.name}",
        color=INFO_COLOR
    )

    # Monitored Channels
    channel_mentions = [f'<#{cid}>' for cid in config.get('monitored_channels', [])]
    channel_text = '\n'.join(channel_mentions) if channel_mentions else "None"
    embed.add_field(name="Monitored Forum Channels", value=channel_text, inline=False)

    # Support Roles
    role_mentions = [f'<@&{rid}>' for rid in config.get('support_roles', [])]
    role_text = '\n'.join(role_mentions) if role_mentions else "None"
    embed.add_field(name="Support Roles", value=role_text, inline=False)

    # DM Notifications
    dms_enabled = config.get('dm_notifications_enabled', True)
    dm_status = "Enabled" if dms_enabled else "Disabled"
    embed.add_field(name="DM Notifications on Reply Deletion", value=dm_status, inline=False)

    embed.set_footer(text=f"Guild ID: {guild.id}")
    return embed

def dm_notification_embed(thread: discord.Thread) -> discord.Embed:
    """Creates the embed sent to a user whose message was deleted."""
    message = (
        f"Your message in the thread `\"{thread.name}\"` was automatically removed.\n\n"
        + f"In this server, replies in monitored forum posts are restricted to the original poster "
        + f"and designated support roles to keep the discussion focused.\n\n"
        + f"If you believe this was an error, please contact a server moderator."
    )
    embed = discord.Embed(
        title="Message Removed",
        description=message,
        color=ERROR_COLOR
    )
    embed.set_footer(text=f"Server: {thread.guild.name}")
    return embed