"""Service for performing sentiment analysis on text."""
import logging
from typing import Dict

# A simple sentiment word list (this can be expanded)
POSITIVE_WORDS = {"good", "great", "excellent", "awesome", "love", "like", "amazing", "beautiful", "brilliant"}
NEGATIVE_WORDS = {"bad", "terrible", "awful", "hate", "dislike", "poor", "sad", "angry", "frustrating"}

logger = logging.getLogger(__name__)

class SentimentService:
    """A simple sentiment analysis service."""

    def analyze_sentiment(self, text: str) -> Dict[str, any]:
        """Analyzes the sentiment of a given text.

        Args:
            text: The text to analyze.

        Returns:
            A dictionary containing the sentiment score and classification.
        """
        if not text:
            return {"score": 0.5, "classification": "neutral"}

        try:
            words = text.lower().split()
            pos_count = sum(1 for word in words if word in POSITIVE_WORDS)
            neg_count = sum(1 for word in words if word in NEGATIVE_WORDS)

            total_sentiment_words = pos_count + neg_count
            if total_sentiment_words == 0:
                score = 0.5  # Neutral
            else:
                score = pos_count / total_sentiment_words

            classification = "positive" if score > 0.6 else "negative" if score < 0.4 else "neutral"

            return {
                "score": score,
                "classification": classification,
                "positive_words": pos_count,
                "negative_words": neg_count,
            }
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return {"score": 0.5, "classification": "neutral", "error": str(e)}
