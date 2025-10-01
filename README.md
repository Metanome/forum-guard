# ForumGuard

ForumGuard is a Discord bot designed to moderate forum channels. It restricts reply permissions to the original poster (OP) and designated support roles, provides automated escalation for unanswered threads, and manages thread lifecycle based on solution tags.

## Features

- **Access Control**: Restricts replies in forum threads to OP and configured support roles
- **Solution Management**: Automatic thread archiving/unarchiving based on solution tags
- **Escalation System**: Automated escalation for stale threads with configurable timeouts
- **Configuration**: Slash command interface with persistent SQLite database storage

## Commands

All commands require the `Manage Server` permission and are organized under the `/forum` namespace:

**Channel Management**
- `/forum channel add <channel>` - Monitor a forum channel
- `/forum channel remove <channel>` - Stop monitoring a channel

**Role Configuration**
- `/forum role add <role>` - Add support role with reply permissions
- `/forum role remove <role>` - Remove support role

**Solution Tag Management**
- `/forum tags add <forum> <tag>` - Configure solution tag for forum
- `/forum tags remove <forum> <tag>` - Remove solution tag
- `/forum tags list` - View all configured solution tags

**Escalation Configuration**
- `/forum escalation setup` - Configure automated escalation system
- `/forum escalation view` - View current escalation settings
- `/forum escalation reset` - Reset escalation states

**Settings & Utilities**
- `/forum settings dms <enabled>` - Toggle DM notifications
- `/forum settings view` - Display complete server configuration
- `/forum help` - Show detailed command reference

## Local Development

### Prerequisites
- Python 3.9 or higher
- Discord bot token with appropriate permissions

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Metanome/forum-guard.git
   cd forum-guard
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   # Create .env file
   echo "DISCORD_BOT_TOKEN=your_bot_token_here" > .env
   ```

5. **Run the bot:**
   ```bash
   python main.py
   ```

## Deployment

### Render (Recommended)

The repository includes production-ready configuration for [Render](https://render.com/) deployment:

1. Fork this repository to your GitHub account
2. Create a new Blueprint service in Render Dashboard
3. Connect your forked repository - Render will auto-detect `render.yaml`
4. Configure environment variables:
   - `DISCORD_BOT_TOKEN`: Your Discord bot token
5. Deploy - The service will automatically build and start

**Note:** Requires Render's paid "Starter" plan for persistent disk storage.

### Other Platforms

ForumGuard can be deployed on any platform supporting:
- Python 3.9+ runtime
- Persistent file storage for SQLite database
- 24/7 background process execution
- Environment variable configuration