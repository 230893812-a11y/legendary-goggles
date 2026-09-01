# -*- coding: utf-8 -*-
"""
坦克大战 Tank Battle — 网页版 (Web Version)
基于 pygame-ce + pygbag 编译为 WebAssembly, 在浏览器中运行。

与桌面版的主要区别:
  1. 无 ctypes 窗口管理 (浏览器无窗口概念)
  2. 无文件 IO (日志/快照系统禁用)
  3. 使用 pygame 默认字体 (浏览器无中文字体)
  4. 背景图 1.jpg 通过 pygbag 数据打包

操作说明:
    W / 上箭头   向上移动
    S / 下箭头   向下移动
    A / 左箭头   向左移动
    D / 右箭头   向右移动
    空格 / J     发射炮弹
    P            暂停 / 继续
    R            游戏结束后重开
"""

import os
import sys
import random
import math
import time

import pygame

# 检测是否在 WebAssembly (pygbag) 环境下运行
IS_WEB = (sys.platform == 'emscripten')

# ====================== 基本配置 ======================
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
COLOR_WATER = (60, 120, 200)
COLOR_WATER_LIGHT = (90, 160, 230)
COLOR_GRASS = (60, 140, 60)
COLOR_BASE = (220, 180, 60)
COLOR_BASE_DARK = (150, 110, 30)
COLOR_TEXT = (245, 245, 245)
COLOR_ACCENT = (255, 170, 70)

# 瓦片类型
TILE_EMPTY = 0
TILE_BRICK = 1
TILE_STEEL = 2
TILE_WATER = 3
TILE_GRASS = 4
TILE_BASE = 5
TILE_BASE_DEAD = 6

# 方向
DIR_UP = 0
DIR_RIGHT = 1
DIR_DOWN = 2
DIR_LEFT = 3
DIR_DX = [0, 1, 0, -1]
DIR_DY = [-1, 0, 1, 0]


