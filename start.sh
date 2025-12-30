#!/bin/bash

# Send Money Agent - Quick Start Script

echo "================================"
echo "Send Money Agent - Quick Start"
echo "================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Backend setup
echo "📦 Setting up backend..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
    echo "⚠️  WARNING: .env file not found!"
    echo "Please create a .env file with your GOOGLE_API_KEY"
    echo "Example: cp .env.example .env"
    echo ""
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "✅ Backend setup complete"
echo ""

# Frontend setup
echo "📦 Setting up frontend..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    npm install
fi

echo "✅ Frontend setup complete"
echo ""

# Start services
echo "================================"
echo "🚀 Starting services..."
echo "================================"
echo ""

cd ../backend
echo "Starting backend on http://localhost:8000"
python main.py &
BACKEND_PID=$!

sleep 3

cd ../frontend
echo "Starting frontend on http://localhost:3000"
npm start &
FRONTEND_PID=$!

echo ""
echo "================================"
echo "✅ Application is running!"
echo "================================"
echo ""
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Trap Ctrl+C and cleanup
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT

# Wait for processes
wait
