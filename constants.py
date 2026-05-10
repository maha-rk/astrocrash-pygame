"""
constants.py
All global configuration values for AstroCrash.

Keeping every magic number here means a single edit propagates
everywhere — no need to hunt through multiple files to tune gameplay.
"""

# ── Screen ────────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1200, 800   # window dimensions in pixels
FPS           = 60           # target frame rate
TITLE         = "AstroCrash" # window title bar text

# ── Ship ──────────────────────────────────────────────────────────────────────
SHIP_RADIUS = 15   # collision circle radius (pixels)
SHIP_SIZE   = 30   # scaling factor for the rocket polygon
SHIP_SPEED  = 7    # pixels the ship moves toward the cursor each frame

# Dead zone: ship stops when cursor is closer than this, preventing jitter
MOVE_THRESHOLD = 2   # minimum distance before ship chases cursor
STOP_RADIUS    = 40  # ship stops completely inside this radius (px)

# Aim is frozen inside this radius to prevent atan2 instability (spinning-star bug)
AIM_FREEZE_RADIUS = 30  # angle update threshold (px)

# ── Bullets ───────────────────────────────────────────────────────────────────
BULLET_RADIUS   = 5   # collision / rendering radius
BULLET_SPEED    = 14  # pixels per frame
BULLET_MAX      = 5   # maximum bullets on screen simultaneously
BULLET_COOLDOWN = 9   # frames between shots (~150 ms at 60 FPS)

# ── Asteroid sizes ────────────────────────────────────────────────────────────
# These are both the collision radii and the rendering scale.
ASTEROID_LARGE_SIZE  = 36
ASTEROID_MEDIUM_SIZE = 22  # produced when a large is destroyed (depth≥1)
ASTEROID_SMALL_SIZE  = 13  # produced when a medium is destroyed (depth≥2)

# ── Lives & invincibility ─────────────────────────────────────────────────────
STARTING_LIVES       = 3    # lives at game start and each new level
INVINCIBILITY_FRAMES = 120  # frames of protection after a hit (2 s at 60 FPS)

# ── Shield (hold SHIFT) ───────────────────────────────────────────────────────
SHIELD_MAX      = 300  # maximum energy units
SHIELD_DRAIN    = 1    # energy lost per frame while active
SHIELD_RECHARGE = 0.4  # energy gained per frame while inactive

# ── Hyperspace (press H) ──────────────────────────────────────────────────────
HYPERSPACE_DANGER = 0.25  # 25% chance of landing near an asteroid

# ── Screen shake ──────────────────────────────────────────────────────────────
SHAKE_DURATION  = 18  # frames the shake lasts after a hit
SHAKE_MAGNITUDE = 7   # maximum pixel offset during shake

# ── Power-ups ─────────────────────────────────────────────────────────────────
POWERUP_DROP_CHANCE = 0.18   # probability a large asteroid drops a power-up
POWERUP_DURATION    = 360    # frames a timed power-up lasts (6 s at 60 FPS)
POWERUP_RADIUS      = 12     # collision / rendering radius
RAPIDFIRE_COOLDOWN  = 3      # bullet cooldown frames during rapid-fire

# ── Mother Ship ───────────────────────────────────────────────────────────────
MOTHERSHIP_SPEED       = 0.45   # base pixels per frame toward the player
MOTHERSHIP_SHOOT_EVERY = 260    # base frames between shots (~4.3 s at 60 FPS)
MOTHERSHIP_HOME_STR    = 0.018  # homing bullet turn strength per frame
MOTHERSHIP_RING_COUNT  = 10     # asteroids spawned in the explosion ring
MOTHERSHIP_SCORE       = 500    # bonus points for destroying the Mother Ship

# ── Combo system ─────────────────────────────────────────────────────────────
COMBO_WINDOW = 90  # frames allowed between kills to keep the combo alive

