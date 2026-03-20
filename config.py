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

# Plex path translation (for Docker setups where Plex sees different paths)
# PLEX_PATH_PREFIX  = the path prefix as Plex sees it inside its container
# PLEX_PATH_REPLACE = what to replace it with on the host
# e.g. PLEX_PATH_PREFIX=/data  PLEX_PATH_REPLACE=/mnt/user/Media
#   Plex returns:  /data/Movies/Foo/foo.mkv
#   Translated to: /mnt/user/Media/Movies/Foo/foo.mkv
PLEX_PATH_PREFIX = os.getenv("PLEX_PATH_PREFIX", "")
PLEX_PATH_REPLACE = os.getenv("PLEX_PATH_REPLACE", "")
