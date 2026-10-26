"""Deterministic, hierarchical query expansion for game-review retrieval.

Broad aspect query -> original full aspect vocabulary.
Specific subtopic query -> only vocabulary for matched subtopics.
No recognizable aspect -> query unchanged.
"""
import re
from dataclasses import dataclass

import Stemmer

# Preserve the original broad aspect vocabulary for general queries.
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

# Specific subtopics are intentionally reusable rather than hardcoded by game/query.
# Generic aspect names (e.g. "gameplay", "controls", "multiplayer") are NOT
# subtopic triggers. Those use the broad fallback unless more specific language appears.
# Keep short and tightly tied to each information need; adjust using measured ablations.
SUBTOPICS = {
    'Gameplay': {
        'difficulty': (['difficulty', 'difficult', 'challenging', 'challenge', 'hard', 'easy', 'punishing', 'difficulty level', 'difficulty setting'],
                       ['difficulty', 'challenge', 'enemy difficulty', 'difficulty balance', 'hard mode']),
        'combat': (['combat', 'fighting', 'fight', 'battle', 'weapons', 'parry', 'dodging'],
                   ['combat', 'fighting', 'battle mechanics', 'attacks', 'enemy encounters']),
        'progression': (['progression', 'leveling', 'levelling', 'level up', 'upgrades', 'skill tree'],
                        ['progression', 'leveling', 'upgrades', 'skill progression']),
        'crafting': (['crafting', 'craft', 'recipes', 'materials'], ['crafting', 'materials', 'recipes', 'item creation']),
        'missions': (['missions', 'mission', 'quests', 'quest', 'objectives'], ['missions', 'quests', 'objectives', 'quest design']),
        'replayability': (['replayability', 'replayable', 'replay value', 'replay', 'playthroughs'],
                          ['replayability', 'replay value', 'repeat playthroughs']),
        'exploration': (['exploration', 'explore', 'discovery', 'secrets', 'map traversal'],
                        ['exploration', 'discovery', 'secrets', 'world traversal']),
        'pacing': (['pacing', 'pace', 'grind', 'grindy'], ['pacing', 'grind', 'gameplay flow']),
        'mechanics': (['mechanics', 'game systems', 'mechanic'], ['mechanics', 'game systems', 'core gameplay']),
    },
    'Controls': {
        'responsiveness': (['responsive', 'responsiveness', 'unresponsive', 'input lag', 'input delay', 'clunky', 'sluggish'],
                           ['control responsiveness', 'input response', 'input lag', 'control feel']),
        'movement': (['movement', 'move', 'maneuver', 'traversal', 'platforming', 'walking'],
                     ['movement controls', 'movement responsiveness', 'character movement']),
        'aiming': (['aim', 'aiming', 'targeting', 'camera', 'camera controls'],
                   ['aiming', 'camera controls', 'targeting', 'aim sensitivity']),
        'input_devices': (['keyboard', 'mouse', 'gamepad', 'controller support', 'using a controller', 'keybind', 'input mapping'],
                          ['controller support', 'keyboard and mouse', 'key bindings', 'input mapping']),
    },
    'Online and Multiplayer': {
        'coop': (['co-op', 'coop', 'cooperative', 'teamwork', 'teammates', 'play with friends', 'playing with friends'],
                 ['co-op', 'cooperative play', 'teamwork', 'playing with friends']),
        'competitive': (['pvp', 'competitive', 'ranked', 'player versus player'],
                        ['pvp', 'competitive multiplayer', 'ranked matches']),
        'matchmaking': (['matchmaking', 'lobbies', 'queue', 'server', 'servers', 'connection', 'disconnect', 'latency'],
                        ['matchmaking', 'servers', 'connection quality', 'lobbies']),
        'cheating': (['cheater', 'cheaters', 'cheating', 'hacks'], ['cheating', 'cheaters', 'anti-cheat']),
    },
    'Story and characters': {
        'story': (['story', 'plot', 'narrative', 'storyline', 'storytelling'], ['story', 'plot', 'narrative', 'storytelling', 'writing']),
        'characters': (['character', 'characters', 'character development', 'protagonist', 'cast'],
                       ['characters', 'character development', 'character writing', 'cast']),
        'dialogue': (['dialogue', 'dialog', 'conversations'], ['dialogue', 'conversations', 'writing']),
        'lore': (['lore', 'worldbuilding', 'world building'], ['lore', 'worldbuilding', 'background story']),
    },
    'Graphics and visuals': {
        'graphics': (['graphics', 'visual', 'visuals', 'visual quality'], ['graphics', 'visual quality', 'visual fidelity']),
        'textures': (['texture', 'textures', 'resolution'], ['textures', 'texture quality', 'resolution']),
        'lighting': (['lighting', 'shadows', 'ray tracing'], ['lighting', 'shadows', 'ray tracing']),
        'animation': (['animation', 'animations', 'facial animation'], ['animations', 'facial animations', 'motion']),
        'art': (['art style', 'art direction', 'aesthetic'], ['art style', 'art direction', 'aesthetics']),
    },
    'Performance and optimizations': {
        'framerate': (['fps', 'frame rate', 'framerate', 'frame drops', 'frame drop', 'stutter', 'stuttering', 'lag', 'smoothly'],
                       ['fps', 'frame rate', 'frame drops', 'stuttering', 'smooth performance']),
        'optimization': (['optimization', 'optimizations', 'optimized', 'optimize'],
                         ['optimization', 'performance optimization', 'efficient performance']),
        'loading': (['loading', 'load times', 'loading times'], ['loading times', 'load speed']),
        'hardware': (['gpu', 'cpu', 'hardware', 'system requirements', 'minimum specs'],
                     ['gpu performance', 'cpu performance', 'hardware requirements']),
    },
    'Music and Audio': {
        'music': (['music', 'soundtrack', 'score', 'background music'], ['music', 'soundtrack', 'background score']),
        'effects': (['sound effects', 'sound design', 'sfx', 'audio effects'], ['sound effects', 'sound design', 'audio effects']),
        'voice': (['voice acting', 'voiceover', 'voice over', 'dialogue audio'], ['voice acting', 'voiceover', 'spoken dialogue']),
    },
    'Bugs and Stability': {
        'stability': (['stable', 'stability', 'reliability', 'reliable', 'unstable'], ['stability', 'reliability', 'technical issues']),
        'crashes': (['crash', 'crashes', 'crashing', 'freeze', 'freezes', 'freezing'], ['crashes', 'freezes', 'game stability']),
        'bugs': (['bug', 'bugs', 'buggy', 'glitch', 'glitches', 'softlock'], ['bugs', 'glitches', 'softlocks']),
        'patches': (['patch', 'patches', 'updates', 'bug fixes'], ['patches', 'bug fixes', 'updates']),
    },
}

