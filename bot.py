import discord
from discord.ext import commands
from discord import app_commands

import json
import os
import time

from datetime import datetime, timezone

INTENTS = discord.Intents.all()

client = commands.Bot(
    command_prefix="!",
    intents=INTENTS
)

#JSON

with open(
    "config.json",
    "r",
    encoding="utf-8"
) as archivo:

    config = json.load(archivo)

TOKEN = config["BOT_TOKEN"]
HOST_ROLE_ID = config["ESTUDIANTE_DEFINITIVO_ID"]
VOICE_CATEGORY_ID = config["INGAME_CATEGORY_ID"]
ADMIN_ID = config["ADMIN_ROLE_ID"]


if not os.path.exists("partidas.json"):

    with open(
        "partidas.json",
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            {},
            archivo,
            indent=4,
            ensure_ascii=False
        )


with open(
    "partidas.json",
    "r",
    encoding="utf-8"
) as archivo:

    partidas = json.load(archivo)


# CONSTANTES

UNIVERSAL_TZ = timezone.utc

IMAGEN_PARTIDA = (
    "https://media.discordapp.net/attachments/"
    "1554199273527050270/1554199301243273246/"
    "rq070kf.jfif?ex=6abc0465&is=6abab2e5&"
    "hm=9483976461136175c2f9c3a84c3a9e4ebfffd707"
    "fa0ffcc09e634f4ce9550198&=&format=webp"
)

JUGADORES_NECESARIOS = 16
BUMP_ROLE_ID = config["BUMP_ROLE_ID"]
BUMP_CHANNEL_ID = config["BUMP_CHANNEL_ID"]
BUMP_COOLDOWN_SECONDS = 60 * 60
bump_cooldowns = {}


def guardar_partidas():

    with open(
        "partidas.json",
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            partidas,
            archivo,
            indent=4,
            ensure_ascii=False
        )


def obtener_partida(message_id):

    message_id = int(message_id)

    for partida in partidas.values():

        if partida.get("message_id") == message_id:
            return partida

    return None



def Es_Admin(usuario: discord.Member) -> bool:
    if usuario.id == 387765989854543882:
        return True

    if usuario.guild_permissions.administrator:
        return True

    return any(
        rol.id == ADMIN_ID
        for rol in usuario.roles
    )


def generar_lista_jugadores(partida):

    texto = ""

    for numero, jugador in enumerate(
        partida["jugadores"],
        start=1
    ):

        texto += (
            f"{numero}. "
            f"<@{jugador['user_id']}> "
            f"({jugador['personaje']})\n"
        )

    return texto


def generar_cuadro_jugadores(partida):

    cantidad = len(
        partida["jugadores"]
    )

    cuadros = []

    for i in range(JUGADORES_NECESARIOS):

        if i < cantidad:

            cuadros.append(
                ":green_square:"
            )

        else:

            cuadros.append(
                ":black_large_square:"
            )

    return " ".join(cuadros)


def crear_embed_partida(partida):

    es_quick_play = (
        partida["timestamp"] is None
    )

    if es_quick_play:

        color = discord.Color.from_str(
            "#2090f7"
        )

        titulo = (
            f"Partida Quick Play de "
            f"{partida['host_name']}"
        )

    else:

        color = discord.Color.from_str(
            "#14b306"
        )

        titulo = (
            f"Partida programada de "
            f"{partida['host_name']}"
        )

    if partida.get("title", "").strip():

        titulo = partida["title"].strip()

    cantidad = len(
        partida["jugadores"]
    )

    descripcion = (
        f"{cantidad}/{JUGADORES_NECESARIOS} "
        f":busts_in_silhouette:\n"
        f"{generar_cuadro_jugadores(partida)}\n\n"
        f"{generar_lista_jugadores(partida)}"
    )

    if partida["extras"]:

        descripcion += "\n**Extras:**\n"

        for extra in partida["extras"]:

            descripcion += (
                f"<@{extra['user_id']}>\n"
            )

    embed = discord.Embed(
        title=titulo,
        description=descripcion,
        color=color
    )

    reglas = partida["reglas"]

    if not reglas:

        reglas = (
            "No hay reglas establecidas "
            "por el anfitrión de la partida."
        )

    embed.add_field(
        name="Reglas del host",
        value=reglas,
        inline=False
    )

    if partida["timestamp"] is not None:

        embed.add_field(
            name="Fecha y hora de la partida",
            value=(
                f"<t:{partida['timestamp']}:F>"
            ),
            inline=False
        )

    embed.set_image(
        url=IMAGEN_PARTIDA
    )


    embed.set_footer(
        text=(
            f"- {partida['host_name']}"
        )
    )

    return embed


