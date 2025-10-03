import discord
from discord.ext import commands
import asyncio


r"""
Liste de channels ignorés pour ne pas surcharger le bot.

Exemple : Général, commandes...
Veuillez copier-coller les channels importants.

/!\ Éviter les salons contenant trop de messages.
"""
IGNORED_CHANNEL_IDS = [
    0000000000000000000,
    1111111111111111111,
    2222222222222222222
]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

SOURCE_GUILD_ID = 0000000000000000000  # Serveur source
TARGET_GUILD_ID = 1111111111111111111  # Serveur cible
OWNER_ID = 00000000000000000  # Remplace par ton ID Discord

# Connexion du bot
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    # Synchronisation des commandes slash
    await bot.tree.sync()


# 
@bot.tree.command(name="clone", description="Clone les messages des salons et forums du serveur source vers le serveur cible")
async def clone(interaction: discord.Interaction):
    # Vérification propriétaire
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)
        return

    await interaction.response.send_message("🔄 Démarrage du clonage...", ephemeral=True)

    source_guild = bot.get_guild(SOURCE_GUILD_ID)
    target_guild = bot.get_guild(TARGET_GUILD_ID)

    if not source_guild or not target_guild:
        await interaction.followup.send("❌ Serveurs introuvables. Vérifie les IDs.", ephemeral=True)
        return

    # --- Cloner les salons textuels ---
    for source_channel in source_guild.text_channels:
        if source_channel.id in IGNORED_CHANNEL_IDS:
            print(f"Salon textuel {source_channel.name} ignoré.")
            continue

        target_channel = discord.utils.get(target_guild.text_channels, name=source_channel.name)
        if not target_channel:
            await interaction.followup.send(f"⛔ Pas de salon textuel nommé '{source_channel.name}' sur le serveur cible.", ephemeral=True)
            continue

        try:
            # Réutiliser un webhook existant si possible
            existing_webhooks = await target_channel.webhooks()
            webhook = discord.utils.get(existing_webhooks, name="CloneBot")

            if webhook is None:
                webhook = await target_channel.create_webhook(name="CloneBot")
                await asyncio.sleep(3)  # pause pour éviter le rate limit

            async for message in source_channel.history(limit=None, oldest_first=True):
                if not message.content:
                    continue
                await webhook.send(
                    content=message.content,
                    username=message.author.display_name,
                    avatar_url=message.author.display_avatar.url if message.author.display_avatar else None
                )
                await asyncio.sleep(5)  # délai important pour éviter rate limit

            await interaction.followup.send(f"✅ Messages copiés dans #{source_channel.name}", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Erreur pour #{source_channel.name} : {e}", ephemeral=True)

    # --- Cloner les forums ---
    for source_channel in source_guild.channels:
        if isinstance(source_channel, discord.ForumChannel):
            target_channel = discord.utils.get(
                target_guild.channels,
                name=source_channel.name,
                type=discord.ChannelType.forum
            )
            if not target_channel:
                await interaction.followup.send(f"⛔ Forum '{source_channel.name}' non trouvé dans le serveur cible.", ephemeral=True)
                continue

            # Récupérer ou créer un seul webhook à réutiliser pour ce forum
            existing_webhooks = await target_channel.webhooks()
            webhook = discord.utils.get(existing_webhooks, name="CloneBot")
            if webhook is None:
                webhook = await target_channel.create_webhook(name="CloneBot")
                await asyncio.sleep(3)

            threads = source_channel.threads
            for thread in threads:
                try:
                    messages = [m async for m in thread.history(limit=None, oldest_first=True)]
                    if not messages:
                        await interaction.followup.send(f"⚠️ Thread vide: {thread.name}", ephemeral=True)
                        continue

                    # Créer le thread sur le forum cible
                    first_msg = messages[0]
                    content = f"{first_msg.content}" if first_msg.content else "*Message vide*"

                    new_thread = await target_channel.create_thread(name=thread.name, content=content)
                    await asyncio.sleep(3)

                    # Envoyer les messages suivants via le webhook dans le thread
                    for msg in messages[1:]:
                        if not msg.content:
                            continue
                        try:
                            await webhook.send(
                                content=msg.content,
                                username=msg.author.display_name,
                                avatar_url=msg.author.display_avatar.url if msg.author.display_avatar else None,
                                thread=new_thread  # envoyer dans le thread
                            )
                            await asyncio.sleep(3)
                        except Exception as e:
                            print(f"Erreur en envoyant un message dans le thread '{new_thread.name}': {e}")

                    await interaction.followup.send(f"✅ Thread '{thread.name}' cloné avec succès.", ephemeral=True)

                except Exception as e:
                    await interaction.followup.send(f"❌ Erreur sur le thread '{thread.name}': {e}", ephemeral=True)

    await interaction.followup.send("🎉 Clonage terminé !", ephemeral=True)

bot.run('TOKEN_BOT')
