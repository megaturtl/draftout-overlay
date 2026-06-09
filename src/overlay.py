import tkinter as tk
from typing import Callable

from config import BG, FG, DIM, GREEN, RED, DRAW, ENTRY_BG
from stats import Record


class OverlayView:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.configure(bg=BG)

        # --- Top Row ---
        self.top = tk.Frame(self.root, bg=BG)
        self.top.pack(fill="x", padx=10, pady=(4, 0))

        self.close_btn = self._glyph(self.top, "×", DIM, 22)
        self.close_btn.pack(side="right")

        self.refresh_btn = self._glyph(self.top, "⟳", DIM, 20)

        self.name_lbl = self._label(self.top, FG, 13, bold=True)
        self.name_lbl.pack(side="left")

        self.elo_lbl = self._label(self.top, DIM, 13)
        self.elo_lbl.pack(side="left", padx=(6, 16))

        # --- Second Row ---
        self.row = tk.Frame(self.root, bg=BG)
        self.row.pack(fill="x", padx=10, pady=(0, 8))

        self.w_lbl = self._label(self.row, GREEN, 16, bold=True)
        self.sep1 = self._label(self.row, DIM, 16, bold=True)
        self.d_lbl = self._label(self.row, DRAW, 16, bold=True)
        self.sep2 = self._label(self.row, DIM, 16, bold=True)
        self.l_lbl = self._label(self.row, RED, 16, bold=True)

        self.stat_labels = (self.w_lbl, self.sep1, self.d_lbl, self.sep2, self.l_lbl)
        for w in self.stat_labels:
            w.pack(side="left")

        self.ff_lbl = self._label(self.row, DIM, 12)
        self.ff_lbl.pack(side="left", padx=(12, 0))

        # --- Entry ---
        self.entry = tk.Entry(
            self.root,
            fg=FG,
            bg=ENTRY_BG,
            insertbackground=FG,
            font=("monospace", 11),
            relief="flat",
            width=20,
        )

        # Expose widgets that make up the "draggable" background
        self.draggable_areas = [
            self.root,
            self.top,
            self.name_lbl,
            self.elo_lbl,
            self.row,
        ]

    # -- Widget Factories --
    def _label(
        self, parent: tk.Misc, fg: str, size: int, bold: bool = False
    ) -> tk.Label:
        font = ("monospace", size, "bold") if bold else ("monospace", size)
        return tk.Label(parent, text="", fg=fg, bg=BG, font=font)

    def _glyph(self, parent: tk.Misc, text: str, fg: str, size: int) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            fg=fg,
            bg=BG,
            font=("monospace", size, "bold"),
            padx=4,
        )

    # -- Visual State Toggles --
    def show_waiting(self) -> None:
        self.name_lbl.config(text="Waiting for match...")
        self.elo_lbl.config(text="")
        for w in self.stat_labels + (self.ff_lbl,):
            w.config(text="")
        self.refresh_btn.pack_forget()
        self.entry.pack(fill="x", padx=10, pady=(0, 8))

    def show_player(self, rec: Record) -> None:
        self.entry.pack_forget()
        self.refresh_btn.pack(side="right")
        self.name_lbl.config(text=rec.name)
        self.elo_lbl.config(text=f"({rec.elo})" if rec.elo is not None else "")
        self.w_lbl.config(text=str(rec.wins))
        self.sep1.config(text="/")
        self.d_lbl.config(text=str(rec.draws))
        self.sep2.config(text="/")
        self.l_lbl.config(text=str(rec.losses), fg=RED)
        self.ff_lbl.config(
            text=f"FF:{rec.forfeit_pct}%" if rec.forfeit_pct is not None else ""
        )

    def show_status(self, name: str, message: str) -> None:
        self.entry.pack_forget()
        self.name_lbl.config(text=name)
        self.elo_lbl.config(text="")
        for w in self.stat_labels + (self.ff_lbl,):
            w.config(text="")
        self.l_lbl.config(text=message, fg=DIM)


class Overlay:
    def __init__(
        self,
        on_submit: Callable[[str], None],
        on_refresh: Callable[[], None],
        x: int = 60,
        y: int = 120,
    ) -> None:
        self._on_submit = on_submit
        self._on_refresh = on_refresh

        # Window setup
        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.geometry(f"+{x}+{y}")

        # Initialize UI View
        self._view = OverlayView(self._root)
        self._offset: tuple[int, int] = (0, 0)

        self._bind_events()
        self._keep_responsive()
        self.show_waiting()

    def _bind_events(self) -> None:
        # Buttons
        self._view.close_btn.bind("<Button-1>", lambda e: self.close())
        self._view.refresh_btn.bind("<Button-1>", lambda e: self._on_refresh())

        # Inputs
        self._view.entry.bind("<Return>", self._submit)
        self._root.bind("<Escape>", lambda e: self.close())

        # Dragging
        for w in self._view.draggable_areas:
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

    def _submit(self, _event: "tk.Event") -> None:
        name = self._view.entry.get().strip()
        if name:
            self._on_submit(name)
        self._view.entry.delete(0, "end")

    # -- Thread-safe State Updates --
    def show_waiting(self) -> None:
        self._root.after(0, self._view.show_waiting)

    def set_player(self, rec: Record) -> None:
        self._root.after(0, lambda: self._view.show_player(rec))

    def set_status(self, name: str, message: str) -> None:
        self._root.after(0, lambda: self._view.show_status(name, message))

    # -- Window Dragging --
    def _start_drag(self, event: "tk.Event") -> None:
        self._offset = (
            event.x_root - self._root.winfo_x(),
            event.y_root - self._root.winfo_y(),
        )

    def _on_drag(self, event: "tk.Event") -> None:
        x, y = event.x_root - self._offset[0], event.y_root - self._offset[1]
        self._root.geometry(f"+{x}+{y}")

    # -- Lifecycle --
    def _keep_responsive(self) -> None:
        self._root.after(200, self._keep_responsive)

    def close(self) -> None:
        self._root.after(0, self._root.destroy)

    def run(self) -> None:
        self._root.mainloop()
