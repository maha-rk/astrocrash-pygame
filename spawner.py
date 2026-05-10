"""
spawner.py
Generates the asteroid wave for each level.

All difficulty parameters (rock count, speed, split depth, special types)
come from the LEVEL_DEFS table in constants.py — this module just reads
that table and creates the correct Asteroid objects.
"""

import random
import math

from constants import (
    WIDTH, HEIGHT,
    ASTEROID_LARGE_SIZE,
    get_level_def, level_palette,
)
from entities import Asteroid

# Minimum distance from screen centre when placing a new asteroid.
# Prevents asteroids from spawning on top of the ship.
_SAFE_RADIUS = 160

# Weighted type distribution for special asteroid waves (level 4+)
_TYPES   = ("normal", "fast", "heavy", "zigzag")
_WEIGHTS = (60, 18, 12, 10)   # normal is most common; zigzag is rarest

# Generates a new wave of asteroids based on level definitions
# Ensures asteroids spawn outside a safe radius from the player
def spawn_wave(level: int) -> list:
    """Create and return the opening asteroid wave for the given level.

    Reads the level definition to determine:
      - How many large asteroids to place
      - Their speed multiplier
      - Their split depth (0 = no split, 1 = → medium, 2 = full chain)
      - Whether to use special types (fast / heavy / zigzag)
      - Which colour palette to use
    """
    ldef        = get_level_def(level)
    pal         = level_palette(level)
    use_special = ldef.get("special", False)

    asteroids = []
    for _ in range(ldef["spawn"]):
        # Pick a type: special types only available from level 4 onwards
        kind = (random.choices(_TYPES, weights=_WEIGHTS, k=1)[0]
                if use_special else "normal")

        # Speed has a ±20% random variation so asteroids don't all move identically
        speed = ldef["speed"] * random.uniform(0.8, 1.2)

        asteroids.append(
            Asteroid(*_safe_position(), ASTEROID_LARGE_SIZE,
                     random.uniform(0, 360), speed,
                     pal, ldef["depth"], kind)
        )
    return asteroids


def _safe_position() -> tuple:
    """Return a random (x, y) that is at least _SAFE_RADIUS pixels
    from the screen centre, so asteroids never spawn on the ship."""
    cx, cy = WIDTH // 2, HEIGHT // 2
    while True:
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        if math.hypot(x - cx, y - cy) >= _SAFE_RADIUS:
            return x, y