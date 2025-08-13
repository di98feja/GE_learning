#!/bin/bash
# Grid Enforcer Development Setup Script

set -e  # Exit on any error

echo "🚀 Setting up Grid Enforcer development environment..."

# Function to detect Python command
detect_python() {
    if command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        echo "python"
    else
        echo "❌ Python not found! Please install Python 3.11 or later."
        echo "On Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-venv python3-pip"
        echo "On macOS: brew install python3"
        echo "On Windows: Download from https://python.org"
        exit 1
    fi
}

# Detect Python
PYTHON=$(detect_python)
echo "✅ Found Python: $PYTHON"

# Check Python version
PYTHON_VERSION=$($PYTHON --version 2>&1 | cut -d' ' -f2)
echo "📋 Python version: $PYTHON_VERSION"

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Removing old one..."
    rm -rf venv
fi

$PYTHON -m venv venv

# Activate virtual environment and install dependencies
echo "📥 Installing dependencies..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source venv/Scripts/activate
else
    # Linux/macOS
    source venv/bin/activate
fi

# Upgrade pip
pip install --upgrade pip

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Requirements installed"
else
    echo "⚠️  requirements.txt not found. Creating minimal one..."
    cat > requirements.txt << EOF
# Core dependencies for Grid Enforcer
pymodbus>=3.5.0
paho-mqtt>=1.6.1
pydantic>=2.0.0

# Development tools
pytest>=7.0.0
black>=23.0.0
isort>=5.12.0
mypy>=1.5.0

# Home Assistant for testing
homeassistant>=2024.1.0
EOF
    pip install -r requirements.txt
    echo "✅ Created and installed requirements.txt"
fi

# Create basic project structure if needed
echo "📁 Setting up project structure..."
mkdir -p custom_components/grid_enforcer
mkdir -p tests
mkdir -p config

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "📝 Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
venv/
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Home Assistant
config/.*
config/deps/
config/tts/
config/secrets.yaml
config/known_devices.yaml
config/entity_registry.yaml
config/device_registry.yaml
config/.storage/

# Docker
.docker/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Logs
*.log
mosquitto/data/*
mosquitto/log/*

# OS
.DS_Store
Thumbs.db
EOF
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "To activate the virtual environment:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "  source venv/Scripts/activate"
else
    echo "  source venv/bin/activate"
fi
echo ""
echo "Then you can run:"
echo "  black custom_components/"
echo "  isort custom_components/"
echo "  pytest tests/ -v"
echo ""
echo "Or use the Makefile commands:"
echo "  make format    # Format code"
echo "  make lint      # Check code quality"
echo "  make test      # Run tests"
echo "  make dev-up    # Start development services"
echo ""