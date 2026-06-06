import os
import time
import json
import datetime
import requests
import ccxt
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Carrega as configurações de variáveis de ambiente (.env)
load_dotenv()

# Importa as configurações do Bot A
import config_a as config

# Caminho do arquivo de persistência de estado do Bot A
STATE_FILE = config.STATE_FILE

# --- FUNÇÕES DE CONEXÃO COM O BACKEND API ---

def fetch_backend_config():
    """Busca as configurações do robô no backend NestJS."""
    backend_url = os.getenv('BACKEND_URL', 'http://localhost:3000')
    user_id = os.getenv('USER_ID', 'guest')
    try:
        response = requests.get(f"{backend_url}/bot/config?userId={user_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"\n[ERRO] Falha ao buscar config do backend (Bot C): Status {response.status_code}")
    except Exception as e:
        print(f"\n[ERRO] Falha ao conectar ao backend (Bot C): {e}")
    return None

def register_trade_backend(asset, trade_type, price, amount, value, profit_pct=None):
    """Registra uma transação no backend para aparecer no histórico do app."""
    backend_url = os.getenv('BACKEND_URL', 'http://localhost:3000')
    user_id = os.getenv('USER_ID', 'guest')
    payload = {
        'userId': user_id,
        'asset': asset,
        'type': trade_type,
        'price': float(price),
        'amount': float(amount),
        'value': float(value)
    }
    if profit_pct is not None:
        payload['profitPct'] = f"{profit_pct:+.2f}%" if isinstance(profit_pct, (int, float)) else str(profit_pct)

    try:
        response = requests.post(f"{backend_url}/bot/trades", json=payload, timeout=10)
        if response.status_code == 201:
            print(f"\n[BACKEND] Trade registrado com sucesso (Bot C): {trade_type} {asset}")
        else:
            print(f"\n[ERRO] Falha ao registrar trade no backend (Bot C): Status {response.status_code}")
    except Exception as e:
        print(f"\n[ERRO] Falha ao conectar ao backend para registrar trade (Bot C): {e}")

# --- FUNÇÕES DE INICIALIZAÇÃO E UTILITÁRIAS ---

def get_exchange_connection(api_key=None, api_secret=None):
    """Inicializa a conexão com a API da Binance usando CCXT."""
    if not api_key or api_key == 'sua_chave_api_aqui':
        api_key = os.getenv('BINANCE_API_KEY')
    if not api_secret or api_secret == 'sua_chave_api_aqui':
        api_secret = os.getenv('BINANCE_API_SECRET')
    use_testnet = os.getenv('USE_TESTNET', 'True').lower() == 'true'

    if not api_key or not api_secret or api_key == 'sua_chave_api_aqui':
        print("[AVISO] Chaves de API não configuradas corretamente no arquivo .env!")
        print("[INFO] O bot rodará apenas em modo de leitura (sem enviar ordens reais ou simuladas).")
        return ccxt.binance({
            'enableRateLimit': True,
        }), use_testnet

    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot'
        }
    })

    if use_testnet:
        exchange.set_sandbox_mode(True)
        print("[BOT A - INFO] Conectado à TESTNET (Simulador) da Binance.")
    else:
        print("[BOT A - PERIGO] CONECTADO À CONTA REAL DA BINANCE! Operações usarão saldo real.")

    return exchange, use_testnet

def send_telegram_message(message):
    """Envia um alerta formatado para o Telegram do usuário se configurado."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id or token == 'seu_token_do_telegram_aqui':
        print(f"[TELEGRAM BOT A] {message}")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': f"🤖 *Bot A (Seguidor de Tendência)*\n\n{message}",
        'parse_mode': 'Markdown'
    }
    
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[ERRO TELEGRAM] Falha ao enviar mensagem: {e}")

# --- GERENCIAMENTO DE ESTADO ---

def load_state():
    """Carrega o estado atual do bot do arquivo JSON."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                print(f"[ESTADO BOT A] Estado carregado.")
                return state
        except Exception as e:
            print(f"[ERRO] Falha ao carregar estado do Bot A: {e}")
    
    return {
        'in_position': False,
        'entry_price': 0.0,
        'stop_loss_price': 0.0,
        'take_profit_1': 0.0,
        'take_profit_2': 0.0,
        'quantity_bought': 0.0,
        'is_partial_executed': False,
        'daily_loss_accumulated': 0.0,
        'daily_profit_accumulated': 0.0,
        'last_reset_date': str(datetime.date.today())
    }

