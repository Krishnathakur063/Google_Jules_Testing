import pygame

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
PLAYER_SPEED = 5
GRAVITY = 1
JUMP_STRENGTH = -20

# --- Platform Class ---
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.Surface([width, height])
        self.image.fill(GREEN)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

# --- Player Class ---
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([40, 50])
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH / 2
        self.rect.bottom = SCREEN_HEIGHT - 40 # Start on the ground
        self.velocity_y = 0
        self.on_ground = False

    def update(self, platforms):
        # Apply gravity
        self.velocity_y += GRAVITY
        self.rect.y += self.velocity_y
        self.on_ground = False

        # Collision detection for platforms
        collided_platforms = pygame.sprite.spritecollide(self, platforms, False)
        for platform in collided_platforms:
            if self.velocity_y > 0: # If falling
                self.rect.bottom = platform.rect.top
                self.velocity_y = 0
                self.on_ground = True
                break

        # Move left/right
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.rect.x -= PLAYER_SPEED
        if keys[pygame.K_RIGHT]:
            self.rect.x += PLAYER_SPEED

        # Keep player on screen
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

    def jump(self):
        if self.on_ground:
            self.velocity_y = JUMP_STRENGTH

def main():
    """
    Main function to run the game.
    """
    # --- Initialization ---
    pygame.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Jules's Platformer")

    clock = pygame.time.Clock()

    # --- Sprites ---
    all_sprites = pygame.sprite.Group()
    platforms = pygame.sprite.Group()
    player = Player()
    all_sprites.add(player)

    # Create platforms
    level = [
        (0, SCREEN_HEIGHT - 40, SCREEN_WIDTH, 40), # Ground
        (200, SCREEN_HEIGHT - 150, 150, 20),
        (450, SCREEN_HEIGHT - 300, 150, 20),
    ]

    for plat_data in level:
        platform = Platform(*plat_data)
        platforms.add(platform)
        all_sprites.add(platform)

    # --- Game Loop ---
    running = True
    while running:
        # Set the frame rate
        clock.tick(60)

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.jump()

        # --- Update ---
        all_sprites.update(platforms)

        # --- Drawing ---
        screen.fill(BLACK)
        all_sprites.draw(screen)

        # --- Update the display ---
        pygame.display.flip()

    # --- Quit ---
    pygame.quit()

if __name__ == "__main__":
    main()
