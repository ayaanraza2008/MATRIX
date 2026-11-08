"""MATRIX AirTouch Gesture3D Controller.
Translates real-time hand/fist movement into smooth, continuous 3D object rotation.
Features:
- Dual-axis and tri-axis rotation tracking
- Adaptive velocity scaling and sensitivity configuration
- Jump suppression and deadzone thresholding (prevents erratic snapping)
- Integrated Holt-Wright double-exponential smoothing
- Emits rotation angles and 4x4 transformation matrices for 3D hologram/HUD objects
"""
import time
import math
from typing import Dict, Any, Tuple, Optional
import numpy as np
from vision.airtouch.smoother import HoltWrightSmoother


class Gesture3DController:
    """Controls 3D object rotation using hand and fist movement vectors."""

    def __init__(
        self,
        sensitivity: float = 3.5,
        smoothing_alpha: float = 0.85,
        deadzone_px: float = 2.0,
        jump_threshold_px: float = 80.0
    ):
        self.sensitivity = float(sensitivity)
        self.deadzone_px = float(deadzone_px)
        self.jump_threshold_px = float(jump_threshold_px)
        
        # Holt-Wright smoother for rotation angles [yaw, pitch, roll]
        self.smoother = HoltWrightSmoother(
            alphas=[smoothing_alpha, smoothing_alpha, smoothing_alpha],
            initial_values=[0.0, 0.0, 0.0],
            look_ahead=0.4
        )
        
        self.current_angles = [0.0, 0.0, 0.0]  # [yaw (Y), pitch (X), roll (Z)] in radians
        self.last_pos: Optional[Tuple[float, float]] = None
        self.last_update = time.perf_counter()
        self.is_active = True
        self.rotation_count = 0

    def update_position(
        self,
        pos_x: float,
        pos_y: float,
        frame_width: int = 640,
        frame_height: int = 480,
        is_fist_closed: bool = True
    ) -> Dict[str, Any]:
        """Update controller with current hand/fist centroid and return smooth 3D rotation state."""
        now = time.perf_counter()
        dt = max(now - self.last_update, 1e-4)
        self.last_update = now

        if self.last_pos is None:
            self.last_pos = (pos_x, pos_y)
            return self._build_state(dx=0.0, dy=0.0, jumping=False)

        # Delta in pixels
        dx_px = pos_x - self.last_pos[0]
        dy_px = pos_y - self.last_pos[1]
        dist_px = math.hypot(dx_px, dy_px)

        # Check for abnormal jump (e.g. hand left frame and reappeared on opposite side)
        if dist_px > self.jump_threshold_px:
            self.last_pos = (pos_x, pos_y)
            return self._build_state(dx=0.0, dy=0.0, jumping=True)

        # Check deadzone
        if dist_px < self.deadzone_px:
            self.last_pos = (pos_x, pos_y)
            # Still run smoother to allow inertia to settle smoothly
            smoothed = self.smoother.smooth(self.current_angles)
            self.current_angles = smoothed
            return self._build_state(dx=0.0, dy=0.0, jumping=False)

        # Normalized screen space deltas (-1.0 to 1.0)
        norm_dx = dx_px / max(frame_width, 1)
        norm_dy = dy_px / max(frame_height, 1)

        # Apply rotation if fist/hand is in active controlling state
        if is_fist_closed and self.is_active:
            # Horizontal hand motion rotates around Y-axis (yaw)
            # Vertical hand motion rotates around X-axis (pitch)
            self.current_angles[0] += norm_dx * self.sensitivity * math.pi
            self.current_angles[1] += norm_dy * self.sensitivity * math.pi
            self.rotation_count += 1

        # Smooth angles
        smoothed = self.smoother.smooth(self.current_angles)
        self.current_angles = smoothed
        self.last_pos = (pos_x, pos_y)

        return self._build_state(dx=norm_dx, dy=norm_dy, jumping=False)

    def _build_state(self, dx: float, dy: float, jumping: bool) -> Dict[str, Any]:
        yaw = self.current_angles[0]
        pitch = self.current_angles[1]
        roll = self.current_angles[2]

        # Convert to degrees for frontend UI / CSS transforms
        yaw_deg = math.degrees(yaw) % 360.0
        pitch_deg = math.degrees(pitch) % 360.0

        # Construct 4x4 column-major transformation matrix
        cy, sy = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)

        matrix = [
            cy, sy * sp, sy * cp, 0.0,
            0.0, cp, -sp, 0.0,
            -sy, cy * sp, cy * cp, 0.0,
            0.0, 0.0, 0.0, 1.0
        ]

        return {
            "rotation_rad": {"yaw": round(yaw, 4), "pitch": round(pitch, 4), "roll": round(roll, 4)},
            "rotation_deg": {"yaw": round(yaw_deg, 2), "pitch": round(pitch_deg, 2)},
            "delta": {"dx": round(dx, 4), "dy": round(dy, 4)},
            "matrix": [round(m, 5) for m in matrix],
            "is_jumping": jumping,
            "rotation_count": self.rotation_count,
            "css_transform": f"rotateY({yaw_deg:.1f}deg) rotateX({-pitch_deg:.1f}deg)"
        }

    def reset(self):
        """Reset rotation angles back to zero identity."""
        self.current_angles = [0.0, 0.0, 0.0]
        self.last_pos = None
        self.smoother.reset([0.0, 0.0, 0.0])
