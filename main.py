import discord
from discord.ext import commands
import json
import os 

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Sistema de XP y Niveles
xp_per_level = {range(1, 21): 100, range(21, 41): 150, range(41, 61): 200}

# Roles con sus IDs correspondientes
roles_per_level = {
    range(1, 21): "Astronauta",
    range(21, 41): "Tripulante",
    range(41, 61): "Spazio Captain"
}

# IDs de los roles específicos
role_ids = {
    "Astronauta": None,
    "Tripulante": 1253739367483310161,
    "Spazio Captain": 1253739352861839451
}

# Archivo JSON para guardar los datos de los usuarios
data_file = 'users_data.json'

# Cargar datos desde el archivo JSON
if os.path.exists(data_file):
    with open(data_file, 'r') as f:
        try:
            users = json.load(f)
        except json.JSONDecodeError:
            users = {}
else:
    users = {}

def save_data():
    with open(data_file, 'w') as f:
        json.dump(users, f, indent=4)

users = {}

def get_xp_required(level):
    for level_range, xp in xp_per_level.items():
        if level in level_range:
            return xp
    return 200  # Default XP if level exceeds 60

async def assign_role(member, old_level, new_level):
    guild = member.guild
    new_role_name = None
    old_role_name = None

    # Buscar el nombre del rol anterior y el nuevo
    for level_range, role_name in roles_per_level.items():
        if new_level in level_range:
            new_role_name = role_name
            break

    # Obtener el rol anterior del usuario
    for level_range, role_name in roles_per_level.items():
        if old_level in level_range:
            old_role_name = role_name
            break

    if not new_role_name:
        new_role_name = "Spazio Captain"  # Default role if level exceeds 60

    new_role_id = role_ids.get(new_role_name)

    if new_role_id:
        new_role = discord.utils.get(guild.roles, id=new_role_id)

        if new_role:
            current_roles = [role for role in member.roles if role.name in roles_per_level.values()]
            await member.remove_roles(*current_roles)
            await member.add_roles(new_role)

            # Enviar mensaje personalizado de felicitación al usuario
            if old_role_name != new_role_name:  # Solo si el rol ha cambiado
                channel = guild.get_channel(1253720087492562964)
                if channel:
                    xp_total = users[member.id]["xp"]
                    xp_required = get_xp_required(new_level)
                    xp_needed = xp_required - xp_total if xp_total < xp_required else 0

                    progress_bar = generate_progress_bar(xp_total, xp_required)
                    await channel.send(f"Felicidades {member.mention} has conseguido a rango {new_role_name} y ahora tienes más nivel en nuestra nave y contarás con más beneficios!\n\n"
                                       f"**Progresión de XP:**\n{progress_bar}\n"
                                       f"**XP Total:** {xp_total}\n"
                                       f"**XP Necesarios para Subir:** {xp_needed}")

def generate_progress_bar(current, total, bar_length=10):
    progress = current / total
    bar = "["

    num_blocks = int(progress * bar_length)
    bar += "#" * num_blocks
    bar += "-" * (bar_length - num_blocks)

    bar += f"] ({current}/{total})"

    return bar

async def update_xp(user_id, guild, message_content):
    if user_id not in users:
        users[user_id] = {"xp": 0, "level": 1}

    xp_earned = 0

    # Calcular XP basado en la longitud del mensaje
    if len(message_content) > 5:
        xp_earned = 5

    users[user_id]["xp"] += xp_earned

    old_level = users[user_id]["level"]

    # Calcular los niveles que se pueden subir
    while users[user_id]["xp"] >= get_xp_required(users[user_id]["level"]):
        users[user_id]["xp"] -= get_xp_required(users[user_id]["level"])
        users[user_id]["level"] += 1

        member = guild.get_member(user_id)
        await assign_role(member, old_level, users[user_id]["level"])

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await update_xp(message.author.id, message.guild, message.content)
    await bot.process_commands(message)

@bot.command()
async def xp(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_data = users.get(member.id, {"xp": 0, "level": 1})

    xp_total = user_data["xp"]
    xp_required = get_xp_required(user_data["level"])
    xp_needed = xp_required - xp_total if xp_total < xp_required else 0

    progress_bar = generate_progress_bar(xp_total, xp_required)

    channel = ctx.guild.get_channel(1253720419656138782)
    if channel:
        await channel.send(f"{member.mention} está en el nivel {user_data['level']} con {user_data['xp']} XP.\n\n"
                           f"**Progresión de XP:**\n{progress_bar}\n"
                           f"**XP Necesarios para Subir:** {xp_needed}")

@bot.command()
@commands.has_permissions(administrator=True)
async def add_xp(ctx, member: discord.Member, xp: int):
    if member.id not in users:
        users[member.id] = {"xp": 0, "level": 1}
    users[member.id]["xp"] += xp

    # Actualizar niveles después de agregar XP
    await update_xp(member.id, ctx.guild, "")
    await ctx.send(f"{xp} XP añadido a {member.mention}. Ahora tiene {users[member.id]['xp']} XP.")

@add_xp.error
async def add_xp_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("No tienes permiso para usar este comando.")

@bot.command()
@commands.has_permissions(administrator=True)
async def resetxp(ctx, member: discord.Member):
    if member.id in users:
        users[member.id] = {"xp": 0, "level": 1}
        await ctx.send(f"¡Se ha reseteado toda la XP de {member.mention} y ahora está en nivel 1!")
    else:
        await ctx.send(f"No se encontraron datos de XP para {member.mention}.")

@resetxp.error
async def resetxp_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("No tienes permiso para usar este comando.")

@bot.command()
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_data = users.get(member.id, {"xp": 0, "level": 1})
    role_name = None

    for level_range, role in roles_per_level.items():
        if user_data['level'] in level_range:
            role_name = role
            break

    if not role_name:
        role_name = "Spazio Captain"  # Default role if level exceeds 60

    await ctx.send(f"{member.mention} está en el nivel {user_data['level']} y su rango es {role_name}.")

bot.run("MTI1MDE2Mzk1ODY4MjQ4NDk5OA.GNfHZ9.unGY6ox4IWYuimCbLf84u6_UhejRFI__d1zsxw")
