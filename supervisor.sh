#!/bin/bash

# MavadoClaw-Worker Supervisor Script
# Manages all services: OmniRoute, 9Router, OpenHands, MavadoClaw

set -e

# ==================== Configuration ====================
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" ) && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/pids"

# Service definitions: name, port, command, working_dir
declare -A SERVICE_PORTS
declare -A SERVICE_COMMANDS
declare -A SERVICE_DIRS

# Unique ports - no conflicts
SERVICE_PORTS[omniroute]=3000
SERVICE_PORTS[9router]=8081
SERVICE_PORTS[openhands]=3001
SERVICE_PORTS[mavado]=8080

SERVICE_COMMANDS[omniroute]="node dev/run-standalone.mjs"
SERVICE_COMMANDS[9router]="node custom-server.js"
SERVICE_COMMANDS[openhands]="python -m openhands --port 3001"
SERVICE_COMMANDS[mavado]="python app.py"

SERVICE_DIRS[omniroute]="$PROJECT_DIR/omniroute"
SERVICE_DIRS[9router]="$PROJECT_DIR/9router"
SERVICE_DIRS[openhands]="$PROJECT_DIR/openhands"
SERVICE_DIRS[mavado]="$PROJECT_DIR"

# ==================== Setup ====================
mkdir -p "$LOG_DIR" "$PID_DIR"

# ==================== Functions ====================
log() {
    local service=$1
    local message=$2
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$service] $message" | tee -a "$LOG_DIR/supervisor.log"
}

start_service() {
    local service=$1
    local port=${SERVICE_PORTS[$service]}
    local command=${SERVICE_COMMANDS[$service]}
    local dir=${SERVICE_DIRS[$service]}

    # Check if already running
    if [ -f "$PID_DIR/$service.pid" ]; then
        local pid=$(cat "$PID_DIR/$service.pid")
        if kill -0 "$pid" 2>/dev/null; then
            log "$service" "Already running (PID: $pid)"
            return 0
        else
            rm -f "$PID_DIR/$service.pid"
        fi
    fi

    # Check if port is in use
    if lsof -Pi ":$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
        log "$service" "ERROR: Port $port is already in use"
        return 1
    fi

    log "$service" "Starting on port $port..."

    cd "$dir"
    nohup $command > "$LOG_DIR/$service.log" 2>&1 &
    local pid=$!
    echo $pid > "$PID_DIR/$service.pid"

    log "$service" "Started (PID: $pid, Port: $port)"
}

stop_service() {
    local service=$1

    if [ ! -f "$PID_DIR/$service.pid" ]; then
        log "$service" "Not running"
        return 0
    fi

    local pid=$(cat "$PID_DIR/$service.pid")
    if kill -0 "$pid" 2>/dev/null; then
        log "$service" "Stopping (PID: $pid)..."
        kill "$pid"
        sleep 2
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid"
        fi
        log "$service" "Stopped"
    else
        log "$service" "Process not found"
    fi
    rm -f "$PID_DIR/$service.pid"
}

health_check() {
    local service=$1
    local port=${SERVICE_PORTS[$service]}

    if curl -sf "http://localhost:$port/health" > /dev/null 2>&1; then
        log "$service" "Health check passed"
        return 0
    elif curl -sf "http://localhost:$port/" > /dev/null 2>&1; then
        log "$service" "Health check passed (root endpoint)"
        return 0
    else
        log "$service" "Health check failed"
        return 1
    fi
}

show_status() {
    echo "=============================================="
    echo "MavadoClaw-Worker Service Status"
    echo "=============================================="
    printf "%-12s | %-6s | %-8s | %s\n" "Service" "Port" "PID" "Status"
    echo "----------------------------------------------"
    for service in omniroute 9router openhands mavado; do
        local port=${SERVICE_PORTS[$service]}
        local pid="-"
        local status="STOPPED"

        if [ -f "$PID_DIR/$service.pid" ]; then
            pid=$(cat "$PID_DIR/$service.pid")
            if kill -0 "$pid" 2>/dev/null; then
                status="RUNNING"
            fi
        fi

        printf "%-12s | %-6s | %-8s | %s\n" "$service" "$port" "$pid" "$status"
    done
    echo "=============================================="
}

show_logs() {
    local service=${1:-supervisor}
    tail -f "$LOG_DIR/$service.log"
}

# ==================== Main ====================
case "${1:-}" in
    start)
        log "supervisor" "Starting all services..."
        start_service omniroute
        sleep 2
        start_service 9router
        sleep 2
        start_service openhands
        sleep 2
        start_service mavado
        log "supervisor" "All services started"
        show_status
        ;;
    stop)
        log "supervisor" "Stopping all services..."
        stop_service mavado
        stop_service openhands
        stop_service 9router
        stop_service omniroute
        log "supervisor" "All services stopped"
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        show_status
        ;;
    health)
        echo "Running health checks..."
        for service in omniroute 9router openhands mavado; do
            health_check "$service"
        done
        ;;
    logs)
        show_logs "${2:-supervisor}"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|health|logs [service]}"
        echo ""
        echo "Services:"
        echo "  omniroute  - Port 3000 - Primary AI Gateway"
        echo "  9router    - Port 8081 - Backup Router"
        echo "  openhands  - Port 3001 - Coding Agent"
        echo "  mavado     - Port 8080 - CEO/Orchestrator"
        echo ""
        echo "Examples:"
        echo "  $0 start          # Start all services"
        echo "  $0 stop           # Stop all services"
        echo "  $0 status         # Show service status"
        echo "  $0 health         # Run health checks"
        echo "  $0 logs mavado    # Tail MavadoClaw logs"
        exit 1
        ;;
esac
