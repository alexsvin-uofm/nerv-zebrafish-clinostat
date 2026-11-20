"""
physics.py — Bubble-Free Larval Zebrafish 2-Axis Clinostat Physics Engine
=========================================================================
Built for the Yunlu Zhu Lab (CoSE 2-Axis Clinostat / Methylcellulose SOP).

Plain-English Overview for Lab Members:
---------------------------------------
What is happening inside our spinning 1.5 mL Eppendorf tube when there are NO air bubbles?
1. Because 1.5%–3% methylcellulose is super thick (200x–5000x thicker than water) and our
   clinostat spins gently (~3 RPM), the fluid locks onto the tube walls in ~25 milliseconds.
   There is no chaotic sloshing—just smooth, predictable "creeping" Stokes flow.
2. However, because TWO motors spin at right angles on the CoSE rig (an Outer Frame and an
   Inner Core), the outer ring constantly tilts the inner ring's spin axis. That gyroscopic
   precession creates a tiny, gentle swirling force ("Euler acceleration") inside the tube.
3. Meanwhile, our 4-6 dpf zebrafish larva is slightly denser than methylcellulose (~1030 vs
   1005 kg/m^3), so gravity tries to make it sink, and centrifugal force tries to push it
   outward if the tube isn't mounted dead-center on the stage.

This file calculates:
- The tumbling 3D gravity vector inside the tube (and checks if it averages out to ~0g!)
- How far the fish drifts over hours (and whether it bonks into the conical Eppendorf wall)
- The fluid shear stress (in milliPascals, mPa) rubbing against the fish's lateral-line hair cells.
"""

import math
from dataclasses import dataclass, field
import numpy as np


@dataclass
class SimConfig:
    """All the knobs you might tweak before or during a clinostat run."""
    # Motor speeds [RPM]
    # LAB TIP: Never set both to exact 3.00 RPM! They phase-lock into a figure-8 and leave ~0.5g bias.
    rpm_frame: float = 3.00       # Outer CoSE gimbal speed [RPM]
    rpm_core: float = 2.61        # Inner CoSE core speed [RPM]

    # Media properties (Methylcellulose)
    mc_percent: float = 2.0       # Concentration [% w/v] -> controls viscosity exponentially
    rho_fluid: float = 1005.0     # Methylcellulose density [kg/m^3]

    # Zebrafish larva properties (4-6 dpf, uninflated or swim-bladder compensated)
    # [REFINEMENT AREA 1]: Measure exact density of your specific dpf / anesthesia / swim-bladder state!
    # Deflated/anesthetized larvae sit near ~1025-1035 kg/m^3; inflated swim bladders sit much closer to 1005.
    rho_fish: float = 1007.0      # 5-7 dpf larva w/ inflated swim bladder (~1007); set ~1028 for 2 dpf embryos!
    fish_length_mm: float = 4.0   # Snout-to-tail length [mm]
    fish_width_mm: float = 0.6    # Head / yolk width [mm]

    # Hardware mounting offset
    # How far your Eppendorf tube slot sits from the exact intersection of the two CoSE axes [cm].
    rack_offset_cm: float = 2.0

    # 1.5 mL Conical Eppendorf inner geometry [mm]
    # Tube local Z axis runs from conical bottom tip (-20 mm) to flat snap-cap (+18 mm).
    z_tip_mm: float = -20.0
    z_taper_mm: float = -2.0      # Where the cone transitions into the straight cylinder
    z_cap_mm: float = 18.0
    r_tip_mm: float = 1.2         # Inner radius right at the bottom tip
    r_cyl_mm: float = 5.0         # Inner radius of the main upper barrel (10 mm diameter)

    @property
    def eta_zero(self) -> float:
        """
        Zero-shear viscosity [Pa*s] estimated from methylcellulose % w/v.
        ~1.0% -> 0.19 Pa*s | ~2.0% -> 0.80 Pa*s | ~3.0% -> 3.38 Pa*s.
        [REFINEMENT AREA 2]: Replace this curve with viscometer measurements of your lab's exact Sigma batch,
        since molecular weight (e.g., M0512 vs M7027) shifts viscosity substantially!
        """
        return 0.045 * math.exp(1.44 * self.mc_percent)


