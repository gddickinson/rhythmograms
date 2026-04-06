"""Post-processing effects: inversion, solarization, bloom/glow."""

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

    def to_dict(self) -> dict:
        return {
            "invert": self.invert,
            "solarize": self.solarize,
            "solarize_threshold": self.solarize_threshold,
            "bloom": self.bloom,
            "bloom_radius": self.bloom_radius,
            "bloom_intensity": self.bloom_intensity,
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


def _box_blur(arr: np.ndarray, radius: int) -> np.ndarray:
    """Simple 3-pass box blur approximation of Gaussian blur."""
    from numpy.lib.stride_tricks import sliding_window_view
    result = arr.astype(np.float32)
    kernel_size = 2 * radius + 1

    for _ in range(3):  # 3 passes approximates Gaussian
        padded = np.pad(result, ((radius, radius), (radius, radius), (0, 0)),
                        mode='edge')
        # Cumulative sum approach for efficiency
        cumsum = np.cumsum(padded, axis=0)
        result_v = (cumsum[kernel_size:] - cumsum[:-kernel_size]) / kernel_size
        padded2 = np.pad(result_v, ((0, 0), (radius, radius), (0, 0)),
                         mode='edge')
        cumsum2 = np.cumsum(padded2, axis=1)
        result = (cumsum2[:, kernel_size:] - cumsum2[:, :-kernel_size]) / kernel_size

    return result


def apply_bloom(arr: np.ndarray, radius: int = 5, intensity: float = 0.4) -> np.ndarray:
    """Bloom/glow: add blurred version of bright areas back to image."""
    try:
        from scipy.ndimage import gaussian_filter
        blurred = np.empty_like(arr, dtype=np.float32)
        for c in range(3):  # blur RGB only
            blurred[:, :, c] = gaussian_filter(arr[:, :, c].astype(np.float32),
                                               sigma=radius)
        blurred[:, :, 3] = arr[:, :, 3]
    except ImportError:
        blurred = _box_blur(arr, radius)

    result = arr.astype(np.float32) + blurred * intensity
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_effects(image: QImage, config: EffectsConfig) -> QImage:
    """Apply the full effect chain to a QImage."""
    if not config.invert and not config.solarize and not config.bloom:
        return image

    arr = qimage_to_array(image)

    if config.bloom:
        arr = apply_bloom(arr, config.bloom_radius, config.bloom_intensity)
    if config.solarize:
        arr = apply_solarize(arr, config.solarize_threshold)
    if config.invert:
        arr = apply_invert(arr)

    return array_to_qimage(arr)
