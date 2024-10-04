import discord
from discord.ext import commands
from utils.db import execute_query, fetch_query
from config import ADMIN_ROLE_NAME
import asyncio
import re

class Signup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def signup(self, ctx):

        user_id = ctx.author.id
        existing_user = fetch_query(
            "SELECT player_name FROM players WHERE discord_user_id = %s",
            (user_id,)
        )

        if existing_user:
            # User is already signed up
            already_signed_up_embed = discord.Embed(
                title="🔒 **Already Signed Up**",
                description=(
                    f"You are already signed up as **{existing_user[0][0]}**.\n\n"
                    "If you need to update your information, please contact an admin."
                ),
                color=discord.Color.orange()
            )
            await ctx.send(embed=already_signed_up_embed)
            return  # Prevent further execution

        # Step 1: Initialize variables
        total_timeout = 180  # Total time allowed for the signup process
        start_time = asyncio.get_event_loop().time()

        def message_check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        # Step 2: Ask for the player's name
        while True:
            time_elapsed = asyncio.get_event_loop().time() - start_time
            time_remaining = total_timeout - time_elapsed

            if time_remaining <= 0:
                timeout_embed = discord.Embed(
                    title="⏳ **Signup Timed Out**",
                    description="You took too long to respond. Please start the signup process again.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=timeout_embed)
                return

            name_embed = discord.Embed(
                title="📝 **Signup Process**",
                description=(
                    "Please input your name in the format:\n"
                    "**(FirstName)(LastInitial)**\n\n"
                    "**Examples:**\n"
                    "• `DwayneJ`\n"
                    "• `ClarkK`\n"
                    "• `MarieC`"
                ),
                color=discord.Color.blue()
            )
            name_embed.set_footer(text=f"You have {int(time_remaining)} seconds to reply.")
            await ctx.send(embed=name_embed)

            try:
                name_msg = await self.bot.wait_for("message", check=message_check, timeout=time_remaining)
                player_name = name_msg.content.strip()

                # Validate the name format
                if re.match(r'^[A-Z][a-z]+[A-Z]$', player_name):
                    break  # Valid name provided
                else:
                    error_embed = discord.Embed(
                        title="❌ **Invalid Format**",
                        description=(
                            "Your name must be in the format:\n"
                            "**(FirstName)(LastInitial)**\n\n"
                            "Please use proper capitalization.\n\n"
                            "**Examples:**\n"
                            "• `DwayneJ`\n"
                            "• `ClarkK`\n"
                            "• `MarieC`"
                        ),
                        color=discord.Color.red()
                    )
                    error_embed.set_footer(text="Please try again.")
                    await ctx.send(embed=error_embed)
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title="⏳ **Signup Timed Out**",
                    description="You took too long to respond. Please start the signup process again.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=timeout_embed)
                return

        # Step 3: Confirmation of the name
        confirmation_embed = discord.Embed(
            title="✅ **Confirm Your Name**",
            description=f"Do you want to sign up with **{player_name}**?",
            color=discord.Color.blue()
        )
        confirmation_embed.set_footer(text="React with ✅ to confirm or ❌ to cancel.")
        confirmation_message = await ctx.send(embed=confirmation_embed)
        await confirmation_message.add_reaction('✅')
        await confirmation_message.add_reaction('❌')

        def reaction_check(reaction, user):
            return (
                user == ctx.author and
                str(reaction.emoji) in ['✅', '❌'] and
                reaction.message.id == confirmation_message.id
            )

        # Adjust time remaining for the next step
        time_elapsed = asyncio.get_event_loop().time() - start_time
        time_remaining = total_timeout - time_elapsed

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=time_remaining, check=reaction_check)

            if str(reaction.emoji) == '✅':
                # Step 4: Ask for the player's level
                level_embed = discord.Embed(
                    title="🎚️ **Select Your Level**",
                    description=(
                        "Please react with your level:\n\n"
                        "1️⃣ - **Beginner**\n"
                        "2️⃣ - **Intermediate**\n"
                        "3️⃣ - **Advanced (or returning player, I'll manually set it to your old ELO)**"
                    ),
                    color=discord.Color.blue()
                )
                level_embed.set_footer(text="React with 1️⃣, 2️⃣, or 3️⃣.")
                level_message = await ctx.send(embed=level_embed)
                await level_message.add_reaction('1️⃣')
                await level_message.add_reaction('2️⃣')
                await level_message.add_reaction('3️⃣')

                def level_reaction_check(reaction, user):
                    return (
                        user == ctx.author and
                        str(reaction.emoji) in ['1️⃣', '2️⃣', '3️⃣'] and
                        reaction.message.id == level_message.id
                    )

                # Adjust time remaining for the next step
                time_elapsed = asyncio.get_event_loop().time() - start_time
                time_remaining = total_timeout - time_elapsed

                reaction, user = await self.bot.wait_for('reaction_add', timeout=time_remaining, check=level_reaction_check)

                # Set ELO based on the selected level
                if str(reaction.emoji) == '1️⃣':
                    elo = 500
                    level = 'Beginner'
                elif str(reaction.emoji) == '2️⃣':
                    elo = 1000
                    level = 'Intermediate'
                elif str(reaction.emoji) == '3️⃣':
                    elo = 1000
                    level = 'Advanced'
                else:
                    elo = 1000
                    level = 'Intermediate'

                # Insert the player into the database
                query = """
                INSERT INTO players (discord_user_id, player_name, elo)
                VALUES (%s, %s, %s)
                """
                execute_query(query, (ctx.author.id, player_name, elo))

                # Attempt to change the user's nickname
                try:
                    await ctx.author.edit(nick=player_name)
                    nickname_message = f"Your nickname has been changed to **{player_name}**."
                except discord.Forbidden:
                    nickname_message = "I do not have permission to change your nickname."
                except Exception as e:
                    nickname_message = f"An error occurred while changing your nickname: {e}"

                # Send success message
                success_embed = discord.Embed(
                    title="🎉 **Signup Successful**",
                    description=(
                        f"You have been signed up as **{player_name}** with an ELO of **{elo}**!\n\n"
                        f"{nickname_message}"
                        f"Try `!manual` to get started!"
                    ),
                    color=discord.Color.green()
                )
                await ctx.send(embed=success_embed)

                # If advanced, send DM to admins
                if level == 'Advanced':
                    # Fetch users with the admin role
                    admin_role = discord.utils.get(ctx.guild.roles, name=ADMIN_ROLE_NAME)
                    if admin_role:
                        admins = admin_role.members
                        for admin in admins:
                            try:
                                dm_embed = discord.Embed(
                                    title="🚨 **Advanced Player Signup**",
                                    description=(
                                        f"{ctx.author.mention} ({player_name}) has signed up as **Advanced**.\n"
                                        "You may want to manually adjust their ELO."
                                    ),
                                    color=discord.Color.orange()
                                )
                                dm_embed.add_field(
                                    name="Message Link",
                                    value=f"[Jump to Message]({level_message.jump_url})"
                                )
                                await admin.send(embed=dm_embed)
                            except discord.Forbidden:
                                pass
                    else:
                        error_embed = discord.Embed(
                            title="⚠️ **Error**",
                            description=f"Admin role `{ADMIN_ROLE_NAME}` not found.",
                            color=discord.Color.red()
                        )
                        await ctx.send(embed=error_embed)
            else:
                cancel_embed = discord.Embed(
                    title="❌ **Signup Canceled**",
                    description="You have canceled the signup process.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=cancel_embed)
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏳ **Signup Timed Out**",
                description="You took too long to respond. Please start the signup process again.",
                color=discord.Color.red()
            )
            await ctx.send(embed=timeout_embed)

# Setup function to load the cog
async def setup(bot):
    await bot.add_cog(Signup(bot))
