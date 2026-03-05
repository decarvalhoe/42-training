@echo off
REM ===================================
REM  42 TRAINING - LAUNCHER WINDOWS
REM ===================================

echo ===================================
echo      42 PISCINE TRAINING
echo      Session d'apprentissage
echo ===================================
echo.

echo [1] Ouverture de WSL...
start wsl.exe -d Ubuntu --cd ~/42_training

timeout /t 2 >nul

echo [2] Ouverture de Claude...
start https://claude.ai/

timeout /t 2 >nul

echo [3] Instructions:
echo.
echo Dans WSL, tape:
echo   cat REPRENDRE_SESSION.md
echo.
echo Puis copie le contexte dans Claude pour reprendre!
echo.
echo ===================================
echo Commandes utiles:
echo   ./save_progress.sh    (sauvegarder avant de fermer)
echo   ls -la               (voir fichiers)
echo   cat progression.json (voir ta progression)
echo ===================================
echo.
pause