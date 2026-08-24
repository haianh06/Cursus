"""Generate the extension icons without Pillow: hand-rolled RGBA PNG writer.

Design: dark rounded square (matches the popup chrome) with an amber upload
arrow — the extension's whole job is pushing prompts up to the server.
"""
import struct
import sys
import zlib
from pathlib import Path

BG = (30, 33, 40)        # --panel
FG = (217, 119, 6)       # --accent
SS = 3                   # supersampling factor per axis


def inside_rounded_rect(x, y, r):
    """x, y, r in 0..1 normalized space."""
    if r <= 0:
        return 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0
    cx = min(max(x, r), 1 - r)
    cy = min(max(y, r), 1 - r)
    dx, dy = x - cx, y - cy
    return dx * dx + dy * dy <= r * r


def inside_arrow(x, y):
    # stem
    if 0.435 <= x <= 0.565 and 0.44 <= y <= 0.78:
        return True
    # head: widens from the tip at y=0.22 down to y=0.47
    if 0.22 <= y <= 0.47:
        t = (y - 0.22) / (0.47 - 0.22)
        if abs(x - 0.5) <= 0.215 * t:
            return True
    return False


def render(size):
    radius = 0.22
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            r = g = b = a = 0.0
            for sy in range(SS):
                for sx in range(SS):
                    x = (px + (sx + 0.5) / SS) / size
                    y = (py + (sy + 0.5) / SS) / size
                    if not inside_rounded_rect(x, y, radius):
                        continue
                    col = FG if inside_arrow(x, y) else BG
                    r += col[0]
                    g += col[1]
                    b += col[2]
                    a += 255.0
            n = SS * SS
            if a == 0:
                row += bytes((0, 0, 0, 0))
            else:
                # un-premultiply: average colour over covered samples only
                cov = a / 255.0
                row += bytes((
                    int(round(r / cov)),
                    int(round(g / cov)),
                    int(round(b / cov)),
                    int(round(a / n)),
                ))
        rows.append(bytes(row))
    return rows


def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path, size):
    rows = render(size)
    raw = b"".join(b"\x00" + r for r in rows)  # filter type 0 per scanline
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)
    return len(png)


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for size in (16, 32, 48, 128):
        p = out / f"icon{size}.png"
        n = write_png(p, size)
        print(f"  {p.name:14} {size}x{size}  {n} bytes")


if __name__ == "__main__":
    main()
