import base64
import glob
import io
import math
import os
import random
import sys
import time

import pygame
from aigptundertale_ost_data import OST_AUDIO_B64, OST_FORMAT, OST_TITLE

pygame.init()

# Window + timing: Undertale battle logic runs at ~30 Hz; we render at 60 FPS and scale
# per-frame motion so real-time speed matches the original.
DISPLAY_FPS = 60
UNDERTALE_FPS = 30
UT_SPEED = UNDERTALE_FPS / DISPLAY_FPS

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("AC'S UNDERTALE SANS FIGHT")
clock = pygame.time.Clock()

# Fonts
font_title = pygame.font.SysFont("Courier New", 46, bold=True)
font_med = pygame.font.SysFont("Courier New", 29, bold=True)
font_small = pygame.font.SysFont("Courier New", 21, bold=True)

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 60, 60)
YELLOW = (255, 230, 70)
GREEN = (0, 255, 0)
ORANGE = (255, 128, 32)
BLUE = (80, 190, 255)
DARK_BLUE = (0, 60, 255)
PURPLE = (160, 90, 255)
GRAY = (75, 75, 75)

# Main menu
MAIN_MENU_OPTIONS = ["START", "QUIT"]
main_menu_selected = 0
MAIN_MENU_BW, MAIN_MENU_BH = 320, 44
MAIN_MENU_Y_START, MAIN_MENU_GAP = 310, 14
MAIN_MENU_PULSE_MS = 900
MAIN_MENU_SOUL_BOB_PX = 3

# States
STATE_INTRO = 0
STATE_DIALOGUE = 1
STATE_FIGHT = 2
STATE_GAME_OVER = 3

game_state = STATE_INTRO
dialogue_lines = [
    "heya.",
    "you've been busy, huh?",
    "our reports showed a massive anomaly in the timespace continuum.",
    "it looks like this is where i stop you."
]
dialogue_index = 0

# Undertale-like player stats
player_name = "CHARA"
player_lv = 19
player_max_hp = 92
player_hp = float(player_max_hp)
karma = 0.0
invuln_frames = 0

