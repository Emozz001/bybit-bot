#!/bin/bash

# Bybit AI Trader - Interactive Management Script
# Run this script and select options by number

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration file paths
CONFIG_ENV_FILE="config.env"
ENV_FILE=".env"
SETTINGS_YAML_FILE="config/settings.yaml"

# Load configuration from config.env if it exists
load_config() {
    if [ -f "$CONFIG_ENV_FILE" ]; then
        source "$CONFIG_ENV_FILE"
    fi
}

# Function to update .env file with values from config.env
update_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        cp "$ENV_FILE.example" "$ENV_FILE" 2>/dev/null || touch "$ENV_FILE"
    fi
    
    # Update each environment variable if set in config.env
    local vars=(
        "BYBIT_API_KEY"
        "BYBIT_API_SECRET"
        "BYBIT_TESTNET"
        "TRADING_MODE"
        "RISK_PER_TRADE"
        "MAX_LEVERAGE"
        "MAX_POSITIONS"
        "DAILY_LOSS_LIMIT"
        "WEEKLY_LOSS_LIMIT"
        "MONTHLY_LOSS_LIMIT"
        "OPPORTUNITY_THRESHOLD"
        "TELEGRAM_BOT_TOKEN"
        "TELEGRAM_CHAT_ID"
        "DATABASE_PATH"
        "LOG_LEVEL"
    )
    
    for var in "${vars[@]}"; do
        if [ -n "${!var}" ]; then
            if grep -q "^${var}=" "$ENV_FILE" 2>/dev/null; then
                sed -i "s|^${var}=.*|${var}=${!var}|" "$ENV_FILE"
            else
                echo "${var}=${!var}" >> "$ENV_FILE"
            fi
        fi
    done
}

