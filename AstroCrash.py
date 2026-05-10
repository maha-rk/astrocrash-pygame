"""
AstroCrash.py
Main entry point and game loop.

How it works
------------
The game uses a finite-state machine — a variable called `state` holds
one of six string labels. The main while loop checks this label each
frame and runs the correct code path:

  STATE_STORY       - narrative intro, waits for SPACE
  STATE_BRIEF       - mission briefing / controls, waits for SPACE
  STATE_PLAYING     - active gameplay (physics, collisions, rendering)
  STATE_PAUSED      - overlay over frozen game, P to resume
  STATE_LEVEL_CLEAR - between-wave overlay, auto-advances after 2 s
  STATE_GAME_OVER   - death screen, R to restart / Q to quit
  STATE_VICTORY     - animated win screen (victory.py), SPACE to restart

All game objects live in a dictionary called `gv` (game variables).
Storing state in a dict rather than globals means init_game() can
reset everything cleanly by returning a fresh dict.

Delta-time physics
------------------
  dt = clock.tick(FPS) / 1000   (seconds this frame, capped at 50 ms)
  All motion: x += dx * dt * 60

  The * 60 means at exactly 60 FPS the numbers match the original
  per-frame constants. On faster/slower machines the physics stays
  consistent — this is frame-rate independence.

Controls
--------
  Mouse      - ship chases cursor (stops when cursor is close)
  Left Click - shoot (max 5 bullets, cooldown between shots)
  SHIFT hold - activate shield
  H          - hyperspace panic teleport
  P          - pause / unpause
  TAB        - debug engineering overlay
  SPACE      - start / advance screens
  R          - restart (game-over screen only)
"""

import sys
import random
import math
import pygame

from constants import (
    WIDTH, HEIGHT, FPS, TITLE, BLACK, WHITE, YELLOW, RED, CYAN,
    SHAKE_DURATION, SHAKE_MAGNITUDE,
    BULLET_MAX, BULLET_COOLDOWN,
    RAPIDFIRE_COOLDOWN, POWERUP_DURATION, POWERUP_DROP_CHANCE,
    HYPERSPACE_DANGER, COMBO_WINDOW,
    get_level_def, MAX_DEFINED_LEVEL,
)
from entities import (
    Ship, Bullet, Asteroid, MotherShip,
    PowerUp, FloatingText,
    circles_overlap, resolve_asteroid_collision,
)
from spawner import spawn_wave
from particles import Starfield, spawn_explosion
from commentary import Commentary, NEAR_MISS_DIST
from hud import (
    draw_hud, draw_game_over, draw_level_clear,
    draw_start_screen, draw_level_announce,
    draw_pause, draw_debug_overlay,
)
from victory import VictoryScreen
import highscore

# ── State labels ──────────────────────────────────────────────────────────────
STATE_STORY       = "story"
STATE_BRIEF       = "brief"
STATE_PLAYING     = "playing"
STATE_PAUSED      = "paused"
STATE_LEVEL_CLEAR = "level_clear"
STATE_GAME_OVER   = "game_over"
STATE_VICTORY     = "victory"

LEVEL_CLEAR_DUR = 120   # frames the level-clear overlay is shown (2 s)
ANNOUNCE_DUR    = 120   # frames the level-announce banner is shown


