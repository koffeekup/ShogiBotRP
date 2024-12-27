import discord
import logging
from discord.ext import commands
from config import ADMIN_ROLE_NAME
from utils.db import execute_query, fetch_query
from utils.elo import calculate_new_ratings
from utils.role_update import update_player_roles
from utils.decorators import command_in_progress, active_commands


def has_role_name(role_name):
    """Check if the user has the specified role name."""
    def predicate(ctx):
        return any(role.name == role_name for role in ctx.author.roles)
    return commands.check(predicate)


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @command_in_progress()
    @has_role_name(ADMIN_ROLE_NAME)
    async def elowand(self, ctx, player_name: str, new_elo: int):
        """Changes a player's ELO to the specified value."""
        guild_id = ctx.guild.id

        # Ensure the player exists in the current guild
        player_data = fetch_query(
            "SELECT player_id FROM players WHERE player_name = %s AND guild_id = %s",
            (player_name, guild_id)
        )
        if not player_data:
            await ctx.send(f"Player `{player_name}` not found in this guild.")
            return

        execute_query(
            "UPDATE players SET elo = %s WHERE player_name = %s AND guild_id = %s",
            (new_elo, player_name, guild_id)
        )
        await ctx.send(f"Successfully changed {player_name}'s ELO to {new_elo}.")

    @commands.command()
    @command_in_progress()
    @has_role_name(ADMIN_ROLE_NAME)
    async def removemember(self, ctx, player_name: str):
        """
        Removes a player and their associated data from the database.
        """
        guild_id = ctx.guild.id
        user_name = ctx.author.name
        logging.info(
            f"Attempting to remove player `{player_name}` in guild `{ctx.guild.name}` (ID: {guild_id}) by admin `{user_name}`")

        # Check if the player exists in the guild
        player_data = fetch_query(
            "SELECT player_id, discord_user_id FROM players WHERE player_name = %s AND guild_id = %s",
            (player_name, guild_id)
        )
        if not player_data:
            logging.warning(f"Player `{player_name}` not found in guild `{ctx.guild.name}` (ID: {guild_id})")
            await ctx.send(f"Player `{player_name}` not found in this guild.")
            return

        player_id = player_data[0]["player_id"]
        discord_user_id = player_data[0]["discord_user_id"]

        try:
            # Delete the player record, cascading will handle associated data
            execute_query(
                "DELETE FROM players WHERE player_id = %s AND guild_id = %s",
                (player_id, guild_id)
            )
            logging.info(
                f"Successfully removed player `{player_name}` (ID: {player_id}) from guild `{ctx.guild.name}` (ID: {guild_id})")
            await ctx.send(f"Successfully removed player `{player_name}` and associated data from the database.")
        except Exception as e:
            logging.error(
                f"Failed to remove player `{player_name}` (ID: {player_id}) from guild `{ctx.guild.name}`: {e}")
            await ctx.send(f"An error occurred while removing `{player_name}`. Please contact an admin.")


    @commands.command()
    @command_in_progress()
    @has_role_name(ADMIN_ROLE_NAME)
    async def clear(self, ctx, num_messages: int):
        """Clears the specified number of messages."""
        await ctx.channel.purge(limit=num_messages + 1)  # +1 to include the command message
        await ctx.send(f"Cleared {num_messages} messages.", delete_after=5)

    @commands.command(name='removegame')
    @command_in_progress()
    @has_role_name(ADMIN_ROLE_NAME)
    async def remove_game(self, ctx, game_id: int):
        """Removes a game by its ID (Admin only)."""
        guild_id = ctx.guild.id

        # Check if the game exists in the current guild
        game_data = fetch_query(
            "SELECT game_id FROM games WHERE game_id = %s AND guild_id = %s",
            (game_id, guild_id)
        )
        if not game_data:
            await ctx.send(f"Game with ID `{game_id}` not found in this guild.")
            return

        # Delete the game from the database
        execute_query("DELETE FROM games WHERE game_id = %s AND guild_id = %s", (game_id, guild_id))
        await ctx.send(f"Game with ID `{game_id}` has been removed.")

    @remove_game.error
    async def remove_game_error(self, ctx, error):
        """Handles errors for the remove_game command."""
        if isinstance(error, commands.MissingRole):
            await ctx.send("You do not have permission to use this command.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid arguments. Usage: `!removegame <gameID>`")
        else:
            await ctx.send(f"An error occurred: {error}")



# The required setup function
async def setup(bot):
    await bot.add_cog(Admin(bot))
