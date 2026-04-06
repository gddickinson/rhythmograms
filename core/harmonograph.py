"""Numpy-vectorized harmonograph engine with FM/PM, Duffing nonlinearity,
envelope modulation, light extinction, and multi-trace chorus."""

import numpy as np
from .pendulum import HarmonographConfig, PendulumParams


class HarmonographEngine:
    """Computes (x, y) trace points for a 4-pendulum damped harmonograph.

    Supports frequency/phase modulation, Duffing nonlinearity (via RK4),
    strobe/duty-cycle blanking, and multi-trace chorus.
    """

    def __init__(self, config: HarmonographConfig):
        self.config = config
        self._precompute()

    def _precompute(self):
        p = self.config.pendulums
        self._freq = np.array([pp.frequency for pp in p]) * 2 * np.pi
        self._phase = np.array([pp.phase for pp in p])
        self._amp = np.array([pp.amplitude for pp in p])
        self._damp = np.array([pp.damping for pp in p])
        # FM/PM params
        self._fm_freq = np.array([pp.fm_freq for pp in p]) * 2 * np.pi
        self._fm_depth = np.array([pp.fm_depth for pp in p]) * 2 * np.pi
        self._pm_freq = np.array([pp.pm_freq for pp in p]) * 2 * np.pi
        self._pm_depth = np.array([pp.pm_depth for pp in p])
        self._nonlin = np.array([pp.nonlinearity for pp in p])
        self._has_fm = np.any(self._fm_depth != 0)
        self._has_pm = np.any(self._pm_depth != 0)
        self._has_nonlin = np.any(self._nonlin != 0)

    def compute_full(self) -> tuple:
        n = self.config.total_points
        t = np.linspace(0, self.config.duration, n)
        return self._compute_with_chorus(t)

    def compute_chunk(self, start_idx: int, chunk_size: int,
                      unbounded: bool = False) -> tuple:
        n = self.config.total_points
        end_idx = start_idx + chunk_size
        if not unbounded:
            end_idx = min(end_idx, n)
            if start_idx >= n:
                return np.array([]), np.array([])
        t_start = start_idx / self.config.sample_rate
        t_end = end_idx / self.config.sample_rate
        t = np.linspace(t_start, t_end, end_idx - start_idx)
        return self._compute_with_chorus(t)

    def _compute_with_chorus(self, t: np.ndarray) -> tuple:
        """Compute with optional multi-trace chorus (N detuned copies)."""
        cc = self.config
        if cc.chorus_count <= 1:
            x, y = self._compute_at(t)
            return self._apply_strobe(t, x, y)

        # Render N copies with frequency spread, accumulate
        x_acc = np.zeros_like(t)
        y_acc = np.zeros_like(t)
        n_copies = cc.chorus_count
        scale = 1.0 / n_copies

        for i in range(n_copies):
            # Spread frequencies symmetrically around center
            offset = (i - (n_copies - 1) / 2.0) * cc.chorus_spread
            # Temporarily shift frequencies
            orig_freq = self._freq.copy()
            self._freq = orig_freq + offset * 2 * np.pi
            xi, yi = self._compute_at(t)
            self._freq = orig_freq
            x_acc += xi * scale
            y_acc += yi * scale

        return self._apply_strobe(t, x_acc, y_acc)

    def _apply_strobe(self, t, x, y):
        """Apply light extinction / duty cycle blanking."""
        sf = self.config.strobe_freq
        if sf <= 0:
            return x, y
        period = 1.0 / sf
        phase_in_cycle = np.fmod(t, period) / period
        mask = phase_in_cycle < self.config.strobe_duty
        x = np.where(mask, x, np.nan)
        y = np.where(mask, y, np.nan)
        return x, y

    def _compute_at(self, t: np.ndarray) -> tuple:
        """Compute x, y at given time values with FM/PM and envelope."""
        env = self.config.envelope

        if self._has_nonlin:
            return self._compute_nonlinear(t, env)

        signals = np.empty((4, len(t)))
        for i in range(4):
            # Frequency modulation
            freq = self._freq[i]
            if self._fm_depth[i] != 0:
                freq = freq + self._fm_depth[i] * np.sin(self._fm_freq[i] * t)

            # Phase modulation
            phase = self._phase[i]
            if self._pm_depth[i] != 0:
                phase = phase + self._pm_depth[i] * np.sin(self._pm_freq[i] * t)

            oscillation = self._amp[i] * np.sin(freq * t + phase)
            envelope = self._compute_envelope(t, self._damp[i], env)
            signals[i] = oscillation * envelope

        return signals[0] + signals[1], signals[2] + signals[3]

    def _compute_nonlinear(self, t, env):
        """RK4 integration for Duffing nonlinearity."""
        dt = t[1] - t[0] if len(t) > 1 else 1.0 / self.config.sample_rate
        n = len(t)
        signals = np.zeros((4, n))

        for i in range(4):
            # State: [position, velocity]
            pos, vel = 0.0, self._amp[i] * self._freq[i]
            omega = self._freq[i]
            d = self._damp[i]
            nl = self._nonlin[i]
            fm_d = self._fm_depth[i]
            fm_f = self._fm_freq[i]
            pm_d = self._pm_depth[i]
            pm_f = self._pm_freq[i]

            for j in range(n):
                tj = t[j]
                signals[i, j] = pos

                # Effective frequency with FM
                w = omega
                if fm_d != 0:
                    w = omega + fm_d * np.sin(fm_f * tj)

                # Duffing: x'' + d*x' + w^2*x + nl*x^3 = 0
                def deriv(p, v, tt):
                    wt = omega + (fm_d * np.sin(fm_f * tt) if fm_d != 0 else 0)
                    return v, -2 * d * v - wt * wt * p - nl * p * p * p

                # RK4 step
                k1v, k1a = deriv(pos, vel, tj)
                k2v, k2a = deriv(pos + 0.5 * dt * k1v, vel + 0.5 * dt * k1a, tj + 0.5 * dt)
                k3v, k3a = deriv(pos + 0.5 * dt * k2v, vel + 0.5 * dt * k2a, tj + 0.5 * dt)
                k4v, k4a = deriv(pos + dt * k3v, vel + dt * k3a, tj + dt)

                pos += dt / 6.0 * (k1v + 2 * k2v + 2 * k3v + k4v)
                vel += dt / 6.0 * (k1a + 2 * k2a + 2 * k3a + k4a)

            # Apply envelope
            envelope = self._compute_envelope(t, d, env)
            # Normalize amplitude
            max_abs = np.max(np.abs(signals[i]))
            if max_abs > 1e-10:
                signals[i] = signals[i] / max_abs * self._amp[i]
            signals[i] *= envelope

        return signals[0] + signals[1], signals[2] + signals[3]

    @staticmethod
    def _compute_envelope(t, damping, env_config):
        base_decay = np.exp(-damping * t)
        if env_config.mode == "none" or env_config.strength <= 0:
            return base_decay
        s = env_config.strength
        f = max(env_config.frequency, 0.001)
        if env_config.mode == "breathe":
            mod = 0.5 * (1.0 + np.cos(2.0 * np.pi * f * t))
            return base_decay * ((1.0 - s) + s * mod)
        if env_config.mode == "pulse":
            period = 1.0 / f
            t_mod = np.fmod(t, period)
            pulse_env = np.exp(-damping * t_mod)
            return (1.0 - s) * base_decay + s * pulse_env
        if env_config.mode == "bounce":
            period = 1.0 / f
            phase = np.fmod(t, period) / period
            triangle = 1.0 - 2.0 * np.abs(phase - 0.5)
            smooth_tri = np.sin(triangle * np.pi * 0.5)
            return (1.0 - s) * base_decay + s * smooth_tri
        return base_decay

    def compute_normalized(self, width, height, margin=0.05):
        x, y = self.compute_full()
        return self._normalize(x, y, width, height, margin)

    def compute_chunk_normalized(self, start_idx, chunk_size, width, height,
                                 x_range=None, y_range=None, margin=0.05,
                                 unbounded=False):
        x, y = self.compute_chunk(start_idx, chunk_size, unbounded=unbounded)
        if len(x) == 0:
            return np.array([]), np.array([])
        if x_range and y_range:
            x = self._scale(x, x_range, width, margin)
            y = self._scale(y, y_range, height, margin)
        else:
            x, y = self._normalize(x, y, width, height, margin)
        return x, y

    def compute_ranges(self):
        x, y = self.compute_full()
        # Filter NaN from strobe
        x_valid = x[~np.isnan(x)]
        y_valid = y[~np.isnan(y)]
        if len(x_valid) == 0:
            return (-1, 1), (-1, 1)
        return (x_valid.min(), x_valid.max()), (y_valid.min(), y_valid.max())

    def compute_speed_range(self):
        x, y = self.compute_full()
        # Handle NaN from strobe
        mask = ~(np.isnan(x[:-1]) | np.isnan(x[1:]))
        dx = np.diff(x)
        dy = np.diff(y)
        speed = np.sqrt(dx * dx + dy * dy)
        valid = speed[mask]
        if len(valid) == 0:
            return (0.0, 1.0)
        return float(valid.min()), float(valid.max())

    def compute_amplitude_ranges(self):
        a = self._amp
        x_max = a[0] + a[1]
        y_max = a[2] + a[3]
        return (-x_max, x_max), (-y_max, y_max)

    @staticmethod
    def _normalize(x, y, width, height, margin):
        x_valid = x[~np.isnan(x)]
        y_valid = y[~np.isnan(y)]
        if len(x_valid) == 0:
            return x, y
        x_range = (x_valid.min(), x_valid.max())
        y_range = (y_valid.min(), y_valid.max())
        x = HarmonographEngine._scale(x, x_range, width, margin)
        y = HarmonographEngine._scale(y, y_range, height, margin)
        return x, y

    @staticmethod
    def _scale(values, val_range, size, margin):
        v_min, v_max = val_range
        span = v_max - v_min
        if span < 1e-10:
            return np.full_like(values, size / 2.0)
        m = size * margin
        return m + (values - v_min) / span * (size - 2 * m)
