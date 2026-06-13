# -*- coding: utf-8 -*-
import sys
import os

# Define o path para garantir importações corretas
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest_real_exchange_compound import main as run_simulation

if __name__ == '__main__':
    run_simulation()
