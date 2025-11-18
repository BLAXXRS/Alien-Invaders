"""
Alien Invaders - Upgraded Edition
Features:
- Mouse-drag left/right movement
- Auto-shooting player (with upgradeable fire rate)
- Multishot buff drops (5 seconds)
- Player HP + hearts UI
- Explosions / particle effects
- Multiple enemy types (basic, fast, tank, zigzag, boss)
- Enemy bullets, enemy AI variations
- Waves & boss every 5 waves
- Shop between waves (spend score for permanent upgrades)
- Simple sound effects if numpy is installed (optional)
- All-in-one single-file Pygame game

Save as: alien_invaders_full.py
Run: python alien_invaders_full.py
Requires: pygame (pip install pygame). numpy optional for sound (pip install numpy).
"""

import pygame
import random
import math
import sys
import time

# Optional sound: uses numpy to synthesize simple waveforms.
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except Exception:
    NUMPY_AVAILABLE = False

pygame.init()
if NUMPY_AVAILABLE:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# --------------------
# Configuration
# --------------------
WIDTH, HEIGHT = 880, 720
FPS = 60

# Player
PLAYER_START_X = WIDTH // 2
PLAYER_Y = HEIGHT - 70
PLAYER_RADIUS = 18
PLAYER_BASE_HP = 5
PLAYER_BASE_FIRE_DELAY_MS = 220  # auto-shoot delay in ms
PLAYER_SPEED = 99999  # movement controlled by mouse drag; speed not used

# Bullets
PLAYER_BULLET_SPEED = -10
ENEMY_BULLET_SPEED_BASE = 3.5

# Buffs
BUFF_CHANCE = 0.18
BUFF_DURATION_MS = 5000

# Waves
ENEMIES_PER_ROW = 10
BASE_ROWS = 2
WAVE_INCREASE_ROWS = 1
BOSS_EVERY = 5
ENEMY_DROP = 24   # pixels enemies drop when they hit screen edge

# Shop prices (score cost)
SHOP_FIRE_RATE_PRICE = 800
SHOP_MAX_HP_PRICE = 1000
SHOP_SPEED_PRICE = 700  # used to increase drag responsiveness (cosmetic)

# Particles
PARTICLE_COUNT = 14

# Sounds (if numpy available)
SND_VOL = 0.15

# Colors
WHITE = (255,255,255)
BLACK = (10,10,18)
RED = (230,60,60)
GREEN = (80,230,120)
YELLOW = (255,220,50)
CYAN = (80,200,235)
ORANGE = (255,150,60)
GRAY = (120,120,140)

FONT_NAME = "Consolas"

# --------------------
# Utility
# --------------------
def clamp(v, a, b):
    return max(a, min(b, v))