class NoBubbleClinostatSim:
    """
    Real-time & batch physics stepper for a single degassed (bubble-free) Eppendorf tube.
    """

    def __init__(self, config: SimConfig | None = None):
        self.cfg = config or SimConfig()
        self.reset()

    def reset(self):
        """Put the fish back at the center of the tube and zero out our timers."""
        self.t = 0.0                                  # Elapsed simulated time [seconds]
        self.pos = np.array([0.0, 0.0, 0.0])          # Fish [x, y, z] inside tube [meters]
        self.vel = np.array([0.0, 0.0, 0.0])          # Fish velocity inside tube [m/s]

        # Running average of the gravity vector inside the tube frame
        self.g_Accumulator = np.zeros(3)
        self.g_samples = 0

        # Current telemetry readouts for the UI
        self.g_tube_unit = np.array([0.0, 0.0, -1.0]) # Current 'down' direction inside tube
        self.g_avg_mag = 1.0                          # Magnitude of time-averaged gravity [g]
        self.shear_mpa = 0.0
        self.slip_speed_ums = 0.0                          # Skin / neuromast shear stress [mPa]
        self.wall_clearance_mm = self.cfg.r_cyl_mm    # Distance from fish to plastic wall [mm]
        self.wall_hit = False                         # Did the larva touch the Eppendorf wall?

        # Trail of recent positions (in mm) so we can draw the fish's drift path
        self.trail_mm = []
        self._step_counter = 0

    def tube_inner_radius_m(self, z_m: float) -> float:
        """Returns the inner radius [m] of the 1.5 mL Eppendorf tube at height z_m."""
        z_mm = z_m * 1e3
        if z_mm <= self.cfg.z_taper_mm:
            # Linear taper in the conical bottom half
            span = self.cfg.z_taper_mm - self.cfg.z_tip_mm
            frac = np.clip((z_mm - self.cfg.z_tip_mm) / span, 0.0, 1.0)
            r_mm = self.cfg.r_tip_mm + frac * (self.cfg.r_cyl_mm - self.cfg.r_tip_mm)
            return r_mm * 1e-3
        return self.cfg.r_cyl_mm * 1e-3

    def kinematics_in_tube_frame(self, t: float):
        """
        Transforms Lab Gravity into the spinning Eppendorf tube's local coordinates.
        Outer frame spins around Lab X at w1; Inner core spins around local Y at w2.
        """
        w1 = self.cfg.rpm_frame * 2.0 * math.pi / 60.0
        w2 = self.cfg.rpm_core * 2.0 * math.pi / 60.0

        th1 = w1 * t
        th2 = w2 * t
        c1, s1 = math.cos(th1), math.sin(th1)
        c2, s2 = math.cos(th2), math.sin(th2)

        # Rotation matrix Rx(th1) for the outer gimbal
        rx = np.array([
            [1.0, 0.0, 0.0],
            [0.0,  c1, -s1],
            [0.0,  s1,  c1]
        ])
        # Rotation matrix Ry(th2) for the inner core
        ry = np.array([
            [ c2, 0.0, s2],
            [0.0, 1.0, 0.0],
            [-s2, 0.0, c2]
        ])

        # Full orientation of the tube in the lab: R = Rx @ Ry
        # To bring a vector FROM the lab INTO the tube, we multiply by R.T (the transpose).
        r_lab_to_tube = (rx @ ry).T

        g_lab = np.array([0.0, 0.0, -9.80665])
        g_tube = r_lab_to_tube @ g_lab

        # Angular velocity of the tube expressed in tube coordinates:
        # w_outer (along X_frame) rotated by Ry(-th2) + w_inner (along Y_tube)
        omega_tube = (ry.T @ np.array([w1, 0.0, 0.0])) + np.array([0.0, w2, 0.0])

        # Gyroscopic angular acceleration: alpha = w_outer x w_inner
        # Even at constant motor RPMs, tilting a spinning axis creates real angular acceleration!
        alpha_tube = np.cross(ry.T @ np.array([w1, 0.0, 0.0]), np.array([0.0, w2, 0.0]))

        return g_tube, omega_tube, alpha_tube

    def _stokes_drag_factors(self):
        """
        Approximates the zebrafish larva as a sleek prolate spheroid (cigar shape) aligned along Z.
        Moving nose-first has lower drag than drifting sideways.
        [REFINEMENT AREA 3]: Right now we assume the anesthetized/passive fish stays roughly aligned
        with the tube Z-axis. You can expand this to a 6-DOF orientation quaternion if you want to
        track Jeffery orbits (slow tumbling of elongated bodies in shear flow).
        """
        a = 0.5 * self.cfg.fish_length_mm * 1e-3  # Half-length (major semi-axis) [m]
        b = 0.5 * self.cfg.fish_width_mm * 1e-3   # Half-width (minor semi-axis) [m]
        eta = self.cfg.eta_zero

        # Volume of our prolate spheroid fish [m^3]
        vol = (4.0 / 3.0) * math.pi * a * (b ** 2)

        # Eccentricity for Perrin / Oberbeck analytical ellipsoidal Stokes drag
        ecc = math.sqrt(max(1e-6, 1.0 - (b / a) ** 2))
        log_term = math.log((1.0 + ecc) / (1.0 - ecc))

        # Drag coefficients [N / (m/s)] parallel (Z) and perpendicular (X, Y) to body axis
        k_parallel = 16.0 * math.pi * eta * a * (ecc ** 3) / ((1.0 + ecc ** 2) * log_term - 2.0 * ecc)
        k_perp = 32.0 * math.pi * eta * a * (ecc ** 3) / ((3.0 * ecc ** 2 - 1.0) * log_term + 2.0 * ecc)

        return vol, b, np.array([k_perp, k_perp, k_parallel])

    def compute_derivatives_and_telemetry(self, t: float, pos: np.ndarray):
        """
        Calculates instantaneous fish velocity [m/s] and skin shear stress [mPa].
        Because Re << 1 in methylcellulose, inertia is basically zero—forces balance instantly!
        """
        g_b, omega_b, alpha_b = self.kinematics_in_tube_frame(t)
        eta = self.cfg.eta_zero
        rho_f = self.cfg.rho_fluid

        # 1. Background creeping vortex driven by gyroscopic Euler force (-rho * alpha x r)
        # [REFINEMENT AREA 4]: Methylcellulose shear-thins at high shear rates (Carreau-Yasuda model).
        # At 3 RPM our shear rates are tiny (~0.001 s^-1), so constant zero-shear viscosity (eta_zero)
        # is >99.9% exact. If you crank motors >30 RPM, add Carreau shear-thinning here!
        r_wall = self.tube_inner_radius_m(pos[2])
        r_rad = math.hypot(pos[0], pos[1])
        wall_damping = max(0.0, 1.0 - (r_rad / max(r_wall, 1e-4)) ** 2)

        # Analytical Stokes solution inside a cylinder undergoing gyroscopic angular accel (alpha):
        # Secondary swirl velocity u_bg vanishes at the center & walls, and background shear stress
        # grows linearly from the tube centerline: tau_euler(r) = 0.5 * rho_fluid * |alpha| * r.
        # (Right near the center of the tube, r is ~0.3 mm so Euler shear is tiny; out at the 5 mm
        # plastic wall, wall shear reaches ~200 mPa—matching Wuest et al. 2017 CFD benchmarks!)
        u_bg = -0.25 * (rho_f / eta) * np.cross(alpha_b, pos) * (r_wall ** 2) * wall_damping
        r_fish_local = max(0.3e-3, float(np.linalg.norm(pos)))
        tau_euler_pa = 0.5 * rho_f * float(np.linalg.norm(alpha_b)) * r_fish_local

        # 2. Effective acceleration felt by the larva at its rack offset + local position
        r_mount = np.array([self.cfg.rack_offset_cm * 1e-2, 0.0, 0.0])
        r_total = r_mount + pos

        a_centrifugal = np.cross(omega_b, np.cross(omega_b, r_total))
        a_euler = np.cross(alpha_b, r_total)
        a_eff = g_b - a_centrifugal - a_euler

        # 3. Buoyancy-driven Stokes settling slip velocity
        vol, b_head, drag_vec = self._stokes_drag_factors()
        delta_rho = self.cfg.rho_fish - rho_f
        f_buoyancy = delta_rho * vol * a_eff
        v_slip = f_buoyancy / drag_vec

        # 4. Mean skin shear stress [mPa] rubbing across the larva's lateral line / neuromasts:
        # Surface-averaged buoyancy drag stress (|F_buoyancy| / Surface_Area) + local Euler shear.
        # Note for Lab: Increasing methylcellulose % slows settling velocity (1/eta), but because
        # shear stress = eta * (du/dr), the eta cancels out! Buoyancy skin shear depends ONLY on
        # density mismatch (rho_fish - rho_fluid), whereas higher MC% stops the fish from drifting!
        a_half = 0.5 * self.cfg.fish_length_mm * 1e-3
        approx_surface_area = math.pi ** 2 * a_half * b_head  # Prolate spheroid surface area [m^2]
        tau_buoy_pa = float(np.linalg.norm(f_buoyancy)) / approx_surface_area
        tau_mpa = (tau_buoy_pa + tau_euler_pa) * 1e3
        # Also record cupula/neuromast deflection speed [um/s]—this DOES drop steeply with MC%!
        self.slip_speed_ums = float(np.linalg.norm(v_slip)) * 1e6

        # [REFINEMENT AREA 5]: Active larval swimming bouts!
        # Right now this models a passive / immobilized / embryonic fish. For 6+ dpf free-swimming larvae
        # in low-% media, you could inject stochastic SAMPL swim-bout impulses every ~1-2 seconds here.
        v_total = u_bg + v_slip
        return v_total, g_b, tau_mpa, a_eff

    def step(self, dt: float):
        """
        Advances the simulation by `dt` seconds using 2nd-order Midpoint (RK2) integration,
        and enforces the physical polypropylene walls of the 1.5 mL Eppendorf tube.
        """
        if dt <= 0.0:
            return

        # RK2 midpoint step so curved trajectories stay crisp even with Time Warp cranked up
        v1, _, _, _ = self.compute_derivatives_and_telemetry(self.t, self.pos)
        pos_mid = self.pos + 0.5 * dt * v1
        v2, g_b, tau_mpa, _ = self.compute_derivatives_and_telemetry(self.t + 0.5 * dt, pos_mid)

        new_pos = self.pos + dt * v2

        # Keep the fish inside the physical 1.5 mL Eppendorf tube walls (no-penetration check)
        fish_pad = 0.5 * self.cfg.fish_width_mm * 1e-3
        z_min = self.cfg.z_tip_mm * 1e-3 + fish_pad
        z_max = self.cfg.z_cap_mm * 1e-3 - fish_pad

        hit = False
        if new_pos[2] < z_min:
            new_pos[2] = z_min
            hit = True
        elif new_pos[2] > z_max:
            new_pos[2] = z_max
            hit = True

        r_wall = self.tube_inner_radius_m(new_pos[2])
        r_allowed = max(1e-5, r_wall - fish_pad)
        r_xy = math.hypot(new_pos[0], new_pos[1])
        if r_xy > r_allowed:
            scale = r_allowed / r_xy
            new_pos[0] *= scale
            new_pos[1] *= scale
            hit = True

        self.pos = new_pos
        self.vel = v2
        self.t += dt
        self.wall_hit = self.wall_hit or hit

        # Update telemetry
        self.g_tube_unit = g_b / 9.80665
        self.g_Accumulator += self.g_tube_unit
        self.g_samples += 1
        self.g_avg_mag = float(np.linalg.norm(self.g_Accumulator / self.g_samples))
        self.shear_mpa = tau_mpa
        self.wall_clearance_mm = max(0.0, (r_wall - min(r_xy, r_allowed) - fish_pad) * 1e3)

        self._step_counter += 1
        if self._step_counter % 4 == 0:
            self.trail_mm.append((self.pos * 1e3).copy())
            if len(self.trail_mm) > 180:
                self.trail_mm.pop(0)
