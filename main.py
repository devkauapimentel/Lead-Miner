"""
main.py — Ponto de Entrada do Pegador de Contato v2.0
======================================================
python main.py        → Abre a GUI (padrão)
python main.py --cli  → Abre o menu interativo no terminal
"""

import sys
import os

# Garantir que o diretório do projeto está no path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from infra.logger import setup_logger


def main():
    """
    Ponto de entrada principal.
    Decide se abre a GUI ou o CLI com base nos argumentos.
    """
    setup_logger()

    # Verificar argumentos
    use_cli = "--cli" in sys.argv or "-c" in sys.argv

    if use_cli:
        # Modo terminal interativo
        from ui.cli import run_cli
        run_cli()
    else:
        # Modo GUI (padrão)
        try:
            from ui.gui import run_gui
            run_gui()
        except ImportError as e:
            print(f"⚠️ Não foi possível abrir a GUI: {e}")
            print("   Instalando customtkinter...")
            os.system(f"{sys.executable} -m pip install customtkinter")
            print("\n   Tente novamente: python main.py")
            print("   Ou use o modo terminal: python main.py --cli")
            sys.exit(1)
        except Exception as e:
            # Fallback para CLI se GUI falhar (ex: sem display)
            print(f"⚠️ GUI falhou: {e}")
            print("   Iniciando modo terminal...")
            from ui.cli import run_cli
            run_cli()


if __name__ == "__main__":
    main()
