# ShogiBotRP

ShogiBotRP is an interactive Discord bot that enables players to log their Shogi games, track their performance using an ELO rating system, and display leaderboards. Designed for Discord servers, the bot provides a streamlined way to manage Shogi competitions with automated data storage and real-time updates.

---

## Features

### **Core Features**
- **Log Games:** Players can input the results of their games using the `!addgame` command. The bot guides users through the process with prompts, asking for:
  - Game result (e.g., winner/loser).
  - Player colors (e.g., black or white).
  - Additional notes (optional).
- **ELO System:** ELO ratings are automatically updated for both players after each game, factoring in the K-factor and game result.
- **Leaderboards:** The `!leaderboard` command displays the top players in the server, along with their ELO ratings.
- **Profiles:** Users can view their individual stats (e.g., total wins, losses, current ELO) using the `!profile` command.
- **Game History:** The `!history` command allows players to view their logged game history.

### **Admin Features**
- **Manage Players:** Admins can use commands like `!removemember` to delete players or `!elowand` to adjust ELO manually.
- **Role Assignment:** Top players are automatically assigned special Discord roles based on their leaderboard rank.

### **Planned Features (TBD)**
- Notifications and reminders for players.
- Backup and restore system for database storage.
- Customizable settings for the ELO system and leaderboard display.

---

## Commands

### **Player Commands**
| Command         | Description                                                                                    |
|-----------------|------------------------------------------------------------------------------------------------|
| `!addgame`      | Users can start the process to log a Shogi game. Prompts for winner, loser, colors, and notes. |
| `!leaderboard`  | Display the top-ranked players along with their ELO ratings.                                   |
| `!profile`      | Show detailed stats for a specific player, including ELO, wins, and losses.                    |
| `!history`      | View the logged history of Shogi games for a specific player or globally.                      |
| `!signup`       | Users can register themselves as a new player in the system. Linked to Discord account.        |
| `!manual`       | Display the ShogiBot's list of bot commands.                                                   |

### **Admin Commands**
| Command         | Description                                                |
|-----------------|------------------------------------------------------------|
| `!admin`        | Manage users and ELO directly, with options for specific admin actions. |
| `!removemember` | Remove a player from the database.                         |
| `!elowand`      | Adjust a player’s ELO rating manually.                     |

---

## Requirements

### **Software Requirements**
- **Discord Bot Token**: You need a bot token from the [Discord Developer Portal](https://discord.com/developers/applications).
- **PostgreSQL Database**: The bot stores all data in a PostgreSQL database. Make sure your database is set up and running.

You can install dependencies via `requirements.txt`:
```bash
pip install -r requirements.txt