# Soul + battle box
soul_size = 16  # Standard UT 16x16
soul_speed = 5.0 * UT_SPEED  # 150 px/sec
box_x, box_y = 250, 175
box_w, box_h = 300, 225
soul_x = float(box_x + box_w // 2 - soul_size // 2)
soul_y = float(box_y + box_h // 2 - soul_size // 2)
soul_rect = pygame.Rect(int(soul_x), int(soul_y), soul_size, soul_size)

# Blue Soul Physics
soul_mode = "red"
soul_vy = 0.0
is_grounded = False
GRAVITY = 0.8 * UT_SPEED
JUMP_POWER = -11.0 * UT_SPEED
MAX_FALL_SPEED = 12.0 * UT_SPEED

# Attack timing & Sequencing
bullets = []
gaster_blasters = []
scheduled_events = []
attack_index = 0
fight_text = "* Sans is finally giving it his all."

# Turn system (OG-style command turn -> enemy turn)
ACTION_LABELS = ["FIGHT", "ACT", "ITEM", "MERCY"]
PHASE_PLAYER = "player"
PHASE_WAIT = "sans_wait"
PHASE_ATTACK = "sans_attack"
fight_phase = PHASE_PLAYER
selected_action = 0
phase_started_at = 0.0
sans_wait_duration = 0.0
SANS_ATTACK_DURATION = 6.0
BLASTER_WARMUP = 0.65
BLASTER_BEAM_TIME = 0.40
BLASTER_DAMAGE = 2.0
BLASTER_CHARGE_FLASH = 0.12
BEAM_SCREEN_FLASH = 0.09

beam_flash_until = 0.0

EMBEDDED_SANS_PNG_B64 = (
    "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"
)

def make_embedded_sans_sprite():
    png_data = base64.b64decode(EMBEDDED_SANS_PNG_B64)
    return pygame.image.load(io.BytesIO(png_data)).convert_alpha()

sans_sprite = make_embedded_sans_sprite()
sans_sprite_scaled = pygame.transform.scale(
    sans_sprite, (sans_sprite.get_width() * 2, sans_sprite.get_height() * 2)
)

def get_heart_sprite(color):
    surf = pygame.Surface((16, 16), pygame.SRCALPHA)
    # Authentic 16x16 Undertale Heart Pixel Data
    pixels = [
        "                ",
        "                ",
        "   XXXX  XXXX   ",
        "  XXXXXX XXXXXX ",
        " XXXXXXXXXXXXXX ",
        " XXXXXXXXXXXXXX ",
        " XXXXXXXXXXXXXX ",
        " XXXXXXXXXXXXXX ",
        "  XXXXXXXXXXXX  ",
        "   XXXXXXXXXX   ",
        "    XXXXXXXX    ",
        "     XXXXXX     ",
        "      XXXX      ",
        "       XX       ",
        "                ",
        "                "
    ]
    for y, row in enumerate(pixels):
        for x, char in enumerate(row):
            if char == 'X':
                surf.set_at((x, y), color)
    return surf

heart_red = get_heart_sprite(RED)
heart_blue = get_heart_sprite(DARK_BLUE)

# Pre-rendered HUD/menu assets (Constants updated conditionally below if image loaded)
MENU_BX, MENU_BY = 10, 562
MENU_BW, MENU_BH, MENU_GAP = 185, 28, 10

def make_menu_button_surface(label, color):
    surf = pygame.Surface((MENU_BW, MENU_BH), pygame.SRCALPHA)
    pygame.draw.rect(surf, color, (0, 0, MENU_BW, MENU_BH), 3)
    txt = font_small.render(label, True, color)
    surf.blit(txt, ((MENU_BW - txt.get_width()) // 2, 3))
    return surf

# Fallback buttons just in case the image cannot be found
fallback_buttons = {
    "FIGHT": (make_menu_button_surface("FIGHT", ORANGE), make_menu_button_surface("FIGHT", YELLOW)),
    "ACT": (make_menu_button_surface("ACT", ORANGE), make_menu_button_surface("ACT", YELLOW)),
    "ITEM": (make_menu_button_surface("ITEM", ORANGE), make_menu_button_surface("ITEM", YELLOW)),
    "MERCY": (make_menu_button_surface("MERCY", ORANGE), make_menu_button_surface("MERCY", YELLOW))
}

button_sprites = {}
use_image_buttons = False

EMBEDDED_HUD_BUTTONS_PNG_B64 = (
    "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"
)

# Embedded HUD sprite-sheet loading logic (8 vertically stacked strips:
# ACT(red/yellow), FIGHT(red/yellow), ITEM(red/yellow), MERCY(red/yellow)).
try:
    png_data = base64.b64decode(EMBEDDED_HUD_BUTTONS_PNG_B64)
    buttons_sheet = pygame.image.load(io.BytesIO(png_data)).convert_alpha()
    sheet_w, sheet_h = buttons_sheet.get_size()
    if sheet_h < 8:
        raise ValueError(f"HUD sheet too short: {sheet_w}x{sheet_h}")
    slice_w = sheet_w
    slice_h = sheet_h // 8

    IMG_MENU_BW, IMG_MENU_BH = 154, 42

    def get_btn_slice(idx):
        rect = pygame.Rect(0, int(idx * slice_h), int(slice_w), int(slice_h))
        slice_surf = buttons_sheet.subsurface(rect).copy()
        return pygame.transform.scale(slice_surf, (IMG_MENU_BW, IMG_MENU_BH))

    button_sprites["ACT"] = (get_btn_slice(0), get_btn_slice(1))
    button_sprites["FIGHT"] = (get_btn_slice(2), get_btn_slice(3))
    button_sprites["ITEM"] = (get_btn_slice(4), get_btn_slice(5))
    button_sprites["MERCY"] = (get_btn_slice(6), get_btn_slice(7))
    use_image_buttons = True

    MENU_BW, MENU_BH = IMG_MENU_BW, IMG_MENU_BH
    MENU_GAP = 30
    MENU_BX = (WIDTH - (4 * MENU_BW + 3 * MENU_GAP)) // 2
    MENU_BY = 545
    print("[UI] Loaded embedded HUD button sheet (base64).")
except Exception as e:
    print(f"[UI] Embedded HUD button sheet failed ({e}); using fallback UI buttons.")

# Force HUD to use only pre-baked procedural surfaces (no PNG-rendered HUD in-game).
use_image_buttons = False
MENU_BX, MENU_BY = 10, 562
MENU_BW, MENU_BH, MENU_GAP = 185, 28, 10

def make_main_menu_button_surface(label, edge, inner):
    surf = pygame.Surface((MAIN_MENU_BW, MAIN_MENU_BH), pygame.SRCALPHA)
    pygame.draw.rect(surf, edge, (0, 0, MAIN_MENU_BW, MAIN_MENU_BH), 4)
    pygame.draw.rect(surf, inner, (4, 4, MAIN_MENU_BW - 8, MAIN_MENU_BH - 8), 2)
    txt = font_med.render(label, True, edge)
    surf.blit(txt, ((MAIN_MENU_BW - txt.get_width()) // 2, (MAIN_MENU_BH - txt.get_height()) // 2))
    return surf

def make_main_menu_glow_surface():
    surf = pygame.Surface((MAIN_MENU_BW + 20, MAIN_MENU_BH + 20), pygame.SRCALPHA)
    pygame.draw.rect(surf, YELLOW, (4, 4, MAIN_MENU_BW + 12, MAIN_MENU_BH + 12), 2, border_radius=4)
    pygame.draw.rect(surf, ORANGE, (0, 0, MAIN_MENU_BW + 20, MAIN_MENU_BH + 20), 1, border_radius=6)
    return surf

main_menu_button_idle = [
    make_main_menu_button_surface(label, ORANGE, GRAY) for label in MAIN_MENU_OPTIONS
]
main_menu_button_selected = [
    make_main_menu_button_surface(label, YELLOW, ORANGE) for label in MAIN_MENU_OPTIONS
]
_main_glow_base = make_main_menu_glow_surface()
main_menu_glow_frames = []
for i in range(12):
    phase = (2 * math.pi * i) / 12
    alpha = 60 + int(110 * ((math.sin(phase) + 1) * 0.5))
    frame = _main_glow_base.copy()
    frame.set_alpha(alpha)
    main_menu_glow_frames.append(frame)

# Gaster blaster rendering logic
def blaster_open_and_charge(blaster, now):
    spawn = blaster["warmup_end"] - BLASTER_WARMUP
    if now >= blaster["warmup_end"]:
        u_open = 1.0 if now <= blaster["beam_end"] else 0.0
    else:
        u_open = max(0.0, min(1.0, (now - spawn) / BLASTER_WARMUP))
    charge = 0.0
    if now < blaster["warmup_end"] and (blaster["warmup_end"] - now) <= BLASTER_CHARGE_FLASH:
        charge = 0.5 + 0.5 * math.sin(now * 80.0)
    return u_open, charge

def render_gaster_blaster_dynamic(u_open, charge_pulse):
    surf = pygame.Surface((118, 74), pygame.SRCALPHA)
    u = max(0.0, min(1.0, float(u_open)))
    pygame.draw.ellipse(surf, WHITE, (8, 10, 80, 50))
    pygame.draw.ellipse(surf, BLACK, (8, 10, 80, 50), 2)
    sn_top = 25
    sn_top_h = max(4, int(12 - 4 * u))
    pygame.draw.rect(surf, WHITE, (66, sn_top, 40, sn_top_h), border_radius=6)
    pygame.draw.rect(surf, BLACK, (66, sn_top, 40, sn_top_h), 2, border_radius=6)
    gap = max(2, int(2 + u * 22))
    jaw_y = sn_top + sn_top_h + gap
    jaw_h = max(5, int(8 + u * 22))
    pygame.draw.rect(surf, WHITE, (66, jaw_y, 40, jaw_h), border_radius=6)
    pygame.draw.rect(surf, BLACK, (66, jaw_y, 40, jaw_h), 2, border_radius=6)
    pygame.draw.ellipse(surf, BLACK, (68, sn_top + sn_top_h - 1, 36, max(4, gap + 2)))
    pygame.draw.polygon(surf, WHITE, [(20, 12), (13, 1), (28, 9)])
    pygame.draw.polygon(surf, WHITE, [(48, 10), (53, 0), (57, 12)])
    pygame.draw.polygon(surf, WHITE, [(74, 12), (84, 2), (78, 15)])
    pygame.draw.polygon(surf, BLACK, [(20, 12), (13, 1), (28, 9)], 1)
    pygame.draw.polygon(surf, BLACK, [(48, 10), (53, 0), (57, 12)], 1)
    pygame.draw.polygon(surf, BLACK, [(74, 12), (84, 2), (78, 15)], 1)
    pygame.draw.ellipse(surf, BLACK, (21, 25, 16, 12))
    pygame.draw.ellipse(surf, BLACK, (52, 24, 16, 13))
    cp = max(0.0, min(1.0, float(charge_pulse)))
    if cp > 0.22:
        pr = max(2, int(2 + 3 * cp))
        pygame.draw.ellipse(surf, (230, 248, 255), (25, 28, pr, 3))
        pygame.draw.ellipse(surf, (230, 248, 255), (56, 27, pr, 3))
    fy = jaw_y + jaw_h - 10 + int(4 * u)
    pygame.draw.polygon(surf, WHITE, [(72, fy), (76, fy + 9), (80, fy)])
    pygame.draw.polygon(surf, WHITE, [(86, fy), (90, fy + 9), (94, fy)])
    pygame.draw.polygon(surf, BLACK, [(72, fy), (76, fy + 9), (80, fy)], 1)
    pygame.draw.polygon(surf, BLACK, [(86, fy), (90, fy + 9), (94, fy)], 1)
    return surf

bullet_surface_cache = {}

def get_bullet_surface(width, height, color, kind):
    key = (int(width), int(height), tuple(color), kind)
    cached = bullet_surface_cache.get(key)
    if cached is not None:
        return cached

    surf = pygame.Surface((max(2, int(width)), max(2, int(height))), pygame.SRCALPHA)
    w, h = surf.get_width(), surf.get_height()

    if kind == "platform":
        pygame.draw.rect(surf, GREEN, (0, 0, w, h))
        pygame.draw.rect(surf, WHITE, (0, 0, w, h), 1)
    elif kind == "bone":
        horizontal = w >= h
        base = tuple(max(0, min(255, c)) for c in color)
        outline = tuple(max(0, min(255, int(c * 0.75))) for c in base)

        if horizontal:
            cap = max(4, h // 2)
            shaft_h = max(2, h - 6)
            shaft_y = (h - shaft_h) // 2
            pygame.draw.rect(surf, base, (cap - 1, shaft_y, max(2, w - 2 * cap + 2), shaft_h), border_radius=max(1, shaft_h // 2))
            pygame.draw.circle(surf, base, (cap - 1, h // 2), cap - 1)
            pygame.draw.circle(surf, base, (w - cap, h // 2), cap - 1)
            pygame.draw.rect(surf, outline, (cap - 1, shaft_y, max(2, w - 2 * cap + 2), shaft_h), 1, border_radius=max(1, shaft_h // 2))
            pygame.draw.circle(surf, outline, (cap - 1, h // 2), cap - 1, 1)
            pygame.draw.circle(surf, outline, (w - cap, h // 2), cap - 1, 1)
            core_h = max(1, shaft_h // 3)
            core_y = h // 2 - core_h // 2
            pygame.draw.rect(surf, WHITE, (cap, core_y, max(2, w - 2 * cap), core_h), border_radius=max(1, core_h // 2))
            pygame.draw.circle(surf, WHITE, (cap - 1, h // 2), max(1, cap // 2))
            pygame.draw.circle(surf, WHITE, (w - cap, h // 2), max(1, cap // 2))
        else:
            cap = max(4, w // 2)
            shaft_w = max(2, w - 6)
            shaft_x = (w - shaft_w) // 2
            pygame.draw.rect(surf, base, (shaft_x, cap - 1, shaft_w, max(2, h - 2 * cap + 2)), border_radius=max(1, shaft_w // 2))
            pygame.draw.circle(surf, base, (w // 2, cap - 1), cap - 1)
            pygame.draw.circle(surf, base, (w // 2, h - cap), cap - 1)
            pygame.draw.rect(surf, outline, (shaft_x, cap - 1, shaft_w, max(2, h - 2 * cap + 2)), 1, border_radius=max(1, shaft_w // 2))
            pygame.draw.circle(surf, outline, (w // 2, cap - 1), cap - 1, 1)
            pygame.draw.circle(surf, outline, (w // 2, h - cap), cap - 1, 1)
            core_w = max(1, shaft_w // 3)
            core_x = w // 2 - core_w // 2
            pygame.draw.rect(surf, WHITE, (core_x, cap, core_w, max(2, h - 2 * cap)), border_radius=max(1, core_w // 2))
            pygame.draw.circle(surf, WHITE, (w // 2, cap - 1), max(1, cap // 2))
            pygame.draw.circle(surf, WHITE, (w // 2, h - cap), max(1, cap // 2))

    bullet_surface_cache[key] = surf
    return surf

ost_buffer = None
ost_loaded = False

def init_baked_ost():
    global ost_buffer, ost_loaded
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        if not ost_loaded:
            ost_buffer = io.BytesIO(base64.b64decode(OST_AUDIO_B64))
            pygame.mixer.music.load(ost_buffer, OST_FORMAT)
            pygame.mixer.music.set_volume(0.55)
            pygame.mixer.music.play(-1)
            ost_loaded = True
            print(f"[OST] Loaded embedded track: {OST_TITLE}")
    except Exception as err:
        print(f"[OST] Failed to load embedded track: {err}")

def set_soul_mode(mode):
    global soul_mode, soul_vy, is_grounded
    soul_mode = mode
    if mode == "blue":
        soul_vy = 0.0
        is_grounded = False

def schedule_event(time_offset, func, *args):
    scheduled_events.append({
        "trigger_time": time_offset,
        "func": func,
        "args": args,
        "fired": False
    })

def reset_run_state():
    global game_state, dialogue_index, player_hp, karma
    global soul_x, soul_y, attack_index, invuln_frames
    global fight_phase, selected_action, phase_started_at, sans_wait_duration, fight_text
    global beam_flash_until
    
    game_state = STATE_INTRO
    dialogue_index = 0
    player_hp = float(player_max_hp)
    karma = 0.0
    invuln_frames = 0
    soul_x = float(box_x + box_w // 2 - soul_size // 2)
    soul_y = float(box_y + box_h // 2 - soul_size // 2)
    soul_rect.topleft = (int(soul_x), int(soul_y))
    
    set_soul_mode("red")
    bullets.clear()
    gaster_blasters.clear()
    scheduled_events.clear()
    
    attack_index = 0
    fight_phase = PHASE_PLAYER
    selected_action = 0
    phase_started_at = time.time()
    sans_wait_duration = 0.0
    fight_text = "* Sans is finally giving it his all."
    beam_flash_until = 0.0

def start_player_turn():
    global fight_phase, phase_started_at, fight_text
    global beam_flash_until
    fight_phase = PHASE_PLAYER
    phase_started_at = time.time()
    bullets.clear()
    gaster_blasters.clear()
    scheduled_events.clear()
    beam_flash_until = 0.0
    
    set_soul_mode("red")
    fight_text = "* What will you do?"

def start_sans_wait(msg):
    global fight_phase, phase_started_at, sans_wait_duration, fight_text
    global beam_flash_until
    fight_phase = PHASE_WAIT
    phase_started_at = time.time()
    sans_wait_duration = random.uniform(5.0, 10.0)
    fight_text = msg
    bullets.clear()
    gaster_blasters.clear()
    scheduled_events.clear()
    beam_flash_until = 0.0

def spawn_bullet(x, y, vx, vy, w, h, color, kind):
    fx, fy = float(x), float(y)
    bullets.append({
        "rect": pygame.Rect(int(fx), int(fy), int(w), int(h)),
        "fx": fx,
        "fy": fy,
        "vx": float(vx),
        "vy": float(vy),
        "color": color,
        "kind": kind,
    })

def spawn_gaster_blaster_custom(origin_x, origin_y, target_x, target_y):
    origin = pygame.Vector2(origin_x, origin_y)
    target = pygame.Vector2(target_x, target_y)
    direction = target - origin
    if direction.length_squared() < 1:
        direction = pygame.Vector2(1, 0)
    direction = direction.normalize()
    angle = math.degrees(math.atan2(direction.y, direction.x))
    now = time.time()
    # We want warmup relative to NOW
    gaster_blasters.append({
        "origin": origin,
        "direction": direction,
        "angle": angle,
        "warmup_end": now + BLASTER_WARMUP,
        "beam_end": now + BLASTER_WARMUP + BLASTER_BEAM_TIME,
        "beam_started": False,
    })

def spawn_targeted_blaster():
    side = random.choice(["left", "right", "top"])
    if side == "left":
        ox = box_x - 80
        oy = random.randint(box_y + 30, box_y + box_h - 30)
    elif side == "right":
        ox = box_x + box_w + 80
        oy = random.randint(box_y + 30, box_y + box_h - 30)
    else:
        ox = random.randint(box_x + 40, box_x + box_w - 40)
        oy = box_y - 65
    spawn_gaster_blaster_custom(ox, oy, soul_rect.centerx, soul_rect.centery)

def spawn_gaster_blaster_exact(x, y, dx, dy):
    spawn_gaster_blaster_custom(x, y, x + dx, y + dy)

# --- CLASSIC ATTACKS ---

def attack_opener():
    global SANS_ATTACK_DURATION
    SANS_ATTACK_DURATION = 8.5
    set_soul_mode("blue")
    
    # Wave 1 (Right to left)
    for i in range(20):
        schedule_event(0.5 + i*0.08, spawn_bullet, box_x + box_w + 10, box_y + box_h - 4 - 35, -6.5*UT_SPEED, 0, 12, 35, WHITE, "bone")
        
    # Wave 2 (Left to right, taller)
    for i in range(20):
        schedule_event(2.5 + i*0.08, spawn_bullet, box_x - 20, box_y + box_h - 4 - 55, 6.5*UT_SPEED, 0, 12, 55, WHITE, "bone")
        
    # 4 Blasters targeted rapidly
    schedule_event(4.8, spawn_targeted_blaster)
    schedule_event(5.2, spawn_targeted_blaster)
    schedule_event(5.6, spawn_targeted_blaster)
    schedule_event(6.0, spawn_targeted_blaster)

def attack_blue_hops():
    global SANS_ATTACK_DURATION
    SANS_ATTACK_DURATION = 8.0
    set_soul_mode("blue")
    
    times =   [0.5, 1.2, 1.9, 2.5, 3.1, 3.8, 4.4, 4.8, 5.2, 5.8]
    heights = [25,  25,  55,  25,  55,  25,  25,  25,  65,  25]
    
    for i in range(len(times)):
        t, h = times[i], heights[i]
        schedule_event(t, spawn_bullet, box_x + box_w + 10, box_y + box_h - 4 - h, -5.5*UT_SPEED, 0, 14, h, WHITE, "bone")

def attack_bone_gaps():
    global SANS_ATTACK_DURATION
    SANS_ATTACK_DURATION = 9.0
    set_soul_mode("red")
    
    vx = -5.0 * UT_SPEED
    gaps = [
        (0.5, box_y + 40),
        (1.5, box_y + 110),
        (2.5, box_y + 30),
        (3.5, box_y + 140),
        (4.5, box_y + 70),
        (5.5, box_y + 130),
        (6.5, box_y + 50)
    ]
    gap_h = 65
    for t, gy in gaps:
        # Top bone
        schedule_event(t, spawn_bullet, box_x + box_w, box_y + 4, vx, 0, 20, gy - (box_y + 4), WHITE, "bone")
        # Bottom bone
        bh = (box_y + box_h - 4) - (gy + gap_h)
        schedule_event(t, spawn_bullet, box_x + box_w, gy + gap_h, vx, 0, 20, bh, WHITE, "bone")

def attack_platforms():
    global SANS_ATTACK_DURATION
    SANS_ATTACK_DURATION = 8.5
    set_soul_mode("blue")
    
    # Bones completely covering the floor
    schedule_event(0.1, spawn_bullet, box_x + 5, box_y + box_h - 25, 0, 0, box_w - 10, 25, WHITE, "bone")
    
    plat_w, plat_h = 45, 8
    vx = 3.5 * UT_SPEED
    
    # Row 1 (low) moving right
    schedule_event(0.5, spawn_bullet, box_x - plat_w, box_y + 150, vx, 0, plat_w, plat_h, GREEN, "platform")
    schedule_event(3.5, spawn_bullet, box_x - plat_w, box_y + 150, vx, 0, plat_w, plat_h, GREEN, "platform")
    # Row 2 (mid) moving left
    schedule_event(2.0, spawn_bullet, box_x + box_w, box_y + 90, -vx, 0, plat_w, plat_h, GREEN, "platform")
    schedule_event(5.0, spawn_bullet, box_x + box_w, box_y + 90, -vx, 0, plat_w, plat_h, GREEN, "platform")
    # Row 3 (high) moving right
    schedule_event(1.5, spawn_bullet, box_x - plat_w, box_y + 30, vx, 0, plat_w, plat_h, GREEN, "platform")
    schedule_event(4.5, spawn_bullet, box_x - plat_w, box_y + 30, vx, 0, plat_w, plat_h, GREEN, "platform")

    # Blasters adding pressure to platforms
    schedule_event(4.0, spawn_gaster_blaster_exact, box_x - 50, box_y + 130, 1, 0)
    schedule_event(6.0, spawn_gaster_blaster_exact, box_x + box_w + 50, box_y + 70, -1, 0)

def attack_mixed_bones():
    global SANS_ATTACK_DURATION
    SANS_ATTACK_DURATION = 8.0
    set_soul_mode("blue")
    
    vx = -6.5 * UT_SPEED
    pattern = [
        (0.5, WHITE, 30),
        (1.5, BLUE,  70),
        (2.5, ORANGE, 30),
        (3.0, WHITE, 40),
        (4.0, BLUE,  80),
        (5.0, ORANGE, 35),
        (5.5, WHITE, 50),
        (6.5, BLUE,  90)
    ]
    for t, color, h in pattern:
        schedule_event(t, spawn_bullet, box_x + box_w + 10, box_y + box_h - 4 - h, vx, 0, 16, h, color, "bone")

def attack_blaster_circle():
    global SANS_ATTACK_DURATION
    SANS_ATTACK_DURATION = 7.0
    set_soul_mode("red")
    
    cx = box_x + box_w // 2
    cy = box_y + box_h // 2
    radius = 240
    num = 14
    
    for i in range(num):
        angle = i * (360 / num) + (i * 15)
        rad = math.radians(angle)
        bx = cx + math.cos(rad) * radius
        by = cy + math.sin(rad) * radius
        dx = cx - bx
        dy = cy - by
        schedule_event(0.5 + i*0.3, spawn_gaster_blaster_exact, bx, by, dx, dy)

attack_order = [
    attack_opener, 
    attack_blue_hops, 
    attack_bone_gaps, 
    attack_platforms, 
    attack_mixed_bones, 
    attack_blaster_circle
]

def start_sans_attack():
    global fight_phase, phase_started_at, fight_text, attack_index
    global beam_flash_until
    fight_phase = PHASE_ATTACK
    phase_started_at = time.time()
    fight_text = "* Sans attacks!"
    gaster_blasters.clear()
    bullets.clear()
    scheduled_events.clear()
    beam_flash_until = 0.0
    
    # Start sequence
    attack_func = attack_order[attack_index]
    attack_func()
    attack_index = (attack_index + 1) % len(attack_order)

def point_segment_distance(px, py, ax, ay, bx, by):
    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay
    ab_len2 = abx * abx + aby * aby
    if ab_len2 <= 0.0001:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab_len2))
    cx = ax + abx * t
    cy = ay + aby * t
    return math.hypot(px - cx, py - cy)

def update_gaster_blasters():
    global player_hp, karma, invuln_frames
    global beam_flash_until
    now = time.time()
    for blaster in gaster_blasters[:]:
        if now > blaster["beam_end"]:
            gaster_blasters.remove(blaster)
            continue

        if now >= blaster["warmup_end"]:
            if not blaster.get("beam_started"):
                blaster["beam_started"] = True
                beam_flash_until = max(beam_flash_until, now + BEAM_SCREEN_FLASH)
            start = blaster["origin"] + blaster["direction"] * 40
            end = start + blaster["direction"] * 1100
            cx, cy = soul_rect.center
            dist = point_segment_distance(cx, cy, start.x, start.y, end.x, end.y)
            # Collision against Blaster beams (roughly 11px radius around the 8x8 core center)
            if dist <= 11 and invuln_frames <= 0:
                player_hp -= BLASTER_DAMAGE
                karma = min(float(player_max_hp), karma + 12.0)
                invuln_frames = int(round(14 / UT_SPEED))

def update_bullets():
    for bullet in bullets[:]:
        bullet["fx"] += bullet["vx"]
        bullet["fy"] += bullet["vy"]
        bullet["rect"].x = int(bullet["fx"])
        bullet["rect"].y = int(bullet["fy"])

        off_left = bullet["rect"].right < box_x - 120
        off_right = bullet["rect"].left > box_x + box_w + 120
        off_top = bullet["rect"].bottom < box_y - 120
        off_bottom = bullet["rect"].top > box_y + box_h + 120
        if off_left or off_right or off_top or off_bottom:
            bullets.remove(bullet)

def check_damage(moved_this_frame):
    global player_hp, karma, invuln_frames

    if invuln_frames > 0:
        invuln_frames -= 1

    # In Undertale, the actual soul collision box is much smaller than the 16x16 sprite.
    # It's an 8x8 box right in the center. We use inflate(-8, -8) to achieve this forgiving feeling!
    core_hitbox = soul_rect.inflate(-8, -8)

    for bullet in bullets:
        if bullet["kind"] == "platform":
            continue
        if bullet["rect"].colliderect(core_hitbox):
            dmg = 0.0
            if bullet["color"] == WHITE: dmg = 1.0
            elif bullet["color"] == BLUE: dmg = 1.0 if moved_this_frame else 0.0
            elif bullet["color"] == ORANGE: dmg = 1.0 if not moved_this_frame else 0.0
            
            if dmg > 0 and invuln_frames <= 0:
                player_hp -= dmg
                karma = min(float(player_max_hp), karma + 8.0)
                invuln_frames = int(round(10 / UT_SPEED))

    # KR drains after hit, and slowly chips HP like the original feel.
    if karma > 0 and player_hp > 1:
        karma = max(0.0, karma - 0.35 * UT_SPEED)
        player_hp = max(0.0, player_hp - 0.08 * UT_SPEED)

    player_hp = max(0.0, min(float(player_max_hp), player_hp))

def draw_beam_flash_overlay():
    global beam_flash_until
    now = time.time()
    if now >= beam_flash_until:
        return
    t = max(0.0, min(1.0, (beam_flash_until - now) / BEAM_SCREEN_FLASH))
    alpha = int(110 * t)
    if alpha <= 0:
        return
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((180, 240, 255, alpha))
    screen.blit(overlay, (0, 0))

def draw_dialog_box(text):
    dialog = pygame.Rect(12, 430, 776, 86)
    pygame.draw.rect(screen, WHITE, dialog, 4)
    pygame.draw.rect(screen, BLACK, dialog.inflate(-8, -8))
    rendered = font_med.render(text, True, WHITE)
    screen.blit(rendered, (dialog.x + 16, dialog.y + 26))

def draw_status_and_menu():
    hp_ratio = player_hp / player_max_hp
    kr_ratio = karma / player_max_hp

    stats_y = 526
    screen.blit(font_small.render(player_name, True, WHITE), (16, stats_y))
    screen.blit(font_small.render(f"LV {player_lv}", True, WHITE), (117, stats_y))
    screen.blit(font_small.render("HP", True, WHITE), (204, stats_y))

    bar_x, bar_y, bar_w, bar_h = 243, stats_y + 4, 160, 16
    pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_w, bar_h))
    if hp_ratio > 0:
        pygame.draw.rect(screen, YELLOW, (bar_x, bar_y, int(bar_w * hp_ratio), bar_h))
    if kr_ratio > 0:
        pygame.draw.rect(screen, PURPLE, (bar_x, bar_y, int(bar_w * kr_ratio), bar_h), 2)

    hp_text = font_small.render(f"{int(player_hp):02d} / {player_max_hp}", True, WHITE)
    kr_text = font_small.render(f"KR {int(karma):02d} / {player_max_hp}", True, WHITE)
    screen.blit(hp_text, (410, stats_y))
    screen.blit(kr_text, (546, stats_y))

    if fight_phase == PHASE_PLAYER:
        turn_color, turn_text = YELLOW, "PLAYER TURN"
    elif fight_phase == PHASE_WAIT:
        turn_color, turn_text = WHITE, "SANS WAITING"
    else:
        turn_color, turn_text = BLUE, "SANS TURN"
    turn_label = font_small.render(turn_text, True, turn_color)
    screen.blit(turn_label, (640 - turn_label.get_width() // 2, stats_y))

    for index, action in enumerate(ACTION_LABELS):
        rect = pygame.Rect(
            MENU_BX + index * (MENU_BW + MENU_GAP),
            MENU_BY,
            MENU_BW,
            MENU_BH,
        )
        is_sel = (fight_phase == PHASE_PLAYER and index == selected_action)
        
        # Always draw procedurally pre-baked HUD button surfaces (no PNG HUD rendering).
        surf = fallback_buttons[action][1 if is_sel else 0]
        screen.blit(surf, rect.topleft)
        if is_sel:
            screen.blit(heart_red, (rect.x + 8, rect.y + 6))

def draw_sans():
    screen.blit(sans_sprite_scaled, sans_sprite_scaled.get_rect(center=(WIDTH // 2, 96)))

def draw_fight_scene():
    pygame.draw.rect(screen, WHITE, (box_x, box_y, box_w, box_h), 4)
    
    if soul_mode == "blue":
        screen.blit(heart_blue, soul_rect.topleft)
    else:
        screen.blit(heart_red, soul_rect.topleft)

    for bullet in bullets:
        color = bullet["color"]
        rect = bullet["rect"]
        surf = get_bullet_surface(rect.width, rect.height, color, bullet["kind"])
        screen.blit(surf, rect.topleft)

    draw_gaster_blasters()

def draw_gaster_blasters():
    now = time.time()
    for blaster in gaster_blasters:
        start = blaster["origin"] + blaster["direction"] * 40
        end = start + blaster["direction"] * 1100
        if now >= blaster["warmup_end"]:
            if now <= blaster["beam_end"]:
                pygame.draw.line(screen, (28, 28, 28), start, end, 24)
                pygame.draw.line(screen, WHITE, start, end, 16)
                pygame.draw.line(screen, (255, 255, 235), start, end, 7)
        else:
            t = max(0.0, min(1.0, (now - (blaster["warmup_end"] - BLASTER_WARMUP)) / BLASTER_WARMUP))
            width = max(1, int(2 + t * 4))
            pygame.draw.line(screen, (255, 255, 210), start, end, width)
            if blaster["warmup_end"] - now <= BLASTER_CHARGE_FLASH:
                flash = int(200 + 55 * math.sin(now * 80))
                pygame.draw.line(screen, (flash, flash, 255), start, end, width + 5)

        u_open, charge = blaster_open_and_charge(blaster, now)
        base = render_gaster_blaster_dynamic(u_open, charge)
        sprite = pygame.transform.rotozoom(base, -int(round(blaster["angle"])), 1.0)
        rect = sprite.get_rect(center=(int(blaster["origin"].x), int(blaster["origin"].y)))
        screen.blit(sprite, rect)

def draw_main_menu():
    title = font_title.render("AC'S UNDERTALE", True, YELLOW)
    subtitle = font_med.render("CLASSIC SANS FIGHT", True, WHITE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 188))
    screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 245))
    draw_dialog_box("* choose your route.")

    ticks = pygame.time.get_ticks()
    glow_index = (ticks // 70) % len(main_menu_glow_frames)
    bob = int(round(math.sin((2 * math.pi * ticks) / MAIN_MENU_PULSE_MS) * MAIN_MENU_SOUL_BOB_PX))

    for i, label in enumerate(MAIN_MENU_OPTIONS):
        x = WIDTH // 2 - MAIN_MENU_BW // 2
        y = MAIN_MENU_Y_START + i * (MAIN_MENU_BH + MAIN_MENU_GAP)
        if i == main_menu_selected:
            screen.blit(main_menu_glow_frames[glow_index], (x - 10, y - 10))
            screen.blit(main_menu_button_selected[i], (x, y))
        else:
            screen.blit(main_menu_button_idle[i], (x, y))
        if i == main_menu_selected:
            # Main menu soul cursor alignment
            screen.blit(heart_red, (x + 10, y + (MAIN_MENU_BH // 2 - 8) + bob))

    hint = font_small.render("Z/ENTER: SELECT    W/S OR UP/DOWN: MOVE", True, WHITE)
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 387))

running = True
reset_run_state()
init_baked_ost()

while running:
    clock.tick(DISPLAY_FPS)
    screen.fill(BLACK)
    keys = pygame.key.get_pressed()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if game_state == STATE_INTRO:
                if event.key in (pygame.K_UP, pygame.K_w):
                    main_menu_selected = (main_menu_selected - 1) % len(MAIN_MENU_OPTIONS)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    main_menu_selected = (main_menu_selected + 1) % len(MAIN_MENU_OPTIONS)
                elif event.key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
                    if MAIN_MENU_OPTIONS[main_menu_selected] == "START":
                        game_state = STATE_DIALOGUE
                    else:
                        running = False
            elif game_state == STATE_DIALOGUE and event.key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
                dialogue_index += 1
                if dialogue_index >= len(dialogue_lines):
                    game_state = STATE_FIGHT
                    start_player_turn()
            elif game_state == STATE_FIGHT and fight_phase == PHASE_PLAYER:
                if event.key == pygame.K_LEFT:
                    selected_action = (selected_action - 1) % len(ACTION_LABELS)
                elif event.key == pygame.K_RIGHT:
                    selected_action = (selected_action + 1) % len(ACTION_LABELS)
                elif event.key in (pygame.K_z, pygame.K_RETURN, pygame.K_SPACE):
                    action = ACTION_LABELS[selected_action]
                    if action == "FIGHT":
                        start_sans_wait("* You attack. Sans sidesteps.")
                    elif action == "ACT":
                        start_sans_wait("* You ACT. Sans smirks.")
                    elif action == "ITEM":
                        healed = min(12, player_max_hp - player_hp)
                        player_hp += healed
                        start_sans_wait(f"* You used an item. +{int(healed)} HP.")
                    elif action == "MERCY":
                        start_sans_wait("* You showed mercy. Sans refuses.")
            elif game_state == STATE_GAME_OVER and event.key == pygame.K_r:
                reset_run_state()

    if game_state == STATE_FIGHT:
        now = time.time()
        
        if fight_phase == PHASE_WAIT:
            remaining = max(0, int(round(sans_wait_duration - (now - phase_started_at))))
            fight_text = f"* Sans waits... {remaining}s"
            if now - phase_started_at >= sans_wait_duration:
                start_sans_attack()

        elif fight_phase == PHASE_ATTACK:
            old_x, old_y = soul_x, soul_y
            
            # Update objects before checking collisions
            update_bullets()
            
            # Physics & Input update
            if soul_mode == "red":
                if keys[pygame.K_LEFT]: soul_x -= soul_speed
                if keys[pygame.K_RIGHT]: soul_x += soul_speed
                if keys[pygame.K_UP]: soul_y -= soul_speed
                if keys[pygame.K_DOWN]: soul_y += soul_speed
            elif soul_mode == "blue":
                if keys[pygame.K_LEFT]: soul_x -= soul_speed
                if keys[pygame.K_RIGHT]: soul_x += soul_speed
                
                soul_vy += GRAVITY
                if soul_vy > MAX_FALL_SPEED: soul_vy = MAX_FALL_SPEED
                
                if is_grounded and keys[pygame.K_UP]:
                    soul_vy = JUMP_POWER
                    is_grounded = False
                    
                if not keys[pygame.K_UP] and soul_vy < -2.0:
                    soul_vy *= 0.6  # Variable jump
                    
                soul_y += soul_vy

            # Clamp Box Width
            if soul_x < box_x + 5: soul_x = box_x + 5
            if soul_x > box_x + box_w - soul_size - 5: soul_x = box_x + box_w - soul_size - 5

            # Platform Collision (Top Down)
            platform_grounded = False
            platform_vx = 0.0
            soul_rect.x, soul_rect.y = int(soul_x), int(soul_y) # sync for platform check
            if soul_mode == "blue":
                for bullet in bullets:
                    if bullet["kind"] == "platform":
                        plat = bullet["rect"]
                        if soul_vy >= 0 and old_y + soul_size <= plat.top + max(5, soul_vy + 1):
                            if soul_rect.right > plat.left and soul_rect.left < plat.right:
                                if soul_rect.bottom >= plat.top and soul_rect.bottom <= plat.bottom + 10:
                                    soul_y = plat.top - soul_size
                                    soul_vy = 0
                                    is_grounded = True
                                    platform_grounded = True
                                    platform_vx = bullet["vx"]
                                    break
            
            if platform_grounded:
                soul_x += platform_vx

            # Clamp Box Height
            is_grounded = platform_grounded
            if soul_y > box_y + box_h - soul_size - 5:
                soul_y = box_y + box_h - soul_size - 5
                soul_vy = 0
                is_grounded = True
            elif soul_y < box_y + 5:
                soul_y = box_y + 5
                soul_vy = 0
                
            soul_rect.x, soul_rect.y = int(soul_x), int(soul_y)
            moved_this_frame = (soul_x != old_x or soul_y != old_y)
            
            # Core Attack Updates
            check_damage(moved_this_frame)
            update_gaster_blasters()

            # Execute scheduled events
            elapsed = now - phase_started_at
            for ev in scheduled_events:
                if not ev["fired"] and elapsed >= ev["trigger_time"]:
                    ev["func"](*ev["args"])
                    ev["fired"] = True

            if elapsed >= SANS_ATTACK_DURATION:
                start_player_turn()

        if player_hp <= 0:
            game_state = STATE_GAME_OVER

    if game_state == STATE_INTRO:
        draw_main_menu()

    elif game_state == STATE_DIALOGUE:
        draw_sans()
        draw_dialog_box("* " + dialogue_lines[dialogue_index])
        draw_status_and_menu()

    elif game_state == STATE_FIGHT:
        draw_sans()
        draw_fight_scene()
        draw_beam_flash_overlay()
        draw_dialog_box(fight_text)
        draw_status_and_menu()

    elif game_state == STATE_GAME_OVER:
        draw_sans()
        over = font_title.render("YOU DIED", True, RED)
        retry = font_med.render("Press R to reset timeline", True, WHITE)
        screen.blit(over, (WIDTH // 2 - over.get_width() // 2, 250))
        screen.blit(retry, (WIDTH // 2 - retry.get_width() // 2, 320))

    pygame.display.flip()

pygame.quit()
sys.exit()
