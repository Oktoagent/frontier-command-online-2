"""Place the transparent renders on a calm background and add a soft glow to emissive accents."""
import glob, os, sys
import numpy as np
from PIL import Image, ImageFilter

TOP, BOTTOM, HALO = np.array([0x38, 0x44, 0x58]), np.array([0x22, 0x2A, 0x38]), np.array([0x4C, 0x5A, 0x72])


def background(w, h, cx=0.5, cy=0.52, halo=0.42):
    y = np.linspace(0, 1, h)[:, None, None]
    bg = TOP * (1 - y) + BOTTOM * y
    xx, yy = np.meshgrid(np.linspace(0, 1, w), np.linspace(0, 1, h))
    asp = w / h
    r = np.sqrt(((xx - cx) * asp) ** 2 + (yy - cy) ** 2)
    g = np.clip(1 - r / halo, 0, 1)[..., None] ** 2 * 0.55
    bg = bg * (1 - g) + HALO * g
    return bg


def bloom(rgb, alpha, radius):
    hsv = np.array(Image.fromarray(rgb.astype(np.uint8)).convert('HSV')).astype(np.float32) / 255
    m = np.clip((hsv[..., 2] - 0.78) / 0.22, 0, 1) * np.clip((hsv[..., 1] - 0.3) / 0.3, 0, 1) * (alpha > 0.5)
    glow = rgb * m[..., None]
    gi = Image.fromarray(np.clip(glow, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(gi).astype(np.float32)


def compose(src, dst, halo=0.42, grid=None):
    im = np.asarray(Image.open(src).convert('RGBA')).astype(np.float32)
    h, w = im.shape[:2]
    rgb, a = im[..., :3], im[..., 3:] / 255
    if grid:
        bg = np.zeros_like(rgb)
        cols, rows = grid
        bg[:] = background(w, h, 0.5, 0.5, 2.0)
        for r in range(rows):
            for c in range(cols):
                cx, cy = (c + 0.5) / cols, (r + 0.5) / rows
                bg = np.maximum(bg, background(w, h, cx, cy, 0.42 / cols * (w / h) ** 0 * 1.0))
    else:
        bg = background(w, h, halo=halo)
    out = rgb * a + bg * (1 - a)
    out += bloom(rgb, a[..., 0], max(4, w // 110)) * 0.55
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst, quality=93)


if __name__ == '__main__':
    src_dir, dst_dir = sys.argv[1], sys.argv[2]
    os.makedirs(dst_dir, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src_dir, '*.png'))):
        name = os.path.splitext(os.path.basename(f))[0]
        if name.startswith('00_'):
            compose(f, os.path.join(dst_dir, name + '.jpg'), grid=(5, 2))
        else:
            compose(f, os.path.join(dst_dir, name + '.jpg'))
        print('composed', name)
