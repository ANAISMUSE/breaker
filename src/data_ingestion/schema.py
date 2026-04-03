STANDARD_COLUMNS = [
    "user_id",
    "platform",
    "content_id",
    "timestamp",
    "content_type",
    "text",
    "image_url",
    "video_url",
    "like",
    "comment",
    "share",
    "duration",
    "topic",
    "stance",
    "emotion_score",
    "author_id",
]

TOPIC_MAP = {
    "搞笑": "entertainment",
    "娱乐": "entertainment",
    "时政": "politics",
    "社会": "society",
    "科技": "technology",
    "教育": "education",
    "财经": "finance",
    "体育": "sports",
    "健康": "health",
}


def normalize_topic(raw_topic: str) -> str:
    if not raw_topic:
        return "other"
    return TOPIC_MAP.get(raw_topic.strip(), raw_topic.strip().lower())
