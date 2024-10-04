import discord
from discord.ext import commands
from utils.db import fetch_query
import asyncio
import re

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def leaderboard(self, ctx):
        """Displays the leaderboard with pagination."""
        # Fetch all players from the database, ordered by ELO descending
        players = fetch_query("SELECT player_name, elo FROM players ORDER BY elo DESC")

        # Check if the leaderboard is empty
        if not players:
            await ctx.send("The leaderboard is currently empty.")
            return

        # Prepare pagination
        per_page = 5  # Number of players per page
        total_pages = (len(players) - 1) // per_page + 1  # Calculate total pages

        # Medal emojis for top 3 players
        medals = ["🥇", "🥈", "🥉"]

        # Function to calculate the visual length of a string (accounting for emojis)
        def visual_length(s):
            # Emojis are generally considered to be double-width characters in monospace fonts
            emoji_pattern = re.compile(
                "[\U0001F1E6-\U0001F1FF]"  # flags
                "|[\U0001F300-\U0001F5FF]"  # symbols & pictographs
                "|[\U0001F600-\U0001F64F]"  # emoticons
                "|[\U0001F680-\U0001F6FF]"  # transport & map symbols
                "|[\U0001F700-\U0001F77F]"  # alchemical symbols
                "|[\U0001F780-\U0001F7FF]"  # Geometric Shapes Extended
                "|[\U0001F800-\U0001F8FF]"  # Supplemental Arrows-C
                "|[\U0001F900-\U0001F9FF]"  # Supplemental Symbols and Pictographs
                "|[\U0001FA00-\U0001FA6F]"  # Chess Symbols
                "|[\U0001FA70-\U0001FAFF]"  # Symbols and Pictographs Extended-A
                "|[\U00002702-\U000027B0]"  # Dingbats
                "|[\U000024C2-\U0001F251]"  # Enclosed characters
                , flags=re.UNICODE)
            length = 0
            for char in s:
                if emoji_pattern.match(char):
                    length += 2  # Emojis take up 2 spaces
                else:
                    length += 1
            return length

        # Function to generate the embed for a given page
        def get_page(page_number):
            start_index = page_number * per_page
            end_index = start_index + per_page
            page_players = players[start_index:end_index]

            embed = discord.Embed(
                title="🏆 **Leaderboard**",
                description=f"Page {page_number + 1} of {total_pages}",
                color=discord.Color.gold()
            )

            # Prepare the table header
            rank_col_width = 6  # Adjusted to account for emoji width
            name_col_width = 20
            elo_col_width = 5
            total_line_width = rank_col_width + name_col_width + elo_col_width + 4  # 4 for spaces and padding

            header = f"{'Rank':<{rank_col_width}} {'Name':<{name_col_width}} {'ELO':>{elo_col_width}}\n"
            separator = "-" * total_line_width
            table_lines = [header, separator]

            for idx, player in enumerate(page_players):
                rank = start_index + idx + 1
                # Assign medal emojis or rank number
                if rank <= 3:
                    rank_display = f"{medals[rank - 1]}"
                else:
                    rank_display = f"#{rank}"
                rank_display += " "  # Add a space after the rank

                # Calculate the visual length of the rank_display
                rank_display_length = visual_length(rank_display)

                # Adjust rank_col_width for each line
                rank_padding = rank_col_width - rank_display_length
                rank_text = rank_display + ' ' * rank_padding

                name = player[0]
                # Truncate the name if it's too long
                if visual_length(name) > name_col_width:
                    name = name[:name_col_width - 1] + '…'

                elo = player[1]

                # Format the line
                line = f"{rank_text}{name:<{name_col_width}} {elo:>{elo_col_width}}"
                table_lines.append(line)

            # Combine all lines into a single code block
            table = "```" + "\n".join(table_lines) + "```"

            embed.description += "\n" + table
            embed.set_footer(text="Use ⬅️ and ➡️ to navigate pages. Timeout after 60s of inactivity.")
            return embed

        # Send the initial embed
        current_page = 0
        message = await ctx.send(embed=get_page(current_page))

        # Add reactions for navigation if multiple pages exist
        if total_pages > 1:
            try:
                await message.add_reaction('⬅️')
                await message.add_reaction('➡️')
            except discord.HTTPException as e:
                print(f"Error adding reactions: {e}")
                await ctx.send("An error occurred while adding reactions.")
                return

            def check(reaction, user):
                return (
                    user == ctx.author and
                    str(reaction.emoji) in ['⬅️', '➡️'] and
                    reaction.message.id == message.id
                )

            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)

                    if str(reaction.emoji) == '➡️':
                        if current_page < total_pages - 1:
                            current_page += 1
                            await message.edit(embed=get_page(current_page))
                        await message.remove_reaction(reaction, user)
                    elif str(reaction.emoji) == '⬅️':
                        if current_page > 0:
                            current_page -= 1
                            await message.edit(embed=get_page(current_page))
                        await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    # Timeout: remove reactions to indicate the end of interaction
                    try:
                        await message.clear_reactions()
                    except:
                        pass
                    break

    # Setup function to load the cog
async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
