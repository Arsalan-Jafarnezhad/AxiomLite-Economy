"""
Top-right social icon row (GitHub / Telegram / LinkedIn). A text fallback
button is used automatically if an icon file is missing.
"""

from tkinter import Button, Frame, Label, LEFT, PhotoImage
from webbrowser import open_new_tab

from ..config import GITHUB_ICON_PATH, LINKEDIN_ICON_PATH, TELEGRAM_ICON_PATH
from .theme import BG, FG, MUTED, SURFACE

try:
    from PIL import Image, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

ICON_SIZE = 20


class SocialLinksMixin:
    """Mixin providing the top-right "Follow" icon row."""

    def _init_social_links(self) -> None:
        self.github_url = "https://github.com/arsalan-jafarnezhad/"
        self.telegram_url = "https://t.me/axiomlite/"
        self.linkedin_url = "https://linkedin.com/in/arsalan-jafarnezhad/"

        self.icon_fallback_font = ("Segoe UI", 9, "bold")
        self.github_icon = self.load_icon(GITHUB_ICON_PATH, ICON_SIZE)
        self.telegram_icon = self.load_icon(TELEGRAM_ICON_PATH, ICON_SIZE)
        self.linkedin_icon = self.load_icon(LINKEDIN_ICON_PATH, ICON_SIZE)

    def load_icon(self, path, size):
        """Load and resize an icon safely. Returns None if unavailable so
        callers can fall back to a text button instead of crashing."""
        try:
            if PIL_AVAILABLE:
                img = Image.open(path).convert("RGBA")
                img = img.resize((size, size), Image.LANCZOS)
                return ImageTk.PhotoImage(img)

            img = PhotoImage(file=path)
            current_w = img.width() or size
            if current_w > size:
                factor = max(1, round(current_w / size))
                img = img.subsample(factor, factor)
            elif current_w < size:
                factor = max(1, round(size / current_w))
                img = img.zoom(factor, factor)
            return img
        except Exception:
            return None

    def open_link(self, url):
        from tkinter import messagebox

        try:
            open_new_tab(url)
        except Exception:
            messagebox.showerror("Could Not Open Link", f"Unable to open:\n{url}")

    def build_social_icons(self, parent):
        Label(parent, text="Follow", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(
            side=LEFT, padx=(0, 8)
        )
        icons = Frame(parent, bg=BG)
        icons.pack(side=LEFT)

        self.make_social_button(icons, self.github_icon, "GH", self.github_url)
        self.make_social_button(icons, self.telegram_icon, "TG", self.telegram_url)
        self.make_social_button(icons, self.linkedin_icon, "in", self.linkedin_url)

    def make_social_button(self, parent, icon, fallback_text, url):
        common_kwargs = dict(
            command=lambda: self.open_link(url),
            bg=BG,
            activebackground=SURFACE,
            bd=0,
            relief="flat",
            cursor="hand2",
            highlightthickness=0,
        )
        if icon is not None:
            btn = Button(parent, image=icon, **common_kwargs)
            btn.image = icon  # keep a reference so it isn't garbage collected
        else:
            btn = Button(
                parent, text=fallback_text, fg=FG, font=self.icon_fallback_font,
                width=3, **common_kwargs,
            )
        btn.pack(side=LEFT, padx=3)
        btn.bind("<Enter>", lambda e: btn.config(bg=SURFACE))
        btn.bind("<Leave>", lambda e: btn.config(bg=BG))
        return btn
