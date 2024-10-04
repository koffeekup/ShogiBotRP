# utils/embed.py

import discord

def create_embed(
    title=None,
    description=None,
    color=discord.Color.default(),
    fields=None,
    footer_text=None,
    thumbnail_url=None,
    author_name=None,
    author_icon_url=None,
    image_url=None,
    timestamp=None
):
    """
    Creates a standardized Discord Embed object.

    Parameters:
    - title (str): The title of the embed.
    - description (str): The main content of the embed.
    - color (discord.Color): The color strip of the embed.
    - fields (list of dict): A list of fields to add to the embed. Each field should be a dict with 'name', 'value', and 'inline' keys.
    - footer_text (str): Text to display in the footer of the embed.
    - thumbnail_url (str): URL of the image to display as a thumbnail.
    - author_name (str): Name to display as the author.
    - author_icon_url (str): URL of the image to display as the author's icon.
    - image_url (str): URL of the image to display in the embed.
    - timestamp (datetime): A datetime object for the timestamp.

    Returns:
    - embed (discord.Embed): The Discord Embed object.
    """
    embed = discord.Embed(title=title, description=description, color=color)

    if author_name:
        embed.set_author(name=author_name, icon_url=author_icon_url)

    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    if image_url:
        embed.set_image(url=image_url)

    if fields:
        for field in fields:
            embed.add_field(
                name=field.get('name', '\u200b'),  # Use zero-width space if no name
                value=field.get('value', '\u200b'),
                inline=field.get('inline', False)
            )

    if footer_text:
        embed.set_footer(text=footer_text)

    if timestamp:
        embed.timestamp = timestamp

    return embed
