"""Deterministic aspect detection and query expansion for Steam review retrieval."""
import re
from dataclasses import dataclass

import Stemmer

# Expansion terms are intentionally kept close to the original eight-aspect proposal.
ASPECT_QUERIES = {
    'Story and characters': {'bm25': 'story, plot, writing, characters, narrative, protagonist, villain, lore, dialogue', 'dense': 'story, plot, writing, characters, narrative, protagonists, villains, lore, and dialogue'},
    'Graphics and visuals': {'bm25': 'graphics, visuals, textures, lighting, animations, environment, art style', 'dense': 'graphics, visual quality, textures, lighting, animations, environments, and art style'},
    'Gameplay': {'bm25': 'gameplay, combat, mechanics, progression, difficulty, crafting, missions, pacing, replayability, exploration', 'dense': 'gameplay, combat, core mechanics, progression, difficulty, crafting, missions, pacing, replayability, and exploration'},
    'Controls': {'bm25': 'controls, keybinds, controller, keyboard, mouse, aiming, camera, movement, input', 'dense': 'controls, keybinds, controller support, keyboard and mouse input, aiming, camera controls, movement, and input response'},
    'Performance and optimizations': {'bm25': 'performance, optimization, fps, frame rate, stutter, lag, loading, system requirements, gpu, cpu, hardware', 'dense': 'performance, optimization, FPS, frame rate, stuttering, lag, loading times, system requirements, GPU, CPU, and hardware'},
    'Music and Audio': {'bm25': 'music, soundtrack, audio, sound effects, sound design', 'dense': 'music, soundtrack, audio, sound effects, and sound design'},
    'Bugs and Stability': {'bm25': 'reliability, crash, freeze, glitch, bug, softlock, patch', 'dense': 'reliability, crashes, freezes, glitches, bugs, softlocks, and patches'},
    'Online and Multiplayer': {'bm25': 'multiplayer, online, co-op, pvp, servers, matchmaking, cheaters, community', 'dense': 'multiplayer, online play, co-op, PvP, servers, matchmaking, cheaters, and community'},
}

# Include both words from each aspect name, plus paraphrases/derivations
# not reliably connected by stemming (e.g. bug -> buggy).
ASPECT_TRIGGERS = {
    'Story and characters': ['story', 'stories', 'character', 'characters', 'plot', 'narrative', 'writing', 'dialogue', 'protagonist', 'villain', 'lore', 'storyline'],
    'Graphics and visuals': ['graphics', 'graphic', 'visuals', 'visual', 'texture', 'lighting', 'animation', 'art style', 'art direction', 'looks', 'scenery'],
    'Gameplay': ['gameplay', 'combat', 'mechanic', 'difficulty', 'difficult', 'challenge', 'challenging', 'crafting', 'mission', 'quest', 'progression', 'pacing', 'replayability', 'exploration', 'explore', 'fighting'],
    'Controls': ['control', 'controls', 'keybind', 'controller', 'keyboard', 'mouse', 'aiming', 'aim', 'camera', 'movement', 'move', 'input', 'maneuver', 'responsiveness'],
    'Performance and optimizations': ['performance', 'optimization', 'optimizations', 'optimize', 'fps', 'frame rate', 'framerate', 'frame time', 'frame drop', 'stutter', 'lag', 'loading time', 'system requirements', 'gpu', 'cpu', 'hardware', 'runs smoothly'],
    'Music and Audio': ['music', 'audio', 'sound', 'soundtrack', 'sound effects', 'sound design', 'voice acting', 'voiceover', 'footsteps'],
    'Bugs and Stability': ['bugs', 'bug', 'buggy', 'stability', 'stable', 'unstable', 'reliability', 'reliable', 'dependable', 'crash', 'freeze', 'glitch', 'glitchy', 'softlock', 'broken', 'technical issue', 'technical problem'],
    'Online and Multiplayer': ['online', 'multiplayer', 'co-op', 'coop', 'cooperative', 'pvp', 'server', 'matchmaking', 'cheater', 'community', 'teammate', 'playing with friends', 'play with friends', 'connection', 'disconnect'],
}

_STEMMER = Stemmer.Stemmer('english')
_WORDS = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


def _stems(text):
    return tuple(_STEMMER.stemWords(_WORDS.findall(text.casefold())))


def _contains_phrase(query_stems, phrase_stems):
    size = len(phrase_stems)
    return any(query_stems[i:i + size] == phrase_stems
               for i in range(len(query_stems) - size + 1))


# Compile once; match whole normalized token sequences, not substrings.
_COMPILED_TRIGGERS = {
    aspect: tuple(dict.fromkeys(_stems(phrase) for phrase in phrases))
    for aspect, phrases in ASPECT_TRIGGERS.items()
}


def detect_aspects(query):
    tokens = _stems(query)
    return [aspect for aspect, phrases in _COMPILED_TRIGGERS.items()
            if any(_contains_phrase(tokens, phrase) for phrase in phrases)]


def _unique_terms(aspects, field):
    seen = set()
    result = []
    for aspect in aspects:
        for term in ASPECT_QUERIES[aspect][field].split(','):
            term = term.strip()
            key = term.casefold()
            if term and key not in seen:
                seen.add(key)
                result.append(term)
    return result


@dataclass(frozen=True)
class ExpandedQuery:
    original: str
    aspects: tuple[str, ...]
    sparse: str
    dense: str


def expand_query(query):
    if not isinstance(query, str) or not query.strip():
        raise ValueError('Query must be a nonempty string')
    aspects = detect_aspects(query)
    if not aspects:
        return ExpandedQuery(query, (), query, query)

    sparse_terms = _unique_terms(aspects, 'bm25')
    sparse = f"{query} {', '.join(sparse_terms)}"
    dense_parts = [query]
    for i, aspect in enumerate(aspects):
        prefix = 'Topics include' if i == 0 else 'Also consider'
        dense_parts.append(f"{prefix} {ASPECT_QUERIES[aspect]['dense']}.")
    return ExpandedQuery(query, tuple(aspects), sparse, ' '.join(dense_parts))
