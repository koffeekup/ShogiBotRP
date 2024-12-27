import discord
from discord.ext import commands
import asyncio
from utils.db import fetch_query
from utils.decorators import command_in_progress, active_commands


class History(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def history(self, ctx):
        """
        Displays game history for all players or a specific player in the current guild.
        """
        guild_id = ctx.guild.id

        await ctx.send("Please enter `ALL` to see the history of all players, or enter a player's name:")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=60, check=check)
            input_text = msg.content.strip()
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Please try again.")
            return

        if input_text.upper() == "ALL":
            # Fetch the most recent games for all players in the current guild
            games = fetch_query(
                """
                SELECT g.game_id, g.date_played, p1.player_name AS player1_name, p2.player_name AS player2_name,
                       g.player1_color, g.result, g.note
                FROM games g
                JOIN players p1 ON g.player1_id = p1.player_id
                JOIN players p2 ON g.player2_id = p2.player_id
                WHERE g.guild_id = %s
                ORDER BY g.date_played DESC
                LIMIT 25
                """,
                (guild_id,)
            )
            title = "Game History - All Players"
        else:
            # Fetch player ID for the given name in the current guild
            player_data = fetch_query(
                "SELECT player_id FROM players WHERE player_name = %s AND guild_id = %s",
                (input_text, guild_id)
            )
            if not player_data:
                await ctx.send(f"No player found with the name `{input_text}` in this guild.")
                return
            player_id = player_data[0]['player_id']

            # Fetch the most recent games for the player in the current guild
            games = fetch_query(
                """
                SELECT g.game_id, g.date_played, p1.player_name AS player1_name, p2.player_name AS player2_name,
                       g.player1_color, g.result, g.note
                FROM games g
                JOIN players p1 ON g.player1_id = p1.player_id
                JOIN players p2 ON g.player2_id = p2.player_id
                WHERE (g.player1_id = %s OR g.player2_id = %s) AND g.guild_id = %s
                ORDER BY g.date_played DESC
                LIMIT 25
                """,
                (player_id, player_id, guild_id)
            )
            title = f"Game History - {input_text}"

        if not games:
            await ctx.send("No games found.")
            return

        # Paginate the games (5 games per page)
        games_per_page = 5
        pages = []
        for i in range(0, len(games), games_per_page):
            chunk = games[i:i+games_per_page]
            embed = discord.Embed(title=title, color=discord.Color.blue())
            for game in chunk:
                game_id = game['game_id']
                timestamp = game['date_played'].strftime('%Y-%m-%d') if game['date_played'] else 'Unknown'
                player1_name = game['player1_name']
                player2_name = game['player2_name']
                player1_color = game['player1_color']
                result = game['result']
                note = game['note']

                # Determine sente (先手 - black) and gote (後手 - white) players
                if player1_color.lower() == 'sente':
                    sente_player = player1_name
                    gote_player = player2_name
                else:
                    sente_player = player2_name
                    gote_player = player1_name

                # Use emojis for player sides (black goes first in shogi)
                sente_emoji = '🟥'  # Red square for sente
                gote_emoji = '⬜'  # White square for gote

                # Format the result
                if result == '1-0':
                    result_text = f"{sente_player} (sente)"
                elif result == '0-1':
                    result_text = f"{gote_player} (gote)"
                else:
                    result_text = "Draw"

                # Add the game to the embed
                embed.add_field(
                    name=f"**{timestamp}**                                                                 ID: {game_id}",
                    value=(
                        f"{sente_emoji} **{sente_player}** vs {gote_emoji} **{gote_player}**\n"
                        f"**Result:** {result_text}\n"
                        f"{f'**Note:** {note[:200]}...' if note and len(note) > 200 else f'**Note:** {note}' if note else ''}"
                        f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    ),
                    inline=False
                )

            embed.set_footer(text=f"Page {len(pages)+1}/{((len(games) - 1) // games_per_page) + 1}")
            pages.append(embed)

        # Send the first page
        current_page = 0
        message = await ctx.send(embed=pages[current_page])

        # Add reactions for pagination if there are multiple pages
        if len(pages) > 1:
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
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60, check=reaction_check)
                    if str(reaction.emoji) == '➡️' and current_page < len(pages) - 1:
                        current_page += 1
                        await message.edit(embed=pages[current_page])
                    elif str(reaction.emoji) == '⬅️' and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=pages[current_page])
                    await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    break

    # The required setup function
async def setup(bot):
    await bot.add_cog(History(bot))
