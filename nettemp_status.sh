#!/bin/bash
# Nettemp Client Status and Control Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/nettemp.pid"

check_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "✓ Nettemp is running (PID: $PID)"
            return 0
        else
            echo "✗ PID file exists but process is not running"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        # Check if process is running anyway
        PID=$(pgrep -f "python.*nettemp.py" | head -1)
        if [ -n "$PID" ]; then
            echo "⚠ Nettemp is running (PID: $PID) but no PID file found"
            echo $PID > "$PID_FILE"
            return 0
        else
            echo "✗ Nettemp is not running"
            return 1
        fi
    fi
}

stop_nettemp() {
    echo "Stopping nettemp..."
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        kill $PID 2>/dev/null
        sleep 2
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID 2>/dev/null
        fi
        rm -f "$PID_FILE"
        echo "✓ Nettemp stopped"
    else
        # Try to kill by name
        pkill -f "python.*nettemp.py"
        echo "✓ Nettemp stopped (by name)"
    fi
}

start_nettemp() {
    if check_running > /dev/null 2>&1; then
        echo "✗ Nettemp is already running"
        return 1
    fi
    
    echo "Starting nettemp..."
    cd "$SCRIPT_DIR"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    nohup python3 nettemp.py > nettemp.log 2>&1 &
    echo $! > "$PID_FILE"
    sleep 1
    
    if check_running > /dev/null 2>&1; then
        echo "✓ Nettemp started successfully"
    else
        echo "✗ Failed to start nettemp"
        return 1
    fi
}

restart_nettemp() {
    stop_nettemp
    sleep 1
    start_nettemp
}

show_logs() {
    if [ -f "$SCRIPT_DIR/nettemp.log" ]; then
        tail -50 "$SCRIPT_DIR/nettemp.log"
    else
        echo "No log file found"
    fi
}

case "${1:-status}" in
    status)
        check_running
        ;;
    start)
        start_nettemp
        ;;
    stop)
        stop_nettemp
        ;;
    restart)
        restart_nettemp
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "Usage: $0 {status|start|stop|restart|logs}"
        exit 1
        ;;
esac
