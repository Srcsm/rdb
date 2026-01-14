import discord
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api import APIHelper

class EmbedHelper:
    def __init__(self, api_helper: "APIHelper"):
        self.api = api_helper
    
    async def create_success_embed(self, placeholder: str, value: str, context: str, user: discord.Member, settings: dict) -> discord.Embed:
        """Create a success embed for PAPI results"""

        thumbnail_url = self.api.vzge_url(
            subject=context,
            render="bust",
            size=128,
            format="png",
            y=20
        )

        
        embed = discord.Embed(
            title=f"PAPI Results for {user.display_name}",
            color=discord.Colour.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Result", value=f"""```ansi\n\u001b[0;32m{value}\u001b[0;30m\n```""", inline=True)
        embed.add_field(name="Context", value=f"""```ansi\n\u001b[0;34m{context}\u001b[0;30m\n```""", inline=True)
        embed.add_field(name="Placeholder", value=f"""```ansi\n\u001b[0;30m{placeholder}\u001b[0;30m\n```""", inline=False)
        
        if context != "Server":
            embed.set_thumbnail(url=thumbnail_url)
        
        embed.set_footer(text=settings["footer_name"], icon_url=settings["footer_icon"])
        
        return embed