def dist(a,b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

# --------------------
# Retro pixel SFX (square + noise) — kept simple
# --------------------
def _make_sound_from_array(arr):
    try:
        return pygame.sndarray.make_sound(arr.copy())
    except Exception:
        return None

def sfx_square(freq=440, ms=120, vol=0.25, rate=44100):
    if not NUMPY_AVAILABLE:
        return None
    length = int(rate * (ms/1000.0))
    t = np.arange(length)
    wave = np.sign(np.sin(2*np.pi*freq*(t / rate))) * vol
    wave = (wave * 32767).astype(np.int16)
    stereo = np.column_stack((wave, wave))
    return _make_sound_from_array(stereo)

def sfx_noise(ms=80, vol=0.3, rate=44100):
    if not NUMPY_AVAILABLE:
        return None
    length = int(rate * (ms/1000.0))
    wave = np.random.uniform(-1, 1, length) * vol
    wave = (wave * 32767).astype(np.int16)
    stereo = np.column_stack((wave, wave))
    return _make_sound_from_array(stereo)

if NUMPY_AVAILABLE:
    SND_SHOT = sfx_square(880, 70, 0.23)
    SND_ENEMY = sfx_square(420, 90, 0.25)
    SND_EXPLODE = sfx_noise(180, 0.32)
    SND_POWER = sfx_square(1200, 120, 0.28)
else:
    SND_SHOT = SND_ENEMY = SND_EXPLODE = SND_POWER = None

def play(sound):
    if sound:
        try:
            sound.play()
        except Exception:
            pass

# --------------------
# Spinning globe (menu)
# --------------------
def draw_spinning_globe(surf, cx, cy, radius, angle):
    # base globe
    pygame.draw.circle(surf, (12,60,110), (cx, cy), radius)
    pygame.draw.circle(surf, (24,120,200), (cx, cy), radius, 2)
    # rotating longitude arcs
    rect = pygame.Rect(cx - radius, cy - radius, radius*2, radius*2)
    for i in range(6):
        a = angle + i * 0.9
        start = a
        end = a + math.pi
        pygame.draw.arc(surf, (80,170,220), rect, start, end, 2)
    # latitude lines (static)
    for j in range(-2,3):
        if j == 0: w = 2
        else: w = 1
        ry = int(cy + j * (radius * 0.35))
        pygame.draw.ellipse(surf, (80,160,200), (cx - int(radius*0.85), ry - 6, int(radius*1.7), 12), w)
    # subtle stars/dots that rotate
    for k in range(12):
        theta = angle * 1.6 + k * (2*math.pi/12)
        r = radius * 0.65
        x = int(cx + math.cos(theta) * r)
        y = int(cy + math.sin(theta) * r * 0.5)
        pygame.draw.circle(surf, (200,230,255), (x, y), 2)

# --------------------
# Entities
# --------------------
class Particle:
    def __init__(self, x, y, color, life=0.8):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-6, -1)
        self.color = color
        self.life = life
        self.time = 0

    def update(self, dt):
        self.time += dt
        self.x += self.vx
        self.y += self.vy
        self.vy += 10 * dt

    def draw(self, surf):
        alpha = clamp(1 - (self.time / self.life), 0, 1)
        if alpha <= 0: return
        r = int(3 * (1 - alpha) + 1)
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        col = (*self.color, int(255 * alpha))
        pygame.draw.circle(s, col, (r, r), r)
        surf.blit(s, (self.x - r, self.y - r))

class Explosion:
    def __init__(self, x, y, color=ORANGE, num=PARTICLE_COUNT):
        self.particles = [Particle(x + random.uniform(-6,6), y + random.uniform(-6,6), color, life=random.uniform(0.5,1.1)) for _ in range(num)]
    def update(self, dt):
        for p in self.particles: p.update(dt)
        self.particles = [p for p in self.particles if p.time < p.life]
    def draw(self, surf):
        for p in self.particles: p.draw(surf)

class Bullet:
    def __init__(self, x, y, vy, color=YELLOW, owner="player", damage=1):
        self.x = x; self.y = y; self.vy = vy; self.color = color; self.owner = owner
        self.radius = 4 if owner=="player" else 5
        self.damage = damage
        self.rect = pygame.Rect(x-self.radius, y-self.radius, self.radius*2, self.radius*2)
    def update(self, dt):
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))
    def draw(self, surf): pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
    def offscreen(self): return self.y < -30 or self.y > HEIGHT + 30

class BuffDrop:
    def __init__(self, x, y):
        self.x = x; self.y = y; self.rect = pygame.Rect(x-10, y-10, 20, 20); self.vy = 2.2
    def update(self, dt): self.y += self.vy; self.rect.center = (int(self.x), int(self.y))
    def draw(self, surf): pygame.draw.rect(surf, YELLOW, self.rect); pygame.draw.circle(surf, WHITE, self.rect.center, 3)

