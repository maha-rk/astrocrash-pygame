"""
entities.py
All game-object classes and physics helpers for AstroCrash.

Classes
-------
  FloatingText   – "+N" score label that rises and fades on a kill
  PowerUp        – collectible that drifts and pulses
  ThrustDot      – single particle in the rocket's thrust trail
  Ship           – the player's rocket (mouse-controlled, auto-aims)
  Bullet         – projectile fired by the ship
  Asteroid       – spinning rock with fixed shape and optional special type
  MotherShip     – UFO boss enemy with health bar and homing cannon
  MotherBullet   – slow homing projectile fired by the MotherShip

Physics helpers
---------------
  circles_overlap()          – True when two circles intersect
  resolve_asteroid_collision() – 1-D elastic impulse + positional correction
"""

import math
import random
import pygame

from constants import (
    WIDTH, HEIGHT,
    SHIP_RADIUS, SHIP_SIZE, SHIP_SPEED,
    MOVE_THRESHOLD, STOP_RADIUS, AIM_FREEZE_RADIUS,
    BULLET_RADIUS, BULLET_SPEED,
    ASTEROID_LARGE_SIZE, ASTEROID_MEDIUM_SIZE, ASTEROID_SMALL_SIZE,
    STARTING_LIVES, INVINCIBILITY_FRAMES,
    SHIELD_MAX, SHIELD_DRAIN, SHIELD_RECHARGE,
    MOTHERSHIP_SPEED, MOTHERSHIP_SHOOT_EVERY, MOTHERSHIP_HOME_STR,
    MOTHERSHIP_RING_COUNT,
    POWERUP_RADIUS,
    WHITE, BLUE, RED, YELLOW, ORANGE, CYAN, GREEN,
    FLAME_COLOURS, level_palette, LEVEL_PALETTES,
)


# ── FloatingText ──────────────────────────────────────────────────────────────

class FloatingText:
    """A "+N" label that rises from a kill location and fades out."""

    def __init__(self, x: float, y: float, text: str, colour=YELLOW):
        self.x        = x
        self.y        = float(y)
        self.text     = text
        self.colour   = colour
        self.life     = 50
        self.max_life = 50
        self._font    = pygame.font.SysFont("monospace", 16, bold=True)

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.y    -= 1.2   # rise upward
        self.life -= 1

    def draw(self, screen: pygame.Surface) -> None:
        surf = self._font.render(self.text, True, self.colour)
        surf.set_alpha(int(255 * self.life / self.max_life))
        screen.blit(surf, surf.get_rect(center=(int(self.x), int(self.y))))


# ── PowerUp ───────────────────────────────────────────────────────────────────

# Visual properties for each power-up type
POWERUP_COLOURS = {"rapidfire": ORANGE, "shield": CYAN, "extralife": GREEN}
POWERUP_LABELS  = {"rapidfire": "RF",   "shield": "SH", "extralife": "+1"}


class PowerUp:
    """A collectible that drifts slowly and pulses to attract attention.

    Types:
      rapidfire  – fires 3× faster for 6 seconds
      shield     – instantly refills shield energy
      extralife  – adds one life (max 5)
    """

    def __init__(self, x: float, y: float, kind: str):
        self.x      = float(x)
        self.y      = float(y)
        self.kind   = kind
        self.radius = POWERUP_RADIUS
        # Drift in a random direction at a slow, gentle speed
        spd     = random.uniform(0.5, 1.5)
        ang     = random.uniform(0, 360)
        self.dx = math.cos(math.radians(ang)) * spd
        self.dy = math.sin(math.radians(ang)) * spd
        self._age  = 0
        self._font = pygame.font.SysFont("monospace", 11, bold=True)

    def update(self, dt: float = 1/60) -> None:
        """Move the power-up and wrap at screen edges."""
        self.x = (self.x + self.dx * dt * 60) % WIDTH
        self.y = (self.y + self.dy * dt * 60) % HEIGHT
        self._age += 1

    def draw(self, screen: pygame.Surface) -> None:
        """Draw as a pulsing circle with a type label inside."""
        pulse = 1.0 + 0.15 * math.sin(self._age * 0.12)
        r     = int(self.radius * pulse)
        col   = POWERUP_COLOURS[self.kind]
        pygame.draw.circle(screen, col,   (int(self.x), int(self.y)), r)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), r, 1)
        lbl = self._font.render(POWERUP_LABELS[self.kind], True, WHITE)
        screen.blit(lbl, lbl.get_rect(center=(int(self.x), int(self.y))))


