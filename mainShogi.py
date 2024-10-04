# mainShogi.py

import discord
from discord.ext import commands, tasks
from config import BOT_TOKEN
from utils.db import fetch_query
from utils.role_update import update_player_roles
import os

# Set the working directory to the directory of the script
os.chdir(os.path.dirname(os.path.abspath(__file__)))


# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Load Cogs
async def load_cogs():
    for filename in os.listdir('commands'):
        if filename.endswith('.py'):
            await bot.load_extension(f'commands.{filename[:-3]}')
# Background task to update roles
@tasks.loop(hours=24)
async def update_roles_task():
    """Background task to update roles for all players every hour."""
    await bot.wait_until_ready()
    guild = discord.utils.get(bot.guilds, name='Shogi Club')  # Replace with your server name
    if not guild:
        print("Guild not found.")
        return

    # Fetch all players ordered by ELO descending
    players = fetch_query("SELECT player_id, discord_user_id, elo FROM players ORDER BY elo DESC")

    # Assign ranks
    rankings = {}
    rank = 1
    for player in players:
        pid, discord_user_id, elo = player
        rankings[pid] = rank
        rank += 1

    updated_members = 0

    for player in players:
        pid, discord_user_id, elo = player
        member = guild.get_member(discord_user_id)
        if member:
            rank = rankings[pid]
            await update_player_roles(member, elo, rank)
            updated_members += 1

    print(f"Background role update completed. Updated roles for {updated_members} members.")

# On bot ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await load_cogs()
    update_roles_task.start()

# Run the bot
bot.run(BOT_TOKEN)
