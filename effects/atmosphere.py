"""Atmospheric post-processing: smoke glow, god rays, chromatic aberration,
film grain, heat distortion, and color grading."""

from dataclasses import dataclass
import numpy as np


@dataclass
class AtmosphereConfig:
    """Configuration for atmospheric post-processing effects."""
    # Smoke glow — Perlin-noise-modulated multi-radius bloom
    smoke_glow: bool = False
    smoke_intensity: float = 0.4
    smoke_scale: float = 8.0       # noise scale (lower = larger patches)

    # God rays — radial light scattering from center
    god_rays: bool = False
    god_rays_intensity: float = 0.5
    god_rays_samples: int = 48
    god_rays_decay: float = 0.95

    # Chromatic aberration — radial RGB channel offset
    chromatic_aberration: bool = False
    chromatic_strength: float = 3.0

    # Film grain
    film_grain: bool = False
    grain_intensity: float = 0.08
    grain_size: float = 1.5

    # Heat distortion — sine-wave displacement
    heat_distortion: bool = False
    heat_amplitude: float = 3.0
    heat_frequency: float = 0.02

    # Color grading — split toning + contrast/saturation
    color_grading: bool = False
    shadow_tint_r: int = 0
    shadow_tint_g: int = 0
    shadow_tint_b: int = 10
    highlight_tint_r: int = 10
    highlight_tint_g: int = 5
    highlight_tint_b: int = 0
    grade_contrast: float = 1.0
    grade_saturation: float = 1.0

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "AtmosphereConfig":
        fields = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in fields})

    @property
    def has_any(self) -> bool:
        return (self.smoke_glow or self.god_rays or self.chromatic_aberration
                or self.film_grain or self.heat_distortion or self.color_grading)


def apply_atmosphere(arr: np.ndarray, config: AtmosphereConfig) -> np.ndarray:
    """Apply the full atmospheric effect chain."""
    if not config.has_any:
        return arr

    if config.heat_distortion:
        arr = apply_heat_distortion(arr, config.heat_amplitude, config.heat_frequency)
    if config.smoke_glow:
        arr = apply_smoke_glow(arr, config.smoke_intensity, config.smoke_scale)
    if config.god_rays:
        arr = apply_god_rays(arr, config.god_rays_intensity,
                             config.god_rays_samples, config.god_rays_decay)
    if config.chromatic_aberration:
        arr = apply_chromatic_aberration(arr, config.chromatic_strength)
    if config.color_grading:
        arr = apply_color_grading(
            arr,
            (config.shadow_tint_b, config.shadow_tint_g, config.shadow_tint_r),
            (config.highlight_tint_b, config.highlight_tint_g, config.highlight_tint_r),
            config.grade_contrast, config.grade_saturation,
        )
    if config.film_grain:
        arr = apply_film_grain(arr, config.grain_intensity, config.grain_size)

    return arr


# --- Individual effects ---

def _generate_noise_2d(h: int, w: int, scale: float) -> np.ndarray:
    """Generate a simple multi-octave value noise field (0-1 range).

    Uses numpy random + interpolation as a lightweight Perlin alternative.
    """
    # Generate at low resolution then upscale for smooth noise
    sh = max(4, int(h / scale))
    sw = max(4, int(w / scale))
    base = np.random.RandomState(42).rand(sh, sw).astype(np.float32)

    # Smooth upscale via bilinear interpolation
    from scipy.ndimage import zoom
    noise = zoom(base, (h / sh, w / sw), order=1)[:h, :w]

    # Add a finer octave for detail
    sh2, sw2 = sh * 2, sw * 2
    fine = np.random.RandomState(123).rand(sh2, sw2).astype(np.float32)
    fine = zoom(fine, (h / sh2, w / sw2), order=1)[:h, :w]

    return np.clip(0.6 * noise + 0.4 * fine, 0, 1)


def apply_smoke_glow(arr: np.ndarray, intensity: float = 0.4,
                     scale: float = 8.0) -> np.ndarray:
    """Multi-radius bloom modulated by noise for smoke-like scattering."""
    h, w = arr.shape[:2]
    noise = _generate_noise_2d(h, w, scale)

    try:
        from scipy.ndimage import gaussian_filter
    except ImportError:
        return arr

    result = arr.astype(np.float32)

    # Multiple bloom radii for volumetric feel
    for sigma, weight in [(4, 0.4), (12, 0.3), (30, 0.2), (60, 0.1)]:
        blurred = np.empty_like(result)
        for c in range(3):
            blurred[:, :, c] = gaussian_filter(result[:, :, c], sigma=sigma)
        blurred[:, :, 3] = arr[:, :, 3]

        # Modulate by noise — creates irregular smoke density
        mod = (0.3 + 0.7 * noise)[:, :, np.newaxis]
        result[:, :, :3] += blurred[:, :, :3] * weight * intensity * mod[:, :, :1].repeat(3, axis=2)

    return np.clip(result, 0, 255).astype(np.uint8)


