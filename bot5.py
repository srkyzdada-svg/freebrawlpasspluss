import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os

# ─── CONFIGURARE ──────────────────────────────────────────────
# Înlocuiește cu ID-ul serverului tău
# Cum să obții ID-ul: Settings → Advanced → Developer Mode (ON)
# Click dreapta pe numele serverului → Copy ID
ALLOWED_GUILD_ID = 1464389143479058588  # ⚠️ ÎNLOCUIEȘTE CU ID-UL SERVERULUI TĂU
REQUIRED_INVITES = 12  # Numărul de invitații necesare

DATA_FILE = 'data.json'

# ─── Verificare server autorizat ─────────────────────────────
def is_allowed_guild(interaction: discord.Interaction):
    return interaction.guild_id == ALLOWED_GUILD_ID

# ─── JSON storage for invites ──────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ─── Bot ──────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

# ─── Command /send_pass ────────────────────────────────────
@bot.tree.command(name='send_pass', description='Sends the Brawl Pass Plus redeem embed with button')
async def send_pass(interaction: discord.Interaction):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    embed = discord.Embed(
        title='🎫 **Brawl Pass Plus - Redeem**',
        description='Click the button below to redeem.',
        color=discord.Color.purple()
    )
    embed.add_field(
        name='📌 Requirement',
        value=f'**{REQUIRED_INVITES} invites** on this server.',
        inline=False
    )
    embed.add_field(
        name='⚠️ Limit',
        value='Unlimited claims! Invites reset after each claim.',
        inline=False
    )
    embed.set_footer(text='Brawl Pass Plus • 2026')

    view = View()
    button = Button(label='🎁 Redeem Brawl Pass Plus', style=discord.ButtonStyle.primary, custom_id='redeem_pass')
    view.add_item(button)

    await interaction.response.send_message(embed=embed, view=view)

# ─── Button callback ────────────────────────────────────────
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return

    if interaction.data.get('custom_id') != 'redeem_pass':
        return

    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    user_id = str(interaction.user.id)
    data = load_data()

    if user_id not in data:
        data[user_id] = {'invites': 0, 'total_claims': 0}  # Eliminat 'claimed'

    user = data[user_id]

    # Verifică dacă utilizatorul are suficiente invitații
    if user['invites'] < REQUIRED_INVITES:
        await interaction.followup.send(
            f'❌ You need {REQUIRED_INVITES - user["invites"]} more invites. '
            f'You have {user["invites"]}/{REQUIRED_INVITES}.',
            ephemeral=True
        )
        return

    # ─── EDITEAZĂ AICI ──────────────────────────────────────
    # Înlocuiește codul Brawl Pass Plus cu cel real
    try:
        await interaction.user.send(
            "🎫 **BRAWL PASS PLUS REDEEM** 🎫\n\n"
            "✅ **Your Brawl Pass Plus code:**\n"
            "```\n"
            "BRAWL-PASS-PLUS-CODE-HERE\n"
            "```\n\n"
            "📌 **How to redeem:**\n"
            "1. Open Brawl Stars\n"
            "2. Go to Settings\n"
            "3. Click 'Redeem Code'\n"
            "4. Enter the code above\n\n"
            f"📊 **You have claimed {user['total_claims'] + 1} times!**\n"
            "⚠️ Code expires in 24 hours!"
        )
    except:
        await interaction.followup.send('⚠️ Cannot send DM. Please enable DMs from server members.', ephemeral=True)
        return

    # Resetează invitațiile la 0 și crește numărul de claim-uri
    user['invites'] = 0
    user['total_claims'] = user.get('total_claims', 0) + 1
    save_data(data)

    await interaction.followup.send(
        f'✅ **Brawl Pass Plus code sent to your DMs!**\n'
        f'Invites reset to 0. You need {REQUIRED_INVITES} more invites to claim again.\n'
        f'Total claims: {user["total_claims"]}',
        ephemeral=True
    )

# ─── Admin command: manually add invites ───────────────────
@bot.tree.command(name='add_invites', description='[Admin] Add invites to a user')
async def add_invites(interaction: discord.Interaction, member: discord.Member, count: int):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    data = load_data()
    uid = str(member.id)
    if uid not in data:
        data[uid] = {'invites': 0, 'total_claims': 0}
    data[uid]['invites'] += count
    save_data(data)

    await interaction.response.send_message(
        f'✅ {member.mention} now has {data[uid]["invites"]}/{REQUIRED_INVITES} invites.',
        ephemeral=True
    )

