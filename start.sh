#!/bin/sh

echo "Starting Python bots in the background..."
cd /app/binance_bot
python3 run_all_bots.py &

echo "Starting NestJS server..."
cd /app
npm run start:prod
