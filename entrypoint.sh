#!/bin/bash

./wait-for-it.sh db:5432 -- echo "Creating config file"

if [ ! -f manage.py ]; then
  cd gemini
fi

if [ ! -f gemini/config.py ]; then
    cp gemini/config.py.example gemini/config.py
fi

echo "Apply database migrations"
python manage.py makemigrations && python manage.py migrate

echo "Create dirs"
python manage.py shell -c "from gemini import settings; import os; \
  os.makedirs(settings.TMP_DIR); os.makedirs(settings.TEST_TMP_DIR)"

echo "Starting server"
python manage.py runserver 0.0.0.0:8006