# Function to update settings.yaml with values from config.env
update_yaml_file() {
    if [ ! -f "$SETTINGS_YAML_FILE" ]; then
        mkdir -p config
        cat > "$SETTINGS_YAML_FILE" << 'EOF'
# Trading Bot Configuration
trading:
  mode: paper
  symbols: all
  opportunity_threshold: 90
  max_positions: 5
  max_leverage: 10
  
risk:
  risk_per_trade: 1.0
  daily_loss_limit: 5.0
  weekly_loss_limit: 10.0
  monthly_loss_limit: 20.0
  min_risk_reward: 2.0
  
indicators:
  timeframes:
    - 1m
    - 3m
    - 5m
    - 15m
    - 30m
    - 1h
    - 4h
    - 1d
  ema_periods: [20, 50, 100, 200]
  rsi_period: 14
  macd_fast: 12
  macd_slow: 26
  macd_signal: 9
  atr_period: 14
  bollinger_period: 20
  bollinger_std: 2.0
  
execution:
  default_sl_type: stop_loss
  default_tp_type: take_profit
  use_trailing_stop: true
  partial_exits: true
  
dashboard:
  refresh_rate: 1.0
  show_all_symbols: false
  top_opportunities_count: 10
  
logging:
  level: INFO
  save_to_file: true
  rotation_size_mb: 10
  backup_count: 5

telegram:
  enabled: false
  notify_on_trade: true
  notify_on_error: true
  daily_summary: true
EOF
    fi
    
    # Update YAML settings using Python for reliable parsing
    python3 << PYEOF
import yaml
import sys

try:
    with open('$SETTINGS_YAML_FILE', 'r') as f:
        config = yaml.safe_load(f) or {}
except Exception as e:
    config = {}

# Trading section
if '$YAML_TRADING_SYMBOLS':
    config.setdefault('trading', {})['symbols'] = '$YAML_TRADING_SYMBOLS'
if '$YAML_MIN_RISK_REWARD':
    config.setdefault('risk', {})['min_risk_reward'] = float('$YAML_MIN_RISK_REWARD')

# Indicators section
if '$YAML_TIMEFRAMES':
    timeframes = [t.strip() for t in '$YAML_TIMEFRAMES'.split(',')]
    config.setdefault('indicators', {})['timeframes'] = timeframes
if '$YAML_EMA_PERIODS':
    ema_periods = [int(p.strip()) for p in '$YAML_EMA_PERIODS'.split(',')]
    config.setdefault('indicators', {})['ema_periods'] = ema_periods
if '$YAML_RSI_PERIOD':
    config.setdefault('indicators', {})['rsi_period'] = int('$YAML_RSI_PERIOD')
if '$YAML_MACD_FAST':
    config.setdefault('indicators', {})['macd_fast'] = int('$YAML_MACD_FAST')
if '$YAML_MACD_SLOW':
    config.setdefault('indicators', {})['macd_slow'] = int('$YAML_MACD_SLOW')
if '$YAML_MACD_SIGNAL':
    config.setdefault('indicators', {})['macd_signal'] = int('$YAML_MACD_SIGNAL')
if '$YAML_ATR_PERIOD':
    config.setdefault('indicators', {})['atr_period'] = int('$YAML_ATR_PERIOD')
if '$YAML_BOLLINGER_PERIOD':
    config.setdefault('indicators', {})['bollinger_period'] = int('$YAML_BOLLINGER_PERIOD')
if '$YAML_BOLLINGER_STD':
    config.setdefault('indicators', {})['bollinger_std'] = float('$YAML_BOLLINGER_STD')

# Execution section
if '$YAML_DEFAULT_SL_TYPE':
    config.setdefault('execution', {})['default_sl_type'] = '$YAML_DEFAULT_SL_TYPE'
if '$YAML_DEFAULT_TP_TYPE':
    config.setdefault('execution', {})['default_tp_type'] = '$YAML_DEFAULT_TP_TYPE'
if '$YAML_USE_TRAILING_STOP':
    config.setdefault('execution', {})['use_trailing_stop'] = '$YAML_USE_TRAILING_STOP'.lower() == 'true'
if '$YAML_PARTIAL_EXITS':
    config.setdefault('execution', {})['partial_exits'] = '$YAML_PARTIAL_EXITS'.lower() == 'true'

# Dashboard section
if '$YAML_REFRESH_RATE':
    config.setdefault('dashboard', {})['refresh_rate'] = float('$YAML_REFRESH_RATE')
if '$YAML_SHOW_ALL_SYMBOLS':
    config.setdefault('dashboard', {})['show_all_symbols'] = '$YAML_SHOW_ALL_SYMBOLS'.lower() == 'true'
if '$YAML_TOP_OPPORTUNITIES_COUNT':
    config.setdefault('dashboard', {})['top_opportunities_count'] = int('$YAML_TOP_OPPORTUNITIES_COUNT')

# Logging section
if '$YAML_SAVE_TO_FILE':
    config.setdefault('logging', {})['save_to_file'] = '$YAML_SAVE_TO_FILE'.lower() == 'true'
if '$YAML_ROTATION_SIZE_MB':
    config.setdefault('logging', {})['rotation_size_mb'] = int('$YAML_ROTATION_SIZE_MB')
if '$YAML_BACKUP_COUNT':
    config.setdefault('logging', {})['backup_count'] = int('$YAML_BACKUP_COUNT')

# Telegram section
if '$YAML_TELEGRAM_ENABLED':
    config.setdefault('telegram', {})['enabled'] = '$YAML_TELEGRAM_ENABLED'.lower() == 'true'
if '$YAML_NOTIFY_ON_TRADE':
    config.setdefault('telegram', {})['notify_on_trade'] = '$YAML_NOTIFY_ON_TRADE'.lower() == 'true'
if '$YAML_NOTIFY_ON_ERROR':
    config.setdefault('telegram', {})['notify_on_error'] = '$YAML_NOTIFY_ON_ERROR'.lower() == 'true'
if '$YAML_DAILY_SUMMARY':
    config.setdefault('telegram', {})['daily_summary'] = '$YAML_DAILY_SUMMARY'.lower() == 'true'

with open('$SETTINGS_YAML_FILE', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print('YAML settings updated successfully')
PYEOF
}

# Sync all configuration files
sync_config() {
    echo ""
    print_header
    echo ""
    print_option "-" "Synchronizing Configuration Files..."
    echo ""
    
    load_config
    
    if [ -f "$CONFIG_ENV_FILE" ]; then
        print_success "Loaded configuration from $CONFIG_ENV_FILE"
        
        update_env_file
        print_success "Updated $ENV_FILE"
        
        update_yaml_file
        print_success "Updated $SETTINGS_YAML_FILE"
        
        echo ""
        print_success "Configuration synchronized successfully!"
        echo ""
    else
        print_warning "$CONFIG_ENV_FILE not found. Using existing configuration."
        echo ""
    fi
}

# Edit configuration function
do_edit_config() {
    echo ""
    print_header
    echo ""
    
    if [ ! -f "$CONFIG_ENV_FILE" ]; then
        print_warning "$CONFIG_ENV_FILE does not exist. Creating from template..."
        cp "$CONFIG_ENV_FILE" "$CONFIG_ENV_FILE.template" 2>/dev/null || true
    fi
    
    echo "Available editors: nano, vim, vi"
    echo ""
    read -p "Choose editor (nano/vim/vi) [default: nano]: " editor
    editor=${editor:-nano}
    
    if ! command -v $editor &> /dev/null; then
        print_error "$editor not found. Trying alternatives..."
        if command -v nano &> /dev/null; then
            editor=nano
        elif command -v vim &> /dev/null; then
            editor=vim
        elif command -v vi &> /dev/null; then
            editor=vi
        else
            print_error "No text editor found!"
            echo "Please install nano, vim, or vi."
            return 1
        fi
    fi
    
    print_success "Opening $CONFIG_ENV_FILE with $editor..."
    echo ""
    echo "Edit the configuration values, then save and exit."
    echo "After editing, the configuration will be synced to .env and settings.yaml"
    echo ""
    
    $editor "$CONFIG_ENV_FILE"
    
    echo ""
    read -p "Sync configuration to .env and settings.yaml? (y/n): " sync_choice
    if [[ $sync_choice == [yY] || $sync_choice == [yY][eE][sS] ]]; then
        sync_config
    else
        print_warning "Configuration not synced. Run 'sync' option later to apply changes."
    fi
}

# Quick set individual config value
do_set_config() {
    echo ""
    print_header
    echo ""
    
    echo "Common configuration options:"
    echo "  1. BYBIT_API_KEY"
    echo "  2. BYBIT_API_SECRET"
    echo "  3. TRADING_MODE (paper/live)"
    echo "  4. RISK_PER_TRADE"
    echo "  5. MAX_POSITIONS"
    echo "  6. MAX_LEVERAGE"
    echo "  7. OPPORTUNITY_THRESHOLD"
    echo "  8. LOG_LEVEL"
    echo "  9. Custom variable"
    echo ""
    
    read -p "Select option [1-9]: " config_opt
    
    case $config_opt in
        1)
            read -p "Enter BYBIT_API_KEY: " value
            sed -i "s|^BYBIT_API_KEY=.*|BYBIT_API_KEY=$value|" "$CONFIG_ENV_FILE" 2>/dev/null || \
                echo "BYBIT_API_KEY=$value" >> "$CONFIG_ENV_FILE"
            ;;
        2)
            read -p "Enter BYBIT_API_SECRET: " value
            sed -i "s|^BYBIT_API_SECRET=.*|BYBIT_API_SECRET=$value|" "$CONFIG_ENV_FILE" 2>/dev/null || \
                echo "BYBIT_API_SECRET=$value" >> "$CONFIG_ENV_FILE"
            ;;
        3)
            read -p "Enter TRADING_MODE (paper/live): " value
            sed -i "s|^TRADING_MODE=.*|TRADING_MODE=$value|" "$CONFIG_ENV_FILE" 2>/dev/null || \
                echo "TRADING_MODE=$value" >> "$CONFIG_ENV_FILE"
            ;;
        4)
            read -p "Enter RISK_PER_TRADE (e.g., 1.0): " value
            sed -i "s|^RISK_PER_TRADE=.*|RISK_PER_TRADE=$value|" "$CONFIG_ENV_FILE" 2>/dev/null || \
                echo "RISK_PER_TRADE=$value" >> "$CONFIG_ENV_FILE"
            ;;
        5)
            read -p "Enter MAX_POSITIONS: " value
            sed -i "s|^MAX_POSITIONS=.*|MAX_POSITIONS=$value|" "$CONFIG_ENV_FILE" 2>/dev/null || \
                echo "MAX_POSITIONS=$value" >> "$CONFIG_ENV_FILE"
            ;;
        6)
            read -p "Enter MAX_LEVERAGE: " value
            sed -i "s|^MAX_LEVERAGE=.*|MAX_LEVERAGE=$value|" "$CONFIG_ENV_FILE" 2>/dev/null || \
                echo "MAX_LEVERAGE=$value" >> "$CONFIG_ENV_FILE"
            ;;
        7)
            read -p "Enter OPPORTUNITY_THRESHOLD: " value
            sed -i "s|^OPPORTUNITY_THRESHOLD=.*|OPPORTUNITY_THRESHOLD=$value|" "$CONFIG_ENV_FILE" 2>/dev/null || \
                echo "OPPORTUNITY_THRESHOLD=$value" >> "$CONFIG_ENV_FILE"
            ;;
        8)
            read -p "Enter LOG_LEVEL (DEBUG/INFO/WARNING/ERROR): " value
            sed -i "s|^LOG_LEVEL=.*|LOG_LEVEL=$value|" "$CONFIG_ENV_FILE" 2>/dev/null || \
                echo "LOG_LEVEL=$value" >> "$CONFIG_ENV_FILE"
            ;;
        9)
            read -p "Enter variable name: " var_name
            read -p "Enter value: " var_value
            if grep -q "^${var_name}=" "$CONFIG_ENV_FILE" 2>/dev/null; then
                sed -i "s|^${var_name}=.*|${var_name}=${var_value}|" "$CONFIG_ENV_FILE"
            else
                echo "${var_name}=${var_value}" >> "$CONFIG_ENV_FILE"
            fi
            ;;
        *)
            print_error "Invalid option"
            return
            ;;
    esac
    
    print_success "Configuration updated in $CONFIG_ENV_FILE"
    echo ""
    read -p "Sync to .env and settings.yaml now? (y/n): " sync_now
    if [[ $sync_now == [yY] || $sync_now == [yY][eE][sS] ]]; then
        sync_config
    fi
}

