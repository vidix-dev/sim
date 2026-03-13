#!/usr/bin/env python3
"""
Simulation du Comportement Humain
Inspirée de la vidéo de Code BH — Evolution de l'égoïsme dans une population.

Touches:
  ESPACE  — pause/reprise
  +/-     — accélérer/ralentir la simulation
  ÉCHAP   — quitter
"""

import pygame
import random
import math
import sys
from collections import deque

# ─────────────────────────────────────────────────────────────────────────────
#  INIT
# ─────────────────────────────────────────────────────────────────────────────
pygame.init()

W, H = 1400, 860
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Simulation du Comportement Humain — Code BH")
clock = pygame.time.Clock()
FPS = 60

def _font(size, bold=False):
    for n in ("Segoe UI", "Ubuntu", "DejaVu Sans", "Arial"):
        try:
            return pygame.font.SysFont(n, size, bold=bold)
        except Exception:
            pass
    return pygame.font.Font(None, size + 4)

F_TITLE = _font(30, bold=True)
F_BIG   = _font(22, bold=True)
F_MED   = _font(18)
F_SM    = _font(14)
F_XS    = _font(11)

# ─────────────────────────────────────────────────────────────────────────────
#  LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
PRAIRIE_W = 950   # left area (roaming + village)
PANEL_X   = PRAIRIE_W
PANEL_W   = W - PRAIRIE_W   # 450 px right panel

VX, VY  = 700, 60   # village zone top-left within prairie
VW, VH  = PRAIRIE_W - VX - 8, H - 60

# Open roaming field bounds
FX1, FY1 = 12, 12
FX2, FY2 = VX - 18, H - 12

# ─────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
BASE_DAY_TICKS   = FPS * 20   # 20 real seconds per day
NIGHT_TICKS      = FPS * 4
RESULTS_TICKS    = FPS * 3
TRANSITION_TICKS = FPS * 1

SURVIVAL_THRESH  = 5
REPRO_EVERY      = 5          # 1 child per 5 extra points
TENT_CAP         = 10
COW_TARGET       = 16
COW_PTS          = 10
CONFLICT_PEN     = 1
MUTATION_P       = 0.10
MAX_CARROTS      = 80
CARROT_RATE      = 0.09       # probability per frame to spawn a carrot

STRATEGIES       = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
STRAT_LABELS     = ["10%","20%","30%","40%","50%","60%","70%","80%","90%"]

# ─────────────────────────────────────────────────────────────────────────────
#  COLORS
# ─────────────────────────────────────────────────────────────────────────────
GRASS_A   = (40, 112, 36)
GRASS_B   = (52, 132, 46)
GRASS_C   = (28, 84, 24)
DIRT_C    = (128, 108, 70)
SKY_D     = (98, 180, 228)
SKY_DUSK  = (215, 128, 68)
SKY_NIGHT = (10, 14, 44)
SUN_C     = (255, 232, 60)
MOON_C    = (228, 234, 218)
STAR_C    = (240, 245, 220)

CARROT_C  = (255, 132, 18)
CARROT_G  = (14, 172, 50)
COW_C     = (216, 206, 182)
COW_SPOT  = (66, 46, 26)
TENT_C    = (152, 98, 60)
TENT_D    = (106, 66, 36)
OBE_C     = (90, 86, 116)
OBE_L     = (136, 130, 160)

PANEL_BG  = (13, 17, 29)
PANEL_BG2 = (19, 25, 41)
BORDER_C  = (42, 56, 94)
TEXT_C    = (213, 218, 233)
DIM_C     = (106, 116, 142)
GOLD_C    = (255, 210, 58)
WHITE     = (255, 255, 255)
RED_C     = (215, 52, 52)
GREEN_C   = (50, 198, 70)
SMOKE_C   = (176, 176, 176)

# Strategy colors: altruiste (blue) → égoïste (red)
SCOLS = [
    ( 64, 152, 255),
    ( 78, 183, 238),
    ( 93, 205, 188),
    (122, 214, 133),
    (192, 214,  73),
    (230, 190,  64),
    (246, 150,  49),
    (246,  95,  39),
    (236,  45,  35),
]

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def lerp(a, b, t):
    return a + (b - a) * t

def lc(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], max(0.0, min(1.0, t)))) for i in range(3))

