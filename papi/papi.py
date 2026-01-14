import discord
import logging
import aiohttp
import asyncio
import re
import io
import json
from typing import Optional
from collections import defaultdict
from datetime import datetime, timedelta

from redbot.core import commands, Config, app_commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box

ver = "1.2.0"
log = logging.getLogger("red.papi")

def default_time():
    return datetime.min

class PAPI(commands.Cog):
    """PlaceholderAPI integration for Red.
    
    Query placeholders with a Discord slash command.
    """
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=8008132, force_registration=True)
        self.message_helper = MessageHelper(self.config)
        self.role_helper = RoleHelper()
        self.watch_listener = WatchListener(self)
        
        # Default settings
        default_global = {
            "footer_name": "MC SMP",
            "footer_icon": "https://i.imgur.com/example.png",
            "debug": False,
            "api_url": "http://localhost:8080",
            "api_key": "SECRET-KEY",
            "embed_value_title": "Value",
            "embed_context_title": "Context",
            "embed_placeholder_title": "Placeholder",
            "allowed_roles": "",
            "watch_enabled": False,
            "watch_mode": "disabled",  # 'disabled', 'channels', or 'global'
            "watch_strict_mode": False,
            "watch_channels": [],
            "watch_cooldown": 5,
            "watch_max_placeholders": 10,
            "watch_reply_type": "reply",  # 'reply' or 'thread'
            "watch_show_errors": True,
            "watch_require_roles": False,
            "watch_delete_trigger": True
        }

        self.config.register_global(**default_global)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def cog_load(self):
        """Called when the cog loads"""
        self.session = aiohttp.ClientSession()
        self.api_helper = APIHelper(self.session, self.config, ver)
        self.embed_helper = EmbedHelper(self.api_helper)
        settings = await self.config.all()
        if settings["debug"]:
            log.info("PAPI Debug mode enabled.")
        
        # Warn if using default API key
        if settings["api_key"] == "SECRET-KEY":
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
        """Base PAPI cog command"""
        pass
    
    @papiset.command(name="settings", aliases=["info"])
    async def show_settings(self, ctx: commands.Context):
        """Show current PAPI cog settings"""
        settings = await self.config.all()
        
        embed = discord.Embed(
            title="🔧 PAPI Settings",
            color=await ctx.embed_color(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Footer Name", value=settings["footer_name"], inline=False)
        embed.add_field(name="Footer Icon", value=settings["footer_icon"], inline=False)
        embed.add_field(name="API URL", value=settings["api_url"], inline=False)
        embed.add_field(name="API Key", value="✅ Set" if settings["api_key"] != "SECRET-KEY" else "⚠️ _**Missing API key!**_", inline=False)
        embed.add_field(name="Debug Mode", value="✅ Enabled" if settings["debug"] else "❌ Disabled", inline=False)
        
        await self.message_helper.temp_message(
            ctx,
            embed=embed,
            delete_after=15,
            keep_message=True
        )
    
    @papiset.group(name="config")
    async def papiset_config(self, ctx: commands.Context):
        """Commands to configure PAPI settings"""
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
            message = "✅ Role restrictions cleared - everyone can use [p]papi"
        await self.message_helper.temp_message(
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
        await self.message_helper.temp_message(
            ctx,
            f"✅ Debug mode {status}",
            delete_after=3
        )
        log.info(f"Debug mode {status} by {ctx.author}")
    
    @papiset_config.command(name="export")
    async def config_export(self, ctx: commands.Context):
        """Export settings, excluding senitive fields."""
        settings = await self.config.all()
        
        # Don't export sensitive fields
        settings.pop("api_key", None)
        settings.pop("api_url", None)
        
        import json
        data = json.dumps(settings, indent=4)
        
        await ctx.send(
            "📦 **PAPI settings file exported.**\nSensitive fields have been excluded and cannot be imported.",
            file=discord.File(
                fp=io.BytesIO(data.encode("utf-8")),
                filename="papi_settings.json"
            )
        )
        
        asyncio.create_task(self.message_helper.delete_command_message(ctx, delay=0))
    
    @papiset_config.command(name="import")
    async def config_import(self, ctx: commands.Context, file: discord.Attachment):
        """Import settings from a JSON file."""
        if not file.filename.endswith(".json"):
            return await self.message_helper.temp_message(ctx, "❌ Settings must be in a JSON file.", delete_after=3)
            
        data = json.loads(await file.read())
        
        # Don't allow the import of sensitive fields
        data.pop("api_key", None)
        data.pop("api_url", None)
        
        await self.config.set(data)
        
        await self.message_helper.temp_message(ctx, "✅ Successfully imported settings.\n⚠️ Remember to set your API details again.", delete_after=6)
    
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
        await self.message_helper.temp_message(
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
        await self.message_helper.temp_message(
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
        await self.message_helper.temp_message(
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
        await self.message_helper.temp_message(
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
        await self.message_helper.temp_message(
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
            await self.message_helper.temp_message(
                ctx,
                "✅ API key has been set securely.",
                delete_after=3,
                delete_command=False
            )
        except discord.errors.Forbidden:
            await self.message_helper.temp_message(
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
        url = url.rstrip('/')
        await self.config.api_url.set(url)
        await self.message_helper.temp_message(
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
                        await self.message_helper.temp_message(
                            ctx,
                            embed=embed,
                            delete_after=10,
                            delete_command=True,
                            keep_message=True
                        )
                    else:
                        await self.message_helper.temp_message(
                            ctx,
                            f"❌ Connection failed! Status code: {resp.status}",
                            delete_after=3
                        )
            except aiohttp.ClientError as e:
                await self.message_helper.temp_message(
                    ctx,
                    f"❌ Connection failed: {str(e)}\n\nEnsure your server is running and the API URL is correct.",
                    delete_after=3
                )
            except Exception as e:
                log.error(f"Error testing connection: {e}", exc_info=True)
                await self.message_helper.temp_message(
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
        """Enable message watch mode (uses current mode setting)"""
        current_mode = await self.config.watch_mode()
        if current_mode == "disabled":
            await self.message_helper.temp_message(
                ctx,
                "❌ Please set the watch mode first with `[p]papiset watch mode <channels|global>`",
                delete_after=8
            )
            return
        
        await self.config.watch_enabled.set(True)
        await self.message_helper.temp_message(
            ctx,
            f"✅ Watch mode enabled in `{current_mode}` mode",
            delete_after=3
        )
    
    @watch_config.command(name="disable")
    async def watch_disable(self, ctx: commands.Context):
        """Disable message watch mode"""
        await self.config.watch_enabled.set(False)
        await self.config.watch_mode.set("disabled")
        await self.message_helper.temp_message(
            ctx,
            "✅ Watch mode disabled",
            delete_after=3
        )
    
    @watch_config.command(name="mode")
    async def watch_mode(self, ctx: commands.Context, mode: str):
        """Set watch mode: channels or global
        
        - channels: Watch specified channels only
        - global: Watch all channels the bot can see
        """
        mode = mode.lower()
        if mode not in ["channels", "global"]:
            await self.message_helper.temp_message(
                ctx,
                "❌ Invalid mode. Must be `channels` or `global`"
            )
            return
        
        await self.config.watch_mode.set(mode)
        await self.config.watch_enabled.set(True)
        await self.message_helper.temp_message(
            ctx,
            f"✅ Watch mode set to: `{mode}` (enabled)",
            delete_after=3
        )
        
    @watch_config.command(name="strict")
    async def watch_strict(self, ctx: commands.Context, enabled: bool):
        """Require ||papi|| spoiler tag at the start of messages for watch mode."""
        await self.config.watch_strict_mode.set(enabled)
        status = "enabled" if enabled else "disabled"
        await self.message_helper.temp_message(ctx, f"✅ Strict mode {status}", delete_after=3)
    
    @watch_config.command(name="addchannel", aliases=["add"])
    async def watch_add_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Add a channel to the watch list"""
        channels = await self.config.watch_channels()
        
        if channel.id in channels:
            await self.message_helper.temp_message(
                ctx,
                f"❌ {channel.mention} is already in the `channels` list",
                delete_after=3
            )
            return
        
        channels.append(channel.id)
        await self.config.watch_channels.set(channels)
        await self.message_helper.temp_message(
            ctx,
            f"✅ Added {channel.mention} to `channels` list",
            delete_delay=5,
            keep_message=True
        )
    
    @watch_config.command(name="removechannel", aliases=["remove", "rm"])
    async def watch_remove_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Remove a channel from the `channels` list"""
        channels = await self.config.watch_channels()
        
        if channel.id not in channels:
            await self.message_helper.temp_message(
                ctx,
                f"❌ {channel.mention} is not in the `channels` list",
                delete_delay=5
            )
            return
        
        channels.remove(channel.id)
        await self.config.watch_channels.set(channels)
        await self.message_helper.temp_message(
            ctx,
            f"✅ Removed {channel.mention} from `channels` list",
            delete_after=3,
            keep_message=True
        )
    
    @watch_config.command(name="listchannels", aliases=["list"])
    async def watch_list_channels(self, ctx: commands.Context):
        """List all channels in the `channels` list"""
        channels = await self.config.watch_channels()
        
        if not channels:
            await self.message_helper.temp_message(
                ctx,
                "ℹ️ No channels in `channels` list",
                delete_delay=3
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
        await self.message_helper.temp_message(
            ctx,
            embed=embed,
            delete_after=10,
            keep_message=True
        )
    
    @watch_config.command(name="cooldown", aliases=["cd"])
    async def watch_cooldown(self, ctx: commands.Context, seconds: int):
        """Set a cooldown between message parses per user (0 to disable)"""
        if seconds < 0:
            await self.message_helper.temp_message(ctx, "❌ Cooldown must be 0 or greater", delete_after=3)
            return
        
        await self.config.watch_cooldown.set(seconds)
        if seconds == 0:
            await self.message_helper.temp_message(ctx, "✅ Watch cooldown disabled", delete_after=3)
        else:
            await self.message_helper.temp_message(ctx, f"✅ Watch cooldown set to {seconds} seconds", delete_after=3)
    
    @watch_config.command(name="maxplaceholders", aliases=["max"])
    async def watch_max_placeholders(self, ctx: commands.Context, max_count: int):
        """Set the max placeholders allowed per message (0 for no limit)"""
        if max_count < 0:
            await self.message_helper.temp_message(ctx, "❌ Max must be `0` or higher", delete_after=3)
            return
        
        await self.config.watch_max_placeholders.set(max_count)
        if max_count == 0:
            await self.message_helper.temp_message(ctx, "✅ Placeholder limit disabled.", delete_after=3)
        else:
            await self.message_helper.temp_message(ctx, f"✅ Max placeholders set to `{max_count}`", delete_after=3)
    
    @watch_config.command(name="replytype", aliases=["reply"])
    async def watch_reply_type(self, ctx: commands.Context, reply_type: str):
        """Set reply type: reply or thread"""
        reply_type = reply_type.lower()
        if reply_type not in ["reply", "thread"]:
            await self.message_helper.temp_message(ctx, "❌ Invalid type. Use `reply` or `thread`", delete_after=3)
            return
        
        await self.config.watch_reply_type.set(reply_type)
        await self.message_helper.temp_message(ctx, f"✅ Reply type set to: `{reply_type}`", delete_after=3)
    
    @watch_config.command(name="showerrors", aliases=["errors"])
    async def watch_show_errors(self, ctx: commands.Context, enabled: bool):
        """Toggle showing errors in parsed messages (true/false)"""
        await self.config.watch_show_errors.set(enabled)
        status = "enabled" if enabled else "disabled"
        await self.message_helper.temp_message(ctx, f"✅ Error display {status}", delete_after=3)
    
    @watch_config.command(name="requireroles", aliases=["require"])
    async def watch_require_roles(self, ctx: commands.Context, enabled: bool):
        """Toggle requiring allowed_roles for watch mode (true/false)"""
        await self.config.watch_require_roles.set(enabled)
        status = "enabled" if enabled else "disabled"
        await self.message_helper.temp_message(ctx, f"✅ Role requirement: `{status}`", delete_after=3)
    
    @watch_config.command(name="deletetrigger", aliases=["dt"])
    async def watch_delete_trigger(self, ctx: commands.Context, enabled: bool):
        """Toggle deleting user message after parsing (true/false)"""
        await self.config.watch_delete_trigger.set(enabled)
        status = "enabled" if enabled else "disabled"
        await self.message_helper.temp_message(ctx, f"✅ Delete command message: {status}", delete_after=3)
    
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
        
        embed.add_field(
            name="Usage Example",
            value="```\nThe server is <server:server_online>.\nRunning version: <server:server_version>\n```",
            inline=False
        )
        
        await self.message_helper.temp_message(ctx, embed=embed, delete_after=15, keep_message=True)
    
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

            if settings["api_key"] == "change-me-please":
                await interaction.followup.send(
                    "❌ **Error:** API key has not been configured! Please contact the bot owner.",
                    ephemeral=True
                )
                return
            
            result = await self.api_helper.parse_placeholder_via_api(placeholder, player, settings)
            
            if result is None:
                await interaction.followup.send(
                    f"❌ **Error:** Failed to connect to PAPIRestAPI or your Minecraft server.\n\nCheck your configuration or try again later.",
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
            
            # Make success embed
            embed = await self.embed_helper.create_success_embed(
                placeholder=result["placeholder"],
                value=result["value"],
                context=result["context"],
                user=interaction.user,
                settings=settings
            )
            
            await interaction.followup.send(embed=embed)
            
            if debug:
                log.info(f"Successful PAPI response for {placeholder}:{result['value']}")
                
        except Exception as e:
            log.error(f"Error in PAPI command: {e}", exc_info=True)
            await interaction.followup.send(
                "❌ **Error:** An unexpected error occurred.",
                ephemeral=True
            )

async def setup(bot: Red) -> None:
    """Load the PAPI cog"""
    cog = PAPI(bot)
    await bot.add_cog(cog)
