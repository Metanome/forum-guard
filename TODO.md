# ForumGuard Feature TODO List

This list contains potential features for future development. They are not committed and are subject to community feedback and technical evaluation.

---

- [ ] **User Warning System (Grace Period)**
  - **Goal:** To provide a less jarring user experience than instant message deletion.
  - **Implementation:** When a non-permitted message is detected, the bot posts a temporary, ephemeral reply visible only to the user (e.g., "This reply will be deleted in 30 seconds as it violates channel rules."). If the user deletes their message within the grace period, the bot takes no further action. Otherwise, the original message is deleted.
  - **Benefit:** Educates users about the rules and gives them a chance to self-correct, fostering a more positive community environment.

- [ ] **Thread-Specific Permissions**
  - **Goal:** To allow for flexible, case-by-case exceptions to the reply restrictions.
  - **Implementation:** The original poster (OP) of a thread can use a command like `/allow @user` to grant a specific user permission to reply in that single thread. The bot would maintain a temporary list of these permissions.
  - **Benefit:** Empowers thread owners to manage their own discussions and bring in specific people for help without needing moderator intervention to grant a permanent support role.

- [ ] **Automated Post Lifecycle Management**
  - **Goal:** To automatically archive threads that have been successfully resolved.
  - **Implementation:** Admins configure a specific tag (e.g., "Solved ✅"). When the OP applies this tag to their post, the bot detects the change and automatically locks the thread, preventing further replies.
  - **Benefit:** Keeps forums clean, prevents necro-posting on solved issues, and makes it clear to other users that the issue is resolved.

- [ ] **Post Quality and Structure Enforcement**
  - **Goal:** To ensure new posts in support-oriented forums contain necessary information from the start.
  - **Implementation:** For a given forum channel, admins can define a required template (e.g., must contain the strings "Problem Description:" and "Steps to Reproduce:"). The bot checks new posts and if the template is not met, it can either post a public reminder or temporarily remove the post and DM the user with the required format.
  - **Benefit:** Drastically reduces moderator workload and the back-and-forth required to get basic information from users.

- [ ] **Anti-Bumping and Conversation Flow Control**
  - **Goal:** To prevent users from unfairly "bumping" their posts to the top of the forum.
  - **Implementation:** The bot will check if the author of a new message is the same as the author of the previous message in the thread. If so, and if they are the OP, it can enforce a cooldown (e.g., the OP cannot reply to themselves within 24 hours unless someone else has replied). "Bump" messages would be silently deleted.
  - **Benefit:** Ensures a fair and orderly forum where threads gain visibility through genuine engagement, not artificial bumps.

- [ ] **Stale Thread Escalation**
  - **Goal:** To ensure user questions do not go unanswered.
  - **Implementation:** A background task runs periodically, scanning for threads that have had no replies for a configurable duration (e.g., 48 hours). The bot can then automatically apply a "Needs Attention ⚠️" tag and/or post a link to the thread in a private moderator channel.
  - **Benefit:** Acts as an SLA monitor for community support, improving responsiveness and making users feel heard.

- [ ] **Solution Suggestion & Pinning**
  - **Goal:** To make the correct answer in a long thread highly visible.
  - **Implementation:** A support role member can use a right-click Message Action or a command on a specific reply to mark it as a "Suggested Solution." The bot would then pin that reply or copy its content into a final, prominent message in the thread.
  - **Benefit:** Saves time for future readers looking for an answer and empowers the support team to highlight correct information, even if the OP is inactive.