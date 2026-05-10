"""
tests/test_physics.py
---------------------
Unit tests for AstroCrash physics functions.

Run from the project root:
    python -m unittest discover tests/ -v

Tests cover
-----------
  circles_overlap            - overlap / non-overlap / symmetry / concentric
  resolve_asteroid_collision - velocity change, separation, momentum
                               conservation, no action when separating,
                               zero-distance safety
  Asteroid.split()           - fragment count and depth propagation
  Asteroid.hit()             - hit counting for normal and heavy asteroids
  Ship.take_hit()            - lives deduction, shield absorption, energy clamp
"""

import sys, os, math, unittest, types

# ── Minimal pygame stub so tests run without a display ────────────────────────
pg_stub = types.ModuleType("pygame")
pg_stub.font = types.SimpleNamespace(
    init=lambda: None,
    SysFont=lambda *a, **kw: None,
)
pg_stub.key     = types.SimpleNamespace(get_pressed=lambda: [])
pg_stub.Rect    = lambda *a, **kw: None
pg_stub.Surface = type("Surface", (), {})   # minimal Surface class for type hints
sys.modules["pygame"] = pg_stub

# Allow imports from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from entities import (
    circles_overlap, resolve_asteroid_collision,
    Asteroid, Ship,
)


# ── circles_overlap ───────────────────────────────────────────────────────────

class TestCirclesOverlap(unittest.TestCase):

    def test_overlapping_circles(self):
        """Two circles whose centres are closer than sum of radii must overlap."""
        self.assertTrue(circles_overlap(0, 0, 10, 5, 0, 10))

    def test_non_overlapping_circles(self):
        """Well-separated circles must not overlap."""
        self.assertFalse(circles_overlap(0, 0, 5, 100, 0, 5))

    def test_touching_not_overlap(self):
        """Circles exactly touching (dist == sum of radii) should not overlap."""
        self.assertFalse(circles_overlap(0, 0, 10, 20, 0, 10))

    def test_concentric_circles(self):
        """One circle inside another must overlap."""
        self.assertTrue(circles_overlap(0, 0, 20, 0, 0, 5))

    def test_symmetry(self):
        """Overlap detection must be symmetric."""
        self.assertEqual(
            circles_overlap(0, 0, 10, 5, 0, 10),
            circles_overlap(5, 0, 10, 0, 0, 10),
        )


# ── resolve_asteroid_collision ────────────────────────────────────────────────

class TestResolveAsteroidCollision(unittest.TestCase):

    def _overlapping_pair(self, size1=20, size2=20):
        """Two overlapping asteroids on a head-on course."""
        a1 = Asteroid(0,  0, size1, 0, 1, split_depth=0)
        a2 = Asteroid(15, 0, size2, 0, 1, split_depth=0)
        a1.dx, a1.dy =  2.0, 0.0
        a2.dx, a2.dy = -2.0, 0.0
        return a1, a2

    def test_velocities_change_on_collision(self):
        """After collision, velocity must change for at least one asteroid."""
        a1, a2 = self._overlapping_pair()
        old = a1.dx
        resolve_asteroid_collision(a1, a2)
        self.assertNotAlmostEqual(a1.dx, old,
            msg="a1.dx should change after head-on collision")

    def test_no_overlap_after_resolution(self):
        """Asteroids must not remain overlapping after resolution."""
        a1, a2 = self._overlapping_pair()
        resolve_asteroid_collision(a1, a2)
        dist = math.hypot(a1.x - a2.x, a1.y - a2.y)
        self.assertGreaterEqual(dist, a1.size + a2.size - 0.1,
            msg="Asteroids should be separated after resolution")

    def test_momentum_conserved(self):
        """Total momentum (mass × velocity) must be conserved."""
        a1, a2 = self._overlapping_pair(size1=20, size2=30)
        m1, m2 = a1.size ** 2, a2.size ** 2
        px_before = m1 * a1.dx + m2 * a2.dx
        py_before = m1 * a1.dy + m2 * a2.dy
        resolve_asteroid_collision(a1, a2)
        px_after = m1 * a1.dx + m2 * a2.dx
        py_after = m1 * a1.dy + m2 * a2.dy
        self.assertAlmostEqual(px_before, px_after, places=5)
        self.assertAlmostEqual(py_before, py_after, places=5)

    def test_no_action_when_separating(self):
        """Asteroids already moving apart must not receive an impulse."""
        a1 = Asteroid(0,  0, 20, 0, 1, split_depth=0)
        a2 = Asteroid(15, 0, 20, 0, 1, split_depth=0)
        a1.dx, a1.dy = -2.0, 0.0   # moving left (away from a2)
        a2.dx, a2.dy =  2.0, 0.0   # moving right (away from a1)
        old = a1.dx
        resolve_asteroid_collision(a1, a2)
        self.assertAlmostEqual(a1.dx, old,
            msg="No impulse when asteroids are already separating")

    def test_zero_distance_no_crash(self):
        """Identical positions must not raise an exception."""
        a1 = Asteroid(50, 50, 20, 0, 1, split_depth=0)
        a2 = Asteroid(50, 50, 20, 0, 1, split_depth=0)
        try:
            resolve_asteroid_collision(a1, a2)
        except Exception as e:
            self.fail(f"Raised {e} on zero distance")


