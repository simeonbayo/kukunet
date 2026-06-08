@echo off
echo ===================================
echo KUKUNET - Phase 1 Setup Script
echo ===================================

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing requirements...
pip install -r requirements\dev.txt

echo Creating .env file...
if not exist .env copy .env.example .env

echo Running migrations...
python manage.py makemigrations
python manage.py migrate

echo Creating superuser...
python manage.py createsuperuser

echo Seeding initial data...
python manage.py seed_data

echo Collecting static files...
python manage.py collectstatic --noinput

echo ===================================
echo Setup complete! Run:
echo venv\Scripts\activate
echo python manage.py runserver
echo ===================================