import discord
from discord.ext import commands
from discord import option
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(intents=intents)

MODERATOR_ROLE_NAME = "Moderator"
BAN_COOLDOWN = timedelta(hours=6)
KICK_COOLDOWN = timedelta(hours=2)
LOG_CHANNEL_ID = 1456806578119376959
YOUR_GUILD_ID = 1434230104694718508

last_ban_time = {}
last_kick_time = {}

def has_moderator_role(member: discord.Member):
    return any(role.name == MODERATOR_ROLE_NAME for role in member.roles)

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

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith(r"\text"):
        content = message.content[5:].strip()
        if content:
            await message.channel.send(content)
            await message.delete()
        else:
            await message.channel.send("❌ Provide text after \\text")

    await bot.process_commands(message)

@bot.slash_command(description="Ban a user (moderators only)", guild_ids=[YOUR_GUILD_ID])
@option("user", discord.Member, description="User to ban")
@option("reason", str, description="Reason for ban")
async def ban(ctx, user: discord.Member, reason: str):
    moderator = ctx.author
    now = datetime.utcnow()

    if moderator.id != ctx.guild.owner_id and not has_moderator_role(moderator):
        await ctx.respond("❌ You must have the **Moderator** role.", ephemeral=True)
        return

    if has_moderator_role(user) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ You cannot ban another moderator.", ephemeral=True)
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
        # Теперь показываем ID пользователя при бане
        await ctx.respond(f"🔨 **{user}** (ID: `{user.id}`) has been banned.\nReason: {reason}")
        await send_log(
            ctx.guild,
            f"🔨 **BAN**\nModerator: {moderator}\nUser: {user} (ID: {user.id})\nReason: {reason}\nTime: <t:{int(now.timestamp())}:F>"
        )
    except discord.Forbidden:
        await ctx.respond("❌ I don't have permission to ban this user.", ephemeral=True)

@bot.slash_command(description="Unban a user by ID (moderators only)", guild_ids=[YOUR_GUILD_ID])
@option("user_id", int, description="ID of the user to unban")
@option("reason", str, description="Reason for unban")
async def unban(ctx, user_id: int, reason: str):
    moderator = ctx.author
    now = datetime.utcnow()

    if moderator.id != ctx.guild.owner_id and not has_moderator_role(moderator):
        await ctx.respond("❌ You must have the **Moderator** role.", ephemeral=True)
        return

    try:
        # Получаем информацию о пользователе по ID
        user = await bot.fetch_user(user_id)
        
        # Проверяем, забанен ли пользователь
        try:
            ban_entry = await ctx.guild.fetch_ban(user)
        except discord.NotFound:
            await ctx.respond(f"❌ User with ID `{user_id}` is not banned.", ephemeral=True)
            return

        # Снимаем бан
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

@bot.slash_command(description="Kick a user (moderators only)", guild_ids=[YOUR_GUILD_ID])
@option("user", discord.Member, description="User to kick")
@option("reason", str, description="Reason for kick")
async def kick(ctx, user: discord.Member, reason: str):
    moderator = ctx.author
    now = datetime.utcnow()

    if moderator.id != ctx.guild.owner_id and not has_moderator_role(moderator):
        await ctx.respond("❌ You must have the **Moderator** role.", ephemeral=True)
        return

    if has_moderator_role(user) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ You cannot kick another moderator.", ephemeral=True)
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

@bot.slash_command(description="Timeout a user (moderators only, no cooldown)", guild_ids=[YOUR_GUILD_ID])
@option("user", discord.Member, description="User to timeout")
@option("minutes", int, description="Duration in minutes")
@option("reason", str, description="Reason for timeout")
async def timeout(ctx, user: discord.Member, minutes: int, reason: str):
    moderator = ctx.author
    now = datetime.utcnow()

    if moderator.id != ctx.guild.owner_id and not has_moderator_role(moderator):
        await ctx.respond("❌ You must have the **Moderator** role.", ephemeral=True)
        return

    if has_moderator_role(user) and moderator.id != ctx.guild.owner_id:
        await ctx.respond("❌ You cannot timeout another moderator.", ephemeral=True)
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

@bot.slash_command(description="Send text as the bot (moderators only)", guild_ids=[YOUR_GUILD_ID])
@option("text", str, description="Text to send")
async def text(ctx, text: str):
    moderator = ctx.author
    
    if moderator.id != ctx.guild.owner_id and not has_moderator_role(moderator):
        await ctx.respond("❌ You must have the **Moderator** role.", ephemeral=True)
        return
    
    try:
        await ctx.send(text)
        await ctx.respond("✅ Message sent!", ephemeral=True)
        await send_log(
            ctx.guild,
            f"📝 **TEXT COMMAND**\nModerator: {moderator}\nText: {text}\nChannel: {ctx.channel.mention}\nTime: <t:{int(datetime.utcnow().timestamp())}:F>"
        )
    except discord.Forbidden:
        await ctx.respond("❌ I don't have permission to send messages in this channel.", ephemeral=True)

@bot.slash_command(description="Shut down the bot (owner only)", guild_ids=[YOUR_GUILD_ID])
async def shutdown(ctx):
    if ctx.author.id != ctx.guild.owner_id:
        await ctx.respond("❌ Only the server owner can shut down the bot.", ephemeral=True)
        return
    await ctx.respond("🔌 Bot is shutting down...")
    await bot.close()

import os
bot.run(os.environ["DISCORD_BOT_TOKEN"])
