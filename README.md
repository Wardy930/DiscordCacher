# DiscordCacher

A Discord bot that pre-caches Plex movies onto your Unraid cache drive before watching.

## How it works

1. Use `/cache <movie name>` to search your Plex library
2. Pick from results if there are multiple matches
3. Confirm to move the file from the array to the cache drive
4. Unraid's mover will eventually move it back to the array automatically

## Setup

### 1. Create a Discord bot

1. Go to https://discord.com/developers/applications and create a new application
2. Under **Bot**, copy the token
3. Under **OAuth2 > URL Generator**, select `bot` and `applications.commands` scopes
4. Invite the bot to your server with the generated URL

### 2. Get your Plex token

Find your Plex token: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/

### 3. Configure

Copy `.env.example` to `.env` and fill in your values:

```
DISCORD_TOKEN=your_discord_bot_token
PLEX_URL=http://localhost:32400
PLEX_TOKEN=your_plex_token
PLEX_LIBRARY_NAME=Movies
ALLOWED_CHANNEL_ID=your_channel_id
```

Set `ALLOWED_CHANNEL_ID` to the Discord channel ID where the bot should respond (right-click channel > Copy ID with developer mode enabled). Set to `0` to allow all channels.

### 4. Run with Docker

```bash
docker compose up -d
```

The container mounts `/mnt` for access to array disks and cache drive. Uses host networking for Plex localhost access.

## Commands

| Command | Description |
|---------|-------------|
| `/cache <name>` | Search for a movie |
| `/pick <number>` | Select from search results |
| `/confirm` | Move the selected movie to cache |
| `/cancel` | Cancel current selection |
