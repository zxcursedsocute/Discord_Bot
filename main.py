import discord
from discord.ext import commands
from discord import option
from datetime import datetime, timedelta
import random
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(intents=intents)

MODERATOR_ROLE_NAME = "Moderator"
ADMINISTRATOR_ROLE_NAME = "Administrator"
BAN_COOLDOWN = timedelta(hours=6)
KICK_COOLDOWN = timedelta(hours=2)
LOG_CHANNEL_ID = 1456806578119376959
YOUR_GUILD_ID = 1434230104694718508

last_ban_time = {}
last_kick_time = {}

def has_moderator_role(member: discord.Member):
    return any(role.name == MODERATOR_ROLE_NAME for role in member.roles)

def has_administrator_role(member: discord.Member):
    return any(role.name == ADMINISTRATOR_ROLE_NAME for role in member.roles)

def remaining_time(delta):
    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    return f"{hours}h {minutes}m"

async def send_log(guild, message):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(message)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    try:
        await bot.sync_commands()
        print("✅ Slash commands synced!")
        print("Available commands:")
        for cmd in bot.application_commands:
            print(f"  /{cmd.name}")
    except Exception as e:
        print(f"❌ Error syncing commands: {e}")

@bot.slash_command(description="Ban a user (moderators/administrators only 6h cd)", guild_ids=[YOUR_GUILD_ID])
@option("user", discord.Member, description="User to ban")
@option("reason", str, description="Reason for ban")
async def ban(ctx, user: discord.Member, reason: str):
    moderator = ctx.author
    now = datetime.utcnow()

    if moderator.id != ctx.guild.owner_id and not has_moderator_role(moderator) and not has_administrator_role(moderator):
        await ctx.respond("❌ You must have **Moderator** or **Administrator** role.", ephemeral=True)
        return

    if has_administrator_role(user) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ You cannot ban an Administrator.", ephemeral=True)
        return

    if has_moderator_role(user) and not has_administrator_role(moderator) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ You cannot ban another Moderator.", ephemeral=True)
        return

    if has_moderator_role(user) and has_administrator_role(moderator) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ Administrators cannot ban Moderators.", ephemeral=True)
        return

    last_time = last_ban_time.get(moderator.id)
    if last_time and now - last_time < BAN_COOLDOWN and moderator.id != ctx.guild.owner_id:
        await ctx.respond(
            f"⏱ You must wait **{remaining_time(BAN_COOLDOWN - (now - last_time))}** before using /ban again.",
            ephemeral=True
        )
        return

    try:
        await user.ban(reason=f"{reason} | Banned by {moderator}")
        last_ban_time[moderator.id] = now
        await ctx.respond(f"🔨 **{user}** (ID: `{user.id}`) has been banned.\nReason: {reason}")
        await send_log(
            ctx.guild,
            f"🔨 **BAN**\nModerator: {moderator}\nUser: {user} (ID: {user.id})\nReason: {reason}\nTime: <t:{int(now.timestamp())}:F>"
        )
    except discord.Forbidden:
        await ctx.respond("❌ I don't have permission to ban this user.", ephemeral=True)

@bot.slash_command(description="Unban a user by ID (moderators/administrators only)", guild_ids=[YOUR_GUILD_ID])
@option("user_id", int, description="ID of the user to unban")
@option("reason", str, description="Reason for unban")
async def unban(ctx, user_id: int, reason: str):
    moderator = ctx.author
    now = datetime.utcnow()

    if moderator.id != ctx.guild.owner_id and not has_moderator_role(moderator) and not has_administrator_role(moderator):
        await ctx.respond("❌ You must have **Moderator** or **Administrator** role.", ephemeral=True)
        return

    try:
        user = await bot.fetch_user(user_id)
        
        try:
            ban_entry = await ctx.guild.fetch_ban(user)
        except discord.NotFound:
            await ctx.respond(f"❌ User with ID `{user_id}` is not banned.", ephemeral=True)
            return

        await ctx.guild.unban(user, reason=f"{reason} | Unbanned by {moderator}")
        
        await ctx.respond(f"✅ User **{user}** (ID: `{user_id}`) has been unbanned.\nReason: {reason}")
        await send_log(
            ctx.guild,
            f"✅ **UNBAN**\nModerator: {moderator}\nUser: {user} (ID: {user_id})\nReason: {reason}\nTime: <t:{int(now.timestamp())}:F>"
        )
    except discord.Forbidden:
        await ctx.respond("❌ I don't have permission to unban users.", ephemeral=True)
    except discord.HTTPException as e:
        await ctx.respond(f"❌ Error: {str(e)}", ephemeral=True)

