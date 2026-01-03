import pygame
import sys
import random
import cv2
import numpy as np

# Modules
from audio_manager import AudioManager
from input_manager import MouseInput, HandInput
from ui_manager import SceneManager
from game_engine import ClassicMode, SurvivalMode
from game_objects import Blade, Fruit, Bomb, SlicedFruit, Explosion, SplashEffect

# Colors
WHITE = (255, 255, 255)

# Config
WIDTH, HEIGHT = 960, 720 # Increased render scale
FPS = 60
MIN_CUT_VELOCITY = 150 # Rescaled 

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Fruit Ninja Final")
    clock = pygame.time.Clock()
    
    # Systems
    audio = AudioManager()
    ui = SceneManager(WIDTH, HEIGHT)
    
    # Load Backgrounds
    try:
        # Menu Background
        bg_raw = pygame.image.load("assets/background/game_background.jpg").convert()
        bg_img = pygame.transform.scale(bg_raw, (WIDTH, HEIGHT))
        
        # Gameplay Background
        gp_raw = pygame.image.load("assets/background/Game_Playing_image.jpg").convert()
        gameplay_bg_img = pygame.transform.scale(gp_raw, (WIDTH, HEIGHT))
        
        # Darken both
        dark = pygame.Surface((WIDTH, HEIGHT))
        dark.set_alpha(80) # 30% dark
        dark.fill((0, 0, 0))
        
        bg_img.blit(dark, (0,0))
        gameplay_bg_img.blit(dark, (0,0))
        
    except Exception as e:
        print(f"Background load error: {e}")
        bg_img = pygame.Surface((WIDTH, HEIGHT))
        bg_img.fill((50, 50, 50))
        gameplay_bg_img = bg_img

    # Game State Variables
    input_provider = None
    game_mode = None
    blade = Blade()
    
    all_sprites = pygame.sprite.Group()
    fruits = pygame.sprite.Group() # Only active fruits (not slices or bombs)
    
    # VFX State
    shake_timer = 0
    
    # Start Music
    audio.play_music("menu")
    
    running = True
    while running:
        mx, my = pygame.mouse.get_pos()
        click = False
        
        # Shake Logic
        shake_x, shake_y = 0, 0
        if shake_timer > 0:
            shake_timer -= 1
            shake_x = random.randint(-5, 5)
            shake_y = random.randint(-5, 5)

        # Event Loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    click = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and ui.current_scene == "GAME":
                    ui.is_paused = not ui.is_paused
                    
        # --- SCENE LOGIC ---
        
        if ui.current_scene == "MENU":
            screen.blit(bg_img, (0,0))
            action = ui.handle_input("MENU", mx, my, click)
            ui.draw_menu(screen)
            if action == "GOTO_MODE":
                ui.push_scene("MODE_SEL")
                audio.play_sfx("start")

        elif ui.current_scene == "MODE_SEL":
            screen.blit(bg_img, (0,0))
            action = ui.handle_input("MODE_SEL", mx, my, click)
            ui.draw_mode_select(screen)
            
            if action == "MODE_CLASSIC":
                game_mode = ClassicMode()
                ui.push_scene("INPUT_SEL")
                audio.play_sfx("start")
            elif action == "MODE_SURVIVAL":
                game_mode = SurvivalMode()
                ui.push_scene("INPUT_SEL")
                audio.play_sfx("start")
            elif action == "BACK":
                ui.pop_scene()
                audio.play_sfx("start")
                
        elif ui.current_scene == "INPUT_SEL":
            screen.blit(bg_img, (0,0))
            action = ui.handle_input("INPUT_SEL", mx, my, click)
            ui.draw_input_select(screen)
            
            if action:
                if action == "INPUT_MOUSE":
                    input_provider = MouseInput(WIDTH, HEIGHT)
                    ui.push_scene("GAME")
                    audio.play_music("game_slow")
                    all_sprites.empty()
                    fruits.empty()
                    blade = Blade()
                elif action == "INPUT_HAND":
                    input_provider = HandInput(WIDTH, HEIGHT)
                    ui.push_scene("GAME")
                    audio.play_music("game_slow")
                    all_sprites.empty()
                    fruits.empty()
                    blade = Blade()
                elif action == "BACK":
                    ui.pop_scene()
                    audio.play_sfx("start")

        elif ui.current_scene == "GAME":
            # Check if paused
            # Check if paused
            if ui.is_paused:
                # Draw frozen game state (Background + Sprites)
                screen.blit(gameplay_bg_img, (shake_x, shake_y))
                all_sprites.draw(screen)
                blade.draw(screen)
                
                # Draw live Camera PiP even when paused (so user sees themselves)
                if hasattr(input_provider, 'get_frame'):
                    frame = input_provider.get_frame()
                    if frame is not None:
                         img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                         img_rgb = np.rot90(img_rgb)
                         surf = pygame.surfarray.make_surface(img_rgb)
                         surf = pygame.transform.flip(surf, True, False)
                         
                         pip_w = WIDTH // 4
                         pip_aspect = surf.get_height() / surf.get_width()
                         pip_h = int(pip_w * pip_aspect)
                         pip_surf = pygame.transform.scale(surf, (pip_w, pip_h))
                         
                         pip_x = WIDTH - pip_w - 20
                         pip_y = HEIGHT - pip_h - 20
                         
                         pygame.draw.rect(screen, WHITE, (pip_x - 2, pip_y - 2, pip_w + 4, pip_h + 4), 2)
                         screen.blit(pip_surf, (pip_x, pip_y))
                
                # HUD
                hud = ui.font_small.render(game_mode.get_status(), True, WHITE)
                screen.blit(hud, (20, 20))
                
                # Pause menu (mouse-only input)
                action = ui.handle_input("PAUSE", mx, my, click)
                ui.draw_pause(screen)
                
                if action == "RESUME":
                    ui.is_paused = False
                    audio.play_sfx("start")
                elif action == "BACK":
                    ui.is_paused = False
                    if input_provider:
                        input_provider.cleanup()
                        input_provider = None
                    ui.pop_scene()
                    audio.play_music("menu")
            else:
                # Normal gameplay
                ix, iy, velocity, input_paused = input_provider.get_input()
                
                # Draw Background
                # Draw Background (Always dominating)
                screen.blit(gameplay_bg_img, (shake_x, shake_y))
                
                # Camera PiP (Picture-in-Picture)
                if hasattr(input_provider, 'get_frame'):
                    frame = input_provider.get_frame()
                    if frame is not None:
                        # Process frame
                        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img_rgb = np.rot90(img_rgb)
                        surf = pygame.surfarray.make_surface(img_rgb)
                        surf = pygame.transform.flip(surf, True, False)
                        
                        # PiP sizing (e.g., 25% of screen width)
                        pip_w = WIDTH // 4
                        pip_aspect = surf.get_height() / surf.get_width()
                        pip_h = int(pip_w * pip_aspect)
                        
                        pip_surf = pygame.transform.scale(surf, (pip_w, pip_h))
                        
                        # Position: Bottom Right with padding
                        padding = 20
                        pip_x = WIDTH - pip_w - padding
                        pip_y = HEIGHT - pip_h - padding
                        
                        # Draw Border
                        pygame.draw.rect(screen, WHITE, (pip_x - 2, pip_y - 2, pip_w + 4, pip_h + 4), 2)
                        
                        # Draw PiP
                        screen.blit(pip_surf, (pip_x, pip_y))
                
                # Update Logic (only if not palm-paused)
                if not input_paused:
                    if ix is not None:
                        blade.update(ix, iy)
                    
                    # Spawner
                    if random.randint(1, 40) == 1:
                        spawn_x = random.randint(100, WIDTH-100)
                        spawn_y = HEIGHT + 20
                        
                        if random.randint(1, 5) == 1:
                            b = Bomb(spawn_x, spawn_y, WIDTH, HEIGHT)
                            all_sprites.add(b)
                            fruits.add(b)
                        else:
                            f = Fruit(spawn_x, spawn_y, WIDTH, HEIGHT)
                            all_sprites.add(f)
                            fruits.add(f)
                    
                    all_sprites.update()
                    
                    # Collisions
                    segments = blade.get_segments()
                    if velocity > MIN_CUT_VELOCITY and segments:
                        hit_count = 0
                        for entity in list(fruits):
                            if entity.check_slice(segments):
                                hit_count += 1
                                
                                if isinstance(entity, Bomb):
                                    audio.play_sfx("bomb")
                                    boom = Explosion(entity.pos_x, entity.pos_y)
                                    all_sprites.add(boom)
                                    entity.kill()
                                    game_mode.on_bomb()
                                    shake_timer = 20
                                else:
                                    audio.play_sfx("splat")
                                    pts = game_mode.on_slice(entity)
                                    
                                    splash = SplashEffect(entity.pos_x, entity.pos_y, entity.fruit_type, velocity)
                                    all_sprites.add(splash)
                                    
                                    h1 = SlicedFruit(entity.pos_x, entity.pos_y, entity.fruit_type, 1)
                                    h2 = SlicedFruit(entity.pos_x, entity.pos_y, entity.fruit_type, 2)
                                    all_sprites.add(h1)
                                    all_sprites.add(h2)
                                    entity.kill()
                        
                        if hit_count > 1:
                            audio.play_sfx("combo")

                    # Check dropped fruits
                    for entity in list(fruits):
                        if entity.rect.top > HEIGHT:
                            if not isinstance(entity, Bomb):
                                game_mode.on_miss()
                                entity.kill()
                            else:
                                entity.kill()

                    # Check Game Over
                    if game_mode.game_over:
                        ui.current_scene = "OVER"
                        audio.play_sfx("over")
                        audio.stop_music()
                
                # Draw Game
                all_sprites.draw(screen)
                blade.draw(screen)
                
                # Palm pause indicator
                if input_paused:
                    txt = ui.font_big.render("PALM PAUSE", True, (255, 255, 0))
                    screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2))
                
                # HUD
                hud = ui.font_small.render(game_mode.get_status(), True, WHITE)
                screen.blit(hud, (20, 20))
                
                # Pause hint
                hint = ui.font_small.render("ESC to Pause", True, (150, 150, 150))
                screen.blit(hint, (WIDTH - hint.get_width() - 20, 20))

        elif ui.current_scene == "OVER":
            # Keep drawing game in background
            all_sprites.draw(screen)
            action = ui.handle_input("OVER", mx, my, click)
            ui.draw_game_over(screen, game_mode.score)
            
            if action == "GOTO_MENU":
                if input_provider:
                    input_provider.cleanup()
                    input_provider = None
                ui.current_scene = "MENU"
                ui.scene_stack.clear()
                audio.play_music("menu")
            elif action == "RESTART":
                ui.current_scene = "GAME"
                audio.play_music("game_slow")
                
                if isinstance(game_mode, ClassicMode):
                    game_mode = ClassicMode()
                else:
                    game_mode = SurvivalMode()
                    
                all_sprites.empty()
                fruits.empty()
                blade = Blade()

        pygame.display.flip()
        clock.tick(FPS)
        
    
    # Cleanup logic
    if input_provider:
        input_provider.cleanup()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
