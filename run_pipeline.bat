@echo off
echo Waking up the AI Job Aggregator (Powered by uv)...
cd /d "%~dp0"
uv run core\main.py