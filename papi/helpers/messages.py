import discord
import asyncio
import logging
from typing import Optional
from redbot.core import commands

log = logging.getLogger("red.papi.helpers.messages")

class MessageHelper:
    def __init__(self, config):
        self.config = config
    
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
            asyncio.create_task(self.delete_command_message(ctx, delete_command_delay))

        if keep_message and delete_after > 0:
            asyncio.create_task(self.handle_keep_reaction(ctx, msg, delete_after))
        
        return msg
    
    async def handle_keep_reaction(self, ctx, msg, delete_after: float):
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
    
    async def delete_command_message(self, ctx, delay: float = 0):
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