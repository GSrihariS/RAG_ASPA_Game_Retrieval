# Retrieval results: 100 queries, 1000 annotated chunks

Relevant grade >= 1 for P / Recall / RR / R-Prec / bpref; nDCG uses grades 0-2. Candidates per retriever 300, reranker candidates 300, RRF k 60. `+qe` = hierarchical query expansion, `+filter` = game_name filter on the target games (cross-game queries are never filtered).

## Knowledge base and protocol

- The knowledge base is the full index: 12813 chunks from 9772 reviews of 20 games, not only the annotated set.
- The 1000 annotated chunks are a subset of it (same chunk IDs and text).
- The whole pipeline runs on the full knowledge base: BM25 and dense rank every chunk, RRF fuses their top 300 by real rank, and the reranker reorders the fused top 300. Unannotated chunks are dropped only from each final ranking (condensed lists, Sakai & Kando 2008), and only annotated chunks are scored.
- The evaluation depth (300 / 300) is deeper than the app (20 / 30): only ~8% of the index is annotated, so the app-depth top 30 keeps a median of 3 annotated chunks, too few for @10. The reranker scores each chunk independently, so the order of the annotated chunks does not depend on the unannotated ones around them.
- So the metrics measure how the annotated chunks are ordered relative to each other in a real, full-corpus ranking (BM25 statistics and the dense neighbourhood come from all chunks). Unannotated chunks in between are skipped, neither counted as hits nor as errors, so the scores are not the exact top-k a user sees in the app.
- bpref (Buckley & Voorhees 2004) uses only judged chunks by definition, so it is the same on the full and the condensed ranking; it is binary and reported next to the graded nDCG.

## Mean over all queries

| run | P@5 | P@10 | P@20 | Recall@5 | Recall@10 | Recall@20 | RR@20 | nDCG@5 | nDCG@10 | nDCG@20 | R-Prec | bpref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 0.5280 | 0.4400 | 0.3395 | 0.0821 | 0.1331 | 0.1971 | 0.7671 | 0.5258 | 0.4598 | 0.3878 | 0.2703 | 0.2263 |
| dense | 0.6460 | 0.5220 | 0.4230 | 0.1015 | 0.1588 | 0.2526 | 0.8534 | 0.6334 | 0.5455 | 0.4759 | 0.3387 | 0.2933 |
| hybrid_rrf | 0.6280 | 0.5190 | 0.4135 | 0.0998 | 0.1613 | 0.2449 | 0.8292 | 0.6184 | 0.5370 | 0.4670 | 0.2990 | 0.2524 |
| hybrid_rerank | 0.6580 | 0.5550 | 0.4125 | 0.1074 | 0.1710 | 0.2422 | 0.8908 | 0.6683 | 0.5860 | 0.4862 | 0.2680 | 0.2344 |
| bm25+qe | 0.3760 | 0.3250 | 0.2795 | 0.0556 | 0.0926 | 0.1526 | 0.6509 | 0.3780 | 0.3364 | 0.3041 | 0.2313 | 0.1855 |
| dense+qe | 0.5940 | 0.4820 | 0.3890 | 0.0912 | 0.1459 | 0.2308 | 0.8405 | 0.5868 | 0.5053 | 0.4395 | 0.3106 | 0.2700 |
| hybrid_rrf+qe | 0.5460 | 0.4400 | 0.3600 | 0.0853 | 0.1319 | 0.2101 | 0.8126 | 0.5450 | 0.4657 | 0.4049 | 0.2598 | 0.2131 |
| hybrid_rerank+qe | 0.6300 | 0.5190 | 0.3825 | 0.1009 | 0.1566 | 0.2182 | 0.8840 | 0.6442 | 0.5536 | 0.4556 | 0.2441 | 0.2140 |
| bm25+filter | 0.7000 | 0.6920 | 0.6540 | 0.1167 | 0.2303 | 0.4328 | 0.8240 | 0.6685 | 0.6615 | 0.6553 | 0.5409 | 0.5039 |
| dense+filter | 0.7480 | 0.7360 | 0.7015 | 0.1247 | 0.2464 | 0.4590 | 0.8768 | 0.7191 | 0.7118 | 0.7108 | 0.6618 | 0.6889 |
| hybrid_rrf+filter | 0.7460 | 0.7240 | 0.6950 | 0.1246 | 0.2399 | 0.4554 | 0.8520 | 0.7159 | 0.6963 | 0.7010 | 0.5729 | 0.5457 |
| hybrid_rerank+filter | 0.8100 | 0.7900 | 0.7060 | 0.1392 | 0.2691 | 0.4657 | 0.9337 | 0.7881 | 0.7693 | 0.7382 | 0.5252 | 0.5038 |
| bm25+qe+filter | 0.7680 | 0.7660 | 0.7180 | 0.1328 | 0.2658 | 0.4797 | 0.8791 | 0.7285 | 0.7284 | 0.7220 | 0.6457 | 0.6289 |
| dense+qe+filter | 0.7360 | 0.7430 | 0.7065 | 0.1222 | 0.2500 | 0.4648 | 0.8794 | 0.7074 | 0.7090 | 0.7133 | 0.6674 | 0.6969 |
| hybrid_rrf+qe+filter | 0.7820 | 0.7600 | 0.7270 | 0.1326 | 0.2588 | 0.4849 | 0.8845 | 0.7484 | 0.7326 | 0.7359 | 0.6079 | 0.6001 |
| hybrid_rerank+qe+filter | 0.8100 | 0.7970 | 0.7310 | 0.1388 | 0.2718 | 0.4828 | 0.9337 | 0.7870 | 0.7716 | 0.7558 | 0.5631 | 0.5464 |

