# commands/manual.py

import discord
from discord.ext import commands
import asyncio

class Manual(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def manual(self, ctx):
        """Displays the manual with all available commands."""
        # List of commands with descriptions, parameters, and examples
        commands_info = [
            {
                "command": "!signup",
                "description": "Register yourself in the bot system.",
                "parameters": "None",
                "example": "!signup"
            },
            {
                "command": "!profile [player_name]",
                "description": "View your profile or another player's profile.",
                "parameters": "`[player_name]` (optional) - The name of the player whose profile you want to view.",
                "example": "!profile AliceC"
            },
            {
                "command": "!addgame <opponent_name>",
                "description": "Record a new game against an opponent.",
                "parameters": "`<opponent_name>` - The name of your opponent.",
                "example": "!addgame BobT"
            },
            {
                "command": "!history",
                "description": "View game history for all players or a specific player.",
                "parameters": "None",
                "example": "!history"
            },
            {
                "command": "!leaderboard",
                "description": "Display the current leaderboard.",
                "parameters": "None",
                "example": "!leaderboard or !lb"
            },
            {
                "command": "!manual",
                "description": "Display this manual.",
                "parameters": "None",
                "example": "!manual"
            },
            {
                "command": "!elowand <player_name> <new_elo>",
                "description": "Set a player's ELO rating (Admin only).",
                "parameters": "`<player_name>` - The name of the player.\n`<new_elo>` - The new ELO rating.",
                "example": "!elowand AliceC 1500"
            },
            {
                "command": "!removegame <gameID>",
                "description": "Remove a game by its ID (Admin only).",
                "parameters": "`<gameID>` - The ID of the game to remove.",
                "example": "!removegame 42"
            },
            # Add more commands as needed
        ]

        # Paginate the commands
        pages = []
        commands_per_page = 4  # Adjust the number of commands per page if needed
        for i in range(0, len(commands_info), commands_per_page):
            chunk = commands_info[i:i+commands_per_page]
            embed = discord.Embed(title="📖 Bot Manual", description="List of available commands.", color=discord.Color.green())
            for cmd_info in chunk:
                command = cmd_info["command"]
                description = cmd_info["description"]
                parameters = cmd_info.get("parameters", "None")
                example = cmd_info.get("example", "None")
                embed.add_field(
                    name=f"{command}",
                    value=(
                        f"**Description:** {description}\n"
                        f"**Parameters:** {parameters}\n"
                        f"**Example:** `{example}`"
                    ),
                    inline=False
                )
            page_number = (i // commands_per_page) + 1
            total_pages = ((len(commands_info) - 1) // commands_per_page) + 1
            embed.set_footer(text=f"Page {page_number}/{total_pages}")
            pages.append(embed)

        # Send the first page
        current_page = 0
        message = await ctx.send(embed=pages[current_page])

        # Add reactions for pagination if there's more than one page
        if len(pages) > 1:
            await message.add_reaction('⬅️')
            await message.add_reaction('➡️')

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ['⬅️', '➡️'] and reaction.message.id == message.id

            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=120, check=check)
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
                    try:
                        await message.clear_reactions()
                    except:
                        pass
                    break

    # The required setup function
async def setup(bot):
    await bot.add_cog(Manual(bot))
