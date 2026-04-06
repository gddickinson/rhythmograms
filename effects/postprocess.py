"""Post-processing effects: inversion, solarization, bloom/glow, vignette."""

from dataclasses import dataclass
import numpy as np
from PyQt6.QtGui import QImage


@dataclass
class EffectsConfig:
    """Active post-processing effect settings."""
    invert: bool = False
    solarize: bool = False
    solarize_threshold: int = 128    # 0-255
    bloom: bool = False
    bloom_radius: int = 5            # kernel radius
    bloom_intensity: float = 0.4     # blend factor
    bloom_layers: int = 1            # 1 = basic, 2-3 = multi-radius HDR
    vignette: bool = False
    vignette_strength: float = 0.5   # 0.0-1.0

    def to_dict(self) -> dict:
        return {
            "invert": self.invert,
            "solarize": self.solarize,
            "solarize_threshold": self.solarize_threshold,
            "bloom": self.bloom,
            "bloom_radius": self.bloom_radius,
            "bloom_intensity": self.bloom_intensity,
            "bloom_layers": self.bloom_layers,
            "vignette": self.vignette,
            "vignette_strength": self.vignette_strength,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EffectsConfig":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


def qimage_to_array(image: QImage) -> np.ndarray:
    """Convert QImage (Format_ARGB32) to numpy RGBA array."""
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    w, h = image.width(), image.height()
    ptr = image.bits()
    ptr.setsize(h * w * 4)
    arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 4)).copy()
    # QImage ARGB32 is stored as BGRA in memory
    return arr


def array_to_qimage(arr: np.ndarray) -> QImage:
    """Convert numpy BGRA array back to QImage."""
    h, w, _ = arr.shape
    arr = np.ascontiguousarray(arr)
    return QImage(arr.data, w, h, w * 4, QImage.Format.Format_ARGB32).copy()


def apply_invert(arr: np.ndarray) -> np.ndarray:
    """Invert RGB channels (leave alpha untouched). BGRA layout."""
    result = arr.copy()
    result[:, :, :3] = 255 - result[:, :, :3]
    return result


def apply_solarize(arr: np.ndarray, threshold: int = 128) -> np.ndarray:
    """Solarize: invert pixels above threshold. BGRA layout."""
    result = arr.copy()
    rgb = result[:, :, :3]
    mask = rgb > threshold
    rgb[mask] = 255 - rgb[mask]
    return result


def _gaussian_blur(arr: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian blur on RGB channels."""
    try:
        from scipy.ndimage import gaussian_filter
        blurred = np.empty_like(arr, dtype=np.float32)
        for c in range(3):
            blurred[:, :, c] = gaussian_filter(
                arr[:, :, c].astype(np.float32), sigma=sigma
            )
        blurred[:, :, 3] = arr[:, :, 3]
        return blurred
    except ImportError:
        return _box_blur(arr, int(sigma))


def _box_blur(arr: np.ndarray, radius: int) -> np.ndarray:
    """Simple 3-pass box blur approximation of Gaussian blur."""
    result = arr.astype(np.float32)
    kernel_size = 2 * radius + 1

    for _ in range(3):  # 3 passes approximates Gaussian
        padded = np.pad(result, ((radius, radius), (radius, radius), (0, 0)),
                        mode='edge')
        cumsum = np.cumsum(padded, axis=0)
        result_v = (cumsum[kernel_size:] - cumsum[:-kernel_size]) / kernel_size
        padded2 = np.pad(result_v, ((0, 0), (radius, radius), (0, 0)),
                         mode='edge')
        cumsum2 = np.cumsum(padded2, axis=1)
        result = (cumsum2[:, kernel_size:] - cumsum2[:, :-kernel_size]) / kernel_size

    return result


def apply_bloom(arr: np.ndarray, radius: int = 5, intensity: float = 0.4,
                layers: int = 1) -> np.ndarray:
    """Bloom/glow with optional multi-radius HDR layers.

    layers=1: basic single-pass bloom
    layers=2-3: multi-radius glow (tight core + wide halo)
    """
    result = arr.astype(np.float32)

    if layers <= 1:
        blurred = _gaussian_blur(arr, sigma=radius)
        result = result + blurred * intensity
    else:
        # Multi-radius HDR bloom: each layer is wider and softer
        for i in range(layers):
            layer_sigma = radius * (2 ** i)
            layer_intensity = intensity / (1.5 ** i)
            blurred = _gaussian_blur(arr, sigma=layer_sigma)
            result = result + blurred * layer_intensity

    return np.clip(result, 0, 255).astype(np.uint8)


def apply_vignette(arr: np.ndarray, strength: float = 0.5) -> np.ndarray:
    """Apply radial vignette darkening toward edges.

    strength: 0.0 = no effect, 1.0 = heavy darkening at corners.
    """
    h, w = arr.shape[:2]
    cy, cx = h / 2.0, w / 2.0

    # Create radial distance mask normalized to [0, 1]
    y = np.arange(h, dtype=np.float32) - cy
    x = np.arange(w, dtype=np.float32) - cx
    yy, xx = np.meshgrid(y, x, indexing='ij')
    max_dist = np.sqrt(cx * cx + cy * cy)
    dist = np.sqrt(xx * xx + yy * yy) / max_dist

    # Smooth vignette: cos^2 falloff from center
    vignette_mask = 1.0 - strength * (dist ** 2)
    vignette_mask = np.clip(vignette_mask, 0, 1)

    result = arr.astype(np.float32)
    # Apply to RGB channels only (BGRA layout: channels 0,1,2)
    for c in range(3):
        result[:, :, c] *= vignette_mask
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_effects(image: QImage, config: EffectsConfig) -> QImage:
    """Apply the full effect chain to a QImage."""
    has_any = config.invert or config.solarize or config.bloom or config.vignette
    if not has_any:
        return image

    arr = qimage_to_array(image)

    if config.bloom:
        arr = apply_bloom(arr, config.bloom_radius, config.bloom_intensity,
                          config.bloom_layers)
    if config.vignette:
        arr = apply_vignette(arr, config.vignette_strength)
    if config.solarize:
        arr = apply_solarize(arr, config.solarize_threshold)
    if config.invert:
        arr = apply_invert(arr)

    return array_to_qimage(arr)
