"""
hud.py
All HUD and overlay rendering for AstroCrash.

The game loop calls one function per screen state — this module
owns all fonts, layout arithmetic, and animation so the loop
never constructs Surfaces or calls font.render() directly.
"""

import pygame

from constants import (
    WIDTH, HEIGHT,
    WHITE, RED, YELLOW, BLUE, CYAN, ORANGE,
    LIGHT_GREY, DIM_GREY, POWERUP_DURATION,
    get_level_def, MAX_DEFINED_LEVEL,
)

# Initialise fonts once at module load — creating a font each frame is slow
pygame.font.init()
_FL = pygame.font.SysFont("monospace", 36, bold=True)   # large  (title / score)
_FM = pygame.font.SysFont("monospace", 24, bold=True)   # medium (level, overlays)
_FS = pygame.font.SysFont("monospace", 18)               # small  (body text)
_FT = pygame.font.SysFont("monospace", 15)               # tiny   (secondary info)
_FX = pygame.font.SysFont("monospace", 13)               # micro  (debug / labels)


# ── In-game HUD ───────────────────────────────────────────────────────────────

def draw_hud(screen, ship, score: int, level: int,
             high_score: int = 0, combo: int = 0,
             rapidfire_timer: int = 0) -> None:
    """Draw all persistent on-screen information during gameplay:
    score, personal best, level number, lives icons, combo, and
    the rapid-fire energy bar when active."""
    _centred(screen, _FL, f"SCORE  {score:06d}", WHITE, 12)

    # Show best score — gold if currently beating it, grey otherwise
    if high_score:
        col = YELLOW if score >= high_score else DIM_GREY
        _centred(screen, _FX, f"BEST  {high_score:06d}", col, 54)

    _right(screen, _FM, f"LEVEL {level}", YELLOW, 16)
    _draw_lives(screen, ship.lives)

    # Combo multiplier — appears only when combo ≥ 2
    if combo >= 2:
        col = (255, max(0, 220 - combo * 20), 0)
        _centred(screen, _FM, f"COMBO  ×{combo}", col, 72)

    # Rapid-fire progress bar — only visible when the power-up is active
    if rapidfire_timer > 0:
        bw, bh = 160, 7
        bx = WIDTH // 2 - bw // 2
        by = HEIGHT - 50
        frac = rapidfire_timer / POWERUP_DURATION
        pygame.draw.rect(screen, (80, 40, 0), (bx, by, bw, bh), border_radius=4)
        pygame.draw.rect(screen, ORANGE, (bx, by, int(bw * frac), bh), border_radius=4)
        lbl = _FX.render("RAPID FIRE", True, ORANGE)
        screen.blit(lbl, lbl.get_rect(centerx=WIDTH // 2, bottom=by - 2))


def _draw_lives(screen, lives: int) -> None:
    """Render small rocket-shaped icons for each remaining life."""
    fnt = pygame.font.SysFont("monospace", 12)
    screen.blit(fnt.render("LIVES", True, (160, 160, 160)), (12, 42))
    for i in range(lives):
        cx, cy, s = 26 + i * 32, 26, 11
        pts = [(cx, cy - s),
               (cx - s * 0.75, cy + s * 0.6),
               (cx + s * 0.75, cy + s * 0.6)]
        pygame.draw.polygon(screen, BLUE, pts)
        pygame.draw.polygon(screen, WHITE, pts, 1)


# ── Level announce banner ─────────────────────────────────────────────────────

def draw_level_announce(screen, level: int, timer: int,
                        total: int = 120) -> None:
    """Animated banner that slides in from the top at the start of each level.

    Animation: slides down in the first 25% of its duration, holds
    for the middle 50%, then fades out over the last 25%.
    Text is read from the level's banner field in LEVEL_DEFS.
    """
    text     = get_level_def(level)["banner"]
    progress = 1.0 - (timer / total)

    if progress < 0.25:
        y = int(-50 + (progress / 0.25) * 110)
        alpha = 255
    elif progress < 0.75:
        y, alpha = 60, 255
    else:
        y     = 60
        alpha = int(255 * (1.0 - (progress - 0.75) / 0.25))

    surf = _FM.render(text, True, YELLOW)
    surf.set_alpha(alpha)
    screen.blit(surf, surf.get_rect(centerx=WIDTH // 2, centery=y))


# ── Level-clear overlay ───────────────────────────────────────────────────────

def draw_level_clear(screen, level: int) -> None:
    """Semi-transparent overlay shown between waves.
    Includes a progress bar showing how far through the 8 levels the player is."""
    _overlay(screen, 130)
    _centred(screen, _FL, f"LEVEL  {level}  CLEAR!", YELLOW, HEIGHT // 2 - 40)
    _centred(screen, _FS, "Preparing next sector…",  WHITE,  HEIGHT // 2 + 18)

    # Progress bar: filled proportion = current level / total levels
    done  = ((level - 1) % MAX_DEFINED_LEVEL) + 1
    bw, bh = 320, 10
    bx = WIDTH // 2 - bw // 2
    by = HEIGHT // 2 + 60
    pygame.draw.rect(screen, (55, 55, 55), (bx, by, bw, bh), border_radius=5)
    pygame.draw.rect(screen, YELLOW,
                     (bx, by, int(bw * done / MAX_DEFINED_LEVEL), bh),
                     border_radius=5)
    _centred(screen, _FT, f"Sector  {done}  of  {MAX_DEFINED_LEVEL}",
             DIM_GREY, by + 16)


# ── Game over overlay ─────────────────────────────────────────────────────────

def draw_game_over(screen, score: int, high_score: int,
                   is_new_record: bool, level_reached: int = 1,
                   asteroids_destroyed: int = 0) -> None:
    """Full-screen game over overlay showing score, best, and run stats."""
    _overlay(screen, 200)
    _centred(screen, _FL, "— GAME OVER —",            RED,        HEIGHT // 2 - 110)
    _centred(screen, _FM, f"Score :  {score:06d}",    WHITE,      HEIGHT // 2 - 50)
    if is_new_record:
        _centred(screen, _FM, "✦  NEW  RECORD  ✦",   YELLOW,     HEIGHT // 2 + 5)
    else:
        _centred(screen, _FT, f"Best  :  {high_score:06d}",
                 DIM_GREY, HEIGHT // 2 + 5)
    # Run statistics give the player a sense of their performance
    _centred(screen, _FT,
             f"Level reached: {level_reached}   |   Asteroids destroyed: {asteroids_destroyed}",
             LIGHT_GREY, HEIGHT // 2 + 42)
    _centred(screen, _FT, "R  ·  restart          Q  ·  quit",
             LIGHT_GREY, HEIGHT // 2 + 76)


# ── Pause overlay ─────────────────────────────────────────────────────────────

def draw_pause(screen) -> None:
    """Minimal pause overlay — gameplay is visible but frozen underneath."""
    _overlay(screen, 140)
    _centred(screen, _FL, "— PAUSED —",   WHITE,      HEIGHT // 2 - 30)
    _centred(screen, _FS, "P  ·  resume", LIGHT_GREY, HEIGHT // 2 + 30)


# ── Start screens (two pages) ─────────────────────────────────────────────────

def draw_start_screen(screen, high_score: int = 0, page: int = 0) -> None:
    """Two-page intro: page 0 = narrative story, page 1 = mission briefing."""
    if page == 0:
        _draw_story_page(screen, high_score)
    else:
        _draw_controls_page(screen, high_score)


def _draw_story_page(screen, high_score: int) -> None:
    """Narrative intro — sets the scene before gameplay begins."""
    _centred(screen, _FL, "✦  ASTROCRASH  ✦", WHITE, 70)

    story = [
        "The year is 2187.",
        "",
        "You are Commander Asha Reyes, lone pilot of the scout vessel",
        "Horizon IV, deep in the Kepler Belt — three light-years from",
        "the nearest inhabited system.",
        "",
        "Your long-range scanners are screaming.",
        "An asteroid field has destabilised and is closing fast.",
        "Worse: a hostile alien Mother Ship has been detected",
        "trailing the debris — using it as cover.",
        "",
        "Your cannons are charged.  Your hands are steady.",
        "There is no rescue coming.",
        "",
        "Survive.  Or don't.",
    ]
    for i, line in enumerate(story):
        col = YELLOW if line.startswith("Survive") else LIGHT_GREY
        _centred(screen, _FT, line, col, 160 + i * 26)

    if high_score:
        _centred(screen, _FT, f"Personal best:  {high_score:06d}",
                 (100, 180, 100), HEIGHT - 70)
    _centred(screen, _FS, "SPACE  ·  continue", WHITE, HEIGHT - 40)


def _draw_controls_page(screen, high_score: int) -> None:
    """Mission briefing — lists all controls and explains game mechanics."""
    _centred(screen, _FM, "— MISSION BRIEFING —", YELLOW, 55)

    # Each row: (label, description text)
    # Blank label = continuation line, indented below the labelled row
    rules = [
        ("OBJECTIVE",   "Destroy all asteroids in each sector to advance."),
        ("",            "Clear all 8 sectors to complete the mission."),
        ("",            ""),
        ("MOVE + AIM",  "Mouse  —  ship follows cursor, stops when close"),
        ("SHOOT",       "Left Click  (max 5 bullets, brief cooldown)"),
        ("SHIELD",      "Hold  SHIFT  —  absorbs hits while energy remains"),
        ("HYPERSPACE",  "Press  H  —  panic teleport  (25% danger risk!)"),
        ("PAUSE",       "Press  P"),
        ("DEBUG",       "Press  TAB  —  show hitboxes + velocity vectors"),
        ("",            ""),
        ("ASTEROIDS",   "Level 1: large rocks only  (no splitting)."),
        ("",            "Level 2: large rocks split into medium fragments."),
        ("",            "Level 3+: full chain  large → medium → small."),
        ("",            "         + FAST (red) / HEAVY (2 hits) / ZIGZAG types."),
        ("",            ""),
        ("POWER-UPS",   "Drop from large rocks:"),
        ("",            "  RF = Rapid Fire   SH = Shield recharge   +1 = Extra life"),
        ("",            ""),
        ("MOTHER SHIP", "Levels 3, 6 and 8.  Slow but fires homing shots."),
        ("",            "Spike points at YOU.  500-point bonus on kill."),
    ]
    y = 110
    for label, text in rules:
        if label:
            sl = _FS.render(f"{label:<12}", True, YELLOW)
            st = _FS.render(text, True, WHITE)
            screen.blit(sl, (WIDTH // 2 - 360, y))
            screen.blit(st, (WIDTH // 2 - 360 + sl.get_width() + 6, y))
        else:
            st = _FS.render(text, True, LIGHT_GREY)
            screen.blit(st, (WIDTH // 2 - 360 + 192, y))
        y += 22

    _centred(screen, _FS, "SPACE  ·  launch", (100, 220, 100), HEIGHT - 40)


# ── Debug engineering overlay ─────────────────────────────────────────────────

def draw_debug_overlay(screen, clock, gv: dict) -> None:
    """Engineering stats panel shown when debug mode is active (TAB key).

    Displays live FPS, entity counts, and a toggle reminder.
    Useful for verifying efficiency — confirms 60 FPS is maintained
    and that the particle system is not leaking memory.
    """
    fps  = clock.get_fps()
    info = [
        f"FPS         : {fps:.1f}",
        f"Asteroids   : {len(gv['asteroids'])}",
        f"Bullets     : {len(gv['bullets'])}",
        f"Particles   : {len(gv['particles'])}",
        f"MB bullets  : {len(gv['mbullets'])}",
        f"Power-ups   : {len(gv['powerups'])}",
        f"DEBUG  [TAB to toggle]",
    ]
    fnt = pygame.font.SysFont("monospace", 13)
    x   = WIDTH - 220
    y   = HEIGHT - len(info) * 18 - 8
    # Semi-transparent background so the text is always readable
    panel = pygame.Surface((210, len(info) * 18 + 6), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 160))
    screen.blit(panel, (x - 4, y - 2))
    for i, line in enumerate(info):
        col = (0, 255, 0) if i < len(info) - 1 else (180, 180, 180)
        screen.blit(fnt.render(line, True, col), (x, y + i * 18))


# ── Shared utilities ──────────────────────────────────────────────────────────

def _centred(screen, font, text, colour, y) -> None:
    """Render text horizontally centred at the given y position."""
    s = font.render(text, True, colour)
    screen.blit(s, s.get_rect(centerx=WIDTH // 2, top=y))


def _right(screen, font, text, colour, y) -> None:
    """Render text right-aligned with a small margin from the window edge."""
    s = font.render(text, True, colour)
    screen.blit(s, s.get_rect(right=WIDTH - 16, top=y))


def _overlay(screen, alpha: int) -> None:
    """Draw a full-screen semi-transparent black rectangle."""
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, alpha))
    screen.blit(ov, (0, 0))