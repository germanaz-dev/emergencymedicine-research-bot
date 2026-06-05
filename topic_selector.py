import json
from datetime import datetime

TOPICS_FILE = "topics.json"
TEMA_FILE = "tema.txt"

today = datetime.now().date()

with open(TOPICS_FILE, "r", encoding="utf-8") as f:
    topics = json.load(f)

best_topic = None
best_score = -1

for topic in topics:

    priority = topic.get("priority", 1)

    last_used = topic.get("last_used")

    if last_used is None:
        days_since = 9999
    else:
        last_date = datetime.strptime(
            last_used,
            "%Y-%m-%d"
        ).date()

        days_since = (today - last_date).days

    score = priority * 100 + days_since

    if score > best_score:
        best_score = score
        best_topic = topic

selected_topic = best_topic["topic"]

with open(TEMA_FILE, "w", encoding="utf-8") as f:
    f.write(selected_topic)

best_topic["last_used"] = today.strftime("%Y-%m-%d")

with open(TOPICS_FILE, "w", encoding="utf-8") as f:
    json.dump(
        topics,
        f,
        indent=2,
        ensure_ascii=False
    )

print("Tema seleccionado:")
print(selected_topic)
