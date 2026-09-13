#!/usr/bin/env python3
"""
Generate realistic sample images for Clairvoy UI screenshots and demos.
Creates genuine duplicate and near-duplicate pairs (same visual scene with burst variations or compression).
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "assets" / "sample_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def draw_sky_gradient(draw: ImageDraw.ImageDraw, width: int, height: int, top_color: tuple, bot_color: tuple):
    for y in range(height):
        t = y / max(1, height)
        r = int(top_color[0] * (1 - t) + bot_color[0] * t)
        g = int(top_color[1] * (1 - t) + bot_color[1] * t)
        b = int(top_color[2] * (1 - t) + bot_color[2] * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def create_yosemite_mountain_scene(width: int = 1920, height: int = 1080) -> Image.Image:
    """Creates a high-res dramatic mountain landscape at sunrise."""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # 1. Sunrise sky gradient (deep twilight indigo -> warm amber gold)
    draw_sky_gradient(draw, width, int(height * 0.65), (20, 24, 54), (245, 140, 60))

    # 2. Glowing morning sun
    sun_x, sun_y = int(width * 0.68), int(height * 0.42)
    for r in range(120, 0, -5):
        color = (255, 235, 180)
        draw.ellipse([sun_x - r, sun_y - r, sun_x + r, sun_y + r], fill=color)

    # 3. Background mountain ridges (distant purple-slate)
    bg_points = [(0, int(height * 0.58))]
    for x in range(0, width + 50, 40):
        y = int(height * 0.45 + math.sin(x * 0.005) * 60 + math.cos(x * 0.015) * 35)
        bg_points.append((x, y))
    bg_points.extend([(width, height), (0, height)])
    draw.polygon(bg_points, fill=(65, 55, 95))

    # 4. Midground jagged mountain peaks (sharp dark slate with snow highlight)
    mid_points = [(0, int(height * 0.62))]
    peaks = [
        (0.15, 0.32), (0.28, 0.45), (0.42, 0.28),
        (0.58, 0.38), (0.72, 0.25), (0.88, 0.48), (1.0, 0.35),
    ]
    for px_ratio, py_ratio in peaks:
        target_x = int(width * px_ratio)
        target_y = int(height * py_ratio)
        mid_points.append((target_x, target_y))
    mid_points.extend([(width, height), (0, height)])
    draw.polygon(mid_points, fill=(35, 38, 55))

    # Add snowcaps on highest peaks
    for px_ratio, py_ratio in [(0.42, 0.28), (0.72, 0.25)]:
        cx, cy = int(width * px_ratio), int(height * py_ratio)
        draw.polygon([(cx, cy), (cx - 45, cy + 80), (cx + 40, cy + 70)], fill=(230, 235, 245))

    # 5. Foreground evergreen ridge & reflective alpine lake
    water_y = int(height * 0.72)
    # Lake water gradient
    for y in range(water_y, height):
        t = (y - water_y) / (height - water_y)
        r = int(25 * (1 - t) + 10 * t)
        g = int(45 * (1 - t) + 20 * t)
        b = int(70 * (1 - t) + 35 * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Foreground dark pine tree silhouettes on bank
    fg_bank = [(0, int(height * 0.78))]
    for x in range(0, int(width * 0.45), 25):
        bank_y = int(height * 0.74 + math.sin(x * 0.02) * 20)
        fg_bank.append((x, bank_y))
    fg_bank.extend([(int(width * 0.45), height), (0, height)])
    draw.polygon(fg_bank, fill=(15, 20, 28))

    return img


def create_golden_gate_scene(width: int = 1920, height: int = 1080) -> Image.Image:
    """Creates a coastal suspension bridge sunset scene."""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # 1. Sunset sky (deep crimson/magenta -> warm amber orange)
    draw_sky_gradient(draw, width, int(height * 0.70), (45, 15, 50), (250, 120, 45))

    # 2. Glowing low sun
    sun_x, sun_y = int(width * 0.35), int(height * 0.55)
    for r in range(140, 0, -6):
        draw.ellipse([sun_x - r, sun_y - r, sun_x + r, sun_y + r], fill=(255, 220, 140))

    # 3. Distant headlands / coastal hills
    hill_points = [(0, int(height * 0.65))]
    for x in range(0, width + 50, 50):
        y = int(height * 0.58 + math.sin(x * 0.006) * 45)
        hill_points.append((x, y))
    hill_points.extend([(width, height), (0, height)])
    draw.polygon(hill_points, fill=(60, 30, 40))

    # 4. Ocean bay water
    water_y = int(height * 0.68)
    for y in range(water_y, height):
        t = (y - water_y) / (height - water_y)
        draw.line([(0, y), (width, y)], fill=(int(20 * (1 - t) + 8 * t), int(35 * (1 - t) + 15 * t), int(55 * (1 - t) + 25 * t)))

    # 5. Iconic International Orange Suspension Bridge Towers & Cables
    tower_x1 = int(width * 0.48)
    tower_x2 = int(width * 0.82)
    deck_y = int(height * 0.66)
    bridge_color = (215, 65, 45)

    # Deck road line
    draw.rectangle([0, deck_y, width, deck_y + 14], fill=(40, 40, 45))
    draw.line([(0, deck_y + 1), (width, deck_y + 1)], fill=bridge_color, width=3)

    # Towers
    for tx in [tower_x1, tower_x2]:
        # Tower legs
        draw.rectangle([tx - 22, int(height * 0.22), tx - 6, deck_y + 40], fill=bridge_color)
        draw.rectangle([tx + 6, int(height * 0.22), tx + 22, deck_y + 40], fill=bridge_color)
        # Cross struts
        for sy in range(int(height * 0.28), deck_y, int(height * 0.09)):
            draw.rectangle([tx - 22, sy, tx + 22, sy + 10], fill=bridge_color)

    # Main suspension cables (catenary parabola)
    cables = []
    for x in range(0, width, 5):
        if x < tower_x1:
            norm = (x - tower_x1) / tower_x1
            y = int(height * 0.22 + (norm ** 2) * (deck_y - height * 0.22))
        elif x <= tower_x2:
            mid = (tower_x1 + tower_x2) / 2
            span = (tower_x2 - tower_x1) / 2
            norm = (x - mid) / span
            y = int(deck_y - 20 - (1 - norm ** 2) * (deck_y - height * 0.22 - 30))
        else:
            norm = (x - tower_x2) / (width - tower_x2)
            y = int(height * 0.22 + (norm ** 2) * (deck_y - height * 0.22))
        cables.append((x, y))
    draw.line(cables, fill=bridge_color, width=4)

    return img


def main():
    print(f"Generating realistic sample photos in {OUTPUT_DIR}...")

    # --- Group 1: Yosemite Valley Sunrise (Exact Byte Duplicate & Recompression) ---
    img1_master = create_yosemite_mountain_scene(1920, 1080)
    p1_master = OUTPUT_DIR / "Yosemite_Sunrise_4K.jpg"
    img1_master.save(p1_master, quality=95)

    # Exact duplicate (different folder / filename)
    p1_exact_copy = OUTPUT_DIR / "Yosemite_Sunrise_4K (1).jpg"
    img1_master.save(p1_exact_copy, quality=95)

    # Near-duplicate 720p transcode (same scene, compressed resolution)
    img1_720p = img1_master.resize((1280, 720), Image.Resampling.LANCZOS)
    p1_720p = OUTPUT_DIR / "Yosemite_Sunrise_720p_web.jpg"
    img1_720p.save(p1_720p, quality=82)

    # --- Group 2: Golden Gate Sunset (Burst Shot Variation & Color Grade) ---
    img2_burst1 = create_golden_gate_scene(1920, 1080)
    p2_burst1 = OUTPUT_DIR / "GoldenGate_Sunset_Burst_01.jpg"
    img2_burst1.save(p2_burst1, quality=95)

    # Burst shot 2: Slight camera shift & exposure variation
    # Crop slightly and re-center to simulate burst movement
    w, h = img2_burst1.size
    crop_box = (15, 8, w - 10, h - 15)
    img2_burst2 = img2_burst1.crop(crop_box).resize((w, h), Image.Resampling.LANCZOS)
    # Slight exposure boost
    enhancer = ImageEnhance.Brightness(img2_burst2)
    img2_burst2 = enhancer.enhance(1.04)
    p2_burst2 = OUTPUT_DIR / "GoldenGate_Sunset_Burst_02.jpg"
    img2_burst2.save(p2_burst2, quality=92)

    print(f"✓ Created {p1_master.name} and {p1_exact_copy.name} (Exact Duplicate)")
    print(f"✓ Created {p1_720p.name} (4K vs 720p Transcode)")
    print(f"✓ Created {p2_burst1.name} and {p2_burst2.name} (Burst Mode Near-Duplicates)")


if __name__ == "__main__":
    main()
