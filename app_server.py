"""Local Nevori web server powered by the project's classifier and Q-learning agent."""
from __future__ import annotations

import json
import math
import random
import re
import threading
import time
import unicodedata
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from core.ai_brain import QLearningAudioAgent, StressClassifier

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
DATA = ROOT / "data"
USERS = DATA / "users"


def safe_user_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    cleaned = re.sub(r"[^a-z0-9_-]+", "_", normalized.strip().lower()).strip("_")
    return cleaned or "default"


class LocalStore:
    """Small JSON store. All personal data remains inside data/users."""

    def __init__(self, root: Path = USERS):
        self.root = Path(root)
        self.lock = threading.RLock()

    def user_dir(self, user: str) -> Path:
        path = self.root / safe_user_name(user)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def read_json(self, user: str, name: str, default: Any) -> Any:
        path = self.user_dir(user) / name
        with self.lock:
            if not path.exists():
                return default
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return default

    def write_json(self, user: str, name: str, value: Any) -> None:
        path = self.user_dir(user) / name
        temp = path.with_suffix(path.suffix + ".tmp")
        with self.lock:
            temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
            temp.replace(path)

    def sessions(self, user: str) -> list[dict[str, Any]]:
        return self.read_json(user, "sessions.json", [])

    def add_session(self, user: str, session: dict[str, Any]) -> None:
        sessions = self.sessions(user)
        sessions.append(session)
        self.write_json(user, "sessions.json", sessions[-500:])

    def stats(self, user: str) -> dict[str, Any]:
        return self.read_json(
            user,
            "learning.json",
            {"decisions": 0, "positive_responses": 0, "patterns": [], "last_frequency": 40},
        )

    def save_stats(self, user: str, stats: dict[str, Any]) -> None:
        self.write_json(user, "learning.json", stats)

    def clear_sessions(self, user: str) -> None:
        self.write_json(user, "sessions.json", [])

    def profile(self, user: str) -> dict[str, Any]:
        return self.read_json(user, "profile.json", {"mood": "steady", "weekly_goal": 3})

    def save_profile(self, user: str, profile: dict[str, Any]) -> None:
        self.write_json(user, "profile.json", profile)


@dataclass
class BioState:
    heart_rate: float = 68.0
    rmssd: float = 48.0
    breath_rate: float = 11.5
    capacity: int = 72
    signal_quality: str = "Good"
    trend: str = "steady"
    source: str = "demo"
    stress_state: str = "calm"
    audio_frequency: float = 40.0
    audio_bpm: int = 64
    adaptation_copy: str = "Listening for a stable response"
    ai_mode: str = "Calibrating"
    timestamp: str = ""


