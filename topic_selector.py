import json
import random
from datetime import datetime, date
from pathlib import Path

SYLLABUS_FILE = Path("curriculum/syllabus.json")
WEIGHTS_FILE = Path("config/weights.json")
HISTORY_FILE = Path("runtime/history.json")
ALERTS_FILE = Path("runtime/alerts.json")
TEMA_FILE = Path("tema.txt")
SELECTED_FILE = Path("runtime/selected_topic.json")

today = date.today().isoformat()

AXES = {
    "critical_care": 1.25,
    "cardinal_symptoms": 1.20,
    "cardiovascular": 1.15,
    "respiratory": 1.10,
    "neurology": 1.10,
    "infectious": 1.15,
    "trauma_toxicology": 1.10,
    "metabolic_internal": 1.00,
    "vulnerable_populations": 1.05,
    "pocus_procedures": 1.15,
    "systems_safety": 1.20,
    "prehospital": 1.05,
    "innovation": 0.75
}


def load_json(path, default):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


syllabus = load_json(SYLLABUS_FILE, [])
weights = load_json(WEIGHTS_FILE, {})
history = load_json(HISTORY_FILE, {})
alerts = load_json(ALERTS_FILE, [])

priority_weight = weights.get("priority_weight", 10)
recency_weight = weights.get("recency_weight", 0.25)
axis_weight = weights.get("axis_weight", 20)
alert_weight = weights.get("alert_weight", 1.2)
exploration_rate = weights.get("exploration_rate", 0.15)
recent_axis_penalty = weights.get("recent_axis_penalty", 0.65)


def days_since(date_string):
    if not date_string:
        return 999
    try:
        old = datetime.strptime(date_string, "%Y-%m-%d").date()
        return max((date.today() - old).days, 0)
    except Exception:
        return 999


def active_alert_bonus(topic):
    bonus = 0
    matched_alerts = []

    topic_words = set(
        " ".join([topic.get("title", "")] + topic.get("keywords", [])).lower().split()
    )

    for alert in alerts:
        expires = alert.get("expires")
        if expires and expires < today:
            continue

        alert_text = " ".join([
            alert.get("topic", ""),
            " ".join(alert.get("keywords", []))
        ]).lower()

        if any(word in alert_text for word in topic_words if len(word) > 4):
            strength = alert.get("strength", 0)
            bonus += strength * alert_weight
            matched_alerts.append(alert)

    return bonus, matched_alerts


recent_axes = []
for item in history.values():
    if item.get("last_seen"):
        recent_axes.append((item.get("last_seen"), item.get("axis")))
recent_axes = sorted(recent_axes, reverse=True)
last_axis = recent_axes[0][1] if recent_axes else None

scored = []

for topic in syllabus:
    topic_id = topic["id"]
    axis = topic.get("axis", "unknown")

    h = history.get(topic_id, {})
    d_since = days_since(h.get("last_seen"))

    priority_score = topic.get("priority", 5) * priority_weight
    recency_score = min(d_since, topic.get("review_interval_days", 180)) * recency_weight
    axis_score = AXES.get(axis, 1.0) * axis_weight

    alert_score, matched_alerts = active_alert_bonus(topic)

    score = priority_score + recency_score + axis_score + alert_score

    if axis == last_axis:
        score *= recent_axis_penalty

    if axis == "innovation":
        score *= weights.get("frontier_cap", 0.75)

    scored.append({
        "topic": topic,
        "score": score,
        "components": {
            "priority_score": priority_score,
            "recency_score": recency_score,
            "axis_score": axis_score,
            "alert_score": alert_score,
            "last_axis_penalty": axis == last_axis,
            "matched_alerts": matched_alerts
        }
    })

if not scored:
    raise SystemExit("No hay temas en curriculum/syllabus.json")

scored = sorted(scored, key=lambda x: x["score"], reverse=True)

exploration = random.random() < exploration_rate

if exploration and len(scored) > 3:
    pool = scored[:min(8, len(scored))]
    selected = random.choice(pool)
else:
    selected = scored[0]

topic = selected["topic"]
topic_id = topic["id"]

TEMA_FILE.write_text(topic["title"], encoding="utf-8")

history[topic_id] = {
    "last_seen": today,
    "times_reviewed": history.get(topic_id, {}).get("times_reviewed", 0) + 1,
    "axis": topic.get("axis")
}

save_json(HISTORY_FILE, history)

selected_record = {
    "date": today,
    "selected_topic": topic,
    "score": selected["score"],
    "exploration": exploration,
    "reason": selected["components"],
    "top_5": [
        {
            "id": item["topic"]["id"],
            "title": item["topic"]["title"],
            "axis": item["topic"].get("axis"),
            "score": round(item["score"], 2)
        }
        for item in scored[:5]
    ]
}

save_json(SELECTED_FILE, selected_record)

print("Tema seleccionado:")
print(topic["title"])
print("Eje:", topic.get("axis"))
print("Score:", round(selected["score"], 2))
print("Exploración:", exploration)
