# Retrieval results: 100 queries, 1000 annotated chunks

Relevant grade >= 1 for P / Recall / RR / R-Prec; nDCG uses grades 0-2. Candidates per retriever 20, reranker candidates 30, RRF k 60. `+qe` = hierarchical query expansion, `+filter` = game_name filter on the target games (cross-game queries are never filtered).

## Knowledge base and protocol

- The knowledge base is the full index: 12813 chunks from 9772 reviews of 20 games, not only the annotated set.
- The 1000 annotated chunks are a subset of it (same chunk IDs and text).
- Every retriever ranks the whole knowledge base; unannotated chunks are then dropped from the ranking (condensed lists) and only annotated chunks are scored.
- So the metrics measure how the annotated chunks are ordered relative to each other in a real, full-corpus ranking (BM25 statistics and the dense neighbourhood come from all chunks). Unannotated chunks in between are skipped, neither counted as hits nor as errors, so the scores are not the exact top-k a user sees in the app.

## Mean over all queries

| run | P@5 | P@10 | P@20 | Recall@5 | Recall@10 | Recall@20 | RR@20 | nDCG@5 | nDCG@10 | nDCG@20 | R-Prec |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bm25 | 0.5280 | 0.4400 | 0.3395 | 0.0821 | 0.1331 | 0.1971 | 0.7671 | 0.5258 | 0.4598 | 0.3878 | 0.2703 |
| dense | 0.6460 | 0.5220 | 0.4230 | 0.1015 | 0.1588 | 0.2526 | 0.8534 | 0.6334 | 0.5455 | 0.4759 | 0.3387 |
| hybrid_rrf | 0.6140 | 0.5180 | 0.4090 | 0.0974 | 0.1609 | 0.2412 | 0.8281 | 0.6038 | 0.5331 | 0.4616 | 0.2695 |
| hybrid_rerank | 0.6560 | 0.5430 | 0.4210 | 0.1071 | 0.1679 | 0.2502 | 0.8852 | 0.6640 | 0.5742 | 0.4895 | 0.2700 |
| bm25+qe | 0.3760 | 0.3250 | 0.2795 | 0.0556 | 0.0926 | 0.1526 | 0.6509 | 0.3780 | 0.3364 | 0.3041 | 0.2313 |
| dense+qe | 0.5940 | 0.4820 | 0.3890 | 0.0912 | 0.1459 | 0.2308 | 0.8405 | 0.5868 | 0.5053 | 0.4395 | 0.3106 |
| hybrid_rrf+qe | 0.5300 | 0.4530 | 0.3560 | 0.0822 | 0.1361 | 0.2052 | 0.7995 | 0.5328 | 0.4722 | 0.4004 | 0.2383 |
| hybrid_rerank+qe | 0.6240 | 0.5150 | 0.3860 | 0.1008 | 0.1574 | 0.2271 | 0.8768 | 0.6406 | 0.5517 | 0.4588 | 0.2387 |
| bm25+filter | 0.7000 | 0.6920 | 0.6540 | 0.1167 | 0.2303 | 0.4328 | 0.8240 | 0.6685 | 0.6615 | 0.6553 | 0.5409 |
| dense+filter | 0.7480 | 0.7360 | 0.7015 | 0.1247 | 0.2464 | 0.4590 | 0.8768 | 0.7191 | 0.7118 | 0.7108 | 0.6618 |
| hybrid_rrf+filter | 0.7520 | 0.7290 | 0.6960 | 0.1258 | 0.2431 | 0.4562 | 0.8528 | 0.7161 | 0.7000 | 0.7027 | 0.5117 |
| hybrid_rerank+filter | 0.8060 | 0.7920 | 0.7285 | 0.1385 | 0.2692 | 0.4836 | 0.9337 | 0.7851 | 0.7692 | 0.7510 | 0.5223 |
| bm25+qe+filter | 0.7680 | 0.7660 | 0.7180 | 0.1328 | 0.2658 | 0.4797 | 0.8791 | 0.7285 | 0.7284 | 0.7220 | 0.6457 |
| dense+qe+filter | 0.7360 | 0.7430 | 0.7065 | 0.1222 | 0.2500 | 0.4648 | 0.8794 | 0.7074 | 0.7090 | 0.7133 | 0.6674 |
| hybrid_rrf+qe+filter | 0.7840 | 0.7610 | 0.7270 | 0.1340 | 0.2575 | 0.4866 | 0.8760 | 0.7490 | 0.7307 | 0.7328 | 0.5420 |
| hybrid_rerank+qe+filter | 0.8040 | 0.7890 | 0.7435 | 0.1376 | 0.2692 | 0.4950 | 0.9337 | 0.7805 | 0.7664 | 0.7623 | 0.5507 |

