import discord
from discord.ext import commands
from utils.db import execute_query, fetch_query
from config import ADMIN_ROLE_NAME
import asyncio
import re
import logging
from utils.decorators import command_in_progress, active_commands


class Signup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @command_in_progress()
    async def signup(self, ctx):
        """
        Allows a user to sign up for the bot.
        """
        guild_id = ctx.guild.id
        user_id = ctx.author.id
        guild_name = ctx.guild.name
        user_name = ctx.author.name

        logging.info(f"Signup initiated by user: {user_name} (ID: {user_id}) in guild: {guild_name} (ID: {guild_id})")

        # Check if the user is already signed up
        existing_user = fetch_query(
            "SELECT player_name FROM players WHERE discord_user_id = %s AND guild_id = %s",
            (user_id, guild_id)
        )
        if existing_user:
            logging.info(f"User {user_name} (ID: {user_id}) is already signed up with player name: {existing_user[0]['player_name']}")
            already_signed_up_embed = discord.Embed(
                title="🔒 **Already Signed Up**",
                description=(
                    f"You are already signed up as **{existing_user[0]['player_name']}**.\n\n"
                    "If you need to update your information, please contact an admin."
                ),
                color=discord.Color.orange()
            )
            await ctx.send(embed=already_signed_up_embed)
            return

        # Initialize variables
        total_timeout = 180  # Total time allowed for the signup process
        start_time = asyncio.get_event_loop().time()

        def message_check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        def calculate_time_remaining():
            return total_timeout - (asyncio.get_event_loop().time() - start_time)

        # Step 1: Ask for the player's name
        while True:
            time_remaining = calculate_time_remaining()
            if time_remaining <= 0:
                await self.send_timeout_embed(ctx)
                return

            name_embed = discord.Embed(
                title="📝 **Signup Process**",
                description=(
                    "Please input your name in the format:\n"
                    "**(FirstName)(LastInitial)**\n\n"
                    "**Examples:**\n"
                    "• DwayneJ\n"
                    "• ClarkK\n"
                    "• MarieC"
                ),
                color=discord.Color.blue()
            )
            name_embed.set_footer(text=f"You have {int(time_remaining)} seconds to reply.")
            await ctx.send(embed=name_embed)

            try:
                name_msg = await self.bot.wait_for("message", check=message_check, timeout=time_remaining)
                player_name = name_msg.content.strip()

                if not re.match(r'^[A-Z][a-z]+[A-Z]$', player_name):
                    logging.warning(f"User {user_name} (ID: {user_id}) entered an invalid name: {player_name}")
                    await ctx.send(embed=self.invalid_name_embed())
                    continue

                # Check for duplicate names
                duplicate_name = fetch_query(
                    "SELECT player_name FROM players WHERE player_name = %s AND guild_id = %s",
                    (player_name, guild_id)
                )
                if duplicate_name:
                    logging.info(f"User {user_name} (ID: {user_id}) tried to use a duplicate name: {player_name}")
                    duplicate_embed = discord.Embed(
                        title="❌ **Duplicate Name**",
                        description=(
                            f"The name **{player_name}** is already taken by another player.\n"
                            "Please choose a different name."
                        ),
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=duplicate_embed)
                    continue

                # If no issues, break the loop
                logging.info(f"User {user_name} (ID: {user_id}) selected the name: {player_name}")
                break
            except asyncio.TimeoutError:
                logging.warning(f"Signup timed out for user: {user_name} (ID: {user_id})")
                await self.send_timeout_embed(ctx)
                return

        # Step 2: Confirm the name
        confirmation_embed = discord.Embed(
            title="✅ **Confirm Your Name**",
            description=f"Do you want to sign up with **{player_name}**?",
            color=discord.Color.blue()
        )
        confirmation_embed.set_footer(text="React with ✅ to confirm or ❌ to cancel.")
        confirmation_message = await ctx.send(embed=confirmation_embed)
        await confirmation_message.add_reaction('✅')
        await confirmation_message.add_reaction('❌')

        try:
            reaction, user = await self.bot.wait_for(
                'reaction_add',
                timeout=calculate_time_remaining(),
                check=lambda r, u: u == ctx.author and r.message.id == confirmation_message.id and str(r.emoji) in ['✅', '❌']
            )

            if str(reaction.emoji) == '❌':
                logging.info(f"User {user_name} (ID: {user_id}) canceled the signup.")
                await ctx.send(embed=self.canceled_embed())
                return
        except asyncio.TimeoutError:
            logging.warning(f"Signup timed out for user: {user_name} (ID: {user_id}) during confirmation.")
            await self.send_timeout_embed(ctx)
            return

        # Step 3: Select player's level
        level_embed = discord.Embed(
            title="🎚️ **Select Your Level**",
            description=(
                "Please react with your level:\n\n"
                "1️⃣ - **Beginner**\n"
                "2️⃣ - **Intermediate**\n"
                "3️⃣ - **Advanced**"
            ),
            color=discord.Color.blue()
        )
        level_embed.set_footer(text="React with 1️⃣, 2️⃣, or 3️⃣.")
        level_message = await ctx.send(embed=level_embed)
        await level_message.add_reaction('1️⃣')
        await level_message.add_reaction('2️⃣')
        await level_message.add_reaction('3️⃣')

        try:
            reaction, user = await self.bot.wait_for(
                'reaction_add',
                timeout=calculate_time_remaining(),
                check=lambda r, u: u == ctx.author and r.message.id == level_message.id and str(r.emoji) in ['1️⃣', '2️⃣', '3️⃣']
            )

            if str(reaction.emoji) == '1️⃣':
                elo, level = 500, 'Beginner'
            elif str(reaction.emoji) == '2️⃣':
                elo, level = 1000, 'Intermediate'
            elif str(reaction.emoji) == '3️⃣':
                elo, level = 1000, 'Advanced'

            logging.info(f"User {user_name} (ID: {user_id}) selected level: {level} (ELO: {elo})")
        except asyncio.TimeoutError:
            logging.warning(f"Signup timed out for user: {user_name} (ID: {user_id}) during level selection.")
            await self.send_timeout_embed(ctx)
            return

        # Step 4: Add player to the database
        try:
            execute_query(
                "INSERT INTO players (discord_user_id, guild_id, player_name, elo) VALUES (%s, %s, %s, %s)",
                (user_id, guild_id, player_name, elo)
            )
            logging.info(f"User {user_name} (ID: {user_id}) successfully signed up with name: {player_name}, ELO: {elo}, Level: {level}")
        except Exception as e:
            logging.error(f"Failed to insert user {user_name} (ID: {user_id}) into database: {e}")
            await ctx.send("An error occurred while completing your signup. Please contact an admin.")
            return

        # Attempt to change the user's nickname
        try:
            await ctx.author.edit(nick=player_name)
            nickname_message = f"Your nickname has been changed to **{player_name}**."
        except discord.Forbidden:
            logging.warning(f"Bot lacks permission to change nickname for user {user_name} (ID: {user_id}).")
            nickname_message = "I do not have permission to change your nickname."
            await self.notify_admins_nickname(ctx, player_name)

        # Send signup success message
        success_embed = discord.Embed(
            title="🎉 **Signup Successful**",
            description=(
                f"<@{user_id}>, you have been signed up as **{player_name}** with an ELO of **{elo}**!\n\n"
                f"{nickname_message}"
            ),
            color=discord.Color.green()
        )
        await ctx.send(embed=success_embed)

        # Notify admins if "Advanced"
        if level == 'Advanced':
            await self.notify_admins(ctx, player_name)

    # Helper method to notify admins about failed nickname change
    async def notify_admins_nickname(self, ctx, player_name):
        admin_role = discord.utils.get(ctx.guild.roles, name=ADMIN_ROLE_NAME)
        if admin_role:
            for admin in admin_role.members:
                try:
                    dm_embed = discord.Embed(
                        title="🚨 **Nickname Change Required**",
                        description=(
                            f"{ctx.author.mention} ({ctx.author.name}) attempted to sign up with the name "
                            f"**{player_name}**, but I could not change their nickname due to insufficient permissions.\n\n"
                            "Please manually update their nickname to follow server guidelines."
                        ),
                        color=discord.Color.orange()
                    )
                    dm_embed.set_footer(text=f"Guild: {ctx.guild.name}")
                    await admin.send(embed=dm_embed)
                except discord.Forbidden:
                    pass  # Admin has disabled DMs from the server

    # Helper method to notify admins about advanced signup
    async def notify_admins(self, ctx, player_name):
        admin_role = discord.utils.get(ctx.guild.roles, name=ADMIN_ROLE_NAME)
        if admin_role:
            for admin in admin_role.members:
                try:
                    await admin.send(embed=self.advanced_signup_embed(ctx.author, player_name))
                except discord.Forbidden:
                    pass

    # Embed for advanced signup notifications
    def advanced_signup_embed(self, member, player_name):
        return discord.Embed(
            title="🚨 **Advanced Player Signup**",
            description=(
                f"{member.mention} ({player_name}) has signed up as **Advanced**.\n"
                "You may want to manually adjust their ELO."
            ),
            color=discord.Color.orange()
        )

    # Embed for signup cancellation
    def canceled_embed(self):
        return discord.Embed(
            title="❌ **Signup Canceled**",
            description="You have canceled the signup process.",
            color=discord.Color.red()
        )

    # Embed for signup timeout
    async def send_timeout_embed(self, ctx):
        timeout_embed = discord.Embed(
            title="⏳ **Signup Timed Out**",
            description="You took too long to respond. Please start the signup process again.",
            color=discord.Color.red()
        )
        await ctx.send(embed=timeout_embed)

    # Embed for invalid name
    def invalid_name_embed(self):
        return discord.Embed(
            title="❌ **Invalid Format**",
            description=(
                "Your name must be in the format:\n"
                "**(FirstName)(LastInitial)**\n\n"
                "Please use proper capitalization.\n\n"
                "**Examples:**\n"
                "• DwayneJ\n"
                "• ClarkK\n"
                "• MarieC"
            ),
            color=discord.Color.red()
        )

# Setup function to load the cog
async def setup(bot):
    await bot.add_cog(Signup(bot))