# --------------------
# Player
# --------------------
class Player:
    def __init__(self):
        self.x = PLAYER_START_X; self.y = PLAYER_Y; self.radius = PLAYER_RADIUS
        self.hp_max = PLAYER_BASE_HP; self.hp = PLAYER_BASE_HP
        self.fire_delay_ms = PLAYER_BASE_FIRE_DELAY_MS; self.last_shot_time = 0
        self.multishot_active = False; self.multishot_end_time = 0
        self.score = 0; self.lives = 1
        # ultimate
        self.ultimate_count = 0
        self.ultimate_needed = 10
        self.ultimate_available = False
    def update(self):
        if self.multishot_active and pygame.time.get_ticks() > self.multishot_end_time: self.multishot_active = False
    def draw(self, surf):
        x,y = int(self.x), int(self.y)
        pts = [(x, y - self.radius), (x - self.radius, y + self.radius), (x + self.radius, y + self.radius)]
        pygame.draw.polygon(surf, CYAN, pts); pygame.draw.polygon(surf, WHITE, pts, 2)
    def can_shoot(self): return pygame.time.get_ticks() - self.last_shot_time >= self.fire_delay_ms
    def shoot(self):
        self.last_shot_time = pygame.time.get_ticks(); bullets = []
        if self.multishot_active:
            for s in (-14,0,14): bullets.append(Bullet(self.x + s, self.y - self.radius - 4, PLAYER_BULLET_SPEED, YELLOW, "player", damage=1))
            play(SND_SHOT)
        else:
            bullets.append(Bullet(self.x, self.y - self.radius - 6, PLAYER_BULLET_SPEED, YELLOW, "player", damage=1)); play(SND_SHOT)
        return bullets
    def take_damage(self, amount=1):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            return True
        return False
    def use_ultimate(self):
        # consumes ultimate and fires 5 faster bullets in a wide spread (horizontal offsets)
        bullets = []
        offsets = [-40, -20, 0, 20, 40]
        for s in offsets:
            bullets.append(Bullet(self.x + s, self.y - self.radius - 6, int(PLAYER_BULLET_SPEED * 1.6), YELLOW, "player", damage=2))
        return bullets

# --------------------
# Enemies & AI
# --------------------
class Enemy:
    def __init__(self, x, y, etype="basic", hp=1):
        self.x = x; self.y = y; self.etype = etype; self.base_x = x; self.base_y = y
        self.w = 36; self.h = 30; self.hp = hp; self.alive = True; self.arm_state = 0
        self.shoot_timer = random.uniform(0.4, 2.4); self.osc_phase = random.uniform(0, math.pi*2)
    def rect(self): return pygame.Rect(int(self.x - self.w/2), int(self.y - self.h/2), self.w, self.h)
    def toggle_arm(self): self.arm_state = 1 - self.arm_state
    def update(self, step_dx, step_dy, dt, wave, elapsed):
        if not self.alive: return
        if self.etype == "zig": self.y += math.sin(elapsed*2 + self.osc_phase) * 0.4
        elif self.etype == "tank": self.y += math.sin(elapsed*1.2 + self.osc_phase) * 0.15
        self.x += step_dx; self.y += step_dy
        base_rate = 1.0
        if self.etype == "fast": base_rate = 0.5
        elif self.etype == "tank": base_rate = 1.6
        self.shoot_timer -= dt * (1.0 / base_rate)
    def draw(self, surf):
        if not self.alive: return
        px = int(self.x); py = int(self.y)
        frame1 = ["  ██  ", " █  █ ", "██████", "█ ██ █", "█    █", " █  █ "]
        frame2 = ["  ██  ", " █  █ ", "██████", "█ ██ █", " █  █ ", "█    █"]
        frame = frame1 if self.arm_state==0 else frame2
        for ry, row in enumerate(frame):
            for rx, ch in enumerate(row):
                if ch == "█":
                    x = px + (rx - 3) * 3; y = py + (ry - 3) * 3
                    pygame.draw.rect(surf, GREEN, (x, y, 3, 3))

class Boss(Enemy):
    def __init__(self, x, y, hp=18):
        super().__init__(x,y,etype="boss", hp=hp)
        self.w = 120; self.h = 70; self.move_timer = 0; self.dir = 1; self.shoot_timer = 1.2
    def draw(self, surf):
        if not self.alive: return
        rect = pygame.Rect(self.x - self.w/2, self.y - self.h/2, self.w, self.h)
        pygame.draw.rect(surf, (120,50,200), rect); pygame.draw.rect(surf, WHITE, rect, 3)
        pygame.draw.circle(surf, BLACK, (int(self.x - 24), int(self.y - 8)), 8)
        pygame.draw.circle(surf, BLACK, (int(self.x + 24), int(self.y - 8)), 8)
        for i in range(-3,4): tx = int(self.x + i*10); ty = int(self.y + 16); pygame.draw.rect(surf, WHITE, (tx-3, ty, 6, 8))

