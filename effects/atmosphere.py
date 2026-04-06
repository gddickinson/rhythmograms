"""Atmospheric post-processing: smoke glow, god rays, chromatic aberration,
film grain, heat distortion, and color grading.

Performance-optimized with aggressive caching of noise fields, vignette masks,
coordinate grids, and pre-computed decay tables. Most expensive operations
are computed once and reused across frames.
"""

from dataclasses import dataclass
import numpy as np

# Module-level caches — persist across frames, invalidated on resolution change
_cache = {}


def _get_cached(key, compute_fn):
    """Get or compute a cached value."""
    if key not in _cache:
        _cache[key] = compute_fn()
    return _cache[key]


def clear_cache():
    """Clear all caches (call on resize)."""
    _cache.clear()


@dataclass
class AtmosphereConfig:
    """Configuration for atmospheric post-processing effects."""
    smoke_glow: bool = False
    smoke_intensity: float = 0.4
    smoke_scale: float = 8.0

    god_rays: bool = False
    god_rays_intensity: float = 0.5
    god_rays_samples: int = 24      # reduced from 48
    god_rays_decay: float = 0.95

    chromatic_aberration: bool = False
    chromatic_strength: float = 3.0

    film_grain: bool = False
    grain_intensity: float = 0.08
    grain_size: float = 1.5

    heat_distortion: bool = False
    heat_amplitude: float = 3.0
    heat_frequency: float = 0.02

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
    """Apply the full atmospheric effect chain. Optimized with caching."""
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


# --- Cached noise generation ---

def _get_noise(h: int, w: int, scale: float) -> np.ndarray:
    """Get cached noise field. Computed once per resolution+scale combo."""
    def compute():
        sh = max(4, int(h / scale))
        sw = max(4, int(w / scale))
        from scipy.ndimage import zoom
        base = np.random.RandomState(42).rand(sh, sw).astype(np.float32)
        noise = zoom(base, (h / sh, w / sw), order=1)[:h, :w]
        fine = np.random.RandomState(123).rand(sh * 2, sw * 2).astype(np.float32)
        fine = zoom(fine, (h / (sh * 2), w / (sw * 2)), order=1)[:h, :w]
        return np.clip(0.6 * noise + 0.4 * fine, 0, 1)

    return _get_cached(("noise", h, w, scale), compute)


def _get_grain(h: int, w: int, grain_size: float) -> np.ndarray:
    """Get cached film grain noise. Computed once per resolution+size combo."""
    def compute():
        sh = max(4, int(h / grain_size))
        sw = max(4, int(w / grain_size))
        noise = np.random.RandomState(77).normal(0, 1, (sh, sw)).astype(np.float32)
        from scipy.ndimage import zoom
        return zoom(noise, (h / sh, w / sw), order=1)[:h, :w]

    return _get_cached(("grain", h, w, grain_size), compute)


def _get_coord_grid(h: int, w: int):
    """Get cached coordinate grid."""
    def compute():
        return np.mgrid[0:h, 0:w].astype(np.float32)

    return _get_cached(("grid", h, w), compute)


def _get_vignette_dist(h: int, w: int):
    """Get cached radial distance field for vignette/god rays."""
    def compute():
        cy, cx = h / 2.0, w / 2.0
        y = np.arange(h, dtype=np.float32) - cy
        x = np.arange(w, dtype=np.float32) - cx
        yy, xx = np.meshgrid(y, x, indexing='ij')
        max_dist = np.sqrt(cx * cx + cy * cy)
        return np.sqrt(xx * xx + yy * yy) / max_dist

    return _get_cached(("vdist", h, w), compute)


# --- Individual effects (optimized) ---

def _fast_blur_rgb(rgb: np.ndarray, radius: int) -> np.ndarray:
    """Fast box blur via uniform_filter. O(n) regardless of radius."""
    from scipy.ndimage import uniform_filter
    result = rgb.astype(np.float32)
    ks = 2 * radius + 1
    for c in range(result.shape[2]):
        result[:, :, c] = uniform_filter(result[:, :, c], size=ks, mode='nearest')
    # Second pass for smoother Gaussian approximation
    for c in range(result.shape[2]):
        result[:, :, c] = uniform_filter(result[:, :, c], size=ks, mode='nearest')
    return result


def apply_smoke_glow(arr: np.ndarray, intensity: float = 0.4,
                     scale: float = 8.0) -> np.ndarray:
    """Multi-radius bloom modulated by cached noise for smoke-like scattering.

    Uses fast box blur (cumsum-based, O(n) regardless of radius) instead of
    Gaussian filter for 5-10x speedup on large radii.
    """
    h, w = arr.shape[:2]
    noise = _get_noise(h, w, scale)
    mod = (0.3 + 0.7 * noise)[:, :, np.newaxis]

    result = arr.astype(np.float32)
    rgb = result[:, :, :3]

    for radius, weight in [(3, 0.4), (8, 0.3), (20, 0.2), (40, 0.1)]:
        blurred = _fast_blur_rgb(rgb, radius)[:h, :w]
        result[:, :, :3] += blurred * (weight * intensity) * mod

    return np.clip(result, 0, 255).astype(np.uint8)


