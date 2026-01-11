import discord
import logging
import aiohttp
from typing import Optional
from datetime import datetime

from redbot.core import commands, Config, app_commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box

log = logging.getLogger("red.papi")


class PAPI(commands.Cog):
    """PlaceholderAPI integration for Red.
    
    Query placeholders with a Discord slash command.
    """
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        
        # Default settings
        default_global = {
            "server_name": "MC SMP",
            "footer_icon": "https://i.imgur.com/example.png",
            "debug": False,
            "api_url": "http://localhost:8080",
            "api_key": "change-me-please"
        }
        
        self.config.register_global(**default_global)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def cog_load(self):
        """Called when the cog is loaded"""
        self.session = aiohttp.ClientSession()
        settings = await self.config.all()
        if settings["debug"]:
            log.info("PAPI cog loaded with debug mode enabled")
        
        # Warn if using default API key
        if settings["api_key"] == "change-me-please":
            log.warning("="*50)
            log.warning("WARNING: You are using the default API key!")
            log.warning("Please set it with: [p]papiset apikey <your-key>")
            log.warning("="*50)
    
    async def cog_unload(self):
        """Called when the cog is unloaded"""
        if self.session:
            await self.session.close()
    
    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Show version in help"""
        return f"{super().format_help_for_context(ctx)}\n\nVersion: 1.0.1"
    
    # Config commands
    @commands.group()
    @commands.is_owner()
    async def papiset(self, ctx: commands.Context):
        """Configure PAPI integration settings"""
        pass
    
    @papiset.command(name="servername")
    async def set_server_name(self, ctx: commands.Context, *, name: str):
        """Set the server name displayed in embeds
        
        Example: `[p]papiset servername MC SMP`
        """
        await self.config.server_name.set(name)
        await ctx.send(f"✅ Server name set to: **{name}**")
        if await self.config.debug():
            log.info(f"Server name updated by {ctx.author} to: {name}")
    
    @papiset.command(name="footericon")
    async def set_footer_icon(self, ctx: commands.Context, url: str):
        """Set the footer icon URL for embeds
        
        Example: `[p]papiset footericon https://i.imgur.com/example.png`
        """
        await self.config.footer_icon.set(url)
        await ctx.send(f"✅ Footer icon URL set to: {url}")
        if await self.config.debug():
            log.info(f"Footer icon updated by {ctx.author} to: {url}")
    
    @papiset.command(name="apiurl")
    async def set_api_url(self, ctx: commands.Context, url: str):
        """Set the PAPIRRestAPI URL for your Minecraft server
        
        Example: `[p]papiset apiurl http://your-server.com:8080`
        """
        # Remove trailing slash if present
        url = url.rstrip('/')
        await self.config.api_url.set(url)
        await ctx.send(f"✅ API URL set to: {url}")
        if await self.config.debug():
            log.info(f"API URL updated by {ctx.author} to: {url}")
    
    @papiset.command(name="apikey")
    async def set_api_key(self, ctx: commands.Context, key: str):
        """Set the API key for authentication
        _Recommended to generate a key with a service_
        _such as https://uuidgenerator.com/_
        
        Example: `[p]papiset apikey your-secret-key-here`
        
        **Note:** Your message will be immediately deleted for security, regardless please use within a secure channel.
        """
        await self.config.api_key.set(key)
        await ctx.send("✅ API key has been set securely.")
        
        # Delete the command message
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            await ctx.send("⚠️ **WARNING:** _I don't have permission to delete messages._ Please delete your message manually!")
        
        if await self.config.debug():
            log.info(f"API key updated by {ctx.author}")
    
    @papiset.command(name="debug")
    async def toggle_debug(self, ctx: commands.Context):
        """Toggle debug logging"""
        current = await self.config.debug()
        await self.config.debug.set(not current)
        status = "enabled" if not current else "disabled"
        await ctx.send(f"✅ Debug mode {status}")
        log.info(f"Debug mode {status} by {ctx.author}")
    
    @papiset.command(name="test")
    async def test_connection(self, ctx: commands.Context):
        """Test the connection to PAPIRestAPI"""
        async with ctx.typing():
            settings = await self.config.all()
            api_url = settings["api_url"]
            
            try:
                async with self.session.get(
                    f"{api_url}/api/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        embed = discord.Embed(
                            title="✅ Connection Successful",
                            color=discord.Color.green(),
                            timestamp=datetime.utcnow()
                        )
                        embed.add_field(name="Status", value=data.get("status", "Unknown"), inline=True)
                        embed.add_field(name="Plugin", value=data.get("plugin", "Unknown"), inline=True)
                        embed.add_field(name="Version", value=data.get("version", "Unknown"), inline=True)
                        embed.add_field(name="Minecraft Version", value=data.get("minecraft_version", "Unknown"), inline=False)
                        embed.add_field(name="API URL", value=api_url, inline=False)
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"❌ Connection failed! Status code: {resp.status}")
            except aiohttp.ClientError as e:
                await ctx.send(f"❌ Connection failed: {str(e)}\n\nEnsure your server is running and the API URL is correct.")
            except Exception as e:
                log.error(f"Error testing connection: {e}", exc_info=True)
                await ctx.send(f"❌ Unexpected error: {str(e)}")
    
    @papiset.command(name="settings")
    async def show_settings(self, ctx: commands.Context):
        """Show current PAPI settings"""
        settings = await self.config.all()
        
        embed = discord.Embed(
            title="🔧 PAPI Settings",
            color=await ctx.embed_color(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Server Name", value=settings["server_name"], inline=False)
        embed.add_field(name="Footer Icon", value=settings["footer_icon"], inline=False)
        embed.add_field(name="API URL", value=settings["api_url"], inline=False)
        embed.add_field(name="API Key", value="✅ Set" if settings["api_key"] != "change-me-please" else "⚠️ Defaults detected! _(change this!)_", inline=False)
        embed.add_field(name="Debug Mode", value="✅ Enabled" if settings["debug"] else "❌ Disabled", inline=False)
        
        await ctx.send(embed=embed)
    
    # Slash command
    @app_commands.command(name="papi")
    @app_commands.describe(
        placeholder="The placeholder to parse (e.g., player_name, server_online)",
        player="Optional: For player-specific placeholders"
    )
    async def papi_slash(
        self, 
        interaction: discord.Interaction, 
        placeholder: str,
        player: Optional[str] = None
    ):
        """Parse a PlaceholderAPI placeholder from Minecraft"""
        debug = await self.config.debug()
        
        if debug:
            log.info(f"PAPI command received from {interaction.user} - Placeholder: {placeholder}, Player: {player}")
        
        await interaction.response.defer(ephemeral=False)
        
        try:
            settings = await self.config.all()
            
            # Check if API is configured
            if settings["api_key"] == "change-me-please":
                await interaction.followup.send(
                    "❌ **Error:** API key not configured. Please contact the bot owner.",
                    ephemeral=True
                )
                return
            
            # Parse placeholder via REST API
            result = await self._parse_placeholder_via_api(placeholder, player, settings)
            
            if result is None:
                await interaction.followup.send(
                    f"❌ **Error:** Failed to connect to PAPIRestAPI or your Minecraft server. Please try again later.",
                    ephemeral=True
                )
                return
            
            if not result.get("success"):
                error_msg = result.get("error", "Unknown error")
                await interaction.followup.send(
                    f"❌ **Error:** {error_msg}",
                    ephemeral=True
                )
                return
            
            # Create success embed
            embed = await self._create_success_embed(
                placeholder=result["placeholder"],
                value=result["value"],
                context=result["context"]
            )
            
            await interaction.followup.send(embed=embed)
            
            if debug:
                log.info(f"Successfully sent PAPI response for {placeholder}")
                
        except Exception as e:
            log.error(f"Error in PAPI command: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **Error:** An unexpected error occurred while processing the command.",
                ephemeral=True
            )
    
    async def _parse_placeholder_via_api(
        self, 
        placeholder: str, 
        player: Optional[str], 
        settings: dict
    ) -> Optional[dict]:
        """Query the REST API to parse a placeholder"""
        debug = settings["debug"]
        api_url = settings["api_url"]
        api_key = settings["api_key"]

        clean_placeholder = placeholder.strip("%")
        
        params = {"placeholder": clean_placeholder}
        if player:
            params["player"] = player
        
        headers = {"X-API-Key": api_key}
        
        if debug:
            log.info(f"Making API request to {api_url}/api/parse with params: {params}")
        
        try:
            async with self.session.get(
                f"{api_url}/api/parse",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if debug:
                    log.info(f"API response status: {resp.status}")
                
                data = await resp.json()
                
                if debug:
                    log.info(f"API response data: {data}")
                
                return data
                
        except aiohttp.ClientError as e:
            log.error(f"API request failed: {e}")
            return None
        except Exception as e:
            log.error(f"Unexpected error in API request: {e}", exc_info=True)
            return None
    
    async def _create_success_embed(
        self, 
        placeholder: str, 
        value: str, 
        context: str
    ) -> discord.Embed:
        """Create a success embed for PAPI results"""
        settings = await self.config.all()
        
        embed = discord.Embed(
            title="PlaceholderAPI Result",
            color=discord.Colour.green(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="🏷️ **Placeholder**", value=f"`{placeholder}`", inline=True)
        embed.add_field(name="👤 **Context**", value=context, inline=True)
        embed.add_field(name="#️⃣ **Value**", value=value, inline=False)
        
        # Add player thumbnail if it's a player-specific query
        if context != "Server":
            thumbnail_url = f"https://vzge.me/bust/128/{context}"
            embed.set_thumbnail(url=thumbnail_url)
        
        # timestamp_str = datetime.now().strftime("%d/%m/%Y %I:%M%p")
        embed.set_footer(text=settings["server_name"], icon_url=settings["footer_icon"])
        
        return embed


async def setup(bot: Red) -> None:
    """Load the PAPI cog"""
    cog = PAPI(bot)
    await bot.add_cog(cog)



