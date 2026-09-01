"""
Tank Battle - Web Version Entry Point
pygbag 入口文件 — 包含游戏启动逻辑。
"""
import asyncio
import sys
import random
import math
import time

# 调试: 确认脚本被加载 — 使用 JS console.log
try:
    import js
    js.console.log('[MAIN] main.py loaded, sys.platform =', sys.platform)
except:
    print('[MAIN] main.py loaded, sys.platform =', sys.platform)

import pygame
try:
    js.console.log('[MAIN] pygame imported')
except:
    print('[MAIN] pygame imported')

# 立即测试 pygame 属性
try:
    js.console.log('[MAIN] pygame.has init:', hasattr(pygame, 'init'))
    js.console.log('[MAIN] pygame.has display:', hasattr(pygame, 'display'))
except:
    pass

# ====================== 常量 ======================
TITLE = "坦克大战 Tank Battle"
TILE = 32
COLS = 20
ROWS = 15
HUD_HEIGHT = 48
MARGIN = 16
SCREEN_W = MARGIN * 2 + COLS * TILE
SCREEN_H = MARGIN * 2 + ROWS * TILE + HUD_HEIGHT
FPS = 60

# 调色盘
COLOR_BG = (18, 18, 18)
COLOR_HUD_BG = (30, 30, 30)
COLOR_WHITE = (235, 235, 235)
COLOR_YELLOW = (236, 204, 84)
COLOR_RED = (220, 70, 70)
COLOR_GREEN = (110, 200, 110)
COLOR_GRAY = (90, 90, 90)
COLOR_DARK_GRAY = (55, 55, 55)
COLOR_BRICK = (170, 110, 60)
COLOR_BRICK_DARK = (110, 70, 35)
COLOR_STEEL = (170, 170, 180)
COLOR_STEEL_DARK = (120, 120, 130)
COLOR_BASE = (220, 180, 60)
COLOR_BASE_DARK = (150, 110, 30)
COLOR_TEXT = (245, 245, 245)
COLOR_ACCENT = (255, 170, 70)
COLOR_BRICK_LIGHT = (190, 130, 80)
COLOR_STEEL_LIGHT = (200, 200, 210)
COLOR_HUD_TEXT = (245, 245, 245)
COLOR_WARN = (255, 120, 60)

TILE_EMPTY = 0
TILE_BRICK = 1
TILE_STEEL = 2
TILE_WATER = 3
TILE_GRASS = 4
TILE_BASE = 5
TILE_BASE_DEAD = 6

DIR_UP = 0
DIR_RIGHT = 1
DIR_DOWN = 2
DIR_LEFT = 3
DIR_DX = [0, 1, 0, -1]
DIR_DY = [-1, 0, 1, 0]

# ====================== 地图 ======================
def build_map():
    """构建地图, 中央区域用砖墙摆出玩家姓名缩写 'HD'。"""
    rows, cols = ROWS, COLS
    grid = [[TILE_EMPTY] * cols for _ in range(rows)]

    for c in range(cols):
        grid[0][c] = TILE_STEEL
        grid[rows - 1][c] = TILE_STEEL
    for r in range(rows):
        grid[r][0] = TILE_STEEL
        grid[r][cols - 1] = TILE_STEEL

    base_cx = cols // 2
    base_cy = rows - 2
    grid[base_cy][base_cx] = TILE_BASE
    for dc in (-1, 0, 1):
        c = base_cx + dc
        if 0 < c < cols - 1:
            grid[base_cy - 1][c] = TILE_BRICK
    grid[base_cy][base_cx - 1] = TILE_BRICK
    grid[base_cy][base_cx + 1] = TILE_BRICK

    seed = 42
    def seeded_rand():
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
        # Python integers are already unsigned after the mask above;
        # JavaScript's unsigned-shift syntax (>>>) is not valid Python.
        return seed / 0xFFFFFFFF

    for r in (4, 10):
        for c in range(3, cols - 3):
            if seeded_rand() < 0.5:
                grid[r][c] = TILE_BRICK
    for c in (5, 14):
        for r in range(2, rows - 2):
            if seeded_rand() < 0.4:
                grid[r][c] = TILE_BRICK
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            if grid[r][c] == TILE_EMPTY and seeded_rand() < 0.06:
                grid[r][c] = TILE_BRICK

    hd_offsets = [
        (2, 5), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10),
        (3, 8),
        (4, 5), (4, 10),
        (5, 5), (5, 6), (5, 7), (5, 8), (5, 9), (5, 10),
    ]
    for dr, dc in hd_offsets:
        r, c = 6 + dr, 5 + dc
        if 0 <= r < rows and 0 <= c < cols:
            grid[r][c] = TILE_BRICK

    return grid, (base_cx * TILE + MARGIN, base_cy * TILE + MARGIN)