class Engine:
    mood_weights = {"drained": -18, "stretched": -9, "steady": 0, "bright": 8}

    def __init__(self, data_root: Path | None = None, start_simulator: bool = True):
        self.store = LocalStore(data_root or USERS)
        self.state = BioState()
        self.mood = "steady"
        self.sessions: dict[str, dict[str, Any]] = {}
        self.agents: dict[str, QLearningAudioAgent] = {}
        self.classifier = StressClassifier(model_path=str(ROOT / "stresa_modelis.joblib"))
        self.lock = threading.RLock()
        self.started = time.monotonic()
        self.last_decision = self.started
        self.last_rmssd = self.state.rmssd
        self.last_external_sample = 0.0
        if start_simulator:
            threading.Thread(target=self.simulate, daemon=True).start()

    def agent_for(self, user: str) -> QLearningAudioAgent:
        key = safe_user_name(user)
        if key not in self.agents:
            agent = QLearningAudioAgent(user_name=key, storage_dir=str(self.store.user_dir(key)))
            agent.load_model()
            self.agents[key] = agent
        return self.agents[key]

    def capacity(self, mood: str | None = None) -> int:
        hrv = min(max((self.state.rmssd - 20) / 55, 0), 1) * 55
        heart = min(max((92 - self.state.heart_rate) / 35, 0), 1) * 30
        return round(min(max(hrv + heart + 15 + self.mood_weights.get(mood or self.mood, 0), 5), 98))

    def active_session(self) -> dict[str, Any] | None:
        return next((session for session in self.sessions.values() if session["status"] == "active"), None)

    def simulate(self) -> None:
        while True:
            if time.monotonic() - self.last_external_sample < 8:
                time.sleep(2)
                continue
            elapsed = time.monotonic() - self.started
            active = self.active_session()
            settle = min((time.monotonic() - active["started_monotonic"]) / 180, 1) * 5 if active else 0
            with self.lock:
                previous = self.state.rmssd
                self.state.heart_rate = max(52, min(98, 68 + math.sin(elapsed / 12) * 2.4 - settle + random.uniform(-1.2, 1.2)))
                self.state.rmssd = max(18, min(105, 47 + math.sin(elapsed / 17) * 4 + settle * 1.8 + random.uniform(-1.8, 1.8)))
                self.state.breath_rate = 6.0 if active else 11.5 + math.sin(elapsed / 20)
                self.state.trend = "up" if self.state.rmssd > previous + .5 else "down" if self.state.rmssd < previous - .5 else "steady"
                self.state.capacity = self.capacity()
                self.state.timestamp = datetime.now(timezone.utc).isoformat()
                if active and time.monotonic() - self.last_decision >= 12:
                    self._brain_step(active)
            time.sleep(2)

    def ingest_bio(self, heart_rate: float, rmssd: float, rr_count: int, source: str = "wearable") -> dict[str, Any]:
        if not 30 <= heart_rate <= 220:
            raise ValueError("Heart rate is outside the supported range")
        if not 0 <= rmssd <= 250:
            raise ValueError("RMSSD is outside the supported range")
        with self.lock:
            previous = self.state.rmssd
            self.state.heart_rate = heart_rate
            if rmssd > 0:
                self.state.rmssd = rmssd
            self.state.trend = "up" if self.state.rmssd > previous + .5 else "down" if self.state.rmssd < previous - .5 else "steady"
            self.state.source = source
            self.state.signal_quality = "Good" if rr_count >= 12 else "Building" if rr_count >= 4 else "Heart rate only"
            self.state.capacity = self.capacity()
            self.state.timestamp = datetime.now(timezone.utc).isoformat()
            self.last_external_sample = time.monotonic()
        return self.snapshot()

    def _brain_step(self, session: dict[str, Any]) -> None:
        user = session["user"]
        agent = self.agent_for(user)
        predicted = int(self.classifier.predict(self.state.heart_rate, self.state.rmssd))
        reward = 1.0 if self.state.rmssd > self.last_rmssd + .5 else -1.0 if self.state.rmssd < self.last_rmssd - .5 else 0.0
        agent.update_q_table(reward)
        frequency, choice = agent.choose_action(predicted)
        agent.save_model()

        stats = self.store.stats(user)
        stats["decisions"] += 1
        stats["positive_responses"] += int(reward > 0)
        stats["last_frequency"] = frequency
        stats["patterns"] = list(dict.fromkeys([*stats.get("patterns", []), frequency]))
        self.store.save_stats(user, stats)

        target_bpm = max(55, round(self.state.heart_rate - 5))
        self.state.stress_state = "stress" if predicted == 1 else "calm"
        self.state.audio_frequency = frequency
        self.state.audio_bpm = target_bpm
        self.state.ai_mode = "Exploring" if "Eksperiments" in choice else "Personalizing"
        if reward > 0:
            self.state.adaptation_copy = f"HRV is rising — easing toward {target_bpm} BPM"
        elif reward < 0:
            self.state.adaptation_copy = f"Holding a steady {target_bpm} BPM while your response settles"
        else:
            self.state.adaptation_copy = f"Testing a gentle {frequency:g} Hz pattern"
        self.last_rmssd = self.state.rmssd
        self.last_decision = time.monotonic()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return asdict(self.state)

    def checkin(self, mood: str, user: str = "Māris") -> dict[str, Any]:
        if mood not in self.mood_weights:
            raise ValueError("Unknown mood")
        with self.lock:
            self.mood = mood
            self.state.capacity = self.capacity()
            score = self.state.capacity
        checked_in_at = datetime.now(timezone.utc)
        profile = self.store.profile(user)
        mood_checkins = profile.get("mood_checkins", {})
        if not isinstance(mood_checkins, dict):
            mood_checkins = {}
        mood_checkins[checked_in_at.date().isoformat()] = mood
        profile.update(mood=mood, checked_in_at=checked_in_at.isoformat(), mood_checkins=mood_checkins)
        self.store.save_profile(user, profile)
        low = mood in {"drained", "stretched"}
        return {
            "capacity": score,
            "protocol": {
                "title": "The 6-minute downshift" if low else "The 6-minute clear reset",
                "description": "Easy paced breathing with a gentle audio pulse. No breath holds, no performance target."
                if low else "A steady cadence to preserve capacity and sharpen the transition into what comes next.",
            },
        }

    def begin(self, duration: int, mood: str, user: str = "Māris", device: str = "Demo signal") -> dict[str, Any]:
        if mood in self.mood_weights:
            self.mood = mood
        user_key = safe_user_name(user)
        agent = self.agent_for(user_key)
        sid = uuid.uuid4().hex[:12]
        snap = self.snapshot()
        predicted_state = int(self.classifier.predict(snap["heart_rate"], snap["rmssd"]))
        if mood in {"drained", "stretched"}:
            predicted_state = 1
        initial_frequency, choice = agent.choose_action(predicted_state)
        self.state.audio_frequency = initial_frequency
        self.state.audio_bpm = max(55, round(snap["heart_rate"] - (7 if mood in {"drained", "stretched"} else 5)))
        self.state.ai_mode = "Exploring" if "Eksperiments" in choice else "Personalizing"
        self.state.adaptation_copy = f"Beginning with a {initial_frequency:g} Hz pattern informed by your {mood} check-in"
        self.sessions[sid] = {
            "session_id": sid,
            "user": user_key,
            "display_name": user.strip() or "Māris",
            "device": device,
            "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "started_monotonic": time.monotonic(),
            "duration": min(max(duration, 60), 1800),
            "baseline_rmssd": snap["rmssd"],
            "baseline_hr": snap["heart_rate"],
            "mood": self.mood,
            "initial_ai_state": predicted_state,
            "initial_audio_frequency": initial_frequency,
        }
        self.last_rmssd = snap["rmssd"]
        self.last_decision = time.monotonic() - 12
        return {"session_id": sid, "baseline_rmssd": round(snap["rmssd"], 1), "duration": self.sessions[sid]["duration"]}

    def complete(self, sid: str) -> dict[str, Any]:
        session = self.sessions.get(sid)
        if not session:
            raise ValueError("Session not found")
        snap = self.snapshot()
        elapsed = max(1, round(time.monotonic() - session["started_monotonic"]))
        session.update(
            status="complete",
            completed_at=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=min(elapsed, session["duration"]),
            final_rmssd=round(snap["rmssd"], 1),
            final_hr=round(snap["heart_rate"], 1),
            delta_rmssd=round(snap["rmssd"] - session["baseline_rmssd"], 1),
            audio_frequency=snap["audio_frequency"],
            audio_bpm=snap["audio_bpm"],
        )
        stored = {key: value for key, value in session.items() if key != "started_monotonic"}
        self.store.add_session(session["user"], stored)
        self.agent_for(session["user"]).save_model()
        return stored

    def dashboard(self, user: str = "Māris") -> dict[str, Any]:
        user_key = safe_user_name(user)
        sessions = self.store.sessions(user_key)
        now = datetime.now(timezone.utc)
        week_start = (now - timedelta(days=6)).date()
        week_buckets = {week_start + timedelta(days=index): [] for index in range(7)}
        for session in sessions:
            try:
                ended = datetime.fromisoformat(session["completed_at"]).date()
            except (KeyError, ValueError):
                continue
            if ended in week_buckets:
                week_buckets[ended].append(float(session.get("delta_rmssd", 0)))

        week = []
        profile = self.store.profile(user_key)
        mood_checkins = profile.get("mood_checkins", {})
        if not isinstance(mood_checkins, dict):
            mood_checkins = {}
        for day, values in week_buckets.items():
            week.append({
                "day": day.strftime("%a")[0],
                "date": day.isoformat(),
                "shift": round(sum(values) / len(values), 1) if values else 0,
                "mood": mood_checkins.get(day.isoformat()),
            })
        weekly = [session for session in sessions if self._session_date(session) >= week_start]
        shifts = [float(session.get("delta_rmssd", 0)) for session in weekly]
        stats = self.store.stats(user_key)
        observed = len(sessions)
        decisions = int(stats.get("decisions", 0))
        consistency = round(100 * stats.get("positive_responses", 0) / decisions) if decisions else 0
        patterns_tested = len(stats.get("patterns", [])) if observed else 0
        evidence_decisions = min(decisions, observed * 10)
        learning_percent = min(95, round(observed * 7 + patterns_tested * 3 + evidence_decisions * .5)) if observed else 0
        baselines = [float(item.get("baseline_rmssd", 0)) for item in sessions[-14:] if float(item.get("baseline_rmssd", 0)) > 0]
        personal_baseline = round(sum(baselines) / len(baselines), 1) if baselines else round(self.state.rmssd, 1)
        baseline_delta = round(self.state.rmssd - personal_baseline, 1)
        baseline_percent = round((baseline_delta / personal_baseline) * 100) if personal_baseline else 0
        mood = profile.get("mood", "steady")
        capacity = self.capacity(mood)
        if capacity < 45 or mood == "drained":
            readiness = "Recover"
            recommended_minutes = 8
            recommendation = "A longer downshift"
        elif capacity < 70 or mood == "stretched":
            readiness = "Balanced"
            recommended_minutes = 6
            recommendation = "A steady reset"
        else:
            readiness = "Ready"
            recommended_minutes = 4
            recommendation = "A light recharge"
        live_wearable = self.state.source == "wearable" and time.monotonic() - self.last_external_sample < 8
        if observed and live_wearable:
            why = f"Current HRV is {abs(baseline_percent)}% {'above' if baseline_percent >= 0 else 'below'} your recent baseline."
        elif live_wearable:
            why = "Live wearable data is establishing your personal HRV baseline."
        else:
            why = "Connect a wearable for a live readiness score. Current values are an estimate."
        goal = max(1, int(profile.get("weekly_goal", 3)))

        recent = []
        for session in reversed(sessions[-4:]):
            ended = datetime.fromisoformat(session["completed_at"])
            frequency = session.get("audio_frequency", stats.get("last_frequency", 40))
            recent.append({
                "date": ended.strftime("%d"),
                "month": ended.strftime("%b"),
                "title": "Adaptive recharge",
                "duration": max(1, round(session.get("elapsed_seconds", session.get("duration", 360)) / 60)),
                "audio": f"{frequency:g} Hz personal pulse",
                "shift": round(float(session.get("delta_rmssd", 0)), 1),
            })
        best = max(sessions, key=lambda item: float(item.get("delta_rmssd", 0)), default=None)
        return {
            "week": week,
            "average_shift": round(sum(shifts) / len(shifts), 1) if shifts else 0,
            "weekly_sessions": len(weekly),
            "weekly_minutes": sum(max(1, round(item.get("elapsed_seconds", item.get("duration", 0)) / 60)) for item in weekly),
            "sessions": recent,
            "best_session": {
                "shift": round(float(best.get("delta_rmssd", 0)), 1),
                "duration": max(1, round(best.get("elapsed_seconds", best.get("duration", 0)) / 60)),
            } if best else None,
            "learning": {
                "percent": learning_percent,
                "sessions_observed": observed,
                "patterns_tested": patterns_tested,
                "response_consistency": consistency if observed else 0,
                "best_frequency": stats.get("last_frequency", 40),
                "confidence": "Well personalized" if learning_percent >= 80 else "Building confidence" if learning_percent >= 35 else "Early learning",
            },
            "today": {
                "readiness": readiness if live_wearable else "Connect device",
                "capacity": capacity,
                "current_rmssd": round(self.state.rmssd, 1),
                "baseline_rmssd": personal_baseline,
                "baseline_percent": baseline_percent,
                "recommendation": recommendation,
                "recommended_minutes": recommended_minutes,
                "why": why,
                "mood": mood,
                "signal_quality": self.state.signal_quality,
                "data_quality": self.state.signal_quality if live_wearable else "Estimated",
                "live_data": live_wearable,
            },
            "goal": {"target": goal, "completed": len(weekly), "remaining": max(0, goal - len(weekly))},
            "insight": (
                f"Your strongest response so far came after {max(1, round(best.get('elapsed_seconds', best.get('duration', 0)) / 60))} minutes."
                if best else "Complete a few sessions and Nevori will surface your strongest recovery pattern."
            ),
        }

    @staticmethod
    def _session_date(session: dict[str, Any]):
        try:
            return datetime.fromisoformat(session["completed_at"]).date()
        except (KeyError, ValueError):
            return datetime.min.date()


