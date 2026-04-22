import pygame
import random
import math

# INITIALISATION

# Initialise Pygame and its internal modules
pygame.init()

# Screen and timing parameters
WIDTH, HEIGHT = 1200, 800
FPS = 60

# Object sizes
SHIP_RADIUS = 15
ASTEROID_RADIUS = 30
BULLET_RADIUS = 8
ASTEROID_SPLIT_SIZE = 20
SHIP_SIZE = 40

# Movement threshold used to prevent jitter when ship reaches cursor
MOVE_THRESHOLD = 1

# Colour definitions (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED   = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE  = (0, 0, 255)

# Create game window
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AstroCrash")

# Clock object used to control frame rate
clock = pygame.time.Clock()

# Ship class

class Ship:
    """
    Represents the player-controlled ship.
    Handles movement, rotation, drawing and player lives.
    """
    def __init__(self, x, y, angle, speed):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.size = SHIP_SIZE
        self.lives = 3  # Number of lives for the player

    def move_towards(self, target_x, target_y):
        """
        Moves the ship smoothly towards the mouse cursor.
        """
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx**2 + dy**2)

        # Move only if far enough from cursor to avoid vibration
        if distance > MOVE_THRESHOLD:
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed

    def rotate(self, direction):
        """
        Rotates the ship by updating its angle.
        """
        self.angle += direction

    def draw(self):
        """
        Draws the ship as a triangle pointing in the current direction.
        """
        points = [
            (self.x + math.cos(math.radians(self.angle)) * self.size * 2,
             self.y + math.sin(math.radians(self.angle)) * self.size * 2),
            (self.x + math.cos(math.radians(self.angle + 120)) * self.size,
             self.y + math.sin(math.radians(self.angle + 120)) * self.size),
            (self.x + math.cos(math.radians(self.angle + 240)) * self.size,
             self.y + math.sin(math.radians(self.angle + 240)) * self.size)
        ]
        pygame.draw.polygon(screen, BLUE, points)

# Bullet class

class Bullet:
    """
    Represents a bullet fired from the ship.
    """
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.speed = 10

        # Directional velocity components
        self.dx = math.cos(math.radians(angle)) * self.speed
        self.dy = math.sin(math.radians(angle)) * self.speed

    def move(self):
        """
        Updates bullet position.
        """
        self.x += self.dx
        self.y += self.dy

    def draw(self):
        """
        Draws the bullet as a small circle.
        """
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), BULLET_RADIUS)

# Asteroid class

class Asteroid:
    """
    Represents an asteroid that moves across the screen.
    """
    def __init__(self, x, y, size, angle, speed):
        self.x = x
        self.y = y
        self.size = size
        self.speed = speed

        # Directional velocity components
        self.dx = math.cos(math.radians(angle)) * speed
        self.dy = math.sin(math.radians(angle)) * speed

    def move(self):
        """
        Moves asteroid and wraps position at screen edges.
        """
        self.x = (self.x + self.dx) % WIDTH
        self.y = (self.y + self.dy) % HEIGHT

    def draw(self):
        """
        Draws the asteroid as a circle.
        """
        pygame.draw.circle(screen, GREEN, (int(self.x), int(self.y)), self.size)

    def split(self):
        """
        Splits a large asteroid into two smaller asteroids when hit.
        """
        if self.size > ASTEROID_SPLIT_SIZE:
            new_size = self.size // 2
            return [
                Asteroid(self.x, self.y, new_size, random.randint(0, 360), random.randint(1, 3)),
                Asteroid(self.x, self.y, new_size, random.randint(0, 360), random.randint(1, 3))
            ]
        return []

# Game object initialisation

ship = Ship(WIDTH // 2, HEIGHT // 2, 0, 8)
bullets = []

asteroids = [
    Asteroid(
        random.randint(0, WIDTH),
        random.randint(0, HEIGHT),
        random.randint(30, 60),
        random.randint(0, 360),
        random.randint(1, 3)
    ) for _ in range(5)
]

score = 0  # Player score

pygame.mouse.set_visible(False)
running = True
shooting = False

# Main game loop

while running:
    clock.tick(FPS)
    screen.fill(BLACK)

    # ---------------- Event handling ----------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not shooting:
            bullets.append(Bullet(ship.x, ship.y, ship.angle))
            shooting = True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            shooting = False

    # ---------------- Ship control ----------------
    mouse_x, mouse_y = pygame.mouse.get_pos()
    ship.move_towards(mouse_x, mouse_y)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_q]:
        ship.rotate(-5)
    if keys[pygame.K_e]:
        ship.rotate(5)

    # ---------------- Bullet updates ----------------
    for bullet in bullets[:]:
        bullet.move()
        bullet.draw()
        if bullet.x < 0 or bullet.x > WIDTH or bullet.y < 0 or bullet.y > HEIGHT:
            bullets.remove(bullet)

    # ---------------- Asteroid updates ----------------
    new_asteroids = []

    for asteroid in asteroids[:]:
        asteroid.move()
        asteroid.draw()

        # Bullet–asteroid collision
        for bullet in bullets[:]:
            if math.hypot(asteroid.x - bullet.x, asteroid.y - bullet.y) < asteroid.size + BULLET_RADIUS:
                score += asteroid.size  # Larger asteroids give more points
                asteroids.remove(asteroid)
                bullets.remove(bullet)
                new_asteroids.extend(asteroid.split())
                break

        # Ship–asteroid collision
        if math.hypot(asteroid.x - ship.x, asteroid.y - ship.y) < asteroid.size + SHIP_RADIUS:
            ship.lives -= 1
            ship.x, ship.y = WIDTH // 2, HEIGHT // 2
            asteroids.remove(asteroid)
            if ship.lives <= 0:
                running = False

    asteroids.extend(new_asteroids)

    # ---------------- Rendering ----------------
    ship.draw()

    # Draw player lives as red indicators
    for i in range(ship.lives):
        pygame.draw.circle(screen, RED, (20 + i * 20, 20), 6)

    # Draw score as white blocks (avoids font dependency)
    for i in range(score // 10):
        pygame.draw.rect(screen, WHITE, (WIDTH - 20 - i * 12, 15, 10, 10))

    pygame.display.update()

<<<<<<< HEAD
pygame.quit()
=======
pygame.quit()
>>>>>>> e9cfe16 (Add ship-asteroid collision and player lives)
