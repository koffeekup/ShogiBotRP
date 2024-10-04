# commands/admin.py

from discord.ext import commands
from config import ADMIN_ROLE_NAME
from utils.db import execute_query, fetch_query
from utils.elo import calculate_new_ratings
from utils.role_update import update_player_roles

def has_role_name(role_name):
    """Check if the user has the specified role name."""
    def predicate(ctx):
        return any(role.name == role_name for role in ctx.author.roles)
    return commands.check(predicate)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @has_role_name(ADMIN_ROLE_NAME)
    async def elowand(self, ctx, player_name: str, new_elo: int):
        """Changes a player's ELO to the specified value."""
        query = "UPDATE players SET elo = %s WHERE player_name = %s"
        execute_query(query, (new_elo, player_name))
        await ctx.send(f"Successfully changed {player_name}'s ELO to {new_elo}.")

    @commands.command()
    @has_role_name(ADMIN_ROLE_NAME)
    async def removemember(self, ctx, player_name: str):
        """Removes a player from the database."""
        query = "DELETE FROM players WHERE player_name = %s"
        execute_query(query, (player_name,))
        await ctx.send(f"Removed player {player_name} from the database.")

    @commands.command()
    @has_role_name(ADMIN_ROLE_NAME)
    async def changename(self, ctx, old_name: str, new_name: str):
        """Changes a player's name in the database."""
        query = "UPDATE players SET player_name = %s WHERE player_name = %s"
        execute_query(query, (new_name, old_name))
        await ctx.send(f"Changed player name from {old_name} to {new_name}.")

    @commands.command()
    @has_role_name(ADMIN_ROLE_NAME)
    async def clear(self, ctx, num_messages: int):
        """Clears the specified number of messages."""
        await ctx.channel.purge(limit=num_messages + 1)  # +1 to include the command message
        await ctx.send(f"Cleared {num_messages} messages.", delete_after=5)

    @commands.command(name='removegame')
    @commands.has_role(ADMIN_ROLE_NAME)
    async def remove_game(self, ctx, game_id: int):
        """Removes a game by its ID (Admin only)."""
        # Fetch the game details
        game_data = fetch_query("""
                SELECT game_id, player1_id, player2_id, player1_color, result, note, timestamp
                FROM games WHERE game_id = %s
            """, (game_id,))
        if not game_data:
            await ctx.send(f"No game found with ID `{game_id}`.")
            return
        game = game_data[0]
        game_id, player1_id, player2_id, player1_color, result, note, timestamp = game

        # Fetch players' data
        player1_data = fetch_query("""
                SELECT player_id, discord_user_id, elo, wins, losses, draws, games_played
                FROM players WHERE player_id = %s
            """, (player1_id,))
        player2_data = fetch_query("""
                SELECT player_id, discord_user_id, elo, wins, losses, draws, games_played
                FROM players WHERE player_id = %s
            """, (player2_id,))

        if not player1_data or not player2_data:
            await ctx.send("One or both players not found.")
            return

        player1 = player1_data[0]
        player2 = player2_data[0]

        # Now, we need to recalculate ELOs and stats for both players
        # Fetch all games involving both players, excluding the game being removed
        # Combine and sort the games for each player
        all_games_data = fetch_query("""
                SELECT g.game_id, g.player1_id, g.player2_id, g.player1_color, g.result, g.timestamp
                FROM games g
                WHERE (g.player1_id = %s OR g.player2_id = %s OR g.player1_id = %s OR g.player2_id = %s) AND g.game_id != %s
                ORDER BY g.timestamp ASC
            """, (player1_id, player1_id, player2_id, player2_id, game_id))

        # Remove duplicate games
        all_games = list({g[0]: g for g in all_games_data}.values())
        # Sort by timestamp
        all_games.sort(key=lambda x: x[5])  # x[5] is timestamp

        # Initialize players' stats and ELOs
        starting_elo = 1000  # Adjust based on your starting ELO
        player_stats = {}
        player_ids = set()
        for game in all_games:
            player_ids.update([game[1], game[2]])

        for pid in player_ids:
            player_stats[pid] = {
                'elo': starting_elo,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'games_played': 0,
            }

        # For each game, update the stats and ELOs
        for game in all_games:
            g_id, p1_id, p2_id, p1_color, g_result, g_timestamp = game
            # Fetch current ELOs
            p1_elo = player_stats[p1_id]['elo']
            p2_elo = player_stats[p2_id]['elo']

            # Map result to scores for each player
            if g_result == '1-0':
                if p1_color.lower() == 'sente':
                    score_p1 = 1.0
                    score_p2 = 0.0
                else:
                    score_p1 = 0.0
                    score_p2 = 1.0
            elif g_result == '0-1':
                if p1_color.lower() == 'sente':
                    score_p1 = 0.0
                    score_p2 = 1.0
                else:
                    score_p1 = 1.0
                    score_p2 = 0.0
            else:
                score_p1 = 0.5
                score_p2 = 0.5

            # Calculate new ELOs
            new_p1_elo, new_p2_elo = calculate_new_ratings(p1_elo, p2_elo, score_p1, score_p2)

            # Update player stats
            for pid, score, new_elo in [(p1_id, score_p1, new_p1_elo), (p2_id, score_p2, new_p2_elo)]:
                player_stats[pid]['elo'] = new_elo
                player_stats[pid]['games_played'] += 1
                if score == 1.0:
                    player_stats[pid]['wins'] += 1
                elif score == 0.0:
                    player_stats[pid]['losses'] += 1
                else:
                    player_stats[pid]['draws'] += 1

        # Update the players' records in the database
        for pid in player_stats:
            stats = player_stats[pid]
            update_player_query = """
                UPDATE players SET elo = %s, wins = %s, losses = %s, draws = %s, games_played = %s, last_updated = NOW()
                WHERE player_id = %s
                """
            execute_query(update_player_query,
                          (stats['elo'], stats['wins'], stats['losses'], stats['draws'], stats['games_played'], pid))

        # Delete the game from the games table
        execute_query("DELETE FROM games WHERE game_id = %s", (game_id,))

        # Recalculate rankings and update roles for affected players
        # Fetch all players ordered by ELO descending
        players = fetch_query("SELECT player_id, discord_user_id, elo FROM players ORDER BY elo DESC")

        # Assign new ranks based on updated ELOs
        rankings = {}
        rank = 1
        for player in players:
            pid, discord_user_id, elo = player
            rankings[pid] = rank
            rank += 1

        # Update roles for the top players (adjust as needed)
        affected_players = players[:15]  # Top 15 players to cover all ranking roles

        guild = ctx.guild
        updated_members = 0

        for player in affected_players:
            pid, discord_user_id, elo = player
            member = guild.get_member(discord_user_id)
            if member:
                rank = rankings[pid]
                await update_player_roles(member, elo, rank)
                updated_members += 1

        # Also update roles for other involved players if they are not in the top 15
        for pid in player_stats:
            if pid not in [p[0] for p in affected_players]:
                player_data = fetch_query("SELECT discord_user_id FROM players WHERE player_id = %s", (pid,))
                if player_data:
                    discord_id = player_data[0][0]
                    member = guild.get_member(discord_id)
                    if member:
                        rank = rankings.get(pid, None)
                        await update_player_roles(member, player_stats[pid]['elo'], rank)

        await ctx.send(f"Game with ID `{game_id}` has been removed, and players' stats and ELOs have been updated.")

    @remove_game.error
    async def remove_game_error(self, ctx, error):
        if isinstance(error, commands.MissingRole):
            await ctx.send("You do not have permission to use this command.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid arguments. Usage: `!removegame <gameID>`")
        else:
            await ctx.send(f"An error occurred: {error}")

# The required setup function
async def setup(bot):
    await bot.add_cog(Admin(bot))