# Check if Python is installed
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        return 0
    else
        return 1
    fi
}

# Function to print colored output
print_header() {
    echo -e "${CYAN}"
    echo "========================================"
    echo "   Bybit AI Trader - Management Menu"
    echo "========================================"
    echo -e "${NC}"
}

print_option() {
    echo -e "${BLUE}[${1}]${NC} ${2}"
}

print_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

print_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

# Check if virtual environment exists
check_venv() {
    if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
        return 0
    else
        return 1
    fi
}

# Check if .env file exists
check_env() {
    if [ -f ".env" ]; then
        return 0
    else
        return 1
    fi
}

# Install function
do_install() {
    echo ""
    print_header
    echo ""
    
    # Step 1: Check Python
    print_option "1" "Checking Python installation..."
    if check_python; then
        print_success "Python $PYTHON_VERSION found"
    else
        print_error "Python 3.12+ not found!"
        echo "Please install Python 3.12 or later from https://www.python.org/downloads/"
        exit 1
    fi
    
    # Step 2: Create virtual environment
    print_option "2" "Creating virtual environment..."
    if check_venv; then
        print_warning "Virtual environment already exists, skipping..."
    else
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Step 3: Activate virtual environment
    print_option "3" "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"
    
    # Step 4: Upgrade pip
    print_option "4" "Upgrading pip..."
    pip install --upgrade pip --quiet
    print_success "Pip upgraded"
    
    # Step 5: Install dependencies
    print_option "5" "Installing dependencies (this may take a few minutes)..."
    pip install -r requirements.txt --quiet
    print_success "All dependencies installed"
    
    # Step 6: Create .env file
    print_option "6" "Setting up configuration files..."
    if check_env; then
        print_warning ".env file already exists, skipping..."
    else
        cp .env.example .env
        print_success ".env file created from template"
    fi
    
    # Step 7: Create config directory and settings
    if [ ! -d "config" ]; then
        mkdir -p config
    fi
    if [ ! -f "config/settings.yaml" ]; then
        cp config/settings.yaml.example config/settings.yaml 2>/dev/null || echo "# Settings will be loaded from .env" > config/settings.yaml
    fi
    print_success "Config directory setup complete"
    
    # Step 8: Create necessary directories
    mkdir -p logs database cache
    print_success "Directory structure created"
    
    # Step 9: Initialize database
    print_option "7" "Initializing database..."
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from database.manager import DatabaseManager
    import asyncio
    asyncio.run(DatabaseManager().initialize())
    print('Database initialized successfully')
except Exception as e:
    print(f'Database initialization skipped: {e}')
" 2>/dev/null || print_warning "Database will be initialized on first run"
    
    echo ""
    print_success "Installation completed successfully!"
    echo ""
    print_warning "IMPORTANT: Edit the .env file with your API credentials before running!"
    echo "Run: nano .env  (or use your preferred text editor)"
    echo ""
}

