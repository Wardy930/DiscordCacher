import glob
import logging
import os
import shutil
import subprocess

from plexapi.server import PlexServer

import config

log = logging.getLogger(__name__)


def search_movies(query: str) -> list[dict]:
    """Search Plex library for movies matching the query."""
    plex = PlexServer(config.PLEX_URL, config.PLEX_TOKEN)
    section = plex.library.section(config.PLEX_LIBRARY_NAME)
    results = section.search(query)

    movies = []
    for movie in results:
        if movie.TYPE != "movie":
            continue
        locations = movie.locations
        if not locations:
            continue
        movies.append({
            "title": movie.title,
            "year": movie.year,
            "file_path": locations[0],
        })
    return movies


def _relative_path(user_share_path: str) -> str | None:
    """Extract the relative path after the user share base.

    e.g. /mnt/user/Media/Movies/Predator (1987)/file.mkv
      -> Media/Movies/Predator (1987)/file.mkv
    """
    prefix = config.USER_SHARE_BASE.rstrip("/") + "/"
    if user_share_path.startswith(prefix):
        return user_share_path[len(prefix):]
    return None


def get_cache_status(user_share_path: str) -> dict:
    """Check whether a file is on cache, on an array disk, or not found.

    Returns:
        {"status": "already_cached"} or
        {"status": "on_array", "array_path": str, "cache_path": str} or
        {"status": "not_found"}
    """
    rel = _relative_path(user_share_path)
    if rel is None:
        return {"status": "not_found"}

    cache_path = os.path.join(config.CACHE_BASE, rel)
    if os.path.exists(cache_path):
        return {"status": "already_cached"}

    # Search array disks: /mnt/disk1, /mnt/disk2, etc.
    pattern = os.path.join("/mnt/disk*", rel)
    matches = glob.glob(pattern)
    if matches:
        return {
            "status": "on_array",
            "array_path": matches[0],
            "cache_path": cache_path,
        }

    return {"status": "not_found"}


def file_size_str(path: str) -> str:
    """Human-readable file size."""
    size = os.path.getsize(path)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def _is_file_in_use(path: str) -> bool:
    """Check if a file is currently being accessed."""
    try:
        result = subprocess.run(
            ["fuser", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def move_to_cache(array_path: str, cache_path: str) -> None:
    """Safely move a file from an array disk to the cache drive.

    Uses copy + verify + delete rather than shutil.move, since
    array and cache are separate filesystems.

    Raises:
        RuntimeError: if the file is in use, copy fails, or size mismatch.
    """
    if _is_file_in_use(array_path):
        raise RuntimeError(
            "File is currently being accessed. Try again later."
        )

    src_size = os.path.getsize(array_path)

    # Create destination directory
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)

    try:
        shutil.copy2(array_path, cache_path)
    except OSError as e:
        # Clean up partial copy
        if os.path.exists(cache_path):
            os.remove(cache_path)
        raise RuntimeError(f"Copy failed: {e}") from e

    # Verify sizes match
    dst_size = os.path.getsize(cache_path)
    if src_size != dst_size:
        os.remove(cache_path)
        raise RuntimeError(
            f"Size mismatch after copy: source={src_size}, dest={dst_size}"
        )

    # Safe to remove source
    os.remove(array_path)

    # Clean up empty parent directories on the array disk
    parent = os.path.dirname(array_path)
    try:
        os.removedirs(parent)
    except OSError:
        pass  # Directory not empty or other issue, that's fine

    log.info("Moved %s -> %s (%s)", array_path, cache_path, file_size_str(cache_path))
