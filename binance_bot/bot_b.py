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

# Importa as configurações do Bot B
import config_b as config

# Caminho do arquivo de persistência de estado do Bot B
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
            print(f"\n[ERRO] Falha ao buscar config do backend (Bot B): Status {response.status_code}")
    except Exception as e:
        print(f"\n[ERRO] Falha ao conectar ao backend (Bot B): {e}")
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
            print(f"\n[BACKEND] Trade registrado com sucesso (Bot B): {trade_type} {asset}")
        else:
            print(f"\n[ERRO] Falha ao registrar trade no backend (Bot B): Status {response.status_code}")
    except Exception as e:
        print(f"\n[ERRO] Falha ao conectar ao backend para registrar trade (Bot B): {e}")

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
        print("[BOT B - INFO] Conectado à TESTNET (Simulador) da Binance.")
    else:
        print("[BOT B - PERIGO] CONECTADO À CONTA REAL DA BINANCE! Operações usarão saldo real.")

    return exchange, use_testnet

def send_telegram_message(message):
    """Envia um alerta formatado para o Telegram do usuário se configurado."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id or token == 'seu_token_do_telegram_aqui':
        print(f"[TELEGRAM BOT B] {message}")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': f"🤖 *Bot B (Reversão à Média)*\n\n{message}",
        'parse_mode': 'Markdown'
    }
    
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[ERRO TELEGRAM] Falha ao enviar mensagem do Bot B: {e}")

# --- GERENCIAMENTO DE ESTADO ---

def load_state():
    """Carrega o estado atual do bot do arquivo JSON."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                print(f"[ESTADO BOT B] Estado carregado.")
                return state
        except Exception as e:
            print(f"[ERRO] Falha ao carregar estado do Bot B: {e}")
    
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
        print(f"[ERRO] Falha ao salvar estado do Bot B: {e}")

# --- ANÁLISE TÉCNICA E INDICADORES (BANDAS DE BOLLINGER + RSI) ---