# --------------------
# Wave Manager
# --------------------
class WaveManager:
    def __init__(self):
        self.wave_num = 0; self.enemies = []
        self.step_interval = 0.8; self.step_acc = 0.0; self.direction = 1; self.elapsed = 0.0
        self.base_speed = 28.0; self.enemy_shoot_prob = 0.006
        self.spawn_wave()
    def spawn_wave(self):
        self.wave_num += 1; self.enemies = []
        rows = BASE_ROWS + (self.wave_num - 1) // 1
        if self.wave_num % BOSS_EVERY == 0:
            boss = Boss(WIDTH//2, 120, hp=12 + self.wave_num*2); self.enemies.append(boss); self.step_interval = max(0.6 - (self.wave_num*0.01), 0.35); return
        cols = ENEMIES_PER_ROW; start_x = 120; start_y = 90; spacing_x = 58; spacing_y = 54
        for r in range(rows):
            for c in range(cols):
                x = start_x + c * spacing_x; y = start_y + r * spacing_y
                t = random.random()
                if t < 0.62: etype='basic'; hp=1
                elif t < 0.82: etype='fast'; hp=1
                elif t < 0.94: etype='zig'; hp=1
                else: etype='tank'; hp=2 + (self.wave_num//3)
                self.enemies.append(Enemy(x,y,etype=etype,hp=hp))
        self.step_interval = max(0.95 - (self.wave_num*0.02), 0.35)
        self.base_speed = 20 + self.wave_num * 2.2
        self.enemy_shoot_prob = clamp(0.004 + self.wave_num * 0.0009, 0.004, 0.02)
    def update(self, dt):
        self.elapsed += dt; self.step_acc += dt
        if self.step_acc >= self.step_interval:
            times = int(self.step_acc // self.step_interval); self.step_acc -= times * self.step_interval
            step_size = self.base_speed * (self.step_interval)
            for _ in range(times):
                dx = step_size * self.direction
                will_hit = False
                for e in self.enemies:
                    if not e.alive: continue
                    nx = e.x + dx
                    if nx - e.w/2 < 20 or nx + e.w/2 > WIDTH - 20:
                        will_hit = True; break
                if will_hit:
                    for e in self.enemies:
                        if e.alive: e.y += ENEMY_DROP; e.toggle_arm()
                    self.direction *= -1
                else:
                    for e in self.enemies:
                        if e.alive: e.x += dx; e.toggle_arm()
    def any_alive(self): return any(e.alive for e in self.enemies)

# --------------------
# Shop / Upgrades
# --------------------
class Shop:
    def __init__(self): pass
    def open(self, screen, player):
        font = pygame.font.SysFont(FONT_NAME, 24); big = pygame.font.SysFont(FONT_NAME, 40)
        options = [("Faster Fire (reduce delay by 20ms)", SHOP_FIRE_RATE_PRICE, "fire"), ("Increase Max HP (+1)", SHOP_MAX_HP_PRICE, "hp"), ("Heal to Full (+heal)", SHOP_MAX_HP_PRICE//2, "heal")]
        selected = 0; clock = pygame.time.Clock()
        while True:
            clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_t: return
                    if ev.key == pygame.K_UP: selected = (selected - 1) % len(options)
                    if ev.key == pygame.K_DOWN: selected = (selected + 1) % len(options)
                    if ev.key == pygame.K_RETURN:
                        _, cost, code = options[selected]
                        if player.score >= cost:
                            player.score -= cost
                            if code == "fire": player.fire_delay_ms = max(80, player.fire_delay_ms - 20); play(SND_POWER)
                            elif code == "hp": player.hp_max += 1; player.hp += 1; play(SND_POWER)
                            elif code == "heal": player.hp = player.hp_max; play(SND_POWER)
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    mx,my = pygame.mouse.get_pos(); base_y = 240
                    for i,op in enumerate(options):
                        rect = pygame.Rect(180, base_y + i*60, 520, 48)
                        if rect.collidepoint(mx,my): selected = i; _,cost,code = options[i]
                        if player.score >= cost:
                            player.score -= cost
                            if code == "fire": player.fire_delay_ms = max(80, player.fire_delay_ms - 20); play(SND_POWER)
                            elif code == "hp": player.hp_max += 1; player.hp += 1; play(SND_POWER)
                            elif code == "heal": player.hp = player.hp_max; play(SND_POWER)
            screen.fill((6,6,14))
            title = big.render("SHOP - Spend Score", True, YELLOW); screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))
            info = font.render(f"Score: {player.score}", True, WHITE); screen.blit(info, (WIDTH-160, 20))
            base_y = 240
            for i, (desc, cost, code) in enumerate(options):
                rect = pygame.Rect(180, base_y + i*60, 520, 48); color = (40,40,80) if i!=selected else (70,70,120)
                pygame.draw.rect(screen, color, rect); txt = font.render(f"{desc} — Cost: {cost}", True, WHITE); screen.blit(txt, (rect.x + 10, rect.y + 10))
            tip = font.render("Use Up/Down, Enter to buy, or click option. Press T to continue.", True, GRAY); screen.blit(tip, (WIDTH//2 - tip.get_width()//2, HEIGHT - 80))
            pygame.display.flip()

# --------------------
# Main Game (with Menu and Game Over fade)
# --------------------
def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Alien Invaders — Upgraded")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(FONT_NAME, 18)
    bigfont = pygame.font.SysFont(FONT_NAME, 40)

    # game state
    state = 'menu'  # 'menu', 'playing', 'gameover'
    menu_blink = 0.0
    fade_alpha = 0.0

    def reset_game():
        nonlocal player, wave, bullets, enemy_bullets, drops, explosions, game_over, in_shop, time_since_wave_win
        player = Player(); wave = WaveManager(); shop = Shop()
        bullets = []; enemy_bullets = []; drops = []; explosions = []
        game_over = False; in_shop = False; time_since_wave_win = 0.0

    # initial setup
    player = Player(); wave = WaveManager(); shop = Shop()
    bullets = []; enemy_bullets = []; drops = []; explosions = []
    dragging = False; drag_offset_x = 0
    game_over = False; in_shop = False; time_since_wave_win = 0.0
    pygame.mouse.set_visible(True)
    start_time = pygame.time.get_ticks()

    while True:
        dt_ms = clock.tick(FPS)
        dt = dt_ms / 1000.0
        elapsed = (pygame.time.get_ticks() - start_time)/1000.0
        menu_blink += dt

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if state == 'menu':
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_RETURN:
                        state = 'playing'
                        # reset game when starting from menu
                        reset_game()
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    if ev.button == 1:
                        state = 'playing'; reset_game()
            elif state == 'playing':
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_p:
                        paused = True
                        while paused:
                            for e in pygame.event.get():
                                if e.type == pygame.QUIT: pygame.quit(); sys.exit()
                                if e.type == pygame.KEYDOWN and e.key == pygame.K_p: paused = False
                            pause_surf = bigfont.render("PAUSED — Press P to resume", True, YELLOW)
                            screen.blit(pause_surf, (WIDTH//2 - pause_surf.get_width()//2, HEIGHT//2-24))
                            pygame.display.flip(); clock.tick(15)
                    if ev.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()
                    if ev.key == pygame.K_r and game_over:
                        reset_game(); state = 'playing'
                    if ev.key == pygame.K_SPACE:
                        if player.can_shoot(): bullets.extend(player.shoot())
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    if ev.button == 1:
                        mx,my = ev.pos
                        # if click near player -> begin drag
                        if abs(my - player.y) < 100:
                            dragging = True; drag_offset_x = player.x - mx
                        else:
                            # otherwise, try to activate ultimate if available
                            if player.ultimate_available:
                                bullets.extend(player.use_ultimate())
                                player.ultimate_available = False
                                player.ultimate_count = 0
                                play(SND_POWER)
                if ev.type == pygame.MOUSEBUTTONUP:
                    if ev.button == 1: dragging = False
                if ev.type == pygame.MOUSEMOTION:
                    if dragging: mx,my = ev.pos; player.x = clamp(mx + drag_offset_x, 20, WIDTH-20)
            elif state == 'gameover':
                # during fade we ignore inputs; after fade completes click returns to menu
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and fade_alpha >= 255:
                    state = 'menu'
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN and fade_alpha >= 255:
                    state = 'menu'

        # STATE: MENU
        if state == 'menu':
            screen.fill(BLACK)
            title = bigfont.render("ALIEN INVADERS", True, CYAN)
            screen.blit(title, (WIDTH//2 - title.get_width()//2, 140))
            subtitle = font.render("Remastered Enhanced Edition", True, GRAY)
            screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 200))
            # spinning globe under title
            draw_spinning_globe(screen, WIDTH//2, 320, 80, menu_blink * 0.9)
            # flashing prompt
            flash = (math.sin(menu_blink*3.0) + 1) / 2
            alpha = int(80 + 175 * flash)
            prompt_surf = font.render("Press ENTER or Click to Play", True, (255,255,255))
            # draw with slight glow by blitting shadow
            shadow = font.render("Press ENTER or Click to Play", True, (40,40,40))
            screen.blit(shadow, (WIDTH//2 - prompt_surf.get_width()//2 + 2, 420 + 2))
            screen.blit(prompt_surf, (WIDTH//2 - prompt_surf.get_width()//2, 420))
            tip = font.render("YOUR PLANET IS BEING INVADED!", True, GRAY)
            screen.blit(tip, (WIDTH//2 - tip.get_width()//2, HEIGHT-60))
            pygame.display.flip()
            continue

        # STATE: PLAYING
        if state == 'playing':
            # auto-shoot
            if not game_over and not in_shop and player.can_shoot(): bullets.extend(player.shoot())
            player.update()
            wave.update(dt)
            # enemy shooting
            for e in wave.enemies:
                if not e.alive: continue
                base_prob = wave.enemy_shoot_prob
                if isinstance(e, Boss): base_prob *= 0.6
                if e.etype == 'fast': prob = base_prob * 1.8
                elif e.etype == 'tank': prob = base_prob * 0.6
                else: prob = base_prob
                if isinstance(e, Boss):
                    e.shoot_timer -= dt
                    if e.shoot_timer <= 0:
                        e.shoot_timer = 0.8
                        for a in (-1,0,1): enemy_bullets.append(Bullet(e.x + a*16, e.y + e.h//2 + 6, ENEMY_BULLET_SPEED_BASE + 1.2, RED, 'enemy', damage=1))
                        play(SND_ENEMY)
                else:
                    if random.random() < prob:
                        enemy_bullets.append(Bullet(e.x, e.y + e.h//2 + 6, ENEMY_BULLET_SPEED_BASE + (0.1*(1 if e.etype=='fast' else 0)), RED, 'enemy', damage=1))
                        play(SND_ENEMY)
            # enemy ai update
            for e in wave.enemies:
                if e.alive: e.update(0,0,dt,wave,elapsed)
            # bullets
            for b in bullets[:]:
                b.update(dt);
                if b.offscreen(): bullets.remove(b)
            for b in enemy_bullets[:]:
                b.update(dt);
                if b.offscreen(): enemy_bullets.remove(b)
            # drops
            for d in drops[:]:
                d.update(dt);
                if d.y > HEIGHT + 40: drops.remove(d)
            # explosions
            for ex in explosions[:]:
                ex.update(dt);
                if not ex.particles: explosions.remove(ex)
            # collisions player bullets -> enemies
            for b in bullets[:]:
                if b.owner != 'player': continue
                hit = False
                for e in wave.enemies:
                    if not e.alive: continue
                    if e.rect().collidepoint(b.x, b.y):
                        e.hp -= b.damage
                        try: bullets.remove(b)
                        except: pass
                        play(SND_EXPLODE)
                        if e.hp <= 0:
                            e.alive = False; player.score += 120 if not isinstance(e,Boss) else 1200
                            # track for ultimate
                            player.ultimate_count += 1
                            if player.ultimate_count >= player.ultimate_needed:
                                player.ultimate_available = True
                            explosions.append(Explosion(e.x, e.y, color=ORANGE, num=PARTICLE_COUNT + (6 if isinstance(e,Boss) else 0)))
                            if not isinstance(e,Boss) and random.random() < BUFF_CHANCE: drops.append(BuffDrop(e.x, e.y))
                        hit = True; break
                if hit: continue
            # collisions enemy bullets -> player
            for b in enemy_bullets[:]:
                if math.hypot(b.x - player.x, b.y - player.y) < (b.radius + player.radius):
                    try: enemy_bullets.remove(b)
                    except: pass
                    killed = player.take_damage(1)
                    explosions.append(Explosion(player.x, player.y, color=CYAN, num=18))
                    play(SND_EXPLODE)
                    if killed:
                        game_over = True
                        # start fade
                        state = 'gameover'
                        fade_alpha = 0.0
                        fade_start = pygame.time.get_ticks()
                        break
            # collisions drop -> player
            for d in drops[:]:
                if d.rect.colliderect(pygame.Rect(player.x - player.radius, player.y - player.radius, player.radius*2, player.radius*2)):
                    drops.remove(d); player.multishot_active = True; player.multishot_end_time = pygame.time.get_ticks() + BUFF_DURATION_MS; play(SND_POWER)
            # wave cleared
            if not wave.any_alive() and not in_shop:
                player.score += 300; in_shop = True; time_since_wave_win = 0.0
            # shop
            if in_shop:
                shop.open(screen, player); in_shop = False; wave.spawn_wave(); bullets=[]; enemy_bullets=[]; drops=[]; explosions=[]; player.hp = min(player.hp + 1, player.hp_max)
            for e in wave.enemies:
                if e.alive and e.y + e.h/2 >= player.y - 20: game_over = True; state = 'gameover'; fade_alpha = 0.0; fade_start = pygame.time.get_ticks(); break
            # drawing
            screen.fill(BLACK)
            hud_surf = font.render(f"SCORE: {player.score}   WAVE: {wave.wave_num}   ENEMIES: {sum(1 for ee in wave.enemies if ee.alive)}", True, WHITE)
            screen.blit(hud_surf, (12, 12))
            hpw = 160; hp_x = WIDTH - hpw - 20; hp_y = 18
            pygame.draw.rect(screen, GRAY, (hp_x, hp_y, hpw, 18))
            hp_frac = player.hp / max(1, player.hp_max)
            pygame.draw.rect(screen, RED, (hp_x, hp_y, int(hpw*hp_frac), 18))
            hp_txt = font.render(f"HP: {player.hp}/{player.hp_max}", True, WHITE); screen.blit(hp_txt, (hp_x + 6, hp_y - 18))
            # ultimate HUD
            ult_text = "ULTIMATE: READY! Click anywhere (not drag) to use" if player.ultimate_available else f"ULTIMATE: {player.ultimate_count}/{player.ultimate_needed}"
            ult_surf = font.render(ult_text, True, YELLOW if player.ultimate_available else GRAY)
            screen.blit(ult_surf, (12, 36))
            if player.multishot_active:
                rem = max(0, player.multishot_end_time - pygame.time.get_ticks())
                btxt = font.render(f"MULTISHOT: {rem//1000 + 1}s", True, YELLOW); screen.blit(btxt, (12, 56))
            for e in wave.enemies: e.draw(screen)
            for b in bullets: b.draw(screen)
            for b in enemy_bullets: b.draw(screen)
            for d in drops: d.draw(screen)
            player.draw(screen)
            for ex in explosions: ex.draw(screen)
            if not wave.any_alive(): hint = bigfont.render("Wave Cleared! Entering SHOP...", True, YELLOW); screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2 - 24))
            pygame.display.flip()
            continue

        # STATE: GAMEOVER (fade out then return to menu)
        if state == 'gameover':
            # increment fade
            fade_alpha += dt * 255 / 1.0  # 1 second fade
            if fade_alpha >= 255:
                fade_alpha = 255
            # draw last frame of game elements (so player sees where they died)
            screen.fill(BLACK)
            hud_surf = font.render(f"SCORE: {player.score}   WAVE: {wave.wave_num}   ENEMIES: {sum(1 for ee in wave.enemies if ee.alive)}", True, WHITE)
            screen.blit(hud_surf, (12, 12))
            for e in wave.enemies: e.draw(screen)
            for b in bullets: b.draw(screen)
            for b in enemy_bullets: b.draw(screen)
            for d in drops: d.draw(screen)
            player.draw(screen)
            for ex in explosions: ex.draw(screen)
            # overlay fade
            fade_surf = pygame.Surface((WIDTH, HEIGHT))
            fade_surf.set_alpha(int(fade_alpha))
            fade_surf.fill((0,0,0))
            screen.blit(fade_surf, (0,0))
            if fade_alpha >= 255:
                # show final menu text
                go = bigfont.render("GAME OVER", True, RED)
                sub = font.render("Press ENTER or Click to return to Menu", True, WHITE)
                screen.blit(go, (WIDTH//2 - go.get_width()//2, HEIGHT//2 - 50))
                screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 10))
            pygame.display.flip()
            # if fade complete and input handled earlier, reset happens in event loop
            if fade_alpha >= 255:
                # wait for click/enter — handled in event loop above
                pass
            continue

# --------------------
# Run
# --------------------
if __name__ == '__main__':
    main()