def dst(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def rrect(surf, col, rect, r=6, alpha=255):
    if alpha < 255:
        s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        pygame.draw.rect(s, (*col, alpha), (0, 0, rect[2], rect[3]), border_radius=r)
        surf.blit(s, (rect[0], rect[1]))
    else:
        pygame.draw.rect(surf, col, rect, border_radius=r)

def txt(surf, s, font, col, x, y, center=False):
    shadow = font.render(s, True, (0, 0, 0))
    label  = font.render(s, True, col)
    if center:
        r = label.get_rect(center=(x, y))
        surf.blit(shadow, (r.x + 1, r.y + 1))
        surf.blit(label, r)
    else:
        surf.blit(shadow, (x + 1, y + 1))
        surf.blit(label, (x, y))

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# ─────────────────────────────────────────────────────────────────────────────
#  PARTICLES
# ─────────────────────────────────────────────────────────────────────────────
class Particle:
    __slots__ = ('x','y','vx','vy','color','life','max_life','size')

    def __init__(self, x, y, color, vx, vy, life, size=4):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.color = color
        self.life = self.max_life = life
        self.size = size

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.06
        self.life -= 1
        return self.life > 0

    def draw(self, surf):
        frac  = self.life / self.max_life
        alpha = int(255 * frac)
        r     = max(1, int(self.size * frac))
        s = pygame.Surface((r*2+1, r*2+1), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surf.blit(s, (int(self.x) - r, int(self.y) - r))

particles = []

def spawn_particles(x, y, color, n=10, speed=2.5, life=25, size=4):
    for _ in range(n):
        a  = random.uniform(0, math.tau)
        sp = random.uniform(0.4, speed)
        particles.append(Particle(x, y, color,
                                  math.cos(a)*sp, math.sin(a)*sp - 0.8,
                                  life, size))

def spawn_smoke(x, y, n=18):
    for _ in range(n):
        vx = random.uniform(-1.2, 1.2)
        vy = random.uniform(-2.8, -0.6)
        sz = random.randint(5, 11)
        lf = random.randint(28, 50)
        particles.append(Particle(x, y, SMOKE_C, vx, vy, lf, sz))

def spawn_score(x, y, text_str, color):
    # Floating score text — stored as a special particle-like object
    floating_texts.append(FloatingText(x, y, text_str, color))

# ─────────────────────────────────────────────────────────────────────────────
#  FLOATING TEXT
# ─────────────────────────────────────────────────────────────────────────────
class FloatingText:
    def __init__(self, x, y, text, color):
        self.x, self.y = float(x), float(y)
        self.text  = text
        self.color = color
        self.life  = 60
        self.vy    = -1.0

    def update(self):
        self.y   += self.vy
        self.vy  *= 0.96
        self.life -= 1
        return self.life > 0

    def draw(self, surf):
        alpha = int(255 * min(1.0, self.life / 30))
        s = F_SM.render(self.text, True, self.color)
        s.set_alpha(alpha)
        surf.blit(s, (int(self.x) - s.get_width()//2, int(self.y)))

floating_texts = []

# ─────────────────────────────────────────────────────────────────────────────
#  CARROT
# ─────────────────────────────────────────────────────────────────────────────
class Carrot:
    def __init__(self):
        self.x     = random.uniform(FX1 + 12, FX2 - 12)
        self.y     = random.uniform(FY1 + 12, FY2 - 12)
        self.alive = True
        self.sc    = random.uniform(0.75, 1.25)

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        r = max(3, int(6 * self.sc))
        pts = [(x, y - r), (x - r//2, y + r//2), (x + r//2, y + r//2)]
        pygame.draw.polygon(surf, CARROT_C, pts)
        pygame.draw.polygon(surf, (200, 90, 0), pts, 1)
        for i in range(3):
            gx = x + (i - 1) * 3
            pygame.draw.line(surf, CARROT_G, (gx, y - r), (gx, y - r - 5), 1)

# ─────────────────────────────────────────────────────────────────────────────
#  COW
# ─────────────────────────────────────────────────────────────────────────────
class Cow:
    def __init__(self):
        self.x  = random.uniform(FX1 + 25, FX2 - 25)
        self.y  = random.uniform(FY1 + 25, FY2 - 25)
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-0.5, 0.5)
        self.alive     = True
        self.hunted_by = []
        self.anim      = random.uniform(0, math.tau)

    def update(self):
        if self.hunted_by:
            return
        self.anim += 0.05
        self.vx   += random.uniform(-0.06, 0.06)
        self.vy   += random.uniform(-0.06, 0.06)
        sp = math.hypot(self.vx, self.vy)
        if sp > 0.7:
            self.vx *= 0.7 / sp
            self.vy *= 0.7 / sp
        self.x = clamp(self.x + self.vx, FX1+25, FX2-25)
        self.y = clamp(self.y + self.vy, FY1+25, FY2-25)

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        # Shadow
        sh = pygame.Surface((32, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 55), (0, 0, 32, 12))
        surf.blit(sh, (x - 16, y + 8))
        # Body
        pygame.draw.ellipse(surf, COW_C, (x-14, y-8, 28, 16))
        # Spots
        pygame.draw.circle(surf, COW_SPOT, (x - 4, y - 2), 4)
        pygame.draw.circle(surf, COW_SPOT, (x + 7,  y + 1), 3)
        # Head
        pygame.draw.ellipse(surf, COW_C, (x + 10, y - 9, 14, 10))
        # Nose
        pygame.draw.ellipse(surf, (190, 160, 140), (x+19, y-5, 6, 4))
        # Legs (animated)
        for lx_off in [-8, -2, 4, 10]:
            bob = int(math.sin(self.anim + lx_off) * 2)
            pygame.draw.line(surf, TENT_D, (x+lx_off, y+8), (x+lx_off, y+8+5+bob), 2)
        # Horns
        hx = x + 20
        pygame.draw.line(surf, (210, 190, 130), (hx+2, y-8), (hx+5, y-13), 1)
        pygame.draw.line(surf, (210, 190, 130), (hx+6, y-7), (hx+9, y-12), 1)

# ─────────────────────────────────────────────────────────────────────────────
#  CHARACTER
# ─────────────────────────────────────────────────────────────────────────────
BNAMES = [
    "Bernard","Bernadette","Bernardo","Bertrand","Benoît","Bérénice",
    "Benedikt","Berthe","Bastien","Béatrice","Bruno","Brigitte",
    "Baptiste","Blanche","Benjamin","Bélinda","Boris","Blandine",
    "Brieuc","Brice","Bénédicte","Bertille","Baudouin","Blaise",
]
_name_idx = 0

def next_name():
    global _name_idx
    n = BNAMES[_name_idx % len(BNAMES)]
    _name_idx += 1
    return n


class Character:
    SPEED = 1.9

    def __init__(self, x, y, strategy=0.5):
        self.x, self.y   = float(x), float(y)
        self.strategy    = strategy
        self.name        = next_name()
        self.score       = 0
        self.alive       = True
        self.anim        = random.uniform(0, math.tau)
        self.target      = None
        self.state       = "roam"   # roam|seek_carrot|seek_partner|go_hunt|go_home|sleep
        self.carrot_tgt  = None
        self.partner     = None
        self.cow_tgt     = None
        self.home_tent   = None
        self.hunt_done   = False
        self.flash       = 0
        self.body_r      = 9

    @property
    def strat_idx(self):
        return min(range(len(STRATEGIES)),
                   key=lambda i: abs(STRATEGIES[i] - self.strategy))

    @property
    def color(self):
        return SCOLS[self.strat_idx]

    def _rand_target(self):
        self.target = (random.uniform(FX1+20, FX2-20),
                       random.uniform(FY1+20, FY2-20))

    def move_toward(self, tx, ty, speed=None):
        sp = speed or self.SPEED
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d < sp:
            self.x, self.y = tx, ty
            return True
        self.x += dx/d * sp
        self.y += dy/d * sp
        self.anim += 0.18
        return False

    def update(self, carrots, cows, hunt_phase):
        self.anim += 0.02
        if self.flash > 0:
            self.flash -= 1

        if self.state == "sleep":
            return

        if self.state == "go_home":
            tx = self.home_tent.x + random.uniform(-14, 14) if self.home_tent else VX+VW//2
            ty = self.home_tent.y + 6 if self.home_tent else VY+VH//2
            if self.move_toward(tx, ty, 2.6):
                self.state = "sleep"
            return

        # Hunt phase
        if hunt_phase and not self.hunt_done:
            if self.state not in ("seek_partner", "go_hunt"):
                self.state   = "seek_partner"
                self.partner = None
                self.cow_tgt = None

        if self.state == "seek_partner":
            # Stand still; pairing handled by Simulation
            if self.partner and self.partner.alive and self.partner.partner is self:
                self.state = "go_hunt"
            return

        if self.state == "go_hunt":
            if not self.cow_tgt or not self.cow_tgt.alive:
                self.state     = "roam"
                self.hunt_done = True
                return
            self.move_toward(self.cow_tgt.x, self.cow_tgt.y, 2.2)
            return

        # Normal: collect carrots
        if self.state in ("roam", "seek_carrot"):
            best, bd = None, 160.0
            for c in carrots:
                if c.alive:
                    d = dst((self.x, self.y), (c.x, c.y))
                    if d < bd:
                        bd, best = d, c

            if best:
                self.carrot_tgt = best
                self.state      = "seek_carrot"
            else:
                self.state = "roam"

            if self.state == "seek_carrot" and self.carrot_tgt:
                if not self.carrot_tgt.alive:
                    self.state      = "roam"
                    self.carrot_tgt = None
                else:
                    arrived = self.move_toward(self.carrot_tgt.x, self.carrot_tgt.y)
                    if arrived:
                        if self.carrot_tgt.alive:
                            self.carrot_tgt.alive = False
                            self.score += 1
                            self.flash  = 15
                            spawn_particles(self.x, self.y, CARROT_C, 5, 1.8, 16, 3)
                            spawn_score(self.x, self.y - 12, "+1", CARROT_C)
                        self.state      = "roam"
                        self.carrot_tgt = None
                    return

            if self.state == "roam":
                if not self.target or dst((self.x, self.y), self.target) < 12:
                    self._rand_target()
                self.move_toward(*self.target)

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        r    = self.body_r

        # Shadow
        sh = pygame.Surface((r*3, r), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0,0,0,55), (0, 0, r*3, r))
        surf.blit(sh, (x - r*3//2, y + r - 2))

        # Body
        col = self.color
        if self.flash > 0:
            col = lc(col, WHITE, self.flash / 15)
        pygame.draw.circle(surf, col, (x, y), r)
        pygame.draw.circle(surf, WHITE, (x, y), r, 1)

        # Face
        eye_off = int(math.cos(self.anim * 0.08) * 1.5)
        for ex in [x - 3 + eye_off, x + 3 + eye_off]:
            pygame.draw.circle(surf, WHITE, (ex, y - 2), 2)
            pygame.draw.circle(surf, (15, 15, 15), (ex, y - 2), 1)

        # Legs (walking bob)
        bob = int(math.sin(self.anim * 3.5) * 2)
        pygame.draw.line(surf, TENT_D, (x-4, y+r), (x-5, y+r+5+bob), 2)
        pygame.draw.line(surf, TENT_D, (x+4, y+r), (x+5, y+r+5-bob), 2)

        # Strategy dot on head
        pygame.draw.circle(surf, SCOLS[self.strat_idx], (x, y - r - 4), 3)
        pygame.draw.circle(surf, WHITE,                  (x, y - r - 4), 3, 1)

        # Name tag (only for first 4 characters)
        if hasattr(self, '_show_name') and self._show_name:
            ns = F_XS.render(self.name, True, TEXT_C)
            ns.set_alpha(180)
            surf.blit(ns, (x - ns.get_width()//2, y - r - 16))

# ─────────────────────────────────────────────────────────────────────────────
#  TENT
# ─────────────────────────────────────────────────────────────────────────────
class Tent:
    def __init__(self, x, y):
        self.x, self.y   = x, y
        self.residents   = []
        self.capacity    = TENT_CAP
        self._anim_light = random.uniform(0, math.tau)

    @property
    def full(self):
        return len(self.residents) >= self.capacity

    def draw(self, surf, night_frac=0.0):
        x, y  = int(self.x), int(self.y)
        w, h2 = 38, 30
        self._anim_light += 0.04

        # Shadow
        sh = pygame.Surface((w + 8, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0,0,0,60), (0,0,w+8,10))
        surf.blit(sh, (x - w//2 - 4, y + h2//3 + 2))

        # Tent body
        pts = [(x, y - h2), (x - w//2, y + h2//3), (x + w//2, y + h2//3)]
        pygame.draw.polygon(surf, TENT_C, pts)
        pygame.draw.polygon(surf, TENT_D, pts, 2)

        # Door
        door = pygame.Rect(x - 6, y + h2//3 - 12, 12, 12)
        pygame.draw.rect(surf, TENT_D, door, border_radius=4)
        pygame.draw.rect(surf, (55, 25, 10), door, border_radius=4)

        # Window glow at night
        win_col = (230, 200, 100) if night_frac > 0.3 else (200, 200, 150)
        glow    = int(0.7 + 0.3 * math.sin(self._anim_light)) if night_frac > 0.3 else 0
        pygame.draw.circle(surf, win_col, (x, y - 6), 4)
        pygame.draw.circle(surf, TENT_D,  (x, y - 6), 4, 1)
        if glow > 0 and night_frac > 0.3:
            gs = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*win_col, int(60 * night_frac)), (10,10), 9)
            surf.blit(gs, (x - 10, y - 16))

        # Capacity
        cap = F_XS.render(f"{len(self.residents)}/{self.capacity}", True, WHITE)
        surf.blit(cap, (x - cap.get_width()//2, y + h2//3 + 3))

# ─────────────────────────────────────────────────────────────────────────────
#  OBELISK
# ─────────────────────────────────────────────────────────────────────────────
def draw_obelisk(surf, x, y):
    # Shadow
    sh = pygame.Surface((30, 10), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0,0,0,55), (0,0,30,10))
    surf.blit(sh, (x-15, y+60))
    # Base
    pygame.draw.rect(surf, OBE_C, (x-11, y+42, 22, 18), border_radius=2)
    pygame.draw.rect(surf, OBE_L, (x-11, y+42, 22, 18), 1, border_radius=2)
    # Shaft
    pts = [(x-8, y+42), (x+8, y+42), (x+4, y-10), (x-4, y-10)]
    pygame.draw.polygon(surf, OBE_C, pts)
    pygame.draw.polygon(surf, OBE_L, pts, 1)
    # Tip
    pygame.draw.polygon(surf, OBE_L, [(x, y-26), (x-4, y-10), (x+4, y-10)])
    # Glyphs
    for gy in [y + 2, y + 14, y + 26]:
        pygame.draw.line(surf, OBE_L, (x-4, gy), (x+4, gy), 1)
    # Glyph circles
    pygame.draw.circle(surf, OBE_L, (x, y - 4), 2)

# ─────────────────────────────────────────────────────────────────────────────
#  VILLAGE
# ─────────────────────────────────────────────────────────────────────────────
class Village:
    def __init__(self):
        self.tents     = []
        self.positions = self._gen_positions()

    def _gen_positions(self):
        pos  = []
        cols = 2
        tw, th = 60, 72
        ox = VX + 22
        oy = VY + 90
        for row in range(12):
            for col in range(cols):
                x = ox + col * tw + (row % 2) * 16
                y = oy + row * th
                if x < PRAIRIE_W - 20 and y < H - 30:
                    pos.append((x, y))
        return pos

    def ensure_capacity(self, n):
        needed = max(1, math.ceil(n / TENT_CAP))
        while len(self.tents) < needed and len(self.tents) < len(self.positions):
            px, py = self.positions[len(self.tents)]
            self.tents.append(Tent(px, py))

    def assign(self, char):
        for t in self.tents:
            if not t.full:
                t.residents.append(char)
                char.home_tent = t
                return
        if len(self.tents) < len(self.positions):
            px, py = self.positions[len(self.tents)]
            t = Tent(px, py)
            self.tents.append(t)
            t.residents.append(char)
            char.home_tent = t

    def draw(self, surf, night_frac=0.0):
        for t in self.tents:
            t.draw(surf, night_frac)
        draw_obelisk(surf, VX + VW//2, VY + 42)

# ─────────────────────────────────────────────────────────────────────────────
#  HISTORY GRAPH
# ─────────────────────────────────────────────────────────────────────────────
class HistoryGraph:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.records = deque(maxlen=40)

    def record(self, chars):
        cnt = {s: 0 for s in STRATEGIES}
        for c in chars:
            s = STRATEGIES[min(range(len(STRATEGIES)),
                               key=lambda i: abs(STRATEGIES[i] - c.strategy))]
            cnt[s] += 1
        self.records.append(dict(cnt))

    def draw(self, surf):
        rrect(surf, PANEL_BG2, (self.x, self.y, self.w, self.h), 6)
        pygame.draw.rect(surf, BORDER_C, (self.x, self.y, self.w, self.h), 1, border_radius=6)
        txt(surf, "Évolution des stratégies par jour", F_XS, DIM_C,
            self.x + 4, self.y + 3)
        if not self.records:
            return
        n  = len(self.records)
        bw = max(2, (self.w - 8) // n)
        for i, rec in enumerate(self.records):
            total = sum(rec.values()) or 1
            bx    = self.x + 4 + i * bw
            by    = self.y + self.h - 4
            used  = 0
            for si, s in enumerate(STRATEGIES):
                seg = int(rec[s] / total * (self.h - 18))
                if seg > 0:
                    pygame.draw.rect(surf, SCOLS[si],
                                     (bx, by - used - seg, bw - 1, seg))
                    used += seg

# ─────────────────────────────────────────────────────────────────────────────
#  BACKGROUND
# ─────────────────────────────────────────────────────────────────────────────
# Pre-baked grass texture
_GRASS_DECO = [
    (random.randint(FX1, FX2), random.randint(FY1, FY2),
     random.randint(3, 7),
     random.choice([GRASS_B, GRASS_C, (48, 125, 42)]))
    for _ in range(500)
]
# Stars
_STARS = [(random.randint(10, PRAIRIE_W-10), random.randint(5, 140),
           random.uniform(0.5, 1.5)) for _ in range(80)]

def draw_sky(surf, tod):
    """tod: 0=morning, 1=full night"""
    if tod < 0.5:
        sky = lc(SKY_D, SKY_DUSK, tod * 2)
    else:
        sky = lc(SKY_DUSK, SKY_NIGHT, (tod - 0.5) * 2)
    pygame.draw.rect(surf, sky, (0, 0, PRAIRIE_W, 150))

    # Sun
    sun_x = int(PRAIRIE_W * 0.45)
    sun_y = int(90 - math.sin(math.pi * (1 - tod * 1.4)) * 70)
    sun_a = int(255 * max(0, 1 - tod * 1.6))
    if sun_a > 0:
        ss = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(ss, (*SUN_C, sun_a), (16,16), 14)
        for ra in range(0, 360, 40):
            rad = math.radians(ra)
            pygame.draw.line(ss, (*SUN_C, sun_a//2),
                             (16+int(math.cos(rad)*12), 16+int(math.sin(rad)*12)),
                             (16+int(math.cos(rad)*20), 16+int(math.sin(rad)*20)), 2)
        surf.blit(ss, (sun_x-16, sun_y-16))

    # Moon & stars
    if tod > 0.45:
        moon_a = int(255 * min(1, (tod - 0.45) * 3))
        ms = pygame.Surface((22, 22), pygame.SRCALPHA)
        pygame.draw.circle(ms, (*MOON_C, moon_a), (11,11), 10)
        # crescent
        pygame.draw.circle(ms, (*SKY_NIGHT, moon_a), (15, 9), 8)
        surf.blit(ms, (90, 40))
        for sx, sy, ss2 in _STARS:
            if sy < 140:
                sa = int(moon_a * 0.8)
                twinkle = int(math.sin(pygame.time.get_ticks() * 0.002 + sx) * 40)
                sa = clamp(sa + twinkle, 0, 255)
                pygame.draw.circle(surf, (*STAR_C, sa),
                                   (sx, sy), int(ss2))

def draw_background(surf, tod):
    draw_sky(surf, tod)
    # Ground
    pygame.draw.rect(surf, GRASS_A, (0, 0, PRAIRIE_W, H))
    # Grass texture
    for gx, gy, gs, gc in _GRASS_DECO:
        pygame.draw.circle(surf, gc, (gx, gy), gs)
    # Village dirt area
    village_surf = pygame.Surface((VW + 14, VH + 14), pygame.SRCALPHA)
    pygame.draw.rect(village_surf, (*DIRT_C, 90), (0, 0, VW+14, VH+14), border_radius=5)
    surf.blit(village_surf, (VX - 7, VY - 7))
    # Path from field to village
    pygame.draw.rect(surf, DIRT_C, (FX2 - 24, H//2 - 14, VX - FX2 + 32, 28))

def draw_panel(surf):
    pygame.draw.rect(surf, PANEL_BG, (PANEL_X, 0, PANEL_W, H))
    pygame.draw.line(surf, BORDER_C, (PANEL_X, 0), (PANEL_X, H), 2)

# ─────────────────────────────────────────────────────────────────────────────
#  HUNT RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────
def resolve_hunt(s1, s2, cow_pts=COW_PTS):
    """
    Returns (p1, p2) points for each hunter.
    Rules from the video:
      - sum == 100%: complementary, each gets their share
      - sum <  100%: each gets their share + remainder split (selfish gets odd point)
      - sum >  100%: conflict, each gets exclusive portion minus penalty
    """
    c1    = round(s1 * cow_pts)
    c2    = round(s2 * cow_pts)
    total = c1 + c2
    if total == cow_pts:
        return c1, c2
    elif total < cow_pts:
        rem = cow_pts - total
        if rem % 2 == 0:
            return c1 + rem // 2, c2 + rem // 2
        else:
            if s1 >= s2:   # s1 more selfish
                return c1 + (rem + 1)//2, c2 + (rem - 1)//2
            else:
                return c1 + (rem - 1)//2, c2 + (rem + 1)//2
    else:  # conflict
        p1 = round((1.0 - s2) * cow_pts) - CONFLICT_PEN
        p2 = round((1.0 - s1) * cow_pts) - CONFLICT_PEN
        return p1, p2

def mutate(strategy):
    idx = min(range(len(STRATEGIES)),
              key=lambda i: abs(STRATEGIES[i] - strategy))
    r = random.random()
    if r < MUTATION_P / 2:
        idx = max(0, idx - 1)
    elif r < MUTATION_P:
        idx = min(len(STRATEGIES) - 1, idx + 1)
    return STRATEGIES[idx]

# ─────────────────────────────────────────────────────────────────────────────
#  NOTIFICATION BANNER
# ─────────────────────────────────────────────────────────────────────────────
class Notification:
    def __init__(self, text, color=WHITE, life=220):
        self.text  = text
        self.color = color
        self.life  = life

    def draw(self, surf, y):
        alpha = min(255, self.life * 3)
        s  = F_MED.render(self.text, True, self.color)
        bg = pygame.Surface((s.get_width() + 16, s.get_height() + 8), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0,0,0, alpha//2), (0,0,bg.get_width(),bg.get_height()), border_radius=5)
        bg.set_alpha(alpha)
        sx = PRAIRIE_W//2 - s.get_width()//2
        surf.blit(bg, (sx - 8, y - 4))
        s.set_alpha(alpha)
        surf.blit(s, (sx, y))

# ─────────────────────────────────────────────────────────────────────────────
#  SIMULATION
# ─────────────────────────────────────────────────────────────────────────────
class Simulation:
    def __init__(self):
        self.day         = 0
        self.tick        = 0
        self.speed       = 1          # 1x, 2x, 4x
        self.paused      = False
        self.phase       = "day"      # day | night | results | transition
        self.phase_tick  = 0
        self.hunt_phase  = False
        self.cows_on     = False
        self.strats_on   = False

        self.characters  = []
        self.carrots     = []
        self.cows        = []
        self.village     = Village()
        self.graph       = HistoryGraph(PANEL_X + 10, H - 188, PANEL_W - 20, 174)
        self.notifs      = []
        self.pop_history = []
        self.day_results = []

        global _name_idx
        _name_idx = 0
        self._start_day1()

    # ── Setup ──────────────────────────────────────────────────────
    def _start_day1(self):
        self.day = 1
        b = Character(FX1 + 100, FY1 + 180, 0.5)
        b.name        = "Bernard"
        b._show_name  = True
        self.characters = [b]
        self.village.ensure_capacity(1)
        self.village.assign(b)
        self._new_day()

    def _new_day(self):
        self.tick        = 0
        self.phase       = "day"
        self.phase_tick  = 0
        self.hunt_phase  = False
        self.cows_on     = self.day >= 6
        self.strats_on   = self.day >= 9

        # Spawn initial carrots
        for _ in range(35):
            self.carrots.append(Carrot())

        # Reset characters
        for c in self.characters:
            c.state      = "roam"
            c.score      = 0
            c.hunt_done  = False
            c.partner    = None
            c.cow_tgt    = None
            c._rand_target()

        # Show names for first 4
        for i, c in enumerate(self.characters):
            c._show_name = (i < 4)

        # Spawn cows
        if self.cows_on:
            alive = sum(1 for cv in self.cows if cv.alive)
            for _ in range(max(0, COW_TARGET - alive)):
                self.cows.append(Cow())

    def _end_day(self):
        self.phase      = "night"
        self.phase_tick = 0
        for c in self.characters:
            c.state = "go_home"

        self.day_results = [(c.name, c.score) for c in self.characters]

        survivors = []
        newborns  = []
        for c in self.characters:
            if c.score >= SURVIVAL_THRESH:
                survivors.append(c)
                extras = c.score - SURVIVAL_THRESH
                n_ch   = extras // REPRO_EVERY
                for _ in range(n_ch):
                    cx     = random.uniform(FX1 + 30, FX2 - 30)
                    cy     = random.uniform(FY1 + 30, FY2 - 30)
                    strat  = mutate(c.strategy) if self.strats_on else 0.5
                    child  = Character(cx, cy, strat)
                    newborns.append(child)
            else:
                spawn_particles(c.x, c.y, RED_C, 14, 2.5, 30, 4)

        self.characters = survivors + newborns

        # Day 9: distribute 9 strategy groups evenly
        if self.day == 9 and self.strats_on and self.characters:
            n = len(self.characters)
            for i, c in enumerate(self.characters):
                c.strategy = STRATEGIES[i % len(STRATEGIES)]

        # Rebuild village
        self.village.ensure_capacity(len(self.characters))
        for t in self.village.tents:
            t.residents.clear()
        for c in self.characters:
            c.home_tent = None
        for c in self.characters:
            self.village.assign(c)

        self.graph.record(self.characters)
        self.pop_history.append(len(self.characters))
        self.cows = [cv for cv in self.cows if cv.alive]

        self._notify(f"Jour {self.day} terminé — Population: {len(self.characters)}", GOLD_C)

    # ── Pairing ────────────────────────────────────────────────────
    def _pair_hunters(self):
        seekers = [c for c in self.characters
                   if c.state == "seek_partner" and c.partner is None]
        random.shuffle(seekers)
        while len(seekers) >= 2:
            a, b = seekers.pop(), seekers.pop()
            a.partner = b
            b.partner = a
            alive_cows = [cv for cv in self.cows if cv.alive and not cv.hunted_by]
            if alive_cows:
                cow       = min(alive_cows, key=lambda cv: dst((a.x, a.y), (cv.x, cv.y)))
                a.cow_tgt = cow
                b.cow_tgt = cow
                cow.hunted_by = [a, b]
            a.state = "go_hunt"
            b.state = "go_hunt"

    def _check_hunt(self):
        done = set()
        for c in self.characters:
            if c.state != "go_hunt" or not c.partner or not c.cow_tgt:
                continue
            if id(c) in done or id(c.partner) in done:
                continue
            d1 = dst((c.x, c.y),           (c.cow_tgt.x, c.cow_tgt.y))
            d2 = dst((c.partner.x, c.partner.y), (c.cow_tgt.x, c.cow_tgt.y))
            if d1 < 14 and d2 < 14:
                p1, p2 = resolve_hunt(c.strategy, c.partner.strategy)
                c.score         += max(0, p1)
                c.partner.score += max(0, p2)
                conflict = (c.strategy + c.partner.strategy > 1.001)
                if conflict:
                    spawn_particles(c.cow_tgt.x, c.cow_tgt.y, RED_C, 10, 2, 25)
                    spawn_score(c.x,         c.y - 14, f"{p1:+}", RED_C   if p1<0 else GOLD_C)
                    spawn_score(c.partner.x, c.partner.y - 14, f"{p2:+}", RED_C if p2<0 else GOLD_C)
                else:
                    spawn_smoke(c.cow_tgt.x, c.cow_tgt.y)
                    spawn_score(c.x,         c.y - 14,         f"+{p1}", GOLD_C)
                    spawn_score(c.partner.x, c.partner.y - 14, f"+{p2}", GOLD_C)
                c.cow_tgt.alive = False
                c.hunt_done = c.partner.hunt_done = True
                done.add(id(c)); done.add(id(c.partner))
                c.state = c.partner.state = "roam"
                c.partner.partner = None
                c.partner = None
                c.cow_tgt = None
                if sum(1 for cv in self.cows if cv.alive) < COW_TARGET:
                    self.cows.append(Cow())

    # ── Update ─────────────────────────────────────────────────────
    def update(self):
        global particles, floating_texts
        if self.paused:
            return

        steps = self.speed
        for _ in range(steps):
            self._update_once()

    def _update_once(self):
        global particles, floating_texts

        if self.phase == "transition":
            self.phase_tick += 1
            if self.phase_tick >= TRANSITION_TICKS:
                self.day += 1
                self._new_day()
            return

        if self.phase == "results":
            self.phase_tick += 1
            if self.phase_tick >= RESULTS_TICKS:
                self.phase      = "transition"
                self.phase_tick = 0
            return

        if self.phase == "night":
            self.phase_tick += 1
            for c in self.characters:
                c.update(self.carrots, self.cows, False)
            if self.phase_tick >= NIGHT_TICKS:
                self.phase      = "results"
                self.phase_tick = 0
            return

        # ── Day phase ──────────────────────────────────────────────
        self.tick += 1
        frac = self.tick / BASE_DAY_TICKS

        # Start hunt phase at 72% of day
        if frac >= 0.72 and not self.hunt_phase and self.cows_on:
            self.hunt_phase = True
            self._notify("Phase de chasse !", GOLD_C, 160)

        # Day 6 first cow notification
        if self.day == 6 and self.tick == 1:
            self._notify("Des vaches apparaissent dans la prairie !", COW_C, 220)
        if self.day == 9 and self.tick == 1:
            self._notify("Stratégies de partage introduites !", GREEN_C, 240)

        # Spawn carrots
        if random.random() < CARROT_RATE and len(self.carrots) < MAX_CARROTS:
            self.carrots.append(Carrot())

        # Spawn / replenish cows
        if self.cows_on:
            alive = sum(1 for cv in self.cows if cv.alive)
            if alive < COW_TARGET and random.random() < 0.025:
                self.cows.append(Cow())

        # Update cows
        for cv in self.cows:
            if cv.alive:
                cv.update()

        # Pairing & hunt checks
        if self.hunt_phase:
            self._pair_hunters()
            self._check_hunt()

        # Update characters
        for c in self.characters:
            c.update(self.carrots, self.cows, self.hunt_phase)

        # Particles & texts
        particles     = [p for p in particles     if p.update()]
        floating_texts = [ft for ft in floating_texts if ft.update()]

        # Notifications countdown
        for n in self.notifs:
            n.life -= 1
        self.notifs = [n for n in self.notifs if n.life > 0]

        # End of day
        if self.tick >= BASE_DAY_TICKS:
            self._end_day()

    def _notify(self, text, color=WHITE, life=220):
        self.notifs.append(Notification(text, color, life))

    # ── Draw ───────────────────────────────────────────────────────
    def draw(self):
        frac = self.tick / BASE_DAY_TICKS if self.phase == "day" else 1.0
        tod  = frac * 0.6
        if self.phase in ("night", "results", "transition"):
            tod = lerp(0.6, 1.0, min(1.0, self.phase_tick / (NIGHT_TICKS * 0.8)))

        draw_background(screen, tod)

        # Carrots
        for c in self.carrots:
            if c.alive:
                c.draw(screen)

        # Cows
        for cv in self.cows:
            if cv.alive:
                cv.draw(screen)

        # Village
        self.village.draw(screen, tod)

        # Characters (sort by y for depth)
        for c in sorted(self.characters, key=lambda c: c.y):
            c.draw(screen)

        # Particles
        for p in particles:
            p.draw(screen)
        for ft in floating_texts:
            ft.draw(screen)

        # Day timer bar
        if self.phase == "day":
            pygame.draw.rect(screen, (22, 22, 38), (0, H-8, PRAIRIE_W, 8))
            bar_w   = int(PRAIRIE_W * frac)
            bar_col = lc(GREEN_C, RED_C, frac)
            pygame.draw.rect(screen, bar_col, (0, H-8, bar_w, 8))
            # Time label
            rem = max(0, (BASE_DAY_TICKS - self.tick) // FPS // max(1, self.speed))
            ts  = F_SM.render(f"{rem}s", True, lc(GREEN_C, RED_C, frac))
            screen.blit(ts, (PRAIRIE_W - ts.get_width() - 4, H - 8 - ts.get_height() - 2))

        # Notifications
        for i, n in enumerate(self.notifs):
            n.draw(screen, 18 + i * 28)

        # Panel
        self._draw_panel()

    def _draw_panel(self):
        draw_panel(screen)
        px = PANEL_X + 12
        py = 14

        # Title
        txt(screen, "Comportement", F_BIG,   GOLD_C, PANEL_X + PANEL_W//2, py+2,  center=True)
        txt(screen, "Humain",       F_TITLE, WHITE,  PANEL_X + PANEL_W//2, py+26, center=True)
        py += 62

        # Day box
        phase_color = {
            "day": GREEN_C, "night": (100, 130, 220),
            "results": GOLD_C, "transition": DIM_C
        }.get(self.phase, WHITE)
        rrect(screen, PANEL_BG2, (px, py, PANEL_W-24, 54), 7)
        pygame.draw.rect(screen, phase_color, (px, py, PANEL_W-24, 54), 2, border_radius=7)
        txt(screen, f"Jour {self.day}", F_BIG, GOLD_C, PANEL_X+PANEL_W//2, py+8, center=True)
        phase_strs = {"day": "Journée", "night": "Nuit", "results": "Résultats",
                      "transition": "..."}
        ps = phase_strs.get(self.phase, self.phase)
        if self.hunt_phase and self.phase == "day":
            ps = "Phase de chasse"
        txt(screen, ps, F_SM, DIM_C, PANEL_X+PANEL_W//2, py+32, center=True)
        py += 62

        # Population
        pop = len(self.characters)
        txt(screen, f"Population: {pop}", F_MED, TEXT_C, px, py)
        py += 24

        # Speed indicator
        sp_col = GOLD_C if self.speed > 1 else DIM_C
        txt(screen, f"Vitesse: x{self.speed}  [+/-]", F_XS, sp_col, px, py)
        if self.paused:
            txt(screen, "[PAUSE]", F_XS, RED_C, px + 130, py)
        py += 22

        # Day timer (if in day phase)
        if self.phase == "day":
            frac = self.tick / BASE_DAY_TICKS
            bar_rect = (px, py, PANEL_W - 24, 10)
            pygame.draw.rect(screen, (30, 35, 55), bar_rect, border_radius=4)
            fill_w = int((PANEL_W - 24) * frac)
            if fill_w > 0:
                pygame.draw.rect(screen, lc(GREEN_C, RED_C, frac),
                                 (px, py, fill_w, 10), border_radius=4)
            py += 18

        py += 4

        # Strategy distribution
        if self.strats_on and self.characters:
            txt(screen, "Stratégies:", F_SM, DIM_C, px, py)
            py += 18
            cnt   = {s: 0 for s in STRATEGIES}
            total = len(self.characters) or 1
            for c in self.characters:
                s = STRATEGIES[min(range(len(STRATEGIES)),
                                   key=lambda i: abs(STRATEGIES[i] - c.strategy))]
                cnt[s] += 1
            bw = PANEL_W - 24
            bh = 17
            for si, s in enumerate(STRATEGIES):
                n_s  = cnt[s]
                prop = n_s / total
                fw   = int(bw * prop)
                rrect(screen, (28, 34, 52), (px, py, bw, bh), 3)
                if fw > 0:
                    rrect(screen, SCOLS[si], (px, py, fw, bh), 3)
                lbl_col = WHITE if prop > 0.05 else DIM_C
                lbl     = F_XS.render(f"{STRAT_LABELS[si]} ({n_s})", True, lbl_col)
                screen.blit(lbl, (px + 4, py + 2))
                py += bh + 2
            py += 6

            # Gradient legend
            txt(screen, "← Altruiste        Égoïste →", F_XS, DIM_C, px, py)
            py += 14
            lw = (PANEL_W - 24) // 9
            for si in range(9):
                pygame.draw.rect(screen, SCOLS[si],
                                 (px + si*lw, py, lw, 8), border_radius=2)
            py += 16
        else:
            py += 20

        # Population history
        if self.pop_history:
            mx = max(self.pop_history)
            txt(screen, f"Max population: {mx}  (Jour {self.pop_history.index(mx)+1})",
                F_XS, DIM_C, px, py)
            py += 16

        # Recent day results
        if self.phase in ("results", "transition") and self.day_results:
            txt(screen, "Résultats du jour:", F_SM, GOLD_C, px, py)
            py += 18
            sorted_r = sorted(self.day_results, key=lambda x: x[1], reverse=True)[:9]
            for name, score in sorted_r:
                col = GREEN_C if score >= SURVIVAL_THRESH else RED_C
                sym = "✓" if score >= SURVIVAL_THRESH else "✗"
                txt(screen, f"{sym} {name}: {score} pts", F_XS, col, px, py)
                py += 14
            py += 4

        # Mini stats
        if self.day > 1 and self.pop_history:
            txt(screen, f"Carottes sur le terrain: {sum(1 for c in self.carrots if c.alive)}",
                F_XS, DIM_C, px, py)
            py += 14
            if self.cows_on:
                txt(screen, f"Vaches: {sum(1 for cv in self.cows if cv.alive)}",
                    F_XS, DIM_C, px, py)
                py += 14

        # Graph
        self.graph.draw(screen)

        # Controls hint
        hint = F_XS.render("ESPACE: pause  |  +/-: vitesse  |  ÉCHAP: quitter", True, DIM_C)
        screen.blit(hint, (PANEL_X + PANEL_W//2 - hint.get_width()//2, H - 14))

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    sim = Simulation()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    sim.paused = not sim.paused
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    sim.speed = min(8, sim.speed * 2)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    sim.speed = max(1, sim.speed // 2)
                elif event.key == pygame.K_r:
                    # Restart
                    global particles, floating_texts, _name_idx
                    particles      = []
                    floating_texts = []
                    _name_idx      = 0
                    sim = Simulation()

        sim.update()
        sim.draw()
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
