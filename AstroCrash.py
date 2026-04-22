import pygame
import random
import math

# Initialize Pygame
pygame.init()

# Define constants for the new larger screen size
WIDTH, HEIGHT = 1200, 800  # Screen size
FPS = 60
SHIP_RADIUS = 15
ASTEROID_RADIUS = 30
BULLET_RADIUS = 8           # Increased bullet size
ASTEROID_SPLIT_SIZE = 20    # Increased size for the smallest asteroid
SHIP_SIZE = 40
MOVE_THRESHOLD = 1          # Distance threshold for ship to move

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Set up the game screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Asteroid Game")

# Ship class (includes movement and rotation)
class Ship:
    def __init__(self, x, y, angle, speed):  # Ship has x,y coordinates, angle, speed and size
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.size = SHIP_SIZE
        self.lives = 3  # Player lives

    def move_towards(self, target_x, target_y):  # Function that moves the ship towards target
        dx, dy = target_x - self.x, target_y - self.y
        distance = math.sqrt(dx**2 + dy**2)
        if distance > MOVE_THRESHOLD:
            dx, dy = dx / distance * self.speed, dy / distance * self.speed
            self.x += dx
            self.y += dy

    def rotate(self, direction):    # Function that rotates the ship
        self.angle += direction

    def draw(self):
        points = [
            (self.x + math.cos(math.radians(self.angle)) * self.size * 2,
             self.y + math.sin(math.radians(self.angle)) * self.size * 2),
            (self.x + math.cos(math.radians(self.angle + 120)) * self.size,
             self.y + math.sin(math.radians(self.angle + 120)) * self.size),
            (self.x + math.cos(math.radians(self.angle + 240)) * self.size,
             self.y + math.sin(math.radians(self.angle + 240)) * self.size)
        ]
        pygame.draw.polygon(screen, BLUE, points)

# Bullet class (handles movement)
class Bullet:
    def __init__(self, x, y, angle):   # Bullet has x,y coordinates and an angle
        self.x = x
        self.y = y
        self.speed = 10
        self.dx = math.cos(math.radians(angle)) * self.speed
        self.dy = math.sin(math.radians(angle)) * self.speed

    def move(self):
        self.x += self.dx
        self.y += self.dy

    def draw(self):
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), BULLET_RADIUS)

# Asteroid class (handles movement and splitting)
class Asteroid:
    def __init__(self, x, y, size, angle, speed):
        self.x = x
        self.y = y
        self.size = size
        self.speed = speed
        self.dx = math.cos(math.radians(angle)) * speed
        self.dy = math.sin(math.radians(angle)) * speed

    def move(self):
        self.x = (self.x + self.dx) % WIDTH
        self.y = (self.y + self.dy) % HEIGHT

    def draw(self):
        pygame.draw.circle(screen, GREEN, (int(self.x), int(self.y)), self.size)

    def split(self):
        if self.size > ASTEROID_SPLIT_SIZE:
            new_size = self.size // 2
            return [
                Asteroid(self.x, self.y, new_size, random.randint(0, 360), random.randint(1, 3)),
                Asteroid(self.x, self.y, new_size, random.randint(0, 360), random.randint(1, 3))
            ]
        return []

# Initialize objects
ship = Ship(WIDTH // 2, HEIGHT // 2, 0, 8)
bullets = []
asteroids = [
    Asteroid(random.randint(0, WIDTH),
             random.randint(0, HEIGHT),
             random.randint(30, 60),
             random.randint(0, 360),
             random.randint(1, 3))
    for _ in range(5)
]

pygame.mouse.set_visible(False)
clock = pygame.time.Clock()
running = True
shooting = False

# Main game loop
while running:
    clock.tick(FPS)
    screen.fill(BLACK)

    # Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not shooting:
            bullets.append(Bullet(ship.x, ship.y, ship.angle))
            shooting = True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            shooting = False

    # Ship control
    mouse_x, mouse_y = pygame.mouse.get_pos()
    ship.move_towards(mouse_x, mouse_y)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_q]:
        ship.rotate(-5)
    if keys[pygame.K_e]:
        ship.rotate(5)

    # Bullets
    for bullet in bullets[:]:
        bullet.move()
        bullet.draw()
        if bullet.x < 0 or bullet.x > WIDTH or bullet.y < 0 or bullet.y > HEIGHT:
            bullets.remove(bullet)

    # Asteroids
    new_asteroids = []
    for asteroid in asteroids[:]:
        asteroid.move()
        asteroid.draw()

        # Bullet collision
        for bullet in bullets[:]:
            if math.hypot(asteroid.x - bullet.x, asteroid.y - bullet.y) < asteroid.size + BULLET_RADIUS:
                asteroids.remove(asteroid)
                bullets.remove(bullet)
                new_asteroids.extend(asteroid.split())
                break

        # Ship collision
        if math.hypot(asteroid.x - ship.x, asteroid.y - ship.y) < asteroid.size + SHIP_RADIUS:
            ship.lives -= 1
            ship.x, ship.y = WIDTH // 2, HEIGHT // 2
            asteroids.remove(asteroid)
            if ship.lives <= 0:
                running = False

    asteroids.extend(new_asteroids)

    # Draw ship
    ship.draw()

    # Draw lives as red dots
    for i in range(ship.lives):
        pygame.draw.circle(screen, RED, (20 + i * 20, 20), 6)

    pygame.display.update()

<<<<<<< HEAD
pygame.quit()
=======
pygame.quit()
>>>>>>> e9cfe16 (Add ship-asteroid collision and player lives)
