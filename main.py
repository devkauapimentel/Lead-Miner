"""
main.py — Ponto de Entrada do Lead Miner v2.0.0-beta
=====================================================
Uso:
    python main.py            → Abre a GUI (interface visual)
    python main.py --cli      → Abre o menu interativo no terminal
    python main.py --help     → Mostra ajuda
"""

import sys
import os

# Garantir que o diretório do projeto está no path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def show_help():
    """Exibe ajuda de uso."""
    print("""
  ⛏️  Lead Miner v2.0.0-beta
  ─────────────────────────────

  Uso:
    python main.py            Abre a interface visual (GUI)
    python main.py --cli      Abre o menu interativo no terminal
    python main.py --help     Mostra esta ajuda

  Exemplos:
    venv/bin/python main.py --cli
    venv/bin/python main.py
""")


def main():
    """
    Ponto de entrada principal.
    Abre EXCLUSIVAMENTE o modo escolhido — nunca ambos.
    """
    # Parse de argumentos
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        show_help()
        return

    use_cli = "--cli" in args or "-c" in args

    if use_cli:
        # ======================
        # MODO CLI (Terminal)
        # ======================
        from infra.logger import setup_logger
        setup_logger()
        from ui.cli import run_cli
        run_cli()
    else:
        # ======================
        # MODO GUI (Visual)
        # ======================
        try:
            from infra.logger import setup_logger
            setup_logger()
            from ui.gui import run_gui
            run_gui()
        except ImportError as e:
            print(f"""
  ❌ Não foi possível abrir a interface visual.
  
  Motivo: {e}

  Soluções:
    1. Instale o tkinter:  sudo apt install python3-tk
    2. Recrie o venv:      rm -rf venv && python3 -m venv venv
    3. Instale deps:       venv/bin/pip install -r requirements.txt

  Ou use o modo terminal:
    venv/bin/python main.py --cli
""")
            sys.exit(1)
        except Exception as e:
            print(f"""
  ❌ Erro inesperado ao abrir a GUI: {e}

  Use o modo terminal:
    venv/bin/python main.py --cli
""")
            sys.exit(1)


if __name__ == "__main__":
    main()
