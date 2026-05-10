"""
victory.py
----------
Animated victory screen shown after clearing all 8 levels.

Visual elements
---------------
  - Animated starfield (reused from particles.py)
  - Earth globe drawn procedurally (ocean ellipse + continent blobs
    + atmosphere glow + cloud wisps)
  - Scrolling story text revealing the ending
  - Pulsing "MISSION COMPLETE" title
  - Animated score display
  - "Play Again" prompt
"""

import math, random
import pygame

from constants import WIDTH, HEIGHT, WHITE, BLACK, YELLOW, BLUE, CYAN, GREEN

# ── Story lines ───────────────────────────────────────────────────────────────
_LINES = [
    "",
    "Transmission received — Earth Command.",
    "",
    "Commander Reyes…",
    "We thought we'd lost you.",
    "",
    "The asteroid field has been neutralised.",
    "The Mother Ship fleet has been destroyed.",
    "The Kepler Belt is clear.",
    "",
    "You did it alone, three light-years from home,",
    "with nothing but your cannons and your nerve.",
    "",
    "Eight sectors. Hundreds of threats.",
    "Not a single one got through.",
    "",
    "Earth is safe.",
    "",
    "The cities are lit.",
    "The skies are clear.",
    "Children are looking up at the stars tonight",
    "— the same stars you fought to protect.",
    "",
    "Your name will be carved into the Hall of Pilots.",
    "",
    "Come home, Commander.",
    "You've earned it.",
    "",
    "                    — Admiral Chen, Earth Command",
]

# Continent shape data: list of (cx, cy, rx, ry, angle) relative to globe centre
# These are approximate blobs that together suggest the world map
_CONTINENTS = [
    # North America
    (-0.22, -0.20, 0.18, 0.22, -20),
    # South America
    (-0.12,  0.18, 0.10, 0.18,  10),
    # Europe / Africa
    ( 0.08, -0.05, 0.10, 0.28,   5),
    # Asia
    ( 0.28, -0.18, 0.22, 0.20,  15),
    # Australia
    ( 0.30,  0.25, 0.10, 0.08,  20),
    # Antarctica
    ( 0.00,  0.42, 0.30, 0.06,   0),
]


