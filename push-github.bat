@echo off
REM ============================================================
REM  push-github.bat  -  uploads this project to GitHub
REM
REM  BEFORE running: create an EMPTY repo at https://github.com/new
REM    - name: ai-chatbot
REM    - Public
REM    - do NOT tick "Add a README file"
REM ============================================================
cd /d "%~dp0"

echo ============================================
echo   Upload AI Chatbot to GitHub
echo ============================================
echo.

set /p GH_REPO=Type your repo like  username/ai-chatbox  then press Enter: 

if "%GH_REPO%"=="" (
    echo.
    echo Nothing typed. Run this file again.
    pause
    exit /b 1
)

set URL=https://github.com/%GH_REPO%.git

echo.
echo Repo : %URL%
echo.

git remote remove origin 2>nul
git remote add origin %URL%
git branch -M main

echo Pushing... a GitHub sign-in window may pop up - click "Sign in with your browser".
echo.
git push -u origin main

echo.
if %ERRORLEVEL% equ 0 (
    echo ============================================
    echo  SUCCESS! Your project is live at:
    echo    https://github.com/%GH_REPO%
    echo ============================================
) else (
    echo ============================================
    echo  PUSH FAILED - most common reasons:
    echo   1. Repo name typed wrong - run this again
    echo   2. Repo not created yet - go to https://github.com/new
    echo   3. Repo was created WITH a README tick box
    echo      -^> delete that repo on GitHub, create it again EMPTY
    echo   4. You did not finish the browser sign-in
    echo ============================================
)
pause