async def finalizar_partida_admin(
    interaction,
    partida
):

    guild = interaction.guild


    if partida.get("estado") == "finalizada":

        await interaction.response.send_message(
            "Esta partida ya está finalizada.",
            ephemeral=True
        )

        return


    canal4 = guild.get_channel(
        config["SETUP"]["canal4"]
    )

    if canal4 is None:

        await interaction.response.send_message(
            "No pude encontrar el canal de "
            "partidas finalizadas.",
            ephemeral=True
        )

        return

    embed = crear_embed_partida(
        partida
    )

    await canal4.send(
        embed=embed
    )

    message_id = partida.get(
        "message_id"
    )

    if message_id:

        try:

            mensaje = await guild.get_channel(
                obtener_canal_partida(partida)
            ).fetch_message(
                message_id
            )

            await mensaje.delete()

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
            AttributeError
        ):

            pass


    thread_id = partida.get(
        "thread_id"
    )

    if thread_id:

        try:

            thread = await guild.fetch_channel(
                thread_id
            )

            if isinstance(
                thread,
                discord.Thread
            ):

                await thread.delete()

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):

            pass


    voice_id = partida.get(
        "voice_id"
    )

    if voice_id:

        try:

            canal_voz = guild.get_channel(
                voice_id
            )

            if canal_voz is not None:

                await canal_voz.delete(
                    reason=(
                        "Partida finalizada "
                        "por administrador."
                    )
                )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):

            pass


    partida["estado"] = "finalizada"

    guardar_partidas()




def obtener_canal_partida(partida):

    estado = partida.get(
        "estado"
    )


    if estado == "buscando":

        return config["SETUP"]["canal2"]


    if estado == "en_curso":

        return config["SETUP"]["canal3"]


    if estado == "organizada":

        # Una partida programada todavía
        # está en el canal 2.
        return config["SETUP"]["canal2"]


    return config["SETUP"]["canal2"]


async def crear_thread(
    canal,
    nombre
):

    thread = await canal.create_thread(
        name=nombre,
        type=discord.ChannelType.public_thread,
        invitable=False
    )

    return thread



# AÑADIR JUGADORES AL THREAD

async def actualizar_miembros_thread(
    thread,
    partida
):

    for jugador in partida["jugadores"]:

        try:

            usuario = thread.guild.get_member(
                jugador["user_id"]
            )

            if usuario is not None:

                await thread.add_user(
                    usuario
                )

        except discord.HTTPException:

            pass

async def crear_canal_voz(
    guild,
    partida
):

    categoria = guild.get_channel(
        VOICE_CATEGORY_ID
    )

    if categoria is None:

        return None

    # DETERMINAR NOMBRE

    nombre_base = "Ingame"
    nombre = nombre_base
    numero = 2

    while discord.utils.get(
        categoria.voice_channels,
        name=nombre
    ) is not None:

        nombre = (
            f"{nombre_base} {numero}"
        )

        numero += 1

    overwrites = {

        guild.default_role: discord.PermissionOverwrite(
            connect=False,
            view_channel=False
        )
    }

    # SOLAMENTE DA ACCESO A LOS JUGADORES DE LA PARTIDA CORRESPONDIENTE

    for jugador in partida["jugadores"]:

        usuario = guild.get_member(
            jugador["user_id"]
        )

        if usuario is None:
            continue

        overwrites[usuario] = (
            discord.PermissionOverwrite(
                connect=True,
                view_channel=True
            )
        )

    canal_voz = await guild.create_voice_channel(
        name=nombre,
        category=categoria,
        overwrites=overwrites
    )

    return canal_voz

