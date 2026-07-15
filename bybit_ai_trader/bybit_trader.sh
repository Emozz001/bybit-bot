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

# Check if Python is installed
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        return 0
    else
        return 1
    fi
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
    print_option "6" "Exit"
    echo ""
    echo "========================================"
}

# Main execution
while true; do
    show_menu
    read -p "Enter your choice [1-6]: " choice
    
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
            echo ""
            print_success "Goodbye!"
            echo ""
            exit 0
            ;;
        *)
            print_error "Invalid option. Please enter a number between 1 and 6."
            echo "Press Enter to continue..."
            read
            ;;
    esac
done