def fetch_candles(exchange, symbol, timeframe, limit=100):
    """Busca candles recentes da Binance e retorna em formato DataFrame."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"[ERRO BOT B] Falha ao buscar candles de {symbol}: {e}")
        return None

def calculate_indicators(df):
    """Calcula as Bandas de Bollinger e o RSI."""
    # Cálculo das Bandas de Bollinger
    df['bb_mid'] = df['close'].rolling(window=config.BOLLINGER_PERIOD).mean()
    df['std'] = df['close'].rolling(window=config.BOLLINGER_PERIOD).std()
    df['bb_upper'] = df['bb_mid'] + (config.BOLLINGER_DEV * df['std'])
    df['bb_lower'] = df['bb_mid'] - (config.BOLLINGER_DEV * df['std'])
    
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
        
        print(f"[BOT B - COMPRA] Enviando compra a mercado de {formatted_qty} {market['base']} a ${current_price}")
        order = exchange.create_market_buy_order(symbol, formatted_qty)
        
        time.sleep(1)
        balance = exchange.fetch_balance()
        base_asset = symbol.split('/')[0]
        actual_qty = balance['free'].get(base_asset, 0.0)
        actual_qty_formatted = float(exchange.amount_to_precision(symbol, actual_qty))
        
        print(f"[BOT B - SUCESSO] Quantidade comprada líquida: {actual_qty_formatted}")
        return order, current_price, actual_qty_formatted
    except Exception as e:
        print(f"[ERRO COMPRA BOT B] Falha ao executar: {e}")
        return None, 0.0, 0.0

def sell_exit(exchange, symbol, qty, reason="Saída"):
    """Executa a venda de uma quantidade do ativo no mercado Spot."""
    try:
        exchange.load_markets()
        formatted_qty = float(exchange.amount_to_precision(symbol, qty))
        
        if formatted_qty <= 0:
            print("[BOT B - AVISO] Quantidade zero. Abortando.")
            return None
            
        print(f"[BOT B - VENDA] Venda de {formatted_qty} ({reason})")
        order = exchange.create_market_sell_order(symbol, formatted_qty)
        return order
    except Exception as e:
        print(f"[ERRO VENDA BOT B] Falha ao executar ({reason}): {e}")
        return None

# --- LOOP PRINCIPAL DO MOTOR DE TRADING ---

def run_trading_bot():
    print("====================================================")
    print("      INICIALIZANDO BOT B - REVERSÃO À MÉDIA         ")
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
                print("\n[BOT B - AVISO] Backend inacessível. O robô usará as chaves locais do arquivo .env.")
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
                    print(f"\n🚨 [BOT B - DESLIGAMENTO] Robô desativado pelo usuário. Fechando posição de {qty} {symbol} a mercado por segurança.")
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        current_price = ticker['last']
                        sell_exit(exchange, symbol, qty, reason="Desligamento Forçado")
                        
                        # Calcula lucro/prejuízo
                        profit_pct = ((current_price - state['entry_price']) / state['entry_price']) * 100
                        register_trade_backend(
                            asset=symbol,
                            trade_type="VENDA (MÉDIA - DESLIG)",
                            price=current_price,
                            amount=qty,
                            value=qty * current_price,
                            profit_pct=profit_pct
                        )
                    except Exception as ex:
                        print(f"[ERRO] Falha ao liquidar posição do Bot B no desligamento: {ex}")
                    
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                
                print(f"\r[BOT B - STATUS] Robô desativado na nuvem. Aguardando ativação... | Horário: {datetime.datetime.now().strftime('%H:%M:%S')}", end="", flush=True)
                time.sleep(15)
                continue

            # 3. Inicializa ou reconecta a Exchange se as chaves mudaram
            if exchange is None or api_key != current_api_key or api_secret != current_api_secret:
                print(f"\n[BOT B - INFO] Inicializando conexão com a Binance usando chaves configuradas...")
                exchange, use_testnet = get_exchange_connection(api_key, api_secret)
                if exchange is None:
                    print("[BOT B - ERRO] Chaves de API inválidas ou vazias. Aguardando configuração...")
                    time.sleep(15)
                    continue
                current_api_key = api_key
                current_api_secret = api_secret
            if state['daily_loss_accumulated'] >= config.MAX_DAILY_LOSS_USDT:
                print(f"\n[BOT B - SUSPENSO] Perda diária atingida (-${state['daily_loss_accumulated']:.2f}).")
                time.sleep(600)
                continue
                
            if state['daily_profit_accumulated'] >= config.MAX_DAILY_PROFIT_USDT:
                print(f"\n[BOT B - CONCLUÍDO] Meta de lucro atingida (+${state['daily_profit_accumulated']:.2f}).")
                time.sleep(600)
                continue

            ticker = exchange.fetch_ticker(config.SYMBOL)
            current_price = ticker['last']
            
            print(f"\r[BOT B] Preço: ${current_price:.2f} | Posicionado: {state['in_position']} | Horário: {datetime.datetime.now().strftime('%H:%M:%S')}", end="")

            # --- CASO 1: ROBÔ POSICIONADO (MONITORAMENTO DO MOTOR DE DEFESA) ---
            if state['in_position']:
                qty = state['quantity_bought']
                entry_price = state['entry_price']
                
                # A. STOP LOSS ATINGIDO
                if current_price <= state['stop_loss_price']:
                    loss_usd = (entry_price - current_price) * qty
                    print(f"\n🚨 [BOT B - DEFESA] STOP LOSS acionado a ${current_price:.2f}!")
                    
                    sell_exit(exchange, config.SYMBOL, qty, reason="Stop Loss")
                    
                    state['daily_loss_accumulated'] += loss_usd
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                    
                    # Registra no backend
                    profit_pct = -((entry_price - current_price) / entry_price) * 100
                    register_trade_backend(
                        asset=config.SYMBOL,
                        trade_type="VENDA (MÉDIA - STOP)",
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
                    print(f"\n🎯 [BOT B - ALVO] Alvo Parcial 1 (TP1) atingido a ${current_price:.2f}!")
                    
                    partial_qty = qty * config.PARTIAL_EXIT_PCT
                    sell_exit(exchange, config.SYMBOL, partial_qty, reason="Parcial (TP1)")
                    
                    time.sleep(1)
                    balance = exchange.fetch_balance()
                    base_asset = config.SYMBOL.split('/')[0]
                    remaining_qty = balance['free'].get(base_asset, 0.0)
                    formatted_remaining = float(exchange.amount_to_precision(config.SYMBOL, remaining_qty))
                    
                    if config.ACTIVATE_BREAKEVEN:
                        state['stop_loss_price'] = entry_price
                        print(f"🛡️ [BOT B - BREAKEVEN] Stop Loss movido para o preço de entrada: ${entry_price:.2f}.")
                    
                    # Lucro parcial
                    partial_profit = (current_price - entry_price) * partial_qty
                    state['daily_profit_accumulated'] += partial_profit
                    
                    # Registra a venda parcial no backend
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                    register_trade_backend(
                        asset=config.SYMBOL,
                        trade_type="VENDA PARCIAL (MÉDIA)",
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

                # C. ALVO FINAL (TP2 OU TOQUE NA BANDA SUPERIOR)
                df = fetch_candles(exchange, config.SYMBOL, config.TIMEFRAME)
                hit_upper_bb = False
                if df is not None:
                    df = calculate_indicators(df)
                    last_row = df.iloc[-1]
                    # Se tocar ou fechar acima da Banda de Bollinger Superior, indica exaustão do movimento de alta
                    hit_upper_bb = current_price >= last_row['bb_upper']

                if current_price >= state['take_profit_2'] or hit_upper_bb:
                    profit_usd = (current_price - entry_price) * qty
                    razao = "Alvo Final (TP2)" if current_price >= state['take_profit_2'] else "Toque na Banda Superior"
                    print(f"\n🏆 [BOT B - SUCESSO] Saída final acionada ({razao}) a ${current_price:.2f}!")
                    
                    sell_exit(exchange, config.SYMBOL, qty, reason=razao)
                    
                    state['daily_profit_accumulated'] += profit_usd
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                    
                    # Registra no backend
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                    register_trade_backend(
                        asset=config.SYMBOL,
                        trade_type="VENDA (MÉDIA - TP)",
                        price=current_price,
                        amount=qty,
                        value=qty * current_price,
                        profit_pct=profit_pct
                    )
                    
                    send_telegram_message(
                        f"🏆 *Alvo Final Atingido ({razao})!*\n"
                        f"📈 Preço: ${current_price:.2f}\n"
                        f"💵 Lucro final: +${profit_usd:.2f}"
                    )
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

            # --- CASO 2: ROBÔ FLAT (PROCURANDO OPORTUNIDADE DE COMPRA BARATA) ---
            else:
                df = fetch_candles(exchange, config.SYMBOL, config.TIMEFRAME)
                if df is not None:
                    df = calculate_indicators(df)
                    prev_row = df.iloc[-2]
                    last_row = df.iloc[-1]
                    
                    # Estratégia "Fechou Fora, Fechou Dentro":
                    # O candle anterior fechou abaixo da banda inferior (fora das bandas)
                    # O candle atual fechou acima da banda inferior (voltou para dentro das bandas)
                    fechou_fora = prev_row['close'] < prev_row['bb_lower']
                    fechou_dentro = last_row['close'] >= last_row['bb_lower']
                    
                    # Filtro de RSI: Garante que o mercado está realmente sobrevendido (abaixo ou perto de 35)
                    rsi_sobrevendido = last_row['rsi'] < 40
                    
                    if fechou_fora and fechou_dentro and rsi_sobrevendido:
                        print(f"\n🚀 [BOT B - SINAL] Fechou Fora/Dentro detectado (Reversão à Média)!")
                        print(f"📊 BB Inferior: {last_row['bb_lower']:.2f} | Close Anterior: {prev_row['close']:.2f} | Close Atual: {last_row['close']:.2f} | RSI: {last_row['rsi']:.1f}")
                        
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
                                trade_type="COMPRA (MÉDIA)",
                                price=buy_price,
                                amount=qty_bought,
                                value=qty_bought * buy_price
                            )
                            
                            send_telegram_message(
                                f"🚀 *Bot B: Nova Posição Aberta*\n"
                                f"🪙 Ativo: {config.SYMBOL}\n"
                                f"💵 Entrada: ${buy_price:.2f}\n"
                                f"📦 Qtd: {qty_bought}\n\n"
                                f"🛑 Stop Loss: ${state['stop_loss_price']:.2f}\n"
                                f"🎯 Alvo Parcial (TP1): ${state['take_profit_1']:.2f}\n"
                                f"🏆 Alvo Final (TP2): ${state['take_profit_2']:.2f}"
                            )

            time.sleep(config.LOOP_INTERVAL_SECONDS)
            
        except ccxt.NetworkError as ne:
            print(f"\n[BOT B - ERRO DE REDE] {ne}. Tentando novamente em 15s...")
            time.sleep(15)
        except ccxt.ExchangeError as ee:
            print(f"\n[BOT B - ERRO DE API] {ee}. Tentando em 30s...")
            time.sleep(30)
        except Exception as e:
            print(f"\n[BOT B - ERRO CRÍTICO] {e}. Reiniciando loop em 30s...")
            time.sleep(30)

if __name__ == '__main__':
    run_trading_bot()
