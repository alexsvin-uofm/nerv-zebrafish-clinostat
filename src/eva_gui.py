"""
eva_gui.py — NERV / MAGI Desktop Window for the Bubble-Free Zebrafish Simulator
===============================================================================
Opens a standalone native computer window using Python's built-in `tkinter` library.
Why Tkinter Canvas instead of basic terminal printouts?
- Every Mac/Windows/Linux Python install includes it out of the box (no heavy game engines).
- Gives you a crisp black CRT window with glowing Evangelion amber/neon-green/magenta ASCII
  graphics, scanlines, warning hex-banners, and real clickable tactical buttons!
"""

import math
import tkinter as tk
from src.physics import NoBubbleClinostatSim, SimConfig

# Neon Genesis Evangelion / MAGI Color Palette
BG_BLACK = "#07080c"
PANEL_BG = "#0d1017"
EVA_ORANGE = "#ff8c00"
EVA_AMBER = "#ffb703"
EVA_GREEN = "#39ff14"
EVA_MAGENTA = "#ff0055"
EVA_CYAN = "#00f5d4"
EVA_PURPLE = "#9d4edd"
DIM_GRID = "#232936"


class MagiDesktopApp:
    """Main NERV-styled desktop window with ASCII viewports and clickable controls."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MAGI // PROJECT DANIO-00 : NO-BUBBLE CLINOSTAT SIMULATOR [ZHU LAB]")
        self.root.configure(bg=BG_BLACK)
        self.root.geometry("1180x760")
        self.root.minsize(1060, 700)

        self.sim = NoBubbleClinostatSim(SimConfig())
        self.running = False
        self.time_warp = 10.0   # 10x real-time by default so you can see drift & g-averaging fast!

        self._build_layout()
        self._refresh_labels()
        self._tick()

    def _build_layout(self):
        # Top NERV Tactical Header Banner
        header = tk.Frame(self.root, bg=BG_BLACK, highlightbackground=EVA_ORANGE, highlightthickness=2)
        header.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(
            header,
            text=" ◢◤ NERV BIO-FLUIDICS // MAGI-01 (MELCHIOR) // ZERO-HEADSPACE ZEBRAFISH CLINOSTAT ",
            bg=BG_BLACK, fg=EVA_ORANGE, font=("Courier", 13, "bold"), anchor="w"
        ).pack(side="left", padx=6, pady=5)

        self.status_banner = tk.Label(
            header,
            text="[ CONDITION: STANDBY // DEGASSED MEDIA VERIFIED ]",
            bg=BG_BLACK, fg=EVA_GREEN, font=("Courier", 11, "bold"), anchor="e"
        )
        self.status_banner.pack(side="right", padx=10, pady=5)

        # Main split container: Left = ASCII CRT Display, Right = Clickable Tactical Controls
        body = tk.Frame(self.root, bg=BG_BLACK)
        body.pack(fill="both", expand=True, padx=10, pady=6)

        # Left ASCII Viewport ( rendered on a high-contrast monospace grid )
        left_frame = tk.Frame(body, bg=PANEL_BG, highlightbackground=EVA_ORANGE, highlightthickness=1)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.ascii_canvas = tk.Canvas(left_frame, bg=BG_BLACK, highlightthickness=0)
        self.ascii_canvas.pack(fill="both", expand=True, padx=6, pady=6)

        # Right Control & Telemetry Deck
        right_frame = tk.Frame(body, bg=PANEL_BG, width=370, highlightbackground=EVA_ORANGE, highlightthickness=1)
        right_frame.pack(side="right", fill="y")
        right_frame.pack_propagate(False)

        tk.Label(
            right_frame, text="━━ TACTICAL COMMAND DECK ━━",
            bg=PANEL_BG, fg=EVA_AMBER, font=("Courier", 12, "bold")
        ).pack(pady=(10, 6))

        # Start / Stop / Reset Buttons
        btn_row = tk.Frame(right_frame, bg=PANEL_BG)
        btn_row.pack(fill="x", padx=12, pady=4)

        self.btn_toggle = self._make_eva_button(
            btn_row, "▶ LAUNCH SIM", self.toggle_run, fg=EVA_GREEN, border=EVA_GREEN
        )
        self.btn_toggle.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._make_eva_button(
            btn_row, "⟲ RESET TUBE", self.reset_sim, fg=EVA_CYAN, border=EVA_CYAN
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Quick Lab Presets (Awesome for showing labmates the 3.0/3.0 RPM phase-lock trap!)
        preset_row = tk.Frame(right_frame, bg=PANEL_BG)
        preset_row.pack(fill="x", padx=12, pady=(4, 8))

        self._make_eva_button(
            preset_row, "⚡ OPTIMAL (3.0 / 2.61)", self.preset_optimal, fg=EVA_ORANGE, border=EVA_ORANGE
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._make_eva_button(
            preset_row, "⚠ PHASE-LOCK TRAP (3/3)", self.preset_trap, fg=EVA_MAGENTA, border=EVA_MAGENTA
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Parameter Stepper Controls (Clickable [-] / [+] buttons for crisp lab tweaking)
        self.lbl_vars = {}
        self._add_stepper(right_frame, "OUTER FRAME [RPM]", "rpm_frame", -0.10, +0.10, "{:.2f} RPM")
        self._add_stepper(right_frame, "INNER CORE  [RPM]", "rpm_core", -0.05, +0.05, "{:.2f} RPM")
        self._add_stepper(right_frame, "METHYLCELLULOSE", "mc_percent", -0.25, +0.25, "{:.2f} % w/v")
        self._add_stepper(right_frame, "RACK OFFSET [CM]", "rack_offset_cm", -0.50, +0.50, "{:.1f} cm")
        self._add_warp_stepper(right_frame)

        # Live MAGI Telemetry Readouts
        tk.Label(
            right_frame, text="━━ MAGI LIVE TELEMETRY ━━",
            bg=PANEL_BG, fg=EVA_AMBER, font=("Courier", 12, "bold")
        ).pack(pady=(12, 4))

        self.telemetry_box = tk.Label(
            right_frame, text="", justify="left", anchor="nw",
            bg="#050608", fg=EVA_GREEN, font=("Courier", 10, "bold"),
            padx=10, pady=8, highlightbackground=DIM_GRID, highlightthickness=1
        )
        self.telemetry_box.pack(fill="both", expand=True, padx=12, pady=(2, 12))

    def _make_eva_button(self, parent, text, cmd, fg=EVA_ORANGE, border=EVA_ORANGE):
        return tk.Button(
            parent, text=text, command=cmd,
            bg="#151924", fg=fg, activebackground=fg, activeforeground="#000000",
            font=("Courier", 9, "bold"), relief="flat", bd=0,
            highlightbackground=border, highlightthickness=1, padx=6, pady=6, cursor="hand2"
        )

    def _add_stepper(self, parent, title, attr_name, step_down, step_up, fmt):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill="x", padx=12, pady=3)

        tk.Label(row, text=title, bg=PANEL_BG, fg="#cbd5e1", font=("Courier", 9, "bold"), anchor="w").pack(fill="x")
        ctrl = tk.Frame(row, bg=PANEL_BG)
        ctrl.pack(fill="x", pady=1)

        self._make_eva_button(ctrl, " [ - ] ", lambda: self._adjust_param(attr_name, step_down)).pack(side="left")
        val_lbl = tk.Label(ctrl, text="", bg="#07090e", fg=EVA_CYAN, font=("Courier", 10, "bold"), pady=4)
        val_lbl.pack(side="left", fill="x", expand=True, padx=4)
        self._make_eva_button(ctrl, " [ + ] ", lambda: self._adjust_param(attr_name, step_up)).pack(side="right")

        self.lbl_vars[attr_name] = (val_lbl, fmt)

    def _add_warp_stepper(self, parent):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill="x", padx=12, pady=3)

        tk.Label(row, text="TIME WARP MULTIPLIER", bg=PANEL_BG, fg="#cbd5e1", font=("Courier", 9, "bold"), anchor="w").pack(fill="x")
        ctrl = tk.Frame(row, bg=PANEL_BG)
        ctrl.pack(fill="x", pady=1)

        self._make_eva_button(ctrl, " [ ÷2 ] ", lambda: self._set_warp(0.5)).pack(side="left")
        self.lbl_warp = tk.Label(ctrl, text="10x REALTIME", bg="#07090e", fg=EVA_AMBER, font=("Courier", 10, "bold"), pady=4)
        self.lbl_warp.pack(side="left", fill="x", expand=True, padx=4)
        self._make_eva_button(ctrl, " [ ×2 ] ", lambda: self._set_warp(2.0)).pack(side="right")

    def _adjust_param(self, attr_name, delta):
        val = getattr(self.sim.cfg, attr_name) + delta
        bounds = {
            "rpm_frame": (0.0, 20.0),
            "rpm_core": (0.0, 20.0),
            "mc_percent": (0.5, 4.0),
            "rack_offset_cm": (0.0, 8.0),
        }
        lo, hi = bounds[attr_name]
        setattr(self.sim.cfg, attr_name, max(lo, min(hi, round(val, 3))))
        # Reset cumulative g-average if motor speeds changed so user sees fresh convergence
        if attr_name in ("rpm_frame", "rpm_core"):
            self.sim.g_Accumulator[:] = 0.0
            self.sim.g_samples = 0
        self._refresh_labels()

    def _set_warp(self, factor):
        self.time_warp = max(1.0, min(512.0, round(self.time_warp * factor)))
        self._refresh_labels()

    def _refresh_labels(self):
        for attr_name, (lbl, fmt) in self.lbl_vars.items():
            lbl.config(text=fmt.format(getattr(self.sim.cfg, attr_name)))
        self.lbl_warp.config(text=f"{int(self.time_warp)}x REALTIME")

    def toggle_run(self):
        self.running = not self.running
        if self.running:
            self.btn_toggle.config(text="⏸ PAUSE SIM", fg=EVA_AMBER)
            self.status_banner.config(text="[ PATTERN BLUE // SIMULATION ACTIVE ]", fg=EVA_GREEN)
        else:
            self.btn_toggle.config(text="▶ RESUME SIM", fg=EVA_GREEN)
            self.status_banner.config(text="[ SIMULATION PAUSED // HOLDING ]", fg=EVA_AMBER)

    def reset_sim(self):
        self.sim.reset()
        self.status_banner.config(text="[ TUBE RE-CENTERED // ZERO HEADSPACE ]", fg=EVA_CYAN)

    def preset_optimal(self):
        self.sim.cfg.rpm_frame = 3.00
        self.sim.cfg.rpm_core = 2.61
        self.sim.reset()
        self._refresh_labels()

    def preset_trap(self):
        """Demonstrates why 3.00 / 3.00 RPM fails to zero out gravity!"""
        self.sim.cfg.rpm_frame = 3.00
        self.sim.cfg.rpm_core = 3.00
        self.sim.reset()
        self._refresh_labels()

    # -----------------------------------------------------------------
    # ASCII EVANGELION VIEWPORT RENDERER
    # -----------------------------------------------------------------
    def _build_ascii_grid(self, cols=74, rows=32):
        """Builds a 2D character + color tag grid showing the Eppendorf tube & CoSE rings."""
        grid = [[" " for _ in range(cols)] for _ in range(rows)]
        colors = [[DIM_GRID for _ in range(cols)] for _ in range(rows)]

        def put_str(r, c, s, col):
            if 0 <= r < rows:
                for idx, ch in enumerate(s):
                    if 0 <= c + idx < cols:
                        grid[r][c + idx] = ch
                        colors[r][c + idx] = col

        # Subtle MAGI targeting reticle background
        for r in range(1, rows - 1):
            for c in range(2, cols - 2):
                if r % 6 == 0 and c % 12 == 0:
                    grid[r][c] = "+"
                    colors[r][c] = "#1b2230"

        # ── LEFT HALF: 1.5 mL Conical Eppendorf Cross-Section (X-Z Plane, Zoomed) ──
        tube_cx = 22
        put_str(1, 5, "◢ TUBE MICRO-TRACKER (X-Z) ◣", EVA_ORANGE)
        put_str(2, 6, "[NO-BUBBLE SINGLE PHASE]", EVA_CYAN)

        # Draw snap-cap at top (z = +18 mm -> row 4) and conical tip at bottom (z = -20 mm -> row 28)
        put_str(3, tube_cx - 12, "╔═══════════════════════╗", EVA_ORANGE)
        for r in range(4, 29):
            # Map row 4..28 -> z_mm +18..-20
            frac_down = (r - 4) / 24.0
            z_mm = 18.0 - frac_down * 38.0
            r_mm = self.sim.tube_inner_radius_m(z_mm * 1e-3) * 1e3
            half_w = max(2, int(round((r_mm / 5.0) * 10)))

            # Fill degassed methylcellulose interior with faint viscosity dots
            for cc in range(tube_cx - half_w + 1, tube_cx + half_w):
                if (r + cc) % 5 == 0:
                    grid[r][cc] = "·"
                    colors[r][cc] = "#16292a"

            wall_ch = "║" if z_mm > -2.0 else ("╲" if False else "│")
            left_ch = "║" if z_mm > -2.0 else "╲"
            right_ch = "║" if z_mm > -2.0 else "╱"
            grid[r][tube_cx - half_w] = left_ch
            colors[r][tube_cx - half_w] = EVA_ORANGE
            grid[r][tube_cx + half_w] = right_ch
            colors[r][tube_cx + half_w] = EVA_ORANGE

        put_str(29, tube_cx - 2, "╰───╯", EVA_ORANGE)

        # Plot fish drift trail in purple/cyan
        for tx_mm, _, tz_mm in self.sim.trail_mm:
            tc = tube_cx + int(round((tx_mm / 5.0) * 10))
            tr = 4 + int(round(((18.0 - tz_mm) / 38.0) * 24))
            if 4 <= tr <= 28 and 2 <= tc < 42:
                grid[tr][tc] = "∙"
                colors[tr][tc] = EVA_PURPLE

        # Plot the Larval Zebrafish in ASCII!
        fx_mm, fy_mm, fz_mm = self.sim.pos * 1e3
        fc = tube_cx + int(round((fx_mm / 5.0) * 10))
        fr = 4 + int(round(((18.0 - fz_mm) / 38.0) * 24))
        fish_col = EVA_MAGENTA if (self.sim.wall_hit or self.sim.shear_mpa >= 25.0) else EVA_GREEN
        # Vertical 3-char larva (head with eyes °▲°, yolk █, tail ▾)
        put_str(fr - 1, fc - 1, "°▲°", fish_col)
        put_str(fr,     fc,     "█",   fish_col)
        put_str(fr + 1, fc,     "▾",   fish_col)

        # ── RIGHT TOP: 2-Axis CoSE Gimbal Gyroscope & Gravity Vector ──
        gx_center, gy_center = 56, 10
        put_str(1, 43, "◢ CoSE 2-AXIS GYRO & g(t) ◣", EVA_ORANGE)

        w1 = self.sim.cfg.rpm_frame * 2 * math.pi / 60.0
        w2 = self.sim.cfg.rpm_core * 2 * math.pi / 60.0
        a1, a2 = w1 * self.sim.t, w2 * self.sim.t

        # Outer gimbal ring (ASCII ellipse)
        for deg in range(0, 360, 12):
            rad = math.radians(deg)
            ox = int(round(gx_center + 12 * math.cos(rad)))
            oy = int(round(gy_center + 5.5 * math.sin(rad) * math.cos(a1)))
            if 3 <= oy <= 17 and 42 <= ox < cols - 2:
                grid[oy][ox] = "◎" if deg % 90 == 0 else "○"
                colors[oy][ox] = EVA_AMBER

        # Inner core ring (orthogonal tumbling ASCII ellipse)
        for deg in range(0, 360, 15):
            rad = math.radians(deg)
            ix = int(round(gx_center + 8.5 * math.cos(rad) * math.cos(a2)))
            iy = int(round(gy_center + 4.0 * math.sin(rad)))
            if 3 <= iy <= 17 and 42 <= ix < cols - 2:
                grid[iy][ix] = "•"
                colors[iy][ix] = EVA_CYAN

        # Live tumbling gravity vector arrow inside tube frame
        gx_u, _, gz_u = self.sim.g_tube_unit
        for step_i in range(1, 6):
            ac = int(round(gx_center + gx_u * step_i * 1.8))
            ar = int(round(gy_center - gz_u * step_i * 0.9))
            if 3 <= ar <= 17 and 42 <= ac < cols - 2:
                grid[ar][ac] = "★" if step_i == 5 else "═"
                colors[ar][ac] = EVA_MAGENTA
        put_str(gy_center, gx_center, "⊕", EVA_GREEN)

        # ── RIGHT BOTTOM: Lateral-Line Shear & Micro-g Convergence Bars ──
        put_str(19, 43, "◢ NEUROMAST SHEAR ENVELOPE ◣", EVA_ORANGE)
        # Log bar from 0.01 mPa to 10 mPa (1 mPa hair-cell threshold marked!)
        log_tau = math.log10(max(0.1, min(100.0, self.sim.shear_mpa)))
        bar_len = int(round(((log_tau + 1.0) / 3.0) * 24))
        bar_col = EVA_GREEN if self.sim.shear_mpa < 15.0 else EVA_MAGENTA
        put_str(21, 44, "[" + "█" * bar_len + "░" * (24 - bar_len) + "]", bar_col)
        put_str(22, 44, "0.1        1.0     10     100mPa", "#94a3b8")

        put_str(25, 43, "◢ VECTOR-AVERAGED |<g>| ◣", EVA_ORANGE)
        log_g = math.log10(max(1e-4, min(1.0, self.sim.g_avg_mag)))
        gbar_len = int(round(((log_g + 4.0) / 4.0) * 24))
        g_col = EVA_GREEN if self.sim.g_avg_mag < 0.02 else (EVA_AMBER if self.sim.g_avg_mag < 0.2 else EVA_MAGENTA)
        put_str(27, 44, "[" + "█" * gbar_len + "░" * (24 - gbar_len) + "]", g_col)
        put_str(28, 44, "10⁻⁴g    10⁻²g    10⁻¹g    1g", "#94a3b8")

        # Warning flash if user triggered the 3.0/3.0 phase lock or hit wall!
        if self.sim.wall_hit:
            put_str(30, 6, "▒▒ WARNING: LARVA CONTACTED EPPENDORF WALL! INCREASE MC% OR CENTER TUBE ▒▒", EVA_MAGENTA)
        elif abs(self.sim.cfg.rpm_frame - self.sim.cfg.rpm_core) < 0.02 and self.sim.cfg.rpm_frame > 0:
            put_str(30, 6, "▒▒ MAGI ALERT: EQUAL RPM PHASE-LOCK DETECTED! |<g>| WILL NOT ZERO OUT! ▒▒", EVA_MAGENTA)
        else:
            put_str(30, 6, "── CREEPING STOKES REGIME LOCKED (Re << 1) // ZERO AIR HEADSPACE ──", EVA_GREEN)

        return grid, colors

    def _draw_canvas_And_telemetry(self):
        self.ascii_canvas.delete("all")
        w = max(600, self.ascii_canvas.winfo_width())
        h = max(480, self.ascii_canvas.winfo_height())

        grid, colors = self._build_ascii_grid()
        rows, cols = len(grid), len(grid[0])
        cell_w = w / cols
        cell_h = h / rows

        # Batch contiguous same-color characters on each row so Tkinter renders blazingly fast
        for r in range(rows):
            c = 0
            while c < cols:
                col = colors[r][c]
                start_c = c
                chars = []
                while c < cols and colors[r][c] == col:
                    chars.append(grid[r][c])
                    c += 1
                segment = "".join(chars)
                if segment.strip():
                    x_px = (start_c + len(segment) / 2.0) * cell_w
                    y_px = (r + 0.5) * cell_h
                    self.ascii_canvas.create_text(
                        x_px, y_px, text=segment, fill=col, font=("Courier", 11, "bold")
                    )

        # Subtle CRT horizontal scanline overlay
        for y_line in range(0, int(h), 4):
            self.ascii_canvas.create_line(0, y_line, w, y_line, fill="#040507")

        # Update right-hand numeric telemetry readout
        mins, secs = divmod(int(self.sim.t), 60)
        hrs, mins = divmod(mins, 60)
        fx, fy, fz = self.sim.pos * 1e3
        drift_um = math.hypot(fx, fy, fz) * 1000.0
        eta = self.sim.cfg.eta_zero
        lat_status = "QUIET (SUB-BUBBLE)" if self.sim.shear_mpa < 20.0 else "ELEVATED SHEAR"

        telem_text = (
            f"SIMULATED TIME : {hrs:02d}h {mins:02d}m {secs:02d}s
"
            f"MEDIA VISCOSITY: {eta:.2f} Pa·s
"
            f"─────────────────────────────────
"
            f"FISH POS (X,Y) : {fx:+.3f}, {fy:+.3f} mm
"
            f"FISH POS (Z)   : {fz:+.3f} mm
"
            f"NET 3D DRIFT   : {drift_um:.1f} µm
"
            f"WALL CLEARANCE : {self.sim.wall_clearance_mm:.2f} mm
"
            f"─────────────────────────────────
"
            f"CUMULATIVE |<g>|: {self.sim.g_avg_mag:.4f} g
"
            f"SKIN SHEAR     : {self.sim.shear_mpa:.3f} mPa
"
            f"LATERAL LINE   : {lat_status}
"
            f"WALL COLLISION : {'YES (BOUNDARY)' if self.sim.wall_hit else 'NONE'}"
        )
        self.telemetry_box.config(
            text=telem_text,
            fg=EVA_MAGENTA if self.sim.wall_hit else EVA_GREEN
        )

    def _tick(self):
        if self.running:
            # Step in small chunks if time_warp is huge so physics stays accurate
            total_dt = 0.04 * self.time_warp
            n_sub = max(1, int(math.ceil(total_dt / 0.5)))
            sub_dt = total_dt / n_sub
            for _ in range(n_sub):
                self.sim.step(sub_dt)

        self._draw_canvas_And_telemetry()
        self.root.after(40, self._tick)  # ~25 FPS smooth CRT refresh


def launch_desktop_window():
    root = tk.Tk()
    MagiDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_desktop_window()
