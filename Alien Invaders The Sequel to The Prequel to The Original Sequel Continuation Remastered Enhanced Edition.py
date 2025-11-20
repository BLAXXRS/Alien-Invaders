
def draw_boss_healthbar(surf, x, y, w, h, hp, hp_max):
    # transparent background
    bg = pygame.Surface((w, h), pygame.SRCALPHA)
    bg.fill((0,0,0,120))
    surf.blit(bg, (x, y))
    # hp bar
    fill = int((hp/hp_max) * (w-4))
    pygame.draw.rect(surf, RED, (x+2, y+2, fill, h-4))
    pygame.draw.rect(surf, WHITE, (x, y, w, h), 2)

"""
Alien Invaders The Sequel to The Prequel to The Original Sequel Continuation Remastered Enhanced Edition (with hit-flash + knockback)
- Keeps mouse-drag + keyboard movement (unchanged from your request)
- Shield pickup gives 3 hits
- Prevents enemies spawning on top of the player (uses player position when spawning)
- Repositions dynamic enemies that fly off-screen to the top instead of deleting them
- Collision removed fuck that shit
- Clean, ready-to-run single-file script

Run: python alien_invaders_fixed_knockback.py
Requires: pygame (pip install pygame)
"""

import pygame
import random
import math
import sys
import time

# --------------------
# Configuration
# --------------------
WIDTH, HEIGHT = 880, 720
FPS = 60

# Player
PLAYER_START_X = WIDTH // 2
PLAYER_Y = HEIGHT - 70
PLAYER_RADIUS = 18
PLAYER_BASE_HP = 6
PLAYER_BASE_FIRE_DELAY_MS = 220
PLAYER_SPEED = 260

# Bullets
PLAYER_BULLET_SPEED = -10
ENEMY_BULLET_SPEED_BASE = 3.0

# Buffs
BUFF_CHANCE = 0.18
BUFF_DURATION_MS = 5000

# Shield duration (ms)
SHIELD_DURATION_MS = 5000

# Ultimate
ULTIMATE_DURATION_MS = 8000
ULTIMATE_FIRE_DELAY_MS = 180

# Waves
ENEMIES_PER_ROW = 10
BOSS_EVERY = 5
ENEMY_DROP = 24

# Shop prices
SHOP_FIRE_RATE_PRICE = 800
SHOP_MAX_HP_PRICE = 1000
SHOP_SPEED_PRICE = 700

# Particles
PARTICLE_COUNT = 14

# Knockback (light = 15 px as requested)
KNOCKBACK_PIXELS = 15

# Colors
WHITE = (255,255,255)
BLACK = (10,10,18)
RED = (230,60,60)
GREEN = (80,230,120)
YELLOW = (255,220,50)
CYAN = (80,200,235)
ORANGE = (255,150,60)
GRAY = (120,120,140)
SHIELD_BLUE = (90,180,240)

FONT_NAME = "Consolas"

# --------------------
# Utility
# --------------------
def clamp(v, a, b):
    return max(a, min(b, v))

# --------------------
# Background (stars & planets)
# --------------------
class Star:
    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.speed = random.uniform(0.6, 2.2)
        self.size = random.randint(1, 3)
        self.phase = random.uniform(0, math.pi*2)

    def update(self, dt, h):
        self.y += self.speed * dt
        self.phase += dt * 0.1
        if self.y > h:
            self.y = -2
            self.x = random.uniform(0, WIDTH)

    def draw(self, surf):
        alpha = 150 + int(100 * math.sin(self.phase))
        color = (alpha, alpha, alpha)
        pygame.draw.circle(surf, color, (int(self.x), int(self.y)), self.size)

class Planet:
    def __init__(self, w, h):
        self.x = random.uniform(80, w - 80)
        self.y = random.uniform(-2000, -300)
        self.speed = random.uniform(0.02, 0.12)
        self.size = random.randint(40, 120)
        self.color = (
            random.randint(80, 230),
            random.randint(80, 230),
            random.randint(80, 230)
        )
        self.angle = random.uniform(0, math.pi*2)
        self.spin = random.uniform(-0.6, 0.6)

    def update(self, dt, h):
        self.y += self.speed * dt
        self.angle += self.spin * dt * 0.02
        if self.y > h + 200:
            self.x = random.uniform(80, WIDTH - 80)
            self.y = random.uniform(-1200, -300)
            self.speed = random.uniform(0.02, 0.12)
            self.size = random.randint(40, 120)
            self.color = (
                random.randint(80, 230),
                random.randint(80, 230),
                random.randint(80, 230)
            )

    def draw(self, surf):
        cx = int(self.x); cy = int(self.y)
        pygame.draw.circle(surf, self.color, (cx, cy), self.size)
        highlight_color = (min(255, self.color[0]+30), min(255, self.color[1]+30), min(255, self.color[2]+30))
        hx = cx + int(self.size * 0.25 * math.cos(self.angle))
        hy = cy - int(self.size * 0.25 * math.sin(self.angle))
        pygame.draw.circle(surf, highlight_color, (hx, hy), int(self.size * 0.22))

stars = [Star(WIDTH, HEIGHT) for _ in range(140)]
planets = [Planet(WIDTH, HEIGHT) for _ in range(3)]

# --------------------
# Visual globe for menu
# --------------------
def draw_spinning_globe(surf, cx, cy, radius, angle):
    pygame.draw.circle(surf, (12,60,110), (cx, cy), radius)
    pygame.draw.circle(surf, (24,120,200), (cx, cy), radius, 2)
    rect = pygame.Rect(cx - radius, cy - radius, radius*2, radius*2)
    for i in range(6):
        a = angle + i * 0.9
        pygame.draw.arc(surf, (80,170,220), rect, a, a + math.pi, 2)
    for j in range(-2,3):
        w = 2 if j==0 else 1
        ry = int(cy + j * (radius * 0.35))
        pygame.draw.ellipse(surf, (80,160,200), (cx - int(radius*0.85), ry - 6, int(radius*1.7), 12), w)
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
        self.x = x; self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-6, -1)
        self.color = color
        self.life = life; self.time = 0
    def update(self, dt):
        self.time += dt; self.x += self.vx; self.y += self.vy; self.vy += 10 * dt
    def draw(self, surf):
        alpha = clamp(1 - (self.time / self.life), 0, 1)
        if alpha <= 0: return
        r = int(3 * (1 - alpha) + 1)
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        col = (*self.color, int(255 * alpha))
        pygame.draw.circle(s, col, (r, r), r); surf.blit(s, (self.x - r, self.y - r))

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
        self.x = x; self.y = y; self.vy = vy; self.color = color; self.owner = owner; self.damage = damage
        self.radius = 4 if owner=="player" else 5
        self.rect = pygame.Rect(x-self.radius, y-self.radius, self.radius*2, self.radius*2)
    def update(self, dt):
        self.y += self.vy * (dt * 60 if dt < 5 else dt)
        self.rect.center = (int(self.x), int(self.y))
    def draw(self, surf): pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
    def offscreen(self): return self.y < -30 or self.y > HEIGHT + 30