Rerank candidate recall (relevant chunks in the RRF top-300): base 0.2970, +qe 0.2874, +filter 0.5960, +qe+filter 0.6522

## Annotated chunks per condensed ranking

Lists shorter than k count the missing ranks as nonrelevant.

| run | min | median | queries < 5 | queries < 10 | queries < 20 |
|---|---|---|---|---|---|
| bm25 | 87 | 388 | 0 | 0 | 0 |
| dense | 1000 | 1000 | 0 | 0 | 0 |
| hybrid_rrf | 21 | 43 | 0 | 0 | 0 |
| hybrid_rerank | 14 | 28 | 0 | 0 | 23 |
| bm25+qe | 106 | 478 | 0 | 0 | 0 |
| dense+qe | 1000 | 1000 | 0 | 0 | 0 |
| hybrid_rrf+qe | 29 | 62 | 0 | 0 | 0 |
| hybrid_rerank+qe | 16 | 35 | 0 | 0 | 5 (q07, q21, q52, q72, q81) |
| bm25+filter | 5 | 30 | 0 | 1 (q33) | 14 |
| dense+filter | 50 | 50 | 0 | 0 | 0 |
| hybrid_rrf+filter | 18 | 35 | 0 | 0 | 2 (q72, q81) |
| hybrid_rerank+filter | 12 | 28 | 0 | 0 | 19 |
| bm25+qe+filter | 13 | 35 | 0 | 0 | 4 (q21, q22, q33, q65) |
| dense+qe+filter | 50 | 50 | 0 | 0 | 0 |
| hybrid_rrf+qe+filter | 17 | 36 | 0 | 0 | 1 (q81) |
| hybrid_rerank+qe+filter | 11 | 31 | 0 | 0 | 14 |

## nDCG@10 by query type

