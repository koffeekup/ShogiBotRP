# history.py

import discord
from discord.ext import commands
import asyncio
from utils.db import fetch_query


class History(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def history(self, ctx):
        """Displays game history for all players or a specific player."""
        await ctx.send("Please enter `ALL` to see the history of all players or enter a player's name:")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=60, check=check)
            input_text = msg.content.strip()
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Please try again.")
            return

        if input_text == "ALL":
            # Fetch the most recent games for all players (limit to 25 games)
            games = fetch_query("""
                SELECT g.game_id, g.timestamp, p1.player_name AS player1_name, p2.player_name AS player2_name,
                       g.player1_color, g.result, g.note
                FROM games g
                JOIN players p1 ON g.player1_id = p1.player_id
                JOIN players p2 ON g.player2_id = p2.player_id
                ORDER BY g.timestamp DESC
                LIMIT 25
            """)
            title = "Game History - All Players"
        else:
            # Fetch player ID
            player_data = fetch_query("SELECT player_id FROM players WHERE player_name = %s", (input_text,))
            if not player_data:
                await ctx.send(f"No player found with the name `{input_text}`.")
                return
            player_id = player_data[0][0]
            # Fetch the most recent games for the player (limit to 25 games)
            games = fetch_query("""
                SELECT g.game_id, g.timestamp, p1.player_name AS player1_name, p2.player_name AS player2_name,
                       g.player1_color, g.result, g.note
                FROM games g
                JOIN players p1 ON g.player1_id = p1.player_id
                JOIN players p2 ON g.player2_id = p2.player_id
                WHERE g.player1_id = %s OR g.player2_id = %s
                ORDER BY g.timestamp DESC
                LIMIT 25
            """, (player_id, player_id))
            title = f"Game History - {input_text}"

        if not games:
            await ctx.send("No games found.")
            return

        # Paginate the games
        pages = []
        for i in range(0, len(games), 5):
            chunk = games[i:i+5]
            embed = discord.Embed(title=title, color=discord.Color.blue())
            for game in chunk:
                game_id, timestamp, player1_name, player2_name, player1_color, result, note = game
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else 'Unknown'
                note_text = f"Note: {note}" if note else ""
                # Determine sente and gote players
                if player1_color.lower() == 'sente':
                    sente_player = player1_name
                    gote_player = player2_name
                else:
                    sente_player = player2_name
                    gote_player = player1_name
                # Use emojis
                sente_emoji = '⬜'
                gote_emoji = '⬛'
                # Format the result
                if result == '1-0':
                    result_text = f"{sente_player} wins"
                elif result == '0-1':
                    result_text = f"{gote_player} wins"
                else:
                    result_text = "Draw"
                # Build the field value
                embed.add_field(
                    name=f"Game ID: {game_id} | Date: {timestamp_str}",
                    value=(
                        f"{sente_emoji} **{sente_player}** vs {gote_emoji} **{gote_player}**\n"
                        f"**Result:** {result_text}\n"
                        f"{note_text}"
                    ),
                    inline=False
                )
            embed.set_footer(text=f"Page {len(pages)+1}/{min(5, ((len(games)-1)//5)+1)}")
            pages.append(embed)
            if len(pages) >= 5:
                break  # Limit to 5 pages

        # Send the first page
        current_page = 0
        message = await ctx.send(embed=pages[current_page])

        # Add reactions for pagination
        if len(pages) > 1:
            await message.add_reaction('⬅️')
            await message.add_reaction('➡️')

            def reaction_check(reaction, user):
                return user == ctx.author and reaction.message.id == message.id and str(reaction.emoji) in ['⬅️', '➡️']

            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60, check=reaction_check)
                    if str(reaction.emoji) == '➡️':
                        if current_page < len(pages) - 1:
                            current_page += 1
                            await message.edit(embed=pages[current_page])
                            await message.remove_reaction(reaction, user)
                    elif str(reaction.emoji) == '⬅️':
                        if current_page > 0:
                            current_page -= 1
                            await message.edit(embed=pages[current_page])
                            await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    break

    # The required setup function
async def setup(bot):
    await bot.add_cog(History(bot))