# ─── Admin command: reset all invites ──────────────────────
@bot.tree.command(name='reset_all', description='[Admin] Reset all invites for all users')
async def reset_all(interaction: discord.Interaction):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    data = {}
    save_data(data)
    await interaction.response.send_message('✅ All user data has been reset.', ephemeral=True)

# ─── Admin command: reset user invites ─────────────────────
@bot.tree.command(name='reset_user', description='[Admin] Reset invites for a specific user')
async def reset_user(interaction: discord.Interaction, member: discord.Member):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    data = load_data()
    uid = str(member.id)
    if uid in data:
        data[uid]['invites'] = 0
        save_data(data)
        await interaction.response.send_message(
            f'✅ {member.mention}\'s invites have been reset to 0.',
            ephemeral=True
        )
    else:
        await interaction.response.send_message(f'❌ {member.mention} has no data.', ephemeral=True)

# ─── Admin command: check user invites ─────────────────────
@bot.tree.command(name='check_invites', description='[Admin] Check invites for a user')
async def check_invites(interaction: discord.Interaction, member: discord.Member):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    data = load_data()
    uid = str(member.id)
    if uid in data:
        user_data = data[uid]
        await interaction.response.send_message(
            f'📊 **{member.name}**\n'
            f'Invites: {user_data["invites"]}/{REQUIRED_INVITES}\n'
            f'Total Claims: {user_data.get("total_claims", 0)}\n'
            f'Can Claim: {"✅ Yes" if user_data["invites"] >= REQUIRED_INVITES else "❌ No"}',
            ephemeral=True
        )
    else:
        await interaction.response.send_message(f'❌ {member.mention} has no data.', ephemeral=True)

# ─── Admin command: view all data ──────────────────────────
@bot.tree.command(name='view_data', description='[Admin] View all user data')
async def view_data(interaction: discord.Interaction):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    data = load_data()
    if not data:
        await interaction.response.send_message('📊 No data available.', ephemeral=True)
        return

    # Creează un mesaj cu toate datele
    message = f"📊 **User Data:** (Required: {REQUIRED_INVITES} invites)\n```\n"
    for user_id, user_data in data.items():
        # Încearcă să obții numele utilizatorului
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.name
        except:
            name = user_id
        
        message += f"{name}: {user_data['invites']}/{REQUIRED_INVITES} invites, Claims: {user_data.get('total_claims', 0)}\n"
    
    message += "```"
    
    # Dacă mesajul e prea lung, trimite-l într-un fișier
    if len(message) > 2000:
        with open('data_export.txt', 'w') as f:
            f.write(message)
        await interaction.response.send_message(
            "📊 Data is too long to display. Here's a file:",
            file=discord.File('data_export.txt'),
            ephemeral=True
        )
        os.remove('data_export.txt')
    else:
        await interaction.response.send_message(message, ephemeral=True)

# ─── Admin command: set required invites ───────────────────
@bot.tree.command(name='set_required', description='[Admin] Change the required invites amount')
async def set_required(interaction: discord.Interaction, amount: int):
    # Verificare server autorizat
    if not is_allowed_guild(interaction):
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    global REQUIRED_INVITES
    REQUIRED_INVITES = amount
    await interaction.response.send_message(
        f'✅ Required invites set to **{amount}**!',
        ephemeral=True
    )

# ─── Start the bot ──────────────────────────────────────────
@bot.event
async def on_ready():
    print(f'🤖 Logged in as {bot.user}')
    
    # Verifică dacă botul e pe serverul corect
    guild = bot.get_guild(ALLOWED_GUILD_ID)
    if not guild:
        print(f'⚠️ Bot is NOT on the server with ID {ALLOWED_GUILD_ID}!')
        print('⚠️ The bot will NOT work on any server!')
        print('⚠️ Check the server ID and make sure the bot is invited to the correct server.')
    else:
        print(f'✅ Bot is on server: {guild.name} (ID: {guild.id})')
        print(f'✅ Members: {guild.member_count}')
        print(f'✅ Required invites: {REQUIRED_INVITES}')
    
    await bot.tree.sync()
    print('✅ Commands synced')

if __name__ == '__main__':
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise ValueError('❌ DISCORD_TOKEN is not set!')
    bot.run(token)