| run | single_aspect (40) | aspect_sentiment (34) | multi_aspect (14) | cross_game (12) | all (100) |
|---|---|---|---|---|---|
| bm25 | 0.4345 | 0.3512 | 0.5755 | 0.7170 | 0.4598 |
| dense | 0.4976 | 0.4549 | 0.6579 | 0.8304 | 0.5455 |
| hybrid_rrf | 0.4939 | 0.4406 | 0.6545 | 0.8170 | 0.5370 |
| hybrid_rerank | 0.5287 | 0.5145 | 0.6715 | 0.8800 | 0.5860 |
| bm25+qe | 0.3141 | 0.2644 | 0.3160 | 0.6383 | 0.3364 |
| dense+qe | 0.4736 | 0.4321 | 0.5501 | 0.7661 | 0.5053 |
| hybrid_rrf+qe | 0.4230 | 0.3933 | 0.4939 | 0.7801 | 0.4657 |
| hybrid_rerank+qe | 0.5045 | 0.4713 | 0.6146 | 0.8788 | 0.5536 |
| bm25+filter | 0.6752 | 0.5466 | 0.8540 | 0.7170 | 0.6615 |
| dense+filter | 0.6933 | 0.6258 | 0.8720 | 0.8304 | 0.7118 |
| hybrid_rrf+filter | 0.6951 | 0.5878 | 0.8598 | 0.8170 | 0.6963 |
| hybrid_rerank+filter | 0.7594 | 0.6977 | 0.8769 | 0.8800 | 0.7693 |
| bm25+qe+filter | 0.7595 | 0.6452 | 0.9186 | 0.6383 | 0.7284 |
| dense+qe+filter | 0.6986 | 0.6389 | 0.8604 | 0.7661 | 0.7090 |
| hybrid_rrf+qe+filter | 0.7412 | 0.6370 | 0.8993 | 0.7801 | 0.7326 |
| hybrid_rerank+qe+filter | 0.7667 | 0.6959 | 0.8778 | 0.8788 | 0.7716 |

## R-Prec by query type

| run | single_aspect (40) | aspect_sentiment (34) | multi_aspect (14) | cross_game (12) | all (100) |
|---|---|---|---|---|---|
| bm25 | 0.2596 | 0.2265 | 0.2611 | 0.4404 | 0.2703 |
| dense | 0.2927 | 0.3179 | 0.3263 | 0.5654 | 0.3387 |
| hybrid_rrf | 0.2913 | 0.2991 | 0.3279 | 0.2909 | 0.2990 |
| hybrid_rerank | 0.2870 | 0.2668 | 0.2729 | 0.2024 | 0.2680 |
| bm25+qe | 0.1947 | 0.1834 | 0.1962 | 0.5297 | 0.2313 |
| dense+qe | 0.2635 | 0.2910 | 0.2852 | 0.5524 | 0.3106 |
| hybrid_rrf+qe | 0.2520 | 0.2615 | 0.2543 | 0.2877 | 0.2598 |
| hybrid_rerank+qe | 0.2489 | 0.2527 | 0.2432 | 0.2044 | 0.2441 |
| bm25+filter | 0.5358 | 0.5324 | 0.6624 | 0.4404 | 0.5409 |
| dense+filter | 0.6552 | 0.6271 | 0.8473 | 0.5654 | 0.6618 |
| hybrid_rrf+filter | 0.6156 | 0.5677 | 0.7053 | 0.2909 | 0.5729 |
| hybrid_rerank+filter | 0.5771 | 0.5469 | 0.6005 | 0.2024 | 0.5252 |
| bm25+qe+filter | 0.6556 | 0.6202 | 0.7788 | 0.5297 | 0.6457 |
| dense+qe+filter | 0.6633 | 0.6411 | 0.8414 | 0.5524 | 0.6674 |
| hybrid_rrf+qe+filter | 0.6551 | 0.6120 | 0.7373 | 0.2877 | 0.6079 |
| hybrid_rerank+qe+filter | 0.6250 | 0.5827 | 0.6463 | 0.2044 | 0.5631 |

## nDCG@10 per query

