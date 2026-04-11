#!/bin/bash
# MangroveSpot — Production Setup on Hostinger VPS (Ubuntu 22.04)

echo "🚀 MangroveSpot Production Setup..."

# System packages
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib nginx redis-server certbot python3-certbot-nginx

# PostgreSQL setup
sudo -u postgres psql <<EOF
CREATE DATABASE mangrovespot_db;
CREATE USER mangrovespot_user WITH PASSWORD 'CHANGE_THIS_PASSWORD';
ALTER ROLE mangrovespot_user SET client_encoding TO 'utf8';
ALTER ROLE mangrovespot_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE mangrovespot_user SET timezone TO 'Asia/Kolkata';
GRANT ALL PRIVILEGES ON DATABASE mangrovespot_db TO mangrovespot_user;
EOF

# Project setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# .env setup
cp .env.example .env
echo "⚠️  Edit .env now with production values before continuing!"
echo "    nano .env"
echo ""
read -p "Press Enter after editing .env..."

# Django production setup
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py createsuperuser

# Enable Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server

echo ""
echo "✅ Setup done! Now configure Nginx and Gunicorn."
echo "   See README for Nginx config and systemd service files."
