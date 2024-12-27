import discord
from discord.ext import commands
import asyncio
from utils.db import execute_query, fetch_query
from utils.elo import calculate_new_ratings
from utils.role_update import update_player_roles
import logging
from utils.decorators import command_in_progress, active_commands


class AddGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_player_data(self, query, params):
        """Helper function to fetch a single player's data."""
        result = fetch_query(query, params)
        if not result:
            return None
        return result[0]

    async def get_reaction(self, ctx, message, options, timeout=60):
        """Helper function to get a reaction from a user."""
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in options and reaction.message.id == message.id

        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=timeout, check=check)
            return str(reaction.emoji)
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Please try again.")
            return None

    async def get_confirmations(self, ctx, message, participants, timeout=120):
        """Helper function to wait for confirmations from participants."""
        confirmed_players = set()

        def check(reaction, user):
            return str(reaction.emoji) == '✅' and reaction.message.id == message.id and user.id in participants

        try:
            while len(confirmed_players) < len(participants):
                reaction, user = await self.bot.wait_for('reaction_add', timeout=timeout, check=check)
                confirmed_players.add(user.id)
                await ctx.send(f"{user.mention} has confirmed the game.")
            return True
        except asyncio.TimeoutError:
            return False

    @commands.command()
    @command_in_progress()
    async def addgame(self, ctx, opponent_name: str):
        """
        Handles the process of adding a new game result for the current guild.
        """
        guild_id = ctx.guild.id
        logging.info(f"AddGame invoked in guild `{guild_id}` with opponent `{opponent_name}`.")

        # Fetch invoker data
        invoker_data = await self.fetch_player_data(
            "SELECT player_name, player_id FROM players WHERE discord_user_id = %s AND guild_id = %s",
            (ctx.author.id, guild_id)
        )

        if not invoker_data:
            await ctx.send("❌ You are not registered yet. Use `!signup` to register.")
            return

        invoker_name, invoker_id = invoker_data['player_name'], int(invoker_data['player_id'])

        if opponent_name == invoker_name:
            await ctx.send("❌ You cannot add a game against yourself.")
            return

        # Validate opponent's name format
        import re
        if not re.match(r"^[A-Z][a-z]+[A-Z]$", opponent_name):
            await ctx.send(
                "❌ The opponent's name must be formatted like `JohnC` (capitalized first name and last initial, and no @ symbol).")
            return

        # Check if the opponent exists in the database
        opponent_data = await self.fetch_player_data(
            "SELECT player_id, discord_user_id FROM players WHERE player_name = %s AND guild_id = %s",
            (opponent_name, guild_id)
        )

        if not opponent_data:
            await ctx.send(
                f"❌ Opponent **{opponent_name}** does not exist or is not registered. They need to use `!signup` first.")
            return

        # Extract opponent details
        opponent_id, opponent_discord_id = opponent_data['player_id'], opponent_data['discord_user_id']

        # Ensure the opponent is not the invoker
        if opponent_discord_id == ctx.author.id:
            await ctx.send("❌ You cannot add a game against yourself.")
            return

        # Confirm opponent is a member of the guild
        try:
            opponent_member = await ctx.guild.fetch_member(opponent_discord_id)
        except discord.NotFound:
            await ctx.send(f"❌ Opponent **{opponent_name}** is not a member of this guild.")
            return
        except discord.HTTPException:
            await ctx.send("❌ Error fetching the opponent's membership information. Please try again later.")
            return

        # Log the successful validation of the opponent
        logging.info(f"Validated opponent `{opponent_name}` with Discord ID `{opponent_discord_id}`.")

        # Step 1: Get the invoker's color
        color_embed = discord.Embed(
            title="**Select Color**",
            description="Please select your color:",
            color=discord.Color.blue()
        )
        color_embed.add_field(name="🟥 Sente (先手)", value="--------------", inline=True)
        color_embed.add_field(name="⬜ Gote  (後手)", value="--------------", inline=True)
        color_message = await ctx.send(embed=color_embed)
        await color_message.add_reaction('🟥')
        await color_message.add_reaction('⬜')

        reaction = await self.get_reaction(ctx, color_message, ['🟥', '⬜'])
        if not reaction:
            return

        player_color = 'sente' if reaction == '🟥' else 'gote'

        # Step 2: Get the game result
        result_embed = discord.Embed(
            title="🏁 **Game Result**",
            description="Please select the game result:",
            color=discord.Color.green()
        )
        result_embed.add_field(name="🟥 1-0 (Sente Won)", value="-------------", inline=False)
        result_embed.add_field(name="⬜ 0-1 (Gote Won)", value="-------------", inline=False)
        result_embed.add_field(name="3️⃣ 0.5-0.5 (Draw)", value="--------------", inline=False)
        result_message = await ctx.send(embed=result_embed)
        await result_message.add_reaction('🟥')
        await result_message.add_reaction('⬜')
        await result_message.add_reaction('3️⃣')

        reaction = await self.get_reaction(ctx, result_message, ['🟥', '⬜', '3️⃣'])
        if not reaction:
            return

        result = {'🟥': '1-0', '⬜': '0-1', '3️⃣': '0.5-0.5'}[reaction]

        # Step 3: Validate Opponent
        opponent_data = await self.fetch_player_data(
            "SELECT player_id, discord_user_id FROM players WHERE player_name = %s AND guild_id = %s",
            (opponent_name, guild_id)
        )

        if not opponent_data:
            await ctx.send(f"Opponent **{opponent_name}** not found.")
            return

        opponent_id, opponent_discord_id = opponent_data['player_id'], opponent_data['discord_user_id']

        if opponent_discord_id == ctx.author.id:
            await ctx.send("You cannot add a game against yourself.")
            return

        # Confirm opponent membership in the guild
        try:
            opponent_member = await ctx.guild.fetch_member(opponent_discord_id)
        except discord.NotFound:
            await ctx.send(f"Opponent **{opponent_name}** is not a member of this guild.")
            return

        # Confirm game details
        confirmation_embed = discord.Embed(
            title="✅ **Game Confirmation**",
            description=(
                f"**Players:** {ctx.author.mention} vs {opponent_member.mention}\n"
                f"**Result:** {result}\n"
                f"**{ctx.author.display_name}** played **{player_color.capitalize()}**"
            ),
            color=discord.Color.orange()
        )

        confirmation_message = await ctx.send(embed=confirmation_embed)
        await confirmation_message.add_reaction('✅')

        # Ping both players with instructions
        await ctx.send(
            f"🔔 {ctx.author.mention} and {opponent_member.mention}, please double-check the game details above. "
            f"If everything looks correct, react to the confirmation message with ✅ to confirm the game."
        )

        if not await self.get_confirmations(ctx, confirmation_message, [ctx.author.id, opponent_discord_id]):
            await ctx.send("❌ Confirmation timed out. Please try again.")
            return

        # Update ELOs and record game
        invoker_stats = fetch_query(
            "SELECT elo FROM players WHERE player_id = %s",
            (invoker_id,)
        )[0]
        opponent_stats = fetch_query(
            "SELECT elo FROM players WHERE player_id = %s",
            (opponent_id,)
        )[0]

        new_invoker_elo, new_opponent_elo = calculate_new_ratings(
            invoker_stats['elo'], opponent_stats['elo'],
            1 if result == '1-0' else 0.5 if result == '0.5-0.5' else 0,
            0 if result == '1-0' else 0.5 if result == '0.5-0.5' else 1
        )

        execute_query(
            "UPDATE players SET elo = %s, last_updated = NOW() WHERE player_id = %s",
            (new_invoker_elo, invoker_id)
        )
        execute_query(
            "UPDATE players SET elo = %s, last_updated = NOW() WHERE player_id = %s",
            (new_opponent_elo, opponent_id)
        )

        # Update win/loss/draw statistics and increment games played
        if result == '1-0':  # Sente won
            execute_query(
                "UPDATE players SET wins = wins + 1, games_played = games_played + 1 WHERE player_id = %s",
                (invoker_id if player_color == 'sente' else opponent_id,)
            )
            execute_query(
                "UPDATE players SET losses = losses + 1, games_played = games_played + 1 WHERE player_id = %s",
                (opponent_id if player_color == 'sente' else invoker_id,)
            )
        elif result == '0-1':  # Gote won
            execute_query(
                "UPDATE players SET wins = wins + 1, games_played = games_played + 1 WHERE player_id = %s",
                (opponent_id if player_color == 'sente' else invoker_id,)
            )
            execute_query(
                "UPDATE players SET losses = losses + 1, games_played = games_played + 1 WHERE player_id = %s",
                (invoker_id if player_color == 'sente' else opponent_id,)
            )
        elif result == '0.5-0.5':  # Draw
            execute_query(
                "UPDATE players SET draws = draws + 1, games_played = games_played + 1 WHERE player_id = %s",
                (invoker_id,)
            )
            execute_query(
                "UPDATE players SET draws = draws + 1, games_played = games_played + 1 WHERE player_id = %s",
                (opponent_id,)
            )

        # Fetch all players in the guild sorted by ELO
        players = fetch_query(
            "SELECT player_id FROM players WHERE guild_id = %s ORDER BY elo DESC",
            (guild_id,)
        )

        # Compute ranks
        rankings = {player['player_id']: rank + 1 for rank, player in enumerate(players)}

        # Update roles for both players
        if invoker_id in rankings:
            await update_player_roles(ctx.author, new_invoker_elo, rankings[invoker_id])

        if opponent_id in rankings:
            opponent_member = ctx.guild.get_member(opponent_discord_id)
            if opponent_member:
                await update_player_roles(opponent_member, new_opponent_elo, rankings[opponent_id])

        # Step 3: Add Notes (Optional)
        notes_embed = discord.Embed(
            title="📝 Add Notes (0-60)",
            description="Enter any notes for the game (max 60 characters). For example, the name of the openings used.\n\nReact with ❌ to skip.",
            color=discord.Color.purple()
        )
        notes_message = await ctx.send(embed=notes_embed)
        await notes_message.add_reaction('❌')

        def notes_check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        def reaction_check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '❌' and reaction.message.id == notes_message.id

        notes = None  # Default value

        while True:
            try:
                done, pending = await asyncio.wait(
                    [
                        self.bot.wait_for('message', timeout=60, check=notes_check),
                        self.bot.wait_for('reaction_add', timeout=60, check=reaction_check)
                    ],
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()  # Cancel any pending tasks

                # Check what completed first
                if any(isinstance(task.result(), tuple) for task in done):  # Reaction was added
                    await ctx.send("❌ Notes skipped.")
                    notes = None
                    break
                else:  # User typed a message
                    message = next(task.result() for task in done if not isinstance(task.result(), tuple))
                    notes = message.content.strip()
                    if len(notes) > 60:  # Character limit
                        await ctx.send("⚠️ Notes cannot exceed 60 characters. Please try again.")
                        continue  # Loop back to prompt again
                    await ctx.send(f"📝 Notes added: {notes}")
                    break
            except asyncio.TimeoutError:
                await ctx.send("⏳ You took too long to respond. Skipping notes.")
                notes = None
                break

        # Insert game into the database with notes
        execute_query(
            "INSERT INTO games (player1_id, player2_id, player1_color, result, guild_id, note) VALUES (%s, %s, %s, %s, %s, %s)",
            (invoker_id, opponent_id, player_color, result, guild_id, notes)
        )
        await ctx.send("Game recorded, ELOs updated, and roles assigned!")

    @addgame.error
    async def addgame_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ **Error:** Missing opponent name.\n**Usage:** `!addgame <opponent_name>`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ **Error:** Invalid argument type.\n**Usage:** `!addgame <opponent_name>`")
        else:
            await ctx.send("❌ An unexpected error occurred. Please try again later.")
            raise error

async def setup(bot):
    await bot.add_cog(AddGame(bot))
