#!/bin/bash

# =============================================================================
# Bybit AI Trader - Management Script
# =============================================================================
# Usage: ./bybit_trader.sh [install|run|uninstall|update|status|help]
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
VENV_DIR="venv"
PYTHON_CMD="python3"
PIP_CMD="pip3"
ENV_FILE=".env"
ENV_TEMPLATE=".env.example"
CONFIG_DIR="config"
SETTINGS_FILE="$CONFIG_DIR/settings.yaml"
LOGS_DIR="logs"
DB_DIR="database"
DB_FILE="$DB_DIR/trading.db"

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo -e "${CYAN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║           Bybit AI Trader - Management Tool               ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    echo -e "\n${BLUE}${BOLD}▶ $1${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

check_python() {
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python 3.12+ not found. Please install Python 3.12 or later."
        echo "Download from: https://www.python.org/downloads/"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    REQUIRED_VERSION="3.12"
    
    if [[ $(echo "$PYTHON_VERSION < $REQUIRED_VERSION" | bc) == 1 ]]; then
        print_error "Python 3.12+ required. Found: $PYTHON_VERSION"
        exit 1
    fi
    
    print_success "Python $PYTHON_VERSION detected"
}

check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        return 1
    fi
    return 0
}

activate_venv() {
    if check_venv; then
        source "$VENV_DIR/bin/activate"
        print_success "Virtual environment activated"
    else
        print_error "Virtual environment not found. Run './bybit_trader.sh install' first."
        exit 1
    fi
}

# =============================================================================
# Install Command
# =============================================================================

do_install() {
    print_header
    print_section "Installing Bybit AI Trader"
    
    # Check Python
    print_info "Checking Python version..."
    check_python
    
    # Create virtual environment
    if check_venv; then
        print_warning "Virtual environment already exists. Skipping creation."
    else
        print_info "Creating virtual environment..."
        $PYTHON_CMD -m venv $VENV_DIR
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    activate_venv
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip --quiet
    
    # Install dependencies
    print_info "Installing dependencies (this may take a few minutes)..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --quiet
        print_success "Dependencies installed"
    else
        print_error "requirements.txt not found!"
        exit 1
    fi
    
    # Create .env file
    if [ ! -f "$ENV_FILE" ]; then
        print_info "Creating $ENV_FILE from template..."
        if [ -f "$ENV_TEMPLATE" ]; then
            cp "$ENV_TEMPLATE" "$ENV_FILE"
            print_success "$ENV_FILE created"
            print_warning "Please edit $ENV_FILE with your API credentials before running!"
        else
            print_error "$ENV_TEMPLATE not found!"
            exit 1
        fi
    else
        print_warning "$ENV_FILE already exists. Skipping creation."
    fi
    
    # Create config directory and settings
    if [ ! -d "$CONFIG_DIR" ]; then
        print_info "Creating config directory..."
        mkdir -p "$CONFIG_DIR"
    fi
    
    if [ ! -f "$SETTINGS_FILE" ]; then
        print_info "Creating default settings.yaml..."
        cat > "$SETTINGS_FILE" << 'EOF'
# Bybit AI Trader Configuration
# Do not store API keys here - use .env file instead

trading:
  mode: "paper"  # paper or live
  enabled: true
  max_positions: 5
  max_leverage: 10
  
risk:
  risk_per_trade: 1.0  # Percentage of balance
  daily_loss_limit: 5.0  # Percentage
  weekly_loss_limit: 10.0  # Percentage
  monthly_loss_limit: 20.0  # Percentage
  min_risk_reward: 2.0  # Minimum R:R ratio
  
scanner:
  enabled: true
  scan_interval: 5  # Seconds
  opportunity_threshold: 90  # Minimum score (0-100)
  
timeframes:
  - "1m"
  - "3m"
  - "5m"
  - "15m"
  - "30m"
  - "1h"
  - "4h"
  - "1d"

indicators:
  ema_periods: [20, 50, 100, 200]
  rsi_period: 14
  atr_period: 14
  adx_period: 14
  
dashboard:
  refresh_rate: 1.0  # Seconds
  show_all_symbols: false
  top_opportunities: 10
  
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  save_to_file: true
  rotation_mb: 10
  backup_count: 5
  
telegram:
  enabled: false
  # Add token and chat_id in .env file
EOF
        print_success "settings.yaml created"
    else
        print_warning "settings.yaml already exists. Skipping creation."
    fi
    
    # Create directories
    print_info "Creating necessary directories..."
    mkdir -p "$LOGS_DIR"
    mkdir -p "$DB_DIR"
    print_success "Directories created"
    
    # Initialize database
    print_info "Initializing database..."
    python -c "from database.manager import DatabaseManager; db = DatabaseManager(); db.initialize()" 2>/dev/null || print_warning "Database initialization skipped (will initialize on first run)"
    
    # Create run script
    print_info "Creating run script..."
    cat > "run.sh" << 'EOF'
#!/bin/bash
source venv/bin/activate
python main.py
EOF
    chmod +x run.sh
    print_success "Run script created"
    
    echo ""
    print_success "Installation completed successfully!"
    echo ""
    print_section "Next Steps"
    echo "1. Edit $ENV_FILE with your Bybit API credentials:"
    echo "   nano $ENV_FILE"
    echo ""
    echo "2. Review and customize $SETTINGS_FILE if needed:"
    echo "   nano $SETTINGS_FILE"
    echo ""
    echo "3. Run the bot:"
    echo "   ./bybit_trader.sh run"
    echo "   or"
    echo "   ./run.sh"
    echo ""
    print_warning "Remember: The bot defaults to PAPER TRADING mode for safety!"
    echo ""
}

