import discord
import logging
import aiohttp
import asyncio
from typing import Optional
from datetime import datetime

from redbot.core import commands, Config, app_commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box

ver = 1.0.5
log = logging.getLogger("red.papi")


class PAPI(commands.Cog):
    """PlaceholderAPI integration for Red.
    
    Query placeholders with a Discord slash command.
    """
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=8008132, force_registration=True)
        
        # Default settings
        default_global = {
            "footer_name": "MC SMP",
            "footer_icon": "https://i.imgur.com/example.png",
            "debug": False,
            "api_url": "http://localhost:8080",
            "api_key": "change-me-please",
            "embed_value_title": "Value",
            "embed_context_title": "Context",
            "embed_placeholder_title": "Placeholder",
            "allowed_roles": ""
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
        return f"{super().format_help_for_context(ctx)}\n\nVersion: {ver}"
    
    # Config commands
    @commands.group()
    @commands.is_owner()
    async def papiset(self, ctx: commands.Context):
        """Configure PAPI integration settings"""
        pass

    @papiset.command(name="valuetitle", aliases=["vt"])
    async def set_value_title(self, ctx: commands.Context, *, name: str):
        """Set the title for the value field in embeds
        
        Example: `[p]papiset valuetitle Result`
        """
        await self.config.embed_value_title.set(name)
        await self.temp_message(
            ctx,
            f"✅ Value title set to: **{name}**",
            delete_after=3,
            delete_command_delay=3
        )
        if await self.config.debug():
            log.info(f"Value title updated by {ctx.author} to: {name}")

    @papiset.command(name="contexttitle", aliases=["ct"])
    async def set_context_title(self, ctx: commands.Context, *, name: str):
        """Set the title for the context field in embeds
        
        Example: `[p]papiset contexttitle Context`
        """
        await self.config.embed_context_title.set(name)
        await self.temp_message(
            ctx,
            f"✅ Context title set to: **{name}**",
            delete_after=3,
            delete_command_delay=3
        )
        if await self.config.debug():
            log.info(f"Context title updated by {ctx.author} to: {name}")

    @papiset.command(name="placeholdertitle", aliases=["pt"])
    async def set_value_title(self, ctx: commands.Context, *, name: str):
        """Set the title for the placeholder field in embeds
        
        Example: `[p]papiset placeholdertitle Placeholder`
        """
        await self.config.embed_value_title.set(name)
        await self.temp_message(
            ctx,
            f"✅ Placeholder title set to: **{name}**",
            delete_after=3,
            delete_command_delay=3
        )
        if await self.config.debug():
            log.info(f"Placeholder title updated by {ctx.author} to: {name}")
            
    @papiset.command(name="footername", aliases=["fn"])
    async def set_footer_name(self, ctx: commands.Context, *, name: str):
        """Set the footer name displayed in embeds
        
        Example: `[p]papiset footername MC SMP`
        """
        await self.config.footer_name.set(name)
        await self.temp_message(
            ctx,
            f"✅ Footer name set to: **{name}**",
            delete_after=3,
            delete_command_delay=3
        )
        if await self.config.debug():
            log.info(f"Footer name updated by {ctx.author} to: {name}")
    
    @papiset.command(name="footericon", aliases=["fi"])
    async def set_footer_icon(self, ctx: commands.Context, url: str):
        """Set the footer icon URL for embeds
        
        Example: `[p]papiset footericon https://i.imgur.com/example.png`
        """
        await self.config.footer_icon.set(url)
        await self.temp_message(
            ctx,
            f"✅ Footer icon URL set to: {url}",
            delete_after=3,
            delete_command_delay=3
        )
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
        await self.temp_message(
            ctx,
            f"✅ API URL set to: {url}"
        )
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
        try:
            await ctx.message.delete()
            await self.temp_message(
                ctx,
                "✅ API key has been set securely.",
                delete_after=3,
                delete_command=False
            )
        except discord.errors.Forbidden:
            await self.temp_message(
                ctx,
                "⚠️ **WARNING:** _I don't have permission to delete messages._ Please delete your message manually!",
                delete_command=False
            )
        
        if await self.config.debug():
            log.info(f"API key updated by {ctx.author}")

    @papiset.command(name="allowedroles", aliases=["ar"])
    async def set_allowed_roles(self, ctx: commands.Context, *, roles: str = ""):
        """Set the allowed role(s) to use the [p]papi command

        Examples: [p]papiset allowedroles Admin
                  [p]papiset ar Admin, Owner, 8096845738
        To reset or allow all users, use without any roles listed
                  [p]papiset allowedroles
        """
        await self.config.allowed_roles.set(roles)
        if roles:
            message = f"✅ Allowed roles set to: **{roles}**"
        else:
            message = "✅ Role restrictions cleared - everyone can use /papi"
        await self.temp_message(
            ctx,
            message,
            delete_command_delay=3,
            keep_message=True
        )
        
        if await self.config.debug():
            log.info(f"Allowed roles updated by {ctx.author} to: {roles}")
    
    @papiset.command(name="debug")
    async def toggle_debug(self, ctx: commands.Context):
        """Toggle debug logging"""
        current = await self.config.debug()
        await self.config.debug.set(not current)
        status = "enabled" if not current else "disabled"
        await self.temp_message(
            ctx,
            f"✅ Debug mode {status}",
            delete_after=3
        )
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
                        await self.temp_message(
                            ctx,
                            embed=embed,
                            delete_after=10,
                            delete_command=True,
                            keep_message=True
                        )
                    else:
                        await self.temp_message(
                            ctx,
                            f"❌ Connection failed! Status code: {resp.status}",
                            delete_after=3
                        )
            except aiohttp.ClientError as e:
                await self.temp_message(
                    ctx,
                    f"❌ Connection failed: {str(e)}\n\nEnsure your server is running and the API URL is correct.",
                    delete_after=3
                )
            except Exception as e:
                log.error(f"Error testing connection: {e}", exc_info=True)
                await self.temp_message(
                    ctx,
                    f"❌ Unexpected error: {str(e)}",
                    delete_after=8,
                    delete_command=True
                )
    
    @papiset.command(name="settings", aliases=["info"])
    async def show_settings(self, ctx: commands.Context):
        """Show current PAPI settings"""
        settings = await self.config.all()
        
        embed = discord.Embed(
            title="🔧 PAPI Settings",
            color=await ctx.embed_color(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Footer Name", value=settings["footer_name"], inline=False)
        embed.add_field(name="Footer Icon", value=settings["footer_icon"], inline=False)
        embed.add_field(name="API URL", value=settings["api_url"], inline=False)
        embed.add_field(name="API Key", value="✅ Set" if settings["api_key"] != "change-me-please" else "⚠️ Defaults detected! _(change this!)_", inline=False)
        embed.add_field(name="Debug Mode", value="✅ Enabled" if settings["debug"] else "❌ Disabled", inline=False)
        
        await self.temp_message(
            ctx,
            embed=embed,
            delete_after=8,
            keep_message=True
        )
    
    # Slash command
    @app_commands.command(name="papi")
    @app_commands.describe(
        placeholder="The placeholder to parse (e.g., server_online)",
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
            
            # Check if API key is configured
            if settings["api_key"] == "change-me-please":
                await interaction.followup.send(
                    "❌ **Error:** API key not configured. Please contact the bot owner.",
                    ephemeral=True
                )
                return
            
            # Parse placeholder via PAPIRestAPI
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
                log.info(f"Successfully sent PAPI response for {placeholder}:{value}")
                
        except Exception as e:
            log.error(f"Error in PAPI command: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **Error:** An unexpected error occurred while processing the command.",
                ephemeral=True
            )

    async def temp_message(
        self,
        ctx: commands.Context,
        content: str = None,
        embed: discord.Embed = None,
        delete_after: float = 5.0,
        delete_command: bool = True,
        delete_command_delay: float = 0,
        keep_message: bool = False
    ) -> discord.Message:
        """
        Send a message that will be deleted after a delay
        
        Args:
            ctx: Command context
            content: Message content (optional with embeds)
            embed: Embed to send (optional)
            delete_after: Delay before deleting bot message (default: 5)
            delete_command: True/False to delete the user's command message (default: True)
            delete_command_delay: Delay before deleting command message (default: 0)
            keep_message: Adds a 📌 reaction to prevent message deletion (default: False)
        
        Returns:
            The message object that was sent
        """
        # Send the response message
        msg = await ctx.send(
            content=content,
            embed=embed,
            delete_after=delete_after if delete_after > 0 and not keep_message else None)
        
        if delete_command:
            asyncio.create_task(self._delete_command_message(ctx, delete_command_delay))

        if keep_message and delete_after > 0:
            asyncio.create_task(self._handle_keep_reaction(ctx, msg, delete_after))
        
        return msg

    async def _handle_keep_reaction(
        self, 
        ctx: commands.Context, 
        msg: discord.Message, 
        delete_after: float
    ) -> None:
        """
        Add a 📌 reaction and handle message deletion with keep option.
        
        Args:
            ctx: The command context
            msg: The message to potentially delete
            delete_after: Seconds to wait before deleting
        """
        try:
            await msg.add_reaction("📌")
            
            await asyncio.sleep(delete_after)
            
            # Refresh the message to get current reactions
            try:
                msg = await ctx.channel.fetch_message(msg.id)
            except discord.NotFound:
                return
            
            for reaction in msg.reactions:
                if str(reaction.emoji) == "📌":
                    async for user in reaction.users():
                        if user.id == ctx.author.id:
                            try:
                                await msg.remove_reaction("📌", ctx.bot.user)
                            except:
                                pass
                            if await self.config.debug():
                                log.debug(f"Message kept by {ctx.author} via 📌 reaction")
                            return
            
            try:
                await msg.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                if await self.config.debug():
                    log.debug(f"No permission to delete message in {ctx.channel}")
            except Exception as e:
                if await self.config.debug():
                    log.debug(f"Failed to delete message: {e}")
                    
        except discord.Forbidden:
            if await self.config.debug():
                log.debug(f"No permission to add reactions in {ctx.channel}")
            try:
                await asyncio.sleep(delete_after)
                await msg.delete()
            except:
                pass
        except Exception as e:
            if await self.config.debug():
                log.debug(f"Error in '_handle_keep_reaction': {e}")
    
    async def _delete_command_message(self, ctx: commands.Context, delay: float = 0) -> None:
        """
        Delete the command message
        
        Args:
            ctx: Command context
            delay: Seconds before deleting (default: 0 = immediate)
        """
        if delay > 0:
            await asyncio.sleep(delay)
        
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass  # already deleted
        except discord.Forbidden:
            if await self.config.debug():
                log.debug(f"No permission to delete command message from {ctx.author}")
        except Exception as e:
            if await self.config.debug():
                log.debug(f"Failed to delete command message: {e}")
    
    async def _parse_placeholder_via_api(
        self, 
        placeholder: str, 
        player: Optional[str], 
        settings: dict
    ) -> Optional[dict]:
        """Query PAPIRestAPI to parse a placeholder"""
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
        
        # embed.add_field(name="🏷️ **Placeholder**", value=f"`{placeholder}`", inline=True)
        # embed.add_field(name="👤 **Context**", value=context, inline=True)
        # embed.add_field(name="#️⃣ **Value**", value=value, inline=False)
        embed.add_field(name="Result", value=f"""```ansi\n\u001b[0;32m{value}\u001b[0;30m\n```""", inline=True)
        embed.add_field(name="Context", value=f"""```ansi\n\u001b[0;34m{context}\u001b[0;30m\n```""", inline=True)
        embed.add_field(name="Placeholder", value=f"""```ansi\n\u001b[0;30m{placeholder}\u001b[0;30m\n```""", inline=False)
        
        # Add player thumbnail if it's a player-specific query
        if context != "Server":
            thumbnail_url = f"https://vzge.me/bust/128/{context}"
            embed.set_thumbnail(url=thumbnail_url)
        
        # timestamp_str = datetime.now().strftime("%d/%m/%Y %I:%M%p")
        embed.set_footer(text=settings["footer_name"], icon_url=settings["footer_icon"])
        
        return embed


async def setup(bot: Red) -> None:
    """Load the PAPI cog"""
    cog = PAPI(bot)
    await bot.add_cog(cog)






