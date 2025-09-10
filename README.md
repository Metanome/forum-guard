# ForumGuard

ForumGuard is a specialized Discord bot for moderating forum channels. It restricts reply permissions to the original poster (OP) and designated support roles, ensuring that forum threads remain focused and on-topic.

## Core Features

- Restricts replies in forum threads to the OP and configured support roles.
- Deletes unauthorized replies and optionally notifies the user via DM.
- Highly configurable through intuitive slash commands (`/guard`).
- All settings are stored in a persistent SQLite database.

## Commands

All commands are grouped under the `/guard` namespace and require the `Manage Server` permission.

- `/guard channel add <channel>`: Adds a forum channel to the moderation list.
- `/guard channel remove <channel>`: Removes a forum channel from the moderation list.
- `/guard role add <role>`: Adds a role to the support team, allowing members with this role to reply in any monitored thread.
- `/guard role remove <role>`: Removes a role from the support team.
- `/guard settings dms <enabled>`: Toggles whether the bot sends a DM to users when their reply is deleted.
- `/guard settings view`: Displays the current configuration for the server in a detailed embed.
- `/guard help`: Shows a list of all available commands, including developer information in the footer.

## Local Development & Testing

To run the bot on your local machine for testing:

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd forum-guard
    ```

2.  **Set up a Python virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create an environment file:**
    - Create a file named `.env` in the root of the project.
    - Add your Discord bot token to this file:
      ```
      DISCORD_BOT_TOKEN=YourBotTokenGoesHere
      ```

5.  **Run the bot:**
    ```bash
    python main.py
    ```

## Deployment

This bot is designed to be deployed on a hosting service that supports persistent background workers.

### Recommended: Render

The repository includes a `render.yaml` file configured for deployment on [Render](https://render.com/).

**Important:** Due to the bot's nature as a 24/7 background worker that requires persistent storage for its database, a paid plan on Render is required. The `render.yaml` is pre-configured to use the **`starter` plan**.

**Deployment Steps:**

1.  Fork this repository to your own GitHub account.
2.  In the Render Dashboard, create a new **Blueprint** service and connect it to your forked repository.
3.  Render will automatically detect the `render.yaml` file and configure the service.
4.  Before the first deploy, go to the **Environment** tab for your new service.
5.  Add a new **Secret Variable**:
    - **Key:** `DISCORD_BOT_TOKEN`
    - **Value:** Paste your actual Discord bot token here.
6.  Deploy the service. Render will build and run the bot, and the SQLite database and log file will be stored on the persistent disk attached to the service.