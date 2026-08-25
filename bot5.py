import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os
import sys
import threading
import socket

# ─── SERVER HEALTHCHECK ──────────────────────────────────────
def run_healthcheck_server():
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', 8080))
        server.listen(1)
        print('✅ Healthcheck server running on port 8080')
        while True:
            try:
                client, addr = server.accept()
                client.send(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK')
                client.close()
            except:
                pass
    except Exception as e:
        print(f'⚠️ Healthcheck server error: {e}')

healthcheck_thread = threading.Thread(target=run_healthcheck_server, daemon=True)
healthcheck_thread.start()

# ─── CONFIGURARE ──────────────────────────────────────────────
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
ALLOWED_GUILD_ID = 1464389143479058588
REQUIRED_INVITES = 12

DATA_FILE = 'data.json'
INVITE_CACHE = {}  # Cache pentru invitații

# ─── Verificare token ──────────────────────────────────────
if not DISCORD_TOKEN:
    print('❌ DISCORD_TOKEN is not set!')
    sys.exit(1)

# ─── JSON storage ──────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except json.JSONDecodeError:
            print('⚠️ data.json is corrupted, creating new one...')
            return {}
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

# ─── Salvează invitațiile la pornire ─────────────────────────
@bot.event
async def on_ready():
    print(f'🤖 Logged in as {bot.user}')
    
    # Salvează toate invitațiile pentru server
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            INVITE_CACHE[guild.id] = {}
            for invite in invites:
                INVITE_CACHE[guild.id][invite.code] = {
                    'uses': invite.uses,
                    'inviter_id': str(invite.inviter.id),
                    'max_age': invite.max_age,
                    'max_uses': invite.max_uses
                }
            print(f'✅ Tracked {len(invites)} invites on {guild.name}')
        except Exception as e:
            print(f'⚠️ Could not fetch invites: {e}')
    
    print(f'✅ Required invites: {REQUIRED_INVITES}')
    
    if ALLOWED_GUILD_ID != 0:
        guild = bot.get_guild(ALLOWED_GUILD_ID)
        if not guild:
            print(f'⚠️ Bot is NOT on the server with ID {ALLOWED_GUILD_ID}!')
        else:
            print(f'✅ Bot is on server: {guild.name} (ID: {guild.id})')
            print(f'✅ Members: {guild.member_count}')
    
    try:
        await bot.tree.sync()
        print('✅ Commands synced')
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')

# ─── CÂND SE CREEAZĂ O INVITAȚIE ────────────────────────────
@bot.event
async def on_invite_create(invite):
    """Când se creează o invitație nouă, o adaugă în cache"""
    try:
        if invite.guild.id not in INVITE_CACHE:
            INVITE_CACHE[invite.guild.id] = {}
        
        INVITE_CACHE[invite.guild.id][invite.code] = {
            'uses': invite.uses,
            'inviter_id': str(invite.inviter.id),
            'max_age': invite.max_age,
            'max_uses': invite.max_uses
        }
        print(f'✅ New invite created: {invite.code} by {invite.inviter.name}')
    except Exception as e:
        print(f'⚠️ Error on_invite_create: {e}')

# ─── CÂND SE ȘTERGE O INVITAȚIE ─────────────────────────────
@bot.event
async def on_invite_delete(invite):
    """Când se șterge o invitație, o elimină din cache"""
    try:
        if invite.guild.id in INVITE_CACHE and invite.code in INVITE_CACHE[invite.guild.id]:
            del INVITE_CACHE[invite.guild.id][invite.code]
            print(f'✅ Invite deleted: {invite.code}')
    except Exception as e:
        print(f'⚠️ Error on_invite_delete: {e}')

# ─── DETECTEAZĂ CINE A INVITAT ─────────────────────────────
@bot.event
async def on_member_join(member):
    """Când un membru nou intră, verifică cine l-a invitat"""
    try:
        # Verifică dacă e serverul corect
        if member.guild.id != ALLOWED_GUILD_ID:
            return
        
        # Așteaptă puțin să se actualizeze invitațiile
        await discord.utils.sleep(1.5)
        
        # Obține invitațiile actuale
        current_invites = await member.guild.invites()
        old_invites = INVITE_CACHE.get(member.guild.id, {})
        
        found_inviter_id = None
        found_invite_code = None
        
        # Metoda 1: Compară direct utilizările
        for invite in current_invites:
            old_data = old_invites.get(invite.code)
            if old_data:
                old_uses = old_data.get('uses', 0)
                if invite.uses > old_uses:
                    found_inviter_id = old_data.get('inviter_id')
                    found_invite_code = invite.code
                    print(f'✅ Found invite by direct compare: {invite.code}')
                    break
        
        # Metoda 2: Dacă nu s-a găsit, caută invitația cu cea mai mare creștere
        if not found_inviter_id and current_invites:
            max_diff = 0
            for invite in current_invites:
                old_data = old_invites.get(invite.code)
                if old_data:
                    diff = invite.uses - old_data.get('uses', 0)
                    if diff > max_diff:
                        max_diff = diff
                        found_inviter_id = old_data.get('inviter_id')
                        found_invite_code = invite.code
            
            if found_inviter_id:
                print(f'✅ Found invite by max diff: {found_invite_code} (diff: {max_diff})')
        
        # Dacă s-a găsit cine a invitat
        if found_inviter_id:
            # Încarcă datele
            data = load_data()
            if found_inviter_id not in data:
                data[found_inviter_id] = {'invites': 0, 'total_claims': 0}
            
            # Adaugă o invitație
            data[found_inviter_id]['invites'] += 1
            save_data(data)
            
            # Log
            try:
                inviter = await bot.fetch_user(int(found_inviter_id))
                print(f'✅ {inviter.name} invited {member.name} (Total: {data[found_inviter_id]["invites"]})')
            except:
                print(f'✅ User {found_inviter_id} invited {member.name}')
        else:
            print(f'⚠️ Could not determine who invited {member.name}')
            print(f'   Current invites: {len(current_invites)}')
            print(f'   Cached invites: {len(old_invites)}')
        
        # Actualizează cache-ul pentru data viitoare
        new_cache = {}
        for invite in current_invites:
            new_cache[invite.code] = {
                'uses': invite.uses,
                'inviter_id': str(invite.inviter.id),
                'max_age': invite.max_age,
                'max_uses': invite.max_uses
            }
        INVITE_CACHE[member.guild.id] = new_cache
            
    except Exception as e:
        print(f'⚠️ Error tracking invite: {e}')

# ─── Command /send_pass ────────────────────────────────────
@bot.tree.command(name='send_pass', description='Sends the Brawl Pass Plus redeem embed with button')
async def send_pass(interaction: discord.Interaction):
    if interaction.guild_id != ALLOWED_GUILD_ID:
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

    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    user_id = str(interaction.user.id)
    data = load_data()

    if user_id not in data:
        data[user_id] = {'invites': 0, 'total_claims': 0}

    user = data[user_id]

    if user['invites'] < REQUIRED_INVITES:
        await interaction.followup.send(
            f'❌ You need {REQUIRED_INVITES - user["invites"]} more invites. '
            f'You have {user["invites"]}/{REQUIRED_INVITES}.',
            ephemeral=True
        )
        return

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

    user['invites'] = 0
    user['total_claims'] = user.get('total_claims', 0) + 1
    save_data(data)

    await interaction.followup.send(
        f'✅ **Brawl Pass Plus code sent to your DMs!**\n'
        f'Invites reset to 0. You need {REQUIRED_INVITES} more invites to claim again.\n'
        f'Total claims: {user["total_claims"]}',
        ephemeral=True
    )

# ─── Admin commands ──────────────────────────────────────────

@bot.tree.command(name='add_invites', description='[Admin] Add invites to a user')
async def add_invites(interaction: discord.Interaction, member: discord.Member, count: int):
    if interaction.guild_id != ALLOWED_GUILD_ID:
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

@bot.tree.command(name='reset_user', description='[Admin] Reset invites for a specific user')
async def reset_user(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild_id != ALLOWED_GUILD_ID:
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
        await interaction.response.send_message(f'✅ {member.mention}\'s invites have been reset to 0.', ephemeral=True)
    else:
        await interaction.response.send_message(f'❌ {member.mention} has no data.', ephemeral=True)

@bot.tree.command(name='reset_all', description='[Admin] Reset all invites for all users')
async def reset_all(interaction: discord.Interaction):
    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    data = {}
    save_data(data)
    await interaction.response.send_message('✅ All user data has been reset.', ephemeral=True)

@bot.tree.command(name='check_invites', description='[Admin] Check invites for a user')
async def check_invites(interaction: discord.Interaction, member: discord.Member):
    if interaction.guild_id != ALLOWED_GUILD_ID:
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

@bot.tree.command(name='view_data', description='[Admin] View all user data')
async def view_data(interaction: discord.Interaction):
    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    data = load_data()
    if not data:
        await interaction.response.send_message('📊 No data available.', ephemeral=True)
        return

    message = f"📊 **User Data:** (Required: {REQUIRED_INVITES} invites)\n```\n"
    for user_id, user_data in data.items():
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.name
        except:
            name = user_id
        message += f"{name}: {user_data['invites']}/{REQUIRED_INVITES} invites, Claims: {user_data.get('total_claims', 0)}\n"
    message += "```"
    
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

@bot.tree.command(name='set_required', description='[Admin] Change the required invites amount')
async def set_required(interaction: discord.Interaction, amount: int):
    if interaction.guild_id != ALLOWED_GUILD_ID:
        await interaction.response.send_message('❌ This bot can only be used on the official server.', ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('❌ Only administrators can use this command.', ephemeral=True)
        return

    global REQUIRED_INVITES
    REQUIRED_INVITES = amount
    await interaction.response.send_message(f'✅ Required invites set to **{amount}**!', ephemeral=True)

if __name__ == '__main__':
    try:
        bot.run(DISCORD_TOKEN)
    except discord.errors.PrivilegedIntentsRequired:
        print('❌ Privileged Intents are not enabled!')
        print('📌 Go to: https://discord.com/developers/applications')
        print('📌 Select your app → Bot → Enable Server Members Intent and Message Content Intent')
        sys.exit(1)
    except Exception as e:
        print(f'❌ Error: {e}')
        sys.exit(1)
