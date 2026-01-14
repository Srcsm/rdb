from redbot.core.bot import Red

from .papi import PAPI

__red_end_user_data_statement__ = (
    "This cog stores server configuration data (server name, footer icon URL, API URL, "
    "API key, and debug settings). It does not store any personal user data. "
    "The cog queries PlaceholderAPI data from a connected Minecraft server but does not "
    "persist any of this data within the cog."
)


async def setup(bot: Red) -> None:
    """Load the PAPI cog"""
    await bot.add_cog(PAPI(bot))
