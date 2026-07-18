from collections.abc import Callable


def select_retrieval_query(
    *,
    input_type: str,
    query_text: str,
    message: str,
    image_description: str,
    rewrite: Callable[[str, str], str],
) -> str:
    """Voice bypasses generic rewriting; other inputs preserve existing behavior."""
    if input_type == "voice":
        return query_text
    return rewrite(message, image_description)
