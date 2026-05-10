"""
commentary.py
Dynamic in-game commentary system.

The Commentary class watches for gameplay events and displays
short fading messages at the bottom of the screen — making the
game feel responsive and alive without interrupting play.
"""

import random
import pygame

from constants import WIDTH, HEIGHT, WHITE, YELLOW, RED, ORANGE, LIGHT_GREY

# ── Message pools ─────────────────────────────────────────────────────────────
# Each trigger randomly picks from its pool so messages don't repeat.

_NEAR_MISS = [
    "Nice dodge!",
    "Too close for comfort…",
    "You felt the wind on that one!",
    "Barely scraped through!",
    "Reflexes of a pilot!",
]
_GOT_HIT = [
    "Ouch, that hurt!",
    "Hull breach detected!",
    "Direct hit — shake it off!",
    "They got you — don't let it happen again!",
    "Systems damaged!",
]
_STREAK = [
    "On fire!  Keep going!",
    "Incredible accuracy!",
    "You're unstoppable!",
    "Boom boom boom!",
    "The asteroids don't stand a chance!",
]
_LOW_HEALTH = [
    "Last life — don't blow it!",
    "One hit left.  Be careful!",
    "Critical condition — fly smart!",
    "Your ship is barely holding together!",
]
_MOTHERSHIP = [
    "⚠  MOTHER SHIP DETECTED!",
    "⚠  Enemy vessel approaching!",
    "⚠  Alien command ship spotted!",
]
_LEVEL_CLEAR = [
    "Sector cleared!  Well done!",
    "Wave destroyed!  Advancing…",
    "They're all gone.  For now.",
    "Outstanding piloting!",
]
_BIG_SHOT = [
    "Big rock down!",
    "Direct hit!",
    "Excellent shot!",
    "Bullseye!",
]

# A near-miss is triggered when an asteroid passes within this distance
NEAR_MISS_DIST = 55  # pixels


class Commentary:
    """Tracks game events and shows timed fading messages on screen.

    At most two messages are shown simultaneously — newest at the top.
    A kill streak triggers a special message after 4 quick kills.
    """

    _DURATION    = 160   # frames each message stays visible
    _MAX_SHOWN   = 2     # maximum messages on screen at once
    _STREAK_GAP  = 90    # frames between kills that count as a streak

    def __init__(self):
        self._messages          = []   # list of [text, timer, colour]
        self._streak            = 0
        self._streak_timer      = 0
        self._near_miss_cooldown = 0   # prevents spam when orbiting close
        self._ms_announced      = False

    # ── Event triggers ────────────────────────────────────────────────────────

    def on_near_miss(self) -> None:
        """Called when an asteroid passes very close without hitting."""
        if self._near_miss_cooldown <= 0:
            self._push(random.choice(_NEAR_MISS), YELLOW)
            self._near_miss_cooldown = 90  # 1.5 s cooldown

    def on_hit(self, lives_remaining: int) -> None:
        """Called when the ship takes a hit (not absorbed by shield)."""
        if lives_remaining <= 1:
            self._push(random.choice(_LOW_HEALTH), RED)
        else:
            self._push(random.choice(_GOT_HIT), (255, 120, 120))

    def on_asteroid_killed(self, size: int) -> None:
        """Called each time an asteroid is destroyed by a bullet."""
        self._streak      += 1
        self._streak_timer = self._STREAK_GAP
        if self._streak >= 4:
            self._push(random.choice(_STREAK), ORANGE)
            self._streak = 0
        elif size >= 34:
            # Only comment on large rocks — smalls would spam the screen
            self._push(random.choice(_BIG_SHOT), LIGHT_GREY)

    def on_mothership_appear(self) -> None:
        """Called the first time the Mother Ship becomes active."""
        if not self._ms_announced:
            self._push(random.choice(_MOTHERSHIP), (220, 80, 220))
            self._ms_announced = True

    def on_mothership_only(self) -> None:
        """Called when all asteroids are gone but the Mother Ship remains."""
        self._push("Destroy the Mother Ship to clear the sector!", (220, 80, 220))

    def on_level_clear(self) -> None:
        """Called when the wave is fully cleared."""
        self._push(random.choice(_LEVEL_CLEAR), (100, 220, 100))
        self._ms_announced = False  # reset so the warning fires next MS level

    def reset(self) -> None:
        """Clear all messages and counters — used on game restart."""
        self._messages.clear()
        self._streak       = 0
        self._ms_announced = False

    # ── Per-frame update ──────────────────────────────────────────────────────

    def tick(self) -> None:
        """Age all active messages by one frame and decay streak timer."""
        self._messages = [m for m in self._messages if m[1] > 0]
        for m in self._messages:
            m[1] -= 1
        if self._streak_timer > 0:
            self._streak_timer -= 1
        else:
            self._streak = 0   # streak broken — reset counter
        if self._near_miss_cooldown > 0:
            self._near_miss_cooldown -= 1

    # ── Rendering ─────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the most recent messages, stacked above the bottom edge."""
        font  = pygame.font.SysFont("monospace", 20, bold=True)
        shown = self._messages[-self._MAX_SHOWN:]
        for i, (text, timer, colour) in enumerate(reversed(shown)):
            surf = font.render(text, True, colour)
            surf.set_alpha(min(255, timer * 6))   # fade out in last ~27 frames
            y = HEIGHT - 40 - i * 30
            screen.blit(surf, surf.get_rect(centerx=WIDTH // 2, centery=y))

    # ── Internal ──────────────────────────────────────────────────────────────

    def _push(self, text: str, colour: tuple) -> None:
        """Add a message to the queue, avoiding immediate duplicates."""
        if self._messages and self._messages[-1][0] == text:
            return
        self._messages.append([text, self._DURATION, colour])
        # Keep the queue bounded to prevent memory growth
        if len(self._messages) > 8:
            self._messages.pop(0)