class BuffDrop:
    def __init__(self, x, y, kind='multishot'):
        self.x = x; self.y = y; self.kind = kind; self.vy = 2.2; self.radius = 10
        self.rect = pygame.Rect(x - self.radius, y - self.radius, self.radius*2, self.radius*2)
        self.angle = 0
    def update(self, dt):
        self.y += self.vy * (dt * 60 if dt < 5 else dt); self.angle += dt * 5; self.rect.center = (int(self.x), int(self.y))
    def draw(self, surf):
        x = int(self.x); y = int(self.y)
        if self.kind == 'multishot':
            pygame.draw.circle(surf, YELLOW, (x, y), self.radius)
            ex = int(self.x + self.radius * math.cos(self.angle)); ey = int(self.y + self.radius * math.sin(self.angle))
            pygame.draw.line(surf, WHITE, (self.x, self.y), (ex, ey), 2)
        elif self.kind == 'shield':
            pygame.draw.circle(surf, SHIELD_BLUE, (x, y), self.radius)
            ex = int(self.x + self.radius * math.cos(self.angle)); ey = int(self.y + self.radius * math.sin(self.angle))
            pygame.draw.line(surf, WHITE, (self.x, self.y), (ex, ey), 2)
        else:  # heal / hp drop
            pygame.draw.circle(surf, RED, (x, y), self.radius)
            ex = int(self.x + self.radius * math.cos(self.angle))
            ey = int(self.y + self.radius * math.sin(self.angle))
            pygame.draw.line(surf, WHITE, (self.x, self.y), (ex, ey), 2)


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
        self.speed = PLAYER_SPEED
        # shield: absorbs multiple hits while active
        self.shield_active = False
        self.shield_end_time = 0
        self.shield_uses = 0  # time when shield effect ends
        # hit-flash indicator (visual only)
        self.hit_flash = False
        self.hit_flash_end = 0
        # micro invincibility timer
        self.invincible_until = 0

        # ultimate
        self.ultimate_count = 0; self.ultimate_needed = 10; self.ultimate_available = False
        self.ultimate_active = False; self.ultimate_end_time = 0; self.ultimate_fire_delay_ms = ULTIMATE_FIRE_DELAY_MS; self.last_ultimate_shot_time = 0

    def update(self):
        now = pygame.time.get_ticks()
        # Shield expiration: ensure shield ends when timer passes
        if getattr(self, 'shield_active', False) and getattr(self, 'shield_end_time', 0) and now > self.shield_end_time:
            self.shield_active = False
            self.shield_end_time = 0
            self.shield_uses = 0
            if hasattr(self, 'shield_uses'):
                self.shield_uses = 0

        if self.shield_active and now > self.shield_end_time:
            self.shield_active = False
            self.shield_end_time = 0
            self.shield_uses = 0

        if self.multishot_active and now > self.multishot_end_time:
            self.multishot_active = False
        if self.ultimate_active and now > self.ultimate_end_time:
            self.ultimate_active = False; self.ultimate_end_time = 0; self.last_ultimate_shot_time = 0

    def draw(self, surf):
        x, y = int(self.x), int(self.y)

        # flicker frames (visual only, no invincibility)
        if self.hit_flash:
            if pygame.time.get_ticks() > self.hit_flash_end:
                self.hit_flash = False
            else:
                # simple flicker: skip every other frame
                if (pygame.time.get_ticks() // 60) % 2 == 0:
                    return  # skip drawing this frame for flicker

        # normal draw
        pts = [
            (x, y - self.radius),
            (x - self.radius, y + self.radius),
            (x + self.radius, y + self.radius)
        ]
        pygame.draw.polygon(surf, CYAN, pts)
        pygame.draw.polygon(surf, WHITE, pts, 2)

        # shield visual
        if self.shield_active and self.shield_uses > 0:
            pygame.draw.circle(surf, SHIELD_BLUE, (x,y), self.radius + 10, 3)

    def can_shoot(self):
        return pygame.time.get_ticks() - self.last_shot_time >= self.fire_delay_ms

    def shoot(self):
        self.last_shot_time = pygame.time.get_ticks(); bullets = []
        if self.multishot_active:
            for s in (-14,0,14): bullets.append(Bullet(self.x + s, self.y - self.radius - 4, PLAYER_BULLET_SPEED, YELLOW, "player", damage=1))
        else:
            bullets.append(Bullet(self.x, self.y - self.radius - 6, PLAYER_BULLET_SPEED, YELLOW, "player", damage=1))
        return bullets

    def take_damage(self, amount=1, source=None, knockback=0):
        """
        amount: HP to remove
        source: (sx, sy) tuple indicating position of hit origin (bullet or enemy)
        knockback: pixels to push player away from source (visual reaction)
        Returns True if player died
        """
        # shield absorbs up to its uses
        if self.shield_active and self.shield_uses > 0:
            self.shield_uses -= amount
            if self.shield_uses <= 0:
                self.shield_active = False; self.shield_uses = 0

            # trigger flash and knockback even if shield absorbs
            self.hit_flash = True
            self.hit_flash_end = pygame.time.get_ticks() + 180
            if source and knockback:
                sx, sy = source
                dx = self.x - sx; dy = self.y - sy
                dist = math.hypot(dx, dy)
                if dist == 0:
                    # random small nudge if overlapping exactly
                    angle = random.uniform(0, math.pi*2)
                    dx = math.cos(angle); dy = math.sin(angle); dist = 1.0
                nx = dx / dist; ny = dy / dist
                self.x += nx * knockback
                self.y += ny * knockback
                self.x = clamp(self.x, self.radius, WIDTH - self.radius)
                self.y = clamp(self.y, self.radius, HEIGHT - self.radius)
            return False

        # normal damage
        self.hp -= amount

        # flash feedback (NO invincibility)
        self.hit_flash = True
        self.hit_flash_end = pygame.time.get_ticks() + 180

        # apply knockback if source provided
        if source and knockback:
            sx, sy = source
            dx = self.x - sx; dy = self.y - sy
            dist = math.hypot(dx, dy)
            if dist == 0:
                angle = random.uniform(0, math.pi*2)
                dx = math.cos(angle); dy = math.sin(angle); dist = 1.0
            nx = dx / dist; ny = dy / dist
            self.x += nx * knockback
            self.y += ny * knockback
            self.x = clamp(self.x, self.radius, WIDTH - self.radius)
            self.y = clamp(self.y, self.radius, HEIGHT - self.radius)

        if self.hp <= 0:
            self.hp = 0; return True
        return False

    def use_ultimate_once(self):
        bullets = []
        offsets = [-40, -20, 0, 20, 40]
        for s in offsets:
            bullets.append(Bullet(self.x + s, self.y - self.radius - 6, int(PLAYER_BULLET_SPEED * 1.6), YELLOW, "player", damage=2))
        return bullets

# --------------------
# Enemy
# --------------------
class Enemy:
    def __init__(self, x, y, etype="basic", hp=1):
        self.base_x = x; self.base_y = y; self.x = x; self.y = y
        self.etype = etype
        self.w = 36; self.h = 30; self.hp = hp
        self.hp_max = hp; self.alive = True; self.arm_state = 0
        self.shoot_timer = random.uniform(0.4, 2.4); self.osc_phase = random.uniform(0, math.pi*2)
        self.spin_radius = random.uniform(4, 18)
        self.spin_speed = random.uniform(1.0, 3.0) * (0.6 if etype=="tank" else 1.0)
        self.bob_amp = random.uniform(0.0, 4.0)
        # physics for dynamic spawn
        self.vx = None; self.vy = None; self.curve_phase = 0.0; self.curve_speed = 0.0; self.curve_amount = 0.0

    def rect(self):
        return pygame.Rect(int(self.x - self.w/2), int(self.y - self.h/2), self.w, self.h)
    def toggle_arm(self): self.arm_state = 1 - self.arm_state

    def update(self, step_dx, step_dy, dt, wave, elapsed):
        if not self.alive: return
        # dynamic (free-moving) enemies
        if self.vx is not None and self.vy is not None:
            self.curve_phase += self.curve_speed * dt
            cx = math.sin(self.curve_phase) * self.curve_amount * (0.5 if self.etype == 'fast' else 1.0)
            self.x += (self.vx * (dt * 60))
            self.y += (self.vy * (dt * 60))
            self.x += cx * dt * 18
            if self.etype == "zig":
                self.y += math.sin(elapsed*2 + self.osc_phase) * 0.8
            # if enemy goes far off screen, reposition them back to top (respawn behavior)
            if self.x < -200 or self.x > WIDTH + 200 or self.y > HEIGHT + 200:
                # reposition to top with new parameters (keeps game fun)
                self.x = random.randint(40, WIDTH - 40)
                self.y = -40
                self.vx = random.uniform(-0.6, 0.6)
                self.vy = random.uniform(1.2, 2.5)
                self.curve_phase = random.uniform(0, math.pi*2)
                self.curve_speed = random.uniform(0.4, 1.2)
                self.curve_amount = random.randint(8, 38)
            base_rate = 1.0
            if self.etype == "fast": base_rate = 0.5
            elif self.etype == "tank": base_rate = 1.6
            self.shoot_timer -= dt * (1.0 / base_rate)
            return

        # formation style
        self.base_x += step_dx; self.base_y += step_dy
        if self.etype == "zig":
            bob = math.sin(elapsed*2 + self.osc_phase) * 6
        elif self.etype == "tank":
            bob = math.sin(elapsed*1.2 + self.osc_phase) * 3
        else:
            bob = math.sin(elapsed*1.6 + self.osc_phase) * self.bob_amp
        angle = elapsed * self.spin_speed + self.osc_phase
        self.x = self.base_x + math.cos(angle) * self.spin_radius
        self.y = self.base_y + math.sin(angle) * (self.spin_radius * 0.6) + bob
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
        draw_boss_healthbar(surf, int(self.x-60), int(self.y-self.h//2-20), 120, 14, self.hp, self.hp_max)
        pygame.draw.circle(surf, BLACK, (int(self.x - 24), int(self.y - 8)), 8)
        pygame.draw.circle(surf, BLACK, (int(self.x + 24), int(self.y - 8)), 8)
        for i in range(-3,4): tx = int(self.x + i*10); ty = int(self.y + 16); pygame.draw.rect(surf, WHITE, (tx-3, ty, 6, 8))

# --------------------
# Wave Manager (now accepts player_pos to avoid spawning on player)
# --------------------
class WaveManager:
    def __init__(self, player_pos=None):
        self.wave_num = 0
        self.enemies = []
        self.step_interval = 0.8
        self.step_acc = 0.0
        self.direction = 1
        self.elapsed = 0.0
        self.base_speed = 28.0
        self.enemy_shoot_prob = 0.006
        self.spawn_wave(player_pos)

    def spawn_wave(self, player_pos=None):
        self.wave_num += 1
        self.enemies = []  # Reset enemies each wave
        total = 6 + self.wave_num * 1
        formation_count = max(0, min(ENEMIES_PER_ROW, total // 3))
        dynamic_count = total - formation_count

        # Formation spawn
        if formation_count > 0:
            start_x = max(80, WIDTH // 2 - (formation_count // 2) * 50)
            y = 90
            for i in range(formation_count):
                x = start_x + i * 50
                t = random.random()
                if t < 0.62:
                    etype = 'basic'
                    hp = 1
                elif t < 0.82:
                    etype = 'fast'
                    hp = 1
                elif t < 0.94:
                    etype = 'zig'
                    hp = 1
                else:
                    etype = 'tank'
                    hp = 2 + (self.wave_num // 3)

                # Create enemy and add to the list
                e = Enemy(x, y, etype=etype, hp=hp)
                if etype == 'tank':
                    e.spin_radius = random.uniform(8, 22)
                    e.spin_speed *= 0.7
                if etype == 'fast':
                    e.spin_radius = random.uniform(2, 8)
                    e.spin_speed *= 1.6
                self.enemies.append(e)

        # Dynamic spawn
        for i in range(dynamic_count):
            etype = random.choice(['basic', 'fast', 'zig', 'tank'])
            side = random.choice(['top', 'left', 'right'])

            placed = False
            attempts = 0
            while not placed and attempts < 40:
                attempts += 1
                # Dynamic spawn logic based on side
                if side == 'top':
                    x = random.randint(40, WIDTH - 40)
                    y = -40
                    vx = random.uniform(-0.6, 0.6)
                    vy = random.uniform(1.2, 2.5)
                elif side == 'left':
                    x = -40
                    y = random.randint(60, HEIGHT - 220)
                    vx = random.uniform(1.0, 2.6)
                    vy = random.uniform(-0.2, 0.4)
                else:
                    x = WIDTH + 40
                    y = random.randint(60, HEIGHT - 220)
                    vx = random.uniform(-2.6, -1.0)
                    vy = random.uniform(-0.2, 0.4)

                # Avoid spawning too close to the player
                if player_pos is None or math.hypot(x - player_pos[0], y - player_pos[1]) > 140:
                    placed = True

            # Add enemy to list
            e = Enemy(x, y, etype=etype, hp=(2 if etype == 'tank' else 1))
            e.vx = vx
            e.vy = vy
            e.curve_phase = random.uniform(0, math.pi * 2)
            e.curve_speed = random.uniform(0.4, 1.2)
            e.curve_amount = random.randint(8, 38)

            if etype == 'fast':
                e.vx *= 1.2
                e.vy *= 1.1
                e.curve_amount *= 0.6
            if etype == 'tank':
                e.vx *= 0.6
                e.vy *= 0.75
                e.curve_amount *= 1.1

            self.enemies.append(e)

        # Boss waves
        if self.wave_num % BOSS_EVERY == 0:
            boss_y = min(140, PLAYER_Y - 220)
            boss_hp = 20 + int(self.wave_num * 3.5)
            boss = Boss(WIDTH // 2, boss_y, hp=boss_hp)
            self.enemies.append(boss)

        # Print debug message for the wave and enemies spawned
        print(f"Spawning wave {self.wave_num} with {len(self.enemies)} enemies.")
    
        # Adjust difficulty for next wave
        self.step_interval = max(0.95 - (self.wave_num * 0.02), 0.35)
        self.base_speed = 20 + self.wave_num * 2.2
        self.enemy_shoot_prob = clamp(0.004 + self.wave_num * 0.0009, 0.004, 0.02)

    def update(self, dt):
        self.elapsed += dt
        self.step_acc += dt
        if self.step_acc >= self.step_interval:
            times = int(self.step_acc // self.step_interval)
            self.step_acc -= times * self.step_interval
            step_size = self.base_speed * self.step_interval
            for _ in range(times):
                dx = step_size * self.direction
                will_hit = False
                for e in self.enemies:
                    if not e.alive: continue
                    if getattr(e, 'vx', None) is not None: continue
                    nx = e.base_x + dx
                    if nx - e.w / 2 < 20 or nx + e.w / 2 > WIDTH - 20:
                        will_hit = True
                        break
                if will_hit:
                    for e in self.enemies:
                        if e.alive and getattr(e, 'vx', None) is None:
                            e.base_y += ENEMY_DROP
                            e.toggle_arm()
                    self.direction *= -1
                else:
                    for e in self.enemies:
                        if e.alive and getattr(e, 'vx', None) is None:
                            e.base_x += dx
                            e.toggle_arm()

    def any_alive(self):
        return any(e.alive for e in self.enemies)


# --------------------
# Shop
# --------------------
class Shop:
    def __init__(self): pass
    def open(self, screen, player):
        font = pygame.font.SysFont(FONT_NAME, 24); big = pygame.font.SysFont(FONT_NAME, 40)
        options = [("Faster Fire (reduce delay by 20ms)", SHOP_FIRE_RATE_PRICE, "fire"), ("Increase Max HP (+1)", SHOP_MAX_HP_PRICE, "hp"), ("Heal to Full (+heal)", 1300, "heal")]
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
                            if code == "fire": """
Alien Invaders — Fixed Edition (with hit-flash + knockback + 15s invincibility on hit)
- Keeps mouse-drag + keyboard movement (unchanged)
- Shield pickup gives 3 hits
- Prevents enemies spawning on top of the player (uses player position when spawning)
- Repositions dynamic enemies that fly off-screen to the top instead of deleting them
- Collision: enemy body hit deals 1 HP and grants 15s temporary invincibility
- Clean, ready-to-run single-file script

Run: python alien_invaders_fixed_knockback_invincible.py
Requires: pygame (pip install pygame)
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
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    except Exception:
        pass

# --------------------
# Configuration
# --------------------
WIDTH, HEIGHT = 880, 720
FPS = 60

# Player
PLAYER_START_X = WIDTH // 2
PLAYER_Y = HEIGHT - 70
PLAYER_RADIUS = 18
PLAYER_BASE_HP = 6
PLAYER_BASE_FIRE_DELAY_MS = 220
PLAYER_SPEED = 260

# Bullets
PLAYER_BULLET_SPEED = -10
ENEMY_BULLET_SPEED_BASE = 3.0

# Buffs
BUFF_CHANCE = 0.18
BUFF_DURATION_MS = 5000

# Ultimate
ULTIMATE_DURATION_MS = 8000
ULTIMATE_FIRE_DELAY_MS = 180

# Waves
ENEMIES_PER_ROW = 10
BOSS_EVERY = 5
ENEMY_DROP = 24

# Shop prices
SHOP_FIRE_RATE_PRICE = 800
SHOP_MAX_HP_PRICE = 1000
SHOP_SPEED_PRICE = 700

# Particles
PARTICLE_COUNT = 14

# Knockback (light = 15 px as requested)
KNOCKBACK_PIXELS = 15

# Invincibility (milliseconds)
INVINCIBILITY_MS = 500 # 3 seconds of invincibility after hit

# Colors
WHITE = (255,255,255)
BLACK = (10,10,18)
RED = (230,60,60)
GREEN = (80,230,120)
YELLOW = (255,220,50)
CYAN = (80,200,235)
ORANGE = (255,150,60)
GRAY = (120,120,140)
SHIELD_BLUE = (90,180,240)

FONT_NAME = "Consolas"

# --------------------
# Utility
# --------------------
def clamp(v, a, b):
    return max(a, min(b, v))

# --------------------
# Background (stars & planets)
# --------------------
class Star:
    def __init__(self, w, h):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.speed = random.uniform(0.6, 2.2)
        self.size = random.randint(1, 3)
        self.phase = random.uniform(0, math.pi*2)

    def update(self, dt, h):
        self.y += self.speed * dt
        self.phase += dt * 0.1
        if self.y > h:
            self.y = -2
            self.x = random.uniform(0, WIDTH)

    def draw(self, surf):
        alpha = 150 + int(100 * math.sin(self.phase))
        color = (alpha, alpha, alpha)
        pygame.draw.circle(surf, color, (int(self.x), int(self.y)), self.size)

class Planet:
    def __init__(self, w, h):
        self.x = random.uniform(80, w - 80)
        self.y = random.uniform(-2000, -300)
        self.speed = random.uniform(0.02, 0.12)
        self.size = random.randint(40, 120)
        self.color = (
            random.randint(80, 230),
            random.randint(80, 230),
            random.randint(80, 230)
        )
        self.angle = random.uniform(0, math.pi*2)
        self.spin = random.uniform(-0.6, 0.6)

    def update(self, dt, h):
        self.y += self.speed * dt
        self.angle += self.spin * dt * 0.02
        if self.y > h + 200:
            self.x = random.uniform(80, WIDTH - 80)
            self.y = random.uniform(-1200, -300)
            self.speed = random.uniform(0.02, 0.12)
            self.size = random.randint(40, 120)
            self.color = (
                random.randint(80, 230),
                random.randint(80, 230),
                random.randint(80, 230)
            )

    def draw(self, surf):
        cx = int(self.x); cy = int(self.y)
        pygame.draw.circle(surf, self.color, (cx, cy), self.size)
        highlight_color = (min(255, self.color[0]+30), min(255, self.color[1]+30), min(255, self.color[2]+30))
        hx = cx + int(self.size * 0.25 * math.cos(self.angle))
        hy = cy - int(self.size * 0.25 * math.sin(self.angle))
        pygame.draw.circle(surf, highlight_color, (hx, hy), int(self.size * 0.22))

stars = [Star(WIDTH, HEIGHT) for _ in range(140)]
planets = [Planet(WIDTH, HEIGHT) for _ in range(3)]

# --------------------
# Visual globe for menu
# --------------------
def draw_spinning_globe(surf, cx, cy, radius, angle):
    pygame.draw.circle(surf, (12,60,110), (cx, cy), radius)
    pygame.draw.circle(surf, (24,120,200), (cx, cy), radius, 2)
    rect = pygame.Rect(cx - radius, cy - radius, radius*2, radius*2)
    for i in range(6):
        a = angle + i * 0.9
        pygame.draw.arc(surf, (80,170,220), rect, a, a + math.pi, 2)
    for j in range(-2,3):
        w = 2 if j==0 else 1
        ry = int(cy + j * (radius * 0.35))
        pygame.draw.ellipse(surf, (80,160,200), (cx - int(radius*0.85), ry - 6, int(radius*1.7), 12), w)
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
        self.x = x; self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-6, -1)
        self.color = color
        self.life = life; self.time = 0
    def update(self, dt):
        self.time += dt; self.x += self.vx; self.y += self.vy; self.vy += 10 * dt
    def draw(self, surf):
        alpha = clamp(1 - (self.time / self.life), 0, 1)
        if alpha <= 0: return
        r = int(3 * (1 - alpha) + 1)
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        col = (*self.color, int(255 * alpha))
        pygame.draw.circle(s, col, (r, r), r); surf.blit(s, (self.x - r, self.y - r))

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
        self.x = x; self.y = y; self.vy = vy; self.color = color; self.owner = owner; self.damage = damage
        self.radius = 4 if owner=="player" else 5
        self.rect = pygame.Rect(x-self.radius, y-self.radius, self.radius*2, self.radius*2)
    def update(self, dt):
        self.y += self.vy * (dt * 60 if dt < 5 else dt)
        self.rect.center = (int(self.x), int(self.y))
    def draw(self, surf): pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
    def offscreen(self): return self.y < -30 or self.y > HEIGHT + 30

class BuffDrop:
    def __init__(self, x, y, kind='multishot'):
        self.x = x; self.y = y; self.kind = kind; self.vy = 2.2; self.radius = 10
        self.rect = pygame.Rect(x - self.radius, y - self.radius, self.radius*2, self.radius*2)
        self.angle = 0
    def update(self, dt):
        self.y += self.vy * (dt * 60 if dt < 5 else dt); self.angle += dt * 5; self.rect.center = (int(self.x), int(self.y))
    def draw(self, surf):
        x = int(self.x); y = int(self.y)
        if self.kind == 'multishot':
            pygame.draw.circle(surf, YELLOW, (x, y), self.radius)
            ex = int(self.x + self.radius * math.cos(self.angle)); ey = int(self.y + self.radius * math.sin(self.angle))
            pygame.draw.line(surf, WHITE, (self.x, self.y), (ex, ey), 2)
        elif self.kind == 'shield':
            pygame.draw.circle(surf, SHIELD_BLUE, (x, y), self.radius)
            ex = int(self.x + self.radius * math.cos(self.angle)); ey = int(self.y + self.radius * math.sin(self.angle))
            pygame.draw.line(surf, WHITE, (self.x, self.y), (ex, ey), 2)
        elif self.kind == 'heal':
            pygame.draw.circle(surf, GREEN, (x, y), self.radius)
            ex = int(self.x + self.radius * math.cos(self.angle)); ey = int(self.y + self.radius * math.sin(self.angle))
            pygame.draw.line(surf, WHITE, (self.x, self.y), (ex, ey), 2)

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
        self.speed = PLAYER_SPEED
        # shield: absorbs multiple hits while active
        self.shield_active = False
        self.shield_uses = 0
        # hit-flash indicator (visual only)
        self.hit_flash = False
        self.hit_flash_end = 0
        # micro invincibility timer (ms since epoch)
        self.invincible_until = 0

        # ultimate
        self.ultimate_count = 0; self.ultimate_needed = 10; self.ultimate_available = False
        self.ultimate_active = False; self.ultimate_end_time = 0; self.ultimate_fire_delay_ms = ULTIMATE_FIRE_DELAY_MS; self.last_ultimate_shot_time = 0

    def update(self):
        now = pygame.time.get_ticks()
        # Shield expiration: ensure shield ends when timer passes
        if getattr(self, 'shield_active', False) and getattr(self, 'shield_end_time', 0) and now > self.shield_end_time:
            self.shield_active = False
            self.shield_end_time = 0
            self.shield_uses = 0
            if hasattr(self, 'shield_uses'):
                self.shield_uses = 0

        if self.multishot_active and now > self.multishot_end_time:
            self.multishot_active = False
        if self.ultimate_active and now > self.ultimate_end_time:
            self.ultimate_active = False; self.ultimate_end_time = 0; self.last_ultimate_shot_time = 0

    def draw(self, surf):
        x, y = int(self.x), int(self.y)

        # show invincibility ring if active
        now = pygame.time.get_ticks()
        if now < self.invincible_until:
            alpha = 120 + int(80 * math.sin(now * 0.01))
            ring_s = pygame.Surface((self.radius*4, self.radius*4), pygame.SRCALPHA)
            pygame.draw.circle(ring_s, (200,200,255,int(alpha)), (self.radius*2, self.radius*2), self.radius+14, 6)
            surf.blit(ring_s, (x - self.radius*2, y - self.radius*2))

        # flicker frames (visual only)
        if self.hit_flash:
            if pygame.time.get_ticks() > self.hit_flash_end:
                self.hit_flash = False
            else:
                # simple flicker: skip every other frame
                if (pygame.time.get_ticks() // 60) % 2 == 0:
                    return  # skip drawing this frame for flicker

        # normal draw
        pts = [
            (x, y - self.radius),
            (x - self.radius, y + self.radius),
            (x + self.radius, y + self.radius)
        ]
        pygame.draw.polygon(surf, CYAN, pts)
        pygame.draw.polygon(surf, WHITE, pts, 2)

        # shield visual
        if self.shield_active and self.shield_uses > 0:
            pygame.draw.circle(surf, SHIELD_BLUE, (x,y), self.radius + 10, 3)

    def can_shoot(self):
        return pygame.time.get_ticks() - self.last_shot_time >= self.fire_delay_ms

    def shoot(self):
        self.last_shot_time = pygame.time.get_ticks(); bullets = []
        if self.multishot_active:
            for s in (-14,0,14): bullets.append(Bullet(self.x + s, self.y - self.radius - 4, PLAYER_BULLET_SPEED, YELLOW, "player", damage=1))
        else:
            bullets.append(Bullet(self.x, self.y - self.radius - 6, PLAYER_BULLET_SPEED, YELLOW, "player", damage=1))
        return bullets

    def take_damage(self, amount=1, source=None, knockback=0):
        """
        amount: HP to remove
        source: (sx, sy) tuple indicating position of hit origin (bullet or enemy)
        knockback: pixels to push player away from source (visual reaction)
        Returns True if player died
        """
        now = pygame.time.get_ticks()

        # If currently invincible, ignore damage
        if now < self.invincible_until:
            # still apply a small hit flash for feedback but no HP loss
            self.hit_flash = True
            self.hit_flash_end = now + 180
            return False

        # shield absorbs up to its uses
        if self.shield_active and self.shield_uses > 0:
            self.shield_uses -= amount
            if self.shield_uses <= 0:
                self.shield_active = False; self.shield_uses = 0

            # trigger flash and knockback even if shield absorbs
            self.hit_flash = True
            self.hit_flash_end = now + 180

            # apply invincibility to prevent immediate follow-up hits
            self.invincible_until = now + INVINCIBILITY_MS

            if source and knockback:
                sx, sy = source
                dx = self.x - sx; dy = self.y - sy
                dist = math.hypot(dx, dy)
                if dist == 0:
                    # random small nudge if overlapping exactly
                    angle = random.uniform(0, math.pi*2)
                    dx = math.cos(angle); dy = math.sin(angle); dist = 1.0
                nx = dx / dist; ny = dy / dist
                self.x += nx * knockback
                self.y += ny * knockback
                self.x = clamp(self.x, self.radius, WIDTH - self.radius)
                self.y = clamp(self.y, self.radius, HEIGHT - self.radius)
            return False

        # normal damage
        self.hp -= amount

        # flash feedback
        self.hit_flash = True
        self.hit_flash_end = now + 180

        # apply invincibility to avoid being hit again for a while
        self.invincible_until = now + INVINCIBILITY_MS

        # apply knockback if source provided
        if source and knockback:
            sx, sy = source
            dx = self.x - sx; dy = self.y - sy
            dist = math.hypot(dx, dy)
            if dist == 0:
                angle = random.uniform(0, math.pi*2)
                dx = math.cos(angle); dy = math.sin(angle); dist = 1.0
            nx = dx / dist; ny = dy / dist
            self.x += nx * knockback
            self.y += ny * knockback
            self.x = clamp(self.x, self.radius, WIDTH - self.radius)
            self.y = clamp(self.y, self.radius, HEIGHT - self.radius)

        if self.hp <= 0:
            self.hp = 0; return True
        return False

    def use_ultimate_once(self):
        bullets = []
        offsets = [-40, -20, 0, 20, 40]
        for s in offsets:
            bullets.append(Bullet(self.x + s, self.y - self.radius - 6, int(PLAYER_BULLET_SPEED * 1.6), YELLOW, "player", damage=2))
        return bullets

# --------------------
# Enemy
# --------------------
class Enemy:
    def __init__(self, x, y, etype="basic", hp=1):
        self.base_x = x; self.base_y = y; self.x = x; self.y = y
        self.etype = etype
        self.w = 36; self.h = 30; self.hp = hp
        self.hp_max = hp; self.alive = True; self.arm_state = 0
        self.shoot_timer = random.uniform(0.4, 2.4); self.osc_phase = random.uniform(0, math.pi*2)
        self.spin_radius = random.uniform(4, 18)
        self.spin_speed = random.uniform(1.0, 3.0) * (0.6 if etype=="tank" else 1.0)
        self.bob_amp = random.uniform(0.0, 4.0)
        # physics for dynamic spawn
        self.vx = None; self.vy = None; self.curve_phase = 0.0; self.curve_speed = 0.0; self.curve_amount = 0.0

    def rect(self):
        return pygame.Rect(int(self.x - self.w/2), int(self.y - self.h/2), self.w, self.h)
    def toggle_arm(self): self.arm_state = 1 - self.arm_state

    def update(self, step_dx, step_dy, dt, wave, elapsed):
        if not self.alive: return
        # dynamic (free-moving) enemies
        if self.vx is not None and self.vy is not None:
            self.curve_phase += self.curve_speed * dt
            cx = math.sin(self.curve_phase) * self.curve_amount * (0.5 if self.etype == 'fast' else 1.0)
            self.x += (self.vx * (dt * 60))
            self.y += (self.vy * (dt * 60))
            self.x += cx * dt * 18
            if self.etype == "zig":
                self.y += math.sin(elapsed*2 + self.osc_phase) * 0.8
            # if enemy goes far off screen, reposition them back to top (respawn behavior)
            if self.x < -200 or self.x > WIDTH + 200 or self.y > HEIGHT + 200:
                # reposition to top with new parameters (keeps game fun)
                self.x = random.randint(40, WIDTH - 40)
                self.y = -40
                self.vx = random.uniform(-0.6, 0.6)
                self.vy = random.uniform(1.2, 2.5)
                self.curve_phase = random.uniform(0, math.pi*2)
                self.curve_speed = random.uniform(0.4, 1.2)
                self.curve_amount = random.randint(8, 38)
            base_rate = 1.0
            if self.etype == "fast": base_rate = 0.5
            elif self.etype == "tank": base_rate = 1.6
            self.shoot_timer -= dt * (1.0 / base_rate)
            return

        # formation style
        self.base_x += step_dx; self.base_y += step_dy
        if self.etype == "zig":
            bob = math.sin(elapsed*2 + self.osc_phase) * 6
        elif self.etype == "tank":
            bob = math.sin(elapsed*1.2 + self.osc_phase) * 3
        else:
            bob = math.sin(elapsed*1.6 + self.osc_phase) * self.bob_amp
        angle = elapsed * self.spin_speed + self.osc_phase
        self.x = self.base_x + math.cos(angle) * self.spin_radius
        self.y = self.base_y + math.sin(angle) * (self.spin_radius * 0.6) + bob
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
        draw_boss_healthbar(surf, int(self.x-60), int(self.y-self.h//2-20), 120, 14, self.hp, self.hp_max)
        pygame.draw.circle(surf, BLACK, (int(self.x - 24), int(self.y - 8)), 8)
        pygame.draw.circle(surf, BLACK, (int(self.x + 24), int(self.y - 8)), 8)
        for i in range(-3,4): tx = int(self.x + i*10); ty = int(self.y + 16); pygame.draw.rect(surf, WHITE, (tx-3, ty, 6, 8))

# --------------------
# Wave Manager (now accepts player_pos to avoid spawning on player)
# --------------------
class WaveManager:
    def __init__(self, player_pos=None):
        self.wave_num = 0; self.enemies = []
        self.step_interval = 0.8; self.step_acc = 0.0; self.direction = 1; self.elapsed = 0.0
        self.base_speed = 28.0; self.enemy_shoot_prob = 0.006
        self.spawn_wave(player_pos)

    def spawn_wave(self, player_pos=None):
        self.wave_num += 1
        self.enemies = []
        total = 6 + self.wave_num * 1
        formation_count = max(0, min(ENEMIES_PER_ROW, total // 3))
        dynamic_count = total - formation_count

        # formation
        if formation_count > 0:
            start_x = max(80, WIDTH//2 - (formation_count//2)*50)
            y = 90
            for i in range(formation_count):
                x = start_x + i * 50
                t = random.random()
                if t < 0.62: etype='basic'; hp=1
                elif t < 0.82: etype='fast'; hp=1
                elif t < 0.94: etype='zig'; hp=1
                else: etype='tank'; hp=2 + (self.wave_num//3)
                e = Enemy(x,y,etype=etype,hp=hp)
                if etype=='tank': e.spin_radius = random.uniform(8, 22); e.spin_speed *= 0.7
                if etype=='fast': e.spin_radius = random.uniform(2, 8); e.spin_speed *= 1.6
                self.enemies.append(e)

        # dynamic spawns
        for i in range(dynamic_count):
            etype = random.choice(['basic', 'fast', 'zig', 'tank'])
            # pick side
            side = random.choice(['top','left','right'])
            # pick position while avoiding player's area if provided
            placed = False
            attempts = 0
            while not placed and attempts < 40:
                attempts += 1
                if side == 'top':
                    x = random.randint(40, WIDTH - 40); y = -40; vx = random.uniform(-0.6, 0.6); vy = random.uniform(1.2, 2.5)
                elif side == 'left':
                    x = -40; y = random.randint(60, HEIGHT - 220); vx = random.uniform(1.0, 2.6); vy = random.uniform(-0.2, 0.4)
                else:
                    x = WIDTH + 40; y = random.randint(60, HEIGHT - 220); vx = random.uniform(-2.6, -1.0); vy = random.uniform(-0.2, 0.4)

                if player_pos is None:
                    placed = True
                else:
                    px, py = player_pos
                    if math.hypot(x - px, y - py) > 140:
                        placed = True
            e = Enemy(x, y, etype=etype, hp=(2 if etype=='tank' else 1))
            e.vx = vx; e.vy = vy; e.curve_phase = random.uniform(0, math.pi*2)
            e.curve_speed = random.uniform(0.4, 1.2); e.curve_amount = random.randint(8, 38)
            if etype == 'fast': e.vx *= 1.2; e.vy *= 1.1; e.curve_amount *= 0.6
            if etype == 'tank': e.vx *= 0.6; e.vy *= 0.75; e.curve_amount *= 1.1
            self.enemies.append(e)

        # boss waves
        if self.wave_num % BOSS_EVERY == 0:
            boss_y = min(140, PLAYER_Y - 220)
            boss = Boss(WIDTH//2, boss_y, hp=12 + self.wave_num*2)
            self.enemies.append(boss)

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
                    if getattr(e,'vx',None) is not None: continue
                    nx = e.base_x + dx
                    if nx - e.w/2 < 20 or nx + e.w/2 > WIDTH - 20:
                        will_hit = True; break
                if will_hit:
                    for e in self.enemies:
                        if e.alive and getattr(e,'vx',None) is None: e.base_y += ENEMY_DROP; e.toggle_arm()
                    self.direction *= -1
                else:
                    for e in self.enemies:
                        if e.alive and getattr(e,'vx',None) is None: e.base_x += dx; e.toggle_arm()

    def any_alive(self):
        return any(e.alive for e in self.enemies)

# --------------------
# Shop
# --------------------
class Shop:
    def __init__(self): pass
    def open(self, screen, player):
        font = pygame.font.SysFont(FONT_NAME, 24); big = pygame.font.SysFont(FONT_NAME, 40)
        options = [("Faster Fire (reduce delay by 20ms)", SHOP_FIRE_RATE_PRICE, "fire"), ("Increase Max HP (+1)", SHOP_MAX_HP_PRICE, "hp"), ("Heal to Full (+heal)", 1300, "heal")]
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
                            if code == "fire": player.fire_delay_ms = max(80, player.fire_delay_ms - 20)
                            elif code == "hp": player.hp_max += 1; player.hp += 1           
                        elif code == "heal":
                            player.hp = player.hp_max
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    mx,my = pygame.mouse.get_pos(); base_y = 240
                    for i,op in enumerate(options):
                        rect = pygame.Rect(180, base_y + i*60, 520, 48)
                        if rect.collidepoint(mx,my): selected = i; _,cost,code = options[i]
                        if player.score >= cost:
                            player.score -= cost
                            if code == "fire": player.fire_delay_ms = max(80, player.fire_delay_ms - 20)
                            elif code == "hp": player.hp_max += 1; player.hp += 1                  
                        elif code == "heal":
                            player.hp = player.hp_max
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
# Main Game
# --------------------
def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Alien Invaders The Sequel to The Prequel to The Original Sequel Continuation Remastered Enhanced Edition")
    pygame.display.set_icon(pygame.image.load('C:/Users/azgro/Downloads/Alien Invaders/icon.png'))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(FONT_NAME, 18)
    bigfont = pygame.font.SysFont(FONT_NAME, 40)

    state = 'menu'
    menu_blink = 0.0
    fade_alpha = 0.0

    def reset_game():
        nonlocal player, wave, bullets, enemy_bullets, drops, explosions, game_over, in_shop, time_since_wave_win, shop, start_time
        player = Player()
        wave = WaveManager(player_pos=(player.x, player.y))
        shop = Shop()
        bullets = []; enemy_bullets = []; drops = []; explosions = []
        game_over = False; in_shop = False; time_since_wave_win = 0.0
        start_time = pygame.time.get_ticks()

    # initial setup
    player = Player(); wave = WaveManager(player_pos=(PLAYER_START_X, PLAYER_Y)); shop = Shop()
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
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if state == 'menu':
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                    state = 'playing'; reset_game()
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
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
                    if ev.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()
                    if ev.key == pygame.K_r and game_over: reset_game(); state = 'playing'
                    if ev.key == pygame.K_SPACE:
                        now = pygame.time.get_ticks()
                        if player.ultimate_available and not player.ultimate_active:
                            player.ultimate_active = True; player.ultimate_end_time = now + ULTIMATE_DURATION_MS; player.last_ultimate_shot_time = 0; player.ultimate_available = False; player.ultimate_count = 0
                        else:
                            if not player.ultimate_active and player.can_shoot(): bullets.extend(player.shoot())
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    mx,my = ev.pos
                    if math.hypot(mx - player.x, my - player.y) < 120:
                        dragging = True; drag_offset_x = player.x - mx
                if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                    dragging = False
                if ev.type == pygame.MOUSEMOTION and dragging:
                    mx,my = ev.pos
                    player.x = mx; player.y = my
                    player.x = clamp(player.x, player.radius, WIDTH - player.radius)
                    player.y = clamp(player.y, player.radius, HEIGHT - player.radius)
            elif state == 'gameover':
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and fade_alpha >= 255: state = 'menu'
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN and fade_alpha >= 255: state = 'menu'

        # MENU
        if state == 'menu':
            screen.fill(BLACK)
            for p in planets: p.update(dt * 60, HEIGHT)
            for s in stars: s.update(dt * 60, HEIGHT)
            for p in planets: p.draw(screen)
            for s in stars: s.draw(screen)
            title = bigfont.render("ALIEN INVADERS", True, CYAN); screen.blit(title, (WIDTH//2 - title.get_width()//2, 140))
            subtitle = font.render("Remastered Enhanced Edition", True, GRAY); screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 200))
            draw_spinning_globe(screen, WIDTH//2, 320, 80, menu_blink * 0.9)
            prompt_surf = font.render("Press ENTER or Click to Play", True, WHITE); shadow = font.render("Press ENTER or Click to Play", True, (40,40,40))
            screen.blit(shadow, (WIDTH//2 - prompt_surf.get_width()//2 + 2, 420 + 2)); screen.blit(prompt_surf, (WIDTH//2 - prompt_surf.get_width()//2, 420))
            tip = font.render("YOUR PLANET IS BEING INVADED!", True, GRAY); screen.blit(tip, (WIDTH//2 - tip.get_width()//2, HEIGHT-60))
            pygame.display.flip(); continue

        # PLAYING
        if state == 'playing':
            keys = pygame.key.get_pressed()
            spd = player.speed * dt * 60
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: player.x -= spd
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: player.x += spd
            if keys[pygame.K_UP] or keys[pygame.K_w]: player.y -= spd
            if keys[pygame.K_DOWN] or keys[pygame.K_s]: player.y += spd
            player.x = clamp(player.x, player.radius, WIDTH - player.radius)
            player.y = clamp(player.y, player.radius, HEIGHT - player.radius)

            player.update()
            for p in planets: p.update(dt * 60, HEIGHT)
            for s in stars: s.update(dt * 60, HEIGHT)

            now = pygame.time.get_ticks()
            if not game_over and not in_shop:
                if player.ultimate_active:
                    if player.last_ultimate_shot_time == 0 or (now - player.last_ultimate_shot_time) >= player.ultimate_fire_delay_ms:
                        bullets.extend(player.use_ultimate_once()); player.last_ultimate_shot_time = now
                else:
                    if player.can_shoot(): bullets.extend(player.shoot())

            wave.update(dt)
            # enemy shooting

            for e in wave.enemies:
                if not e.alive: continue
                base_prob = wave.enemy_shoot_prob * 2.0
                if isinstance(e, Boss): base_prob *= 0.6
                if e.etype == 'fast': prob = base_prob * 1.8
                elif e.etype == 'tank': prob = base_prob * 0.6
                else: prob = base_prob
                # If a boss implements its own shooting (custom_shooter=True), skip default triple-shot.
                if isinstance(e, Boss):
                    if getattr(e, 'custom_shooter', False):
                        # custom boss handles its own timing inside its update()
                        pass
                    else:
                        e.shoot_timer -= dt
                        if e.shoot_timer <= 0:
                            e.shoot_timer = 0.8
                            for a in (-1,0,1):
                                enemy_bullets.append(Bullet(e.x + a*16, e.y + e.h//2 + 6, ENEMY_BULLET_SPEED_BASE + 1.2, RED, 'enemy', damage=1))
                else:
                    if random.random() < prob:
                        dx = player.x - e.x; aim_offset = clamp(dx / (WIDTH/2), -0.6, 0.6)
                        speed = ENEMY_BULLET_SPEED_BASE + (0.1*(1 if e.etype=='fast' else 0))
                        enemy_bullets.append(Bullet(e.x + aim_offset*6, e.y + e.h//2 + 6, speed, RED, 'enemy', damage=1))


            # update entities
            for e in wave.enemies:
                if e.alive: e.update(0,0,dt,wave,elapsed)
            for b in bullets[:]: b.update(dt);
            for b in bullets[:]:
                if b.offscreen(): bullets.remove(b)
            for b in enemy_bullets[:]: b.update(dt)
            for b in enemy_bullets[:]:
                if b.offscreen(): enemy_bullets.remove(b)
            for d in drops[:]: d.update(dt);
            for d in drops[:]:
                if d.y > HEIGHT + 40: drops.remove(d)
            for ex in explosions[:]: ex.update(dt)
            for ex in explosions[:]:
                if not ex.particles: explosions.remove(ex)

            # collisions: player bullets -> enemies
            for b in bullets[:]:
                if b.owner != 'player': continue
                hit = False
                for e in wave.enemies:
                    if not e.alive: continue
                    if e.rect().collidepoint(b.x, b.y):
                        e.hp -= b.damage
                        try: bullets.remove(b)
                        except: pass
                        if e.hp <= 0:
                            e.alive = False; player.score += 120 if not isinstance(e,Boss) else 1200
                            if not player.ultimate_active:
                                player.ultimate_count += 1
                                if player.ultimate_count >= player.ultimate_needed: player.ultimate_available = True
                            explosions.append(Explosion(e.x, e.y, color=ORANGE, num=PARTICLE_COUNT + (6 if isinstance(e,Boss) else 0)))
                            if not isinstance(e,Boss) and random.random() < BUFF_CHANCE:
                                kind = random.choice(['multishot','shield','heal'])
                                drops.append(BuffDrop(e.x, e.y, kind=kind))
                        hit = True; break
                if hit: continue


            # collisions: enemy bullets -> player
            player_rect = pygame.Rect(player.x - player.radius, player.y - player.radius, player.radius*2, player.radius*2)
            for b in enemy_bullets[:]:
                if b.rect.colliderect(player_rect) or math.hypot(b.x - player.x, b.y - player.y) < (b.radius + player.radius):
                    try: enemy_bullets.remove(b)
                    except: pass
                    # pass bullet position as source so knockback feels directional
                    killed = player.take_damage(1, source=(b.x, b.y), knockback=KNOCKBACK_PIXELS)
                    explosions.append(Explosion(player.x, player.y, color=CYAN, num=18))
                    if killed:
                        game_over = True; state = 'gameover'; fade_alpha = 0.0; fade_start = pygame.time.get_ticks(); break

            # collisions: enemy body -> player (fixed so it does NOT instantly kill you)
            # This handles enemy touching the player: deals 1 damage, applies knockback,
            # grants INVINCIBILITY_MS of temporary invulnerability, and pushes player away slightly.
            # It breaks after the first hit per frame to avoid multiple simultaneous hits.
            for e in wave.enemies:
                if not e.alive:
                    continue

                er = e.rect()

                collide = (
                    player_rect.colliderect(er) or
                    math.hypot(e.x - player.x, e.y - player.y) < (player.radius + max(e.w, e.h) * 0.45)
                )

                if collide:
                    # only apply damage if not currently invincible (handled inside take_damage)
                    killed = player.take_damage(
                        1,
                        source=(e.x, e.y),
                        knockback=KNOCKBACK_PIXELS
                    )

                    explosions.append(Explosion(player.x, player.y, color=CYAN, num=18))

                    # bump player slightly out to reduce repeated collisions
                    if player.x < e.x:
                        player.x -= 6
                    else:
                        player.x += 6

                    if player.y < e.y:
                        player.y -= 6
                    else:
                        player.y += 6

                    player.x = clamp(player.x, player.radius, WIDTH - player.radius)
                    player.y = clamp(player.y, player.radius, HEIGHT - player.radius)

                    if killed:
                        game_over = True
                        state = 'gameover'
                        fade_alpha = 0.0
                        fade_start = pygame.time.get_ticks()
                    break

            # collisions: drops -> player
            for d in drops[:]:
                if d.rect.colliderect(player_rect):
                    drops.remove(d)
                    if d.kind == 'multishot':
                        player.multishot_active = True
                        player.multishot_end_time = pygame.time.get_ticks() + BUFF_DURATION_MS

                    elif d.kind == 'shield':
                        player.shield_active = True
                        player.shield_uses = 3
                        player.shield_end_time = pygame.time.get_ticks() + SHIELD_DURATION_MS

                    elif d.kind == 'heal':
                        # heal only +1, not full
                        player.hp = min(player.hp_max, player.hp + 1)
        

            # wave cleared -> go to shop
            if not wave.any_alive() and not in_shop:
                player.score += 300; in_shop = True; time_since_wave_win = 0.0

            # shop handling
            if in_shop:
                shop.open(screen, player)
                in_shop = False
                # respawn wave taking into account player's current position so enemies don't spawn in player
                wave.spawn_wave(player_pos=(player.x, player.y))
                bullets=[]; enemy_bullets=[]; drops=[]; explosions=[];

            # drawing
            screen.fill(BLACK)
            for p in planets: p.draw(screen)
            for s in stars: s.draw(screen)

            hud_surf = font.render(f"SCORE: {player.score}   WAVE: {wave.wave_num}   ENEMIES: {sum(1 for ee in wave.enemies if ee.alive)}", True, WHITE)
            screen.blit(hud_surf, (12, 12))
            hpw = 160; hp_x = WIDTH - hpw - 20; hp_y = 18
            pygame.draw.rect(screen, GRAY, (hp_x, hp_y, hpw, 18))
            hp_frac = player.hp / max(1, player.hp_max)
            pygame.draw.rect(screen, RED, (hp_x, hp_y, int(hpw*hp_frac), 18))
            hp_txt = font.render(f"HP: {player.hp}/{player.hp_max}", True, WHITE); screen.blit(hp_txt, (hp_x + 6, hp_y - 18))
            # SHIELD TIMER (top-right)
            if player.shield_active and player.shield_end_time > pygame.time.get_ticks():
                rem_ms = player.shield_end_time - pygame.time.get_ticks()
                rem_s = rem_ms / 1000.0
                shield_txt = font.render(f"SHIELD: {rem_s:.1f}s", True, SHIELD_BLUE)
                screen.blit(shield_txt, (WIDTH - shield_txt.get_width() - 20, hp_y + 22))

            # ultimate HUD
            if player.ultimate_active:
                rem_ms = max(0, player.ultimate_end_time - pygame.time.get_ticks())
                ult_text = f"ULTIMATE ACTIVE: {rem_ms//1000 + 1}s"
                ult_surf = font.render(ult_text, True, YELLOW)
            else:
                ult_text = "ULTIMATE: READY! Press SPACE to use" if player.ultimate_available else f"ULTIMATE: {player.ultimate_count}/{player.ultimate_needed}"
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
            pygame.display.flip(); continue

        # GAMEOVER (fade)
        if state == 'gameover':
            fade_alpha += dt * 255 / 1.0
            if fade_alpha >= 255: fade_alpha = 255
            screen.fill(BLACK)
            for p in planets: p.draw(screen)
            for s in stars: s.draw(screen)
            hud_surf = font.render(f"SCORE: {player.score}   WAVE: {wave.wave_num}   ENEMIES: {sum(1 for ee in wave.enemies if ee.alive)}", True, WHITE)
            screen.blit(hud_surf, (12, 12))
            for e in wave.enemies: e.draw(screen)
            for b in bullets: b.draw(screen)
            for b in enemy_bullets: b.draw(screen)
            for d in drops: d.draw(screen)
            player.draw(screen)
            for ex in explosions: ex.draw(screen)
            fade_surf = pygame.Surface((WIDTH, HEIGHT)); fade_surf.set_alpha(int(fade_alpha)); fade_surf.fill((0,0,0)); screen.blit(fade_surf, (0,0))
            if fade_alpha >= 255:
                go = bigfont.render("GAME OVER", True, RED); sub = font.render("Press ENTER or Click to return to Menu", True, WHITE)
                screen.blit(go, (WIDTH//2 - go.get_width()//2, HEIGHT//2 - 50)); screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 10))
            pygame.display.flip(); continue

# --------------------
# Run
# --------------------
if __name__ == '__main__':
    main()


# --- Extended Bullet and Boss Variants appended by patcher ---
import math as _math

class Bullet:
    def __init__(self, x, y, vy, color=YELLOW, owner="player", damage=1, vx=0):
        # Backwards-compatible: vy is vertical speed; vx is optional horizontal speed.
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.owner = owner
        self.damage = damage
        self.radius = 4 if owner == "player" else 5
        self.rect = pygame.Rect(int(x - self.radius), int(y - self.radius), self.radius*2, self.radius*2)

    def update(self, dt):
        scale = (dt * 60) if dt < 5 else dt
        self.x += self.vx * scale
        self.y += self.vy * scale
        self.rect.center = (int(self.x), int(self.y))

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)

    def offscreen(self):
        return self.x < -40 or self.x > WIDTH + 40 or self.y < -40 or self.y > HEIGHT + 40

# New boss variants
class RotatingShooterBoss(Boss):
    def __init__(self, x, y, hp=24, bullets=8, shoot_interval=0.9, spin_speed=0.9, speed=3.4):
        super().__init__(x, y, hp=hp)
        self.custom_shooter = True
        self.angle = 0.0
        self.spin_speed = spin_speed
        self.bullets_per_shot = bullets
        self.shoot_interval = shoot_interval
        self.shoot_timer = shoot_interval
        self.bullet_speed = speed
        self.w = 140; self.h = 80

    def update(self, step_dx, step_dy, dt, wave, elapsed):
        if not self.alive: return
        # basic bobbing movement (reuse parent's formation math)
        super().update(step_dx, step_dy, dt, wave, elapsed)
        self.angle += self.spin_speed * dt
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_interval
            for i in range(self.bullets_per_shot):
                a = self.angle + (i * (2*_math.pi / self.bullets_per_shot))
                vx = _math.cos(a) * self.bullet_speed
                vy = _math.sin(a) * self.bullet_speed
                enemy_bullets.append(Bullet(self.x, self.y + self.h//2, vy, RED, 'enemy', damage=1, vx=vx))

    def draw(self, surf):
        if not self.alive: return
        rect = pygame.Rect(self.x - self.w/2, self.y - self.h/2, self.w, self.h)
        pygame.draw.ellipse(surf, (160, 60, 200), rect)
        draw_boss_healthbar(surf, int(self.x-60), int(self.y-self.h//2-20), 120, 14, self.hp, self.hp_max)
        pygame.draw.ellipse(surf, WHITE, rect, 3)
        cx = int(self.x + _math.cos(self.angle) * 24)
        cy = int(self.y + _math.sin(self.angle) * 12)
        pygame.draw.circle(surf, YELLOW, (cx, cy), 8)

class TwinShooterBoss(Boss):
    def __init__(self, x, y, hp=20, shoot_interval=0.55, bullet_speed=4.2, horizontal=True):
        super().__init__(x, y, hp=hp)
        self.custom_shooter = True
        self.shoot_interval = shoot_interval
        self.shoot_timer = shoot_interval
        self.bullet_speed = bullet_speed
        self.horizontal = horizontal
        self.w = 120; self.h = 72

    def update(self, step_dx, step_dy, dt, wave, elapsed):
        if not self.alive: return
        super().update(step_dx, step_dy, dt, wave, elapsed)
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_interval
            if self.horizontal:
                enemy_bullets.append(Bullet(self.x - 12, self.y, 0, RED, 'enemy', damage=1, vx=-self.bullet_speed))
                enemy_bullets.append(Bullet(self.x + 12, self.y, 0, RED, 'enemy', damage=1, vx=self.bullet_speed))
            else:
                enemy_bullets.append(Bullet(self.x, self.y - 12, -self.bullet_speed, RED, 'enemy', damage=1, vx=0))
                enemy_bullets.append(Bullet(self.x, self.y + 12, self.bullet_speed, RED, 'enemy', damage=1, vx=0))

    def draw(self, surf):
        if not self.alive: return
        rect = pygame.Rect(self.x - self.w/2, self.y - self.h/2, self.w, self.h)
        pygame.draw.rect(surf, (200,90,60), rect); pygame.draw.rect(surf, WHITE, rect, 3)
        draw_boss_healthbar(surf, int(self.x-60), int(self.y-self.h//2-20), 120, 14, self.hp, self.hp_max)
        pygame.draw.rect(surf, BLACK, (int(self.x - 36), int(self.y - 6), 16, 12))
        pygame.draw.rect(surf, BLACK, (int(self.x + 20), int(self.y - 6), 16, 12))

class SpiralSpreadBoss(Boss):
    def __init__(self, x, y, hp=22, bullets=4, shoot_interval=0.35, spin_speed=2.0, bullet_speed=3.8):
        super().__init__(x, y, hp=hp)
        self.custom_shooter = True
        self.angle = 0.0
        self.spin_speed = spin_speed
        self.bullets_per_shot = bullets
        self.shoot_interval = shoot_interval
        self.shoot_timer = shoot_interval
        self.bullet_speed = bullet_speed
        self.w = 130; self.h = 76

    def update(self, step_dx, step_dy, dt, wave, elapsed):
        if not self.alive: return
        super().update(step_dx, step_dy, dt, wave, elapsed)
        self.angle += self.spin_speed * dt
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = self.shoot_interval
            for i in range(self.bullets_per_shot):
                a = self.angle + (i * (2*_math.pi / self.bullets_per_shot)) + (math.sin(elapsed * 1.3) * 0.12)
                vx = _math.cos(a) * self.bullet_speed
                vy = _math.sin(a) * self.bullet_speed
                enemy_bullets.append(Bullet(self.x, self.y + self.h//2, vy, RED, 'enemy', damage=1, vx=vx))

# End of appended code


# ---- New Enemy Types ----
class MultiShotEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, etype="multishot", hp=7)
        self.shoot_timer = 1.1

    def update(self, step_dx, step_dy, dt, wave, elapsed):
        super().update(step_dx, step_dy, dt, wave, elapsed)
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = 1.1
            for a in (-0.4, 0, 0.4):
                enemy_bullets.append(Bullet(self.x + a*12, self.y + self.h//2, ENEMY_BULLET_SPEED_BASE+1.2, RED, 'enemy'))

class DiagonalEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, etype="diagonal", hp=5)
        self.shoot_timer = 1.3

    def update(self, step_dx, step_dy, dt, wave, elapsed):
        super().update(step_dx, step_dy, dt, wave, elapsed)
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = 1.3
            enemy_bullets.append(Bullet(self.x, self.y, ENEMY_BULLET_SPEED_BASE, RED, 'enemy', vx=2.2))
            enemy_bullets.append(Bullet(self.x, self.y, ENEMY_BULLET_SPEED_BASE, RED, 'enemy', vx=-2.2))

class BurstEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, etype="burst", hp=6)
        self.cooldown = 2.2
        self.burst = 0

    def update(self, step_dx, step_dy, dt, wave, elapsed):
        super().update(step_dx, step_dy, dt, wave, elapsed)
        if self.cooldown > 0:
            self.cooldown -= dt
        else:
            if self.burst < 5:
                enemy_bullets.append(Bullet(self.x, self.y, ENEMY_BULLET_SPEED_BASE+2.5, RED, 'enemy'))
                self.burst += 1
            else:
                self.burst = 0
                self.cooldown = 2.2

class SniperEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, etype="sniper", hp=4)
        self.shoot_timer = 2.0

    def update(self, step_dx, step_dy, dt, wave, elapsed):
        super().update(step_dx, step_dy, dt, wave, elapsed)
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            self.shoot_timer = 2.0
            dx = player.x - self.x
            dy = player.y - self.y
            import math
            d = math.hypot(dx, dy) or 1
            vx = dx/d * (ENEMY_BULLET_SPEED_BASE+3.5)
            vy = dy/d * (ENEMY_BULLET_SPEED_BASE+3.5)
            enemy_bullets.append(Bullet(self.x, self.y, vy, RED, 'enemy', vx=vx))