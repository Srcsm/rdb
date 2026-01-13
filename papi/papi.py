import discord
import logging
import aiohttp
import asyncio
import re
from typing import Optional
from collections import defaultdict
from datetime import datetime, timedelta

from redbot.core import commands, Config, app_commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box

ver = "1.1.6"
log = logging.getLogger("red.papi")
PLACEHOLDER_REGEX = re.compile(r"<([a-zA-Z0-9_:-]+)>")

def default_time():
    return datetime.min

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
            "allowed_roles": "",
            "watch_enabled": False,
            "watch_mode": "disabled",  # 'disabled', 'channels', or 'global'
            "watch_channels": [],
            "watch_cooldown": 5,
            "watch_max_placeholders": 10,
            "watch_reply_type": "reply",  # 'reply' or 'thread'
            "watch_show_errors": True,
            "watch_require_roles": False,
            "watch_delete_trigger": False
        }
    
        self.watch_cooldowns = defaultdict(default_time)
        
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
    
    @commands.group()
    @commands.is_owner()
    async def papiset(self, ctx: commands.Context):
        """Show and configure PAPI settings"""
        pass
    
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
            delete_after=10,
            keep_message=True
        )
    
    @papiset.group(name="config")
    async def papiset_config(self, ctx: commands.Context):
        """Configure PAPI settings"""
        pass
    
    @papiset_config.command(name="allowedroles", aliases=["ar"])
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
    
    @papiset_config.command(name="debug")
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
    
    @papiset_config.group(name="embed")
    async def papiset_config_embed(self, ctx: commands.Context):
        """Configure various embed settings"""
        pass
    
    @papiset_config_embed.command(name="contexttitle", aliases=["ct"])
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
    
    @papiset_config_embed.command(name="footername", aliases=["fn"])
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
    
    @papiset_config_embed.command(name="footericon", aliases=["fi"])
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
    
    @papiset_config_embed.command(name="placeholdertitle", aliases=["pt"])
    async def set_placeholder_title(self, ctx: commands.Context, *, name: str):
        """Set the title for the placeholder field in embeds
        
        Example: `[p]papiset placeholdertitle Placeholder`
        """
        await self.config.embed_placeholder_title.set(name)
        await self.temp_message(
            ctx,
            f"✅ Placeholder title set to: **{name}**",
            delete_after=3,
            delete_command_delay=3
        )
        if await self.config.debug():
            log.info(f"Placeholder title updated by {ctx.author} to: {name}")
    
    @papiset_config_embed.command(name="valuetitle", aliases=["vt"])
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
    
    @papiset_config.group(name="api")
    async def papiset_config_api(self, ctx: commands.Context):
        """Configure API connection settings"""
        pass
    
    @papiset_config_api.command(name="apikey")
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
    
    @papiset_config_api.command(name="apiurl")
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
    
    
    
    @papiset_config_api.command(name="test")
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
    
    
    
    @papiset.group(name="watch")
    async def watch_config(self, ctx: commands.Context):
        """Configure the placeholder watch feature"""
        pass
    
    @watch_config.command(name="enable")
    async def watch_enable(self, ctx: commands.Context):
        """Enable watch mode (uses current mode setting)"""
        current_mode = await self.config.watch_mode()
        if current_mode == "disabled":
            await self.temp_message(
                ctx,
                "❌ Please set watch mode first with `[p]papiset watch mode <channels|global>`",
                delete_command_delay=1
            )
            return
        
        await self.config.watch_enabled.set(True)
        await self.temp_message(
            ctx,
            f"✅ Watch mode enabled in `{current_mode}` mode",
            delete_after=3,
            delete_command_delay=1
        )
    
    @watch_config.command(name="disable")
    async def watch_disable(self, ctx: commands.Context):
        """Disable watch mode"""
        await self.config.watch_enabled.set(False)
        await self.config.watch_mode.set("disabled")
        await self.temp_message(
            ctx,
            "✅ Watch mode disabled",
            delete_after=3,
            delete_command_delay=1
        )
    
    @watch_config.command(name="mode")
    async def watch_mode(self, ctx: commands.Context, mode: str):
        """Set watch mode: channels or global
        
        - channels: Only watch specified channels
        - global: Watch all channels bot can see
        """
        mode = mode.lower()
        if mode not in ["channels", "global"]:
            await self.temp_message(
                ctx,
                "❌ Invalid mode. Use `channels` or `global`",
                delete_after=3,
                delete_command_delay=1
            )
            return
        
        await self.config.watch_mode.set(mode)
        await self.config.watch_enabled.set(True)
        await self.temp_message(
            ctx,
            f"✅ Watch mode set to: `{mode}` (enabled)",
            delete_after=3,
            delete_command_delay=1
        )
    
    @watch_config.command(name="addchannel", aliases=["add"])
    async def watch_add_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Add a channel to the watch list"""
        channels = await self.config.watch_channels()
        
        if channel.id in channels:
            await self.temp_message(
                ctx,
                f"❌ {channel.mention} is already in the watch list",
                delete_after=2,
                delete_command_delay=1,
                keep_message=True
            )
            return
        
        channels.append(channel.id)
        await self.config.watch_channels.set(channels)
        await self.temp_message(
            ctx,
            f"✅ Added {channel.mention} to watch list",
            delete_delay=3,
            delete_command_delay=1,
            keep_message=True
        )
    
    @watch_config.command(name="removechannel", aliases=["remove", "rm"])
    async def watch_remove_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Remove a channel from the watch list"""
        channels = await self.config.watch_channels()
        
        if channel.id not in channels:
            await self.temp_message(
                ctx,
                f"❌ {channel.mention} is not in the watch list",
                delete_delay=3,
                delete_command_delay=1
            )
            return
        
        channels.remove(channel.id)
        await self.config.watch_channels.set(channels)
        await self.temp_message(
            ctx,
            f"✅ Removed {channel.mention} from watch list",
            delete_after=3,
            delete_command_delay=1,
            keep_message=True
        )
    
    @watch_config.command(name="listchannels", aliases=["list"])
    async def watch_list_channels(self, ctx: commands.Context):
        """List all channels in the watch list"""
        channels = await self.config.watch_channels()
        
        if not channels:
            await self.temp_message(
                ctx,
                "ℹ️ No channels in watch list",
                delete_delay=3,
                delete_command_delay=1
            )
            return
        
        channel_mentions = []
        for channel_id in channels:
            channel = ctx.guild.get_channel(channel_id)
            if channel:
                channel_mentions.append(channel.mention)
            else:
                channel_mentions.append(f"Unknown Channel ({channel_id})")
        
        embed = discord.Embed(
            title="Watch List Channels",
            description="\n".join(channel_mentions),
            color=discord.Color.blue()
        )
        await self.temp_message(
            ctx,
            embed=embed,
            delete_after=10,
            delete_command_delay=1,
            keep_message=True
        )
    
    @watch_config.command(name="cooldown", aliases=["cd"])
    async def watch_cooldown(self, ctx: commands.Context, seconds: int):
        """Set cooldown between watch parses per user (0 to disable)"""
        if seconds < 0:
            await self.temp_message(ctx, "❌ Cooldown must be 0 or greater", delete_after=3, delete_command_delay=1)
            return
        
        await self.config.watch_cooldown.set(seconds)
        if seconds == 0:
            await self.temp_message(ctx, "✅ Watch cooldown disabled", delete_after=3, delete_command_delay=1)
        else:
            await self.temp_message(ctx, f"✅ Watch cooldown set to {seconds} seconds", delete_after=3, delete_command_delay=1)
    
    @watch_config.command(name="maxplaceholders", aliases=["max"])
    async def watch_max_placeholders(self, ctx: commands.Context, max_count: int):
        """Set maximum placeholders per message (0 for no limit)"""
        if max_count < 0:
            await self.temp_message(ctx, "❌ Max must be 0 or higher", delete_after=3, delete_command_delay=1)
            return
        
        await self.config.watch_max_placeholders.set(max_count)
        if max_count == 0:
            await self.temp_message(ctx, "✅ Placeholder limit disabled", delete_after=3, delete_command_delay=1)
        else:
            await self.temp_message(ctx, f"✅ Max placeholders set to `{max_count}`", delete_after=3, delete_command_delay=1)
    
    @watch_config.command(name="replytype", aliases=["reply"])
    async def watch_reply_type(self, ctx: commands.Context, reply_type: str):
        """Set reply type: reply or thread"""
        reply_type = reply_type.lower()
        if reply_type not in ["reply", "thread"]:
            await self.temp_message(ctx, "❌ Invalid type. Use `reply` or `thread`", delete_after=3, delete_command_delay=1)
            return
        
        await self.config.watch_reply_type.set(reply_type)
        await self.temp_message(ctx, f"✅ Reply type set to: `{reply_type}`", delete_after=3, delete_command_delay=1)
    
    @watch_config.command(name="showerrors", aliases=["errors"])
    async def watch_show_errors(self, ctx: commands.Context, enabled: bool):
        """Toggle showing errors in parsed messages (true/false)"""
        await self.config.watch_show_errors.set(enabled)
        status = "enabled" if enabled else "disabled"
        await self.temp_message(ctx, f"✅ Error display {status}", delete_after=3, delete_command_delay=1)
    
    @watch_config.command(name="requireroles", aliases=["require"])
    async def watch_require_roles(self, ctx: commands.Context, enabled: bool):
        """Toggle requiring allowed_roles for watch mode (true/false)"""
        await self.config.watch_require_roles.set(enabled)
        status = "enabled" if enabled else "disabled"
        await self.temp_message(ctx, f"✅ Role requirement: {status}", delete_after=3, delete_command_delay=1)
    
    @watch_config.command(name="deletetrigger", aliases=["dt"])
    async def watch_delete_trigger(self, ctx: commands.Context, enabled: bool):
        """Toggle deleting original message after parsing (true/false)"""
        await self.config.watch_delete_trigger.set(enabled)
        status = "enabled" if enabled else "disabled"
        await self.temp_message(ctx, f"✅ Delete command message: {status}", delete_after=3, delete_command_delay=1)
    
    @watch_config.command(name="settings")
    async def watch_settings(self, ctx: commands.Context):
        """Show current watch settings"""
        settings = await self.config.all()
        
        embed = discord.Embed(
            title="🔍 PAPI Watch Settings",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Status
        mode = settings["watch_mode"]
        status = "✅ Enabled" if mode != "disabled" else "❌ Disabled"
        embed.add_field(name="Status", value=f"{status} ({mode})", inline=False)
        
        # Channels
        if mode == "channels":
            channels = settings["watch_channels"]
            if channels:
                channel_list = []
                for channel_id in channels[:10]:  # Limit display
                    channel = ctx.guild.get_channel(channel_id)
                    if channel:
                        channel_list.append(channel.mention)
                channels_text = "\n".join(channel_list) if channel_list else "None"
                if len(channels) > 10:
                    channels_text += f"\n*...and {len(channels) - 10} more*"
            else:
                channels_text = "None configured"
            embed.add_field(name="Watch Channels", value=channels_text, inline=False)
        
        # Other settings
        embed.add_field(name="Cooldown", value=f"{settings['watch_cooldown']}s", inline=True)
        embed.add_field(name="Max Placeholders", value=str(settings['watch_max_placeholders']) or "Unlimited", inline=True)
        embed.add_field(name="Reply Type", value=settings['watch_reply_type'].title(), inline=True)
        embed.add_field(name="Show Errors", value="✅" if settings['watch_show_errors'] else "❌", inline=True)
        embed.add_field(name="Require Roles", value="✅" if settings['watch_require_roles'] else "❌", inline=True)
        embed.add_field(name="Delete Trigger", value="✅" if settings['watch_delete_trigger'] else "❌", inline=True)
        
        # Usage example
        embed.add_field(
            name="Usage Example",
            value="```\nThe server is <server:server_online>.\nRunning version: <server:server_version>\n```",
            inline=False
        )
        
        await self.temp_message(ctx, embed=embed, delete_after=15, delete_command_delay=1, keep_message=True)
    
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
                log.info(f"Successfully sent PAPI response for {placeholder}:{result['value']}")
                
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

    def _dedupe_placeholders(self, placeholders: list[str]) -> list[str]:
        """
        Deduplicate placeholders case-insensitively while preserving original casing.
        Example:
            ["Server:Online", "server:online"] → ["Server:Online"]
        """
        seen = set()
        unique = []
    
        for ph in placeholders:
            key = ph.lower()
            if key not in seen:
                seen.add(key)
                unique.append(ph)
    
        return unique

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages with placeholders and parse them"""
        if message.author.bot:
            return
        
        # Ignore DMs (optional - remove if you want DM support)
        if not message.guild:
            return
        
        # Ignore messages without content
        if not message.content:
            return
        
        settings = await self.config.all()
        debug = settings["debug"]
        
        should_process, reason = await self._should_process_watch(message, settings)
        
        if not should_process:
            if debug and reason != "Watch mode disabled":
                log.debug(f"Skipping watch for message from {message.author}: {reason}")
            return

        matches = PLACEHOLDER_REGEX.findall(message.content)
        if not matches:
            return
        
        # if not self._extract_placeholders(message.content):
        #     return

        unique_placeholders = self._dedupe_placeholders(matches)
        # unique_placeholders = list(dict.fromkeys(matches))
        
        # Enforce max placeholder early
        max_ph = settings["watch_max_placeholders"]
        if max_ph > 0 and len(unique_placeholders) > max_ph:
            if settings["watch_show_errors"]:
                await message.reply(
                    f"❌ Too many placeholders ({len(unique_placeholders)}/{max_ph})",
                    mention_author=False
                )
            return

        
        if debug:
            log.info(f"Processing watch message from {message.author} in #{message.channel.name}")
        
        try:
            result = await self._parse_message_placeholders(message.content, settings)
            
            if "error" in result:
                error_msg = f"❌ {result['error']}"
                if settings["watch_reply_type"] == "reply":
                    await message.reply(error_msg, mention_author=False)
                else:
                    await message.channel.send(error_msg, reference=message)
                return
            
            embed = discord.Embed(
                description=result["parsed_content"],
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            embed.set_author(
                name=f"Parsed for {message.author.display_name}",
                icon_url=message.author.display_avatar.url
            )
            
            footer_text = f"✅ {result['success_count']} parsed"
            if result['error_count'] > 0:
                footer_text += f" • ❌ {result['error_count']} failed"
            
            embed.set_footer(text=footer_text)
            
            if result['errors'] and settings["watch_show_errors"]:
                error_text = "\n".join(result['errors'][:5])  # Limit to 5 errors
                if len(result['errors']) > 5:
                    error_text += f"\n*...and {len(result['errors']) - 5} more*"
                embed.add_field(name="Errors", value=error_text, inline=False)
            
            # Send the response
            if settings["watch_reply_type"] == "thread":
                thread = await message.create_thread(
                    name=f"PAPI Parse - {message.author.display_name}",
                    auto_archive_duration=60
                )
                await thread.send(content=message.author.mention, embed=embed)
            else:
                await message.reply(content=message.author.mention, embed=embed, mention_author=True)
            
            # Delete trigger message if enabled
            if settings["watch_delete_trigger"]:
                try:
                    await message.delete()
                except discord.Forbidden:
                    if debug:
                        log.debug(f"No permission to delete trigger message in {message.channel}")
            
            if debug:
                log.info(f"Successfully parsed watch message from {message.author}")
        
        except Exception as e:
            log.error(f"Error processing watch message: {e}", exc_info=True)
            try:
                await message.reply(
                    "❌ An error occurred while processing your placeholders.",
                    mention_author=True
                )
            except:
                pass

    # def _extract_placeholders(self, content: str) -> list:
    #     """
    #     Extract placeholders from message content
    #     Format: <context:placeholder>
        
    #     Returns list of tuples: [(context, placeholder, full_match), ...]
    #     """
    #     # Regex pattern: <context:placeholder>
    #     # pattern = r'<([^:>]+):([^>]+)>'
    #     matches = re.finditer(PLACEHOLDER_REGEX, content)
        
    #     placeholders = []
    #     for match in matches:
    #         context = match.group(1).strip()
    #         placeholder = match.group(2).strip()
    #         full_match = match.group(0)
    #         placeholders.append((context, placeholder, full_match))
        
    #     return placeholders
    
    async def _check_watch_cooldown(self, user_id: int, cooldown: int) -> bool:
        """Check if user is on cooldown. Boolean result."""
        if cooldown <= 0:
            return True
        
        now = datetime.utcnow()
        last_use = self.watch_cooldowns[user_id]
        
        if now - last_use < timedelta(seconds=cooldown):
            return False
        
        self.watch_cooldowns[user_id] = now
        return True
    
    async def _parse_message_placeholders(self, message_content: str, settings: dict) -> dict:
        """
        Parse all placeholders in a message.
        Returns dict with 'parsed_content', 'success_count', 'error_count', 'errors'
        """
        matches = PLACEHOLDER_REGEX.findall(message_content)
        placeholders = self._dedupe_placeholders(matches)
        # placeholders = self._extract_placeholders(message_content)
        
        max_placeholders = settings["watch_max_placeholders"]
        if max_placeholders > 0 and len(placeholders) > max_placeholders:
            return {
                "error": f"Too many placeholders detected ({len(placeholders)}). Maximum allowed: {max_placeholders}",
                "parsed_content": None
            }
        
        if not placeholders:
            return {
                "error": "No placeholders found in message. Use format: `<context:placeholder>`",
                "parsed_content": None
            }
        
        parsed_content = message_content
        success_count = 0
        error_count = 0
        errors = []
        
        # for context, placeholder, full_match in placeholders:
        for ph in placeholders:
            full_match = f"<{ph}>"
        
            # Split context and placeholder if needed
            if ":" in ph:
                context, placeholder = ph.split(":", 1)
            else:
                context = None
                placeholder = ph

            # player = None if context.lower() == "server" else context
            if context and context.lower() == "server":
                player = None
            else:
                player = context
            
            result = await self._parse_placeholder_via_api(placeholder, player, settings)
            
            if result and result.get("success"):
                parsed_content = parsed_content.replace(full_match, result["value"])
                success_count += 1
            else:
                error_msg = result.get("error", "Unknown error") if result else "Connection failed."
                
                if settings["watch_show_errors"]:
                    # Replace with error indicator
                    parsed_content = parsed_content.replace(full_match, f"❌ *({error_msg})*")
                else:
                    # Leave the original placeholder
                    pass
                
                errors.append(f"`{full_match}`: {error_msg}")
                error_count += 1
        
        return {
            "parsed_content": parsed_content,
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors
        }
    
    async def _should_process_watch(self, message: discord.Message, settings: dict) -> tuple:
        """
        Check if a message should be processed by watch mode.
        Returns (should_process: bool, reason: str)
        """
        watch_mode = settings["watch_mode"]
        if watch_mode == "disabled":
            return (False, "Watch mode disabled")
        
        if watch_mode == "channels":
            if message.channel.id not in settings["watch_channels"]:
                return (False, "Channel not in watch list")
        
        if settings["watch_require_roles"] and message.guild:
            allowed_roles_str = settings["allowed_roles"]
            if allowed_roles_str and allowed_roles_str.strip():
                allowed_roles = self._parse_allowed_roles(allowed_roles_str)
                
                member = message.guild.get_member(message.author.id)
                if not member:
                    return (False, "Member not found")
                
                member_role_ids = [role.id for role in member.roles]
                member_role_names = [role.name for role in member.roles]
                
                has_role = False
                for allowed in allowed_roles:
                    if isinstance(allowed, int):
                        if allowed in member_role_ids:
                            has_role = True
                            break
                    else:
                        if allowed.lower() in [name.lower() for name in member_role_names]:
                            has_role = True
                            break
                
                if not has_role:
                    return (False, "Missing required role")
        
        cooldown = settings["watch_cooldown"]
        if not await self._check_watch_cooldown(message.author.id, cooldown):
            return (False, "User on cooldown")
        
        return (True, "OK")


async def setup(bot: Red) -> None:
    """Load the PAPI cog"""
    cog = PAPI(bot)
    await bot.add_cog(cog)