_STEMMER = Stemmer.Stemmer('english')
_WORDS = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")


def _stems(text):
    return tuple(_STEMMER.stemWords(_WORDS.findall(text.casefold())))


def _contains_phrase(query_stems, phrase_stems):
    size = len(phrase_stems)
    return bool(size) and any(query_stems[i:i + size] == phrase_stems
                              for i in range(len(query_stems) - size + 1))


def _compile_phrases(phrases):
    return tuple(dict.fromkeys(_stems(phrase) for phrase in phrases))


_COMPILED_TRIGGERS = {aspect: _compile_phrases(phrases) for aspect, phrases in ASPECT_TRIGGERS.items()}
_COMPILED_SUBTOPICS = {
    aspect: {name: _compile_phrases(triggers) for name, (triggers, _) in topics.items()}
    for aspect, topics in SUBTOPICS.items()
}


def detect_aspects(query):
    tokens = _stems(query)
    return [aspect for aspect, phrases in _COMPILED_TRIGGERS.items()
            if any(_contains_phrase(tokens, phrase) for phrase in phrases)]


def detect_subtopics(query, aspect):
    tokens = _stems(query)
    return [topic for topic, phrases in _COMPILED_SUBTOPICS[aspect].items()
            if any(_contains_phrase(tokens, phrase) for phrase in phrases)]


def _deduplicate(terms):
    seen, result = set(), []
    for term in terms:
        key = ' '.join(term.casefold().split())
        if key and key not in seen:
            seen.add(key)
            result.append(term)
    return result


@dataclass(frozen=True)
class ExpandedQuery:
    original: str
    aspects: tuple[str, ...]
    sparse: str
    dense: str
    subtopics: tuple[tuple[str, tuple[str, ...]], ...] = ()


def expand_query(query, mode='hierarchical'):
    """mode='broad' reproduces the old expansion; 'hierarchical' narrows specifics."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError('Query must be a nonempty string')
    if mode not in ('hierarchical', 'broad'):
        raise ValueError("mode must be 'hierarchical' or 'broad'")

    aspects = detect_aspects(query)
    if not aspects:
        return ExpandedQuery(query, (), query, query)

    selected_topics = {aspect: detect_subtopics(query, aspect) if mode == 'hierarchical' else []
                       for aspect in aspects}
    all_terms = []
    dense_sections = []
    selected = []
    for aspect in aspects:
        topics = selected_topics[aspect]
        selected.append((aspect, tuple(topics)))
        if topics:
            aspect_terms = _deduplicate(term for topic in topics for term in SUBTOPICS[aspect][topic][1])
            dense_sections.append(', '.join(aspect_terms))
        else:
            aspect_terms = [t.strip() for t in ASPECT_QUERIES[aspect]['bm25'].split(',')]
            dense_sections.append(ASPECT_QUERIES[aspect]['dense'])
        all_terms.extend(aspect_terms)

    terms = _deduplicate(all_terms)
    sparse = f"{query} {', '.join(terms)}" if terms else query
    dense = query + ''.join((' Topics include ' if i == 0 else ' Also consider ') + desc + '.'
                            for i, desc in enumerate(dense_sections))
    return ExpandedQuery(query, tuple(aspects), sparse, dense, tuple(selected))
