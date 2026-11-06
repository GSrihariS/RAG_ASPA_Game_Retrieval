def parse_game_filter(filters):
    """Return the casefolded game names in filters={"game_name": str | [str, ...]}, or None."""
    if filters is None:
        return None
    if not isinstance(filters, dict) or set(filters) != {'game_name'}:
        raise ValueError('Only filters={"game_name": "..."} is supported')
    names = filters['game_name']
    if isinstance(names, str):
        names = [names]
    if (not isinstance(names, (list, tuple)) or not names
            or any(not isinstance(name, str) or not name.strip() for name in names)):
        raise ValueError('game_name must be a nonempty string or a list of nonempty strings')
    return {name.strip().casefold() for name in names}
