import discord
from discord.ext import commands
from datetime import timedelta
from dotenv import load_dotenv
import os

# ===== LOAD ENV =====
load_dotenv()
TOKEN = os.getenv("TOKEN")
print("TOKEN =", TOKEN)

if TOKEN is None:
    raise ValueError("Token not found in .env file")
# ================= INTENTS =================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DATA =================
guild_words = {}      # {guild_id: [words]}
guild_warnings = {}   # {guild_id: {user_id: warning_count}}
guild_timeouts = {}   # {guild_id: {user_id: timeout_count}}

# ================= READY =================
@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")

# ================= MESSAGE FILTER =================
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id

    # init guild data
    guild_words.setdefault(guild_id, ["idiot", "stupid"])
    guild_warnings.setdefault(guild_id, {})
    guild_timeouts.setdefault(guild_id, {})

    msg = message.content.lower()
    banned_words = guild_words[guild_id]

    for word in banned_words:
        if word in msg:
            try:
                await message.delete()
            except:
                pass

            user_id = message.author.id

            # ===== WARNINGS =====
            guild_warnings[guild_id][user_id] = guild_warnings[guild_id].get(user_id, 0) + 1
            warnings = guild_warnings[guild_id][user_id]

            await message.channel.send(
                f"{message.author.mention} Warning {warnings}/3 - Toxic language not allowed."
            )

            # ===== TIMEOUT =====
            if warnings >= 3:
                timeout_count = guild_timeouts[guild_id].get(user_id, 0)

                try:
                    if timeout_count == 0:
                        until = discord.utils.utcnow() + timedelta(minutes=5)
                        await message.author.timeout(until)
                        await message.channel.send(f"{message.author.mention} timeout 5 minutes.")
                    else:
                        until = discord.utils.utcnow() + timedelta(hours=1)
                        await message.author.timeout(until)
                        await message.channel.send(f"{message.author.mention} timeout 1 hour.")

                    guild_timeouts[guild_id][user_id] = timeout_count + 1
                    guild_warnings[guild_id][user_id] = 0

                except Exception as e:
                    await message.channel.send("I cannot timeout this user. Check role position.")
                    print(e)

            break

    await bot.process_commands(message)

# ================= COMMANDS =================

def admin_only():
    return commands.has_permissions(administrator=True)

@bot.command()
@admin_only()
async def addword(ctx, word: str):
    guild_id = ctx.guild.id
    guild_words.setdefault(guild_id, [])

    word = word.lower()
    if word not in guild_words[guild_id]:
        guild_words[guild_id].append(word)
        await ctx.send(f"Added word: {word}")
    else:
        await ctx.send("Word already exists.")

@bot.command()
@admin_only()
async def removeword(ctx, word: str):
    guild_id = ctx.guild.id
    word = word.lower()

    if word in guild_words.get(guild_id, []):
        guild_words[guild_id].remove(word)
        await ctx.send(f"Removed word: {word}")
    else:
        await ctx.send("Word not found.")

@bot.command()
async def listwords(ctx):
    guild_id = ctx.guild.id
    words = guild_words.get(guild_id, [])

    if words:
        await ctx.send("Banned words: " + ", ".join(words))
    else:
        await ctx.send("No banned words set.")

# ================= ADMIN UNMUTE =================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    guild_id = ctx.guild.id

    try:
        await member.timeout(None)

        guild_warnings.setdefault(guild_id, {})
        guild_timeouts.setdefault(guild_id, {})

        guild_warnings[guild_id][member.id] = 0
        guild_timeouts[guild_id][member.id] = 0

        await ctx.send(f"{member.mention} unmuted by admin.")

    except Exception as e:
        await ctx.send("I cannot unmute this user.")
        print(e)

# ================= RUN =================
bot.run(TOKEN)