# ====================== 绘制工具 ======================
def draw_tile(surf, tile_type, x, y, size=TILE):
    rect = pygame.Rect(x, y, size, size)
    if tile_type == TILE_EMPTY:
        return
    if tile_type == TILE_BRICK:
        pygame.draw.rect(surf, COLOR_BRICK, rect)
        pygame.draw.rect(surf, COLOR_BRICK_DARK, rect, 2)
        for i in range(1, 4):
            yy = y + size * i // 4
            pygame.draw.line(surf, COLOR_BRICK_DARK, (x, yy), (x + size, yy), 1)
        for j in range(1, 4):
            xx = x + size * j // 4
            pygame.draw.line(surf, COLOR_BRICK_DARK, (xx, y), (xx, y + size), 1)
        pygame.draw.rect(surf, COLOR_BRICK_LIGHT, rect.inflate(-12, -12), 1)
    elif tile_type == TILE_STEEL:
        pygame.draw.rect(surf, COLOR_STEEL, rect)
        pygame.draw.rect(surf, COLOR_STEEL_DARK, rect, 2)
        pygame.draw.rect(surf, COLOR_STEEL_LIGHT, rect.inflate(-8, -8), 1)
        pygame.draw.line(surf, COLOR_STEEL_DARK,
                         (x + 2, y + 2), (x + size - 2, y + size - 2), 1)
        pygame.draw.line(surf, COLOR_STEEL_DARK,
                         (x + size - 2, y + 2), (x + 2, y + size - 2), 1)
    elif tile_type == TILE_BASE:
        pygame.draw.rect(surf, COLOR_BASE, rect)
        pygame.draw.rect(surf, COLOR_BASE_DARK, rect, 2)
        pygame.draw.circle(surf, COLOR_BASE_DARK,
                           (x + size // 2, y + size // 2), size // 4)
    elif tile_type == TILE_BASE_DEAD:
        pygame.draw.rect(surf, COLOR_DARK_GRAY, rect)

# ====================== 子弹 ======================
class Bullet:
    def __init__(self, x, y, dir, owner):
        self.x = x
        self.y = y
        self.dir = dir
        self.owner = owner
        self.speed = 6
        self.alive = True
        self.w = 6
        self.h = 6

    def update(self, game):
        dx = DIR_DX[self.dir]
        dy = DIR_DY[self.dir]
        self.x += dx * self.speed
        self.y += dy * self.speed
        if self.x < 0 or self.x > SCREEN_W or self.y < HUD_HEIGHT or self.y > SCREEN_H:
            self.alive = False
            return
        tile_col = int((self.x - MARGIN) // TILE)
        tile_row = int((self.y - MARGIN - HUD_HEIGHT) // TILE)
        if 0 <= tile_row < ROWS and 0 <= tile_col < COLS:
            tile = game.grid[tile_row][tile_col]
            if tile == TILE_BRICK:
                game.grid[tile_row][tile_col] = TILE_EMPTY
                self.alive = False
                game.spawn_explosion(self.x, self.y, 16)
            elif tile == TILE_STEEL:
                self.alive = False
                game.spawn_explosion(self.x, self.y, 16)
            elif tile == TILE_BASE:
                game.grid[tile_row][tile_col] = TILE_BASE_DEAD
                self.alive = False
                game.state = 'gameover'
                game.spawn_explosion(self.x, self.y, 32)

    def draw(self, surf):
        color = COLOR_YELLOW if self.owner == 'player' else COLOR_RED
        pygame.draw.rect(surf, color,
                         (int(self.x - self.w//2), int(self.y - self.h//2), self.w, self.h))

# ====================== 坦克 ======================
class Tank:
    def __init__(self, x, y, dir, type='player'):
        self.x = x
        self.y = y
        self.dir = dir
        self.type = type
        self.size = 28
        if type == 'player':
            self.speed = 2
            self.hp = 1
        elif type == 'heavy':
            self.speed = 1.2
            self.hp = 3
        elif type == 'fast':
            self.speed = 2.5
            self.hp = 1
        else:
            self.speed = 1.5
            self.hp = 1
        self.cooldown = 0
        self.alive = True
        self.spawn_timer = 0
        self.move_timer = 0
        self.move_flash = 0

    @property
    def cx(self):
        return self.x + self.size // 2

    @property
    def cy(self):
        return self.y + self.size // 2

    def try_move(self, nx, ny, game):
        if nx < MARGIN or nx + self.size > SCREEN_W - MARGIN:
            return False
        if ny < HUD_HEIGHT + MARGIN or ny + self.size > SCREEN_H - MARGIN:
            return False
        c1 = int((nx - MARGIN) // TILE)
        c2 = int((nx + self.size - 1 - MARGIN) // TILE)
        r1 = int((ny - MARGIN - HUD_HEIGHT) // TILE)
        r2 = int((ny + self.size - 1 - MARGIN) // TILE)
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                if 0 <= r < ROWS and 0 <= c < COLS:
                    if game.grid[r][c] in (TILE_BRICK, TILE_STEEL, TILE_BASE):
                        return False
        for t in [game.player] + game.enemies:
            if t is self or not t.alive:
                continue
            if (nx < t.x + t.size and nx + self.size > t.x and
                ny < t.y + t.size and ny + self.size > t.y):
                return False
        return True

    def move(self, dir, game):
        self.dir = dir
        nx = self.x + DIR_DX[dir] * self.speed
        ny = self.y + DIR_DY[dir] * self.speed
        if self.try_move(nx, ny, game):
            self.x = nx
            self.y = ny
            if self.move_flash == 0:
                self.move_flash = 6
            return True
        return False

    def shoot(self, game):
        if self.cooldown > 0:
            return
        bx = self.cx + DIR_DX[self.dir] * self.size // 2
        by = self.cy + DIR_DY[self.dir] * self.size // 2
        game.bullets.append(Bullet(bx, by, self.dir, self.type))
        self.cooldown = 30 if self.type == 'player' else 60

    def update(self, game):
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.move_flash > 0:
            self.move_flash -= 1
        if self.spawn_timer > 0:
            self.spawn_timer -= 1

    def draw(self, surf):
        if self.spawn_timer > 0 and self.spawn_timer % 6 < 3:
            return
        s = self.size
        if self.type == 'player':
            body_c, track_c, turret_c = COLOR_GREEN, COLOR_DARK_GRAY, (160, 230, 160)
        elif self.type == 'heavy':
            body_c, track_c, turret_c = (150, 80, 180), (80, 50, 100), (190, 130, 210)
        elif self.type == 'fast':
            body_c, track_c, turret_c = (240, 160, 60), (140, 80, 30), (255, 200, 120)
        else:
            body_c, track_c, turret_c = COLOR_RED, (140, 40, 40), (255, 130, 130)
        cx, cy = self.x + s // 2, self.y + s // 2
        pygame.draw.rect(surf, track_c, (self.x, self.y, 5, s))
        pygame.draw.rect(surf, track_c, (self.x + s - 5, self.y, 5, s))
        pygame.draw.rect(surf, body_c, (self.x + 4, self.y + 4, s - 8, s - 8))
        pygame.draw.circle(surf, turret_c, (cx, cy), 6)
        bx = cx + DIR_DX[self.dir] * 4
        by = cy + DIR_DY[self.dir] * 4
        pygame.draw.rect(surf, (40, 40, 40), (bx - 2, by - 2, 4, 4))
        if self.move_flash > 0:
            pygame.draw.rect(surf, (255, 255, 255, 60),
                             (self.x, self.y, s, s), 1)

# ====================== 游戏类 ======================
class Game:
    def __init__(self):
        if hasattr(pygame, 'init'):
            try:
                pygame.init()
            except Exception:
                pass
        try:
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        except Exception:
            self.screen = pygame.Surface((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        try:
            self.font_big = pygame.font.Font(None, 44)
            self.font_medium = pygame.font.Font(None, 28)
            self.font_small = pygame.font.Font(None, 20)
        except Exception:
            self.font_big = self.font_medium = self.font_small = None
        self.bg_image = None
        self.sounds = {}
        self._restart_flash_timer = 0
        self._restart_text_timer = 0
        try:
            self._dark_overlay = pygame.Surface((SCREEN_W, SCREEN_H - HUD_HEIGHT))
            self._dark_overlay.set_alpha(160)
            self._dark_overlay.fill((10, 12, 24))
            self._game_overlay = pygame.Surface((SCREEN_W, SCREEN_H))
            self._game_overlay.set_alpha(200)
            self._game_overlay.fill((0, 0, 0))
        except Exception:
            self._dark_overlay = None
            self._game_overlay = None
        self.state = 'menu'
        self._running = True
        self.init_new_game()

    def init_new_game(self):
        self.grid, self.base_pos = build_map()
        self.bullets = []
        self.explosions = []
        self.enemies = []
        self.score = 0
        self.level = 1
        self.lives = 3
        self.max_enemies = 4
        self.enemies_left = self.max_enemies
        self.enemy_queue = []
        self.spawn_timer = 0
        for i in range(self.max_enemies):
            r = random.random()
            t = 'basic' if r < 0.5 else ('fast' if r < 0.8 else 'heavy')
            self.enemy_queue.append(t)
        self.spawn_enemy()
        self.player = Tank(
            self.base_pos[0] - self.base_pos[0] + 12 * TILE + MARGIN,
            self.base_pos[1] - self.base_pos[1] + 13 * TILE + MARGIN,
            DIR_UP, 'player')

    def spawn_enemy(self):
        if not self.enemy_queue:
            return
        etype = self.enemy_queue.pop(0)
        spawn_cols = [1, 9, 18]
        for c in spawn_cols:
            tx = c * TILE + MARGIN
            ty = HUD_HEIGHT + TILE + MARGIN
            blocked = False
            for t in [self.player] + self.enemies:
                if (tx < t.x + t.size and tx + 28 > t.x and
                    ty < t.y + t.size and ty + 28 > t.y):
                    blocked = True
                    break
            if not blocked:
                e = Tank(tx, ty, DIR_DOWN, etype)
                e.spawn_timer = 40
                self.enemies.append(e)
                return

    def spawn_explosion(self, x, y, size=24):
        self.explosions.append({'x': x, 'y': y, 'r': 4, 'max_r': size,
                                'life': 18, 'max_life': 18})

    def handle_input(self, events):
        keys_down = set()
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                keys_down.add(ev.key)
        if self.state == 'menu':
            if pygame.K_w in keys_down or pygame.K_UP in keys_down:
                self.state = 'playing'
                self.overlay_alpha = 0
        elif self.state == 'playing':
            if pygame.K_w in keys_down or pygame.K_UP in keys_down:
                self.player.move(DIR_UP, self)
            elif pygame.K_s in keys_down or pygame.K_DOWN in keys_down:
                self.player.move(DIR_DOWN, self)
            elif pygame.K_a in keys_down or pygame.K_LEFT in keys_down:
                self.player.move(DIR_LEFT, self)
            elif pygame.K_d in keys_down or pygame.K_RIGHT in keys_down:
                self.player.move(DIR_RIGHT, self)
            if pygame.K_SPACE in keys_down or pygame.K_j in keys_down:
                self.player.shoot(self)
            if pygame.K_p in keys_down:
                self.state = 'paused'
        elif self.state == 'paused':
            if pygame.K_p in keys_down:
                self.state = 'playing'
        elif self.state in ('gameover', 'victory'):
            if pygame.K_r in keys_down:
                self.init_new_game()
                self.state = 'playing'

    def update_enemies(self):
        for e in self.enemies:
            if not e.alive:
                continue
            e.update(self)
            if e.spawn_timer > 0:
                continue
            e.move_timer -= 1
            if e.move_timer <= 0:
                e.move_timer = 40 + random.randint(0, 80)
                if random.random() < 0.5:
                    dx = self.player.cx - e.cx
                    dy = self.player.cy - e.cy
                    if abs(dx) > abs(dy):
                        e.dir = DIR_RIGHT if dx > 0 else DIR_LEFT
                    else:
                        e.dir = DIR_DOWN if dy > 0 else DIR_UP
                else:
                    e.dir = random.randint(0, 3)
            moved = e.move(e.dir, self)
            if not moved:
                e.move_timer = 0
            elif random.random() < 0.03:
                e.shoot(self)

    def update_game(self):
        if self.state != 'playing':
            return
        self.update_enemies()
        for b in self.bullets:
            b.update(self)
        self.bullets = [b for b in self.bullets if b.alive]
        self.check_bullet_hits()
        self.enemies = [e for e in self.enemies if e.alive]
        self.explosions = [e for e in self.explosions if e['life'] > 0]
        for e in self.explosions:
            e['life'] -= 1
            e['r'] = e['max_r'] * (1 - e['life'] / e['max_life'])
        if self._restart_flash_timer > 0:
            self._restart_flash_timer -= 1
        if self._restart_text_timer > 0:
            self._restart_text_timer -= 1
        if self.enemy_queue:
            self.spawn_timer -= 1
            if self.spawn_timer <= 0 and len(self.enemies) < 4:
                self.spawn_enemy()
                self.spawn_timer = 300

    def check_bullet_hits(self):
        for b in self.bullets:
            if not b.alive:
                continue
            bx, by = b.x, b.y
            targets = ([self.player] if b.owner != 'player' else []) + \
                      ([e for e in self.enemies if e.alive] if b.owner == 'player' else [])
            for t in targets:
                if bx >= t.x and bx <= t.x + t.size and by >= t.y and by <= t.y + t.size:
                    b.alive = False
                    self.spawn_explosion(bx, by, 20)
                    if t is self.player:
                        self.lives -= 1
                        if self.lives <= 0:
                            self.player.alive = False
                            self.state = 'gameover'
                            self.overlay_alpha = 0
                        else:
                            self.player.x = 12 * TILE + MARGIN
                            self.player.y = 13 * TILE + MARGIN
                            self.player.dir = DIR_UP
                            self.player.spawn_timer = 30
                    else:
                        t.hp -= 1
                        if t.hp <= 0:
                            t.alive = False
                            self.score += 300 if t.type == 'heavy' else (200 if t.type == 'fast' else 100)
                            self.enemies_left -= 1
                            self._restart_flash_timer = 10
                            if self.enemies_left <= 0 and self.state == 'playing':
                                self.state = 'victory'
                                self.overlay_alpha = 0
                    break

    def draw(self):
        self.screen.fill(COLOR_BG)
        for r in range(ROWS):
            for c in range(COLS):
                draw_tile(self.screen, self.grid[r][c],
                          c * TILE + MARGIN, r * TILE + HUD_HEIGHT + MARGIN)
        if self.player and self.player.alive:
            self.player.draw(self.screen)
        for e in self.enemies:
            if e.alive:
                e.draw(self.screen)
        for b in self.bullets:
            b.draw(self.screen)
        for e in self.explosions:
            alpha = int(255 * e['life'] / e['max_life'])
            pygame.draw.circle(self.screen, (255, 180, 0, alpha),
                               (int(e['x']), int(e['y'])), max(1, int(e['r'])))
        self.draw_hud()
        if self.state != 'playing':
            self.draw_overlay()
        pygame.display.flip()

    def draw_hud(self):
        pygame.draw.rect(self.screen, COLOR_HUD_BG,
                         (0, 0, SCREEN_W, HUD_HEIGHT))
        if self.font_small:
            lives = '❤' * max(0, self.lives)
            try:
                surf = self.font_small.render(lives + ' Score:' + str(self.score) +
                                              ' Lv:' + str(self.level) +
                                              ' Enemies:' + str(self.enemies_left),
                                              True, COLOR_HUD_TEXT)
                self.screen.blit(surf, (MARGIN, HUD_HEIGHT // 2 - surf.get_height() // 2))
            except Exception:
                pass

    def draw_overlay(self):
        if hasattr(self, 'overlay_alpha'):
            self.overlay_alpha = min(1, self.overlay_alpha + 0.03)
        else:
            self.overlay_alpha = 1
        overlay = pygame.Surface((SCREEN_W, SCREEN_H))
        overlay.set_alpha(int(180 * self.overlay_alpha))
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        if self.font_big:
            if self.state == 'menu':
                self._draw_title('TANK BATTLE', 'HD', 'Press W to Start')
            elif self.state == 'gameover':
                self._draw_title('GAME OVER', 'Score:' + str(self.score), 'Press R to Restart')
            elif self.state == 'victory':
                self._draw_title('VICTORY!', 'Score:' + str(self.score), 'Press R to Play Again')
            elif self.state == 'paused':
                self._draw_title('PAUSED', '', 'Press P to Resume')

    def _draw_title(self, title, subtitle, hint):
        if self.font_big:
            s = self.font_big.render(title, True, COLOR_WHITE)
            self.screen.blit(s, (SCREEN_W // 2 - s.get_width() // 2,
                                 SCREEN_H // 2 - 60))
        if subtitle and self.font_medium:
            s = self.font_medium.render(subtitle, True, COLOR_YELLOW)
            self.screen.blit(s, (SCREEN_W // 2 - s.get_width() // 2,
                                 SCREEN_H // 2 - 10))
        if hint and self.font_small:
            s = self.font_small.render(hint, True, COLOR_GRAY)
            self.screen.blit(s, (SCREEN_W // 2 - s.get_width() // 2,
                                 SCREEN_H // 2 + 40))

    async def run(self):
        self._running = True
        while self._running:
            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    self._running = False
                if ev.type == pygame.VIDEORESIZE:
                    try:
                        self.screen = pygame.display.set_mode((ev.w, ev.h))
                    except Exception:
                        pass
            self.handle_input(events)
            self.update_game()
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
            await asyncio.sleep(0)

# ====================== 入口 ======================
try:
    import js
    js.console.log('[MAIN] Defining main()...')
except:
    print('[MAIN] Defining main()...')

async def main():
    """pygbag 入口 — 自动被调用。"""
    try:
        import js
        js.console.log('[MAIN] main() called!')
    except:
        print('[MAIN] main() called!')
    try:
        game = Game()
        try:
            import js
            js.console.log('[MAIN] Game created, starting run...')
        except:
            pass
        await game.run()
    except Exception as e:
        try:
            import js
            js.console.log('[FATAL] Game crashed:', e)
        except:
            print('[FATAL] Game crashed:', e)
        import traceback
        traceback.print_exc()

try:
    import js
    js.console.log('[MAIN] main() defined, file loaded completely')
except:
    print('[MAIN] main() defined, file loaded completely')

# 顶层初始化游戏 (如果 pygbag 不自动调用 main)
try:
    import js
    js.console.log('[MAIN] Attempting direct game launch...')
except:
    print('[MAIN] Attempting direct game launch...')

try:
    game = Game()
    try:
        import js
        js.console.log('[MAIN] Game created directly! Starting async loop...')
        # 在 pygbag 环境中使用 ensure_future 启动游戏循环
        asyncio.ensure_future(game.run())
    except Exception as e:
        try:
            import js
            js.console.log('[MAIN] Failed to start async loop:', e)
        except:
            print('[MAIN] Failed to start async loop:', e)
except Exception as e:
    try:
        import js
        js.console.log('[MAIN] Direct launch failed:', e)
    except:
        print('[MAIN] Direct launch failed:', e)