# ── Asteroid.split() ──────────────────────────────────────────────────────────

class TestAsteroidSplit(unittest.TestCase):

    def test_depth0_no_fragments(self):
        a = Asteroid(100, 100, 36, 0, 1, split_depth=0)
        self.assertEqual(a.split(), [])

    def test_depth1_two_fragments(self):
        a = Asteroid(100, 100, 36, 0, 1, split_depth=1)
        frags = a.split()
        self.assertEqual(len(frags), 2)
        for f in frags:
            self.assertEqual(f.split_depth, 0)

    def test_depth2_two_fragments_depth1(self):
        a = Asteroid(100, 100, 36, 0, 1, split_depth=2)
        frags = a.split()
        self.assertEqual(len(frags), 2)
        for f in frags:
            self.assertEqual(f.split_depth, 1)

    def test_children_at_least_as_fast(self):
        a = Asteroid(100, 100, 36, 0, 2.0, split_depth=2)
        for f in a.split():
            self.assertGreaterEqual(f.speed, a.speed * 0.9)


# ── Asteroid.hit() ────────────────────────────────────────────────────────────

class TestAsteroidHit(unittest.TestCase):

    def test_normal_one_hit(self):
        a = Asteroid(0, 0, 36, 0, 1, kind="normal")
        self.assertTrue(a.hit())

    def test_heavy_survives_first(self):
        a = Asteroid(0, 0, 36, 0, 1, kind="heavy")
        self.assertFalse(a.hit())

    def test_heavy_destroyed_second(self):
        a = Asteroid(0, 0, 36, 0, 1, kind="heavy")
        a.hit()
        self.assertTrue(a.hit())


# ── Ship.take_hit() ───────────────────────────────────────────────────────────

class TestShipTakeHit(unittest.TestCase):

    def test_hit_reduces_lives(self):
        s = Ship(100, 100)
        s.shield_active = False
        initial = s.lives
        absorbed = s.take_hit()
        self.assertFalse(absorbed)
        self.assertEqual(s.lives, initial - 1)

    def test_shield_absorbs_hit(self):
        s = Ship(100, 100)
        s.shield_active = True
        s.shield_energy = 200
        initial = s.lives
        self.assertTrue(s.take_hit())
        self.assertEqual(s.lives, initial)

    def test_shield_energy_decreases(self):
        s = Ship(100, 100)
        s.shield_active = True
        s.shield_energy = 200
        s.take_hit()
        self.assertLess(s.shield_energy, 200)

    def test_shield_energy_never_negative(self):
        s = Ship(100, 100)
        s.shield_active = True
        s.shield_energy = 10
        s.take_hit()
        self.assertGreaterEqual(s.shield_energy, 0)

    def test_invincibility_set_after_hit(self):
        s = Ship(100, 100)
        s.shield_active = False
        s.take_hit()
        self.assertGreater(s.invincible_timer, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)