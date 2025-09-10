
import os
import discord
from discord.ext import commands
import logging
import asyncio
from dotenv import load_dotenv

from utils import database_handler as db

# 1. Load Environment Variables
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN not found in .env file!")

# 2. Setup Logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# File Handler
log_path = os.getenv('LOG_PATH', 'bot.log')
file_handler = logging.FileHandler(log_path)
file_handler.setFormatter(log_formatter)

# Get root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Silence some of discord.py's noisier loggers
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)

# 3. Bot Intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True # Required to read message content
intents.members = True # Required to get member roles

# 4. Bot Instantiation
class ForumGuardBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_cogs = [
            'cogs.settings',
            'cogs.moderation'
        ]

    async def setup_hook(self):
        # Initialize database
        await db.initialize_database()
        logging.info("Database initialized.")

        # Load cogs
        for cog in self.initial_cogs:
            try:
                await self.load_extension(cog)
                logging.info(f"Successfully loaded cog: {cog}")
            except Exception as e:
                logging.error(f"Failed to load cog {cog}: {e}")
        
        # Sync slash commands
        # To sync for a specific guild, use: await self.tree.sync(guild=discord.Object(id=YOUR_GUILD_ID))
        await self.tree.sync()
        logging.info("Slash commands synced globally.")

    async def on_ready(self):
        logging.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logging.info('------')

bot = ForumGuardBot(command_prefix="!", intents=intents) # Prefix is not used for slash commands but is a required arg

if __name__ == "__main__":
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        logging.critical(f"Error while running bot: {e}")