def save_state(state):
    """Salva o estado atual do bot no arquivo JSON."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"[ERRO] Falha ao salvar estado do Bot A: {e}")

# --- ANÁLISE TÉCNICA E INDICADORES ---

def fetch_candles(exchange, symbol, timeframe, limit=100):
    """Busca candles recentes da Binance e retorna em formato DataFrame."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"[ERRO BOT A] Falha ao buscar candles de {symbol}: {e}")
        return None

def calculate_indicators(df):
    """Calcula as Médias Móveis Exponenciais (EMA) e o RSI."""
    # Cálculo das EMAs
    df['ema_fast'] = df['close'].ewm(span=config.EMA_FAST_PERIOD, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=config.EMA_SLOW_PERIOD, adjust=False).mean()
    
    # Cálculo do RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=config.RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=config.RSI_PERIOD).mean()
    
    rs = gain / (loss + 1e-9)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df

# --- MOTOR DE EXECUÇÃO DE ORDENS E DEFESA ---

def buy_entry(exchange, symbol, amount_usdt):
    """Executa a compra do ativo no mercado Spot calculando precisões corretas."""
    try:
        exchange.load_markets()
        market = exchange.market(symbol)
        
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        qty = amount_usdt / current_price
        formatted_qty = float(exchange.amount_to_precision(symbol, qty))
        
        print(f"[BOT A - COMPRA] Enviando compra a mercado de {formatted_qty} {market['base']} a ${current_price}")
        order = exchange.create_market_buy_order(symbol, formatted_qty)
        
        time.sleep(1)
        balance = exchange.fetch_balance()
        base_asset = symbol.split('/')[0]
        actual_qty = balance['free'].get(base_asset, 0.0)
        actual_qty_formatted = float(exchange.amount_to_precision(symbol, actual_qty))
        
        print(f"[BOT A - SUCESSO] Quantidade comprada líquida: {actual_qty_formatted}")
        return order, current_price, actual_qty_formatted
    except Exception as e:
        print(f"[ERRO COMPRA BOT A] Falha ao executar: {e}")
        return None, 0.0, 0.0

def sell_exit(exchange, symbol, qty, reason="Saída"):
    """Executa a venda de uma quantidade do ativo no mercado Spot."""
    try:
        exchange.load_markets()
        formatted_qty = float(exchange.amount_to_precision(symbol, qty))
        
        if formatted_qty <= 0:
            print("[BOT A - AVISO] Quantidade zero. Abortando.")
            return None
            
        print(f"[BOT A - VENDA] Venda de {formatted_qty} ({reason})")
        order = exchange.create_market_sell_order(symbol, formatted_qty)
        return order
    except Exception as e:
        print(f"[ERRO VENDA BOT A] Falha ao executar ({reason}): {e}")
        return None

# --- LOOP PRINCIPAL DO MOTOR DE TRADING ---

