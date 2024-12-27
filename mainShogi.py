import discord
from discord.ext import commands, tasks
import os
import logging
from dotenv import load_dotenv
from utils.db import fetch_query, execute_query
from utils.role_update import update_player_roles

# Load environment variables from .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)



# Load Cogs
async def load_cogs():
    """
    Dynamically load command cogs from the commands folder.
    """
    for filename in os.listdir('commands'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'commands.{filename[:-3]}')
                logging.info(f"Loaded cog: {filename}")
            except Exception as e:
                logging.error(f"Failed to load cog {filename}: {e}")

# Ensure guild exists in the database
async def ensure_guild_exists(guild):
    """
    Ensure a guild is present in the database.
    """
    guild_data = fetch_query(
        "SELECT guild_id FROM guilds WHERE guild_id = %s",
        (guild.id,)
    )
    if not guild_data:
        try:
            execute_query(
                "INSERT INTO guilds (guild_id, guild_name) VALUES (%s, %s)",
                (guild.id, guild.name)
            )
            logging.info(f"Added guild to database: {guild.name} (ID: {guild.id})")
        except Exception as e:
            logging.error(f"Failed to add guild {guild.name} (ID: {guild.id}) to database: {e}")

# Background task to update roles
@tasks.loop(hours=24)
async def update_roles_task():
    """
    Background task to update roles for all players in all guilds.
    """
    await bot.wait_until_ready()

    for guild in bot.guilds:
        logging.info(f"Updating roles for guild: {guild.name} (ID: {guild.id})")
        await ensure_guild_exists(guild)  # Ensure the guild exists in the database

        # Fetch all players for the current guild ordered by ELO descending
        players = fetch_query(
            "SELECT player_id, discord_user_id, elo FROM players WHERE guild_id = %s ORDER BY elo DESC",
            params=(guild.id,)
        )

        rankings = {}
        rank = 1
        for player in players:
            pid, discord_user_id, elo = player['player_id'], player['discord_user_id'], player['elo']
            rankings[pid] = rank
            rank += 1

        updated_members = 0
        for player in players:
            pid, discord_user_id, elo = player['player_id'], player['discord_user_id'], player['elo']
            member = guild.get_member(discord_user_id)
            if member:
                rank = rankings[pid]
                await update_player_roles(member, elo, rank)
                updated_members += 1

        logging.info(f"Finished updating roles for {updated_members} members in guild: {guild.name}")

# On bot ready
@bot.event
async def on_ready():
    """
    Event triggered when the bot is ready.
    """
    logging.info(f'Logged in as {bot.user.name}')
    await load_cogs()  # Load command cogs when the bot is ready

    for guild in bot.guilds:
        await ensure_guild_exists(guild)
        # Force caching of all members in the guild
        await guild.chunk()
        logging.info(f"Cached members for guild: {guild.name} (ID: {guild.id})")
        logging.info(f"Cached members for guild: {guild.name} (ID: {guild.id})")
        member_ids = [member.id for member in guild.members]
        logging.info(f"Cached member IDs for {guild.name}: {member_ids}")
    update_roles_task.start()  # Start the background task

# Run the bot
bot.run(BOT_TOKEN)
