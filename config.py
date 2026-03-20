import os

from dotenv import load_dotenv

load_dotenv()

# Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", "0"))

# Plex
PLEX_URL = os.getenv("PLEX_URL", "http://localhost:32400")
PLEX_TOKEN = os.getenv("PLEX_TOKEN", "")
PLEX_LIBRARY_NAME = os.getenv("PLEX_LIBRARY_NAME", "Films")

# Unraid paths
USER_SHARE_BASE = os.getenv("USER_SHARE_BASE", "/mnt/user")
CACHE_BASE = os.getenv("CACHE_BASE", "/mnt/cache")