Rerank candidate recall (relevant chunks in the RRF top-30): base 0.2933, +qe 0.2630, +filter 0.5751, +qe+filter 0.6139

## nDCG@10 by query type

| run | single_aspect (40) | aspect_sentiment (34) | multi_aspect (14) | cross_game (12) | all (100) |
|---|---|---|---|---|---|
| bm25 | 0.4345 | 0.3512 | 0.5755 | 0.7170 | 0.4598 |
| dense | 0.4976 | 0.4549 | 0.6579 | 0.8304 | 0.5455 |
| hybrid_rrf | 0.4763 | 0.4448 | 0.6679 | 0.8149 | 0.5331 |
| hybrid_rerank | 0.5153 | 0.5084 | 0.6350 | 0.8865 | 0.5742 |
| bm25+qe | 0.3141 | 0.2644 | 0.3160 | 0.6383 | 0.3364 |
| dense+qe | 0.4736 | 0.4321 | 0.5501 | 0.7661 | 0.5053 |
| hybrid_rrf+qe | 0.4306 | 0.3959 | 0.5118 | 0.7812 | 0.4722 |
| hybrid_rerank+qe | 0.5070 | 0.4806 | 0.5987 | 0.8474 | 0.5517 |
| bm25+filter | 0.6752 | 0.5466 | 0.8540 | 0.7170 | 0.6615 |
| dense+filter | 0.6933 | 0.6258 | 0.8720 | 0.8304 | 0.7118 |
| hybrid_rrf+filter | 0.7010 | 0.5969 | 0.8491 | 0.8149 | 0.7000 |
| hybrid_rerank+filter | 0.7610 | 0.6923 | 0.8789 | 0.8865 | 0.7692 |
| bm25+qe+filter | 0.7595 | 0.6452 | 0.9186 | 0.6383 | 0.7284 |
| dense+qe+filter | 0.6986 | 0.6389 | 0.8604 | 0.7661 | 0.7090 |
| hybrid_rrf+qe+filter | 0.7430 | 0.6332 | 0.8891 | 0.7812 | 0.7307 |
| hybrid_rerank+qe+filter | 0.7639 | 0.6929 | 0.8823 | 0.8474 | 0.7664 |

## R-Prec by query type

| run | single_aspect (40) | aspect_sentiment (34) | multi_aspect (14) | cross_game (12) | all (100) |
|---|---|---|---|---|---|
| bm25 | 0.2596 | 0.2265 | 0.2611 | 0.4404 | 0.2703 |
| dense | 0.2927 | 0.3179 | 0.3263 | 0.5654 | 0.3387 |
| hybrid_rrf | 0.2837 | 0.2893 | 0.2899 | 0.1417 | 0.2695 |
| hybrid_rerank | 0.2896 | 0.2916 | 0.2826 | 0.1291 | 0.2700 |
| bm25+qe | 0.1947 | 0.1834 | 0.1962 | 0.5297 | 0.2313 |
| dense+qe | 0.2635 | 0.2910 | 0.2852 | 0.5524 | 0.3106 |
| hybrid_rrf+qe | 0.2462 | 0.2664 | 0.2310 | 0.1403 | 0.2383 |
| hybrid_rerank+qe | 0.2557 | 0.2683 | 0.2144 | 0.1269 | 0.2387 |
| bm25+filter | 0.5358 | 0.5324 | 0.6624 | 0.4404 | 0.5409 |
| dense+filter | 0.6552 | 0.6271 | 0.8473 | 0.5654 | 0.6618 |
| hybrid_rrf+filter | 0.5734 | 0.5413 | 0.5808 | 0.1417 | 0.5117 |
| hybrid_rerank+filter | 0.5775 | 0.5720 | 0.5808 | 0.1291 | 0.5223 |
| bm25+qe+filter | 0.6556 | 0.6202 | 0.7788 | 0.5297 | 0.6457 |
| dense+qe+filter | 0.6633 | 0.6411 | 0.8414 | 0.5524 | 0.6674 |
| hybrid_rrf+qe+filter | 0.6041 | 0.5840 | 0.6069 | 0.1403 | 0.5420 |
| hybrid_rerank+qe+filter | 0.6139 | 0.6038 | 0.6041 | 0.1269 | 0.5507 |

