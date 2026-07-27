# ui/logo_widget.py
"""
Professional animated logo widget for AI Rebar.
The text resides inside the rebar loop, and a red slogan (not bold) is displayed
underneath. Background matches the parent theme.
"""

import tkinter as tk
from tkinter import ttk
import math
from typing import Optional, Tuple


class LogoWidget(tk.Canvas):
    """Canvas‑based animated logo: rebar shape + inner text + static red slogan."""

    def __init__(
        self,
        parent: tk.Widget,
        width: int = 180,
        height: int = 80,
        bg: str = None,
        dark_color: str = "#0d3b4c",
        light_color: str = "#2ecc71",
        glow_color: str = "#1abc9c",
        font: Tuple[str, int, str] = ("Helvetica", 14, "bold"),
        slogan: str = "Cutting Optimization",
        slogan_font: Tuple[str, int, str] = ("Helvetica", 9, "italic"),  # not bold
        slogan_color: str = "#e74c3c",   # striking red
        text: str = "AI Rebar",
        speed_ms: int = 40,
        **kwargs
    ):
        # --- Automatically match parent's background ---
        if bg is None:
            if isinstance(parent, ttk.Widget):
                style = ttk.Style()
                try:
                    bg = style.lookup(parent['style'], 'background')
                except:
                    bg = "#ffffff"
            else:
                try:
                    bg = parent.cget("bg")
                except:
                    bg = "#ffffff"

        super().__init__(parent, width=width, height=height,
                         bg=bg, highlightthickness=0, **kwargs)
        self._dark = dark_color
        self._light = light_color
        self._glow = glow_color
        self._font = font
        self._slogan = slogan
        self._slogan_font = slogan_font
        self._slogan_color = slogan_color
        self._text_str = text
        self._speed = speed_ms
        self._running = False
        self._phase = 0.0
        self._job_id: Optional[str] = None

        self._bar_items: list = []
        self._text_id: Optional[int] = None
        self._slogan_id: Optional[int] = None

        self._draw_shapes()
        self.bind("<Configure>", self._on_resize)
        self.start_animation()

    # ------------------------------------------------------------------
    # Color helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _interpolate_color(hex1: str, hex2: str, t: float) -> str:
        r1, g1, b1 = int(hex1[1:3], 16), int(hex1[3:5], 16), int(hex1[5:7], 16)
        r2, g2, b2 = int(hex2[1:3], 16), int(hex2[3:5], 16), int(hex2[5:7], 16)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _draw_shapes(self, event=None):
        self.delete("all")
        self._bar_items.clear()

        w = self.winfo_width()
        h = self.winfo_height()
        if w < 20 or h < 20:
            w, h = 180, 80

        shape_area_height = int(h * 0.6)
        bar_y = shape_area_height
        hook_len = int(shape_area_height * 0.55)
        hook_ext = int(h * 0.15)
        left_x = int(w * 0.18)
        right_x = int(w * 0.82)

        bar_id = self.create_line(
            left_x, bar_y, right_x, bar_y,
            fill=self._light, width=3, tags="shape"
        )
        self._bar_items.append(bar_id)

        l1 = self.create_line(
            left_x, bar_y, left_x, bar_y - hook_len,
            fill=self._light, width=3, tags="shape"
        )
        l2 = self.create_line(
            left_x, bar_y - hook_len, left_x + hook_ext, bar_y - hook_len,
            fill=self._light, width=3, tags="shape"
        )
        self._bar_items.extend([l1, l2])

        r1 = self.create_line(
            right_x, bar_y, right_x, bar_y - hook_len,
            fill=self._light, width=3, tags="shape"
        )
        r2 = self.create_line(
            right_x, bar_y - hook_len, right_x - hook_ext, bar_y - hook_len,
            fill=self._light, width=3, tags="shape"
        )
        self._bar_items.extend([r1, r2])

        text_x = w // 2
        text_y = bar_y - hook_len // 2
        self._text_id = self.create_text(
            text_x, text_y,
            text=self._text_str,
            font=self._font,
            fill=self._light,
            anchor="center",
            tags="text"
        )

        # Static red slogan – italic, not bold
        if self._slogan:
            slogan_y = shape_area_height + (h - shape_area_height) // 2
            self._slogan_id = self.create_text(
                w // 2, slogan_y,
                text=self._slogan,
                font=self._slogan_font,
                fill=self._slogan_color,
                anchor="center",
                tags="slogan"
            )

    def _on_resize(self, event):
        self._draw_shapes()

    # ------------------------------------------------------------------
    # Animation (only shapes + inner text breathe)
    # ------------------------------------------------------------------
    def _animate(self):
        if not self._running:
            return
        t = (math.sin(self._phase) + 1) / 2.0

        shape_color = self._interpolate_color(self._dark, self._light, t)
        for item in self._bar_items:
            self.itemconfig(item, fill=shape_color)

        if self._text_id:
            self.itemconfig(self._text_id, fill=shape_color)

        # Slogan is static – no animation

        self._phase += 0.05
        self._job_id = self.after(self._speed, self._animate)

    def start_animation(self):
        if not self._running:
            self._running = True
            self._animate()

    def stop_animation(self):
        self._running = False
        if self._job_id is not None:
            self.after_cancel(self._job_id)
            self._job_id = None

    def destroy(self):
        self.stop_animation()
        super().destroy()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_text(self, new_text: str):
        self._text_str = new_text
        if self._text_id:
            self.itemconfig(self._text_id, text=new_text)

    def set_slogan(self, new_slogan: str):
        self._slogan = new_slogan
        self._draw_shapes()

    def set_slogan_color(self, color: str):
        self._slogan_color = color
        if self._slogan_id:
            self.itemconfig(self._slogan_id, fill=color)

    def set_font(self, font: tuple):
        self._font = font
        if self._text_id:
            self.itemconfig(self._text_id, font=font)

    def set_colors(self, dark: str = None, light: str = None, glow: str = None):
        if dark: self._dark = dark
        if light: self._light = light
        if glow: self._glow = glow
        self._draw_shapes()