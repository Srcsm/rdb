import discord
import re
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import TYPE_CHECKING

from .helpers import APIHelper, EmbedHelper, MessageHelper, RoleHelper
from .watch import WatchListener

if TYPE_CHECKING:
    from ..papi import PAPI

PLACEHOLDER_REGEX = re.compile(r"<([a-zA-Z0-9_:-]+)>")
log = logging.getLogger("red.papi.watch")

def default_time():
    return datetime.min

class WatchListener:
    def __init__(self, cog: "PAPI"):
        self.cog = cog
        self.cooldowns = defaultdict(default_time)
    
    @staticmethod
    def dedupe_placeholders(placeholders: list[str]) -> list[str]:
        """
        Deduplicate placeholders case-insensitively and preserve original casing.
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
    
    async def check_cooldown(self, user_id: int, cooldown: int) -> bool:
        """Check if user is on cooldown. Returns a boolean."""
        if cooldown <= 0:
            return True
        
        now = datetime.utcnow()
        last_use = self.cooldowns[user_id]
        
        if now - last_use < timedelta(seconds=cooldown):
            return False
        
        self.cooldowns[user_id] = now
        return True
    
    async def parse_message_placeholders(self, message_content: str, settings: dict) -> dict:
        """
        Parse all placeholders in a message.
        Returns dict with 'parsed_content', 'success_count', 'error_count', 'errors'
        """
        matches = PLACEHOLDER_REGEX.findall(message_content)
        placeholders = self.dedupe_placeholders(matches)
        
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
            
            result = await self.cog.api_helper.parse_placeholder_via_api(placeholder, player, settings)
            
            if result and result.get("success"):
                parsed_content = parsed_content.replace(full_match, result["value"])
                success_count += 1
            else:
                error_msg = result.get("error", "Unknown error") if result else "Connection failed."
                
                if settings["watch_show_errors"]:
                    # Replace with error indicator
                    parsed_content = parsed_content.replace(full_match, f"❌ *({error_msg})*")
                else:
                    # original placeholder
                    pass
                
                errors.append(f"`{full_match}`: {error_msg}")
                error_count += 1
        
        return {
            "parsed_content": parsed_content,
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors
        }
    
    async def should_process_watch(self, message: discord.Message, settings: dict) -> tuple:
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
                allowed_roles = self.cog.role_helper.parse_allowed_roles(allowed_roles_str)
                
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
        if not await self.check_cooldown(message.author.id, cooldown):
            return (False, "User on cooldown")
        
        return (True, "OK")
    
    async def on_message(self, message: discord.Message):
        """Listener for messages with placeholder to parse"""
        if message.author.bot:
            return
        
        if not message.guild:
            return
        
        if not message.content:
            return
        
        settings = await self.cog.config.all()
        debug = settings["debug"]
        
        should_process, reason = await self.should_process_watch(message, settings)

        if settings["watch_strict_mode"]:
            # Must start with a spoiler tag containing "papi"
            if not message.content.startswith("||papi||"):
                return

            # Remove the trigger from the content before parsing
            content = message.content[len("||papi||"):].lstrip()
        else:
            content = message.content
        
        
        if not should_process:
            if debug and reason != "Watch mode disabled":
                log.debug(f"Skipping watch for message from {message.author}: {reason}")
            return

        matches = PLACEHOLDER_REGEX.findall(message.content)
        if not matches:
            return
        
        unique_placeholders = self.dedupe_placeholders(matches)
        
        # Enforce max placeholder early on
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
            result = await self.parse_message_placeholders(content, settings) # message.content
            
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
                error_text = "\n".join(result['errors'][:5])  # Show up to 5 errors
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