async def actualizar_permisos_voz(
    canal_voz,
    partida
):

    guild = canal_voz.guild

    await canal_voz.set_permissions(
        guild.default_role,
        connect=False,
        view_channel=False
    )

    for jugador in partida["jugadores"]:

        usuario = guild.get_member(
            jugador["user_id"]
        )

        if usuario is None:
            continue

        await canal_voz.set_permissions(
            usuario,
            connect=True,
            view_channel=True
        )

def generar_ping_jugadores(partida):

    menciones = []

    for jugador in partida["jugadores"]:

        menciones.append(
            f"<@{jugador['user_id']}>"
        )

    return " ".join(menciones)



class CrearPartidaModal(
    discord.ui.Modal,
    title="Crear partida"
):

    titulo = discord.ui.TextInput(
        label="Título de la partida",
        placeholder="Opcional — deja vacío para usar el título predeterminado",
        required=False,
        max_length=100
    )

    fecha_hora = discord.ui.TextInput(
        label="Fecha y hora (Vacío = partida Quick Play)",
        placeholder=(
            "DD/MM/YYYY HH:MM (Hora UTC) "
            "— <t:??????????:F>"
        ),
        required=False,
        max_length=16
    )

    reglas = discord.ui.TextInput(
        label="Reglas / detalles de la partida",
        placeholder=(
            "Escribe aquí las reglas "
            "de la partida..."
        ),
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    personaje = discord.ui.TextInput(
        label="Tu personaje",
        placeholder=(
            "Escribe el personaje "
            "que utilizarás"
        ),
        required=True,
        max_length=100
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        timestamp = None

        fecha_hora_input = self.fecha_hora.value.strip()

        if fecha_hora_input:

            if fecha_hora_input.startswith("<t:"):

                try:

                    contenido = fecha_hora_input[3:]

                    timestamp_str = contenido.split(":")[0]

                    timestamp = int(timestamp_str)

                except (ValueError, IndexError):

                    await interaction.response.send_message(
                        "El timestamp de Discord no es válido.\n\n"
                        "Ejemplo válido:\n"
                        "`<t:1790899020:d>`",
                        ephemeral=True
                    )

                    return

            else:

                try:

                    fecha = datetime.strptime(
                        fecha_hora_input,
                        "%d/%m/%Y %H:%M"
                    )

                    fecha = fecha.replace(
                        tzinfo=UNIVERSAL_TZ
                    )

                    timestamp = int(
                        fecha.timestamp()
                    )

                except ValueError:

                    await interaction.response.send_message(
                        "La fecha y hora no tienen "
                        "un formato válido.\n\n"
                        "Puedes utilizar cualquiera "
                        "de estos formatos:\n\n"
                        "`DD/MM/YYYY HH:MM`\n"
                        "Ejemplo: `05/10/2026 21:30`\n\n"
                        "O un timestamp de Discord:\n"
                        "`<t:1790899020:d>`",
                        ephemeral=True
                    )

                    return

        canal2_id = config["SETUP"]["canal2"]

        canal2 = interaction.guild.get_channel(
            canal2_id
        )

        if canal2 is None:

            await interaction.response.send_message(
                "No pude encontrar el canal "
                "de búsqueda de partidas.",
                ephemeral=True
            )

            return

        partida = {
            "guild_id": interaction.guild.id,

            "host_id": interaction.user.id,

            "host_name": interaction.user.display_name,

            "title": self.titulo.value.strip(),

            "timestamp": timestamp,

            "reglas": self.reglas.value.strip(),

            "jugadores": [
                {
                    "user_id": interaction.user.id,
                    "personaje": self.personaje.value.strip()
                }
            ],

            "extras": [],

            "message_id": None,

            "thread_id": None,

            "voice_id": None,

            "estado": "buscando"
        }

        embed = crear_embed_partida(
            partida
        )

        mensaje = await canal2.send(
            embed=embed,
            view=PartidaView()
        )

        partida["message_id"] = (
            mensaje.id
        )

        thread = await crear_thread(
            canal2,
            f"Partida - {interaction.user.display_name}"
        )

        partida["thread_id"] = (
            thread.id
        )

        # Añadir host
        await thread.add_user(
            interaction.user
        )

        partidas[str(mensaje.id)] = (
            partida
        )

        guardar_partidas()

        await interaction.response.send_message(
            "Tu partida fue creada correctamente.",
            ephemeral=True
        )



class ParticiparModal(
    discord.ui.Modal,
    title="Participar en la partida"
):

    personaje = discord.ui.TextInput(
        label="¿Cuál será tu personaje?",
        placeholder= "Escribe el personaje que utilizarás",
        required=True,
        max_length=100
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        message_id = str(
            interaction.message.id
        )

        partida = obtener_partida(
            message_id
        )

        if partida is None:

            await interaction.response.send_message(
                "Esta partida ya no está disponible.",
                ephemeral=True
            )

            return

        jugadores = partida[
            "jugadores"
        ]

        for jugador in jugadores:

            if (
                jugador["user_id"]
                == interaction.user.id
            ):

                await interaction.response.send_message(
                    "Ya estás participando "
                    "en esta partida.",
                    ephemeral=True
                )

                return

        if len(jugadores) >= JUGADORES_NECESARIOS:

            await interaction.response.send_message(
                "La partida ya está completa.",
                ephemeral=True
            )

            return

        jugadores.append(
            {
                "user_id": interaction.user.id,

                "personaje": (
                    self.personaje.value.strip()
                )
            }
        )

        guardar_partidas()

        embed = crear_embed_partida(
            partida
        )

        await interaction.message.edit(
            embed=embed,
            view=PartidaView()
        )
        #Comprobación de jugadores. Si hay 16, comienza.
        if len(jugadores) == JUGADORES_NECESARIOS:

            await finalizar_organizacion(
                interaction.guild,
                partida
            )

        else:

            await interaction.response.send_message(
                "Te has unido correctamente "
                "a la partida.",
                ephemeral=True
            )


async def finalizar_organizacion(
    guild,
    partida
):


    if partida["estado"] != "buscando":

        return

    partida["estado"] = "organizada"

    guardar_partidas()

    thread = guild.get_thread(
        partida["thread_id"]
    )

    if thread is None:

        try:

            thread = await guild.fetch_channel(
                partida["thread_id"]
            )

        except discord.HTTPException:

            thread = None

    # QUICK PLAY

    if partida["timestamp"] is None:

        await convertir_quick_play(
            guild,
            partida,
            thread
        )

    # PROGRAMADA

    else:

        if thread is not None:

            await thread.send(
                f"{generar_ping_jugadores(partida)}\n\n"
                "Se han encontrado a los 16 participantes. ¡La partida está completamente organizada!"
            )

        canal2 = guild.get_channel(
            config["SETUP"]["canal2"]
        )

        if canal2 is not None:

            try:

                mensaje = await canal2.fetch_message(
                    partida["message_id"]
                )

                await mensaje.edit(
                    embed=crear_embed_partida(
                        partida
                    ),
                    view=PartidaFinalizadaView()
                )

            except discord.HTTPException:

                pass

    guardar_partidas()


async def convertir_quick_play(
    guild,
    partida,
    thread_anterior
):

    canal2 = guild.get_channel(
        config["SETUP"]["canal2"]
    )

    canal3 = guild.get_channel(
        config["SETUP"]["canal3"]
    )

    if canal3 is None:

        return

    if canal2 is not None:

        try:

            mensaje_antiguo = await canal2.fetch_message(
                partida["message_id"]
            )

            await mensaje_antiguo.delete()

        except discord.HTTPException:

            pass

    if thread_anterior is not None:

        try:

            await thread_anterior.delete()

        except discord.HTTPException:

            pass

    canal_voz = await crear_canal_voz(
        guild,
        partida
    )

    if canal_voz is not None:

        partida["voice_id"] = (
            canal_voz.id
        )

    mensaje_nuevo = await canal3.send(
        embed=crear_embed_partida(
            partida
        ),
        view=PartidaFinalizadaView()
    )

    thread_nuevo = await crear_thread(
        canal3,
        f"Ingame - {partida['host_name']}"
    )

    partida["message_id"] = (
        mensaje_nuevo.id
    )

    partida["thread_id"] = (
        thread_nuevo.id
    )

    await actualizar_miembros_thread(
        thread_nuevo,
        partida
    )


    aviso = (
        f"{generar_ping_jugadores(partida)}\n\n"
        "¡La partida está completamente organizada!\n"
    )

    if canal_voz is not None:

        aviso += (
            f"También tienen disponible el canal "
            f"de voz {canal_voz.mention} para charlar."
        )

    else:

        aviso += (
            "No se pudo crear el canal de voz."
        )

    await thread_nuevo.send(
        aviso
    )

    partida["estado"] = "en_curso"

    guardar_partidas()


# BOTÓN CREAR PARTIDA

class SetupButton(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Crear partida",
        style=discord.ButtonStyle.primary,
        custom_id="setup_crear_partida"
    )
    async def crear_partida(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        rol = interaction.guild.get_role(
            HOST_ROLE_ID
        )

        if rol is None:

            await interaction.response.send_message(
                "No pude encontrar el rol requerido.",
                ephemeral=True
            )

            return

        if rol not in interaction.user.roles:

            await interaction.response.send_message(
                "Este comando solo está "
                f"disponible para el rol "
                f"{rol.mention}",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            CrearPartidaModal()
        )


class PartidaView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Participar",
        style=discord.ButtonStyle.success,
        custom_id="partida_participar"
    )
    async def participar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        partida = obtener_partida(
            interaction.message.id
        )

        if partida is None:

            await interaction.response.send_message(
                "Esta partida ya no está disponible.",
                ephemeral=True
            )

            return

        if len(partida["jugadores"]) >= JUGADORES_NECESARIOS:

            await interaction.response.send_message(
                "La partida ya está completa.",
                ephemeral=True
            )

            return

        for jugador in partida["jugadores"]:

            if (
                jugador["user_id"]
                == interaction.user.id
            ):

                await interaction.response.send_message(
                    "Ya estás participando "
                    "en esta partida.",
                    ephemeral=True
                )

                return

        await interaction.response.send_modal(
            ParticiparModal()
        )

    @discord.ui.button(
        label="Entrar como extra",
        style=discord.ButtonStyle.secondary,
        custom_id="partida_extra"
    )
    async def entrar_como_extra(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        partida = obtener_partida(
            interaction.message.id
        )

        if partida is None:

            await interaction.response.send_message(
                "Esta partida ya no está disponible.",
                ephemeral=True
            )

            return


        for jugador in partida["jugadores"]:

            if (
                jugador["user_id"]
                == interaction.user.id
            ):

                await interaction.response.send_message(
                    "Ya formas parte de los jugadores "
                    "de esta partida.",
                    ephemeral=True
                )

                return


        for extra in partida["extras"]:

            if (
                extra["user_id"]
                == interaction.user.id
            ):

                await interaction.response.send_message(
                    "Ya estás registrado como extra "
                    "en esta partida.",
                    ephemeral=True
                )

                return

        partida["extras"].append(
            {
                "user_id": interaction.user.id
            }
        )

        guardar_partidas()


        embed = crear_embed_partida(
            partida
        )

        await interaction.message.edit(
            embed=embed,
            view=PartidaView()
        )

        await interaction.response.send_message(
            "Te has registrado como extra "
            "para esta partida.",
            ephemeral=True
        )

    @discord.ui.button(
    label="Cancelar participación",
    style=discord.ButtonStyle.danger,
    custom_id="partida_cancelar"
    )
    async def cancelar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        partida = obtener_partida(
            interaction.message.id
        )

        if partida is None:

            await interaction.response.send_message(
                "Esta partida ya no está disponible.",
                ephemeral=True
            )

            return


        jugador_encontrado = None

        for jugador in partida["jugadores"]:

            if (
                jugador["user_id"]
                == interaction.user.id
            ):

                jugador_encontrado = jugador
                break

        if jugador_encontrado is not None:

            if (
                interaction.user.id
                == partida["host_id"]
            ):

                await interaction.response.send_message(
                    "El anfitrión no puede cancelar "
                    "su propia participación.",
                    ephemeral=True
                )

                return

            partida["jugadores"].remove(
                jugador_encontrado
            )

            guardar_partidas()

            embed = crear_embed_partida(
                partida
            )

            await interaction.message.edit(
                embed=embed,
                view=PartidaView()
            )

            await interaction.response.send_message(
                "Has cancelado tu participación "
                "en la partida.",
                ephemeral=True
            )

            return


        extra_encontrado = None

        for extra in partida["extras"]:

            if (
                extra["user_id"]
                == interaction.user.id
            ):

                extra_encontrado = extra
                break

        if extra_encontrado is not None:

            partida["extras"].remove(
                extra_encontrado
            )

            guardar_partidas()

            embed = crear_embed_partida(
                partida
            )

            await interaction.message.edit(
                embed=embed,
                view=PartidaView()
            )

            await interaction.response.send_message(
                "Has dejado de estar registrado "
                "como extra.",
                ephemeral=True
            )

            return


        await interaction.response.send_message(
            "No estás participando ni estás "
            "registrado como extra en esta partida.",
            ephemeral=True
        )


class PartidaFinalizadaView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Partida finalizada",
        style=discord.ButtonStyle.primary,
        custom_id="partida_finalizada"
    )
    async def finalizar(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        partida = obtener_partida(
            interaction.message.id
        )

        if partida is None:

            await interaction.response.send_message(
                "No pude encontrar esta partida.",
                ephemeral=True
            )

            return

        if (
            interaction.user.id != partida["host_id"]
            and not Es_Admin(interaction.user)
        ):
            await interaction.response.send_message(
                "Solo el anfitrión de la partida "
                "o un admin pueden finalizar la partida.",
                ephemeral=True
            )

            return

        
        await interaction.response.send_message(
                    "Intentando finalizar tu partida...",
                    ephemeral=True
                )

        
        canal4 = interaction.guild.get_channel(
            config["SETUP"]["canal4"]
        )

        if canal4 is None:

            await interaction.response.send_message(
                "No pude encontrar el canal "
                "de partidas finalizadas.",
                ephemeral=True
            )

            return

        await canal4.send(
            embed=crear_embed_partida(
                partida
            )
        )

        try:

            await interaction.message.delete()

        except discord.HTTPException:

            pass

        if partida.get("thread_id"):

            try:

                thread = await interaction.guild.fetch_channel(
                    partida["thread_id"]
                )

                await thread.delete()

            except discord.HTTPException:

                pass

        if partida.get("voice_id"):

            try:

                voice = interaction.guild.get_channel(
                    partida["voice_id"]
                )

                if voice is not None:

                    await voice.delete()

            except discord.HTTPException:

                pass

        partida["estado"] = "finalizada"

        guardar_partidas()



@client.tree.command(
    name="agregar",
    description="Agrega un usuario a la partida.(HOST)"
)
@app_commands.describe(
    usuario="Usuario que quieres agregar"
)
async def agregar(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    if not isinstance(
        interaction.channel,
        discord.VoiceChannel
    ):

        await interaction.response.send_message(
            "Este comando solamente puede "
            "utilizarse dentro del canal de voz "
            "correspondiente a la partida.",
            ephemeral=True
        )

        return

    partida = None

    for datos in partidas.values():

        if datos.get(
            "voice_id"
        ) == interaction.channel.id:

            partida = datos
            break

    if partida is None:

        await interaction.response.send_message(
            "Este canal de voz no está asociado "
            "a ninguna partida.",
            ephemeral=True
        )

        return

    if (
        interaction.user.id
        != partida["host_id"]
    ):

        await interaction.response.send_message(
            "Solo el anfitrión puede utilizar "
            "este comando.",
            ephemeral=True
        )

        return

    for jugador in partida["jugadores"]:

        if (
            jugador["user_id"]
            == usuario.id
        ):

            await interaction.response.send_message(
                "Ese usuario ya forma parte "
                "de la partida.",
                ephemeral=True
            )

            return

    partida["jugadores"].append(
        {
            "user_id": usuario.id,
            "personaje": "Invitado"
        }
    )

    guardar_partidas()

    await interaction.channel.set_permissions(
        usuario,
        connect=True,
        view_channel=True
    )

    if partida.get("thread_id"):

        try:

            thread = await interaction.guild.fetch_channel(
                partida["thread_id"]
            )

            await thread.add_user(
                usuario
            )

        except discord.HTTPException:

            pass

    await interaction.response.send_message(
        f"{usuario.mention} ha sido agregado "
        "a la partida."
    )


@client.tree.command(
    name="finalizar_partida",
    description="Finaliza y archiva una partida.(ADMIN)"
)
@app_commands.describe(
    message_id="ID del mensaje de la partida."
)
async def finalizar_partida(
    interaction: discord.Interaction,
    message_id: str
):


    if not Es_Admin(interaction.user):

        await interaction.response.send_message(
            "No tienes permisos para utilizar "
            "este comando.",
            ephemeral=True
        )

        return


    try:

        message_id_int = int(message_id)

    except ValueError:

        await interaction.response.send_message(
            "El Message ID proporcionado no es válido.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
                "Intentando finalizar la partida...",
                ephemeral=True
            )


    partida = obtener_partida(message_id)

    if partida is None:

        await interaction.response.send_message(
            "No encontré ninguna partida registrada "
            "con ese Message ID.",
            ephemeral=True
        )

        return

    await finalizar_partida_admin(
        interaction,
        partida
    )


@client.tree.command(
    name="eliminar",
    description="Expulsa un usuario de la partida.(HOST)"
)
@app_commands.describe(
    usuario="Usuario que quieres expulsar"
)
async def eliminar(
    interaction: discord.Interaction,
    usuario: discord.Member
):

    if not isinstance(
        interaction.channel,
        discord.VoiceChannel
    ):

        await interaction.response.send_message(
            "Este comando solamente puede "
            "utilizarse dentro del canal de voz "
            "correspondiente a la partida.",
            ephemeral=True
        )

        return

    partida = None

    for datos in partidas.values():

        if datos.get(
            "voice_id"
        ) == interaction.channel.id:

            partida = datos
            break

    if partida is None:

        await interaction.response.send_message(
            "Este canal de voz no está asociado "
            "a ninguna partida.",
            ephemeral=True
        )

        return

    if (
        interaction.user.id
        != partida["host_id"]
    ):

        await interaction.response.send_message(
            "Solo el anfitrión puede utilizar "
            "este comando.",
            ephemeral=True
        )

        return

    if usuario.id == partida["host_id"]:

        await interaction.response.send_message(
            "El anfitrión no puede ser eliminado "
            "de su propia partida.",
            ephemeral=True
        )

        return

    jugador_encontrado = None

    for jugador in partida["jugadores"]:

        if (
            jugador["user_id"]
            == usuario.id
        ):

            jugador_encontrado = jugador
            break

    if jugador_encontrado is None:

        await interaction.response.send_message(
            "Ese usuario no forma parte "
            "de la partida.",
            ephemeral=True
        )

        return

    partida["jugadores"].remove(
        jugador_encontrado
    )

    guardar_partidas()

    await interaction.channel.set_permissions(
        usuario,
        overwrite=None
    )

    if partida.get("thread_id"):

        try:

            thread = await interaction.guild.fetch_channel(
                partida["thread_id"]
            )

            await thread.remove_user(
                usuario
            )

        except discord.HTTPException:

            pass

    await interaction.response.send_message(
        f"{usuario.mention} ha sido eliminado "
        "de la partida."
    )



@client.tree.command(
    name="setup",
    description="Configura los canales del sistema.(ADMIN)"
)
@app_commands.describe(
    canal1="ID del canal principal",
    canal2="ID del canal de búsqueda de partidas",
    canal3="ID del canal de partidas en curso",
    canal4="ID del canal de partidas finalizadas"
)
async def setup(
    interaction: discord.Interaction,
    canal1: str,
    canal2: str,
    canal3: str,
    canal4: str
):

    if not Es_Admin(interaction.user):

            await interaction.response.send_message(
                "No tienes permisos para utilizar "
                "este comando.",
                ephemeral=True
            )

            return

    try:

        canal1_id = int(canal1)
        canal2_id = int(canal2)
        canal3_id = int(canal3)
        canal4_id = int(canal4)

    except ValueError:

        await interaction.response.send_message(
            "Uno de los IDs de canal no es válido.",
            ephemeral=True
        )

        return

    canal1_obj = interaction.guild.get_channel(
        canal1_id
    )

    if canal1_obj is None:

        await interaction.response.send_message(
            "No pude encontrar el canal 1.",
            ephemeral=True
        )

        return

    config["SETUP"] = {

        "canal1": canal1_id,

        "canal2": canal2_id,

        "canal3": canal3_id,

        "canal4": canal4_id
    }

    with open(
        "config.json",
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            config,
            archivo,
            indent=4,
            ensure_ascii=False
        )

    embed = discord.Embed(
        title="¿Quieres organizar una partida?",
        description=(
            "¡Presiona el botón para "
            "convertirte en un anfitrión!"
        ),
        color=discord.Color.blue()
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1554199273527050270/1554214219996733540/k4rxmhw.jpg?ex=6abc1249&is=6abac0c9&hm=dc7d6b4181b7392d79f40be0a457d6de2df8d31d318cbb454fadc6100952e144&=&format=webp")

    await canal1_obj.send(
        embed=embed,
        view=SetupButton()
    )

    await interaction.response.send_message(
        "El sistema fue configurado correctamente.",
        ephemeral=True
    )


@client.tree.command(
    name="bump",
    description="Notifica a los jugadores de una partida en búsqueda."
)
async def bump(
    interaction: discord.Interaction
):

    if interaction.guild is None:

        await interaction.response.send_message(
            "Este comando solo puede utilizarse "
            "dentro de un servidor.",
            ephemeral=True
        )

        return

    partida_activa = any(
        partida.get("guild_id") == interaction.guild_id
        and partida.get("host_id") == interaction.user.id
        and partida.get("estado") == "buscando"
        for partida in partidas.values()
    )
#TODO: CUANDO EL BOT SEA LA ÚNICA VIA PARA BUSCAR PARTIDAS, REACTIVAR ESTA OPCIÓN.
#    if not partida_activa:
#
#        await interaction.response.send_message(
#            "Solo el anfitrión de una partida que está "
#            "buscando jugadores puede utilizar este comando.",
#            ephemeral=True
#        )
#
#        return

    ahora = time.monotonic()
    ultimo_bump = bump_cooldowns.get(interaction.user.id)

    if ultimo_bump is not None:

        restante = BUMP_COOLDOWN_SECONDS - (
            ahora - ultimo_bump
        )

        if restante > 0:

            segundos = int(restante) + 1
            minutos, segundos = divmod(segundos, 60)

            await interaction.response.send_message(
                "Debes esperar "
                f"**{minutos} min {segundos} s** "
                "antes de volver a usar `/bump`.",
                ephemeral=True
            )

            return

    await interaction.response.defer(
        ephemeral=True
    )

    canal = interaction.guild.get_channel(
        BUMP_CHANNEL_ID
    )

    if canal is None:

        try:

            canal = await interaction.guild.fetch_channel(
                BUMP_CHANNEL_ID
            )

        except discord.HTTPException:

            await interaction.followup.send(
                "No pude encontrar el canal donde se envían "
                "las notificaciones.",
                ephemeral=True
            )

            return

    if not isinstance(
        canal,
        (discord.TextChannel, discord.Thread)
    ):

        await interaction.followup.send(
            "El canal configurado para las notificaciones "
            "no es un canal de texto válido.",
            ephemeral=True
        )

        return

    bump_cooldowns[interaction.user.id] = ahora

    try:

        await canal.send(
            f"El usuario <@{interaction.user.id}> ha usado /bump para avisar que <@&{BUMP_ROLE_ID}>. ¡Échale un vistazo a su partida en <#1527880398837780610> / <#1555600674253701262>!",
            allowed_mentions=discord.AllowedMentions(
                roles=[discord.Object(id=BUMP_ROLE_ID)],
                users=False,
                everyone=False
            )
        )

    except discord.HTTPException:

        if bump_cooldowns.get(interaction.user.id) == ahora:
            del bump_cooldowns[interaction.user.id]

        await interaction.followup.send(
            "No pude enviar la notificación. "
            "Comprueba que tengo permisos en ese canal.",
            ephemeral=True
        )

        return

    await interaction.followup.send(
        "Notificación enviada correctamente.",
        ephemeral=True
    )









@client.event
async def on_ready():

    print(
        f"Conectado como {client.user}"
    )

    client.add_view(
        SetupButton()
    )

    client.add_view(
        PartidaView()
    )

    client.add_view(
        PartidaFinalizadaView()
    )

    try:

        synced = await client.tree.sync()

        print(
            f"Comandos sincronizados: "
            f"{len(synced)}"
        )

    except Exception as error:

        print(
            f"Error sincronizando comandos: "
            f"{error}"
        )




client.run(TOKEN)