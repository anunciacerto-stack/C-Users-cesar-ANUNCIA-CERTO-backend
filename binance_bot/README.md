# 🤖 Robô de Trading Binance com Motor de Defesa Automático

Este é um robô de trading de criptomoedas automatizado em Python, projetado para operar na **Binance** (via Spot API) com uma estratégia focada em **preservação de capital** e **ganho consistente**.

Ele utiliza médias móveis exponenciais (EMA) e RSI para identificar tendências de alta, e um robusto **Motor de Defesa** que atua diminuindo o risco para zero assim que o preço começa a andar a favor.

---

## 🛡️ O Motor de Defesa (Como Funciona)

1. **Entrada:** O robô detecta o cruzamento de médias e abre uma compra. Ele envia os parâmetros iniciais para o Telegram e começa a monitorar o mercado segundo a segundo.
2. **Realização Parcial (TP1):** Assim que o preço sobe e bate no alvo do Take Profit 1 (ex: +1.0%), o robô vende uma fração da posição (ex: 60% dos contratos) garantindo o lucro inicial no bolso.
3. **Breakeven (Risco Zero):** Imediatamente após a parcial, o Stop Loss da quantidade restante é movido para o **preço de entrada**. Se o mercado despencar de volta, você sai no zero a zero na quantidade restante. **A operação torna-se impossível de gerar prejuízo.**
4. **Alvo Final (TP2):** O restante da posição (40%) continua rodando até bater no alvo final (ex: +3.0%) para maximizar os lucros da tendência.
5. **Travas Diárias:** Se no pior cenário o mercado estiver muito ruim e o robô bater o limite máximo de perda diária configurado (ex: -$15), ele se desliga automaticamente pelo dia para proteger seu saldo.

---

## ⚙️ Instalação e Configuração

### 1. Pré-requisitos
Certifique-se de ter o Python 3.8+ instalado em sua máquina.

### 2. Instalar dependências
Abra o terminal na pasta do projeto e execute:
```bash
pip install -r requirements.txt
```

### 3. Configurar Chaves de API e Variáveis (.env)
Renomeie ou edite o arquivo oculto `.env` na raiz do projeto e insira suas credenciais:
* **`BINANCE_API_KEY`**: Sua chave de API da Binance.
* **`BINANCE_API_SECRET`**: Seu segredo de API da Binance.
* **`USE_TESTNET`**: Deixe como `True` para operar de forma 100% simulada sem risco. Mude para `False` apenas após ver o robô funcionando com perfeição.

#### *Opcional: Alertas no Telegram*
Para receber notificações de cada ação do robô no seu celular:
1. Inicie uma conversa com o `@BotFather` no Telegram e crie um novo bot para obter o token (`TELEGRAM_BOT_TOKEN`).
2. Fale com o `@userinfobot` para descobrir o seu chat ID numérico (`TELEGRAM_CHAT_ID`).
3. Preencha estes dois dados no arquivo `.env`.

### 4. Ajustar Estratégia e Limites (config.py)
No arquivo `config.py`, você pode personalizar:
* O ativo a ser operado (`SYMBOL`). Ex: `'BTC/USDT'`.
* O valor de USDT investido por entrada (`TRADE_AMOUNT_USDT`).
* As porcentagens de stop, alvos e frações de parciais.
* Os limites diários de segurança de perda e ganho.

---

## 🚀 Execução

Para iniciar o robô, execute o comando abaixo no seu terminal:
```bash
python bot.py
```

> [!WARNING]
> **AVISO DE SEGURANÇA:**
> Sempre mantenha `USE_TESTNET=True` nos primeiros dias de teste. Verifique se o robô está abrindo ordens na Testnet da Binance de forma correta e simulada antes de sequer cogitar mudar para dinheiro real.
