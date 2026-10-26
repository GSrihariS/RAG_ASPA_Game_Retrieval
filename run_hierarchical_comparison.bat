@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "query_hybrid.py" (
  echo ERROR: Place these files in the directory containing your retrieval dependencies and indices.
  exit /b 1
)
if not exist "results_hierarchical" mkdir "results_hierarchical"
call :run Q01 "How good are the story and characters?" "Clair Obscur: Expedition 33"
call :run Q02 "How is the performance and optimization?" "Monster Hunter Wilds"
call :run Q03 "How are the controls and difficulty?" "Cyberpunk 2077"
call :run Q04 "How good is the cooperative multiplayer experience?" "Left 4 Dead 2"
call :run Q05 "How responsive are the controls and how challenging is the gameplay?" "Hollow Knight: Silksong"
call :run Q06 "How good are the music and sound effects?" "Hades II"
call :run Q07 "How are the story, characters, and controls?" "Red Dead Redemption 2"
call :run Q08 "How stable is the game? Are crashes and bugs common?" "Cyberpunk 2077"
call :run Q09 "How good are the graphics and visual quality?" "Monster Hunter Wilds"
call :run Q10 "How engaging are the combat mechanics and progression?" "Clair Obscur: Expedition 33"
echo Finished. Results in results_hierarchical\
exit /b 0
:run
set "ID=%~1"
set "QUERY=%~2"
set "GAME=%~3"
echo Running %ID% hierarchical: %GAME%
python query_hybrid.py "%QUERY%" --game "%GAME%" --top-k 10 --candidates 20 --rerank-candidates 30 --expansion-mode hierarchical > "results_hierarchical\%ID%_hierarchical.txt" 2>&1
if errorlevel 1 echo FAILED: %ID% hierarchical
exit /b 0
