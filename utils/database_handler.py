
import aiosqlite
import asyncio
import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS forum_solution_tags (
                guild_id INTEGER,
                forum_id INTEGER,
                tag_id INTEGER,
                tag_name TEXT,
                PRIMARY KEY (guild_id, forum_id, tag_id),
                FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS thread_solutions (
                thread_id INTEGER,
                message_id INTEGER,
                marked_by INTEGER,
                marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category TEXT DEFAULT 'solution',
                PRIMARY KEY (thread_id, message_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS managed_solution_threads (
                thread_id INTEGER PRIMARY KEY,
                managed_since TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                managed_by TEXT DEFAULT 'tag_change'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_escalation_settings (
                guild_id INTEGER PRIMARY KEY,
                tier_1_hours INTEGER DEFAULT 24,
                tier_1_role_id INTEGER,
                tier_2_hours INTEGER DEFAULT 48,
                tier_2_role_id INTEGER,
                escalation_channel_id INTEGER,
                enabled BOOLEAN DEFAULT 0,
                escalation_behavior TEXT DEFAULT 'support_only',
                community_delay_hours INTEGER DEFAULT 12,
                max_thread_age_days INTEGER DEFAULT 7,
                FOREIGN KEY (guild_id) REFERENCES guild_settings(guild_id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS thread_escalation_state (
                thread_id INTEGER PRIMARY KEY,
                last_non_op_message TIMESTAMP,
                last_community_message TIMESTAMP,
                last_support_message TIMESTAMP,
                tier_1_executed BOOLEAN DEFAULT 0,
                tier_2_executed BOOLEAN DEFAULT 0
            )
        """)
        await db.commit()
        
        # Perform any necessary migrations
        await migrate_database()

async def migrate_database():
    """Perform database migrations for new columns."""
    async with aiosqlite.connect(DB_FILE) as db:
        # Check if max_thread_age_days column exists
        cursor = await db.execute("PRAGMA table_info(guild_escalation_settings)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'max_thread_age_days' not in column_names:
            await db.execute("ALTER TABLE guild_escalation_settings ADD COLUMN max_thread_age_days INTEGER DEFAULT 7")
            logger.info("Added max_thread_age_days column to guild_escalation_settings table")
        
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

async def add_solution_tag(guild_id: int, forum_id: int, tag_id: int, tag_name: str) -> bool:
    """Adds a solution tag for a forum. Returns False if already exists."""
    await add_guild_if_not_exists(guild_id)
    async with aiosqlite.connect(DB_FILE) as db:
        try:
            await db.execute("INSERT INTO forum_solution_tags (guild_id, forum_id, tag_id, tag_name) VALUES (?, ?, ?, ?)", 
                           (guild_id, forum_id, tag_id, tag_name))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def remove_solution_tag(guild_id: int, forum_id: int, tag_id: int) -> bool:
    """Removes a solution tag. Returns False if it wasn't there."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("DELETE FROM forum_solution_tags WHERE guild_id = ? AND forum_id = ? AND tag_id = ?", 
                                (guild_id, forum_id, tag_id))
        await db.commit()
        return cursor.rowcount > 0

async def get_forum_solution_tags(guild_id: int, forum_id: int) -> List[int]:
    """Gets all solution tag IDs for a specific forum."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT tag_id FROM forum_solution_tags WHERE guild_id = ? AND forum_id = ?", 
                                (guild_id, forum_id))
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def get_guild_solution_tags(guild_id: int) -> dict:
    """Gets all solution tags for a guild, organized by forum."""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT forum_id, tag_id, tag_name FROM forum_solution_tags WHERE guild_id = ?", 
                                (guild_id,))
        rows = await cursor.fetchall()
        
        result = {}
        for row in rows:
            forum_id = row['forum_id']
            if forum_id not in result:
                result[forum_id] = []
            result[forum_id].append({'tag_id': row['tag_id'], 'tag_name': row['tag_name']})
        
        return result

async def add_thread_solution(thread_id: int, message_id: int, marked_by: int, category: str = 'solution'):
    """Adds a thread solution marker."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR REPLACE INTO thread_solutions (thread_id, message_id, marked_by, category) VALUES (?, ?, ?, ?)",
                        (thread_id, message_id, marked_by, category))
        await db.commit()

async def remove_thread_solution(thread_id: int, message_id: int) -> bool:
    """Removes a thread solution marker. Returns False if it wasn't there."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("DELETE FROM thread_solutions WHERE thread_id = ? AND message_id = ?", 
                                (thread_id, message_id))
        await db.commit()
        return cursor.rowcount > 0

async def get_thread_solutions(thread_id: int) -> List[dict]:
    """Gets all solutions for a thread."""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT message_id, marked_by, marked_at, category FROM thread_solutions WHERE thread_id = ?", 
                                (thread_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

# Escalation management functions
async def set_guild_escalation_settings(guild_id: int, tier_1_hours: int, tier_1_role_id: int, 
                                       tier_2_hours: int, tier_2_role_id: int, escalation_channel_id: int, 
                                       enabled: bool = True, escalation_behavior: str = 'support_only', 
                                       community_delay_hours: int = 12, max_thread_age_days: int = 7):
    """Sets escalation settings for a guild (applies to all monitored forums)."""
    await add_guild_if_not_exists(guild_id)
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            INSERT OR REPLACE INTO guild_escalation_settings 
            (guild_id, tier_1_hours, tier_1_role_id, tier_2_hours, tier_2_role_id, 
             escalation_channel_id, enabled, escalation_behavior, community_delay_hours, max_thread_age_days) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (guild_id, tier_1_hours, tier_1_role_id, tier_2_hours, tier_2_role_id, 
              escalation_channel_id, enabled, escalation_behavior, community_delay_hours, max_thread_age_days))
        await db.commit()

async def get_guild_escalation_settings(guild_id: int) -> Optional[dict]:
    """Gets escalation settings for a guild."""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM guild_escalation_settings WHERE guild_id = ?", 
                                (guild_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def disable_guild_escalation(guild_id: int) -> bool:
    """Disables escalation for a guild. Returns False if no settings exist."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("UPDATE guild_escalation_settings SET enabled = 0 WHERE guild_id = ?", 
                                (guild_id,))
        await db.commit()
        return cursor.rowcount > 0

async def update_thread_escalation_state(thread_id: int, last_non_op_message: int = None, 
                                        last_community_message: int = None, last_support_message: int = None,
                                        tier_1_executed: bool = False, tier_2_executed: bool = False):
    """Updates or creates thread escalation state."""
    async with aiosqlite.connect(DB_FILE) as db:
        # Get current state first
        cursor = await db.execute("SELECT * FROM thread_escalation_state WHERE thread_id = ?", (thread_id,))
        current = await cursor.fetchone()
        
        if current:
            # Update existing record, preserving values that aren't being changed
            await db.execute("""
                UPDATE thread_escalation_state 
                SET last_non_op_message = COALESCE(?, last_non_op_message),
                    last_community_message = COALESCE(?, last_community_message),
                    last_support_message = COALESCE(?, last_support_message),
                    tier_1_executed = ?,
                    tier_2_executed = ?
                WHERE thread_id = ?
            """, (last_non_op_message, last_community_message, last_support_message, 
                  tier_1_executed, tier_2_executed, thread_id))
        else:
            # Create new record
            await db.execute("""
                INSERT INTO thread_escalation_state 
                (thread_id, last_non_op_message, last_community_message, last_support_message, tier_1_executed, tier_2_executed) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (thread_id, last_non_op_message, last_community_message, last_support_message, 
                  tier_1_executed, tier_2_executed))
        await db.commit()

async def get_thread_escalation_state(thread_id: int) -> Optional[dict]:
    """Gets escalation state for a thread."""
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM thread_escalation_state WHERE thread_id = ?", (thread_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def mark_escalation_tier_executed(thread_id: int, tier: int):
    """Marks a specific escalation tier as executed for a thread."""
    async with aiosqlite.connect(DB_FILE) as db:
        # Use UPSERT logic to ensure row exists
        if tier == 1:
            await db.execute("""
                INSERT INTO thread_escalation_state (thread_id, tier_1_executed, tier_2_executed) 
                VALUES (?, 1, 0)
                ON CONFLICT(thread_id) DO UPDATE SET tier_1_executed = 1
            """, (thread_id,))
        elif tier == 2:
            await db.execute("""
                INSERT INTO thread_escalation_state (thread_id, tier_1_executed, tier_2_executed) 
                VALUES (?, 0, 1)
                ON CONFLICT(thread_id) DO UPDATE SET tier_2_executed = 1
            """, (thread_id,))
        await db.commit()

async def set_guild_escalation_behavior(guild_id: int, behavior: str, community_delay_hours: int = 12):
    """Updates escalation behavior for a guild."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            UPDATE guild_escalation_settings 
            SET escalation_behavior = ?, community_delay_hours = ?
            WHERE guild_id = ?
        """, (behavior, community_delay_hours, guild_id))
        await db.commit()

async def reset_thread_escalation_state(thread_id: int):
    """Resets escalation state when thread gets activity."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM thread_escalation_state WHERE thread_id = ?", (thread_id,))
        await db.commit()

async def reset_all_escalation_states(guild_id: int) -> int:
    """Resets escalation state for all threads in a guild. Returns count of reset threads."""
    async with aiosqlite.connect(DB_FILE) as db:
        # Get count of threads that will be reset
        cursor = await db.execute("""
            SELECT COUNT(*) FROM thread_escalation_state tes
            WHERE EXISTS (
                SELECT 1 FROM guild_escalation_settings ges 
                WHERE ges.guild_id = ? AND ges.enabled = 1
            )
        """, (guild_id,))
        count = (await cursor.fetchone())[0]
        
        # Reset all escalation states for threads in this guild's monitored forums
        await db.execute("""
            DELETE FROM thread_escalation_state 
            WHERE thread_id IN (
                SELECT tes.thread_id FROM thread_escalation_state tes
                WHERE EXISTS (
                    SELECT 1 FROM guild_escalation_settings ges 
                    WHERE ges.guild_id = ? AND ges.enabled = 1
                )
            )
        """, (guild_id,))
        await db.commit()
        return count


async def add_managed_solution_thread(thread_id: int, managed_by: str = 'tag_change'):
    """Marks a thread as managed by the bot for solution tag tracking."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR IGNORE INTO managed_solution_threads (thread_id, managed_by) VALUES (?, ?)",
                        (thread_id, managed_by))
        await db.commit()


async def remove_managed_solution_thread(thread_id: int):
    """Removes a thread from bot management for solution tag tracking."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM managed_solution_threads WHERE thread_id = ?", (thread_id,))
        await db.commit()


async def is_thread_managed(thread_id: int) -> bool:
    """Checks if a thread is managed by the bot for solution tag tracking."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT 1 FROM managed_solution_threads WHERE thread_id = ? LIMIT 1", (thread_id,))
        result = await cursor.fetchone()
        return result is not None


async def get_managed_threads_count(guild_id: int = None) -> int:
    """Gets the count of managed solution threads, optionally filtered by guild."""
    async with aiosqlite.connect(DB_FILE) as db:
        if guild_id:
            # This would require joining with thread data - for now just return total count
            cursor = await db.execute("SELECT COUNT(*) FROM managed_solution_threads")
        else:
            cursor = await db.execute("SELECT COUNT(*) FROM managed_solution_threads")
        result = await cursor.fetchone()
        return result[0] if result else 0
