import discord
from discord.ext import commands
from discord import app_commands

import json
import os

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

    return partidas.get(
        str(message_id)
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

    for i in range(16):

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

    cantidad = len(
        partida["jugadores"]
    )

    descripcion = (
        f"{cantidad}/16 "
        f":busts_in_silhouette:\n"
        f"{generar_cuadro_jugadores(partida)}\n\n"
        f"{generar_lista_jugadores(partida)}"
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

    if es_quick_play:
        embed.set_footer(
            text=(
                "La batalla entre desesperación y "
                "esperanza comenzará en breve..."
            )
        )

    return embed


async def crear_thread_privado(
    canal,
    nombre
):

    thread = await canal.create_thread(
        name=nombre,
        type=discord.ChannelType.private_thread,
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

    fecha_hora = discord.ui.TextInput(
        label="Fecha y hora (Vacío = partida Quick Play)",
        placeholder=(
            "DD/MM/YYYY HH:MM (Hora UTC) "
            "— vacío = Quick Play"
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

        if self.fecha_hora.value.strip():

            try:

                fecha = datetime.strptime(
                    self.fecha_hora.value.strip(),
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
                    "Utiliza:\n"
                    "`DD/MM/YYYY HH:MM`\n\n"
                    "Ejemplo:\n"
                    "`05/10/2026 21:30`",
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

            "host_name": (
                interaction.user.display_name
            ),

            "timestamp": timestamp,

            "reglas": (
                self.reglas.value.strip()
            ),

            "jugadores": [

                {
                    "user_id": interaction.user.id,

                    "personaje": (
                        self.personaje.value.strip()
                    )
                }
            ],

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

        thread = await crear_thread_privado(
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

        if len(jugadores) >= 16:

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
        if len(jugadores) == 16:

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

            await thread_anterior.edit(
                archived=True,
                locked=True
            )

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

    thread_nuevo = await crear_thread_privado(
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

        if len(partida["jugadores"]) >= 16:

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

        if jugador_encontrado is None:

            await interaction.response.send_message(
                "No estás participando "
                "en esta partida.",
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
            interaction.user.id
            != partida["host_id"]
        ):

            await interaction.response.send_message(
                "Solo el anfitrión de la partida "
                "puede finalizarla.",
                ephemeral=True
            )

            return

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

                await thread.edit(
                    archived=True,
                    locked=True
                )

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

        await interaction.response.send_message(
            "La partida fue archivada correctamente.",
            ephemeral=True
        )



@client.tree.command(
    name="agregar",
    description="Agrega un usuario a la partida."
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
    name="eliminar",
    description="Expulsa un usuario de la partida."
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
    description="Configura los canales del sistema."
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