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

# Fonts
<<<<<<< HEAD
#pygame.font.init()
#font = pygame.font.SysFont("Arial", 24)
=======
# font = pygame.font.SysFont("Arial", 24)
>>>>>>> c46fd06 (Get AstroCrash running and fix pygame environment issues)

# Ship class (includes movement and rotation)
class Ship:
    def __init__(self, x, y, angle, speed):  # Ship has x,y coordinates, angle, speed and size
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.size = SHIP_SIZE

    def move_towards(self, target_x, target_y):  # Function that moves the ship towards target (later this will be used to follow the mouse)
        dx, dy = target_x - self.x, target_y - self.y
        distance = math.sqrt(dx**2 + dy**2)
        if distance > MOVE_THRESHOLD:  # Only move if the ship is far enough from the mouse, wrong setting may cause "vibration" effect
            dx, dy = dx / distance * self.speed, dy / distance * self.speed
            self.x += dx
            self.y += dy

    def rotate(self, direction):    # Function that rotates the ship (changes its angle)
        self.angle += direction

    def draw(self):
        points = [
            (self.x + math.cos(math.radians(self.angle)) * self.size * 2,
             self.y + math.sin(math.radians(self.angle)) * self.size * 2),  # Top of ship
            (self.x + math.cos(math.radians(self.angle + 120)) * self.size / 1.5,
             self.y + math.sin(math.radians(self.angle + 120)) * self.size / 1.5),  # Bottom left
            (self.x + math.cos(math.radians(self.angle + 240)) * self.size / 1.5,
             self.y + math.sin(math.radians(self.angle + 240)) * self.size / 1.5)  # Bottom right
        ]
        pygame.draw.polygon(screen, BLUE, points)


# Bullet class (handles movement)
class Bullet:
    def __init__(self, x, y, angle):   # Bullet has x,y coordinates and an angle
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 10  # Increased speed for visibility, should speed be defined here?
        self.dx = math.cos(math.radians(angle)) * self.speed
        self.dy = math.sin(math.radians(angle)) * self.speed

    def move(self):    # Move bullet
        self.x += self.dx
        self.y += self.dy

    def draw(self):
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), BULLET_RADIUS)


# Asteroid class (handles movement and splitting)
class Asteroid:
    def __init__(self, x, y, size, angle, speed):  # Asteroid has x,y coordinates, angle, angle and speed
        self.x = x
        self.y = y
        self.size = size
        self.angle = angle
        self.speed = speed
        self.dx = math.cos(math.radians(angle)) * self.speed
        self.dy = math.sin(math.radians(angle)) * self.speed

    def move(self):         # Asteroids wrap around the screen, ship and bullets shouldn't, unless you think it makes the game better!
        self.x += self.dx
        self.y += self.dy
        # Wrap around the screen edges
        if self.x < 0:
            self.x = WIDTH
        elif self.x > WIDTH:
            self.x = 0
        if self.y < 0:
            self.y = HEIGHT
        elif self.y > HEIGHT:
            self.y = 0

    def draw(self):  # Draw
        pygame.draw.circle(screen, GREEN, (int(self.x), int(self.y)), self.size)

    def split(self):    # Split asteroid when hit and return two new asteroids, new asteroids should be smaller
        if self.size > ASTEROID_SPLIT_SIZE:
            new_size = self.size // 2  # Reduce asteroid size upon splitting
            new_speed = random.randint(1, 3)
            return [
                Asteroid(self.x, self.y, new_size, self.angle + random.randint(-45, 45), new_speed),
                Asteroid(self.x, self.y, new_size, self.angle + random.randint(-45, 45), new_speed)
            ]
        return []


# Initialize the ship, bullets lists, and asteroids list
ship = Ship(WIDTH // 2, HEIGHT // 2, 0, 10)  # Should this be hard-coded like this?
bullets = []
asteroids = []

for _ in range(5):
    asteroids.append(
        Asteroid(
            random.randint(0, WIDTH),
            random.randint(0, HEIGHT),
            random.randint(30, 60),
            random.randint(0, 360),
            random.randint(1, 3)
        )
    )


# Main game loop - infinite WHILE loop tied to your processor clock, be careful!
clock = pygame.time.Clock()
running = True
shooting = False
pygame.mouse.set_visible(False)  # Hide the cursor and create a custom red dot cursor

while running:
    screen.fill(BLACK)  # Background screen color

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False  # This stops the inf loop (closing the game) - extremely important, do not alter unless you know what you are doing

        # Shoot on left click (only one bullet at a time)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left-click
                if not shooting:  # Prevent multiple bullets per click
                    bullets.append(Bullet(ship.x, ship.y, ship.angle))
                    shooting = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left-click
                shooting = False

    # Get mouse position
    mouse_x, mouse_y = pygame.mouse.get_pos()

    # Move the ship towards the mouse
    ship.move_towards(mouse_x, mouse_y)

    # Handle ship rotation (Q and E keys)
    keys = pygame.key.get_pressed()
    if keys[pygame.K_q]:
        ship.rotate(-5)  # Rotate counterclockwise
    if keys[pygame.K_e]:
        ship.rotate(5)  # Rotate clockwise

    # Move and draw bullets
    for bullet in bullets[:]:  # Use a slice to avoid modifying the list while iterating
        bullet.move()
        bullet.draw()
        if bullet.x < 0 or bullet.x > WIDTH or bullet.y < 0 or bullet.y > HEIGHT:
            bullets.remove(bullet)

    # Move and draw asteroids
    asteroids_to_remove = []  # List of asteroids to remove
    new_asteroids = []  # List of new asteroids to add

    for asteroid in asteroids:
        asteroid.move()
        asteroid.draw()
        # Check for collisions with bullets
        for bullet in bullets[:]:
            if math.sqrt((asteroid.x - bullet.x)**2 + (asteroid.y - bullet.y)**2) < asteroid.size + BULLET_RADIUS:
                # Mark the asteroid for removal and split it into new asteroids
                asteroids_to_remove.append(asteroid)
                bullets.remove(bullet)
                new_asteroids.extend(asteroid.split())
                break

    # After the loop, remove destroyed asteroids and add new ones from splitting
    for asteroid in asteroids_to_remove:
        if asteroid in asteroids:
            asteroids.remove(asteroid)
    asteroids.extend(new_asteroids)

    # Draw the ship
    ship.draw()

    # Draw the custom cursor (red dot)
    pygame.draw.circle(screen, RED, (mouse_x, mouse_y), 2)  # Custom cursor size set to 2

    # Update the display
    pygame.display.update()

    # Limit the frame rate
    clock.tick(FPS)

# Quit the game
pygame.quit()
