# utils/role_update.py

import discord
import re

# Define ranking roles with their colors
RANKING_ROLES = {
    1: {'role_name': 'Rank 1', 'color': discord.Color.gold()},
    2: {'role_name': 'Rank 2', 'color': discord.Color.from_rgb(192, 192, 192)},  # Silver color
    3: {'role_name': 'Rank 3', 'color': discord.Color.from_rgb(205, 127, 50)},   # Bronze color
    'top_10': {'role_name': 'Top 10', 'color': discord.Color.blue()}             # Light blue color
}

async def update_player_roles(member: discord.Member, elo: int, rank: int):
    """
    Update the player's roles based on their ELO rating and rank.

    Parameters:
    - member: The Discord member whose roles need to be updated.
    - elo: The player's current ELO rating.
    - rank: The player's current rank (1-based).
    """
    guild = member.guild

    # Remove existing ranking roles from the member
    ranking_role_names = [role_info['role_name'] for role_info in RANKING_ROLES.values()]
    roles_to_remove = [discord.utils.get(guild.roles, name=role_name) for role_name in ranking_role_names]
    roles_to_remove = [role for role in roles_to_remove if role and role in member.roles]

    if roles_to_remove:
        try:
            await member.remove_roles(*roles_to_remove)
        except discord.Forbidden:
            print(f"⚠️ Failed to remove ranking roles from {member.display_name}. Insufficient permissions.")
        except Exception as e:
            print(f"⚠️ Error removing ranking roles from {member.display_name}: {e}")

    # Assign new ranking role if applicable
    role_info = None
    if rank == 1:
        role_info = RANKING_ROLES[1]
    elif rank == 2:
        role_info = RANKING_ROLES[2]
    elif rank == 3:
        role_info = RANKING_ROLES[3]
    elif 4 <= rank <= 10:
        role_info = RANKING_ROLES['top_10']

    if role_info:
        new_ranking_role = discord.utils.get(guild.roles, name=role_info['role_name'])
        if not new_ranking_role:
            # Create the role if it doesn't exist
            try:
                new_ranking_role = await guild.create_role(name=role_info['role_name'], color=role_info['color'])
            except discord.Forbidden:
                print(f"⚠️ Failed to create ranking role {role_info['role_name']}. Insufficient permissions.")
                new_ranking_role = None
            except Exception as e:
                print(f"⚠️ Error creating ranking role {role_info['role_name']}: {e}")
                new_ranking_role = None

        if new_ranking_role:
            try:
                await member.add_roles(new_ranking_role)
            except discord.Forbidden:
                print(f"⚠️ Failed to add ranking role {new_ranking_role.name} to {member.display_name}. Insufficient permissions.")
            except Exception as e:
                print(f"⚠️ Error adding ranking role {new_ranking_role.name} to {member.display_name}: {e}")

    # Remove existing ELO roles
    elo_role_pattern = re.compile(r'^\d{3,4}$')
    existing_elo_roles = [role for role in member.roles if elo_role_pattern.match(role.name)]
    if existing_elo_roles:
        try:
            await member.remove_roles(*existing_elo_roles)
        except discord.Forbidden:
            print(f"⚠️ Failed to remove ELO roles from {member.display_name}. Insufficient permissions.")
        except Exception as e:
            print(f"⚠️ Error removing ELO roles from {member.display_name}: {e}")

    # Assign new ELO role
    elo_role_name = f"{(elo // 100) * 100}"
    new_elo_role = discord.utils.get(guild.roles, name=elo_role_name)
    if not new_elo_role:
        # Create the ELO role if it doesn't exist
        try:
            new_elo_role = await guild.create_role(name=elo_role_name)
        except discord.Forbidden:
            print(f"⚠️ Failed to create ELO role {elo_role_name}. Insufficient permissions.")
            new_elo_role = None
        except Exception as e:
            print(f"⚠️ Error creating ELO role {elo_role_name}: {e}")
            new_elo_role = None

    if new_elo_role:
        try:
            await member.add_roles(new_elo_role)
        except discord.Forbidden:
            print(f"⚠️ Failed to add ELO role {new_elo_role.name} to {member.display_name}. Insufficient permissions.")
        except Exception as e:
            print(f"⚠️ Error adding ELO role {new_elo_role.name} to {member.display_name}: {e}")
