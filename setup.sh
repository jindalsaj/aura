#!/bin/bash

echo "🚀 Setting up Aura Personal Assistant..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    exit 1
fi

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed. Please install PostgreSQL first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Setup backend
echo "📦 Setting up backend..."
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp env.example .env
    echo "📝 Created .env file. Please update it with your API keys."
fi

cd ..

# Setup frontend
echo "📦 Setting up frontend..."
cd frontend
npm install
cd ..

# Setup database
echo "🗄️ Setting up database..."
createdb aura_db 2>/dev/null || echo "Database aura_db already exists"

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update backend/.env with your API keys:"
echo "   - Google Client ID/Secret for Gmail and Drive"
echo "   - Plaid Client ID/Secret for bank integration"
echo "   - WhatsApp Access Token for WhatsApp integration"
echo ""
echo "2. Start the backend:"
echo "   cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo ""
echo "3. Start the frontend:"
echo "   cd frontend && npm start"
echo ""
echo "4. Visit http://localhost:3000 to use the app"
echo ""
echo "📚 API documentation will be available at http://localhost:8000/docs"
