# AstroCrash

AstroCrash is an arcade-style asteroid shooting game built in Python using the pygame library. Inspired by the classic Asteroids game, it extends the core concept into a fully structured system with multiple levels, physics-based interactions, and modular architecture.

---

## Overview

AstroCrash transforms a basic, non-functional starting point into a complete and playable system. The project focuses on clean software design, correctness, and extensibility while delivering an engaging gameplay experience.

The game features a finite-state architecture, real-time physics simulation, progressive difficulty, and additional mechanics such as power-ups and enemy behaviour.

---

## Features

### Core Gameplay

- Mouse-controlled ship movement with smooth directional targeting
- Shooting mechanics with cooldown and bullet limits
- Asteroid splitting system (large → medium → small)
- Elastic asteroid–asteroid collisions with momentum conservation

### Progression System

- Eight progressively challenging levels
- Configurable level definitions (spawn count, speed, special behaviour)
- Dynamic difficulty scaling

### Player Mechanics

- Lives system with invincibility frames
- Shield system with energy management
- Hyperspace teleport with risk factor

### Advanced Features

- Power-ups:
  - Rapid fire
  - Shield recharge
  - Extra life
- Enemy system:
  - Mother Ship with homing attacks and scaling difficulty
- Combo-based scoring system

### Visual and UX Enhancements

- Particle system for asteroid explosions
- Parallax starfield background
- HUD displaying score, lives, level, and power-up status
- Dynamic in-game commentary feedback
- Level transition overlays and game-over screen
- Animated victory screen with procedural graphics

### Engineering Features

- Modular codebase with single-responsibility design
- Finite-state machine for game control
- Delta-time physics for frame-rate independence
- Unit tests for physics and core mechanics

---

## Controls

| Input | Action |
|---|---|
| Mouse | Move ship |
| Q / E | Rotate ship |
| Left Click | Fire bullets |
| Shift | Activate shield |
| H | Hyperspace |
| P | Pause / Resume |
| Space | Start / Continue |
| R | Restart (game over) |

---

## Project Structure

```
astrocrash-pygame/
├── AstroCrash.py       Main entry point, game loop, and finite-state machine
├── entities.py         Ship, Bullet, Asteroid, MotherShip, PowerUp classes
│                       and elastic collision physics helpers
├── constants.py        All global parameters: sizes, colours, physics values
├── spawner.py          Asteroid wave generation (level-scaled, type-aware)
├── hud.py              HUD and overlay rendering: score, lives, screens
├── particles.py        Particle effects for explosions and thrust
├── commentary.py       Dynamic in-game commentary system
├── victory.py          Animated victory screen
├── highscore.py        High score load/save logic
├── highscore.txt       Persisted high score
└── test_physics.py     Unit tests for physics and gameplay mechanics
```

---

## Requirements

- Python 3.8 or later
- pygame

---

## Installation and Running

```bash
pip install pygame
python AstroCrash.py
```

---

## Testing

The project includes a unit test suite for validating physics and gameplay logic.

```bash
python -m unittest discover tests/ -v
```

The tests cover:

- Collision detection
- Elastic collision behaviour
- Asteroid splitting logic
- Ship damage and shield mechanics

---

## Gameplay Notes

**Asteroids** spawn in waves at the edges of the screen. Destroying a large asteroid produces two medium fragments; each medium produces two small ones. Small asteroids are destroyed outright.

**Special asteroid types** appear from level 4 onward:

- Fast — moves at twice the normal speed, slightly smaller, red outline
- Heavy — requires two hits, marked with an X crack, dark outline
- Zigzag — deflects direction randomly every 1–2 seconds, purple outline

**The MotherShip** appears at levels 3, 6, and 8. It homes in on the player and fires slow homing projectiles. Its health, speed, and fire rate all increase with each appearance. Destroying it yields 500 points and scatters a ring of small asteroids.

**Power-ups** drop occasionally from destroyed asteroids and drift across the screen:

- RF (Rapid Fire) — triples fire rate for 6 seconds
- SH (Shield) — instantly refills shield energy
- +1 (Extra Life) — adds one life, up to a maximum of 5

**The shield** drains while Shift is held. A hit while the shield is active costs energy rather than a life. Energy recharges automatically when the shield is inactive.

---

## Design Highlights

**Modular Architecture** — Each component is isolated into its own module, making the system straightforward to extend and maintain.

**Finite-State Machine** — Clear separation between gameplay states (playing, paused, game over, victory) keeps control flow predictable.

**Physics Correctness** — Elastic collision logic preserves momentum and applies positional correction to prevent overlap artefacts.

**Frame-Rate Independence** — Delta-time scaling ensures consistent gameplay speed across different hardware.