class VictoryScreen:
    """
    Call update() + draw() every frame.
    Returns True from update() when the player presses SPACE / R.
    """

    def __init__(self, score: int, high_score: int,
                 level_reached: int = 8, asteroids_destroyed: int = 0):
        self.score               = score
        self.high_score          = high_score
        self.level_reached       = level_reached
        self.asteroids_destroyed = asteroids_destroyed
        self._frame     = 0
        self._scroll    = float(HEIGHT)   # text start y (scrolls up)
        self._font_xl   = pygame.font.SysFont("monospace", 44, bold=True)
        self._font_lg   = pygame.font.SysFont("monospace", 28, bold=True)
        self._font_md   = pygame.font.SysFont("monospace", 20)
        self._font_sm   = pygame.font.SysFont("monospace", 16)
        # Pre-render story lines
        self._rendered  = [
            self._font_sm.render(line, True, (180, 220, 180))
            for line in _LINES
        ]
        # Stars
        random.seed(99)
        self._stars = [
            (random.randint(0, WIDTH), random.randint(0, HEIGHT),
             random.randint(1, 2), random.uniform(60, 200))
            for _ in range(180)
        ]
        random.seed()  # reset seed

    def update(self) -> bool:
        self._frame  += 1
        self._scroll -= 0.6   # scroll speed
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                import sys; pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_r,
                                 pygame.K_RETURN):
                    return True
        return False

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(BLACK)
        self._draw_stars(screen)
        self._draw_earth(screen)
        self._draw_title(screen)
        self._draw_score(screen)
        self._draw_story(screen)
        self._draw_prompt(screen)

    # ── Private drawing helpers ───────────────────────────────────────────────

    def _draw_stars(self, screen):
        for x, y, r, b in self._stars:
            pulse = b + 30 * math.sin(self._frame * 0.04 + x)
            c = max(40, min(255, int(pulse)))
            pygame.draw.circle(screen, (c, c, c), (x, y), r)

    def _draw_earth(self, screen):
        """
        Draw Earth as a procedural globe:
          1. Atmosphere glow (large translucent blue circle)
          2. Ocean (solid blue ellipse)
          3. Continent blobs (green ellipses clipped to globe)
          4. Cloud wisps (thin white arcs)
          5. Highlight (top-left shine)
        """
        # Position: right half of screen, vertically centred
        cx = int(WIDTH * 0.72)
        cy = int(HEIGHT * 0.48)
        R  = 155   # globe radius

        # Atmosphere glow — concentric fading circles
        for ring in range(18, 0, -2):
            alpha = int(12 * (19 - ring) / 18)
            glow  = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(glow, (60, 140, 255, alpha),
                               (cx, cy), R + ring * 3)
            screen.blit(glow, (0, 0))

        # Ocean
        pygame.draw.circle(screen, (20, 60, 160), (cx, cy), R)

        # Continent blobs — clip to globe using a mask surface
        continent_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for (rx_f, ry_f, ew_f, eh_f, ang) in _CONTINENTS:
            ecx  = int(cx + rx_f * R)
            ecy  = int(cy + ry_f * R)
            ew   = int(ew_f * R * 2)
            eh   = int(eh_f * R * 2)
            rect = pygame.Rect(ecx - ew//2, ecy - eh//2, ew, eh)
            # Rotate using a temp surface
            blob = pygame.Surface((ew + 4, eh + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(blob, (34, 120, 50, 255),
                                blob.get_rect())
            blob = pygame.transform.rotate(blob, ang)
            bx   = ecx - blob.get_width()  // 2
            by   = ecy - blob.get_height() // 2
            continent_surf.blit(blob, (bx, by))

        # Mask continents to the globe circle
        mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (cx, cy), R)
        continent_surf.blit(mask, (0, 0),
                            special_flags=pygame.BLEND_RGBA_MIN)
        screen.blit(continent_surf, (0, 0))

        # Cloud wisps (slowly rotating)
        cloud_angle = self._frame * 0.15
        for i in range(5):
            a  = math.radians(cloud_angle + i * 72)
            wx = cx + int(math.cos(a) * R * 0.6)
            wy = cy + int(math.sin(a) * R * 0.55)
            pygame.draw.ellipse(screen, (200, 220, 255),
                                pygame.Rect(wx - 22, wy - 8, 44, 14))

        # Globe outline
        pygame.draw.circle(screen, (80, 140, 255), (cx, cy), R, 2)

        # Highlight shine (top-left)
        shine = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(shine, (255, 255, 255, 35),
                           (cx - R//3, cy - R//3), R // 2)
        screen.blit(shine, (0, 0))

        # "EARTH" label beneath globe
        lbl = self._font_sm.render("— EARTH —", True, (100, 180, 255))
        screen.blit(lbl, lbl.get_rect(centerx=cx, top=cy + R + 10))

    def _draw_title(self, screen):
        pulse = 1.0 + 0.06 * math.sin(self._frame * 0.06)
        text  = "★  MISSION COMPLETE  ★"
        # Glow layer
        glow_col = (int(80 * pulse), int(180 * pulse), int(80 * pulse))
        surf_g    = self._font_xl.render(text, True, glow_col)
        screen.blit(surf_g, surf_g.get_rect(centerx=WIDTH // 3, top=38))
        # Main layer
        surf = self._font_xl.render(text, True, (150, 255, 150))
        screen.blit(surf, surf.get_rect(centerx=WIDTH // 3, top=40))

    def _draw_score(self, screen):
        y = 100
        s1 = self._font_md.render(f"Final Score :  {self.score:06d}", True, WHITE)
        screen.blit(s1, s1.get_rect(centerx=WIDTH // 3, top=y))
        if self.score >= self.high_score and self.high_score > 0:
            s2 = self._font_md.render("✦  NEW RECORD  ✦", True, YELLOW)
            screen.blit(s2, s2.get_rect(centerx=WIDTH // 3, top=y + 30))
        else:
            s2 = self._font_sm.render(f"Best :  {self.high_score:06d}",
                                      True, (120, 120, 120))
            screen.blit(s2, s2.get_rect(centerx=WIDTH // 3, top=y + 32))
        stats = self._font_sm.render(
            f"Levels cleared: {self.level_reached}   |   Asteroids destroyed: {self.asteroids_destroyed}",
            True, (140, 200, 140))
        screen.blit(stats, stats.get_rect(centerx=WIDTH // 3, top=y + 62))

    def _draw_story(self, screen):
        """Scroll story lines up from the bottom of the left panel."""
        line_h = 26
        clip   = pygame.Rect(0, 150, int(WIDTH * 0.52), HEIGHT - 160)
        screen.set_clip(clip)
        y = int(self._scroll)
        for surf in self._rendered:
            if 140 < y < HEIGHT:
                screen.blit(surf, surf.get_rect(centerx=WIDTH // 3, top=y))
            y += line_h
        screen.set_clip(None)

    def _draw_prompt(self, screen):
        if (self._frame // 40) % 2 == 0:
            s = self._font_md.render("SPACE  ·  play again", True,
                                     (100, 220, 100))
            # Place under the globe (right side), always visible
            globe_cx = int(WIDTH * 0.72)
            globe_bottom = int(HEIGHT * 0.48) + 155 + 10 + 24  # cy + R + label
            screen.blit(s, s.get_rect(centerx=globe_cx, top=globe_bottom + 16))