# ── ThrustDot ─────────────────────────────────────────────────────────────────

class ThrustDot:
    """A single tiny dot emitted from the rocket nozzle while thrusting.

    Dots fade from orange to black over their short lifetime,
    giving the appearance of glowing exhaust.
    """

    def __init__(self, x: float, y: float, dx: float, dy: float):
        self.x  = x
        self.y  = y
        # Add a small random spread so the trail looks natural
        self.dx = dx + random.uniform(-0.5, 0.5)
        self.dy = dy + random.uniform(-0.5, 0.5)
        self.life     = random.randint(8, 18)
        self.max_life = self.life

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.x    += self.dx
        self.y    += self.dy
        self.life -= 1

    def draw(self, screen: pygame.Surface) -> None:
        frac = self.life / self.max_life
        b    = int(200 * frac)
        pygame.draw.circle(screen, (b, int(b * 0.6), 0),
                           (int(self.x), int(self.y)), max(1, int(3 * frac)))


# ── Ship ──────────────────────────────────────────────────────────────────────

class Ship:
    """The player's rocket ship.

    Movement: chases the mouse cursor at SHIP_SPEED px/frame.
    Dead zone: stops when cursor is within STOP_RADIUS to allow hovering.
    Auto-aim: nose faces cursor via atan2, frozen within AIM_FREEZE_RADIUS
              to prevent the spinning-star artefact at close range.
    Shield:   hold SHIFT — absorbs hits while energy remains.
    Flame:    always rendered (idle flicker when still, full when moving).
    """

    def __init__(self, x: float, y: float):
        self.x      = float(x)
        self.y      = float(y)
        self.angle  = -90.0        # degrees, 0 = pointing right
        self.radius = SHIP_RADIUS
        self.size   = SHIP_SIZE
        self.lives  = STARTING_LIVES
        self.invincible_timer = 0
        self._moving      = False
        self.shield_energy  = float(SHIELD_MAX)
        self.shield_active  = False
        self.thrust_dots: list = []

    # ── Per-frame update ──────────────────────────────────────────────────────

    def update(self, tx: float, ty: float, dt: float = 1/60) -> None:
        """Move toward the cursor, update aim angle, manage shield energy."""
        dx   = tx - self.x
        dy   = ty - self.y
        dist = math.hypot(dx, dy)

        # Only move when cursor is outside the dead zone
        self._moving = dist > STOP_RADIUS
        if self._moving:
            self.x += (dx / dist) * SHIP_SPEED * dt * 60
            self.y += (dy / dist) * SHIP_SPEED * dt * 60
            # Emit a thrust trail dot from the nozzle position
            back = math.radians(self.angle + 180)
            ox   = self.x + math.cos(back) * self.size * 0.6
            oy   = self.y + math.sin(back) * self.size * 0.6
            self.thrust_dots.append(
                ThrustDot(ox, oy, math.cos(back) * 1.5, math.sin(back) * 1.5))

        # Only update aim when cursor is far enough for atan2 to be stable
        if dist > AIM_FREEZE_RADIUS:
            self.angle = math.degrees(math.atan2(dy, dx))

        # Age and cull expired thrust dots
        for d in list(self.thrust_dots):
            d.update()
            if not d.alive:
                self.thrust_dots.remove(d)

        # Shield: active while SHIFT is held and energy remains
        keys = pygame.key.get_pressed()
        self.shield_active = (keys[pygame.K_LSHIFT]
                              and self.shield_energy > 0
                              and not self.is_invincible)
        if self.shield_active:
            # Clamp to prevent negative energy
            self.shield_energy = max(0.0, self.shield_energy - SHIELD_DRAIN)
        else:
            # Clamp to prevent over-charge from power-up pickups
            self.shield_energy = min(float(SHIELD_MAX),
                                     self.shield_energy + SHIELD_RECHARGE)

    # ── Damage and respawn ────────────────────────────────────────────────────

    @property
    def is_invincible(self) -> bool:
        return self.invincible_timer > 0

    def take_hit(self) -> bool:
        """Register an incoming hit.
        Returns True if the shield absorbed it, False if a life was lost."""
        if self.shield_active:
            self.shield_energy = max(0.0, self.shield_energy - 80)
            return True   # absorbed — no life lost
        self.lives -= 1
        self.invincible_timer = INVINCIBILITY_FRAMES
        return False

    def tick_invincibility(self) -> None:
        """Count down the invincibility timer each frame."""
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

    def reset_position(self) -> None:
        """Teleport to screen centre and grant invincibility."""
        self.x = float(WIDTH  // 2)
        self.y = float(HEIGHT // 2)
        self.invincible_timer = INVINCIBILITY_FRAMES

    def hyperspace(self) -> None:
        """Teleport to a random position with brief invincibility.
        The caller is responsible for clamping coordinates in bounds."""
        self.x = random.uniform(80, WIDTH  - 80)
        self.y = random.uniform(80, HEIGHT - 80)
        self.invincible_timer = 40

    # ── Rendering ─────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface, frame: int = 0) -> None:
        """Draw thrust trail, then flame, then rocket body.

        During invincibility the ship blinks by skipping alternate
        6-frame windows — a classic visual cue that the player is safe.
        """
        for d in self.thrust_dots:
            d.draw(screen)

        # Skip every other 6-frame block while invincible (blinking effect)
        if self.is_invincible and (self.invincible_timer // 6) % 2 == 0:
            return

        rad   = math.radians(self.angle)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)
        perp  = rad + math.pi / 2
        s     = self.size

        # ── Rocket geometry ───────────────────────────────────────────────────
        nose  = (self.x + cos_r * s * 2.0,  self.y + sin_r * s * 2.0)
        rear  = (self.x - cos_r * s * 0.9,  self.y - sin_r * s * 0.9)
        b_l   = (self.x + math.cos(perp) * s * 0.55 - cos_r * s * 0.5,
                 self.y + math.sin(perp) * s * 0.55 - sin_r * s * 0.5)
        b_r   = (self.x - math.cos(perp) * s * 0.55 - cos_r * s * 0.5,
                 self.y - math.sin(perp) * s * 0.55 - sin_r * s * 0.5)

        # Swept fins at the rear
        fl_root = (self.x + math.cos(perp) * s * 0.45 - cos_r * s * 0.5,
                   self.y + math.sin(perp) * s * 0.45 - sin_r * s * 0.5)
        fl_tip  = (self.x + math.cos(perp) * s * 1.0  - cos_r * s * 1.1,
                   self.y + math.sin(perp) * s * 1.0  - sin_r * s * 1.1)
        fr_root = (self.x - math.cos(perp) * s * 0.45 - cos_r * s * 0.5,
                   self.y - math.sin(perp) * s * 0.45 - sin_r * s * 0.5)
        fr_tip  = (self.x - math.cos(perp) * s * 1.0  - cos_r * s * 1.1,
                   self.y - math.sin(perp) * s * 1.0  - sin_r * s * 1.1)

        # Nozzle origin: midpoint of rear edge, pushed past hull so flame clears body
        mx_r = (b_l[0] + b_r[0]) / 2
        my_r = (b_l[1] + b_r[1]) / 2
        ox   = mx_r + math.cos(rad + math.pi) * s * 0.4
        oy   = my_r + math.sin(rad + math.pi) * s * 0.4

        # Draw flame first so the body paints over the nozzle base
        self._draw_flame(screen, rad, frame, ox, oy, idle=not self._moving)

        # Shield bubble — pulsing ring, only when actively draining
        if self.shield_active and self.shield_energy > 0:
            pulse_r = int((self.radius + 14) + 3 * math.sin(frame * 0.15))
            pygame.draw.circle(screen, CYAN,
                               (int(self.x), int(self.y)), pulse_r, 2)

        # Fins
        pygame.draw.polygon(screen, (60, 100, 200), [fl_root, fl_tip, rear])
        pygame.draw.polygon(screen, WHITE,           [fl_root, fl_tip, rear], 1)
        pygame.draw.polygon(screen, (60, 100, 200), [fr_root, fr_tip, rear])
        pygame.draw.polygon(screen, WHITE,           [fr_root, fr_tip, rear], 1)

        # Main fuselage
        pygame.draw.polygon(screen, BLUE,  [nose, b_l, rear, b_r])
        pygame.draw.polygon(screen, WHITE, [nose, b_l, rear, b_r], 1)

        # Nose cone highlight
        mid_l = ((nose[0] + b_l[0]) / 2, (nose[1] + b_l[1]) / 2)
        mid_r = ((nose[0] + b_r[0]) / 2, (nose[1] + b_r[1]) / 2)
        pygame.draw.polygon(screen, (140, 200, 255), [nose, mid_l, mid_r])

        # Cockpit window
        win_x = int(self.x + cos_r * s * 0.9)
        win_y = int(self.y + sin_r * s * 0.9)
        pygame.draw.circle(screen, (180, 230, 255), (win_x, win_y), max(2, int(s * 0.18)))
        pygame.draw.circle(screen, WHITE,            (win_x, win_y), max(2, int(s * 0.18)), 1)

    def _draw_flame(self, screen: pygame.Surface, rad: float,
                    frame: int, ox: float, oy: float,
                    idle: bool = False) -> None:
        """Three concentric flame layers forming a teardrop shape.

        idle=True renders at 35% scale as a small flicker so the engine
        always looks live, even when the ship is hovering in place.
        """
        back  = rad + math.pi
        perp  = rad + math.pi / 2
        scale = 0.35 if idle else 1.0

        for lf, wf, colour in [
            (1.6,  0.55, FLAME_COLOURS[0]),   # outer layer — wide, orange
            (1.25, 0.35, FLAME_COLOURS[1]),   # middle layer — yellow
            (0.85, 0.18, FLAME_COLOURS[2]),   # core — narrow, near-white
        ]:
            flicker = 1.0 + 0.35 * math.sin(frame * 0.45 + lf)
            length  = self.size * lf * flicker * scale
            width   = self.size * wf * scale
            tip_f   = (ox + math.cos(back) * length, oy + math.sin(back) * length)
            l_pt    = (ox + math.cos(perp) * width,  oy + math.sin(perp) * width)
            r_pt    = (ox - math.cos(perp) * width,  oy - math.sin(perp) * width)
            pygame.draw.polygon(screen, colour, [tip_f, l_pt, r_pt])

    def draw_shield_bar(self, screen: pygame.Surface) -> None:
        """Render the shield energy bar at the bottom-left of the screen."""
        bw, bh = 140, 8
        bx, by = 12, HEIGHT - 28
        frac = max(0.0, min(1.0, self.shield_energy / SHIELD_MAX))
        pygame.draw.rect(screen, (30, 60, 60), (bx, by, bw, bh), border_radius=4)
        pygame.draw.rect(screen, CYAN, (bx, by, int(bw * frac), bh), border_radius=4)
        fnt = pygame.font.SysFont("monospace", 12)
        screen.blit(fnt.render("SHIELD  [SHIFT]", True, (80, 200, 200)), (bx, by - 16))


# ── Bullet ────────────────────────────────────────────────────────────────────

class Bullet:
    """A projectile fired by the ship.  Removed when it leaves the screen."""

    def __init__(self, x: float, y: float, angle: float, fast: bool = False):
        self.x      = float(x)
        self.y      = float(y)
        self.radius = BULLET_RADIUS
        spd = BULLET_SPEED * (1.5 if fast else 1.0)  # rapid-fire boosts speed
        rad = math.radians(angle)
        self.dx = math.cos(rad) * spd
        self.dy = math.sin(rad) * spd

    def move(self, dt: float = 1/60) -> None:
        """Advance the bullet by one dt-scaled step."""
        self.x += self.dx * dt * 60
        self.y += self.dy * dt * 60

    @property
    def off_screen(self) -> bool:
        return not (0 <= self.x <= WIDTH and 0 <= self.y <= HEIGHT)

    def draw(self, screen: pygame.Surface) -> None:
        pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE,  (int(self.x), int(self.y)), self.radius - 2)


# ── Asteroid ──────────────────────────────────────────────────────────────────

class Asteroid:
    """A spinning rock that can collide with the ship and bullets.

    Shape: vertex offsets are generated ONCE in __init__ so the shape
    is a rigid body — it rotates but never morphs (prevents the
    'morphing star' artefact caused by re-seeding each frame).

    split_depth controls fragmentation:
      0 – destroyed immediately, no fragments
      1 – splits into 2 medium fragments (depth 0 — won't split again)
      2 – splits into 2 medium (depth 1), each splits into 2 small (depth 0)

    Dynamic types (level 4+):
      normal  – standard behaviour, white outline
      fast    – 2× speed, slightly smaller, red outline
      heavy   – 0.5× speed, 2 hits required, dark outline + X crack
      zigzag  – changes direction every 60-120 frames, purple outline
    """

    def __init__(self, x: float, y: float, size: int, angle: float,
                 speed: float, palette: dict = None,
                 split_depth: int = 2, kind: str = "normal"):
        self.x           = float(x)
        self.y           = float(y)
        self.kind        = kind
        self.split_depth = split_depth
        self._palette    = palette or LEVEL_PALETTES["grey"]

        # Apply type-specific speed and size modifiers
        if kind == "fast":
            speed *= 2.0
            size   = max(int(size * 0.85), 10)
        elif kind == "heavy":
            speed *= 0.45

        self.hits_remaining = 2 if kind == "heavy" else 1
        self.size   = size
        self.speed  = speed
        self.flash_timer = 0   # frames of white hit-flash remaining

        rad     = math.radians(angle)
        self.dx = math.cos(rad) * speed
        self.dy = math.sin(rad) * speed

        self.colour       = self._pick_colour(self._palette)
        self._outline_col = {"fast":   (255, 80, 80),
                             "heavy":  (80, 80, 80),
                             "zigzag": (180, 80, 255)}.get(kind, WHITE)

        # Fixed vertex offsets — generated once, never change
        n = random.randint(7, 10)
        self._verts = []
        for i in range(n):
            base_a = (2 * math.pi / n) * i
            jitter = random.uniform(-0.18, 0.18) * (2 * math.pi / n)
            self._verts.append((base_a + jitter, random.uniform(0.70, 1.0)))

        self.rotation       = random.uniform(0, 2 * math.pi)
        self.rotation_speed = random.uniform(-0.022, 0.022)   # radians/frame
        self._zz_timer      = random.randint(60, 120)          # zigzag direction timer

    def _pick_colour(self, pal: dict) -> tuple:
        """Choose colour based on size band using the level's palette."""
        if self.size >= ASTEROID_LARGE_SIZE  - 4: return pal["large"]
        if self.size >= ASTEROID_MEDIUM_SIZE - 2: return pal["medium"]
        return pal["small"]

    def move(self, dt: float = 1/60) -> None:
        """Move, wrap at screen edges, advance rotation, tick flash timer."""
        if self.kind == "zigzag":
            self._zz_timer -= 1
            if self._zz_timer <= 0:
                # Deflect 60-120 degrees in a random direction
                self._zz_timer = random.randint(60, 120)
                ang = math.atan2(self.dy, self.dx) + random.uniform(
                    math.radians(60), math.radians(120)) * random.choice([-1, 1])
                self.dx = math.cos(ang) * self.speed
                self.dy = math.sin(ang) * self.speed

        self.x = (self.x + self.dx * dt * 60) % WIDTH
        self.y = (self.y + self.dy * dt * 60) % HEIGHT
        self.rotation += self.rotation_speed
        if self.flash_timer > 0:
            self.flash_timer -= 1

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the asteroid polygon using its stored fixed vertices.

        When flash_timer > 0 (just hit by a bullet) the fill is white,
        giving satisfying impact feedback for 4 frames.
        """
        pts = [
            (self.x + math.cos(self.rotation + a) * self.size * r,
             self.y + math.sin(self.rotation + a) * self.size * r)
            for a, r in self._verts
        ]
        draw_col = WHITE if self.flash_timer > 0 else self.colour
        pygame.draw.polygon(screen, draw_col, pts)
        pygame.draw.polygon(screen, self._outline_col, pts,
                            2 if self.kind == "heavy" else 1)

        # Heavy asteroids show an X crack to indicate they need a second hit
        if self.kind == "heavy" and self.hits_remaining == 2:
            cx, cy = int(self.x), int(self.y)
            cr = int(self.size * 0.4)
            pygame.draw.line(screen, (200, 200, 200), (cx-cr, cy-cr), (cx+cr, cy+cr), 1)
            pygame.draw.line(screen, (200, 200, 200), (cx+cr, cy-cr), (cx-cr, cy+cr), 1)

    def hit(self) -> bool:
        """Register a bullet hit.  Returns True when the asteroid is destroyed."""
        self.hits_remaining -= 1
        return self.hits_remaining <= 0

    def split(self) -> list:
        """Return fragment asteroids based on split_depth.

        depth 0 → no fragments (destroyed silently)
        depth 1 → two medium fragments (won't split further)
        depth 2 → two medium fragments that each split into two smalls
        """
        if self.split_depth == 0:
            return []
        child_depth = self.split_depth - 1
        child_size  = (ASTEROID_MEDIUM_SIZE if self.split_depth == 2
                       else ASTEROID_SMALL_SIZE)
        # Children travel slightly faster than parent — keeps the game lively
        spd = min(self.speed * random.uniform(1.1, 1.4), 9.0)
        return [
            Asteroid(self.x, self.y, child_size,
                     random.uniform(0, 360), spd,
                     self._palette, child_depth, "normal")
            for _ in range(2)
        ]


# ── MotherShip ────────────────────────────────────────────────────────────────

class MotherShip:
    """The UFO boss enemy.

    Drawn as a saucer (flat ellipse body + dome) with a red cannon spike
    that always rotates to face the player — making its aim direction clear.

    Difficulty scales per appearance so the player faces an escalating
    challenge rather than the same boss each time:
      Level 3: health 3, slow (0.7×), shoots infrequently
      Level 6: health 4, standard speed, standard rate
      Level 8: health 5, faster (1.15×), shoots frequently
    """

    SCORE_VALUE = 500   # bonus points awarded on destruction

    # Per-appearance difficulty lookup
    _APPEARANCE_HEALTH     = {3: 3, 6: 4, 8: 5}
    _APPEARANCE_SHOOT_MULT = {3: 1.4, 6: 1.0, 8: 0.7}   # multiplier on MOTHERSHIP_SHOOT_EVERY
    _APPEARANCE_SPEED_MULT = {3: 0.7, 6: 1.0, 8: 1.15}  # multiplier on MOTHERSHIP_SPEED

    def __init__(self, x: float, y: float, level: int):
        self.x      = float(x)
        self.y      = float(y)
        self.radius = 40
        self.health = self._APPEARANCE_HEALTH.get(level, max(3, level - 2))
        sm = self._APPEARANCE_SHOOT_MULT.get(level, 1.0)
        sp = self._APPEARANCE_SPEED_MULT.get(level, 1.0)
        self._speed       = MOTHERSHIP_SPEED * sp
        self._shoot_every = int(MOTHERSHIP_SHOOT_EVERY * sm)
        self.shoot_timer  = self._shoot_every // 2   # first shot comes mid-interval
        self.alive        = True
        self._level       = level
        self._aim         = 0.0   # radians — updated every frame toward player

    def update(self, tx: float, ty: float, dt: float = 1/60) -> list:
        """Move toward the player, update aim, and fire when timer expires.
        Returns a list of new MotherBullet objects (empty most frames)."""
        dx   = tx - self.x
        dy   = ty - self.y
        dist = math.hypot(dx, dy) or 1
        self._aim = math.atan2(dy, dx)   # update cannon direction each frame

        if dist > self.radius:
            self.x += (dx / dist) * self._speed * dt * 60
            self.y += (dy / dist) * self._speed * dt * 60

        # Wrap at edges so the Mother Ship can approach from any direction
        self.x %= WIDTH
        self.y %= HEIGHT

        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot_timer = self._shoot_every
            return [MotherBullet(self.x, self.y, math.degrees(self._aim))]
        return []

    def take_hit(self) -> bool:
        """Reduce health.  Returns True when health reaches zero."""
        self.health -= 1
        if self.health <= 0:
            self.alive = False
            return True
        return False

    def explode(self) -> list:
        """Return a ring of small asteroids flying outward on destruction.
        The ring only spawns if there are still other asteroids on screen —
        the caller checks this to avoid blocking the level-clear condition."""
        pal = level_palette(self._level)
        spd = 2.0 + self._level * 0.15
        return [
            Asteroid(self.x, self.y, ASTEROID_SMALL_SIZE,
                     (360 / MOTHERSHIP_RING_COUNT) * i,
                     spd + random.uniform(-0.3, 0.3),
                     pal, split_depth=0, kind="normal")
            for i in range(MOTHERSHIP_RING_COUNT)
        ]

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the UFO saucer: spike → body → dome → light → health bar."""
        cx, cy = int(self.x), int(self.y)
        r  = self.radius
        bh = r // 3     # body half-height (flat saucer shape)
        dr = r // 2     # dome radius

        aa   = self._aim
        perp = aa + math.pi / 2

        # Cannon spike drawn first so the body paints over its base
        slen  = r * 1.5
        sbase = r * 0.9
        sw    = r * 0.2
        s_tip = (self.x + math.cos(aa) * (sbase + slen),
                 self.y + math.sin(aa) * (sbase + slen))
        s_l   = (self.x + math.cos(aa) * sbase + math.cos(perp) * sw,
                 self.y + math.sin(aa) * sbase + math.sin(perp) * sw)
        s_r   = (self.x + math.cos(aa) * sbase - math.cos(perp) * sw,
                 self.y + math.sin(aa) * sbase - math.sin(perp) * sw)
        pygame.draw.polygon(screen, RED, [s_tip, s_l, s_r])

        # Saucer body and dome
        pygame.draw.ellipse(screen, (150, 0, 150), pygame.Rect(cx-r, cy-bh, r*2, bh*2))
        pygame.draw.ellipse(screen, WHITE,          pygame.Rect(cx-r, cy-bh, r*2, bh*2), 2)
        pygame.draw.ellipse(screen, (195, 55, 195), pygame.Rect(cx-dr, cy-bh-dr+3, dr*2, dr*2))
        pygame.draw.ellipse(screen, WHITE,          pygame.Rect(cx-dr, cy-bh-dr+3, dr*2, dr*2), 1)

        # Porthole light
        pygame.draw.circle(screen, (255, 100, 100), (cx, cy - bh // 2 - 2), 5)

        # Health bar — shows how many hits remain
        bw  = r * 2
        bx  = cx - r
        by  = cy - bh - dr - 16
        mhp = max(3, self._level)
        pygame.draw.rect(screen, (70, 0, 0),    (bx, by, bw, 6))
        pygame.draw.rect(screen, (210, 45, 45), (bx, by, int(bw * max(0, self.health / mhp)), 6))

        # Label above the health bar
        try:
            fnt = pygame.font.SysFont("monospace", 13)
            lbl = fnt.render("MOTHER SHIP", True, (220, 100, 220))
            screen.blit(lbl, lbl.get_rect(centerx=cx, bottom=by - 2))
        except Exception:
            pass


# ── MotherBullet ──────────────────────────────────────────────────────────────

class MotherBullet:
    """A slow homing projectile fired by the Mother Ship.

    Each frame the velocity is nudged slightly toward the player
    (soft homing), then clamped to a maximum speed so it is always
    possible to outmanoeuvre.
    """

    def __init__(self, x: float, y: float, angle: float):
        self.x      = float(x)
        self.y      = float(y)
        self.radius = 7
        rad     = math.radians(angle)
        self.dx = math.cos(rad) * 4.5
        self.dy = math.sin(rad) * 4.5

    def update(self, tx: float, ty: float, dt: float = 1/60) -> None:
        """Nudge velocity toward (tx, ty), clamp speed, then move."""
        dx   = tx - self.x
        dy   = ty - self.y
        dist = math.hypot(dx, dy) or 1
        self.dx += (dx / dist) * MOTHERSHIP_HOME_STR
        self.dy += (dy / dist) * MOTHERSHIP_HOME_STR
        spd = math.hypot(self.dx, self.dy)
        if spd > 4.5:
            self.dx = self.dx / spd * 4.5
            self.dy = self.dy / spd * 4.5
        self.x += self.dx * dt * 60
        self.y += self.dy * dt * 60

    @property
    def off_screen(self) -> bool:
        return not (-60 <= self.x <= WIDTH + 60 and -60 <= self.y <= HEIGHT + 60)

    def draw(self, screen: pygame.Surface) -> None:
        pygame.draw.circle(screen, (210, 40, 210), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE,           (int(self.x), int(self.y)), self.radius, 1)


# ── Collision helpers ─────────────────────────────────────────────────────────

def circles_overlap(ax: float, ay: float, ar: float,
                    bx: float, by: float, br: float) -> bool:
    """Return True when two circles overlap (distance < sum of radii)."""
    return math.hypot(ax - bx, ay - by) < ar + br


def resolve_asteroid_collision(a1: "Asteroid", a2: "Asteroid") -> None:
    """Apply a 1-D elastic impulse between two overlapping asteroids,
    then push them apart so they no longer overlap (positional correction).

    Physics summary
    ---------------
    1. Compute the unit normal vector along the line joining centres.
    2. Project both velocities onto that normal.
    3. Guard: skip if asteroids are already separating (v1n - v2n <= 0).
    4. Apply the 1-D elastic collision formula:
         nv1 = (v1*(m1-m2) + 2*m2*v2) / (m1+m2)
         nv2 = (v2*(m2-m1) + 2*m1*v1) / (m1+m2)
       where mass = size² (proportional to cross-sectional area).
    5. Reconstruct full 2-D velocities.
    6. Positional correction: push both asteroids apart by half the
       overlap distance so they exit the collision cleanly.

    Complexity: O(1) per pair.  The caller iterates all pairs → O(n²).
    Acceptable for n ≤ ~30; spatial hashing would reduce to O(n) but
    would be premature optimisation at this scale.
    """
    nx   = a2.x - a1.x
    ny   = a2.y - a1.y
    dist = math.hypot(nx, ny)
    if dist == 0:
        return   # identical positions — skip to avoid division by zero
    nx /= dist
    ny /= dist

    # Mass proportional to area (size²) so larger rocks deflect smaller ones more
    m1  = a1.size ** 2
    m2  = a2.size ** 2
    v1n = a1.dx * nx + a1.dy * ny
    v2n = a2.dx * nx + a2.dy * ny

    if v1n - v2n <= 0:
        return   # already separating — no impulse needed

    nv1 = (v1n * (m1 - m2) + 2 * m2 * v2n) / (m1 + m2)
    nv2 = (v2n * (m2 - m1) + 2 * m1 * v1n) / (m1 + m2)

    a1.dx += (nv1 - v1n) * nx
    a1.dy += (nv1 - v1n) * ny
    a2.dx += (nv2 - v2n) * nx
    a2.dy += (nv2 - v2n) * ny

    # Push apart to eliminate overlap (static resolution)
    overlap = (a1.size + a2.size) - dist
    a1.x   -= nx * overlap * 0.5
    a1.y   -= ny * overlap * 0.5
    a2.x   += nx * overlap * 0.5
    a2.y   += ny * overlap * 0.5