def run_trading_bot():
    print("====================================================")
    print("      INICIALIZANDO BOT A - SEGUIDOR DE TENDÊNCIA    ")
    print("====================================================")
    
    state = load_state()
    
    today_str = str(datetime.date.today())
    if state.get('last_reset_date') != today_str:
        state['daily_loss_accumulated'] = 0.0
        state['daily_profit_accumulated'] = 0.0
        state['last_reset_date'] = today_str
        save_state(state)

    exchange = None
    use_testnet = False
    current_api_key = None
    current_api_secret = None

    while True:
        try:
            # 1. Busca configurações no backend
            backend_config = fetch_backend_config()
            
            if backend_config is None:
                print("\n[BOT C - AVISO] Backend inacessível. O robô usará as chaves locais do arquivo .env.")
                api_key = os.getenv('BINANCE_API_KEY')
                api_secret = os.getenv('BINANCE_API_SECRET')
                is_active = True  # Assume ativo em caso de queda do backend para monitoramento local
            else:
                api_key = backend_config.get('binanceApiKey')
                api_secret = backend_config.get('binanceApiSecret')
                is_active = backend_config.get('isActive', False)

            # 2. Se o usuário desativou o robô
            if not is_active:
                # Se estiver posicionado, fecha a posição imediatamente para segurança do saldo
                if state['in_position'] and exchange is not None:
                    qty = state['quantity_bought']
                    symbol = config.SYMBOL
                    print(f"\n🚨 [BOT C - DESLIGAMENTO] Robô desativado pelo usuário. Fechando posição de {qty} {symbol} a mercado por segurança.")
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        current_price = ticker['last']
                        sell_exit(exchange, symbol, qty, reason="Desligamento Forçado")
                        
                        # Calcula lucro/prejuízo
                        profit_pct = ((current_price - state['entry_price']) / state['entry_price']) * 100
                        register_trade_backend(
                            asset=symbol,
                            trade_type="VENDA (BTC-TEND - DESLIG)",
                            price=current_price,
                            amount=qty,
                            value=qty * current_price,
                            profit_pct=profit_pct
                        )
                    except Exception as ex:
                        print(f"[ERRO] Falha ao liquidar posição do Bot C no desligamento: {ex}")
                    
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                
                print(f"\r[BOT C - STATUS] Robô desativado na nuvem. Aguardando ativação... | Horário: {datetime.datetime.now().strftime('%H:%M:%S')}", end="", flush=True)
                time.sleep(15)
                continue

            # 3. Inicializa ou reconecta a Exchange se as chaves mudaram
            if exchange is None or api_key != current_api_key or api_secret != current_api_secret:
                print(f"\n[BOT C - INFO] Inicializando conexão com a Binance usando chaves configuradas...")
                exchange, use_testnet = get_exchange_connection(api_key, api_secret)
                if exchange is None:
                    print("[BOT C - ERRO] Chaves de API inválidas ou vazias. Aguardando configuração...")
                    time.sleep(15)
                    continue
                current_api_key = api_key
                current_api_secret = api_secret
            if state['daily_loss_accumulated'] >= config.MAX_DAILY_LOSS_USDT:
                print(f"\n[BOT A - SUSPENSO] Perda diária atingida (-${state['daily_loss_accumulated']:.2f}).")
                time.sleep(600)
                continue
                
            if state['daily_profit_accumulated'] >= config.MAX_DAILY_PROFIT_USDT:
                print(f"\n[BOT A - CONCLUÍDO] Meta de lucro atingida (+${state['daily_profit_accumulated']:.2f}).")
                time.sleep(600)
                continue

            ticker = exchange.fetch_ticker(config.SYMBOL)
            current_price = ticker['last']
            
            print(f"\r[BOT A] Preço: ${current_price:.2f} | Posicionado: {state['in_position']} | Horário: {datetime.datetime.now().strftime('%H:%M:%S')}", end="")

            # --- CASO 1: ROBÔ POSICIONADO (MONITORAMENTO DO MOTOR DE DEFESA) ---
            if state['in_position']:
                qty = state['quantity_bought']
                entry_price = state['entry_price']
                
                # A. STOP LOSS ATINGIDO
                if current_price <= state['stop_loss_price']:
                    loss_usd = (entry_price - current_price) * qty
                    print(f"\n🚨 [BOT C - DEFESA] STOP LOSS acionado a ${current_price:.2f}!")
                    
                    sell_exit(exchange, config.SYMBOL, qty, reason="Stop Loss")
                    
                    state['daily_loss_accumulated'] += loss_usd
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                    
                    # Registra no backend
                    profit_pct = -((entry_price - current_price) / entry_price) * 100
                    register_trade_backend(
                        asset=config.SYMBOL,
                        trade_type="VENDA (BTC-TEND - STOP)",
                        price=current_price,
                        amount=qty,
                        value=qty * current_price,
                        profit_pct=profit_pct
                    )
                    
                    send_telegram_message(
                        f"❌ *Operação encerrada no Stop Loss*\n"
                        f"📉 Preço de Saída: ${current_price:.2f}\n"
                        f"💸 Perda simulada: -${loss_usd:.2f}"
                    )
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                # B. REALIZAÇÃO PARCIAL (TP1) E BREAKEVEN
                if not state['is_partial_executed'] and current_price >= state['take_profit_1']:
                    print(f"\n🎯 [BOT C - ALVO] Alvo Parcial 1 (TP1) atingido a ${current_price:.2f}!")
                    
                    partial_qty = qty * config.PARTIAL_EXIT_PCT
                    sell_exit(exchange, config.SYMBOL, partial_qty, reason="Parcial (TP1)")
                    
                    time.sleep(1)
                    balance = exchange.fetch_balance()
                    base_asset = config.SYMBOL.split('/')[0]
                    remaining_qty = balance['free'].get(base_asset, 0.0)
                    formatted_remaining = float(exchange.amount_to_precision(config.SYMBOL, remaining_qty))
                    
                    if config.ACTIVATE_BREAKEVEN:
                        state['stop_loss_price'] = entry_price
                        print(f"🛡️ [BOT C - BREAKEVEN] Stop Loss movido para o preço de entrada: ${entry_price:.2f}.")
                    
                    # Lucro parcial
                    partial_profit = (current_price - entry_price) * partial_qty
                    state['daily_profit_accumulated'] += partial_profit
                    
                    # Registra a venda parcial no backend
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                    register_trade_backend(
                        asset=config.SYMBOL,
                        trade_type="VENDA PARCIAL (BTC-TEND)",
                        price=current_price,
                        amount=partial_qty,
                        value=partial_qty * current_price,
                        profit_pct=profit_pct
                    )

                    # Verifica se o que restou na carteira é apenas poeira/dust (menor que $2)
                    remaining_value_usdt = formatted_remaining * current_price
                    if remaining_value_usdt < 2.0:
                        state['in_position'] = False
                        state['is_partial_executed'] = False
                        state['quantity_bought'] = 0.0
                        print(f"\n📌 [INFO] Posição totalmente encerrada (restante de ${remaining_value_usdt:.2f} é poeira/dust).")
                    else:
                        state['quantity_bought'] = formatted_remaining
                        state['is_partial_executed'] = True
                    
                    save_state(state)
                    
                    send_telegram_message(
                        f"🎯 *Parcial (TP1) Concluída!*\n"
                        f"💰 Preço: ${current_price:.2f}\n"
                        f"📈 Lucro parcial: +${partial_profit:.2f}\n"
                        f"🛡️ *Breakeven Ativado:* Stop Loss movido para a entrada (${entry_price:.2f})."
                    )
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                # C. ALVO FINAL (TP2)
                if current_price >= state['take_profit_2']:
                    profit_usd = (current_price - entry_price) * qty
                    print(f"\n🏆 [BOT C - SUCESSO] Alvo Final (TP2) atingido a ${current_price:.2f}!")
                    
                    sell_exit(exchange, config.SYMBOL, qty, reason="Alvo Final (TP2)")
                    
                    state['daily_profit_accumulated'] += profit_usd
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                    
                    # Registra no backend
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                    register_trade_backend(
                        asset=config.SYMBOL,
                        trade_type="VENDA (BTC-TEND - TP)",
                        price=current_price,
                        amount=qty,
                        value=qty * current_price,
                        profit_pct=profit_pct
                    )
                    
                    send_telegram_message(
                        f"🏆 *Alvo Final (TP2) Atingido!*\n"
                        f"📈 Preço: ${current_price:.2f}\n"
                        f"💵 Lucro final: +${profit_usd:.2f}"
                    )
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                # D. SAÍDA TÉCNICA (SINAL REVERSO DE TENDÊNCIA)
                df = fetch_candles(exchange, config.SYMBOL, config.TIMEFRAME)
                if df is not None:
                    df = calculate_indicators(df)
                    last_row = df.iloc[-1]
                    
                    if last_row['ema_fast'] < last_row['ema_slow']:
                        profit_usd = (current_price - entry_price) * qty
                        print(f"\n⚠️ [BOT A - TÉCNICO] Médias cruzaram para baixo. Fechando posição preventivamente.")
                        
                        sell_exit(exchange, config.SYMBOL, qty, reason="Saída Técnica (Cruzamento Reverso)")
                        
                        if profit_usd > 0:
                            state['daily_profit_accumulated'] += profit_usd
                        else:
                            state['daily_loss_accumulated'] += abs(profit_usd)
                            
                        state['in_position'] = False
                        state['is_partial_executed'] = False
                        save_state(state)
                        
                        # Registra no backend
                        profit_pct = ((current_price - entry_price) / entry_price) * 100
                        register_trade_backend(
                            asset=config.SYMBOL,
                            trade_type="VENDA (BTC-TEND - TÉC)",
                            price=current_price,
                            amount=qty,
                            value=qty * current_price,
                            profit_pct=profit_pct
                        )
                        
                        send_telegram_message(
                            f"⚠️ *Bot C: Saída Técnica*\n"
                            f"📉 Preço: ${current_price:.2f}\n"
                            f"💵 Resultado estimado: {'+$' if profit_usd >= 0 else '-$'}{abs(profit_usd):.2f}"
                        )

            # --- CASO 2: ROBÔ FLAT (PROCURANDO OPORTUNIDADE DE ATAQUE) ---
            else:
                df = fetch_candles(exchange, config.SYMBOL, config.TIMEFRAME)
                if df is not None:
                    df = calculate_indicators(df)
                    prev_row = df.iloc[-2]
                    last_row = df.iloc[-1]
                    
                    cruzamento_alta = (prev_row['ema_fast'] <= prev_row['ema_slow']) and (last_row['ema_fast'] > last_row['ema_slow'])
                    rsi_aceitavel = last_row['rsi'] < config.RSI_OVERBOUGHT
                    
                    if cruzamento_alta and rsi_aceitavel:
                        print(f"\n🚀 [BOT A - SINAL] Cruzamento de Alta detectado!")
                        
                        order, buy_price, qty_bought = buy_entry(exchange, config.SYMBOL, config.TRADE_AMOUNT_USDT)
                        
                        if order is not None and qty_bought > 0:
                            state['in_position'] = True
                            state['entry_price'] = buy_price
                            state['quantity_bought'] = qty_bought
                            state['stop_loss_price'] = buy_price * (1.0 - config.STOP_LOSS_PCT)
                            state['take_profit_1'] = buy_price * (1.0 + config.TAKE_PROFIT_1_PCT)
                            state['take_profit_2'] = buy_price * (1.0 + config.TAKE_PROFIT_2_PCT)
                            state['is_partial_executed'] = False
                            save_state(state)
                            
                            # Registra compra no backend
                            register_trade_backend(
                                asset=config.SYMBOL,
                                trade_type="COMPRA (BTC-TEND)",
                                price=buy_price,
                                amount=qty_bought,
                                value=qty_bought * buy_price
                            )
                            
                            send_telegram_message(
                                f"🚀 *Bot C: Nova Posição Aberta*\n"
                                f"🪙 Ativo: {config.SYMBOL}\n"
                                f"💵 Entrada: ${buy_price:.2f}\n"
                                f"📦 Qtd: {qty_bought}\n\n"
                                f"🛑 Stop Loss: ${state['stop_loss_price']:.2f}\n"
                                f"🎯 Alvo Parcial (TP1): ${state['take_profit_1']:.2f}\n"
                                f"🏆 Alvo Final (TP2): ${state['take_profit_2']:.2f}"
                            )

            time.sleep(config.LOOP_INTERVAL_SECONDS)
            
        except ccxt.NetworkError as ne:
            print(f"\n[BOT A - ERRO DE REDE] {ne}. Tentando novamente em 15s...")
            time.sleep(15)
        except ccxt.ExchangeError as ee:
            print(f"\n[BOT A - ERRO DE API] {ee}. Tentando em 30s...")
            time.sleep(30)
        except Exception as e:
            print(f"\n[BOT A - ERRO CRÍTICO] {e}. Reiniciando loop em 30s...")
            time.sleep(30)

if __name__ == '__main__':
    run_trading_bot()
