import discord
from discord.ext import commands
from utils.db import fetch_query
import asyncio
import re
from utils.decorators import command_in_progress, active_commands


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='leaderboard', aliases=['lb'])
    async def leaderboard(self, ctx):
        """
        Displays the leaderboard for the current guild with pagination.
        """
        guild_id = ctx.guild.id

        # Fetch players from the current guild, ordered by ELO descending
        players = fetch_query(
            "SELECT player_name, elo FROM players WHERE guild_id = %s ORDER BY elo DESC",
            (guild_id,)
        )

        # Check if the leaderboard is empty
        if not players:
            await ctx.send("The leaderboard is currently empty.")
            return

        # Pagination setup
        per_page = 5  # Number of players per page
        total_pages = (len(players) - 1) // per_page + 1  # Calculate total pages

        # Medal emojis for the top 3 players
        medals = ["🥇", "🥈", "🥉"]

        # Function to generate the embed for a specific page
        def get_page(page_number):
            start_index = page_number * per_page
            end_index = start_index + per_page
            page_players = players[start_index:end_index]

            embed = discord.Embed(
                title=f"🏆 **Leaderboard** - {ctx.guild.name}",
                description=f"Page {page_number + 1}/{total_pages}",
                color=discord.Color.gold()
            )

            # Build the leaderboard table
            table_lines = []
            for idx, player in enumerate(page_players):
                rank = start_index + idx + 1
                medal = medals[rank - 1] if rank <= 3 else f"#{rank}"
                name = player['player_name']
                elo = player['elo']

                # Format the line with rank, name, and ELO
                table_lines.append(f"{medal:<3} {name:<20} {elo:>5}")

            # Add the table to the embed
            table = "```" + "\n".join(table_lines) + "```"
            embed.add_field(name="Rankings", value=table, inline=False)
            embed.set_footer(text="Use ⬅️ and ➡️ to navigate pages. Timeout after 60s of inactivity.")
            return embed

        # Send the initial leaderboard page
        current_page = 0
        message = await ctx.send(embed=get_page(current_page))

        # Add reactions for pagination if there are multiple pages
        if total_pages > 1:
            await message.add_reaction('⬅️')
            await message.add_reaction('➡️')

            def reaction_check(reaction, user):
                return (
                    user == ctx.author and
                    reaction.message.id == message.id and
                    str(reaction.emoji) in ['⬅️', '➡️']
                )

            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=reaction_check)

                    if str(reaction.emoji) == '➡️' and current_page < total_pages - 1:
                        current_page += 1
                        await message.edit(embed=get_page(current_page))
                        await message.remove_reaction(reaction, user)
                    elif str(reaction.emoji) == '⬅️' and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=get_page(current_page))
                        await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    # Clear reactions after timeout
                    try:
                        await message.clear_reactions()
                    except discord.Forbidden:
                        pass
                    break

    # Setup function to load the cog
async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
