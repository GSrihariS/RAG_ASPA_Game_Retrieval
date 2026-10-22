timeout 10
python query_hybrid.py "What do players think about the story and characters?" --game "Clair Obscur: Expedition 33" --candidates 20 --top-k 10 > sq001_hybrid_rerank.txt
timeout 10
python query_hybrid.py "How do players describe performance and optimization?" --game "Monster Hunter Wilds" --candidates 20 --top-k 10 > sq002_hybrid_rerank.txt
timeout 10
python query_hybrid.py "What do players say about stability and reliability?" --game "Cyberpunk 2077" --candidates 20 --top-k 10 > sq003_hybrid_rerank.txt
timeout 10
python query_hybrid.py "What do players think about cooperative multiplayer?" --game "Left 4 Dead 2" --candidates 20 --top-k 10 > sq004_hybrid_rerank.txt
timeout 10
python query_hybrid.py "How do players describe the controls, movement, and difficulty?" --game "Hollow Knight: Silksong" --candidates 20 --top-k 10 > sq005_hybrid_rerank.txt
timeout 10
python query_hybrid.py "What do players think about the music and sound design?" --game "Hades II" --candidates 20 --top-k 10 > sq006_hybrid_rerank.txt
timeout 10
python query_hybrid.py "What do players think about the story, characters, and controls?" --game "Red Dead Redemption 2" --candidates 20 --top-k 10 > sq007_hybrid_rerank.txt
timeout 10
python query_hybrid.py "What do players say about performance and optimization?" --candidates 20 --top-k 10 > sq008_hybrid_rerank.txt
timeout 10
python query_hybrid.py "What do players say about performance and optimization?" --game "Clair Obscur: Expedition 33" --candidates 20 --top-k 10 > sq009_hybrid_rerank.txt
timeout 10