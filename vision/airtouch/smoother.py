"""MATRIX AirTouch Smoothing Filter.
Implements double-exponential smoothing based on Wright's modification of Holt's method
for irregular sampling intervals with velocity trend look-ahead.
Eliminates jitter from hand tracking, 3D rotations, and eye gaze tracking.
"""
import time
import math
from typing import List, Sequence
import numpy as np


class HoltWrightSmoother:
    """Adaptive double-exponential smoother for irregular real-time video tracking data."""

    def __init__(
        self,
        alphas: Sequence[float],
        initial_values: Sequence[float],
        look_ahead: float = 0.5
    ):
        self.num_values = len(initial_values)
        self.initial_alphas = list(alphas)
        self.alphas = list(alphas)
        self.a = np.array(initial_values, dtype=np.float64)
        self.b = np.zeros(self.num_values, dtype=np.float64)
        self.look_ahead = float(look_ahead)
        self.last_update = time.perf_counter()
        self.initialized = True

    def smooth(self, values: Sequence[float]) -> List[float]:
        """Apply Wright's modification of Holt's method for irregular delta-time updates."""
        now = time.perf_counter()
        dt = max(now - self.last_update, 1e-4)
        self.last_update = now

        smoothed = []
        for i in range(self.num_values):
            val = float(values[i])
            init_alpha = self.initial_alphas[i]
            
            # Wright's adaptive alpha compensation for irregular time delta
            decay = math.pow(max(1.0 - init_alpha, 1e-6), dt)
            adjusted_alpha = self.alphas[i] / (self.alphas[i] + decay)
            self.alphas[i] = adjusted_alpha

            old_a = self.a[i]
            # Level update
            self.a[i] = adjusted_alpha * val + (1.0 - adjusted_alpha) * (old_a + self.b[i] * dt)
            # Trend (velocity) update
            self.b[i] = adjusted_alpha * (self.a[i] - old_a) / dt + (1.0 - adjusted_alpha) * self.b[i]

            # Forecast with look-ahead
            projected = self.a[i] + dt * self.look_ahead * self.b[i]
            smoothed.append(float(projected))

        return smoothed

    def reset(self, initial_values: Sequence[float]):
        """Reset state to baseline initial values."""
        self.alphas = list(self.initial_alphas)
        self.a = np.array(initial_values, dtype=np.float64)
        self.b = np.zeros(self.num_values, dtype=np.float64)
        self.last_update = time.perf_counter()
