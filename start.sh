#!/bin/sh

# Executa a criação das tabelas no banco de dados
echo "Running prisma db push..."
npx prisma db push

# Inicia o robô Python em segundo plano e salva o PID
echo "Starting Python bots..."
cd /app/binance_bot
python3 -u run_all_bots.py &
BOT_PID=$!

# Inicia o servidor NestJS em segundo plano e salva o PID
echo "Starting NestJS server..."
cd /app
npm run start:prod &
NEST_PID=$!

# Loop de monitoramento: se qualquer um dos processos cair, encerra o container
while true; do
  if ! kill -0 $BOT_PID 2>/dev/null; then
    echo "❌ O processo do robô Python caiu! Reiniciando container..."
    exit 1
  fi

  if ! kill -0 $NEST_PID 2>/dev/null; then
    echo "❌ O processo do servidor NestJS caiu! Reiniciando container..."
    exit 1
  fi

  sleep 10
done
