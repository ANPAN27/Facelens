from face.matcher import cosine_similarity
from config import RANKING_WEIGHTS, SIMILARITY_THRESHOLD_HIGH, SIMILARITY_THRESHOLD_MEDIUM


def classify_match(similarity: float) -> str:
    if similarity >= SIMILARITY_THRESHOLD_HIGH:
        return "HIGH"
    elif similarity >= SIMILARITY_THRESHOLD_MEDIUM:
        return "MEDIUM"
    return "LOW"


def compute_source_score(platform: str) -> float:
    social_platforms = {"Instagram", "Facebook", "X/Twitter", "LinkedIn", "Reddit", "TikTok", "Pinterest"}
    news_platforms = {"News", "Press", "Article"}

    if platform in social_platforms:
        return 1.0
    elif platform in news_platforms:
        return 0.7
    elif platform == "Image":
        return 0.3
    return 0.5


def rank_candidates(input_embedding, candidates: list[dict]) -> list[dict]:
    ranked = []
    for c in candidates:
        if not c.get("face_detected"):
            continue

        best_similarity = 0.0
        for face in c.get("faces", []):
            emb = face.get("embedding")
            if emb is not None:
                sim = cosine_similarity(input_embedding, emb)
                best_similarity = max(best_similarity, sim)

        if best_similarity <= 0:
            continue

        source_score = compute_source_score(c.get("platform", "Unknown"))
        search_score = 0.5

        final_score = (
            RANKING_WEIGHTS["face"] * best_similarity
            + RANKING_WEIGHTS["image"] * best_similarity * 0.8
            + RANKING_WEIGHTS["search"] * search_score
            + RANKING_WEIGHTS["source"] * source_score
        )

        classification = classify_match(best_similarity)

        ranked.append({
            **c,
            "face_similarity": round(best_similarity, 6),
            "source_score": source_score,
            "search_score": search_score,
            "final_score": round(final_score, 6),
            "classification": classification,
        })

    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    return ranked