| query | type | rel | bm25 | dense | hybrid_rrf | hybrid_rerank | hybrid_rerank+qe | hybrid_rerank+qe+filter | query text |
|---|---|---|---|---|---|---|---|---|---|
| q01 | single_aspect | 35 | 0.5638 | 0.6332 | 0.6489 | 0.7084 | 0.6208 | 1.0000 | What do players think of the story and characters in Clair Obscur: Expedition 33? |
| q02 | single_aspect | 32 | 0.2863 | 0.6236 | 0.4422 | 0.6275 | 0.6275 | 1.0000 | How is the soundtrack in Hollow Knight? |
| q03 | single_aspect | 16 | 0.0948 | 0.0784 | 0.0948 | 0.2201 | 0.2201 | 0.3819 | How well does Cyberpunk 2077 run on PC these days? |
| q04 | single_aspect | 28 | 0.5370 | 0.6137 | 0.6817 | 0.6371 | 0.5645 | 0.7799 | Does Monster Hunter Wilds run smoothly, or is the frame rate a problem? |
| q05 | single_aspect | 29 | 0.4819 | 0.7034 | 0.5063 | 0.4085 | 0.4789 | 0.7820 | What is the multiplayer experience like in Call of Duty: Warzone? |
| q06 | single_aspect | 31 | 0.5175 | 0.5036 | 0.5077 | 0.7885 | 0.7156 | 0.9337 | Is Left 4 Dead 2 still fun to play with friends? |
| q07 | single_aspect | 38 | 0.3933 | 0.3590 | 0.4959 | 0.4729 | 0.3938 | 1.0000 | How do reviewers rate the narrative of Red Dead Redemption 2? |
| q08 | single_aspect | 45 | 0.9364 | 1.0000 | 1.0000 | 1.0000 | 0.8611 | 1.0000 | How does the combat feel in Hades II? |
| q09 | single_aspect | 17 | 0.6691 | 0.5447 | 0.6691 | 0.6805 | 0.6805 | 0.7722 | How do the controls feel in Hollow Knight: Silksong? |
| q10 | single_aspect | 28 | 0.2835 | 0.3850 | 0.3495 | 0.2758 | 0.1420 | 0.8044 | Is Test Drive Unlimited Solar Crown well optimized? |
| q11 | single_aspect | 18 | 0.6911 | 0.5642 | 0.6562 | 0.7034 | 0.7008 | 0.8913 | RollerCoaster Tycoon World camera and building controls |
| q12 | single_aspect | 44 | 0.7281 | 0.7936 | 0.7859 | 0.8753 | 0.7792 | 0.8753 | What do longtime fans think of the gameplay changes in Warhammer 40,000: Dawn of War III? |
| q13 | single_aspect | 25 | 0.0000 | 0.3500 | 0.0948 | 0.2900 | 0.1799 | 0.5677 | What do players say about the visuals of Resident Evil Requiem? |
| q14 | single_aspect | 29 | 0.8122 | 0.7846 | 0.8707 | 0.6686 | 0.8517 | 0.8067 | What is GTA Online like in Grand Theft Auto V Legacy? |
| q15 | single_aspect | 44 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | PAYDAY 3 heist gameplay |
| q16 | single_aspect | 25 | 0.4035 | 0.4226 | 0.3590 | 0.3590 | 0.3590 | 0.9048 | Does Redfall have a good story? |
| q17 | single_aspect | 45 | 0.6540 | 0.5756 | 0.7081 | 0.7176 | 0.7202 | 0.9266 | Umbrella Corps gameplay mechanics |
| q18 | single_aspect | 33 | 0.3437 | 0.2489 | 0.3125 | 0.5107 | 0.4698 | 0.8900 | music in Clair Obscur Expedition 33 |
| q19 | single_aspect | 25 | 0.7020 | 0.6552 | 0.6653 | 0.7333 | 0.7333 | 0.8910 | How does co-op work in Wolfenstein: Youngblood? |
| q20 | single_aspect | 31 | 0.2090 | 0.4153 | 0.2547 | 0.4249 | 0.4249 | 0.6754 | Hollow Knight art style |
| q21 | single_aspect | 34 | 0.1642 | 0.5645 | 0.3660 | 0.5965 | 0.5965 | 0.8268 | Is there enough to do in Spacebase DF-9? |
| q22 | single_aspect | 38 | 0.6300 | 0.7859 | 0.7126 | 0.7917 | 0.7917 | 0.9432 | How is the asymmetric gameplay in Resident Evil Resistance? |
| q23 | aspect_sentiment | 35 | 0.0000 | 0.3938 | 0.2083 | 0.3571 | 0.2935 | 0.9149 | Why do players complain about crashes and bugs in Spacebase DF-9? |
| q24 | aspect_sentiment | 36 | 0.5200 | 0.7975 | 0.6325 | 0.7682 | 0.7682 | 0.8390 | What technical problems ruin RollerCoaster Tycoon World? |
| q25 | aspect_sentiment | 27 | 0.4323 | 0.4249 | 0.4323 | 0.6275 | 0.6016 | 0.7116 | What do fans love about how Silksong looks? |
| q26 | aspect_sentiment | 35 | 0.6706 | 0.7792 | 0.6751 | 0.8023 | 0.6422 | 0.9576 | What do players praise about the story and characters of Cyberpunk 2077? |
| q27 | aspect_sentiment | 26 | 0.3597 | 0.3364 | 0.3567 | 0.7001 | 0.4584 | 0.7001 | Why is the story of Wolfenstein: Youngblood criticized? |
| q28 | aspect_sentiment | 39 | 0.2568 | 0.6076 | 0.4615 | 0.4805 | 0.3618 | 0.7406 | complaints about matchmaking and servers in Resident Evil Resistance |
| q29 | aspect_sentiment | 14 | 0.0948 | 0.0734 | 0.0948 | 0.2686 | 0.1884 | 0.8166 | What frustrates players about the always-online requirement in Test Drive Unlimited Solar Crown? |
| q30 | aspect_sentiment | 26 | 0.6616 | 0.7254 | 0.7922 | 0.7900 | 0.7900 | 0.7900 | Why do players love the music in Hades II? |
| q31 | aspect_sentiment | 23 | 0.1478 | 0.6911 | 0.6055 | 0.5591 | 0.5591 | 0.7105 | What bugs and glitches do players run into in Call of Duty: Warzone? |
| q32 | aspect_sentiment | 11 | 0.1299 | 0.0851 | 0.0784 | 0.1100 | 0.0948 | 0.1682 | What do players dislike about the controls and camera in Monster Hunter Wilds? |
| q33 | aspect_sentiment | 23 | 0.3149 | 0.3052 | 0.3301 | 0.3590 | 0.3590 | 0.7968 | Redfall broken and buggy at launch |
| q34 | aspect_sentiment | 17 | 0.2782 | 0.4698 | 0.3437 | 0.2867 | 0.1389 | 0.5578 | What problems do players have with the controls in Warhammer 40,000: Dawn of War III? |
| q35 | aspect_sentiment | 13 | 0.0000 | 0.2240 | 0.2051 | 0.3590 | 0.3590 | 0.5405 | Why do people find Red Dead Redemption 2 clunky to play? |
| q36 | aspect_sentiment | 39 | 0.4134 | 0.8058 | 0.6389 | 0.7915 | 0.5638 | 0.9432 | What makes Left 4 Dead 2 so replayable? |
| q37 | multi_aspect | 36 | 0.6722 | 0.6353 | 0.6835 | 0.6137 | 0.7008 | 0.9576 | How do the single-player story and GTA Online compare in Grand Theft Auto V Legacy? |
| q38 | multi_aspect | 25 | 0.5101 | 0.4441 | 0.5677 | 0.7223 | 0.7968 | 0.7968 | Are the PAYDAY 3 servers stable, or is the game full of bugs? |
| q39 | multi_aspect | 36 | 0.4572 | 0.5573 | 0.4925 | 0.6659 | 0.3052 | 0.7174 | How are the story and sound design in Resident Evil Requiem? |
| q40 | multi_aspect | 40 | 0.5225 | 0.4690 | 0.6178 | 0.5763 | 0.5763 | 0.8611 | How do the controls and online matches feel in Umbrella Corps? |
| q41 | multi_aspect | 50 | 1.0000 | 0.7543 | 0.8630 | 0.8522 | 0.8415 | 1.0000 | How hard is Hollow Knight: Silksong, and are the controls precise enough for it? |
| q42 | multi_aspect | 36 | 0.7792 | 0.7721 | 0.7752 | 0.6521 | 0.4153 | 0.9266 | Are the graphics of Monster Hunter Wilds worth the performance cost? |
| q43 | cross_game | 260 | 0.9364 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | Which games are so buggy that they keep crashing? |
| q44 | cross_game | 212 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | games with an amazing soundtrack |
| q45 | cross_game | 211 | 0.8879 | 0.8650 | 0.8533 | 1.0000 | 1.0000 | 1.0000 | Games where cheaters and bad matchmaking ruin the multiplayer |
| q46 | cross_game | 157 | 0.4819 | 0.7163 | 0.6546 | 0.9477 | 0.8796 | 0.8796 | Which games have poor optimization and low FPS even on good hardware? |
| q47 | cross_game | 303 | 0.7314 | 0.8533 | 0.6897 | 0.7973 | 0.7869 | 0.7869 | Games with a memorable, emotional story |
| q48 | cross_game | 297 | 0.7799 | 1.0000 | 0.9477 | 0.9074 | 0.9074 | 0.9074 | Which games have breathtaking visuals and art direction? |
| q49 | cross_game | 150 | 0.8659 | 0.8580 | 0.9266 | 0.8416 | 0.9052 | 0.9052 | games with clunky, unresponsive controls |
| q50 | cross_game | 538 | 0.8341 | 0.9052 | 0.9337 | 0.9368 | 0.9511 | 0.9511 | Which games have the most satisfying combat? |
| q51 | single_aspect | 21 | 0.0463 | 0.3668 | 0.3195 | 0.0261 | 0.0221 | 0.3334 | Does Call of Duty: Warzone have stuttering or FPS drops? |
| q52 | single_aspect | 43 | 1.0000 | 0.8580 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | How does the turn-based combat with parrying work in Clair Obscur: Expedition 33? |
| q53 | single_aspect | 13 | 0.1884 | 0.1799 | 0.2646 | 0.2999 | 0.2999 | 0.6438 | What do people think of the soundtrack and radio stations in Cyberpunk 2077? |
| q54 | single_aspect | 23 | 0.2201 | 0.3647 | 0.2201 | 0.2201 | 0.2201 | 0.5993 | Is the Grand Theft Auto V Legacy campaign worth playing? |
| q55 | single_aspect | 22 | 0.5581 | 0.6844 | 0.6570 | 0.8415 | 0.8415 | 0.8415 | Hades II art and character designs |
| q56 | single_aspect | 47 | 0.1003 | 0.4490 | 0.2162 | 0.2996 | 0.2996 | 0.8044 | How difficult is Hollow Knight for new players? |
| q57 | single_aspect | 19 | 0.3437 | 0.4192 | 0.5609 | 0.2971 | 0.3042 | 0.4340 | Does Left 4 Dead 2 still hold up visually? |
| q58 | single_aspect | 22 | 0.6086 | 0.6780 | 0.6489 | 0.6300 | 0.5326 | 0.8365 | How is hunting with friends online in Monster Hunter Wilds? |
| q59 | single_aspect | 14 | 0.2201 | 0.2240 | 0.3149 | 0.3938 | 0.3938 | 0.3996 | How does PAYDAY 3 run on PC? |
| q60 | single_aspect | 24 | 0.2122 | 0.2240 | 0.2064 | 0.0636 | 0.1357 | 0.7799 | Red Dead Redemption 2 open world scenery and graphics |
| q61 | single_aspect | 39 | 0.2900 | 0.3590 | 0.4374 | 0.4323 | 0.4374 | 1.0000 | What is the gameplay loop like in Redfall? |
| q62 | single_aspect | 18 | 0.5510 | 0.3621 | 0.4153 | 0.6275 | 0.5271 | 0.8604 | Is Resident Evil Requiem well optimized for PC? |
| q63 | single_aspect | 8 | 0.0000 | 0.0000 | 0.0000 | 0.0843 | 0.0000 | 0.0798 | Is Resident Evil Resistance stable, or does it have technical issues? |
| q64 | single_aspect | 23 | 0.7386 | 0.7990 | 0.8512 | 0.9052 | 0.9052 | 0.9052 | Is it fun to build parks in RollerCoaster Tycoon World? |
| q65 | single_aspect | 10 | 0.1055 | 0.2734 | 0.2681 | 0.2622 | 0.0766 | 0.3720 | How is the interface and control scheme in Spacebase DF-9? |
| q66 | single_aspect | 24 | 0.6141 | 0.4383 | 0.6023 | 0.5730 | 0.5730 | 0.6691 | Is there much of a story in Hollow Knight: Silksong? |
| q67 | single_aspect | 16 | 0.3640 | 0.3070 | 0.3476 | 0.3223 | 0.3223 | 0.5949 | Does Umbrella Corps have any story or lore? |
| q68 | single_aspect | 24 | 0.1167 | 0.3128 | 0.2436 | 0.3786 | 0.3786 | 0.8604 | Dawn of War III art style and visuals |
| q69 | aspect_sentiment | 27 | 0.5638 | 0.4690 | 0.5707 | 0.5922 | 0.5006 | 0.8910 | What do players praise about the art direction of Clair Obscur: Expedition 33? |
| q70 | aspect_sentiment | 29 | 0.2614 | 0.5763 | 0.4584 | 0.7084 | 0.7084 | 0.9266 | Why do fans love the lore and world of Hollow Knight? |
| q71 | aspect_sentiment | 30 | 0.5263 | 0.3938 | 0.5361 | 0.6489 | 0.6489 | 0.7788 | What do players like about the music in Hollow Knight: Silksong? |
| q72 | aspect_sentiment | 36 | 0.4249 | 0.5638 | 0.6325 | 0.6372 | 0.6532 | 0.9511 | Why is Arthur Morgan's story so loved in Red Dead Redemption 2? |
| q73 | aspect_sentiment | 25 | 0.5036 | 0.5225 | 0.5225 | 0.3120 | 0.3223 | 0.5211 | How good does Night City look in Cyberpunk 2077? |
| q74 | aspect_sentiment | 25 | 0.4374 | 0.4501 | 0.3882 | 0.6719 | 0.6719 | 0.6835 | What do players enjoy about the characters and dialogue in Hades II? |
| q75 | aspect_sentiment | 28 | 0.2489 | 0.5988 | 0.5186 | 0.6364 | 0.6242 | 0.6512 | What do fans like about the story of Resident Evil Requiem? |
| q76 | aspect_sentiment | 11 | 0.0990 | 0.0483 | 0.1008 | 0.0766 | 0.0766 | 0.2941 | Why does Left 4 Dead 2 run so well even on old PCs? |
| q77 | aspect_sentiment | 9 | 0.2467 | 0.2299 | 0.3700 | 0.3421 | 0.3529 | 0.8519 | What do players like about the graphics of Grand Theft Auto V Legacy? |
| q78 | aspect_sentiment | 13 | 0.2985 | 0.3601 | 0.3687 | 0.4815 | 0.4153 | 0.5763 | What do players enjoy about the engine sounds and music in Test Drive Unlimited Solar Crown? |
| q79 | aspect_sentiment | 32 | 0.6862 | 0.6774 | 0.6723 | 0.7523 | 0.7523 | 0.7768 | What do players enjoy about the hunts and weapons in Monster Hunter Wilds? |
| q80 | aspect_sentiment | 12 | 0.4577 | 0.3149 | 0.4085 | 0.5541 | 0.5541 | 0.6898 | Why do players say Hollow Knight's controls feel tight and responsive? |
| q81 | aspect_sentiment | 32 | 0.2079 | 0.5598 | 0.3257 | 0.4652 | 0.4210 | 0.5427 | What do players dislike about the driving and progression in Test Drive Unlimited Solar Crown? |
| q82 | aspect_sentiment | 15 | 0.2048 | 0.3667 | 0.2743 | 0.3689 | 0.3747 | 0.3785 | Why does RollerCoaster Tycoon World lag with big parks? |
| q83 | aspect_sentiment | 31 | 0.4857 | 0.4974 | 0.5605 | 0.5326 | 0.5326 | 0.6088 | Why is it so hard to find a match in Umbrella Corps? |
| q84 | aspect_sentiment | 18 | 0.4780 | 0.6325 | 0.6422 | 0.5175 | 0.5395 | 0.5387 | What do players dislike about the story of Hades II compared to the first game? |
| q85 | aspect_sentiment | 32 | 0.6313 | 0.4189 | 0.5214 | 0.7893 | 0.7893 | 0.8529 | Why do players dislike the leveling and bullet-sponge enemies in Wolfenstein: Youngblood? |
| q86 | aspect_sentiment | 12 | 0.3448 | 0.4413 | 0.4440 | 0.4474 | 0.4413 | 0.8023 | What do players criticize about Redfall's visuals? |
| q87 | aspect_sentiment | 15 | 0.2436 | 0.2685 | 0.4553 | 0.2122 | 0.2051 | 0.7354 | What bugs and crashes do players report in Warhammer 40,000: Dawn of War III? |
| q88 | aspect_sentiment | 31 | 0.3104 | 0.3585 | 0.3550 | 0.4867 | 0.2609 | 0.4231 | What do players dislike about the progression and heists in PAYDAY 3? |
| q89 | multi_aspect | 32 | 0.1546 | 0.2832 | 0.2494 | 0.2083 | 0.2025 | 0.9149 | Is Cyberpunk 2077 finally fixed: does it run well, and are the bugs gone? |
| q90 | multi_aspect | 42 | 0.5638 | 0.8553 | 0.8512 | 0.7752 | 0.7885 | 0.9337 | How do the gunplay and visuals of Wolfenstein: Youngblood hold up? |
| q91 | multi_aspect | 40 | 0.4690 | 0.7084 | 0.6844 | 0.8007 | 0.8007 | 0.9364 | Is Resident Evil Resistance balanced, and does it work without technical problems? |
| q92 | multi_aspect | 48 | 0.6688 | 0.8604 | 0.8007 | 0.9364 | 0.8701 | 1.0000 | Is Spacebase DF-9 unfinished: how much content is there, and does it crash? |
| q93 | multi_aspect | 46 | 0.5622 | 1.0000 | 0.7885 | 0.8486 | 0.6274 | 1.0000 | How do the driving controls and frame rate feel in Test Drive Unlimited Solar Crown? |
| q94 | multi_aspect | 44 | 0.6204 | 0.6911 | 0.6489 | 0.7818 | 0.7850 | 1.0000 | How do the story and combat of Clair Obscur: Expedition 33 compare? |
| q95 | multi_aspect | 45 | 0.7910 | 0.8572 | 0.7485 | 0.8643 | 0.7917 | 0.9306 | How are the multiplayer matches and MOBA-style gameplay in Dawn of War III? |
| q96 | multi_aspect | 35 | 0.2860 | 0.3223 | 0.3922 | 0.1029 | 0.1029 | 0.3142 | Is Call of Duty: Warzone stable and smooth to play? |
| q97 | cross_game | 58 | 0.3169 | 0.5331 | 0.4881 | 0.6370 | 0.6300 | 0.6300 | Which games are polished and almost free of bugs? |
| q98 | cross_game | 120 | 0.4383 | 0.6036 | 0.5626 | 0.7780 | 0.7754 | 0.7754 | Which games are great to play co-op with friends? |
| q99 | cross_game | 62 | 0.6770 | 0.7975 | 0.8669 | 0.7870 | 0.8533 | 0.8533 | games with bad voice acting or annoying sound |
| q100 | cross_game | 126 | 0.6543 | 0.8333 | 0.8800 | 0.9266 | 0.8564 | 0.8564 | Which games are well optimized and run smoothly? |
