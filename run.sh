#!/bin/bash

# Price Comparison Tool - macOS Startup Script
# This script starts both the FastAPI backend and the frontend server

set -e  # Exit on any error

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3010
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"


# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -i :$port &> /dev/null; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti :$port)
    if [ ! -z "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)"
        kill -9 $pid
        sleep 2
    fi
}

# Function to cleanup on exit
cleanup() {
    echo "Shutting down servers..."
    
    # Kill backend process
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    # Kill frontend process
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Kill any remaining processes on our ports
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    
    echo "Cleanup complete"
    exit 0
}

# Set up trap for cleanup on exit
trap cleanup EXIT INT TERM

echo "Price Comparison Tool - Startup Script"

# Check if we're in the right directory
if [ ! -f "$PROJECT_DIR/backend/main.py" ] || [ ! -f "$PROJECT_DIR/frontend/index.html" ]; then
    echo "Error: Cannot find required files. Make sure you're running this script from the project root."
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check for pip
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is required but not installed."
    exit 1
fi

# Kill any existing processes on our ports
if check_port $BACKEND_PORT; then
    echo "Port $BACKEND_PORT is in use, attempting to free it..."
    kill_port $BACKEND_PORT
fi

if check_port $FRONTEND_PORT; then
    echo "Port $FRONTEND_PORT is in use, attempting to free it..."
    kill_port $FRONTEND_PORT
fi

# Install backend dependencies
echo "Installing backend dependencies..."
cd "$BACKEND_DIR"
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo "Backend dependencies installed successfully"
    else
        echo "Failed to install backend dependencies"
        exit 1
    fi
else
    echo "Error: requirements.txt not found in backend directory"
    exit 1
fi

# Start backend server
echo "Starting FastAPI backend server..."
cd "$BACKEND_DIR"
python3 -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload --no-use-colors &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend is running
if check_port $BACKEND_PORT; then
    echo "Backend server started successfully on port $BACKEND_PORT"
else
    echo "Failed to start backend server"
    exit 1
fi

# Start frontend server
echo "Starting frontend server..."
cd "$FRONTEND_DIR"
python3 server.py &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 2

# Check if frontend is running
if check_port $FRONTEND_PORT; then
    echo "Frontend server started successfully on port $FRONTEND_PORT"
else
    echo "Failed to start frontend server"
    exit 1
fi

echo "Price Comparison Tool is now running!"
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo "Backend API: http://localhost:$BACKEND_PORT"
echo "API Documentation: http://localhost:$BACKEND_PORT/docs"
echo "Health Check: http://localhost:$BACKEND_PORT/api/health"
echo "Tips:"
echo "   - Use Ctrl+C to stop both servers"
echo "   - Check the API documentation at /docs for detailed endpoint information"
echo "   - The backend uses SQLite database (api_endpoints.db) for storing API configurations"

# Open browser on macOS
if command -v open &> /dev/null; then
    echo "Opening browser..."
    open "http://localhost:$FRONTEND_PORT"
fi

# Wait for servers to run
echo "Servers are running. Press Ctrl+C to stop..."
wait