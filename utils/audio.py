"""Audio analysis for audio-reactive mode — maps audio spectrum to pendulum params."""

import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class AudioAnalysis:
    """Pre-analyzed audio data for reactive modulation."""
    sample_rate: int
    duration: float
    # Per-frame spectral data (n_frames x n_bands)
    band_energies: np.ndarray    # shape (n_frames, n_bands)
    frame_duration: float        # seconds per frame
    n_bands: int

    def energy_at(self, t: float, band: int) -> float:
        """Get normalized energy (0-1) for a frequency band at time t."""
        frame_idx = int(t / self.frame_duration)
        frame_idx = max(0, min(frame_idx, len(self.band_energies) - 1))
        band = max(0, min(band, self.n_bands - 1))
        return float(self.band_energies[frame_idx, band])

    def modulation_at(self, t: float) -> dict:
        """Get modulation values for all bands at time t.

        Returns dict with keys 'bass', 'low_mid', 'mid', 'high_mid',
        'high', 'brightness', 'energy'.
        """
        frame_idx = int(t / self.frame_duration)
        frame_idx = max(0, min(frame_idx, len(self.band_energies) - 1))
        energies = self.band_energies[frame_idx]

        n = len(energies)
        return {
            "bass": float(np.mean(energies[:max(1, n // 5)])),
            "low_mid": float(np.mean(energies[n // 5:2 * n // 5])),
            "mid": float(np.mean(energies[2 * n // 5:3 * n // 5])),
            "high_mid": float(np.mean(energies[3 * n // 5:4 * n // 5])),
            "high": float(np.mean(energies[4 * n // 5:])),
            "brightness": float(np.mean(energies[n // 2:])),
            "energy": float(np.mean(energies)),
        }


def analyze_wav(path: str, n_bands: int = 8,
                frame_duration: float = 0.05) -> Optional[AudioAnalysis]:
    """Analyze a WAV file and extract spectral band energies over time.

    Args:
        path: Path to WAV file
        n_bands: Number of frequency bands to extract
        frame_duration: Duration of each analysis frame in seconds

    Returns AudioAnalysis or None on failure.
    """
    try:
        from scipy.io import wavfile
    except ImportError:
        return None

    try:
        sr, data = wavfile.read(path)
    except Exception:
        return None

    # Convert to mono float
    if data.ndim > 1:
        data = data.mean(axis=1)
    data = data.astype(np.float64)
    max_val = np.max(np.abs(data))
    if max_val > 0:
        data = data / max_val

    duration = len(data) / sr
    frame_samples = int(frame_duration * sr)
    n_frames = max(1, len(data) // frame_samples)

    band_energies = np.zeros((n_frames, n_bands))

    for i in range(n_frames):
        start = i * frame_samples
        end = min(start + frame_samples, len(data))
        chunk = data[start:end]

        if len(chunk) < 16:
            continue

        # FFT
        fft = np.abs(np.fft.rfft(chunk))
        n_bins = len(fft)

        # Split into frequency bands (log-spaced)
        band_edges = np.logspace(
            np.log10(1), np.log10(n_bins), n_bands + 1
        ).astype(int)
        band_edges = np.clip(band_edges, 0, n_bins)

        for b in range(n_bands):
            lo, hi = band_edges[b], band_edges[b + 1]
            if hi > lo:
                band_energies[i, b] = np.mean(fft[lo:hi])

    # Normalize each band to 0-1
    for b in range(n_bands):
        band_max = band_energies[:, b].max()
        if band_max > 0:
            band_energies[:, b] /= band_max

    return AudioAnalysis(
        sample_rate=sr,
        duration=duration,
        band_energies=band_energies,
        frame_duration=frame_duration,
        n_bands=n_bands,
    )


def check_audio_support() -> bool:
    """Check if audio analysis dependencies are available."""
    try:
        from scipy.io import wavfile
        return True
    except ImportError:
        return False
