"""MATRIX AirTouch Touchless Gesture Scrolling Subsystem.
Translates vertical hand/finger gestures into smooth, velocity-controlled scrolling:
- Supports webpages, documents, and Matrix UI
- Up/Down directional scrolling
- Velocity and momentum curves with Holt-Wright smoothing
- Adjustable sensitivity modes (LOW, MEDIUM, HIGH)
- Accidental scroll prevention (deadzones, jump suppression, gesture-locking)
- Closed fist locks/stops scrolling immediately
- Emits OS scroll events via pyautogui and WebSocket payloads for web/HUD clients
"""
from typing import Dict, Any, Optional, Tuple
import math
import time

try:
    import pyautogui
    # Configure pyautogui safety
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.01
except ImportError:
    pyautogui = None

from vision.airtouch.smoother import HoltWrightSmoother
from config.logging_config import get_logger

logger = get_logger("vision.airtouch.scroll")


class AirTouchGestureScroll:
    """Controls OS and application scrolling via touchless hand gestures."""

    SPEED_PRESETS = {
        "LOW": 0.5,
        "MEDIUM": 1.0,
        "HIGH": 2.2
    }

    def __init__(
        self,
        speed_setting: str = "MEDIUM",
        sensitivity: float = 1.0,
        deadzone_px: float = 3.5,
        jump_threshold_px: float = 120.0,
        enable_os_scroll: bool = True
    ):
        self.speed_setting = speed_setting.upper() if speed_setting.upper() in self.SPEED_PRESETS else "MEDIUM"
        self.sensitivity = float(sensitivity)
        self.deadzone_px = float(deadzone_px)
        self.jump_threshold_px = float(jump_threshold_px)
        self.enable_os_scroll = enable_os_scroll and (pyautogui is not None)

        # Velocity smoother for smooth deceleration
        self.smoother = HoltWrightSmoother(
            alphas=[0.80],
            initial_values=[0.0],
            look_ahead=0.3
        )

        self.last_pos_y: Optional[float] = None
        self.last_update = time.perf_counter()
        self.consecutive_scroll_frames = 0
        self.min_activation_frames = 2
        self.is_locked = False
        self.total_scrolled_units = 0.0
        self.active_direction = "IDLE"

    def update_hand(
        self,
        pos_y: float,
        gesture: str,
        frame_height: int = 480
    ) -> Dict[str, Any]:
        """Update scroll controller with hand Y position and current gesture.
        
        Args:
            pos_y: Centroid or fingertip Y coordinate in pixel space.
            gesture: Classified gesture ('FIST', 'OPEN_PALM', 'POINTING', etc.).
            frame_height: Frame height in pixels for normalization.
        """
        now = time.perf_counter()
        dt = max(now - self.last_update, 1e-4)
        self.last_update = now

        # 1. Closed Fist immediately stops/locks scrolling
        if gesture == "FIST":
            self.is_locked = True
            self.consecutive_scroll_frames = 0
            self.last_pos_y = pos_y
            self.active_direction = "LOCKED"
            self.smoother.reset([0.0])
            return self._build_telemetry(0.0, 0.0, locked=True, direction="LOCKED", gesture=gesture)

        # Unlock if open palm or pointing
        if gesture in ("OPEN_PALM", "POINTING", "PEACE", "PARTIAL_HAND"):
            self.is_locked = False

        if self.last_pos_y is None:
            self.last_pos_y = pos_y
            return self._build_telemetry(0.0, 0.0, locked=False, direction="IDLE", gesture=gesture)

        # Delta Y (In screen/camera coords: hand moving UP means pos_y decreases)
        dy_px = pos_y - self.last_pos_y
        dist_y = abs(dy_px)

        # Jump suppression: Ignore abnormal jumps (hand re-entering frame)
        if dist_y > self.jump_threshold_px:
            self.last_pos_y = pos_y
            self.consecutive_scroll_frames = 0
            return self._build_telemetry(0.0, 0.0, locked=False, direction="JUMP_SUPPRESSED", gesture=gesture)

        # Deadzone thresholding
        if dist_y < self.deadzone_px:
            self.last_pos_y = pos_y
            # Smoothly damp residual velocity
            smoothed_vel = self.smoother.smooth([0.0])[0]
            if abs(smoothed_vel) < 0.05:
                smoothed_vel = 0.0
            return self._build_telemetry(0.0, smoothed_vel, locked=False, direction="IDLE", gesture=gesture)

        # Increment consecutive valid movement frames to prevent sporadic twitch triggers
        self.consecutive_scroll_frames += 1
        if self.consecutive_scroll_frames < self.min_activation_frames:
            self.last_pos_y = pos_y
            return self._build_telemetry(0.0, 0.0, locked=False, direction="ARMING", gesture=gesture)

        # Calculate normalized velocity (units per second)
        norm_dy = dy_px / max(frame_height, 1)
        instant_velocity = norm_dy / dt  # normalized units / sec

        # Holt-Wright smoothing on velocity
        smoothed_velocity = self.smoother.smooth([instant_velocity])[0]

        # Multipliers
        speed_mult = self.SPEED_PRESETS.get(self.speed_setting, 1.0) * self.sensitivity
        # Natural mapping:
        # Hand moves UP (dy_px < 0) -> scroll content UP (positive scroll units)
        # Hand moves DOWN (dy_px > 0) -> scroll content DOWN (negative scroll units)
        scroll_units = - (dy_px * speed_mult * 3.5)

        direction = "UP" if scroll_units > 0 else "DOWN"
        self.active_direction = direction
        self.total_scrolled_units += abs(scroll_units)
        self.last_pos_y = pos_y

        # Execute OS native scroll if enabled
        if self.enable_os_scroll and abs(scroll_units) >= 1.0:
            try:
                # pyautogui.scroll accepts integer clicks (positive for up, negative for down)
                clicks = int(round(scroll_units))
                if clicks != 0:
                    pyautogui.scroll(clicks)
            except Exception as e:
                logger.debug(f"OS scroll dispatch failed: {e}")

        return self._build_telemetry(
            scroll_units=scroll_units,
            velocity=smoothed_velocity,
            locked=False,
            direction=direction,
            gesture=gesture
        )

    def set_speed(self, preset: str):
        """Update speed preset ('LOW', 'MEDIUM', 'HIGH')."""
        upper = preset.upper()
        if upper in self.SPEED_PRESETS:
            self.speed_setting = upper
            logger.info(f"Gesture scroll speed set to {upper}")

    def set_sensitivity(self, val: float):
        """Update custom sensitivity multiplier."""
        self.sensitivity = max(0.1, min(float(val), 10.0))

    def reset(self):
        """Reset state."""
        self.last_pos_y = None
        self.consecutive_scroll_frames = 0
        self.is_locked = False
        self.smoother.reset([0.0])
        self.active_direction = "IDLE"

    def _build_telemetry(
        self,
        scroll_units: float,
        velocity: float,
        locked: bool,
        direction: str,
        gesture: str
    ) -> Dict[str, Any]:
        return {
            "scroll_units": round(scroll_units, 2),
            "velocity": round(velocity, 3),
            "direction": direction,
            "is_locked": locked,
            "active_gesture": gesture,
            "speed_setting": self.speed_setting,
            "sensitivity": self.sensitivity,
            "total_scrolled": round(self.total_scrolled_units, 1)
        }