# Run function
do_run() {
    echo ""
    print_header
    echo ""
    
    # Check if installed
    if ! check_venv; then
        print_error "Virtual environment not found!"
        print_warning "Please run option 1 (Install) first."
        echo ""
        return
    fi
    
    if ! check_env; then
        print_error ".env file not found!"
        print_warning "Please run option 1 (Install) first."
        echo ""
        return
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    print_success "Starting Bybit AI Trader..."
    echo ""
    echo "Press Ctrl+C to stop the bot"
    echo ""
    
    # Run the bot
    python3 main.py
}

# Uninstall function
do_uninstall() {
    echo ""
    print_header
    echo ""
    
    print_warning "This will remove:"
    echo "  - Virtual environment (venv/)"
    echo "  - Log files (logs/)"
    echo "  - Database files (database/)"
    echo "  - Cache files (cache/)"
    echo ""
    echo "This will NOT remove:"
    echo "  - Configuration files (.env, config/)"
    echo "  - Source code"
    echo "  - Requirements.txt"
    echo ""
    
    read -p "Are you sure you want to uninstall? (y/n): " confirm
    if [[ $confirm != [yY] && $confirm != [yY][eE][sS] ]]; then
        print_warning "Uninstall cancelled"
        return
    fi
    
    print_option "1" "Removing virtual environment..."
    rm -rf venv
    print_success "Virtual environment removed"
    
    print_option "2" "Removing log files..."
    rm -rf logs/*
    print_success "Log files removed"
    
    print_option "3" "Removing database files..."
    rm -rf database/*
    print_success "Database files removed"
    
    print_option "4" "Removing cache files..."
    rm -rf cache/*
    print_success "Cache files removed"
    
    echo ""
    print_success "Uninstallation completed!"
    echo ""
    print_warning "Your configuration files (.env, config/) have been preserved."
    echo "To reinstall, run this script again and select option 1."
    echo ""
}

# Update function
do_update() {
    echo ""
    print_header
    echo ""
    
    # Check if installed
    if ! check_venv; then
        print_error "Virtual environment not found!"
        print_warning "Please run option 1 (Install) first."
        echo ""
        return
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    print_option "1" "Updating pip..."
    pip install --upgrade pip --quiet
    print_success "Pip updated"
    
    print_option "2" "Updating all dependencies..."
    pip install --upgrade -r requirements.txt --quiet
    print_success "All dependencies updated"
    
    echo ""
    print_success "Update completed successfully!"
    echo ""
}

# Status function
do_status() {
    echo ""
    print_header
    echo ""
    
    print_option "-" "System Status"
    echo ""
    
    # Python version
    if check_python; then
        print_success "Python: $PYTHON_VERSION"
    else
        print_error "Python: Not installed"
    fi
    
    # Virtual environment
    if check_venv; then
        print_success "Virtual Environment: Installed"
    else
        print_error "Virtual Environment: Not installed"
    fi
    
    # .env file
    if check_env; then
        print_success "Configuration: .env file exists"
    else
        print_error "Configuration: .env file missing"
    fi
    
    # Config directory
    if [ -d "config" ] && [ -f "config/settings.yaml" ]; then
        print_success "Config: settings.yaml exists"
    else
        print_warning "Config: settings.yaml missing (will use .env defaults)"
    fi
    
    # Directories
    for dir in logs database cache; do
        if [ -d "$dir" ]; then
            print_success "Directory: $dir/ exists"
        else
            print_warning "Directory: $dir/ missing"
        fi
    done
    
    echo ""
}

# Main menu loop
show_menu() {
    clear
    print_header
    echo ""
    print_option "1" "Install / Setup System"
    print_option "2" "Run Trading Bot"
    print_option "3" "Uninstall (remove venv, logs, database)"
    print_option "4" "Update Dependencies"
    print_option "5" "Check Status"
    print_option "6" "Edit Configuration (config.env)"
    print_option "7" "Set Individual Config Value"
    print_option "8" "Sync Configuration Files"
    print_option "9" "Exit"
    echo ""
    echo "========================================"
}

# Main execution
while true; do
    show_menu
    read -p "Enter your choice [1-9]: " choice
    
    case $choice in
        1)
            do_install
            echo "Press Enter to continue..."
            read
            ;;
        2)
            do_run
            ;;
        3)
            do_uninstall
            echo "Press Enter to continue..."
            read
            ;;
        4)
            do_update
            echo "Press Enter to continue..."
            read
            ;;
        5)
            do_status
            echo "Press Enter to continue..."
            read
            ;;
        6)
            do_edit_config
            echo "Press Enter to continue..."
            read
            ;;
        7)
            do_set_config
            echo "Press Enter to continue..."
            read
            ;;
        8)
            sync_config
            echo "Press Enter to continue..."
            read
            ;;
        9)
            echo ""
            print_success "Goodbye!"
            echo ""
            exit 0
            ;;
        *)
            print_error "Invalid option. Please enter a number between 1 and 9."
            echo "Press Enter to continue..."
            read
            ;;
    esac
done
