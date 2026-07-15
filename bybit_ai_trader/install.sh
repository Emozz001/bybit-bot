#!/bin/bash

###############################################################################
# Bybit AI Trader - Installation Script for macOS
# 
# This script will:
# 1. Check Python version (requires 3.12+)
# 2. Create a virtual environment
# 3. Install all required dependencies
# 4. Set up configuration files
# 5. Initialize the database
#
# Usage: ./install.sh
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Bybit AI Trader - Installation Script              ║${NC}"
echo -e "${BLUE}║     For macOS (MacBook Air 2017 compatible)           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print status messages
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    print_warning "This script is optimized for macOS. You're running on $(uname)."
    print_warning "The bot should still work, but you may need to adjust some commands."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python version
print_status "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.12 or higher."
    print_error "Download from: https://www.python.org/downloads/mac-osx/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo -e "  Found Python ${PYTHON_VERSION}"

if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 12 ]]; then
    print_error "Python 3.12 or higher is required. You have ${PYTHON_VERSION}."
    print_error "Please upgrade Python from: https://www.python.org/downloads/mac-osx/"
    exit 1
fi

print_success "Python version check passed!"

# Check if virtual environment already exists
if [ -d "venv" ]; then
    print_warning "Virtual environment 'venv' already exists."
    read -p "Do you want to recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Removing existing virtual environment..."
        rm -rf venv
    else
        print_status "Using existing virtual environment."
    fi
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created!"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip and setuptools..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
print_success "Pip upgraded!"

# Install dependencies
print_status "Installing dependencies from requirements.txt..."
print_warning "This may take a few minutes..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    print_success "All dependencies installed!"
else
    print_error "Failed to install dependencies."
    exit 1
fi

# Setup configuration files
print_status "Setting up configuration files..."

# Copy .env.example to .env if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_success "Created .env file from template."
    print_warning "Please edit .env with your Bybit API credentials before running."
else
    print_status ".env file already exists."
fi

# Ensure config directory exists
if [ ! -d "config" ]; then
    mkdir -p config
fi

# Create default settings.yaml if it doesn't exist
if [ ! -f "config/settings.yaml" ]; then
    cat > config/settings.yaml << 'EOF'
# Bybit AI Trader Configuration

trading:
  mode: "paper"  # paper or live
  enabled: true
  
risk:
  max_leverage: 10
  risk_per_trade: 0.01  # 1% of balance
  daily_loss_limit: 0.05  # 5% of balance
  weekly_loss_limit: 0.10  # 10% of balance
  monthly_loss_limit: 0.20  # 20% of balance
  max_positions: 5
  min_risk_reward: 2.0

scanner:
  enabled: true
  scan_interval: 5  # seconds
  opportunity_threshold: 90  # minimum score to consider

timeframes:
  - "1m"
  - "3m"
  - "5m"
  - "15m"
  - "30m"
  - "1h"
  - "4h"
  - "1d"

dashboard:
  refresh_rate: 1  # seconds
  show_all_symbols: false
  max_opportunities_display: 10

database:
  path: "database/trading.db"
  backup_enabled: true
  backup_interval: 86400  # seconds (24 hours)

logging:
  level: "INFO"
  save_to_file: true
  rotation_size: "10 MB"
  backup_count: 5

telegram:
  enabled: false
  # bot_token: "YOUR_BOT_TOKEN"
  # chat_id: "YOUR_CHAT_ID"
EOF
    print_success "Created default config/settings.yaml"
else
    print_status "config/settings.yaml already exists."
fi

# Ensure logs directory exists
if [ ! -d "logs" ]; then
    mkdir -p logs
    print_status "Created logs directory."
fi

# Ensure database directory exists
if [ ! -d "database" ]; then
    mkdir -p database
    print_status "Created database directory."
fi

# Initialize database
print_status "Initializing database..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from database.manager import DatabaseManager
    db = DatabaseManager()
    db.initialize()
    print('Database initialized successfully!')
except Exception as e:
    print(f'Database initialization note: {e}')
    print('Database will be initialized on first run.')
" 2>/dev/null || print_status "Database will be initialized on first run."

# Create run script
cat > run.sh << 'EOF'
#!/bin/bash
# Bybit AI Trader - Run Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Please run ./install.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Run the bot
echo "Starting Bybit AI Trader..."
python3 main.py
EOF

chmod +x run.sh
print_success "Created run.sh script."

# Print summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Installation Complete!                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Configure your API credentials:"
echo -e "   ${BLUE}nano .env${NC}  (or use your favorite text editor)"
echo ""
echo "2. Review trading settings (optional):"
echo -e "   ${BLUE}nano config/settings.yaml${NC}"
echo ""
echo "3. Run the trading bot:"
echo -e "   ${BLUE}./run.sh${NC}"
echo ""
echo -e "   Or manually:"
echo -e "   ${BLUE}source venv/bin/activate${NC}"
echo -e "   ${BLUE}python3 main.py${NC}"
echo ""
echo -e "${YELLOW}Important Notes:${NC}"
echo ""
echo "• The bot starts in PAPER TRADING mode by default (no real money)"
echo "• Test thoroughly before switching to live trading"
echo "• Never share your API keys or .env file"
echo "• Keep your system awake for continuous operation"
echo ""
echo -e "${BLUE}For help, see README.md or run: ${NC}${YELLOW}python3 main.py --help${NC}"
echo ""
print_success "Happy Trading! 🚀"
echo ""