def apply_god_rays(arr: np.ndarray, intensity: float = 0.5,
                   num_samples: int = 48, decay: float = 0.95) -> np.ndarray:
    """Radial light scattering from image center (screen-space god rays)."""
    h, w = arr.shape[:2]

    # Work at reduced resolution for performance
    scale = 4
    sh, sw = h // scale, w // scale
    from scipy.ndimage import zoom as sz
    small = sz(arr[:, :, :3].astype(np.float32), (sh / h, sw / w, 1), order=1)

    # Light source at center
    cy, cx = 0.5, 0.5
    yy, xx = np.mgrid[0:sh, 0:sw]
    uy = yy / sh
    ux = xx / sw

    dy = (uy - cy) / num_samples
    dx = (ux - cx) / num_samples

    result = np.zeros((sh, sw, 3), dtype=np.float64)
    coord_y = uy.astype(np.float64)
    coord_x = ux.astype(np.float64)
    illum_decay = 1.0

    for _ in range(num_samples):
        coord_y -= dy
        coord_x -= dx
        sy = np.clip((coord_y * sh).astype(int), 0, sh - 1)
        sx = np.clip((coord_x * sw).astype(int), 0, sw - 1)
        sample = small[sy, sx].astype(np.float64)
        result += sample * illum_decay * 0.02
        illum_decay *= decay

    # Upscale back
    rays = sz(result, (h / sh, w / sw, 1), order=1)[:h, :w]

    out = arr.astype(np.float32)
    out[:, :, :3] += (rays * intensity).astype(np.float32)
    return np.clip(out, 0, 255).astype(np.uint8)


def apply_chromatic_aberration(arr: np.ndarray, strength: float = 3.0) -> np.ndarray:
    """Radial RGB channel separation mimicking lens chromatic aberration."""
    try:
        from scipy.ndimage import map_coordinates
    except ImportError:
        return arr

    h, w = arr.shape[:2]
    cy, cx = h / 2.0, w / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    result = arr.copy()
    # BGRA order: 0=B, 1=G, 2=R
    # Red pushes outward, blue pulls inward
    for ch_idx, s in [(2, strength * 0.001), (0, -strength * 0.001)]:
        scale = 1.0 + s
        src_y = cy + (yy - cy) / scale
        src_x = cx + (xx - cx) / scale
        result[:, :, ch_idx] = map_coordinates(
            arr[:, :, ch_idx].astype(np.float32),
            [src_y, src_x], order=1, mode='nearest'
        ).astype(np.uint8)

    return result


def apply_film_grain(arr: np.ndarray, intensity: float = 0.08,
                     grain_size: float = 1.5) -> np.ndarray:
    """Luminance-dependent photographic film grain."""
    h, w = arr.shape[:2]

    # Generate grain at reduced resolution for natural clumping
    sh = max(4, int(h / grain_size))
    sw = max(4, int(w / grain_size))
    noise = np.random.normal(0, 1, (sh, sw)).astype(np.float32)

    from scipy.ndimage import zoom
    noise = zoom(noise, (h / sh, w / sw), order=1)[:h, :w]

    # More visible in midtones (like real film)
    lum = arr[:, :, :3].astype(np.float32).mean(axis=2) / 255.0
    midtone_weight = 4.0 * lum * (1.0 - lum)

    grain = noise * intensity * 255.0 * midtone_weight

    result = arr.astype(np.float32)
    result[:, :, :3] += grain[:, :, np.newaxis]
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_heat_distortion(arr: np.ndarray, amplitude: float = 3.0,
                          frequency: float = 0.02) -> np.ndarray:
    """Sine-wave pixel displacement for atmospheric shimmer."""
    try:
        from scipy.ndimage import map_coordinates
    except ImportError:
        return arr

    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    dx = amplitude * np.sin(yy * frequency * 2 * np.pi)
    dy = amplitude * np.sin(xx * frequency * 2 * np.pi * 0.7)

    result = arr.copy()
    for c in range(3):
        result[:, :, c] = map_coordinates(
            arr[:, :, c].astype(np.float32),
            [yy + dy, xx + dx], order=1, mode='reflect'
        ).astype(np.uint8)
    return result


def apply_color_grading(arr: np.ndarray, shadow_tint=(0, 0, 10),
                        highlight_tint=(10, 5, 0),
                        contrast: float = 1.0,
                        saturation: float = 1.0) -> np.ndarray:
    """Split-toning color grading with contrast and saturation."""
    img = arr[:, :, :3].astype(np.float32)
    lum = img.mean(axis=2, keepdims=True)

    # Contrast around midpoint
    if abs(contrast - 1.0) > 0.01:
        img = (img - 128) * contrast + 128

    # Saturation
    if abs(saturation - 1.0) > 0.01:
        img = lum + (img - lum) * saturation

    # Split toning
    lum_norm = lum / 255.0
    shadow_mask = 1.0 - lum_norm
    highlight_mask = lum_norm
    for c in range(3):
        img[:, :, c] += shadow_tint[c] * shadow_mask[:, :, 0]
        img[:, :, c] += highlight_tint[c] * highlight_mask[:, :, 0]

    out = arr.copy()
    out[:, :, :3] = np.clip(img, 0, 255).astype(np.uint8)
    return out