@bot.slash_command(description="Kick a user (moderators/administrators only 2h cd)", guild_ids=[YOUR_GUILD_ID])
@option("user", discord.Member, description="User to kick")
@option("reason", str, description="Reason for kick")
async def kick(ctx, user: discord.Member, reason: str):
    moderator = ctx.author
    now = datetime.utcnow()

    if moderator.id != ctx.guild.owner_id and not has_moderator_role(moderator) and not has_administrator_role(moderator):
        await ctx.respond("❌ You must have **Moderator** or **Administrator** role.", ephemeral=True)
        return

    if has_administrator_role(user) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ You cannot kick an Administrator.", ephemeral=True)
        return

    if has_moderator_role(user) and not has_administrator_role(moderator) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ You cannot kick another Moderator.", ephemeral=True)
        return

    if has_moderator_role(user) and has_administrator_role(moderator) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ Administrators cannot kick Moderators.", ephemeral=True)
        return

    last_time = last_kick_time.get(moderator.id)
    if last_time and now - last_time < KICK_COOLDOWN and moderator.id != ctx.guild.owner_id:
        await ctx.respond(
            f"⏱ You must wait **{remaining_time(KICK_COOLDOWN - (now - last_time))}** before using /kick again.",
            ephemeral=True
        )
        return

    try:
        await user.kick(reason=f"{reason} | Kicked by {moderator}")
        last_kick_time[moderator.id] = now
        await ctx.respond(f"👢 **{user}** has been kicked.\nReason: {reason}")
        await send_log(
            ctx.guild,
            f"👢 **KICK**\nModerator: {moderator}\nUser: {user}\nReason: {reason}\nTime: <t:{int(now.timestamp())}:F>"
        )
    except discord.Forbidden:
        await ctx.respond("❌ I don't have permission to kick this user.", ephemeral=True)

@bot.slash_command(description="Timeout a user (moderators/administrators only)", guild_ids=[YOUR_GUILD_ID])
@option("user", discord.Member, description="User to timeout")
@option("minutes", int, description="Duration in minutes")
@option("reason", str, description="Reason for timeout")
async def timeout(ctx, user: discord.Member, minutes: int, reason: str):
    moderator = ctx.author
    now = datetime.utcnow()

    if moderator.id != ctx.guild.owner_id and not has_moderator_role(moderator) and not has_administrator_role(moderator):
        await ctx.respond("❌ You must have **Moderator** or **Administrator** role.", ephemeral=True)
        return

    if has_administrator_role(user) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ You cannot timeout an Administrator.", ephemeral=True)
        return

    if has_moderator_role(user) and not has_administrator_role(moderator) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ You cannot timeout another Moderator.", ephemeral=True)
        return

    try:
        duration = timedelta(minutes=minutes)
        await user.timeout_for(duration, reason=f"{reason} | Timed out by {moderator}")
        await ctx.respond(f"⏳ **{user}** has been timed out for **{minutes} minutes**.\nReason: {reason}")
        await send_log(
            ctx.guild,
            f"⏳ **TIMEOUT**\nModerator: {moderator}\nUser: {user}\nDuration: {minutes} minutes\nReason: {reason}\nTime: <t:{int(now.timestamp())}:F>"
        )
    except discord.Forbidden:
        await ctx.respond("❌ I don't have permission to timeout this user.", ephemeral=True)

