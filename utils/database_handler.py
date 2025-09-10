
import aiosqlite
import asyncio
import os
from typing import List, Optional

DB_FILE = os.getenv('DATABASE_PATH', 'database.sqlite3')

async def initialize_database():
    """Initializes the database and creates tables if they don't exist."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                dm_notifications_enabled BOOLEAN DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monitored_channels (
                guild_id INTEGER,
                channel_id INTEGER,
                PRIMARY KEY (guild_id, channel_id),
                FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS support_roles (
                guild_id INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, role_id),
                FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
            )
        """)
        await db.commit()

async def add_guild_if_not_exists(guild_id: int):
    """Ensures a guild has a default entry in the guild_settings table."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))
        await db.commit()

async def add_monitored_channel(guild_id: int, channel_id: int) -> bool:
    """Adds a channel to the monitored list for a guild. Returns False if already exists."""
    await add_guild_if_not_exists(guild_id)
    async with aiosqlite.connect(DB_FILE) as db:
        try:
            await db.execute("INSERT INTO monitored_channels (guild_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def remove_monitored_channel(guild_id: int, channel_id: int) -> bool:
    """Removes a channel from the monitored list. Returns False if it wasn't there."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("DELETE FROM monitored_channels WHERE guild_id = ? AND channel_id = ?", (guild_id, channel_id))
        await db.commit()
        return cursor.rowcount > 0

async def add_support_role(guild_id: int, role_id: int) -> bool:
    """Adds a support role for a guild. Returns False if already exists."""
    await add_guild_if_not_exists(guild_id)
    async with aiosqlite.connect(DB_FILE) as db:
        try:
            await db.execute("INSERT INTO support_roles (guild_id, role_id) VALUES (?, ?)", (guild_id, role_id))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def remove_support_role(guild_id: int, role_id: int) -> bool:
    """Removes a support role. Returns False if it wasn't there."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("DELETE FROM support_roles WHERE guild_id = ? AND role_id = ?", (guild_id, role_id))
        await db.commit()
        return cursor.rowcount > 0

async def set_dm_notifications(guild_id: int, enabled: bool):
    """Sets the DM notification preference for a guild."""
    await add_guild_if_not_exists(guild_id)
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE guild_settings SET dm_notifications_enabled = ? WHERE guild_id = ?", (enabled, guild_id))
        await db.commit()

async def get_guild_config(guild_id: int) -> Optional[dict]:
    """Fetches the entire configuration for a given guild."""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        
        # Fetch main settings
        settings_cursor = await db.execute("SELECT dm_notifications_enabled FROM guild_settings WHERE guild_id = ?", (guild_id,))
        settings = await settings_cursor.fetchone()
        if not settings:
            return None

        # Fetch monitored channels
        channels_cursor = await db.execute("SELECT channel_id FROM monitored_channels WHERE guild_id = ?", (guild_id,))
        channels = [row['channel_id'] for row in await channels_cursor.fetchall()]

        # Fetch support roles
        roles_cursor = await db.execute("SELECT role_id FROM support_roles WHERE guild_id = ?", (guild_id,))
        roles = [row['role_id'] for row in await roles_cursor.fetchall()]

        return {
            "dm_notifications_enabled": settings["dm_notifications_enabled"],
            "monitored_channels": channels,
            "support_roles": roles
        }