ENGINE = Engine()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, fmt, *args):
        print(f"[nevori] {fmt % args}")

    def end_headers(self):
        if not any(name.lower() == "cache-control" for name, _ in self._headers_buffer_items()):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _headers_buffer_items(self):
        for raw in getattr(self, "_headers_buffer", []):
            try:
                name, value = raw.decode("latin-1").split(":", 1)
                yield name.strip(), value.strip()
            except (ValueError, UnicodeDecodeError):
                continue

    def send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def payload(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 64000:
            raise ValueError("Payload too large")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/api/state":
            return self.send_json(ENGINE.snapshot())
        if parsed.path == "/api/dashboard":
            return self.send_json(ENGINE.dashboard(query.get("user", ["Māris"])[0]))
        if parsed.path == "/api/health":
            return self.send_json({"status": "ok", "service": "nevori", "brain": "classifier+q-learning"})
        return super().do_GET()

    def do_POST(self):
        try:
            payload = self.payload()
            if self.path == "/api/checkin":
                return self.send_json(ENGINE.checkin(str(payload.get("mood", "")), str(payload.get("user", "Māris"))))
            if self.path == "/api/reflection":
                user = str(payload.get("user", "Māris"))
                value = str(payload.get("reflection", ""))
                if value not in {"worse", "same", "better"}:
                    raise ValueError("Unknown reflection")
                profile = ENGINE.store.profile(user)
                profile.update(last_reflection=value, reflected_at=datetime.now(timezone.utc).isoformat())
                ENGINE.store.save_profile(user, profile)
                return self.send_json({"saved": True, "reflection": value})
            if self.path == "/api/bio/sample":
                return self.send_json(ENGINE.ingest_bio(
                    float(payload.get("heart_rate", 0)),
                    float(payload.get("rmssd", 0)),
                    int(payload.get("rr_count", 0)),
                    str(payload.get("source", "wearable")),
                ))
            if self.path == "/api/session/start":
                return self.send_json(
                    ENGINE.begin(
                        int(payload.get("duration", 360)),
                        str(payload.get("mood", "steady")),
                        str(payload.get("user", "Māris")),
                        str(payload.get("device", "Demo signal")),
                    ),
                    HTTPStatus.CREATED,
                )
            if self.path == "/api/session/complete":
                return self.send_json(ENGINE.complete(str(payload.get("session_id", ""))))
            if self.path == "/api/data/clear":
                ENGINE.store.clear_sessions(str(payload.get("user", "Māris")))
                return self.send_json({"cleared": True})
            if self.path == "/api/device/connect":
                supported = {"Polar H10", "Polar Verity Sense", "Polar Vantage V3", "Polar Grit X Pro", "Suunto Race", "COROS PACE Pro", "Wahoo TICKR X"}
                device = str(payload.get("device", "Polar H10"))
                if device not in supported:
                    raise ValueError("Unsupported device")
                return self.send_json({"connected": True, "device": device, "label": f"{device} · signal good", "message": "Clean RR signal found."})
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    print(f"\n  Nevori is running at http://{host}:{port}")
    print(f"  Local user data: {USERS}\n")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    run_server()
