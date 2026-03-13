#!/bin/bash

# Script to run both the FastAPI backend and React frontend for the Agentic Healthcare Research Copilot.

# Kill background processes on exit
trap "kill 0" EXIT

echo " Starting Agentic Healthcare Research Copilot..."

# 0. Cleanup old processes
echo "Cleaning up existing processes on ports 8000 and 8501..."
lsof -ti:8000,8501 | xargs kill -9 2>/dev/null || true

# 1. Start FastAPI Backend
echo "Starting Backend API on http://localhost:8000..."
export PYTHONPATH=.
python3 api/main.py &

# 2. Start Streamlit UI
echo "Starting Streamlit UI on http://localhost:8501..."
streamlit run app_streamlit.py --server.port 8501 --server.headless true &

# Keep script running
wait
