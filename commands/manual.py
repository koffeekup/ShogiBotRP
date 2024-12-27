import discord
from discord.ext import commands
import asyncio
from utils.db import fetch_query, execute_query
from utils.decorators import command_in_progress, active_commands


class Manual(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def manual(self, ctx):
        """Displays the manual with all available commands."""
        commands_info = [
            {
                "command": "!signup",
                "description": "Register yourself in the bot system.",
                "parameters": "None",
                "example": "!signup",
                "roles": ["Everyone"]
            },
            {
                "command": "!profile [player_name]",
                "description": "View your profile or another player's profile.",
                "parameters": "`[player_name]` (optional) - The name of the player whose profile you want to view.",
                "example": "!profile AliceC",
                "roles": ["Everyone"]
            },
            {
                "command": "!addgame <opponent_name>",
                "description": "Record a new game against an opponent.",
                "parameters": "`<opponent_name>` - The name of your opponent.",
                "example": "!addgame BobT",
                "roles": ["Everyone"]
            },
            {
                "command": "!history",
                "description": "View game history for all players or a specific player.",
                "parameters": "None",
                "example": "!history",
                "roles": ["Everyone"]
            },
            {
                "command": "!leaderboard",
                "description": "Display the current leaderboard.",
                "parameters": "None",
                "example": "!leaderboard or !lb",
                "roles": ["Everyone"]
            },
            {
                "command": "!manual",
                "description": "Display this manual.",
                "parameters": "None",
                "example": "!manual",
                "roles": ["Everyone"]
            },
            {
                "command": "!elowand <player_name> <new_elo>",
                "description": "Set a player's ELO rating (Admin only).",
                "parameters": "`<player_name>` - The name of the player.\n`<new_elo>` - The new ELO rating.",
                "example": "!elowand AliceC 1500",
                "roles": ["Shogibot Admin"]
            },
            {
                "command": "!removegame <gameID>",
                "description": "Remove a game by its ID (Admin only).",
                "parameters": "`<gameID>` - The ID of the game to remove.",
                "example": "!removegame 42",
                "roles": ["Shogibot Admin"]
            },
            {
                "command": "!clear <number>",
                "description": "Clear the specified number of messages from the channel (Admin only).",
                "parameters": "`<number>` - The number of messages to delete.",
                "example": "!clear 1000",
                "roles": ["Shogibot Admin"]
            },
            {
                "command": "!removemember <player_name>",
                "description": "Remove a player from the database (Admin only).",
                "parameters": "`<player_name>` - The name of the player to remove.",
                "example": "!removemember JohnC",
                "roles": ["Shogibot Admin"]
            },
        ]

        user_roles = [role.name for role in ctx.author.roles]
        accessible_commands = [
            cmd for cmd in commands_info
            if "Everyone" in cmd["roles"] or any(role in user_roles for role in cmd["roles"])
        ]

        pages = []
        commands_per_page = 4
        for i in range(0, len(accessible_commands), commands_per_page):
            chunk = accessible_commands[i:i+commands_per_page]
            embed = discord.Embed(title="📖 Bot Manual", description="List of available commands.", color=discord.Color.green())
            for cmd_info in chunk:
                embed.add_field(
                    name=f"{cmd_info['command']}",
                    value=(
                        f"**Description:** {cmd_info['description']}\n"
                        f"**Parameters:** {cmd_info.get('parameters', 'None')}\n"
                        f"**Example:** `{cmd_info.get('example', 'None')}`"
                    ),
                    inline=False
                )
            page_number = (i // commands_per_page) + 1
            total_pages = ((len(accessible_commands) - 1) // commands_per_page) + 1
            embed.set_footer(text=f"Page {page_number}/{total_pages}")
            pages.append(embed)

        current_page = 0
        message = await ctx.send(embed=pages[current_page])

        if len(pages) > 1:
            await message.add_reaction('⬅️')
            await message.add_reaction('➡️')

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ['⬅️', '➡️'] and reaction.message.id == message.id

            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=120, check=check)
                    if str(reaction.emoji) == '➡️' and current_page < len(pages) - 1:
                        current_page += 1
                        await message.edit(embed=pages[current_page])
                    elif str(reaction.emoji) == '⬅️' and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=pages[current_page])
                    await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    await message.clear_reactions()
                    break

    @commands.command()
    @commands.has_role("Shogibot Admin")
    async def elowand(self, ctx, player_name: str, new_elo: int):
        """Set a player's ELO rating."""
        player_data = fetch_query(
            "SELECT player_id FROM players WHERE player_name = %s AND guild_id = %s",
            (player_name, ctx.guild.id)
        )
        if not player_data:
            await ctx.send(f"❌ Player `{player_name}` not found in the database.")
            return

        execute_query(
            "UPDATE players SET elo = %s WHERE player_id = %s",
            (new_elo, player_data[0]['player_id'])
        )
        await ctx.send(f"✅ Updated `{player_name}`'s ELO to {new_elo}.")

    @commands.command()
    @commands.has_role("Shogibot Admin")
    async def removegame(self, ctx, game_id: int):
        """Remove a game from the database by its ID."""
        game_data = fetch_query("SELECT * FROM games WHERE game_id = %s", (game_id,))
        if not game_data:
            await ctx.send(f"❌ No game found with ID `{game_id}`.")
            return

        execute_query("DELETE FROM games WHERE game_id = %s", (game_id,))
        await ctx.send(f"✅ Removed game with ID `{game_id}` from the database.")

    @commands.command()
    @commands.has_role("Shogibot Admin")
    async def clear(self, ctx, number: int):
        """Clear the specified number of messages from the channel."""
        if number <= 0:
            await ctx.send("⚠️ Please specify a number greater than 0.")
            return
        deleted = await ctx.channel.purge(limit=number)
        await ctx.send(f"🧹 Cleared {len(deleted)} messages.", delete_after=5)

    @commands.command()
    @commands.has_role("Shogibot Admin")
    async def removemember(self, ctx, player_name: str):
        """Remove a player from the database."""
        player_data = fetch_query(
            "SELECT player_id FROM players WHERE player_name = %s AND guild_id = %s",
            (player_name, ctx.guild.id)
        )
        if not player_data:
            await ctx.send(f"❌ Player `{player_name}` not found in the database.")
            return

        execute_query("DELETE FROM players WHERE player_id = %s", (player_data[0]['player_id'],))
        await ctx.send(f"✅ Player `{player_name}` has been removed from the database.")

    # The required setup function
async def setup(bot):
    await bot.add_cog(Manual(bot))
