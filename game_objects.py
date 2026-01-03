import pygame
import random
import time
from collections import deque
import physics

# Basic Colors
RED = (255, 50, 50)
GREEN = (50, 255, 50)
WHITE = (255, 255, 255)
ORANGE = (255, 165, 0)

class Blade:
    def __init__(self):
        # Stores (x, y, timestamp)
        self.points = deque(maxlen=20) 
        self.color = (0, 255, 255) # Cyan for high contrast
        self.min_width = 5
        self.max_width = 25
        self.fade_speed = 5 # How fast trail fades

    def update(self, x, y):
        current_time = time.time()
        self.points.append((x, y, current_time))
        
        # Remove old points (older than 0.2s) to keep trail short & responsive
        while self.points:
            if current_time - self.points[0][2] > 0.15:
                self.points.popleft()
            else:
                break
                
    def draw(self, screen):
        if len(self.points) < 2:
            return
            
        # Draw connected lines with varying thickness
        # Newest points = thickest
        points_list = list(self.points)
        for i in range(len(points_list) - 1):
            p1 = points_list[i]
            p2 = points_list[i+1]
            
            # Ratio: 0 (oldest) to 1 (newest)
            ratio = i / len(points_list)
            width = int(self.min_width + (self.max_width - self.min_width) * ratio)
            
            # Draw line segment
            # Note: Pygame lines with width > 1 have gaps at corners. 
            # Ideally draw circles at joints, but lines are fast.
            start_pos = (p1[0], p1[1])
            end_pos = (p2[0], p2[1])
            pygame.draw.line(screen, self.color, start_pos, end_pos, width)
            pygame.draw.circle(screen, self.color, end_pos, width // 2)

    def get_segments(self):
        """Returns list of line segments ((x1,y1), (x2,y2)) currently active."""
        segments = []
        pts = list(self.points)
        for i in range(len(pts) - 1):
            segments.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])))
        return segments

import os

class Fruit(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, fruit_type=None):
        super().__init__()
        
        # Available types in assets
        types = ["apple", "banana", "coconut", "orange", "pineapple", "watermelon"]
        if fruit_type is None:
            self.fruit_type = random.choice(types)
        else:
            self.fruit_type = fruit_type

        # Load Image
        # Try loading small version for performance if exists, else normal
        try:
            path = f"assets/fruits/{self.fruit_type}_small.png"
            if not os.path.exists(path):
                path = f"assets/fruits/{self.fruit_type}.png"
            
            raw_image = pygame.image.load(path).convert_alpha()
            # If standard ones are huge (300KB+ pngs might be large), we might need scaling.
            # Based on file sizes, _small are ~10KB, likely icons. Large are ~300KB.
            
            if "small" not in path:
                # Scale down large images to decent game size
                self.image = pygame.transform.scale(raw_image, (85, 85))
            else:
                self.image = raw_image
                
        except Exception as e:
            # Fallback
            # print(f"Error loading {self.fruit_type}: {e}")
            self.radius = 35
            self.color = random.choice([RED, ORANGE, GREEN])
            self.image = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
            pygame.draw.circle(self.image, self.color, (self.radius, self.radius), self.radius)

        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.radius = self.rect.width // 2 # Approx radius for collision
        self.screen_h = height
        
        # Physics
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.vel_x = random.uniform(-1.5, 1.5) # Even slower horizontal
        self.vel_y = random.uniform(-10, -7.5) # Tuned for low gravity
        self.gravity = 0.08                    # 40% slower feel (Floaty)
        
    def update(self):
        self.vel_y += self.gravity
        self.pos_x += self.vel_x
        self.pos_y += self.vel_y
        
        self.rect.centerx = int(self.pos_x)
        self.rect.centery = int(self.pos_y)
        
        if self.rect.top > self.screen_h:
            self.kill()
            
    def check_slice(self, segments):
        """
        Check collision against a list of blade segments.
        Using swept-circle (capsule) collision.
        """
        center = (self.pos_x, self.pos_y)
        for p1, p2 in segments:
            # We treat the blade as having a thickness
            # Let's say effective blade radius is 5px
            if physics.check_capsule_circle_collision(p1, p2, 15, center, self.radius): # Increased blade radius for leniency
                return True
        return False

