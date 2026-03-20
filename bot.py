import asyncio
import logging
import os
import time

import discord
from discord import app_commands

import cacher
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("cacher").setLevel(logging.DEBUG)
log = logging.getLogger(__name__)

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Per-user pending search results: {user_id: [movie_dict, ...]}
pending: dict[int, list[dict]] = {}
# Per-user selected movie: {user_id: movie_dict}
selected: dict[int, dict] = {}


def channel_check(interaction: discord.Interaction) -> bool:
    """Return True if the command is in the allowed channel (or no restriction)."""
    if config.ALLOWED_CHANNEL_ID == 0:
        return True
    return interaction.channel_id == config.ALLOWED_CHANNEL_ID


@tree.command(name="cache", description="Search for a movie to pre-cache")
@app_commands.describe(movie_name="Movie title to search for")
async def cache_command(interaction: discord.Interaction, movie_name: str):
    if not channel_check(interaction):
        await interaction.response.send_message(
            "This command can only be used in the designated channel.",
            ephemeral=True,
        )
        return

    await interaction.response.defer()

    try:
        results = await asyncio.get_event_loop().run_in_executor(
            None, cacher.search_movies, movie_name
        )
    except Exception as e:
        await interaction.followup.send(f"Error searching Plex: {e}")
        return

    user_id = interaction.user.id

    if not results:
        pending.pop(user_id, None)
        selected.pop(user_id, None)
        await interaction.followup.send(
            f"No movies found matching **{movie_name}**."
        )
        return

    if len(results) == 1:
        movie = results[0]
        selected[user_id] = movie
        pending.pop(user_id, None)
        filename = os.path.basename(movie["file_path"])
        await interaction.followup.send(
            f"Found: **{movie['title']} ({movie['year']})**\n"
            f"File: `{filename}`\n\n"
            f"Use `/confirm` to move to cache, or `/cancel`."
        )
        return

    # Multiple results
    pending[user_id] = results
    selected.pop(user_id, None)
    lines = [f"Found **{len(results)}** results:\n"]
    for i, movie in enumerate(results[:15], 1):
        lines.append(f"**{i}.** {movie['title']} ({movie['year']})")
    lines.append("\nUse `/pick <number>` to select.")
    await interaction.followup.send("\n".join(lines))


@tree.command(name="pick", description="Pick a movie from the search results")
@app_commands.describe(number="The number of the movie to select")
async def pick_command(interaction: discord.Interaction, number: int):
    if not channel_check(interaction):
        await interaction.response.send_message(
            "This command can only be used in the designated channel.",
            ephemeral=True,
        )
        return

    user_id = interaction.user.id
    results = pending.get(user_id)

    if not results:
        await interaction.response.send_message(
            "No pending search results. Use `/cache <movie name>` first.",
            ephemeral=True,
        )
        return

    if number < 1 or number > len(results):
        await interaction.response.send_message(
            f"Invalid selection. Pick a number between 1 and {len(results)}.",
            ephemeral=True,
        )
        return

    movie = results[number - 1]
    selected[user_id] = movie
    pending.pop(user_id, None)

    filename = os.path.basename(movie["file_path"])

    # Try to get file size
    try:
        size = await asyncio.get_event_loop().run_in_executor(
            None, cacher.file_size_str, movie["file_path"]
        )
        size_info = f" ({size})"
    except OSError:
        size_info = ""

    await interaction.response.send_message(
        f"Selected: **{movie['title']} ({movie['year']})**\n"
        f"File: `{filename}`{size_info}\n\n"
        f"Use `/confirm` to move to cache, or `/cancel`."
    )


@tree.command(name="confirm", description="Confirm and move the selected movie to cache")
async def confirm_command(interaction: discord.Interaction):
    if not channel_check(interaction):
        await interaction.response.send_message(
            "This command can only be used in the designated channel.",
            ephemeral=True,
        )
        return

    user_id = interaction.user.id
    movie = selected.get(user_id)

    if not movie:
        await interaction.response.send_message(
            "Nothing selected. Use `/cache <movie name>` to search first.",
            ephemeral=True,
        )
        return

    await interaction.response.defer()

    try:
        status = await asyncio.get_event_loop().run_in_executor(
            None, cacher.get_cache_status, movie["file_path"]
        )
    except Exception as e:
        await interaction.followup.send(f"Error checking cache status: {e}")
        return

    if status["status"] == "already_cached":
        selected.pop(user_id, None)
        await interaction.followup.send(
            f"**{movie['title']} ({movie['year']})** is already on the cache drive!"
        )
        return

    if status["status"] == "not_found":
        selected.pop(user_id, None)
        await interaction.followup.send(
            f"Could not locate the file on any array disk. "
            f"It may have been moved or deleted.\n"
            f"Debug — path from Plex: `{movie['file_path']}`"
        )
        return

    # File is on array, move it
    array_path = status["array_path"]
    cache_path = status["cache_path"]

    try:
        size = await asyncio.get_event_loop().run_in_executor(
            None, cacher.file_size_str, array_path
        )
    except OSError:
        size = "unknown size"

    await interaction.followup.send(
        f"Moving **{movie['title']} ({movie['year']})** to cache drive... ({size})"
    )

    start = time.monotonic()
    try:
        await asyncio.get_event_loop().run_in_executor(
            None, cacher.move_to_cache, array_path, cache_path
        )
    except RuntimeError as e:
        await interaction.channel.send(f"Move failed: {e}")
        return
    except Exception as e:
        await interaction.channel.send(f"Unexpected error during move: {e}")
        return

    elapsed = time.monotonic() - start
    minutes, seconds = divmod(int(elapsed), 60)
    if minutes > 0:
        time_str = f"{minutes}m {seconds}s"
    else:
        time_str = f"{seconds}s"

    selected.pop(user_id, None)
    await interaction.channel.send(
        f"Done! **{movie['title']} ({movie['year']})** is now on the cache drive. "
        f"Took {time_str}."
    )


@tree.command(name="cancel", description="Cancel the current selection")
async def cancel_command(interaction: discord.Interaction):
    user_id = interaction.user.id
    pending.pop(user_id, None)
    selected.pop(user_id, None)
    await interaction.response.send_message("Cancelled.")


@client.event
async def on_ready():
    await tree.sync()
    log.info("Logged in as %s (ID: %s)", client.user, client.user.id)
    log.info("Slash commands synced.")


if __name__ == "__main__":
    if not config.DISCORD_TOKEN:
        raise SystemExit("DISCORD_TOKEN is not set. Check your .env file.")
    if not config.PLEX_TOKEN:
        raise SystemExit("PLEX_TOKEN is not set. Check your .env file.")
    client.run(config.DISCORD_TOKEN)
