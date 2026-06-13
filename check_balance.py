import ccxt

api_key = 'w71RsVYyP3FSDTu2RXEcoixynaan8eurroWXQl1E8xzaClxB33PIuEgkM3s8M3Eb'
api_secret = 'weoqhf61oP5Ng5RHv3GEiPv44bH2BQzTJyLkdPUSFzYp3yjOjxMP6Gsp4hAosCfh'

ex = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
})

try:
    balance = ex.fetch_balance()
    print('=== SALDO CONTA REAL BINANCE ===')
    moedas = ['USDT','BTC','ETH','SOL','BNB','FDUSD']
    for coin in moedas:
        total = balance['total'].get(coin, 0)
        free  = balance['free'].get(coin, 0)
        if total > 0.0001:
            print(f'{coin}: {total:.6f} livre: {free:.6f}')
    usdt = balance['total'].get('USDT', 0)
    brl = usdt * 5.40
    print('')
    print('SALDO USDT: $' + str(round(usdt, 2)))
    print('Em reais:   R$' + str(round(brl, 2)))
    print('================================')
except Exception as e:
    print('ERRO conta real: ' + str(e))
    print('Tentando testnet...')
    try:
        ex.set_sandbox_mode(True)
        balance = ex.fetch_balance()
        usdt = balance['total'].get('USDT', 0)
        print('TESTNET USDT: $' + str(round(usdt, 2)))
    except Exception as e2:
        print('ERRO testnet: ' + str(e2))
