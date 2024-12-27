import discord
from discord.ext import commands
from utils.db import fetch_query
import logging
from utils.decorators import command_in_progress, active_commands


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @command_in_progress()
    async def profile(self, ctx, *, player_name: str = None):
        """
        Displays the profile of a player or the invoker.
        """
        guild_id = ctx.guild.id

        if player_name is None:
            # Show the invoker's profile
            discord_user_id = ctx.author.id
            player_data = fetch_query(
                """
                SELECT player_name, elo, wins, losses, draws, games_played
                FROM players WHERE discord_user_id = %s AND guild_id = %s
                """,
                (discord_user_id, guild_id)
            )
            if not player_data:
                await ctx.send("You are not registered yet. Use `!signup` to register.")
                return
            member = ctx.author
        else:
            # Show the profile of the specified player
            player_data = fetch_query(
                """
                SELECT discord_user_id, player_name, elo, wins, losses, draws, games_played
                FROM players WHERE player_name = %s AND guild_id = %s
                """,
                (player_name, guild_id)
            )
            if not player_data:
                await ctx.send(f"No player found with the name `{player_name}` in this guild.")
                return
            member = ctx.guild.get_member(player_data[0]['discord_user_id'])

        if not player_data or not isinstance(player_data[0], dict):
            logging.error(f"Unexpected query result: {player_data}")
            await ctx.send("Error fetching your profile. Please contact an admin.")
            return

        # Parse data safely
        try:
            player_name = player_data[0].get('player_name')
            elo = int(player_data[0].get('elo', 1200))  # Default to 1200 if invalid
            wins = int(player_data[0].get('wins', 0))
            losses = int(player_data[0].get('losses', 0))
            draws = int(player_data[0].get('draws', 0))
            games_played = int(player_data[0].get('games_played', 0))
        except ValueError as e:
            logging.error(f"Data type error: {e}")
            await ctx.send("Error parsing your profile data. Please contact an admin.")
            return

        # Calculate Win/Loss/Draw Ratios
        total_games = wins + losses + draws
        win_ratio = (wins / total_games * 100) if total_games > 0 else 0.0
        loss_ratio = (losses / total_games * 100) if total_games > 0 else 0.0
        draw_ratio = (draws / total_games * 100) if total_games > 0 else 0.0

        # Get the player's roles (exclude @everyone)
        roles = [role.name for role in member.roles if role.name != "@everyone"] if member else []

        # Create an embed to display the profile
        embed = discord.Embed(title=f"📊 Profile of {player_name}", color=discord.Color.blue())
        embed.set_thumbnail(
            url=member.avatar.url if member and member.avatar else
            member.default_avatar.url if member else
            ctx.guild.icon.url if ctx.guild.icon else ""
        )
        embed.add_field(name="ELO", value=f"{elo}", inline=True)
        embed.add_field(name="Games Played", value=f"{games_played}", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Empty field for spacing

        embed.add_field(name="Wins", value=f"{wins}", inline=True)
        embed.add_field(name="Losses", value=f"{losses}", inline=True)
        embed.add_field(name="Draws", value=f"{draws}", inline=True)

        embed.add_field(name="Win Ratio", value=f"{win_ratio:.1f}%", inline=True)
        embed.add_field(name="Loss Ratio", value=f"{loss_ratio:.1f}%", inline=True)
        embed.add_field(name="Draw Ratio", value=f"{draw_ratio:.1f}%", inline=True)

        embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        )
        await ctx.send(embed=embed)

# The required setup function
async def setup(bot):
    await bot.add_cog(Profile(bot))
