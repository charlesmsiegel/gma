#!/bin/bash

# Script to run both Django and React development servers
# with proper cleanup on exit

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=============================================${NC}"
echo -e "${GREEN}🚀 Game Master Application - Dev Environment${NC}"
echo -e "${BLUE}=============================================${NC}"
echo -e "${GREEN}✅ All backend services are running${NC}"
echo -e "${YELLOW}📡 Django API Server: http://localhost:8080${NC}"
echo -e "${YELLOW}⚛️  React Frontend: http://localhost:3000${NC}"
echo -e ""
echo -e "${BLUE}👉 Visit http://localhost:8080 for the full application${NC}"
echo -e "${RED}👉 Press Ctrl+C to stop all servers${NC}"
echo -e "${BLUE}=============================================${NC}"
echo -e ""

# Function to cleanup background processes
cleanup() {
    echo -e "\n${YELLOW}Stopping servers...${NC}"
    if [ ! -z "$REACT_PID" ]; then
        kill $REACT_PID 2>/dev/null || true
    fi
    # Kill any remaining npm/react processes
    pkill -f "react-scripts start" 2>/dev/null || true
    pkill -f "npm start" 2>/dev/null || true
    echo -e "${GREEN}All servers stopped${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start React development server in background
echo -e "${GREEN}Starting React development server...${NC}"
cd frontend
npm start > /dev/null 2>&1 &
REACT_PID=$!
cd ..

# Give React a moment to start
sleep 3

# Start Django server in foreground (so we see its output)
echo -e "${GREEN}Starting Django server...${NC}"
python manage.py runserver 0.0.0.0:8080

# If Django exits, cleanup React
cleanup
