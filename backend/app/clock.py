from datetime import date


def get_today() -> date:
    """Today's date; a FastAPI dependency so tests can pin it to a fixed day."""
    return date.today()