def apply_god_rays(arr: np.ndarray, intensity: float = 0.5,
                   num_samples: int = 24, decay: float = 0.95) -> np.ndarray:
    """Radial light scattering with pre-computed decay table and downsampled pass."""
    h, w = arr.shape[:2]

    # Downsample for speed
    ds = 4
    sh, sw = h // ds, w // ds
    from scipy.ndimage import zoom as sz
    small = sz(arr[:, :, :3].astype(np.float32), (sh / h, sw / w, 1), order=1)

    # Pre-compute decay table (instead of per-iteration multiply)
    decay_table = np.power(decay, np.arange(num_samples)) * 0.02

    cy, cx = 0.5, 0.5
    yy, xx = np.mgrid[0:sh, 0:sw]
    uy = (yy / sh).astype(np.float64)
    ux = (xx / sw).astype(np.float64)

    dy = (uy - cy) / num_samples
    dx = (ux - cx) / num_samples

    result = np.zeros((sh, sw, 3), dtype=np.float64)
    coord_y, coord_x = uy.copy(), ux.copy()

    for i in range(num_samples):
        coord_y -= dy
        coord_x -= dx
        sy = np.clip((coord_y * sh).astype(int), 0, sh - 1)
        sx = np.clip((coord_x * sw).astype(int), 0, sw - 1)
        result += small[sy, sx].astype(np.float64) * decay_table[i]

    # Upscale back
    rays = sz(result, (h / sh, w / sw, 1), order=1)[:h, :w]

    out = arr.astype(np.float32)
    out[:, :, :3] += (rays * intensity).astype(np.float32)
    return np.clip(out, 0, 255).astype(np.uint8)


def apply_chromatic_aberration(arr: np.ndarray, strength: float = 3.0) -> np.ndarray:
    """Radial RGB channel separation with cached coordinate grids."""
    try:
        from scipy.ndimage import map_coordinates
    except ImportError:
        return arr

    h, w = arr.shape[:2]
    yy, xx = _get_coord_grid(h, w)
    cy, cx = h / 2.0, w / 2.0

    result = arr.copy()
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
    """Luminance-dependent photographic grain with cached noise."""
    h, w = arr.shape[:2]
    noise = _get_grain(h, w, grain_size)

    lum = arr[:, :, :3].astype(np.float32).mean(axis=2) / 255.0
    midtone_weight = 4.0 * lum * (1.0 - lum)
    grain = noise * intensity * 255.0 * midtone_weight

    result = arr.astype(np.float32)
    result[:, :, :3] += grain[:, :, np.newaxis]
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_heat_distortion(arr: np.ndarray, amplitude: float = 3.0,
                          frequency: float = 0.02) -> np.ndarray:
    """Sine-wave displacement with cached coordinate grid."""
    try:
        from scipy.ndimage import map_coordinates
    except ImportError:
        return arr

    h, w = arr.shape[:2]
    yy, xx = _get_coord_grid(h, w)

    dx = amplitude * np.sin(yy * frequency * 2 * np.pi)
    dy = amplitude * np.sin(xx * frequency * 2 * np.pi * 0.7)

    src_y = yy + dy
    src_x = xx + dx

    result = arr.copy()
    for c in range(3):
        result[:, :, c] = map_coordinates(
            arr[:, :, c].astype(np.float32),
            [src_y, src_x], order=1, mode='reflect'
        ).astype(np.uint8)
    return result


def apply_color_grading(arr: np.ndarray, shadow_tint=(0, 0, 10),
                        highlight_tint=(10, 5, 0),
                        contrast: float = 1.0,
                        saturation: float = 1.0) -> np.ndarray:
    """Split-toning with vectorized broadcasting."""
    img = arr[:, :, :3].astype(np.float32)
    lum = img.mean(axis=2, keepdims=True)

    if abs(contrast - 1.0) > 0.01:
        img = (img - 128) * contrast + 128

    if abs(saturation - 1.0) > 0.01:
        img = lum + (img - lum) * saturation

    # Vectorized split toning (no per-channel loop)
    lum_norm = lum / 255.0
    shadow_arr = np.array(shadow_tint, dtype=np.float32).reshape(1, 1, 3)
    highlight_arr = np.array(highlight_tint, dtype=np.float32).reshape(1, 1, 3)
    img += (1.0 - lum_norm) * shadow_arr
    img += lum_norm * highlight_arr

    out = arr.copy()
    out[:, :, :3] = np.clip(img, 0, 255).astype(np.uint8)
    return out
