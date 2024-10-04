import discord
from discord.ext import commands
import asyncio
from utils.db import execute_query, fetch_query
from utils.elo import calculate_new_ratings
from utils.role_update import update_player_roles


class AddGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def addgame(self, ctx, opponent_name: str):
        """Handles the process of adding a new game result."""

        # Prevent players from adding a game against themselves
        invoker_data = fetch_query("SELECT player_name FROM players WHERE discord_user_id = %s", (ctx.author.id,))
        if not invoker_data:
            await ctx.send("You are not registered yet. Use `!signup` to register.")
            return
        invoker_name = invoker_data[0][0]
        if opponent_name == invoker_name:
            await ctx.send("You cannot add a game against yourself.")
            return

        # Step 1: Get the invoker's color
        color_embed = discord.Embed(
            title="**Select Color**",
            description="Please select your color:",
            color=discord.Color.blue()
        )
        color_embed.add_field(name="1️⃣ Sente (先手)", value="--------------", inline=True)
        color_embed.add_field(name="2️⃣ Gote (後手)", value="--------------", inline=True)
        color_message = await ctx.send(embed=color_embed)
        await color_message.add_reaction('1️⃣')  # White
        await color_message.add_reaction('2️⃣')  # gote

        def color_reaction_check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['1️⃣', '2️⃣'] and reaction.message.id == color_message.id

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60, check=color_reaction_check)
            if str(reaction.emoji) == '1️⃣':
                player_color = 'sente'
            else:
                player_color = 'gote'
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Please try again.")
            return

        # Step 2: Get the game result
        result_embed = discord.Embed(
            title="🏁 **Game Result**",
            description="Please select the game result:",
            color=discord.Color.green()
        )
        result_embed.add_field(name="1️⃣ 1-0 (Sente Won)", value="-------------", inline=False)
        result_embed.add_field(name="2️⃣ 0-1 (Gote Won)", value="-------------", inline=False)
        result_embed.add_field(name="3️⃣ 0.5-0.5 (Draw)", value="--------------", inline=False)
        result_message = await ctx.send(embed=result_embed)
        await result_message.add_reaction('1️⃣')
        await result_message.add_reaction('2️⃣')
        await result_message.add_reaction('3️⃣')

        def result_reaction_check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['1️⃣', '2️⃣', '3️⃣'] and reaction.message.id == result_message.id

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60, check=result_reaction_check)
            if str(reaction.emoji) == '1️⃣':
                result = '1-0'
            elif str(reaction.emoji) == '2️⃣':
                result = '0-1'
            else:
                result = '0.5-0.5'
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Please try again.")
            return

        # Step 3: Confirm with both players
        opponent_data = fetch_query("SELECT discord_user_id, player_id FROM players WHERE player_name = %s", (opponent_name,))
        if not opponent_data:
            await ctx.send(f"Opponent **{opponent_name}** not found.")
            return
        opponent_discord_id, opponent_id = opponent_data[0]

        # Prevent adding a game against oneself (additional check using discord ID)
        if opponent_discord_id == ctx.author.id:
            await ctx.send("You cannot add a game against yourself.")
            return

        # Send a message that pings both players
        await ctx.send(f"{ctx.author.mention} vs <@{opponent_discord_id}>")

        # Create confirmation embed
        confirmation_embed = discord.Embed(
            title="✅ **Game Confirmation**",
            description=(
                f"**Players:** {ctx.author.mention} vs <@{opponent_discord_id}>\n"
                f"**Result:** {result}\n"
                f"**{ctx.author.display_name}** played **{player_color.capitalize()}**"
            ),
            color=discord.Color.orange()
        )
        confirmation_embed.set_footer(text="Both players must react with ✅ to confirm.")
        confirmation_message = await ctx.send(embed=confirmation_embed)
        await confirmation_message.add_reaction('✅')

        # Wait for both players to confirm
        confirmed_players = set()

        def confirmation_check(reaction, user):
            return str(reaction.emoji) == '✅' and reaction.message.id == confirmation_message.id and \
                   user.id in [ctx.author.id, opponent_discord_id]

        try:
            while len(confirmed_players) < 2:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=120, check=confirmation_check)
                if user.id not in confirmed_players:
                    confirmed_players.add(user.id)
                    await ctx.send(f"{user.mention} has confirmed the game.")
        except asyncio.TimeoutError:
            await ctx.send("Confirmation timed out. Please try again.")
            return

        # Step 4: Ask if the invoker wants to add a note
        note_prompt_embed = discord.Embed(
            title="📝 **Add a Note?**",
            description="Would you like to add a note to this game?\nReact with ✅ to add a note or ❌ to skip.",
            color=discord.Color.blue()
        )
        note_prompt_message = await ctx.send(embed=note_prompt_embed)
        await note_prompt_message.add_reaction('✅')
        await note_prompt_message.add_reaction('❌')

        def note_reaction_check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == note_prompt_message.id

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60, check=note_reaction_check)
            if str(reaction.emoji) == '✅':
                await ctx.send("Please enter your note (maximum 70 characters). You have 180 seconds to reply.")
                while True:
                    try:
                        note_message = await self.bot.wait_for(
                            'message',
                            timeout=180,
                            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                        )
                        note = note_message.content.strip()
                        if len(note) > 70:
                            await ctx.send("Your note exceeds 70 characters. Please enter a shorter note.")
                            continue
                        break
                    except asyncio.TimeoutError:
                        await ctx.send("You took too long to respond. No note will be added.")
                        note = None
                        break
            else:
                note = None
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. No note will be added.")
            note = None

        # Step 5: Update the database and ELO ratings
        # Fetch current ELOs and other stats
        invoker_data = fetch_query("SELECT player_id, elo, wins, losses, draws, games_played FROM players WHERE discord_user_id = %s", (ctx.author.id,))
        opponent_data = fetch_query("SELECT player_id, elo, wins, losses, draws, games_played FROM players WHERE discord_user_id = %s", (opponent_discord_id,))

        if not invoker_data or not opponent_data:
            await ctx.send("One or both players are not registered.")
            return

        invoker_id, invoker_elo, invoker_wins, invoker_losses, invoker_draws, invoker_games_played = invoker_data[0]
        opponent_id, opponent_elo, opponent_wins, opponent_losses, opponent_draws, opponent_games_played = opponent_data[0]

        # Map result to scores
        if result == '1-0':
            if player_color == 'sente':
                score_invoker = 1.0
                score_opponent = 0.0
            else:
                score_invoker = 0.0
                score_opponent = 1.0
            if score_invoker == 1.0:
                invoker_wins += 1
                opponent_losses += 1
            else:
                invoker_losses += 1
                opponent_wins += 1
        elif result == '0-1':
            if player_color == 'sente':
                score_invoker = 0.0
                score_opponent = 1.0
            else:
                score_invoker = 1.0
                score_opponent = 0.0
            if score_invoker == 1.0:
                invoker_wins += 1
                opponent_losses += 1
            else:
                invoker_losses += 1
                opponent_wins += 1
        else:
            score_invoker = 0.5
            score_opponent = 0.5
            invoker_draws += 1
            opponent_draws += 1

        invoker_games_played += 1
        opponent_games_played += 1

        # Calculate new ELO ratings using your rating system
        new_invoker_elo, new_opponent_elo = calculate_new_ratings(invoker_elo, opponent_elo, score_invoker, score_opponent)

        # Update players' ELOs and stats in the database
        update_player_query = """
        UPDATE players SET elo = %s, wins = %s, losses = %s, draws = %s, games_played = %s, last_updated = NOW()
        WHERE player_id = %s
        """
        execute_query(update_player_query, (new_invoker_elo, invoker_wins, invoker_losses, invoker_draws, invoker_games_played, invoker_id))
        execute_query(update_player_query, (new_opponent_elo, opponent_wins, opponent_losses, opponent_draws, opponent_games_played, opponent_id))

        # Step 6: Insert the game into the games table (including the note)
        insert_game_query = """
        INSERT INTO games (player1_id, player2_id, player1_color, result, note)
        VALUES (%s, %s, %s, %s, %s)
        """
        execute_query(insert_game_query, (invoker_id, opponent_id, player_color, result, note))

        # Step 7: Update roles for affected players
        # Fetch updated player rankings
        players = fetch_query("SELECT player_id, discord_user_id, elo FROM players ORDER BY elo DESC")

        # Assign new ranks based on updated ELOs
        rankings = {}
        rank = 1
        for player in players:
            pid, discord_user_id, elo = player
            rankings[pid] = rank
            rank += 1

        # Update roles for the top 15 players (adjust as needed)
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

        # Also update roles for the invoker and opponent if they are not in the top 15
        for pid, discord_id, elo in [(invoker_id, ctx.author.id, new_invoker_elo), (opponent_id, opponent_discord_id, new_opponent_elo)]:
            if pid not in [p[0] for p in affected_players]:
                member = guild.get_member(discord_id)
                if member:
                    rank = rankings.get(pid, None)
                    await update_player_roles(member, elo, rank)

        await ctx.send("Game recorded and ELOs updated!")
# Error handler for the addgame command
    @addgame.error
    async def addgame_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ **Error:** Missing opponent name.\n**Usage:** `!addgame <opponent_name>`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ **Error:** Invalid argument type.\n**Usage:** `!addgame <opponent_name>`")
        else:
            # For any other errors, you can either ignore or handle them as needed
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
            # Optionally, log the error or re-raise
            raise error
# The required setup function
async def setup(bot):
    await bot.add_cog(AddGame(bot))
