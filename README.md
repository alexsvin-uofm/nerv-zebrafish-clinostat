# ◢◤ NERV // DANIO-00 : Bubble-Free Zebrafish Clinostat Simulator

A pure-Python physics engine + **Neon Genesis Evangelion (MAGI)** ASCII tactical interface for simulating a larval zebrafish (*Danio rerio*, 4–7 dpf) inside a degassed (bubble-free) 1.5 mL conical Eppendorf tube mounted on a **2-axis CoSE clinostat** filled with methylcellulose.

Built with plain-English, lab-friendly comments so anyone in the lab can read, tweak, or defend every equation in lab meeting.

---

## Desktop Window vs. Web View — You Get Both!
- **Native Computer Window (`python main.py`)**: Uses Python's built-in `tkinter` canvas to pop open a dark CRT window with glowing Evangelion ASCII graphics and clickable tactical buttons. Zero complex GUI libraries required—just `numpy`!
- **Instant Browser / GitHub Pages View (`web/index.html`)**: Double-click `web/index.html` (or enable **GitHub Pages** on the `/web` or root folder) so PIs and labmates can click around in a browser without even having Python installed.

---

## Quick Start (Run in 30 Seconds)

```bash
# 1. Clone your new repo
git clone https://github.com/<your-username>/nerv-zebrafish-clinostat.git
cd nerv-zebrafish-clinostat

# 2. Install numpy (the ONLY external dependency!)
pip install -r requirements.txt

# 3. Pop open the Evangelion ASCII Desktop Window
python main.py
```

Want a quick 24-hour batch printout in the terminal without opening a window?
```bash
python main.py --headless --hours 24.0 --rpm-frame 3.00 --rpm-core 2.61 --mc 2.0 --offset 2.0
```

---

## Cool Lab Experiments to Try Right Away
1. **The 3.00 / 3.00 RPM Phase-Lock Trap**: Click the magenta **`⚠ PHASE-LOCK TRAP (3/3)`** button. Watch the `|<g>|` bar freeze near **0.5g** and trigger a MAGI alert! When both axes turn at the exact same speed, they trace a closed figure-8 and fail to average out gravity, marching the larva straight into the Eppendorf wall. Click **`⚡ OPTIMAL (3.0 / 2.61)`** to watch `|<g>|` plunge below `0.01g`.
2. **Tube Rack Slot Offset (`RACK OFFSET [CM]`)**: Crank Time Warp to `128x` and move the rack offset from `0.5 cm` out to `6.5 cm` (outer edge of the CoSE stage). Watch centrifugal drift slowly push the denser larva toward the wall—then raise `METHYLCELLULOSE` from `1.5%` to `2.5%` to arrest the drift!
3. **Lateral-Line Mechanosensory Check**: Notice that in a bubble-free tube at ~3 RPM, skin shear stays peacefully around **~0.15–0.30 mPa**—well below the ~1 mPa neuromast hair-cell firing threshold.

---

## Areas Marked in Code for Lab Refinement (`src/physics.py`)
Search `src/physics.py` for `[REFINEMENT AREA]` tags where your lab can plug in wet-lab measurements:
1. **`[REFINEMENT AREA 1]` — Larval Tissue & Swim-Bladder Density (`rho_fish`)**: Measure settling speed of your exact age group (e.g., 30–66 hpf embryos vs. 6.5 dpf larvae with/without inflated swim bladders) in stationary 1g media to lock in `rho_fish`.
2. **`[REFINEMENT AREA 2]` — Batch-Specific Methylcellulose Rheology (`eta_zero`)**: Different Sigma/Fisher catalog molecular weights vary widely at 2% w/v. Swap the exponential curve with a 3-point viscometer fit for your exact stock bottle.
3. **`[REFINEMENT AREA 3]` — 6-DOF Jeffery Orbits (Body Tumbling)**: Currently models the fish aligned along the tube axis using analytical Perrin ellipsoidal Stokes drag. Can be expanded with a quaternion to track slow rotational tumbling.
4. **`[REFINEMENT AREA 4]` — Carreau-Yasuda Shear Thinning**: Unnecessary at 3 RPM (shear rate $\sim 10^{-3}\text{ s}^{-1}$ sits purely on the zero-shear plateau), but marked right where to drop it in if you test fast $>30\text{ RPM}$ profiles.
5. **`[REFINEMENT AREA 5]` — Active SAMPL Swim Bouts**: Ready hook for injecting stochastic 20 Hz larval tail-beat impulses if testing unanesthetized older larvae in lower-viscosity media.

---

## Push This Folder to Your Own GitHub Repo
```bash
cd nerv-zebrafish-clinostat
git init
git add .
git commit -m "Initial commit: NERV MAGI No-Bubble Zebrafish Clinostat Simulator"
git branch -M main
git remote add origin https://github.com/<your-username>/nerv-zebrafish-clinostat.git
git push -u origin main
```
