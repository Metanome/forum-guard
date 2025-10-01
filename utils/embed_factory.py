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

def thread_closed_embed(user: discord.Member) -> discord.Embed:
    """Creates the embed posted when a thread is automatically closed."""
    message = (
        "🔒 This thread has been marked as solved and archived.\n\n"
        + "If you need further help, please create a new thread."
    )
    embed = discord.Embed(
        title="Thread Closed",
        description=message,
        color=SUCCESS_COLOR
    )
    embed.set_footer(text=f"Marked as solved by {user.display_name}")
    return embed

def thread_reopened_embed() -> discord.Embed:
    """Creates the embed posted when a thread is automatically reopened."""
    message = (
        "🔓 This thread has been reopened.\n\n"
        + "The solution tag was removed and the thread is now active again."
    )
    embed = discord.Embed(
        title="Thread Reopened",
        description=message,
        color=INFO_COLOR
    )
    return embed

def solution_marked_embed(message: discord.Message, marked_by: discord.Member, category: str) -> discord.Embed:
    """Creates the embed posted when a message is marked as a solution."""
    category_emoji = "✅" if category == "solution" else "💡"
    category_title = "Solution" if category == "solution" else "Helpful Answer"
    
    embed = discord.Embed(
        title=f"{category_emoji} {category_title} Marked",
        description=f"A message by {message.author.mention} has been marked as a {category} by {marked_by.mention}.",
        color=SUCCESS_COLOR
    )
    
    message_preview = message.content[:200] + "..." if len(message.content) > 200 else message.content
    embed.add_field(name="Message", value=f"[Jump to message]({message.jump_url})\n{message_preview}", inline=False)
    
    return embed

def solution_closure_suggestion_embed(solution_message: discord.Message) -> discord.Embed:
    """Creates the embed suggesting thread closure after a solution is marked."""
    embed = discord.Embed(
        title="💡 Consider Marking as Solved",
        description=(
            "A solution has been marked in this thread! If this resolves your issue, "
            "consider applying a solution tag to close and archive this thread.\n\n"
            "This will help keep the forum organized and let others know the issue is resolved."
        ),
        color=INFO_COLOR
    )
    
    embed.add_field(
        name="Marked Solution", 
        value=f"[Jump to solution]({solution_message.jump_url})", 
        inline=False
    )
    
    return embed