# ── Game initialisation ───────────────────────────────────────────────────────
# Initializes and returns the full game state
# Keeps all mutable runtime data in one dictionary for easy reset/restart
def init_game() -> dict:
    """Build and return a fresh game-state dictionary.

    Called at startup and whenever the player restarts. Returning a new
    dict each time prevents stale values from one session affecting the
    next — cleaner than resetting individual global variables.
    """
    asteroids = spawn_wave(1)
    ship      = Ship(WIDTH // 2, HEIGHT // 2)
    # Ensure the ship doesn't start on top of an asteroid
    _safe_respawn(ship, asteroids)

    return dict(
        ship                 = ship,
        level                = 1,
        score                = 0,
        bullets              = [],
        asteroids            = asteroids,
        particles            = [],       # explosion debris
        mothership           = None,     # MotherShip instance or None
        mbullets             = [],       # MotherBullet list
        powerups             = [],       # PowerUp list
        floats               = [],       # FloatingText list (kill labels)
        level_clear_timer    = 0,
        announce_timer       = ANNOUNCE_DUR,
        shake_timer          = 0,        # frames of screen shake remaining
        frame                = 0,        # absolute frame counter
        shoot_cooldown       = 0,        # frames until next shot is allowed
        rapidfire_timer      = 0,        # frames of rapid-fire power-up remaining
        combo                = 0,        # current kill-streak count
        combo_timer          = 0,        # frames until combo resets
        debug                = False,    # True when TAB overlay is visible
        asteroids_destroyed  = 0,        # total kills (shown on game-over screen)
        level_reached        = 1,        # highest level entered (shown on game-over)
    )


# ── Entry point ───────────────────────────────────────────────────────────────
# Main entry point
# Sets up pygame, loads resources, and runs the infinite game loop
def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)
    clock  = pygame.time.Clock()
    pygame.mouse.set_visible(False)

    # Offscreen canvas — everything is drawn here each frame, then blitted
    # to the real screen with a shake offset when the ship has been hit.
    canvas    = pygame.Surface((WIDTH, HEIGHT))
    starfield = Starfield()
    comment   = Commentary()
    hs        = highscore.load()
    state     = STATE_STORY
    gv        = init_game()
    victory   = None   # VictoryScreen instance, created when all 8 levels clear

    while True:
        # ──────────────────────────────────────────────────────────────
        # Main Game Loop (Finite State Machine)
        #
        # This loop runs continuously (~60 FPS) and:
        # - handles input events
        # - updates game logic
        # - renders the current frame
        #
        # Behaviour changes depending on the current game state
        # (e.g. menu, gameplay, pause, game over, victory).
        #
        # Efficiency is critical since this loop executes every frame.
        # ──────────────────────────────────────────────────────────────
        raw_ms = clock.tick(FPS)
        dt     = min(raw_ms / 1000.0, 0.05)

        # ── Victory screen has its own event loop ─────────────────────────────
        if state == STATE_VICTORY:
            if victory.update():   # returns True when player presses SPACE
                gv      = init_game()
                comment.reset()
                victory = None
                state   = STATE_STORY
            else:
                victory.draw(screen)
            pygame.display.update()
            continue

        # ── Events ────────────────────────────────────────────────────────────

        # --- Input Handling ---
        # Processes all user inputs (keyboard, mouse, system events)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                k = event.key

                if k == pygame.K_SPACE:
                    if   state == STATE_STORY: state = STATE_BRIEF
                    elif state == STATE_BRIEF:
                        gv = init_game()
                        comment.reset()
                        state = STATE_PLAYING

                if k == pygame.K_p and state in (STATE_PLAYING, STATE_PAUSED):
                    state = STATE_PAUSED if state == STATE_PLAYING else STATE_PLAYING

                if k == pygame.K_r and state == STATE_GAME_OVER:
                    gv = init_game()
                    comment.reset()
                    state = STATE_PLAYING

                if k == pygame.K_q and state == STATE_GAME_OVER:
                    pygame.quit()
                    sys.exit()

                if k == pygame.K_TAB and state == STATE_PLAYING:
                    gv["debug"] = not gv["debug"]

                if k == pygame.K_h and state == STATE_PLAYING:
                    _do_hyperspace(gv, comment)

            # Shoot on left mouse click — only during active gameplay
            if (event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                    and state == STATE_PLAYING):
                _try_shoot(gv)

        # ── Build the frame on the offscreen canvas ───────────────────────────
        # Apply a subtle background tint that shifts with the level palette
        tints = {"grey": (0,0,0), "blue": (0,0,8), "orange": (8,2,0), "purple": (4,0,8)}
        pal_key = get_level_def(gv["level"]).get("pal", "grey") if state == STATE_PLAYING else "grey"
        canvas.fill(tints.get(pal_key, (0, 0, 0)))
        starfield.draw(canvas, gv["frame"])

        if state == STATE_STORY:
            draw_start_screen(canvas, hs, page=0)

        elif state == STATE_BRIEF:
            draw_start_screen(canvas, hs, page=1)

        elif state == STATE_PLAYING:
            state, hs = _update_playing(canvas, gv, comment, hs, dt, clock)

        elif state == STATE_PAUSED:
            _draw_entities(canvas, gv)
            draw_hud(canvas, gv["ship"], gv["score"],
                     gv["level"], hs, gv["combo"], gv["rapidfire_timer"])
            draw_pause(canvas)

        elif state == STATE_LEVEL_CLEAR:
            _draw_entities(canvas, gv)
            draw_level_clear(canvas, gv["level"])
            gv["level_clear_timer"] -= 1
            if gv["level_clear_timer"] <= 0:
                if gv["level"] >= MAX_DEFINED_LEVEL:
                    # All 8 levels cleared — show victory screen
                    highscore.save(gv["score"])
                    hs      = highscore.load()
                    victory = VictoryScreen(gv["score"], hs,
                                            gv["level_reached"],
                                            gv["asteroids_destroyed"])
                    state = STATE_VICTORY
                else:
                    # Advance to next level
                    gv["level"] += 1
                    ldef = get_level_def(gv["level"])
                    gv["asteroids"]      = spawn_wave(gv["level"])
                    gv["bullets"]        = []
                    gv["mbullets"]       = []
                    gv["powerups"]       = []
                    gv["announce_timer"] = ANNOUNCE_DUR
                    gv["ship"].lives     = 3   # reset lives each new level
                    _safe_respawn(gv["ship"], gv["asteroids"])
                    gv["mothership"] = (
                        MotherShip(WIDTH - 100, HEIGHT // 2, gv["level"])
                        if ldef["ms"] else None)
                    if gv["mothership"]:
                        comment.on_mothership_appear()
                    state = STATE_PLAYING

        elif state == STATE_GAME_OVER:
            draw_game_over(canvas, gv["score"], hs,
                           gv["score"] > hs,
                           gv["level_reached"],
                           gv["asteroids_destroyed"])

        # ── Screen shake ──────────────────────────────────────────────────────
        # Achieved by blitting the canvas to the screen with a random offset.
        # The canvas itself is never distorted.
        if gv["shake_timer"] > 0:
            ox = random.randint(-SHAKE_MAGNITUDE, SHAKE_MAGNITUDE)
            oy = random.randint(-SHAKE_MAGNITUDE, SHAKE_MAGNITUDE)
            gv["shake_timer"] -= 1
        else:
            ox = oy = 0

        screen.fill(BLACK)
        screen.blit(canvas, (ox, oy))
        gv["frame"] += 1
        pygame.display.update()


# ── Shoot helper ──────────────────────────────────────────────────────────────

def _try_shoot(gv: dict) -> None:
    """Fire a bullet if the cooldown has elapsed and the bullet cap allows it."""
    cooldown = RAPIDFIRE_COOLDOWN if gv["rapidfire_timer"] > 0 else BULLET_COOLDOWN
    if gv["shoot_cooldown"] <= 0 and len(gv["bullets"]) < BULLET_MAX:
        s    = gv["ship"]
        fast = gv["rapidfire_timer"] > 0
        gv["bullets"].append(Bullet(s.x, s.y, s.angle, fast))
        gv["shoot_cooldown"] = cooldown


# ── Hyperspace helper ─────────────────────────────────────────────────────────

def _do_hyperspace(gv: dict, comment: Commentary) -> None:
    """Teleport the ship to a random position.

    25% chance of a 'bad jump' that lands near a random asteroid.
    Coordinates are clamped inside the screen boundary after teleport
    to prevent the ship from spawning in the border margin.
    """
    ship = gv["ship"]
    ship.hyperspace()

    # Clamp to safe bounds regardless of outcome
    ship.x = max(80, min(WIDTH  - 80, ship.x))
    ship.y = max(80, min(HEIGHT - 80, ship.y))

    if random.random() < HYPERSPACE_DANGER and gv["asteroids"]:
        # Bad jump — land near a random asteroid
        target = random.choice(gv["asteroids"])
        ship.x = (target.x + random.uniform(-60, 60)) % WIDTH
        ship.y = (target.y + random.uniform(-60, 60)) % HEIGHT
        comment._push("Bad jump — danger zone!", RED)
    else:
        comment._push("Hyperspace activated!", CYAN)


# ── Safe respawn helper ───────────────────────────────────────────────────────

def _safe_respawn(ship: Ship, asteroids: list, margin: int = 80) -> None:
    """Move the ship to a position that does not overlap any asteroid.

    Tries the screen centre first, then four corner positions, then up
    to 40 random positions. Falls back to the centre if nothing works.
    Grants invincibility regardless of where the ship lands.
    """
    candidates = [
        (WIDTH // 2,     HEIGHT // 2),      # screen centre — tried first
        (WIDTH // 4,     HEIGHT // 4),
        (WIDTH * 3 // 4, HEIGHT // 4),
        (WIDTH // 4,     HEIGHT * 3 // 4),
        (WIDTH * 3 // 4, HEIGHT * 3 // 4),
    ]
    for _ in range(40):
        candidates.append((
            random.uniform(margin, WIDTH  - margin),
            random.uniform(margin, HEIGHT - margin),
        ))

    for cx, cy in candidates:
        # A position is safe if the ship is at least 30 px from every asteroid edge
        safe = all(
            math.hypot(cx - a.x, cy - a.y) > a.size + ship.radius + 30
            for a in asteroids
        )
        if safe:
            ship.x = float(cx)
            ship.y = float(cy)
            ship.invincible_timer = 120
            return

    # Fallback: centre with maximum invincibility
    ship.x = float(WIDTH  // 2)
    ship.y = float(HEIGHT // 2)
    ship.invincible_timer = 120


# ── Main playing update ───────────────────────────────────────────────────────

def _update_playing(canvas, gv: dict, comment: Commentary,
                    hs: int, dt: float, clock) -> tuple:
    """Run one frame of active gameplay and return (next_state, high_score).

    Frame order
    -----------
    1.  Ship — move, aim, shield, invincibility
    2.  Bullets — move, cull off-screen
    3.  Asteroid-asteroid elastic collisions
    4.  Asteroid movement, bullet hits, ship hits
    5.  Mother Ship — move, shoot, bullet hits, ship hit
    6.  Mother bullets — homing update, ship hit, cull
    7.  Power-ups — move, collect
    8.  Particles and floating text — update, cull expired
    9.  Commentary — tick timers
    10. Draw all entities + HUD + banner + floats + commentary
    11. Win / loss checks
    """
    ship      = gv["ship"]
    bullets   = gv["bullets"]
    asteroids = gv["asteroids"]
    particles = gv["particles"]
    mbullets  = gv["mbullets"]
    powerups  = gv["powerups"]
    floats    = gv["floats"]

    # 1. Ship
    mx, my = pygame.mouse.get_pos()
    ship.update(mx, my, dt)
    ship.tick_invincibility()
    if gv["shoot_cooldown"]  > 0: gv["shoot_cooldown"]  -= 1
    if gv["rapidfire_timer"] > 0: gv["rapidfire_timer"] -= 1
    if gv["combo_timer"]     > 0: gv["combo_timer"]     -= 1
    else:                         gv["combo"] = 0

    # 2. Bullets — move each one and remove it once it leaves the screen
    for b in list(bullets):
        b.move(dt)
        if b.off_screen:
            bullets.remove(b)

    # 3. Asteroid-asteroid elastic collisions
    # All pairs are checked. O(n²) is fine here — max ~30 asteroids at once.
    for i in range(len(asteroids)):
        for j in range(i + 1, len(asteroids)):
            a1, a2 = asteroids[i], asteroids[j]
            if circles_overlap(a1.x, a1.y, a1.size, a2.x, a2.y, a2.size):
                resolve_asteroid_collision(a1, a2)

    # 4. Asteroid movement and collision detection
    # Index sets are used so the asteroid/bullet lists are never mutated
    # during iteration — avoids ValueError from in-place removal.
    new_frags = []
    a_rm      = set()   # asteroid indices to remove this frame
    b_rm      = set()   # bullet indices to remove this frame

    for ia, ast in enumerate(asteroids):
        ast.move(dt)

        # Near-miss check — triggers commentary when very close but no collision
        if not ship.is_invincible:
            dist = math.hypot(ast.x - ship.x, ast.y - ship.y)
            if ast.size + NEAR_MISS_DIST > dist > ast.size + ship.radius:
                comment.on_near_miss()

        # Bullet-asteroid collision
        for ib, bul in enumerate(bullets):
            if ib in b_rm:
                continue   # bullet already consumed this frame
            if circles_overlap(ast.x, ast.y, ast.size,
                               bul.x, bul.y, bul.radius):
                if ast.hit():   # returns True when fully destroyed
                    ast.flash_timer = 4   # brief white flash on impact

                    # Score = size × level bonus × combo multiplier
                    gv["combo"]      += 1
                    gv["combo_timer"] = COMBO_WINDOW
                    mult  = max(1, gv["combo"])
                    pts   = ast.size * (1 + gv["level"] // 3) * mult
                    gv["score"]              += int(pts)
                    gv["asteroids_destroyed"] += 1

                    # Floating kill label
                    col = YELLOW if mult == 1 else (255, 120, 0)
                    floats.append(FloatingText(
                        ast.x, ast.y - ast.size,
                        f"+{int(pts)}" + (f" ×{mult}" if mult > 1 else ""), col))

                    a_rm.add(ia)
                    new_frags.extend(ast.split())
                    particles.extend(spawn_explosion(ast.x, ast.y, ast.size))
                    comment.on_asteroid_killed(ast.size)

                    # 18% chance to drop a power-up from large asteroids
                    if ast.size >= 30 and random.random() < POWERUP_DROP_CHANCE:
                        kind = random.choices(
                            ["rapidfire", "shield", "extralife"],
                            weights=[50, 35, 15], k=1)[0]
                        powerups.append(PowerUp(ast.x, ast.y, kind))
                b_rm.add(ib)
                break   # one bullet can only destroy one asteroid per frame

        # Ship-asteroid collision (only when not invincible)
        if ia not in a_rm and not ship.is_invincible:
            if circles_overlap(ast.x, ast.y, ast.size,
                               ship.x, ship.y, ship.radius):
                absorbed = not ship.take_hit()
                if not absorbed:
                    ship.reset_position()
                    comment.on_hit(ship.lives)
                    gv["shake_timer"] = SHAKE_DURATION
                particles.extend(spawn_explosion(ast.x, ast.y, ast.size))
                a_rm.add(ia)

    # Apply removals in reverse index order so earlier indices stay valid
    for idx in sorted(a_rm, reverse=True): asteroids.pop(idx)
    for idx in sorted(b_rm, reverse=True): bullets.pop(idx)
    asteroids.extend(new_frags)

    # 5. Mother Ship
    ms = gv["mothership"]
    if ms and ms.alive:
        mbullets.extend(ms.update(ship.x, ship.y, dt))

        btr = set()   # bullet indices that hit the Mother Ship
        for ib, bul in enumerate(bullets):
            if circles_overlap(ms.x, ms.y, ms.radius,
                               bul.x, bul.y, bul.radius):
                btr.add(ib)
                if ms.take_hit():
                    gv["score"] += ms.SCORE_VALUE
                    # Only spawn the ring if asteroids remain — otherwise the
                    # level would fail to clear after the player clears the board
                    if len(asteroids) > 0:
                        asteroids.extend(ms.explode())
                    particles.extend(spawn_explosion(ms.x, ms.y, ms.radius * 2))
                    floats.append(FloatingText(ms.x, ms.y, "+500 MOTHERSHIP!", (220, 80, 220)))
                    gv["mothership"]  = None
                    gv["shake_timer"] = SHAKE_DURATION
                break
        for idx in sorted(btr, reverse=True): bullets.pop(idx)

        if ms and not ship.is_invincible:
            if circles_overlap(ms.x, ms.y, ms.radius,
                               ship.x, ship.y, ship.radius):
                absorbed = not ship.take_hit()
                if not absorbed:
                    ship.reset_position()
                    comment.on_hit(ship.lives)
                    gv["shake_timer"] = SHAKE_DURATION

    # 6. Mother bullets (homing projectiles)
    mb_rm = set()
    for im, mb in enumerate(mbullets):
        mb.update(ship.x, ship.y, dt)
        if mb.off_screen:
            mb_rm.add(im)
            continue
        if not ship.is_invincible:
            if circles_overlap(mb.x, mb.y, mb.radius,
                               ship.x, ship.y, ship.radius):
                absorbed = not ship.take_hit()
                if not absorbed:
                    ship.reset_position()
                    comment.on_hit(ship.lives)
                    gv["shake_timer"] = SHAKE_DURATION
                mb_rm.add(im)
    for idx in sorted(mb_rm, reverse=True): mbullets.pop(idx)

    # 7. Power-ups — move them and collect on overlap with ship
    pu_rm = set()
    for ip, pu in enumerate(powerups):
        pu.update(dt)
        # Slightly enlarged collection radius so it doesn't feel pixel-perfect
        if circles_overlap(pu.x, pu.y, pu.radius,
                           ship.x, ship.y, ship.radius + 8):
            _apply_powerup(gv, pu.kind, comment)
            pu_rm.add(ip)
    for idx in sorted(pu_rm, reverse=True): powerups.pop(idx)

    # 8. Particles and floating text — update and remove when expired
    for p in list(particles):
        p.update()
        if not p.alive: particles.remove(p)
    for ft in list(floats):
        ft.update()
        if not ft.alive: floats.remove(ft)

    # 9. Commentary tick
    comment.tick()

    # 10. Draw everything
    _draw_entities(canvas, gv)
    if gv["debug"]:
        _draw_debug(canvas, gv, clock)
    draw_hud(canvas, ship, gv["score"], gv["level"], hs,
             gv["combo"], gv["rapidfire_timer"])
    ship.draw_shield_bar(canvas)

    # Level announce banner (slides in at start of each level)
    if gv["announce_timer"] > 0:
        draw_level_announce(canvas, gv["level"],
                            gv["announce_timer"], ANNOUNCE_DUR)
        gv["announce_timer"] -= 1

    for ft in floats:
        ft.draw(canvas)
    comment.draw(canvas)

    # Hint when the Mother Ship is the last thing remaining
    if len(asteroids) == 0 and gv["mothership"] and gv["mothership"].alive:
        comment.on_mothership_only()

    # Fading control hint at the start of level 1
    if gv["level"] == 1 and gv["frame"] < 600:
        alpha = min(255, max(0, 255 - max(0, gv["frame"] - 420)))
        fnt   = pygame.font.SysFont("monospace", 16)
        hint  = fnt.render(
            "Move mouse to fly   |   Stop moving mouse to hover   |   Click to shoot",
            True, (150, 150, 150))
        hint.set_alpha(alpha)
        canvas.blit(hint, hint.get_rect(centerx=WIDTH // 2, bottom=HEIGHT - 60))

    # 11. Win / loss checks
    if ship.lives <= 0:
        highscore.save(gv["score"])
        hs = highscore.load()
        gv["level_reached"] = gv["level"]
        # Clear all entities so the game-over screen is clean and readable
        for k in ("asteroids", "bullets", "mbullets", "particles", "powerups", "floats"):
            gv[k].clear()
        gv["mothership"] = None
        return STATE_GAME_OVER, hs

    if len(asteroids) == 0 and gv["mothership"] is None:
        gv["level_reached"] = gv["level"]
        comment.on_level_clear()
        gv["level_clear_timer"] = LEVEL_CLEAR_DUR
        return STATE_LEVEL_CLEAR, hs

    return STATE_PLAYING, hs


# ── Power-up application ──────────────────────────────────────────────────────

def _apply_powerup(gv: dict, kind: str, comment: Commentary) -> None:
    """Apply the collected power-up effect to the game state."""
    from constants import SHIELD_MAX
    ship = gv["ship"]
    if kind == "rapidfire":
        gv["rapidfire_timer"] = POWERUP_DURATION
        comment._push("RAPID FIRE — go go go!", (255, 160, 0))
    elif kind == "shield":
        ship.shield_energy = float(SHIELD_MAX)   # clamp enforced in Ship.update
        comment._push("Shield fully recharged!", (0, 210, 210))
    elif kind == "extralife":
        ship.lives = min(ship.lives + 1, 5)       # cap at 5 lives
        comment._push("Extra life!", (0, 220, 80))


# ── Draw helpers ──────────────────────────────────────────────────────────────

def _draw_entities(canvas, gv: dict) -> None:
    """Draw all game objects back-to-front so the ship is always on top."""
    for p  in gv["particles"]: p.draw(canvas)
    for a  in gv["asteroids"]: a.draw(canvas)
    for pu in gv["powerups"]:  pu.draw(canvas)
    for mb in gv["mbullets"]:  mb.draw(canvas)
    ms = gv.get("mothership")
    if ms and ms.alive:        ms.draw(canvas)
    for b  in gv["bullets"]:   b.draw(canvas)
    gv["ship"].draw(canvas, gv["frame"])


def _draw_debug(canvas, gv: dict, clock) -> None:
    """Draw hitbox circles and velocity vectors for all entities.

    Green circle = ship hitbox.
    Yellow circle + line = asteroid hitbox + velocity direction.
    Pink circle = Mother Ship hitbox.
    Stats panel (bottom-right) shows live FPS and entity counts.
    """
    ship = gv["ship"]
    pygame.draw.circle(canvas, (0, 255, 0),
                       (int(ship.x), int(ship.y)), ship.radius, 1)
    for ast in gv["asteroids"]:
        pygame.draw.circle(canvas, (255, 255, 0),
                           (int(ast.x), int(ast.y)), ast.size, 1)
        # Velocity vector: line scaled × 12 so it's visible at typical speeds
        ex = int(ast.x + ast.dx * 12)
        ey = int(ast.y + ast.dy * 12)
        pygame.draw.line(canvas, (255, 200, 0),
                         (int(ast.x), int(ast.y)), (ex, ey), 1)
    ms = gv.get("mothership")
    if ms and ms.alive:
        pygame.draw.circle(canvas, (255, 100, 255),
                           (int(ms.x), int(ms.y)), ms.radius, 1)
    draw_debug_overlay(canvas, clock, gv)


if __name__ == "__main__":
    main()