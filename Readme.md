# Nevori — bio-adaptive mental recharge

Nevori turns the existing wearable, RMSSD, stress-classifier, and adaptive-audio
prototype into a personal recovery product. The app now uses a focused
three-step journey:

1. A home dashboard with weekly progress, previous sessions, and plain-language
   notes about what the adaptive model has learned.
2. A dedicated device selector and signal-preparation screen supporting Polar,
   Suunto, COROS, and Wahoo hardware.
3. A distraction-free audio session where pulse tempo changes in response to
   sustained HRV movement.

## Run

Start the complete local app:

```powershell
python main.py
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

The **Connect** action presents the selected wearable bridge state. A demo-signal option
is included so the complete product flow can be explored without the strap. The
original BLE and native-audio hardware pipeline remains available through:

```powershell
python main.py --hardware
```

## What is measured

- Heart rate and RR intervals from the BLE Heart Rate Measurement service
- Artifact-filtered RMSSD from RR differences
- A short subjective check-in
- Change from the user's own session baseline

Nevori uses the existing stress classifier and Q-learning audio agent. If the
optional model dependencies are unavailable, it falls back to a conservative
local HR/HRV heuristic while keeping the Q-learning loop active.

Personal learning state, completed sessions, and each user's Q-table are stored
locally under `data/users/<name>/`. Nothing is uploaded.

The recharge-capacity value is an explainable wellness heuristic, not a
validated medical score. Nevori does not diagnose or treat health conditions.
