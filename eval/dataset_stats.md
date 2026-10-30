# Annotation set statistics

Source: `data/steam_annotations_confirmed.json` (dataset `steam-annotation-1000-1a592433720b`)

- Confirmed chunks: 1000 from 1000 reviews of 20 games
- Chunk length (words): min 16, median 52, max 154
- Aspects: 8 (story, graphics_visuals, gameplay, controls, performance, audio, bugs_stability, online_multiplayer)

## Chunks per game

| game | chunks |
|---|---|
| Call of Duty: Warzone | 50 |
| Clair Obscur: Expedition 33 | 50 |
| Cyberpunk 2077 | 50 |
| Grand Theft Auto V Legacy | 50 |
| Hades II | 50 |
| Hollow Knight | 50 |
| Hollow Knight: Silksong | 50 |
| Left 4 Dead 2 | 50 |
| Monster Hunter Wilds | 50 |
| PAYDAY 3 | 50 |
| Red Dead Redemption 2 | 50 |
| Redfall | 50 |
| Resident Evil Requiem | 50 |
| Resident Evil Resistance | 50 |
| RollerCoaster Tycoon World | 50 |
| Spacebase DF-9 | 50 |
| Test Drive Unlimited Solar Crown | 50 |
| Umbrella Corps | 50 |
| Warhammer 40,000: Dawn of War III | 50 |
| Wolfenstein: Youngblood | 50 |

## Aspect x sentiment

| aspect | Positive | Negative | Mixed | Neutral | Unclear | Not mentioned | mentioned |
|---|---|---|---|---|---|---|---|
| story | 239 | 99 | 31 | 32 | 1 | 598 | 402 |
| graphics_visuals | 268 | 84 | 13 | 16 | 0 | 619 | 381 |
| gameplay | 376 | 237 | 139 | 23 | 0 | 225 | 775 |
| controls | 68 | 130 | 14 | 6 | 0 | 782 | 218 |
| performance | 96 | 127 | 9 | 21 | 0 | 747 | 253 |
| audio | 204 | 54 | 5 | 3 | 0 | 734 | 266 |
| bugs_stability | 50 | 252 | 6 | 2 | 0 | 690 | 310 |
| online_multiplayer | 82 | 173 | 24 | 14 | 0 | 707 | 293 |

## Subjectivity of aspect mentions

| aspect | Opinionated | Objective | (blank) |
|---|---|---|---|
| story | 377 | 17 | 8 |
| graphics_visuals | 375 | 6 | 0 |
| gameplay | 751 | 10 | 14 |
| controls | 210 | 4 | 4 |
| performance | 236 | 11 | 6 |
| audio | 263 | 2 | 1 |
| bugs_stability | 306 | 3 | 1 |
| online_multiplayer | 278 | 12 | 3 |

## Aspects mentioned per chunk

| aspects | chunks |
|---|---|
| 0 | 2 |
| 1 | 92 |
| 2 | 313 |
| 3 | 317 |
| 4 | 189 |
| 5 | 51 |
| 6 | 34 |
| 7 | 2 |

## Positive / negative mentions per game and aspect

| game | story | graphics_visuals | gameplay | controls | performance | audio | bugs_stability | online_multiplayer |
|---|---|---|---|---|---|---|---|---|
| Call of Duty: Warzone | 0 / 0 | 0 / 10 | 3 / 22 | 0 / 12 | 0 / 20 | 0 / 2 | 0 / 23 | 0 / 28 |
| Clair Obscur: Expedition 33 | 25 / 4 | 25 / 1 | 26 / 7 | 1 / 7 | 3 / 5 | 31 / 1 | 3 / 8 | 0 / 1 |
| Cyberpunk 2077 | 31 / 1 | 24 / 0 | 24 / 3 | 5 / 3 | 8 / 6 | 13 / 0 | 12 / 11 | 0 / 0 |
| Grand Theft Auto V Legacy | 18 / 2 | 8 / 0 | 15 / 5 | 0 / 4 | 4 / 2 | 2 / 0 | 0 / 11 | 10 / 8 |
| Hades II | 20 / 13 | 21 / 1 | 36 / 3 | 3 / 2 | 3 / 0 | 25 / 1 | 0 / 1 | 0 / 0 |
| Hollow Knight | 25 / 0 | 31 / 0 | 34 / 3 | 11 / 0 | 3 / 1 | 32 / 0 | 0 / 1 | 3 / 0 |
| Hollow Knight: Silksong | 22 / 0 | 27 / 0 | 33 / 5 | 15 / 0 | 5 / 0 | 30 / 0 | 7 / 0 | 0 / 0 |
| Left 4 Dead 2 | 11 / 2 | 11 / 3 | 34 / 2 | 1 / 2 | 9 / 0 | 5 / 1 | 1 / 7 | 22 / 8 |
| Monster Hunter Wilds | 8 / 9 | 10 / 8 | 24 / 5 | 5 / 10 | 12 / 12 | 4 / 3 | 9 / 8 | 8 / 13 |
| PAYDAY 3 | 3 / 2 | 11 / 2 | 13 / 15 | 7 / 2 | 7 / 6 | 8 / 3 | 4 / 10 | 7 / 10 |
| Red Dead Redemption 2 | 32 / 2 | 23 / 0 | 23 / 8 | 0 / 11 | 9 / 5 | 14 / 2 | 2 / 12 | 6 / 7 |
| Redfall | 7 / 14 | 12 / 9 | 17 / 12 | 2 / 6 | 6 / 8 | 3 / 4 | 3 / 21 | 6 / 9 |
| Resident Evil Requiem | 23 / 5 | 22 / 2 | 30 / 2 | 3 / 3 | 11 / 5 | 9 / 2 | 0 / 6 | 0 / 0 |
| Resident Evil Resistance | 2 / 0 | 5 / 1 | 12 / 16 | 0 / 4 | 0 / 3 | 2 / 1 | 1 / 7 | 6 / 29 |
| RollerCoaster Tycoon World | 0 / 0 | 1 / 11 | 8 / 12 | 0 / 16 | 3 / 15 | 0 / 4 | 4 / 36 | 0 / 0 |
| Spacebase DF-9 | 0 / 1 | 2 / 2 | 5 / 23 | 1 / 8 | 0 / 2 | 1 / 3 | 0 / 35 | 0 / 0 |
| Test Drive Unlimited Solar Crown | 2 / 7 | 15 / 17 | 11 / 22 | 11 / 10 | 2 / 23 | 11 / 10 | 0 / 18 | 0 / 14 |
| Umbrella Corps | 5 / 9 | 3 / 4 | 12 / 22 | 2 / 9 | 3 / 4 | 3 / 3 | 1 / 6 | 4 / 26 |
| Warhammer 40,000: Dawn of War III | 4 / 6 | 8 / 12 | 7 / 26 | 0 / 17 | 2 / 3 | 6 / 7 | 2 / 15 | 2 / 6 |
| Wolfenstein: Youngblood | 1 / 22 | 9 / 1 | 9 / 24 | 1 / 4 | 6 / 7 | 5 / 7 | 1 / 16 | 8 / 14 |
