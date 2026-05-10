# AstroCrash

An asteroids-style arcade game built with Python and pygame.

## Project Structure

```
AstroCrash/
├── AstroCrash.py   – Main entry point and game loop
├── constants.py    – All global parameters (sizes, colours, physics values)
├── entities.py     – Ship, Bullet, Asteroid classes + elastic collision helper
├── spawner.py      – Asteroid wave generation (level-scaled)
├── hud.py          – All HUD and overlay rendering (score, lives, screens)
└── README.md
```

## Features

- Mouse-driven ship movement with Q/E rotation
- Left-click shooting with auto-removing off-screen bullets
- Asteroid splitting on bullet hit (large → 2 × medium → 2 × small)
- **Elastic asteroid-asteroid collisions** with momentum conservation
- Player lives with invincibility frames and flashing feedback
- Progressive level system – more asteroids, faster speeds each wave
- Level-clear and game-over overlays
- Colour-coded asteroids by size
- Score and lives HUD with rendered fonts

## Controls

| Input | Action |
|-------|--------|
| Mouse | Move ship |
| Q | Rotate left |
| E | Rotate right |
| Left Click | Shoot |
| SPACE | Start game |
| R | Restart (from game-over screen) |

## Requirements

- Python 3.8+
- pygame

## Run

```bash
pip install pygame
python AstroCrash.py
```