# ====================== 工具函数 ======================
def draw_tile(surf, tile_type, x, y, size=TILE):
    """绘制单个瓦片。"""
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
    elif tile_type == TILE_STEEL:
        pygame.draw.rect(surf, COLOR_STEEL, rect)
        pygame.draw.rect(surf, COLOR_STEEL_DARK, rect, 2)
        pygame.draw.line(surf, COLOR_STEEL_DARK,
                         (x + 4, y + 4), (x + size - 4, y + size - 4), 1)
        pygame.draw.line(surf, COLOR_STEEL_DARK,
                         (x + size - 4, y + 4), (x + 4, y + size - 4), 1)
    elif tile_type == TILE_WATER:
        pygame.draw.rect(surf, COLOR_WATER, rect)
        t = pygame.time.get_ticks() / 300.0
        for k in range(3):
            ox = (math.sin(t + k) + 1) * 6
            pygame.draw.line(surf, COLOR_WATER_LIGHT,
                             (x + ox, y + 6 + k * 8),
                             (x + ox + 10, y + 6 + k * 8), 1)
    elif tile_type == TILE_GRASS:
        pygame.draw.rect(surf, COLOR_GRASS, rect)
        for k in range(4):
            gx = x + (k * 7 + 3) % size
            gy = y + (k * 13 + 5) % size
            pygame.draw.circle(surf, (80, 170, 80), (gx, gy), 2)
    elif tile_type == TILE_BASE:
        pygame.draw.rect(surf, COLOR_BASE_DARK, rect)
        pygame.draw.rect(surf, COLOR_BASE, (x + 4, y + 4, size - 8, size - 8))
        pygame.draw.polygon(surf, COLOR_BASE_DARK,
                            [(x + size // 2, y + 6),
                             (x + size - 6, y + size // 2),
                             (x + size // 2, y + size - 6),
                             (x + 6, y + size // 2)])
    elif tile_type == TILE_BASE_DEAD:
        pygame.draw.rect(surf, COLOR_DARK_GRAY, rect)
        pygame.draw.line(surf, COLOR_RED, (x + 4, y + 4),
                         (x + size - 4, y + size - 4), 3)
        pygame.draw.line(surf, COLOR_RED, (x + size - 4, y + 4),
                         (x + 4, y + size - 4), 3)


def load_sound(name):
    """加载音效, 失败则返回 None。Web 版使用 pygbag 打包的数据文件。"""
    try:
        # pygbag 将数据文件放在 / 目录下
        if IS_WEB:
            return pygame.mixer.Sound('/' + name)
        return pygame.mixer.Sound(name)
    except Exception:
        return None


# ====================== 地图 ======================
def build_map():
    """构建地图, 中央区域用砖墙摆出玩家姓名缩写 "HD"。"""
    rows = 15
    cols = 20
    grid = [[TILE_EMPTY] * cols for _ in range(rows)]

    # 四周围墙 (钢墙)
    for c in range(cols):
        grid[0][c] = TILE_STEEL
        grid[rows - 1][c] = TILE_STEEL
    for r in range(rows):
        grid[r][0] = TILE_STEEL
        grid[r][cols - 1] = TILE_STEEL

    # 玩家基地 (下方中央)
    base_cx = cols // 2
    base_cy = rows - 2
    grid[base_cy][base_cx] = TILE_BASE
    for dc in (-1, 0, 1):
        c = base_cx + dc
        if 0 < c < cols - 1:
            grid[base_cy - 1][c] = TILE_BRICK
    grid[base_cy][base_cx - 1] = TILE_BRICK
    grid[base_cy][base_cx + 1] = TILE_BRICK

    # 随机砖墙障碍
    random.seed(42)
    for r in range(2, rows - 3):
        for c in range(2, cols - 2):
            if 5 <= r <= 9 and 7 <= c <= 12:
                continue
            if base_cy - 2 <= r <= base_cy and base_cx - 2 <= c <= base_cx + 2:
                continue
            if random.random() < 0.18:
                grid[r][c] = TILE_BRICK

    # 水池
    water_blocks = [(3, 5), (12, 13)]
    for cr, cc in water_blocks:
        if 0 < cr < rows - 1 and 0 < cc < cols - 1:
            grid[cr][cc] = TILE_WATER
            if cc + 1 < cols - 1:
                grid[cr][cc + 1] = TILE_WATER

    # 草地
    grass_blocks = [(2, 2), (2, 17), (11, 2), (11, 17)]
    for gr, gc in grass_blocks:
        if 0 < gr < rows - 1 and 0 < gc < cols - 1:
            grid[gr][gc] = TILE_GRASS
            if gc + 1 < cols - 1:
                grid[gr][gc + 1] = TILE_GRASS

    # 散布钢墙
    steel_positions = [(4, 4), (4, 15), (10, 4), (10, 15)]
    for sr, sc in steel_positions:
        if 0 < sr < rows - 1 and 0 < sc < cols - 1:
            if not (5 <= sr <= 9 and 7 <= sc <= 12):
                grid[sr][sc] = TILE_STEEL

    # 中央姓名缩写 "HD"
    initials_patterns = {
        'H': ["X.X", "X.X", "XXX", "X.X", "X.X"],
        'D': ["XX.", "X.X", "X.X", "X.X", "XX."],
    }

    player_initials = "HD"
    pattern_height = 5
    patterns = []
    total_width = 0
    for ch in player_initials:
        if ch in initials_patterns:
            pat = initials_patterns[ch]
            patterns.append(pat)
            total_width += len(pat[0]) + 1
    total_width = max(0, total_width - 1)

    start_col = (cols - total_width) // 2
    start_row = (rows - pattern_height) // 2

    cur_col = start_col
    for pat in patterns:
        for row_offset in range(pattern_height):
            line = pat[row_offset]
            for col_offset, ch in enumerate(line):
                r = start_row + row_offset
                c = cur_col + col_offset
                if 0 <= r < rows and 0 <= c < cols:
                    if ch == 'X' and grid[r][c] == TILE_EMPTY:
                        grid[r][c] = TILE_BRICK
        cur_col += len(pat[0]) + 1

    # 玩家出生点清空
    spawn_points = [
        (base_cy, base_cx - 3),
        (base_cy, base_cx + 3),
        (base_cy - 2, base_cx - 2),
        (base_cy - 2, base_cx + 2),
    ]
    for r, c in spawn_points:
        if 0 <= r < rows and 0 <= c < cols:
            if grid[r][c] != TILE_BASE:
                grid[r][c] = TILE_EMPTY

    return grid, (base_cx, base_cy)


# ====================== 子弹 ======================
class Bullet:
    def __init__(self, x, y, direction, owner, speed=8, power=1):
        self.x = x
        self.y = y
        self.direction = direction
        self.owner = owner
        self.speed = speed
        self.power = power
        self.size = 6
        self.dead = False

    def update(self):
        self.x += DIR_DX[self.direction] * self.speed
        self.y += DIR_DY[self.direction] * self.speed

    def rect(self):
        return pygame.Rect(self.x, self.y, self.size, self.size)

    def draw(self, surf):
        color = COLOR_YELLOW if self.owner == 'player' else COLOR_RED
        pygame.draw.rect(surf, color, self.rect(), border_radius=2)


# ====================== 坦克 ======================
class Tank:
    def __init__(self, x, y, direction, owner='player', kind=0):
        self.x = x
        self.y = y
        self.size = TILE - 2
        self.direction = direction
        self.owner = owner
        self.kind = kind
        self.speed = 2 if owner == 'player' else (1 if kind == 0 else 2)
        if kind == 2:
            self.hp = 3
        else:
            self.hp = 1
        self.cooldown = 0
        self.max_cooldown = 8 if owner == 'player' else 40
        self.alive = True
        self.moving = False
        self.tread_phase = 0
        self.spawn_time = pygame.time.get_ticks()

    def rect(self):
        return pygame.Rect(self.x, self.y, self.size, self.size)

    def center(self):
        return self.x + self.size // 2, self.y + self.size // 2

    def try_move(self, direction, game):
        self.direction = direction
        self.moving = True
        nx = self.x + DIR_DX[direction] * self.speed
        ny = self.y + DIR_DY[direction] * self.speed
        new_rect = pygame.Rect(nx, ny, self.size, self.size)

        left_bound = MARGIN
        right_bound = SCREEN_W - MARGIN
        top_bound = MARGIN + HUD_HEIGHT
        bottom_bound = SCREEN_H - MARGIN
        if nx < left_bound or ny < top_bound or \
           nx + self.size > right_bound or ny + self.size > bottom_bound:
            return False

        check_rect = new_rect.inflate(-2, -2)
        pts = [
            (check_rect.left, check_rect.top),
            (check_rect.right - 1, check_rect.top),
            (check_rect.left, check_rect.bottom - 1),
            (check_rect.right - 1, check_rect.bottom - 1),
            (check_rect.centerx, check_rect.centery),
        ]
        for px, py in pts:
            c = int((px - MARGIN) // TILE)
            r = int((py - MARGIN - HUD_HEIGHT) // TILE)
            if 0 <= r < ROWS and 0 <= c < COLS:
                t = game.grid[r][c]
                if t in (TILE_BRICK, TILE_STEEL, TILE_WATER,
                         TILE_BASE, TILE_BASE_DEAD):
                    return False

        for tank in game.all_tanks():
            if tank is self or not tank.alive:
                continue
            if new_rect.colliderect(tank.rect()):
                return False

        self.x = nx
        self.y = ny
        self.tread_phase = (self.tread_phase + 1) % 8
        return True

    def shoot(self, game):
        if self.cooldown > 0:
            return
        if self.owner == 'player':
            player_bullets = [b for b in game.bullets if b.owner == 'player']
            if len(player_bullets) >= 2:
                return
        cx, cy = self.center()
        bx = cx - 3 + DIR_DX[self.direction] * (self.size // 2)
        by = cy - 3 + DIR_DY[self.direction] * (self.size // 2)
        bullet = Bullet(bx, by, self.direction, self.owner,
                        speed=8 if self.owner == 'player' else 5,
                        power=2 if self.kind == 2 and self.owner == 'player' else 1)
        game.bullets.append(bullet)
        self.cooldown = self.max_cooldown
        game.play_sfx('shoot')

    def update_cooldown(self):
        if self.cooldown > 0:
            self.cooldown -= 1

    def hit(self, damage=1):
        self.hp -= damage
        if self.hp <= 0:
            self.alive = False

    def draw(self, surf):
        if not self.alive:
            return
        x, y, s = self.x, self.y, self.size

        if self.owner == 'player':
            body_c, tread_c, turret_c = (230, 220, 90), (180, 160, 60), (250, 240, 140)
        elif self.kind == 0:
            body_c, tread_c, turret_c = (200, 200, 200), (130, 130, 130), (180, 180, 180)
        elif self.kind == 1:
            body_c, tread_c, turret_c = (150, 200, 230), (100, 140, 180), (190, 220, 240)
        else:
            body_c, tread_c, turret_c = (160, 160, 160), (80, 80, 80), (200, 200, 200)

        elapsed = pygame.time.get_ticks() - self.spawn_time
        if elapsed < 1200 and (pygame.time.get_ticks() // 80) % 2 == 0:
            body_c = turret_c = (255, 255, 255)

        pygame.draw.rect(surf, body_c, (x, y, s, s), border_radius=3)

        dir_ = self.direction
        if dir_ in (DIR_UP, DIR_DOWN):
            pygame.draw.rect(surf, tread_c, (x + 1, y + 2, 4, s - 4), border_radius=2)
            pygame.draw.rect(surf, tread_c, (x + s - 5, y + 2, 4, s - 4), border_radius=2)
            for k in range(3):
                yy = y + 4 + k * ((s - 8) // 2) + (self.tread_phase % 4)
                pygame.draw.line(surf, body_c, (x + 1, yy), (x + 5, yy), 1)
                pygame.draw.line(surf, body_c, (x + s - 5, yy), (x + s - 1, yy), 1)
        else:
            pygame.draw.rect(surf, tread_c, (x + 2, y + 1, s - 4, 4), border_radius=2)
            pygame.draw.rect(surf, tread_c, (x + 2, y + s - 5, s - 4, 4), border_radius=2)
            for k in range(3):
                xx = x + 4 + k * ((s - 8) // 2) + (self.tread_phase % 4)
                pygame.draw.line(surf, body_c, (xx, y + 1), (xx, y + 5), 1)
                pygame.draw.line(surf, body_c, (xx, y + s - 5), (xx, y + s - 1), 1)

        cx, cy = x + s // 2, y + s // 2
        pygame.draw.circle(surf, turret_c, (cx, cy), s // 3)
        pygame.draw.circle(surf, tread_c, (cx, cy), s // 3, 1)

        barrel_len = s // 2 + 2
        barrel_w = 5
        if dir_ == DIR_UP:
            pygame.draw.rect(surf, turret_c,
                             (cx - barrel_w // 2, cy - barrel_len, barrel_w, barrel_len))
        elif dir_ == DIR_DOWN:
            pygame.draw.rect(surf, turret_c,
                             (cx - barrel_w // 2, cy, barrel_w, barrel_len))
        elif dir_ == DIR_LEFT:
            pygame.draw.rect(surf, turret_c,
                             (cx - barrel_len, cy - barrel_w // 2, barrel_len, barrel_w))
        elif dir_ == DIR_RIGHT:
            pygame.draw.rect(surf, turret_c,
                             (cx, cy - barrel_w // 2, barrel_len, barrel_w))

        if self.owner == 'enemy' and self.kind == 2 and self.hp > 0:
            bar_w = s - 4
            pygame.draw.rect(surf, COLOR_RED, (x + 2, y - 5, bar_w, 3))
            pygame.draw.rect(surf, COLOR_GREEN,
                             (x + 2, y - 5, int(bar_w * self.hp / 3.0), 3))


# ====================== 游戏主类 (Web 版) ======================
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()

        # 字体 — Web 版使用默认字体 (浏览器无中文字体)
        self.font_big = pygame.font.Font(None, 44)
        self.font_medium = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 20)

        # 底图
        self.bg_image = None
        self._load_background()

        # 音效
        self.sounds = {}
        self.sounds['shoot'] = load_sound('shoot.wav')
        self.sounds['explode'] = load_sound('explode.wav')

        # 按键日志
        self.last_keys_str = ""
        self.key_log_timer = 0

        # 重新开始反馈
        self._restart_flash_timer = 0
        self._restart_text_timer = 0

        # 预创建性能 Surface
        self._dark_overlay = pygame.Surface((SCREEN_W, SCREEN_H - HUD_HEIGHT))
        self._dark_overlay.set_alpha(160)
        self._dark_overlay.fill((10, 12, 24))
        self._game_overlay = pygame.Surface((SCREEN_W, SCREEN_H))
        self._game_overlay.set_alpha(200)
        self._game_overlay.fill((0, 0, 0))

        # 状态
        self.state = 'menu'
        self._running = True
        self.init_new_game()

    def _load_background(self):
        """加载背景图 1.jpg (Web 版通过 pygbag 打包在 / 目录下)。"""
        if IS_WEB:
            bg_path = '/1.jpg'
        else:
            bg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '1.jpg')
            if not os.path.isfile(bg_path):
                bg_path = '1.jpg'

        try:
            raw = pygame.image.load(bg_path).convert()
            scaled = pygame.transform.smoothscale(
                raw, (SCREEN_W, SCREEN_H - HUD_HEIGHT))
            self.bg_image = scaled.convert_alpha()
        except Exception:
            self.bg_image = None

    def _get_font(self, size):
        if size >= 40:
            return self.font_big
        elif size >= 24:
            return self.font_medium
        else:
            return self.font_small

    def _trigger_restart_feedback(self):
        self._restart_flash_timer = 10
        self._restart_text_timer = 60
        self.play_sfx('explode')

    def init_new_game(self):
        self.grid, self.base_pos = build_map()
        self.bullets = []
        self.explosions = []
        self.enemies = []
        self.score = 0
        self.level = 1
        self.lives = 3
        self.enemies_left = 10
        self.spawn_timer = 0
        self.spawn_index = 0
        self.max_active_enemies = 3
        self.player = None
        self.player_spawn()
        self.enemy_spawn_points = [(1, 1), (COLS - 2, 1), (COLS // 2, 1)]
        self.enemies_to_spawn = self.generate_enemy_queue(10)

    def generate_enemy_queue(self, count):
        queue = []
        for _ in range(count):
            r = random.random()
            queue.append(0 if r < 0.55 else (1 if r < 0.85 else 2))
        return queue

    def player_spawn(self):
        base_cx, base_cy = self.base_pos
        spawn_c = base_cx - 3
        spawn_r = base_cy
        px = MARGIN + spawn_c * TILE + 1
        py = MARGIN + HUD_HEIGHT + spawn_r * TILE + 1
        self.player = Tank(px, py, DIR_UP, owner='player', kind=0)

    def spawn_enemy(self):
        if not self.enemies_to_spawn:
            return
        if len([e for e in self.enemies if e.alive]) >= self.max_active_enemies:
            return
        sp = self.enemy_spawn_points[self.spawn_index % len(self.enemy_spawn_points)]
        self.spawn_index += 1
        ex = MARGIN + sp[0] * TILE + 1
        ey = MARGIN + HUD_HEIGHT + sp[1] * TILE + 1
        kind = self.enemies_to_spawn.pop(0)
        self.enemies.append(Tank(ex, ey, DIR_DOWN, owner='enemy', kind=kind))

    def all_tanks(self):
        tanks = []
        if self.player and self.player.alive:
            tanks.append(self.player)
        for e in self.enemies:
            if e.alive:
                tanks.append(e)
        return tanks

    def play_sfx(self, name):
        s = self.sounds.get(name)
        if s is not None:
            try:
                s.play()
            except Exception:
                pass

    def spawn_explosion(self, x, y, size=24):
        self.explosions.append({'x': x, 'y': y, 'r': 4, 'max_r': size,
                                'life': 18, 'max_life': 18})
        self.play_sfx('explode')

    def update_explosions(self):
        self.explosions = [e for e in self.explosions if e['life'] > 0]
        for e in self.explosions:
            e['life'] -= 1
            e['r'] = int(e['max_r'] * (1 - e['life'] / e['max_life']))

    # ==================== 输入处理 ====================
    def handle_input(self, events):
        keys = pygame.key.get_pressed()
        if self.state == 'playing' and self.player and self.player.alive:
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                self.player.try_move(DIR_UP, self)
            elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
                self.player.try_move(DIR_DOWN, self)
            elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
                self.player.try_move(DIR_LEFT, self)
            elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                self.player.try_move(DIR_RIGHT, self)
            else:
                self.player.moving = False

        pressed = []
        for k, name in [(pygame.K_w, 'W'), (pygame.K_a, 'A'),
                         (pygame.K_s, 'S'), (pygame.K_d, 'D'),
                         (pygame.K_UP, 'UP'), (pygame.K_DOWN, 'DOWN'),
                         (pygame.K_LEFT, 'LEFT'), (pygame.K_RIGHT, 'RIGHT'),
                         (pygame.K_SPACE, 'SPACE'), (pygame.K_j, 'J'),
                         (pygame.K_r, 'R'), (pygame.K_p, 'P')]:
            if keys[k]:
                pressed.append(name)
        if pressed:
            self.last_keys_str = '+'.join(pressed)
            self.key_log_timer = 90

        for ev in events:
            if ev.type != pygame.KEYDOWN:
                continue

            if ev.key == pygame.K_r:
                if self.state in ('gameover', 'victory', 'menu'):
                    self._trigger_restart_feedback()
                    self.init_new_game()
                    self.state = 'playing'
                continue

            if self.state == 'menu':
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_w,
                              pygame.K_a, pygame.K_s, pygame.K_d,
                              pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT,
                              pygame.K_RIGHT, pygame.K_j):
                    self._trigger_restart_feedback()
                    self.init_new_game()
                    self.state = 'playing'
                    continue

            if ev.key == pygame.K_p:
                if self.state == 'playing':
                    self.state = 'paused'
                elif self.state == 'paused':
                    self.state = 'playing'

            if self.state == 'playing' and self.player and self.player.alive:
                if ev.key in (pygame.K_SPACE, pygame.K_j):
                    self.player.shoot(self)
                elif ev.key in (pygame.K_w, pygame.K_UP):
                    self.player.try_move(DIR_UP, self)
                elif ev.key in (pygame.K_s, pygame.K_DOWN):
                    self.player.try_move(DIR_DOWN, self)
                elif ev.key in (pygame.K_a, pygame.K_LEFT):
                    self.player.try_move(DIR_LEFT, self)
                elif ev.key in (pygame.K_d, pygame.K_RIGHT):
                    self.player.try_move(DIR_RIGHT, self)

    # ==================== AI & 游戏逻辑 ====================
    def update_ai(self, enemy):
        if not enemy.alive:
            return
        if not hasattr(enemy, 'ai_dir_timer'):
            enemy.ai_dir_timer = 0
            enemy.ai_shoot_timer = random.randint(40, 100)

        enemy.ai_dir_timer -= 1
        enemy.ai_shoot_timer -= 1

        if enemy.ai_dir_timer <= 0 or not enemy.try_move(enemy.direction, self):
            cx, cy = enemy.center()
            base_x = MARGIN + self.base_pos[0] * TILE
            base_y = MARGIN + HUD_HEIGHT + self.base_pos[1] * TILE
            dx_t, dy_t = base_x - cx, base_y - cy

            candidates = list(range(4))
            random.shuffle(candidates)
            preferred = DIR_RIGHT if dx_t > 0 else DIR_LEFT if dx_t < 0 else \
                        DIR_DOWN if dy_t > 0 else DIR_UP
            if abs(dx_t) + abs(dy_t) > 0 and random.random() < 0.5:
                if preferred in candidates:
                    candidates.remove(preferred)
                candidates.insert(0, preferred)

            moved = False
            for d in candidates:
                if enemy.try_move(d, self):
                    enemy.ai_dir_timer = random.randint(30, 80)
                    moved = True
                    break
            if not moved:
                enemy.ai_dir_timer = 5

        if enemy.ai_shoot_timer <= 0:
            enemy.shoot(self)
            enemy.ai_shoot_timer = random.randint(50, 120)

        enemy.update_cooldown()

    def update_bullets(self):
        new_bullets = []
        for b in self.bullets:
            b.update()
            if b.x < MARGIN or b.y < MARGIN + HUD_HEIGHT or \
               b.x > SCREEN_W - MARGIN or b.y > SCREEN_H - MARGIN:
                self.spawn_explosion(b.x + 3, b.y + 3, 10)
                continue

            hit = False
            c = int((b.x + b.size // 2 - MARGIN) // TILE)
            r = int((b.y + b.size // 2 - MARGIN - HUD_HEIGHT) // TILE)
            if 0 <= r < ROWS and 0 <= c < COLS:
                t = self.grid[r][c]
                if t == TILE_BRICK:
                    self.grid[r][c] = TILE_EMPTY
                    self.spawn_explosion(b.x + 3, b.y + 3, 12)
                    hit = True
                elif t == TILE_STEEL:
                    if b.power >= 2:
                        self.grid[r][c] = TILE_EMPTY
                    self.spawn_explosion(b.x + 3, b.y + 3, 10)
                    hit = True
                elif t == TILE_BASE:
                    self.grid[r][c] = TILE_BASE_DEAD
                    self.spawn_explosion(b.x + 3, b.y + 3, 30)
                    self.state = 'gameover'
                    hit = True

            if not hit:
                b_rect = b.rect()
                for tank in self.all_tanks():
                    if tank.owner == b.owner:
                        continue
                    if b_rect.colliderect(tank.rect()):
                        tank.hit(damage=2 if tank.owner == 'enemy' and tank.kind == 2 else 1)
                        self.spawn_explosion(b.x + 3, b.y + 3, 16)
                        if not tank.alive and tank.owner == 'enemy':
                            self.score += 100 if tank.kind == 2 else (60 if tank.kind == 1 else 40)
                            self.enemies_left -= 1
                        hit = True
                        break

            if not hit:
                for b2 in self.bullets:
                    if b2 is b or b2.owner == b.owner:
                        continue
                    if b.rect().colliderect(b2.rect()):
                        b2.dead = True
                        self.spawn_explosion(b.x + 3, b.y + 3, 8)
                        hit = True
                        break

            if not hit and not b.dead:
                new_bullets.append(b)

        self.bullets = new_bullets

    def update_game(self):
        if self.state != 'playing':
            if self.player and self.player.alive and self.player.cooldown > 0:
                self.player.update_cooldown()
            return

        self.spawn_timer -= 1
        if self.spawn_timer <= 0 and self.enemies_to_spawn:
            self.spawn_enemy()
            self.spawn_timer = 120

        if self.player and self.player.alive:
            self.player.update_cooldown()

        for enemy in self.enemies:
            if enemy.alive:
                self.update_ai(enemy)

        self.enemies = [e for e in self.enemies if e.alive]
        self.update_bullets()
        self.update_explosions()

        if self.player and not self.player.alive:
            self.lives -= 1
            if self.lives > 0:
                self.player_spawn()
            else:
                self.state = 'gameover'

        if self.enemies_left <= 0 and not self.enemies_to_spawn:
            self.state = 'victory'

    # ==================== 绘制 ====================
    def draw_hud(self):
        pygame.draw.rect(self.screen, COLOR_HUD_BG,
                         (0, 0, SCREEN_W, HUD_HEIGHT))
        pygame.draw.line(self.screen, COLOR_DARK_GRAY,
                         (0, HUD_HEIGHT - 1), (SCREEN_W, HUD_HEIGHT - 1), 1)

        lives_text = self.font_small.render(
            f"Lives: {'❤' * max(0, self.lives)}", True, COLOR_WHITE)
        self.screen.blit(lives_text, (MARGIN, (HUD_HEIGHT - lives_text.get_height()) // 2))

        score_text = self.font_small.render(
            f"Score: {self.score}", True, COLOR_ACCENT)
        self.screen.blit(score_text, (MARGIN + 120, (HUD_HEIGHT - score_text.get_height()) // 2))

        level_text = self.font_small.render(
            f"Level: {self.level}", True, COLOR_WHITE)
        self.screen.blit(level_text, (MARGIN + 220, (HUD_HEIGHT - level_text.get_height()) // 2))

        enemy_text = self.font_small.render(
            f"Enemies: {self.enemies_left}", True, COLOR_RED)
        self.screen.blit(enemy_text, (MARGIN + 300, (HUD_HEIGHT - enemy_text.get_height()) // 2))

        title_text = self.font_small.render("TANK BATTLE - HD", True, COLOR_YELLOW)
        self.screen.blit(title_text,
                         (SCREEN_W - MARGIN - title_text.get_width(),
                          (HUD_HEIGHT - title_text.get_height()) // 2))

        tip = self.font_small.render(
            "WASD/Arrows:Move  Space/J:Shoot  P:Pause  R:Restart", True, COLOR_GRAY)
        self.screen.blit(tip,
                         (SCREEN_W // 2 - tip.get_width() // 2,
                          (HUD_HEIGHT - tip.get_height()) // 2))

        if self.key_log_timer > 0 and self.last_keys_str:
            self.key_log_timer -= 1
            key_text = self.font_small.render(
                f"Keys: {self.last_keys_str}", True, COLOR_GREEN)
            self.screen.blit(key_text, (MARGIN, HUD_HEIGHT + 2))

    def draw_background(self):
        self.screen.fill(COLOR_BG)
        if self.bg_image is not None:
            self.screen.blit(self.bg_image, (0, HUD_HEIGHT))
            self.screen.blit(self._dark_overlay, (0, HUD_HEIGHT))

    def draw_map(self):
        for r in range(ROWS):
            for c in range(COLS):
                t = self.grid[r][c]
                if t == TILE_EMPTY or t == TILE_GRASS:
                    continue
                draw_tile(self.screen, t,
                          MARGIN + c * TILE, MARGIN + HUD_HEIGHT + r * TILE)

    def draw_grass(self):
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] == TILE_GRASS:
                    draw_tile(self.screen, TILE_GRASS,
                              MARGIN + c * TILE, MARGIN + HUD_HEIGHT + r * TILE)

    def draw_tanks(self):
        if self.player and self.player.alive:
            self.player.draw(self.screen)
        for e in self.enemies:
            if e.alive:
                e.draw(self.screen)

    def draw_bullets(self):
        for b in self.bullets:
            b.draw(self.screen)

    def draw_explosions(self, surf=None):
        surf = surf or self.screen
        for e in self.explosions:
            alpha = int(220 * e['life'] / e['max_life'])
            r = max(2, e['r'])
            color = (min(255, 200 + alpha // 4), max(40, 120 + alpha // 3), 40)
            pygame.draw.circle(surf, color, (e['x'], e['y']), r)
            pygame.draw.circle(surf, COLOR_YELLOW, (e['x'], e['y']), max(1, r // 2), 1)

    def draw_overlay(self, title, subtitle, tips=None):
        self.screen.blit(self._game_overlay, (0, 0))

        title_surf = self.font_big.render(title, True, COLOR_YELLOW)
        self.screen.blit(title_surf,
                         (SCREEN_W // 2 - title_surf.get_width() // 2,
                          SCREEN_H // 2 - 80))

        sub_surf = self.font_medium.render(subtitle, True, COLOR_WHITE)
        self.screen.blit(sub_surf,
                         (SCREEN_W // 2 - sub_surf.get_width() // 2,
                          SCREEN_H // 2 - 20))

        if tips:
            tip_surf = self.font_small.render(tips, True, COLOR_GRAY)
            self.screen.blit(tip_surf,
                             (SCREEN_W // 2 - tip_surf.get_width() // 2,
                              SCREEN_H // 2 + 30))

    def draw_restart_feedback(self):
        if self._restart_flash_timer > 0:
            flash = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 180))
            self.screen.blit(flash, (0, 0))
            self._restart_flash_timer -= 1

        if self._restart_text_timer > 0:
            self._restart_text_timer -= 1
            t = self._restart_text_timer
            alpha = min(255, t * 4)
            color = (255, 200, 80) if t > 30 else (255, 255, 255)
            text_surf = self.font_medium.render("NEW GAME!", True, color)
            text_surf.set_alpha(alpha)
            scale = min(1.0, (60 - t) / 30.0)
            scaled = pygame.transform.smoothscale(
                text_surf,
                (int(text_surf.get_width() * scale),
                 int(text_surf.get_height() * scale)))
            self.screen.blit(scaled,
                             (SCREEN_W // 2 - scaled.get_width() // 2,
                              SCREEN_H // 2 - scaled.get_height() - 40))

    def draw(self):
        self.draw_background()
        self.draw_map()
        self.draw_tanks()
        self.draw_bullets()
        self.draw_grass()
        self.draw_explosions()
        self.draw_hud()
        self.draw_restart_feedback()

        if self.state == 'menu':
            self.draw_overlay("TANK BATTLE", "Player HD",
                              "Press W / Enter / Space to Start")
        elif self.state == 'paused':
            self.draw_overlay("PAUSED", "", "Press P to Resume")
        elif self.state == 'gameover':
            self.draw_overlay("GAME OVER", f"Score: {self.score}",
                              "Press R to Restart")
        elif self.state == 'victory':
            self.draw_overlay("VICTORY!", f"Score: {self.score}",
                              "Press R to Play Again")

    # ==================== 主循环 ====================
    def run(self):
        self._running = True
        clock_fps = pygame.time.Clock()

        # 清空事件队列
        pygame.event.clear()

        while self._running:
            frame_start = time.perf_counter()

            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    self._running = False
                    break
                # 处理窗口大小变化 (Web 版)
                if ev.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((ev.w, ev.h))

            if not self._running:
                break

            self.handle_input(events)
            self.update_game()
            self.draw()
            pygame.display.flip()

            frame_time_ms = (time.perf_counter() - frame_start) * 1000.0

            # Web 版不需要精确 FPS 控制, 但保持一致性
            clock_fps.tick(FPS)


# ====================== 入口 ======================
def main():
    """Web 版游戏入口。"""
    game = Game()
    game.run()


if __name__ == '__main__':
    main()