class SlicedFruit(pygame.sprite.Sprite):
    def __init__(self, x, y, fruit_type, half_id):
        super().__init__()
        # Try loading specific half
        try:
            # e.g. assets/fruits/apple_half_1_small.png
            base = f"assets/fruits/{fruit_type}_half_{half_id}"
            path_small = f"{base}_small.png"
            path_large = f"{base}.png"
            
            path = path_small if os.path.exists(path_small) else path_large
            
            if os.path.exists(path):
                 raw = pygame.image.load(path).convert_alpha()
                 if "small" not in path:
                     self.image = pygame.transform.scale(raw, (42, 85)) # generic half size
                 else:
                     self.image = raw
            else:
                 raise FileNotFoundError(f"Half image not found: {path}")
        except Exception as e:
            print(f"SlicedFruit load error for {fruit_type} half {half_id}: {e}")
            # Fallback
            self.image = pygame.Surface((35, 35), pygame.SRCALPHA)
            pygame.draw.arc(self.image, GREEN, (0,0,35,35), 0, 3.14, 20)          
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        
        # Physics to fly apart
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.gravity = 0.12 # Slow fall
        
        # Push apart based on ID
        if half_id == 1:
            self.vel_x = random.uniform(-4, -1)
            self.angle_speed = 2
        else:
            self.vel_x = random.uniform(1, 4)
            self.angle_speed = -2
            
        self.vel_y = random.uniform(-3, -1) # Little pop up
        
        # Rotation logic
        self.original_image = self.image
        self.angle = 0
        self.alpha = 255 # For fading if we want (optional)

    def update(self):
        self.vel_y += self.gravity
        self.pos_x += self.vel_x
        self.pos_y += self.vel_y
        
        # Rotate
        self.angle += self.angle_speed
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect(center=(self.pos_x, self.pos_y))
        
        if self.rect.top > 800: # Cleanup
            self.kill()

class Bomb(Fruit):
    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, "bomb")
        try:
            path = "assets/fruits/bomb_small.png"
            if not os.path.exists(path):
                 path = "assets/fruits/bomb.png"
            
            self.image = pygame.image.load(path).convert_alpha()
            if "small" not in path:
                 self.image = pygame.transform.scale(self.image, (100, 100))
            
            self.radius = self.image.get_width() // 2
        except Exception as e:
            print(f"Bomb load error: {e}")
            self.radius = 40
            self.image = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.circle(self.image, (50, 50, 50), (40, 40), 40)
            pygame.draw.circle(self.image, RED, (40, 40), 10) # Fuse
        
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.radius = self.rect.width // 2

class Explosion(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        try:
            # Use specific explosion asset
            path = "assets/vfx/explosion_small.png"
            if not os.path.exists(path):
                 path = "assets/vfx/explosion.png"
            
            self.image = pygame.image.load(path).convert_alpha()
            self.image = pygame.transform.scale(self.image, (150, 150)) # big boom
        except:
            self.image = pygame.Surface((100, 100))
            self.image.fill(RED)
            
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.timer = 30 # frames (0.5 sec at 60fps)
        self.original_image = self.image

    def update(self):
        self.timer -= 1
        # Simple fade
        alpha = int((self.timer / 30) * 255)
        self.image.set_alpha(alpha)
        
        if self.timer <= 0:
            self.kill()

class SplashEffect(pygame.sprite.Sprite):
    # Fruit to splash color mapping
    FRUIT_SPLASH_MAP = {
        "apple": "red",
        "watermelon": "red",
        "banana": "yellow",
        "pineapple": "yellow",
        "orange": "orange",
        "coconut": "transparent"
    }
    
    def __init__(self, x, y, fruit_type, velocity=0):
        super().__init__()
        
        # Determine splash color
        splash_color = self.FRUIT_SPLASH_MAP.get(fruit_type, "transparent")
        
        # Choose size variant based on velocity
        # High velocity (fast slice) = bigger splash
        if velocity > 400:
            size_variant = ""  # Use large splash
            scale_size = (180, 180)
        else:
            size_variant = "_small"
            scale_size = (120, 120)
        
        # Load splash image
        try:
            path = f"assets/vfx/splash_{splash_color}{size_variant}.png"
            if not os.path.exists(path):
                # Fallback to small if large doesn't exist
                path = f"assets/vfx/splash_{splash_color}_small.png"
                scale_size = (120, 120)
            
            raw_image = pygame.image.load(path).convert_alpha()
            self.image = pygame.transform.scale(raw_image, scale_size)
            self.original_image = self.image.copy()
            
        except Exception as e:
            # Fallback to colored circle
            self.image = pygame.Surface((100, 100), pygame.SRCALPHA)
            color_map = {
                "red": (255, 50, 50),
                "yellow": (255, 255, 50),
                "orange": (255, 165, 0)
            }
            color = color_map.get(splash_color, (200, 200, 200))
            pygame.draw.circle(self.image, (*color, 150), (50, 50), 50)
            self.original_image = self.image.copy()
        
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        
        # Animation properties
        self.lifetime = 20  # frames (~0.33 sec at 60fps)
        self.age = 0
        
        # Slight random rotation for variety
        angle = random.randint(-15, 15)
        self.image = pygame.transform.rotate(self.original_image, angle)
        self.rect = self.image.get_rect(center=(x, y))
        
    def update(self):
        self.age += 1
        
        # Fade out
        alpha = int(255 * (1 - self.age / self.lifetime))
        if alpha < 0:
            alpha = 0
            
        # Create faded version
        self.image = self.original_image.copy()
        self.image.set_alpha(alpha)
        
        if self.age >= self.lifetime:
            self.kill()
