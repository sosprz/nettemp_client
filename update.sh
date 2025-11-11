#!/bin/bash

echo "========================================="
echo "  Nettemp Client Update"
echo "========================================="
echo ""

# Check if we're in a git repository
if [ ! -d .git ]; then
    echo "Error: Not a git repository. Please run this from the nettemp_client directory."
    exit 1
fi

# Stop running client if found
PIDFILE=".nettemp_client.pid"
if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "[1/5] Stopping running client (PID: $PID)..."
        kill $PID
        sleep 2
    else
        echo "[1/5] No running client found (stale pidfile)"
        rm -f "$PIDFILE"
    fi
else
    echo "[1/5] No running client detected"
fi

# Pull latest changes
echo "[2/5] Pulling latest changes from GitHub..."
git pull origin main

if [ $? -ne 0 ]; then
    echo "Error: Failed to pull changes. Please resolve conflicts manually."
    exit 1
fi

# Activate venv and update dependencies
echo "[3/5] Updating Python dependencies..."
if [ -d "venv" ]; then
    . venv/bin/activate
    pip3 install -r requirements.txt --upgrade
    deactivate
else
    echo "Warning: Virtual environment not found. Run ./setup.sh first."
fi

# Check for new config options
echo "[4/5] Checking configuration..."
if [ -f "example_config.conf" ] && [ -f "config.conf" ]; then
    echo "✓ config.conf preserved"
fi

if [ -f "example_drivers_config.yaml" ] && [ -f "drivers_config.yaml" ]; then
    echo "✓ drivers_config.yaml preserved"
fi

echo ""
echo "Note: Check example_config.conf and example_drivers_config.yaml for new options"
echo ""

# Restart client
echo "[5/5] Restarting client..."
if [ -t 0 ]; then
    # Interactive mode - ask user
    read -p "Start client now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 nettemp_client.py &
        echo "✓ Client started in background"
    else
        echo "Start manually with: python3 nettemp_client.py"
    fi
else
    # Non-interactive - just start it
    python3 nettemp_client.py &
    echo "✓ Client started in background"
fi

echo ""
echo "========================================="
echo "  Update Complete!"
echo "========================================="
