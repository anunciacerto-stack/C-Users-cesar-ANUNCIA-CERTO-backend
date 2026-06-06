import subprocess
import sys
import time
import os
import threading

# Garante que a saída padrão no console Windows suporte UTF-8 e trate caracteres especiais/emojis sem quebrar
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

def read_logs(proc, script_name):
    # Lê os logs do processo em tempo real em uma thread separada
    try:
        for line in iter(proc.stdout.readline, ''):
            line_str = line.strip()
            if line_str:
                print(f"[{script_name.upper()}] {line_str}")
    except Exception as e:
        print(f"[MASTER - ERRO] Falha ao ler logs de {script_name}: {e}")

def run_script(script_name):
    print(f"[MASTER] Inicializando {script_name}...")
    process = subprocess.Popen(
        [sys.executable, "-u", script_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='replace'
    )
    # Inicia a thread para ler os logs do processo
    t = threading.Thread(target=read_logs, args=(process, script_name), daemon=True)
    t.start()
    return process

def main():
    scripts = ["bot.py", "bot_b.py", "bot_a.py"]
    processes = {}
    
    # Inicia todos os scripts
    for script in scripts:
        if os.path.exists(script):
            processes[script] = run_script(script)
            time.sleep(2)  # Delay para evitar colisões de logs na inicialização
        else:
            print(f"[MASTER - ERRO] Arquivo {script} não encontrado!")

    print("[MASTER] Todos os robôs foram inicializados e estão rodando em segundo plano.")
    print("[MASTER] Monitorando logs (Ctrl+C para encerrar todos os robôs):\n")

    # Monitoramento de status dos processos
    try:
        while True:
            for name, proc in list(processes.items()):
                poll = proc.poll()
                if poll is not None:
                    print(f"\n[MASTER - CRÍTICO] O {name} parou de rodar com código de saída {poll}!")
                    print(f"[MASTER] Reiniciando {name} em 5 segundos...")
                    time.sleep(5)
                    processes[name] = run_script(name)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[MASTER] Ctrl+C detectado! Encerrando todos os robôs com segurança...")
        for name, proc in processes.items():
            print(f"[MASTER] Finalizando {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("[MASTER] Todos os robôs foram desligados com sucesso.")

if __name__ == "__main__":
    main()
