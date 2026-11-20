#!/usr/bin/env python3
"""
main.py — Launchpad for the Zhu Lab No-Bubble Zebrafish Clinostat Simulator
===========================================================================
Run normally to pop open the Evangelion ASCII Desktop Window:
    python main.py

Or run a quick 1-hour headless terminal check (great for SSH / quick sanity checks):
    python main.py --headless --hours 1.0
"""

import argparse
from src.physics import NoBubbleClinostatSim, SimConfig


def run_headless(hours: float, rpm_frame: float, rpm_core: float, mc_pct: float, offset_cm: float):
    cfg = SimConfig(
        rpm_frame=rpm_frame,
        rpm_core=rpm_core,
        mc_percent=mc_pct,
        rack_offset_cm=offset_cm,
    )
    sim = NoBubbleClinostatSim(cfg)
    dt = 0.5
    steps = int((hours * 3600.0) / dt)
    for _ in range(steps):
        sim.step(dt)

    drift_mm = (sim.pos[0]**2 + sim.pos[1]**2 + sim.pos[2]**2) ** 0.5 * 1e3
    print("=" * 64)
    print(" MAGI-01 // HEADLESS CLINOSTAT DIAGNOSTIC REPORT (NO BUBBLES)")
    print("=" * 64)
    print(f" Simulated Duration      : {hours:.2f} hours ({rpm_frame:.2f} / {rpm_core:.2f} RPM)")
    print(f" Methylcellulose Media   : {mc_pct:.2f}% w/v (eta_0 = {cfg.eta_zero:.2f} Pa*s)")
    print(f" Rack Mounting Offset    : {offset_cm:.1f} cm from gimbal center")
    print("-" * 64)
    print(f" Residual Vector |<g>|   : {sim.g_avg_mag:.5f} g")
    print(f" Net Larval 3D Drift     : {drift_mm:.3f} mm ({drift_mm*1000:.1f} um)")
    print(f" Remaining Wall Clearance: {sim.wall_clearance_mm:.2f} mm")
    print(f" Larval Skin Shear Stress: {sim.shear_mpa:.2f} mPa  [vs 50-300 mPa RPM wall / bubble spikes]")
    print(f" Neuromast Slip Velocity : {sim.slip_speed_ums:.2f} um/s [Cupula threshold ~10-50 um/s]")
    print(f" Wall Contact Occurred?  : {'YES - WARNING!' if sim.wall_hit else 'NO (Safe)'}")
    print("=" * 64)


def main():
    parser = argparse.ArgumentParser(description="NERV No-Bubble Zebrafish Clinostat Simulator")
    parser.add_argument("--headless", action="store_true", help="Run fast terminal report without opening a GUI window")
    parser.add_argument("--hours", type=float, default=1.0, help="Hours to simulate in headless mode")
    parser.add_argument("--rpm-frame", type=float, default=3.00, help="Outer frame RPM")
    parser.add_argument("--rpm-core", type=float, default=2.61, help="Inner core RPM")
    parser.add_argument("--mc", type=float, default=2.0, help="Methylcellulose concentration (%% w/v)")
    parser.add_argument("--offset", type=float, default=2.0, help="Tube rack offset from center (cm)")
    args = parser.parse_args()

    if args.headless:
        run_headless(args.hours, args.rpm_frame, args.rpm_core, args.mc, args.offset)
    else:
        from src.eva_gui import launch_desktop_window
        launch_desktop_window()


if __name__ == "__main__":
    main()
