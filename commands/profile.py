# commands/profile.py

import discord
from discord.ext import commands
from utils.db import fetch_query

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def profile(self, ctx, *, player_name: str = None):
        """Displays the profile of a player."""
        if player_name is None:
            # Show the invoker's profile
            discord_user_id = ctx.author.id
            player_data = fetch_query("""
                SELECT player_name, elo, wins, losses, draws, games_played
                FROM players WHERE discord_user_id = %s
            """, (discord_user_id,))
            if not player_data:
                await ctx.send("You are not registered yet. Use `!signup` to register.")
                return
            player_name, elo, wins, losses, draws, games_played = player_data[0]
            member = ctx.author
        else:
            # Show the profile of the specified player
            player_data = fetch_query("""
                SELECT discord_user_id, player_name, elo, wins, losses, draws, games_played
                FROM players WHERE player_name = %s
            """, (player_name,))
            if not player_data:
                await ctx.send(f"No player found with the name `{player_name}`.")
                return
            discord_user_id, player_name, elo, wins, losses, draws, games_played = player_data[0]
            member = ctx.guild.get_member(discord_user_id)
            if member is None:
                await ctx.send(f"Could not find Discord member for player `{player_name}`.")
                return

        # Calculate Win/Loss/Draw Ratio
        total_games = wins + losses + draws
        if total_games > 0:
            win_ratio = (wins / total_games) * 100
            loss_ratio = (losses / total_games) * 100
            draw_ratio = (draws / total_games) * 100
        else:
            win_ratio = loss_ratio = draw_ratio = 0.0

        # Get the player's roles
        roles = [role.name for role in member.roles if role.name != "@everyone"]

        # Create an embed to display the profile
        embed = discord.Embed(title=f"📊 Profile of {player_name}", color=discord.Color.blue())
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
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
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=embed)

# The required setup function
async def setup(bot):
    await bot.add_cog(Profile(bot))