# =============================================================================
# Run Command
# =============================================================================

do_run() {
    print_header
    print_section "Starting Bybit AI Trader"
    
    # Check if installed
    if ! check_venv; then
        print_error "Bot not installed. Run './bybit_trader.sh install' first."
        exit 1
    fi
    
    # Check .env file
    if [ ! -f "$ENV_FILE" ]; then
        print_error "$ENV_FILE not found. Run './bybit_trader.sh install' first."
        exit 1
    fi
    
    # Check if API keys are set
    if grep -q "YOUR_BYBIT_API_KEY_HERE" "$ENV_FILE" || grep -q "YOUR_BYBIT_SECRET_KEY_HERE" "$ENV_FILE"; then
        print_warning "API keys not configured in $ENV_FILE"
        print_info "The bot will run in offline mode or exit if API is required."
        echo ""
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Please edit $ENV_FILE with your API credentials."
            exit 0
        fi
    fi
    
    # Activate and run
    activate_venv
    
    print_info "Starting trading bot..."
    print_info "Press Ctrl+C to stop"
    echo ""
    
    python main.py
}

# =============================================================================
# Uninstall Command
# =============================================================================

do_uninstall() {
    print_header
    print_section "Uninstalling Bybit AI Trader"
    
    print_warning "This will remove:"
    echo "  - Virtual environment ($VENV_DIR)"
    echo "  - Installed packages"
    echo "  - Log files ($LOGS_DIR)"
    echo "  - Database ($DB_FILE)"
    echo ""
    echo "This will NOT remove:"
    echo "  - Configuration files ($ENV_FILE, $SETTINGS_FILE)"
    echo "  - Source code"
    echo ""
    
    read -p "Are you sure you want to uninstall? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Uninstallation cancelled."
        exit 0
    fi
    
    # Remove virtual environment
    if check_venv; then
        print_info "Removing virtual environment..."
        rm -rf "$VENV_DIR"
        print_success "Virtual environment removed"
    else
        print_warning "Virtual environment not found. Skipping."
    fi
    
    # Remove logs
    if [ -d "$LOGS_DIR" ]; then
        print_info "Removing log files..."
        rm -rf "$LOGS_DIR"/*
        print_success "Log files removed"
    fi
    
    # Remove database
    if [ -f "$DB_FILE" ]; then
        print_info "Removing database..."
        rm -f "$DB_FILE"
        print_success "Database removed"
    fi
    
    # Remove run script
    if [ -f "run.sh" ]; then
        rm -f run.sh
        print_success "Run script removed"
    fi
    
    echo ""
    print_success "Uninstallation completed!"
    echo ""
    print_info "Your configuration files have been preserved:"
    echo "  - $ENV_FILE"
    echo "  - $SETTINGS_FILE"
    echo ""
    print_info "To reinstall, run: ./bybit_trader.sh install"
    echo ""
}

# =============================================================================
# Update Command
# =============================================================================

do_update() {
    print_header
    print_section "Updating Bybit AI Trader"
    
    # Check if installed
    if ! check_venv; then
        print_error "Bot not installed. Run './bybit_trader.sh install' first."
        exit 1
    fi
    
    activate_venv
    
    # Update pip
    print_info "Upgrading pip..."
    pip install --upgrade pip --quiet
    
    # Update dependencies
    print_info "Updating dependencies..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --upgrade --quiet
        print_success "Dependencies updated"
    else
        print_error "requirements.txt not found!"
        exit 1
    fi
    
    # Check for new .env variables
    if [ -f "$ENV_FILE" ] && [ -f "$ENV_TEMPLATE" ]; then
        print_info "Checking for new configuration options..."
        # Compare and notify about new variables (simplified check)
        NEW_VARS=$(diff <(grep "=" "$ENV_TEMPLATE" | cut -d= -f1 | sort) <(grep "=" "$ENV_FILE" | cut -d= -f1 | sort) | grep "^>" | cut -c3- || true)
        if [ -n "$NEW_VARS" ]; then
            print_warning "New configuration variables available:"
            echo "$NEW_VARS"
            print_info "Consider updating your $ENV_FILE file"
        fi
    fi
    
    echo ""
    print_success "Update completed successfully!"
    echo ""
    print_info "You can now run the bot with: ./bybit_trader.sh run"
    echo ""
}

# =============================================================================
# Status Command
# =============================================================================

do_status() {
    print_header
    print_section "System Status"
    
    # Python version
    if command -v $PYTHON_CMD &> /dev/null; then
        PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
        print_success "Python: $PYTHON_VERSION"
    else
        print_error "Python: Not found"
    fi
    
    # Virtual environment
    if check_venv; then
        print_success "Virtual Environment: Active"
        
        # Check if some key packages are installed
        if source "$VENV_DIR/bin/activate" && python -c "import pybit" 2>/dev/null; then
            print_success "Key packages: Installed"
        else
            print_warning "Key packages: Missing or incomplete"
        fi
    else
        print_error "Virtual Environment: Not found"
    fi
    
    # Configuration files
    if [ -f "$ENV_FILE" ]; then
        print_success "Environment File: Present"
        # Check if API keys are configured
        if grep -q "YOUR_BYBIT_API_KEY_HERE" "$ENV_FILE"; then
            print_warning "API Keys: Not configured"
        else
            print_success "API Keys: Configured"
        fi
    else
        print_error "Environment File: Missing"
    fi
    
    if [ -f "$SETTINGS_FILE" ]; then
        print_success "Settings File: Present"
    else
        print_warning "Settings File: Missing"
    fi
    
    # Directories
    if [ -d "$LOGS_DIR" ]; then
        LOG_COUNT=$(find "$LOGS_DIR" -name "*.log" 2>/dev/null | wc -l)
        print_success "Logs Directory: Present ($LOG_COUNT log files)"
    else
        print_info "Logs Directory: Not created yet"
    fi
    
    if [ -f "$DB_FILE" ]; then
        print_success "Database: Initialized"
    else
        print_info "Database: Not initialized yet"
    fi
    
    # Run script
    if [ -f "run.sh" ]; then
        print_success "Run Script: Present"
    else
        print_info "Run Script: Not created yet"
    fi
    
    echo ""
}

# =============================================================================
# Help Command
# =============================================================================

do_help() {
    print_header
    echo "Usage: ./bybit_trader.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  install    - Install all dependencies and set up the environment"
    echo "  run        - Start the trading bot"
    echo "  uninstall  - Remove virtual environment, logs, and database"
    echo "  update     - Update dependencies to latest versions"
    echo "  status     - Show current system status"
    echo "  help       - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./bybit_trader.sh install    # First-time setup"
    echo "  ./bybit_trader.sh run        # Start the bot"
    echo "  ./bybit_trader.sh status     # Check installation status"
    echo "  ./bybit_trader.sh update     # Update packages"
    echo "  ./bybit_trader.sh uninstall  # Clean installation"
    echo ""
    echo "Quick Start:"
    echo "  1. ./bybit_trader.sh install"
    echo "  2. Edit .env with your API credentials"
    echo "  3. ./bybit_trader.sh run"
    echo ""
}

# =============================================================================
# Main Entry Point
# =============================================================================

if [ $# -eq 0 ]; then
    do_help
    exit 0
fi

case "$1" in
    install)
        do_install
        ;;
    run)
        do_run
        ;;
    uninstall)
        do_uninstall
        ;;
    update)
        do_update
        ;;
    status)
        do_status
        ;;
    help|--help|-h)
        do_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        do_help
        exit 1
        ;;
esac