# ── Colours (R, G, B) ─────────────────────────────────────────────────────────
WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0  )
RED        = (220, 30,  30 )
GREEN      = (0,   200, 80 )
BLUE       = (80,  160, 255)
YELLOW     = (255, 215, 0  )
ORANGE     = (255, 130, 0  )
CYAN       = (0,   220, 220)
LIGHT_GREY = (180, 180, 180)
DIM_GREY   = (100, 100, 100)
PURPLE     = (180, 60,  220)

# Thruster flame layers: outer (wide, orange) → middle → inner (narrow, near-white)
FLAME_COLOURS = [
    (255, 160,  20),
    (255, 220,  60),
    (255, 255, 180),
]

# ── Level definitions ─────────────────────────────────────────────────────────
# Each entry is one level's complete configuration.
#
# spawn   – number of large asteroids placed at wave start
# depth   – asteroid split depth: 0=no split, 1=large→medium, 2=full chain
# speed   – speed multiplier applied to all asteroids in this wave
# ms      – True if the Mother Ship appears this level
# pal     – colour palette key (see LEVEL_PALETTES below)
# special – True if dynamic asteroid types (fast/heavy/zigzag) are used
# banner  – text shown on the level-announce slide-in banner
#
# Design notes:
#   Level 3 has fewer rocks (5) because it simultaneously introduces the
#   full split chain AND the Mother Ship — two new challenges at once.
#   Special types are held back until Level 4 so the player can learn
#   the full chain before facing type-specific behaviour.
#   Level 8 has fewer rocks than Level 7 because it has the hardest
#   Mother Ship — total threat still increases.
LEVEL_DEFS = [
    dict(spawn=4, depth=0, speed=0.65, ms=False, pal="grey",   special=False,
         banner="Level 1  ·  Destroy the rocks!"),
    dict(spawn=5, depth=1, speed=0.78, ms=False, pal="grey",   special=False,
         banner="Level 2  ·  They split now — watch out!"),
    dict(spawn=5, depth=2, speed=0.88, ms=True,  pal="blue",   special=False,
         banner="Level 3  ·  Mother Ship detected — stay calm!"),
    dict(spawn=6, depth=2, speed=1.0,  ms=False, pal="blue",   special=True,
         banner="Level 4  ·  New asteroid types incoming…"),
    dict(spawn=7, depth=2, speed=1.15, ms=False, pal="orange", special=True,
         banner="Level 5  ·  Volcanic field — stay sharp!"),
    dict(spawn=8, depth=2, speed=1.3,  ms=True,  pal="orange", special=True,
         banner="Level 6  ·  Mother Ship returns — angrier now!"),
    dict(spawn=9, depth=2, speed=1.5,  ms=False, pal="purple", special=True,
         banner="Level 7  ·  Deep space — no mercy."),
    dict(spawn=8, depth=2, speed=1.45, ms=True,  pal="purple", special=True,
         banner="Level 8  ·  FINAL WAVE — give it everything!"),
]
MAX_DEFINED_LEVEL = len(LEVEL_DEFS)  # 8 — used to detect when all levels are cleared


def get_level_def(level: int) -> dict:
    """Return the definition dict for a given 1-indexed level.
    Cycles back to level 1 definition after MAX_DEFINED_LEVEL."""
    return LEVEL_DEFS[(level - 1) % MAX_DEFINED_LEVEL]


# Asteroid colour palettes — one per level zone.
# Each zone uses three shades: large, medium, and small.
# Colours shift every 2 levels to give visual variety:
#   grey (levels 1-2) → blue (3-4) → orange (5-6) → purple (7-8)
LEVEL_PALETTES = {
    "grey":   {"large": (155, 75,  38 ), "medium": (115, 115, 115), "small": (190, 150, 95 )},
    "blue":   {"large": (60,  100, 195), "medium": (50,  85,  170), "small": (120, 165, 235)},
    "orange": {"large": (195, 70,  15 ), "medium": (170, 52,  8  ), "small": (235, 130, 52 )},
    "purple": {"large": (130, 30,  175), "medium": (100, 22,  145), "small": (180, 88,  215)},
}


def level_palette(level: int) -> dict:
    """Return the colour palette dict for a given level."""
    return LEVEL_PALETTES[get_level_def(level)["pal"]]