## nDCG@10 per query

| query | type | rel | bm25 | dense | hybrid_rrf | hybrid_rerank | hybrid_rerank+qe | hybrid_rerank+qe+filter | query text |
|---|---|---|---|---|---|---|---|---|---|
| q01 | single_aspect | 35 | 0.5638 | 0.6332 | 0.6489 | 0.7034 | 0.6995 | 1.0000 | What do players think of the story and characters in Clair Obscur: Expedition 33? |
| q02 | single_aspect | 32 | 0.2863 | 0.6236 | 0.4636 | 0.6275 | 0.6325 | 1.0000 | How is the soundtrack in Hollow Knight? |
| q03 | single_aspect | 16 | 0.0948 | 0.0784 | 0.1100 | 0.2201 | 0.2201 | 0.3819 | How well does Cyberpunk 2077 run on PC these days? |
| q04 | single_aspect | 28 | 0.5370 | 0.6137 | 0.5479 | 0.4983 | 0.4983 | 0.7799 | Does Monster Hunter Wilds run smoothly, or is the frame rate a problem? |
| q05 | single_aspect | 29 | 0.4819 | 0.7034 | 0.3719 | 0.4085 | 0.5868 | 0.7820 | What is the multiplayer experience like in Call of Duty: Warzone? |
| q06 | single_aspect | 31 | 0.5175 | 0.5036 | 0.4537 | 0.7156 | 0.7156 | 0.9337 | Is Left 4 Dead 2 still fun to play with friends? |
| q07 | single_aspect | 38 | 0.3933 | 0.3590 | 0.4722 | 0.3301 | 0.3301 | 1.0000 | How do reviewers rate the narrative of Red Dead Redemption 2? |
| q08 | single_aspect | 45 | 0.9364 | 1.0000 | 1.0000 | 1.0000 | 0.8611 | 1.0000 | How does the combat feel in Hades II? |
| q09 | single_aspect | 17 | 0.6691 | 0.5447 | 0.7066 | 0.6805 | 0.6805 | 0.7722 | How do the controls feel in Hollow Knight: Silksong? |
| q10 | single_aspect | 28 | 0.2835 | 0.3850 | 0.3687 | 0.2083 | 0.1420 | 0.8044 | Is Test Drive Unlimited Solar Crown well optimized? |
| q11 | single_aspect | 18 | 0.6911 | 0.5642 | 0.6577 | 0.7337 | 0.6168 | 0.8238 | RollerCoaster Tycoon World camera and building controls |
| q12 | single_aspect | 44 | 0.7281 | 0.7936 | 0.7917 | 0.6624 | 0.8023 | 0.8753 | What do longtime fans think of the gameplay changes in Warhammer 40,000: Dawn of War III? |
| q13 | single_aspect | 25 | 0.0000 | 0.3500 | 0.0000 | 0.3476 | 0.2533 | 0.5677 | What do players say about the visuals of Resident Evil Requiem? |
| q14 | single_aspect | 29 | 0.8122 | 0.7846 | 0.9511 | 0.7354 | 0.8517 | 0.8067 | What is GTA Online like in Grand Theft Auto V Legacy? |
| q15 | single_aspect | 44 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | PAYDAY 3 heist gameplay |
| q16 | single_aspect | 25 | 0.4035 | 0.4226 | 0.3590 | 0.3590 | 0.3590 | 0.9511 | Does Redfall have a good story? |
| q17 | single_aspect | 45 | 0.6540 | 0.5756 | 0.6992 | 0.6540 | 0.7202 | 0.9266 | Umbrella Corps gameplay mechanics |
| q18 | single_aspect | 33 | 0.3437 | 0.2489 | 0.3273 | 0.4600 | 0.4632 | 0.8900 | music in Clair Obscur Expedition 33 |
| q19 | single_aspect | 25 | 0.7020 | 0.6552 | 0.5638 | 0.7333 | 0.7333 | 0.8910 | How does co-op work in Wolfenstein: Youngblood? |
| q20 | single_aspect | 31 | 0.2090 | 0.4153 | 0.2122 | 0.4249 | 0.4690 | 0.7417 | Hollow Knight art style |
| q21 | single_aspect | 34 | 0.1642 | 0.5645 | 0.3312 | 0.5894 | 0.5894 | 0.8268 | Is there enough to do in Spacebase DF-9? |
| q22 | single_aspect | 38 | 0.6300 | 0.7859 | 0.6489 | 0.9306 | 0.7968 | 0.9432 | How is the asymmetric gameplay in Resident Evil Resistance? |
| q23 | aspect_sentiment | 35 | 0.0000 | 0.3938 | 0.2646 | 0.3747 | 0.1420 | 0.9149 | Why do players complain about crashes and bugs in Spacebase DF-9? |
| q24 | aspect_sentiment | 36 | 0.5200 | 0.7975 | 0.6962 | 0.7656 | 0.7530 | 0.8390 | What technical problems ruin RollerCoaster Tycoon World? |
| q25 | aspect_sentiment | 27 | 0.4323 | 0.4249 | 0.4252 | 0.6275 | 0.6016 | 0.7116 | What do fans love about how Silksong looks? |
| q26 | aspect_sentiment | 35 | 0.6706 | 0.7792 | 0.7413 | 0.7337 | 0.7116 | 0.9576 | What do players praise about the story and characters of Cyberpunk 2077? |
| q27 | aspect_sentiment | 26 | 0.3597 | 0.3364 | 0.4261 | 0.7001 | 0.5302 | 0.7001 | Why is the story of Wolfenstein: Youngblood criticized? |
| q28 | aspect_sentiment | 39 | 0.2568 | 0.6076 | 0.4519 | 0.4805 | 0.4315 | 0.7406 | complaints about matchmaking and servers in Resident Evil Resistance |
| q29 | aspect_sentiment | 14 | 0.0948 | 0.0734 | 0.1389 | 0.1884 | 0.2048 | 0.8166 | What frustrates players about the always-online requirement in Test Drive Unlimited Solar Crown? |
| q30 | aspect_sentiment | 26 | 0.6616 | 0.7254 | 0.7126 | 0.7900 | 0.7900 | 0.7900 | Why do players love the music in Hades II? |
| q31 | aspect_sentiment | 23 | 0.1478 | 0.6911 | 0.4517 | 0.5022 | 0.4883 | 0.7105 | What bugs and glitches do players run into in Call of Duty: Warzone? |
| q32 | aspect_sentiment | 11 | 0.1299 | 0.0851 | 0.1447 | 0.0948 | 0.0851 | 0.1682 | What do players dislike about the controls and camera in Monster Hunter Wilds? |
| q33 | aspect_sentiment | 23 | 0.3149 | 0.3052 | 0.3590 | 0.3590 | 0.3590 | 0.7968 | Redfall broken and buggy at launch |
| q34 | aspect_sentiment | 17 | 0.2782 | 0.4698 | 0.3437 | 0.2785 | 0.2051 | 0.5578 | What problems do players have with the controls in Warhammer 40,000: Dawn of War III? |
| q35 | aspect_sentiment | 13 | 0.0000 | 0.2240 | 0.1610 | 0.3590 | 0.3590 | 0.4769 | Why do people find Red Dead Redemption 2 clunky to play? |
| q36 | aspect_sentiment | 39 | 0.4134 | 0.8058 | 0.6354 | 0.6558 | 0.5638 | 0.9432 | What makes Left 4 Dead 2 so replayable? |
| q37 | multi_aspect | 36 | 0.6722 | 0.6353 | 0.7165 | 0.6137 | 0.6137 | 0.9576 | How do the single-player story and GTA Online compare in Grand Theft Auto V Legacy? |
| q38 | multi_aspect | 25 | 0.5101 | 0.4441 | 0.6316 | 0.7968 | 0.7223 | 0.7968 | Are the PAYDAY 3 servers stable, or is the game full of bugs? |
| q39 | multi_aspect | 36 | 0.4572 | 0.5573 | 0.4857 | 0.4055 | 0.3052 | 0.7201 | How are the story and sound design in Resident Evil Requiem? |
| q40 | multi_aspect | 40 | 0.5225 | 0.4690 | 0.5541 | 0.5763 | 0.4983 | 0.8611 | How do the controls and online matches feel in Umbrella Corps? |
| q41 | multi_aspect | 50 | 1.0000 | 0.7543 | 0.9306 | 0.8522 | 0.7779 | 1.0000 | How hard is Hollow Knight: Silksong, and are the controls precise enough for it? |
| q42 | multi_aspect | 36 | 0.7792 | 0.7721 | 0.7779 | 0.5737 | 0.4153 | 0.9216 | Are the graphics of Monster Hunter Wilds worth the performance cost? |
| q43 | cross_game | 260 | 0.9364 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | Which games are so buggy that they keep crashing? |
| q44 | cross_game | 212 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | games with an amazing soundtrack |
| q45 | cross_game | 211 | 0.8879 | 0.8650 | 0.8533 | 1.0000 | 1.0000 | 1.0000 | Games where cheaters and bad matchmaking ruin the multiplayer |
| q46 | cross_game | 157 | 0.4819 | 0.7163 | 0.6552 | 0.8882 | 0.8069 | 0.8069 | Which games have poor optimization and low FPS even on good hardware? |
| q47 | cross_game | 303 | 0.7314 | 0.8533 | 0.7812 | 0.8023 | 0.7869 | 0.7869 | Games with a memorable, emotional story |
| q48 | cross_game | 297 | 0.7799 | 1.0000 | 0.9432 | 0.9074 | 0.9074 | 0.9074 | Which games have breathtaking visuals and art direction? |
| q49 | cross_game | 150 | 0.8659 | 0.8580 | 0.9216 | 0.9052 | 0.8611 | 0.8611 | games with clunky, unresponsive controls |
| q50 | cross_game | 538 | 0.8341 | 0.9052 | 0.9337 | 0.9368 | 0.9537 | 0.9537 | Which games have the most satisfying combat? |
| q51 | single_aspect | 21 | 0.0463 | 0.3668 | 0.2090 | 0.0261 | 0.0245 | 0.3103 | Does Call of Duty: Warzone have stuttering or FPS drops? |
| q52 | single_aspect | 43 | 1.0000 | 0.8580 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | How does the turn-based combat with parrying work in Clair Obscur: Expedition 33? |
| q53 | single_aspect | 13 | 0.1884 | 0.1799 | 0.2344 | 0.2999 | 0.2999 | 0.6464 | What do people think of the soundtrack and radio stations in Cyberpunk 2077? |
| q54 | single_aspect | 23 | 0.2201 | 0.3647 | 0.2201 | 0.2201 | 0.2201 | 0.5993 | Is the Grand Theft Auto V Legacy campaign worth playing? |
| q55 | single_aspect | 22 | 0.5581 | 0.6844 | 0.6570 | 0.8415 | 0.7779 | 0.8415 | Hades II art and character designs |
| q56 | single_aspect | 47 | 0.1003 | 0.4490 | 0.2130 | 0.2996 | 0.2996 | 0.8044 | How difficult is Hollow Knight for new players? |
| q57 | single_aspect | 19 | 0.3437 | 0.4192 | 0.5366 | 0.2971 | 0.3010 | 0.4340 | Does Left 4 Dead 2 still hold up visually? |
| q58 | single_aspect | 22 | 0.6086 | 0.6780 | 0.5795 | 0.7008 | 0.4323 | 0.7728 | How is hunting with friends online in Monster Hunter Wilds? |
| q59 | single_aspect | 14 | 0.2201 | 0.2240 | 0.3301 | 0.3301 | 0.3301 | 0.3996 | How does PAYDAY 3 run on PC? |
| q60 | single_aspect | 24 | 0.2122 | 0.2240 | 0.2154 | 0.0000 | 0.1331 | 0.7799 | Red Dead Redemption 2 open world scenery and graphics |
| q61 | single_aspect | 39 | 0.2900 | 0.3590 | 0.4284 | 0.4323 | 0.4374 | 1.0000 | What is the gameplay loop like in Redfall? |
| q62 | single_aspect | 18 | 0.5510 | 0.3621 | 0.4789 | 0.6275 | 0.5271 | 0.8604 | Is Resident Evil Requiem well optimized for PC? |
| q63 | single_aspect | 8 | 0.0000 | 0.0000 | 0.0000 | 0.0731 | 0.0731 | 0.0798 | Is Resident Evil Resistance stable, or does it have technical issues? |
| q64 | single_aspect | 23 | 0.7386 | 0.7990 | 0.8415 | 0.9052 | 0.9052 | 0.9052 | Is it fun to build parks in RollerCoaster Tycoon World? |
| q65 | single_aspect | 10 | 0.1055 | 0.2734 | 0.2580 | 0.2622 | 0.2216 | 0.3720 | How is the interface and control scheme in Spacebase DF-9? |
| q66 | single_aspect | 24 | 0.6141 | 0.4383 | 0.5993 | 0.5730 | 0.5730 | 0.6691 | Is there much of a story in Hollow Knight: Silksong? |
| q67 | single_aspect | 16 | 0.3640 | 0.3070 | 0.3706 | 0.3223 | 0.3223 | 0.5949 | Does Umbrella Corps have any story or lore? |
| q68 | single_aspect | 24 | 0.1167 | 0.3128 | 0.1944 | 0.3786 | 0.3786 | 0.7885 | Dawn of War III art style and visuals |
| q69 | aspect_sentiment | 27 | 0.5638 | 0.4690 | 0.5758 | 0.5922 | 0.5006 | 0.8910 | What do players praise about the art direction of Clair Obscur: Expedition 33? |
| q70 | aspect_sentiment | 29 | 0.2614 | 0.5763 | 0.3854 | 0.7084 | 0.7116 | 0.9266 | Why do fans love the lore and world of Hollow Knight? |
| q71 | aspect_sentiment | 30 | 0.5263 | 0.3938 | 0.5361 | 0.6489 | 0.6489 | 0.7788 | What do players like about the music in Hollow Knight: Silksong? |
| q72 | aspect_sentiment | 36 | 0.4249 | 0.5638 | 0.6325 | 0.6968 | 0.5850 | 0.9537 | Why is Arthur Morgan's story so loved in Red Dead Redemption 2? |
| q73 | aspect_sentiment | 25 | 0.5036 | 0.5225 | 0.5271 | 0.3120 | 0.3125 | 0.5211 | How good does Night City look in Cyberpunk 2077? |
| q74 | aspect_sentiment | 25 | 0.4374 | 0.4501 | 0.3764 | 0.6719 | 0.6831 | 0.6719 | What do players enjoy about the characters and dialogue in Hades II? |
| q75 | aspect_sentiment | 28 | 0.2489 | 0.5988 | 0.5128 | 0.5606 | 0.6242 | 0.6616 | What do fans like about the story of Resident Evil Requiem? |
| q76 | aspect_sentiment | 11 | 0.0990 | 0.0483 | 0.1060 | 0.0766 | 0.0766 | 0.2941 | Why does Left 4 Dead 2 run so well even on old PCs? |
| q77 | aspect_sentiment | 9 | 0.2467 | 0.2299 | 0.3529 | 0.3421 | 0.3700 | 0.8519 | What do players like about the graphics of Grand Theft Auto V Legacy? |
| q78 | aspect_sentiment | 13 | 0.2985 | 0.3601 | 0.4499 | 0.4153 | 0.5033 | 0.5420 | What do players enjoy about the engine sounds and music in Test Drive Unlimited Solar Crown? |
| q79 | aspect_sentiment | 32 | 0.6862 | 0.6774 | 0.6246 | 0.6847 | 0.6847 | 0.7768 | What do players enjoy about the hunts and weapons in Monster Hunter Wilds? |
| q80 | aspect_sentiment | 12 | 0.4577 | 0.3149 | 0.4000 | 0.5541 | 0.5541 | 0.6898 | Why do players say Hollow Knight's controls feel tight and responsive? |
| q81 | aspect_sentiment | 32 | 0.2079 | 0.5598 | 0.3863 | 0.4793 | 0.4374 | 0.4672 | What do players dislike about the driving and progression in Test Drive Unlimited Solar Crown? |
| q82 | aspect_sentiment | 15 | 0.2048 | 0.3667 | 0.2048 | 0.3811 | 0.3786 | 0.3843 | Why does RollerCoaster Tycoon World lag with big parks? |
| q83 | aspect_sentiment | 31 | 0.4857 | 0.4974 | 0.5644 | 0.5326 | 0.5326 | 0.6088 | Why is it so hard to find a match in Umbrella Corps? |
| q84 | aspect_sentiment | 18 | 0.4780 | 0.6325 | 0.6173 | 0.5175 | 0.5811 | 0.5395 | What do players dislike about the story of Hades II compared to the first game? |
| q85 | aspect_sentiment | 32 | 0.6313 | 0.4189 | 0.6078 | 0.8529 | 0.8529 | 0.8529 | Why do players dislike the leveling and bullet-sponge enemies in Wolfenstein: Youngblood? |
| q86 | aspect_sentiment | 12 | 0.3448 | 0.4413 | 0.4638 | 0.5138 | 0.3749 | 0.8023 | What do players criticize about Redfall's visuals? |
| q87 | aspect_sentiment | 15 | 0.2436 | 0.2685 | 0.4639 | 0.3471 | 0.2173 | 0.7354 | What bugs and crashes do players report in Warhammer 40,000: Dawn of War III? |
| q88 | aspect_sentiment | 31 | 0.3104 | 0.3585 | 0.3839 | 0.4867 | 0.4867 | 0.4867 | What do players dislike about the progression and heists in PAYDAY 3? |
| q89 | multi_aspect | 32 | 0.1546 | 0.2832 | 0.2462 | 0.2051 | 0.2083 | 0.9149 | Is Cyberpunk 2077 finally fixed: does it run well, and are the bugs gone? |
| q90 | multi_aspect | 42 | 0.5638 | 0.8553 | 0.8390 | 0.7752 | 0.8669 | 0.9337 | How do the gunplay and visuals of Wolfenstein: Youngblood hold up? |
| q91 | multi_aspect | 40 | 0.4690 | 0.7084 | 0.6969 | 0.7273 | 0.8643 | 1.0000 | Is Resident Evil Resistance balanced, and does it work without technical problems? |
| q92 | multi_aspect | 48 | 0.6688 | 0.8604 | 0.8604 | 0.9364 | 0.8701 | 1.0000 | Is Spacebase DF-9 unfinished: how much content is there, and does it crash? |
| q93 | multi_aspect | 46 | 0.5622 | 1.0000 | 0.7820 | 0.6582 | 0.6300 | 0.8900 | How do the driving controls and frame rate feel in Test Drive Unlimited Solar Crown? |
| q94 | multi_aspect | 44 | 0.6204 | 0.6911 | 0.6372 | 0.7818 | 0.7702 | 1.0000 | How do the story and combat of Clair Obscur: Expedition 33 compare? |
| q95 | multi_aspect | 45 | 0.7910 | 0.8572 | 0.8007 | 0.8643 | 0.7273 | 1.0000 | How are the multiplayer matches and MOBA-style gameplay in Dawn of War III? |
| q96 | multi_aspect | 35 | 0.2860 | 0.3223 | 0.3925 | 0.1232 | 0.1113 | 0.3567 | Is Call of Duty: Warzone stable and smooth to play? |
| q97 | cross_game | 58 | 0.3169 | 0.5331 | 0.4907 | 0.6988 | 0.6118 | 0.6118 | Which games are polished and almost free of bugs? |
| q98 | cross_game | 120 | 0.4383 | 0.6036 | 0.5656 | 0.7754 | 0.7754 | 0.7754 | Which games are great to play co-op with friends? |
| q99 | cross_game | 62 | 0.6770 | 0.7975 | 0.8238 | 0.8533 | 0.7897 | 0.7897 | games with bad voice acting or annoying sound |
| q100 | cross_game | 126 | 0.6543 | 0.8333 | 0.8106 | 0.8707 | 0.6764 | 0.6764 | Which games are well optimized and run smoothly? |
