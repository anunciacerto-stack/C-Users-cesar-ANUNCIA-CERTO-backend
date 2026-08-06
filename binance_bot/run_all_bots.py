"""
╔══════════════════════════════════════════════════════════════════════════╗
║  LAUNCHER PRINCIPAL — Inicia o MOMENTUM SURFER PRO v4.0                 ║
║                                                                          ║
║  COMO USAR:                                                              ║
║    python run_all_bots.py                                                ║
║                                                                          ║
║  Este script inicia o sistema unificado que gerencia os 3 ativos         ║
║  (SOL/USDT, BTC/USDT, ETH/USDT) em paralelo com um único processo.     ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import subprocess
import sys
import os

def main():
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
            sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        except Exception:
            pass

    print("=" * 72)
    print("  💎 LAUNCHER — MOMENTUM SURFER PRO v4.0")
    print("=" * 72)
    
    # Verifica dependências
    missing = []
    for pkg in ['ccxt', 'pandas', 'numpy', 'requests', 'dotenv']:
        try:
            __import__(pkg if pkg != 'dotenv' else 'dotenv')
        except ImportError:
            missing.append(pkg if pkg != 'dotenv' else 'python-dotenv')
    
    if missing:
        print(f"[SETUP] Instalando dependências faltantes: {missing}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
        print("[SETUP] Instalação concluída!")
    
    # Inicia o sistema
    script_dir = os.path.dirname(os.path.abspath(__file__))
    bot_path = os.path.join(script_dir, 'momentum_surfer.py')
    
    print(f"[LAUNCHER] Iniciando: {bot_path}")
    print("=" * 72)
    
    # Executa o bot principal
    os.execv(sys.executable, [sys.executable, bot_path])


if __name__ == '__main__':
    main()
