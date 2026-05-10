"""
particles.py
Visual-only effects: explosion debris and a twinkling parallax starfield.

Neither class contains any game logic or collision data — they are
purely cosmetic and can be removed without affecting gameplay.
"""

import math
import random
import pygame

from constants import WIDTH, HEIGHT, WHITE, YELLOW, ORANGE, RED


class Particle:
    """A single short-lived debris fragment from an asteroid explosion.

    Each particle has a random velocity and fades to black over its
    lifetime, giving the impression of glowing hot debris cooling down.
    """

    def __init__(self, x: float, y: float, colour: tuple):
        self.x   = x
        self.y   = y
        # Scatter in a random direction at a random speed
        angle    = random.uniform(0, 2 * math.pi)
        speed    = random.uniform(1.0, 5.0)
        self.dx  = math.cos(angle) * speed
        self.dy  = math.sin(angle) * speed
        self.lifetime     = random.randint(20, 45)
        self.max_lifetime = self.lifetime
        self.colour       = colour
        self.radius       = random.randint(2, 4)

    @property
    def alive(self) -> bool:
        return self.lifetime > 0

# Apply motion and slowly reduce velocity to simulate energy dissipation
    def update(self) -> None:
        """Move the particle and apply light friction so it slows down."""
        self.x        += self.dx
        self.y        += self.dy
        self.dx       *= 0.96   # friction
        self.dy       *= 0.96
        self.lifetime -= 1

# Fade particle colour and size over lifetime for smooth disappearance
    def draw(self, screen: pygame.Surface) -> None:
        """Draw fading from full colour to black as lifetime runs out."""
        frac   = self.lifetime / self.max_lifetime
        colour = tuple(int(c * frac) for c in self.colour)
        radius = max(1, int(self.radius * frac))
        pygame.draw.circle(screen, colour, (int(self.x), int(self.y)), radius)


def spawn_explosion(x: float, y: float, size: int) -> list:
    """Return a burst of Particles centred at (x, y).

    Larger asteroids produce more particles and use warmer colours
    to suggest a bigger, hotter explosion.
    """
    count = max(8, size // 3)

    if size > 40:
        colours = [ORANGE, RED, (220, 80, 20)]
    elif size > 20:
        colours = [YELLOW, ORANGE, (200, 160, 60)]
    else:
        colours = [WHITE, YELLOW, (180, 220, 255)]

    return [Particle(x, y, random.choice(colours)) for _ in range(count)]


class Starfield:
    """Two-layer parallax starfield drawn behind all game objects.

    Stars are generated once and stored.  Each frame they twinkle
    by varying brightness through a per-star sine wave — giving a
    subtle living feel without any movement.

    Layer 0 (far)  — many small, dim stars
    Layer 1 (near) — fewer larger, brighter stars
    """

    _LAYERS = [
        # (count, min_radius, max_radius, min_brightness, max_brightness)
        (120, 1, 1,  80, 160),   # far layer
        (40,  1, 2, 160, 255),   # near layer
    ]

    def __init__(self):
        # Pre-generate all stars once so draw() is cheap every frame
        self._stars = []
        for count, rmin, rmax, bmin, bmax in self._LAYERS:
            for _ in range(count):
                self._stars.append({
                    "x":     random.randint(0, WIDTH),
                    "y":     random.randint(0, HEIGHT),
                    "r":     random.randint(rmin, rmax),
                    "b":     random.randint(bmin, bmax),
                    "phase": random.uniform(0, 2 * math.pi),   # twinkle offset
                    "speed": random.uniform(0.03, 0.08),        # twinkle rate
                })

    def draw(self, screen: pygame.Surface, frame: int) -> None:
        """Draw all stars, each pulsing gently at its own rate."""
        for s in self._stars:
            pulse = math.sin(frame * s["speed"] + s["phase"])
            b     = max(40, min(255, int(s["b"] + pulse * 30)))
            pygame.draw.circle(screen, (b, b, b), (s["x"], s["y"]), s["r"])