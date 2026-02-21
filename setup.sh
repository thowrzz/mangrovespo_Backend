#!/bin/bash
# MangroveSpot — Dev Setup Script
# Run this once after cloning the repo

echo "🌿 Setting up MangroveSpot Backend..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy .env file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ .env file created — fill in your values!"
fi

# Run migrations (SQLite in dev — zero config)
python manage.py migrate

# Create superuser
echo "Creating Django superuser..."
python manage.py createsuperuser

echo ""
echo "✅ Setup complete! Run the server with:"
echo "   source venv/bin/activate"
echo "   python manage.py runserver"
echo ""
echo "📌 API available at: http://localhost:8000/api/v1/"
echo "📌 Django Admin:     http://localhost:8000/django-admin/"