@bot.slash_command(description="Send text or image as the bot (moderators/administrators only)", guild_ids=[YOUR_GUILD_ID])
@option("text", str, description="Text to send", required=False)
@option("image", discord.Attachment, description="Image to send", required=False)
async def text(ctx, text: str = None, image: discord.Attachment = None):
    moderator = ctx.author
    
    if moderator.id != ctx.guild.owner_id and not has_moderator_role(moderator) and not has_administrator_role(moderator):
        await ctx.respond("❌ You must have **Moderator** or **Administrator** role.", ephemeral=True)
        return
    
    if not text and not image:
        await ctx.respond("❌ You must provide text or an image.", ephemeral=True)
        return
    
    try:
        if image:
            if image.content_type and image.content_type.startswith('image/'):
                file = await image.to_file()
                if text:
                    await ctx.send(content=text, file=file)
                else:
                    await ctx.send(file=file)
            else:
                await ctx.respond("❌ The attachment must be an image.", ephemeral=True)
                return
        else:
            await ctx.send(text)
        
        await ctx.respond("✅ Message sent!", ephemeral=True)
        await send_log(
            ctx.guild,
            f"📝 **TEXT COMMAND**\nModerator: {moderator}\nText: {text if text else 'No text'}\nImage: {'Yes' if image else 'No'}\nChannel: {ctx.channel.mention}\nTime: <t:{int(datetime.utcnow().timestamp())}:F>"
        )
    except discord.Forbidden:
        await ctx.respond("❌ I don't have permission to send messages in this channel.", ephemeral=True)

@bot.slash_command(description="Warn a user by sending them a private message (moderators/administrators only)", guild_ids=[YOUR_GUILD_ID])
@option("user", discord.Member, description="User to warn")
@option("reason", str, description="Reason for warning")
async def warn(ctx, user: discord.Member, reason: str):
    moderator = ctx.author
    now = datetime.utcnow()

    if moderator.id != ctx.guild.owner_id and not has_moderator_role(moderator) and not has_administrator_role(moderator):
        await ctx.respond("❌ You must have **Moderator** or **Administrator** role.", ephemeral=True)
        return

    if has_administrator_role(user) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ You cannot warn an Administrator.", ephemeral=True)
        return

    if has_moderator_role(user) and not has_administrator_role(moderator) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ You cannot warn another Moderator.", ephemeral=True)
        return

    dm_sent = False
    try:
        embed = discord.Embed(
            title=f"⚠️ You have been warned in {ctx.guild.name}",
            color=discord.Color.orange(),
            timestamp=now
        )
        embed.add_field(name="Moderator", value=moderator.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"User ID: {user.id}")
        await user.send(embed=embed)
        dm_sent = True
    except discord.Forbidden:
        dm_sent = False

    log_msg = (
        f"⚠️ **WARN**\n"
        f"Moderator: {moderator}\n"
        f"User: {user} (ID: {user.id})\n"
        f"Reason: {reason}\n"
        f"DM Sent: {'Yes' if dm_sent else 'No'}\n"
        f"Time: <t:{int(now.timestamp())}:F>"
    )
    await send_log(ctx.guild, log_msg)

    response = f"⚠️ **{user}** has been warned.\nReason: {reason}"
    if not dm_sent:
        response += "\n*(Could not send DM to user)*"
    await ctx.respond(response)

@bot.slash_command(description="Check if user is a femboy", guild_ids=[YOUR_GUILD_ID])
@option("user", discord.Member, description="User to check")
async def isfemboy(ctx, user: discord.Member):
    percentage = random.randint(50, 100)
    emoji = "🌸" if percentage > 75 else "💅" if percentage > 60 else "✨"
    
    await ctx.respond(f"{emoji} **{user.name}** is **{percentage}%** femboy! {emoji}")

@bot.slash_command(description="Shut down the bot (owner only)", guild_ids=[YOUR_GUILD_ID])
async def shutdown(ctx):
    if ctx.author.id != ctx.guild.owner_id:
        await ctx.respond("❌ Only the server owner can shut down the bot.", ephemeral=True)
        return
    await ctx.respond("🔌 Bot is shutting down...")
    await bot.close()

bot.run(os.environ["DISCORD_BOT_TOKEN"])
