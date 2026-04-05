"""
ui/cli.py — Interface de Linha de Comando (Terminal Premium)
=============================================================
Menu interativo estilizado com cores, banners e feedback visual.
Usa questionary para checkboxes e prompts interativos.
"""

import os
import sys
import time
import logging

try:
    import questionary
    from questionary import Style
except ImportError:
    questionary = None

# Adicionar raiz ao path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.config_manager import ConfigManager, KNOWN_LABELS

log = logging.getLogger("pegador")

# =====================================================================
# CORES ANSI PARA OUTPUT BONITO
# =====================================================================

class C:
    """Cores ANSI para terminal."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"
    BG_DARK = "\033[48;5;234m"

# Estilo do questionary (combinando com nossas cores)
CLI_STYLE = Style([
    ('qmark', 'fg:#e94560 bold'),
    ('question', 'fg:#ffffff bold'),
    ('answer', 'fg:#53e683 bold'),
    ('pointer', 'fg:#e94560 bold'),
    ('highlighted', 'fg:#e94560 bold'),
    ('selected', 'fg:#53e683'),
    ('separator', 'fg:#6c6c6c'),
    ('instruction', 'fg:#6c6c6c'),
]) if questionary else None


# =====================================================================
# COMPONENTES VISUAIS
# =====================================================================

def clear_screen():
    """Limpa o terminal."""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_banner():
    """Banner estilizado."""
    clear_screen()
    print(f"""
{C.CYAN}{C.BOLD}  ╔══════════════════════════════════════════════╗
  ║                                              ║
  ║   ⚡  PEGADOR DE CONTATO  v2.0               ║
  ║   ─────────────────────────────              ║
  ║   Extrator de Leads do WhatsApp Business     ║
  ║                                              ║
  ╚══════════════════════════════════════════════╝{C.RESET}
""")


def print_divider(title: str = ""):
    """Linha divisória com título opcional."""
    if title:
        print(f"\n  {C.CYAN}{'─' * 3} {C.BOLD}{title} {C.RESET}{C.CYAN}{'─' * (40 - len(title))}{C.RESET}")
    else:
        print(f"  {C.GRAY}{'─' * 50}{C.RESET}")


def print_success(msg: str):
    print(f"  {C.GREEN}✅ {msg}{C.RESET}")


def print_error(msg: str):
    print(f"  {C.RED}❌ {msg}{C.RESET}")


def print_warning(msg: str):
    print(f"  {C.YELLOW}⚠️  {msg}{C.RESET}")


def print_info(msg: str):
    print(f"  {C.BLUE}ℹ  {msg}{C.RESET}")


def print_label(label: str, value: str):
    """Exibe um par label: valor alinhado."""
    print(f"  {C.GRAY}{label:.<20s}{C.RESET} {C.WHITE}{value}{C.RESET}")


def print_tag_list(title: str, tags: list, color: str):
    """Exibe uma lista de tags com cor."""
    if tags:
        tags_str = f"{C.RESET}{C.GRAY}, {color}".join(tags)
        print(f"  {C.GRAY}{title:.<20s}{C.RESET} {color}{tags_str}{C.RESET}")
    else:
        print(f"  {C.GRAY}{title:.<20s}{C.RESET} {C.DIM}(nenhuma){C.RESET}")


def confirm_action(msg: str) -> bool:
    """Confirmação com estilo."""
    if questionary:
        return questionary.confirm(msg, default=True, style=CLI_STYLE).ask()
    resp = input(f"  {C.YELLOW}? {msg} (S/n): {C.RESET}").strip().lower()
    return resp in ('', 's', 'sim', 'y', 'yes')


def press_enter():
    """Pausa aguardando Enter."""
    input(f"\n  {C.DIM}Pressione Enter para continuar...{C.RESET}")


# =====================================================================
# TELAS
# =====================================================================

def show_config_summary(config: dict):
    """Exibe resumo da configuração atual de forma visual."""
    print_divider("CONFIGURAÇÃO ATUAL")
    print()
    print_label("Negócio", config.get("business_name", "Não definido"))
    print_label("Número", config.get("own_number", "Não definido") or f"{C.RED}⚠ Não configurado")
    print_label("Modo filtro", config.get("filter_mode", "labels").upper())
    print()

    labels = config.get("labels", {})
    print_tag_list("Incluir (leads)", labels.get("include", []), C.GREEN)
    print_tag_list("Excluir (bloq.)", labels.get("exclude", []), C.RED)
    print()

    blacklist = config.get("blacklist_names", [])
    if blacklist:
        print_tag_list("Lista negra", blacklist, C.YELLOW)
    print()


def show_main_menu() -> str:
    """Menu principal com visual premium."""
    print_divider("MENU PRINCIPAL")
    print()

    if not questionary:
        print(f"  {C.GREEN}1{C.RESET} 🚀 Iniciar Extração")
        print(f"  {C.CYAN}2{C.RESET} 📌 Configurar Etiquetas")
        print(f"  {C.CYAN}3{C.RESET} 📋 Dados do Negócio")
        print(f"  {C.CYAN}4{C.RESET} 📦 Carregar Preset")
        print(f"  {C.YELLOW}5{C.RESET} 🗑️  Limpar Progresso")
        print(f"  {C.RED}0{C.RESET} ❌ Sair")
        print()
        choice = input(f"  {C.BOLD}Escolha uma opção: {C.RESET}").strip()
        mapping = {
            "1": "start", "2": "labels", "3": "business",
            "4": "preset", "5": "clear", "0": "exit",
        }
        return mapping.get(choice, "")

    choices = [
        questionary.Choice("🚀 Iniciar Extração", value="start"),
        questionary.Separator("─── Configuração ───"),
        questionary.Choice("📌 Configurar Etiquetas", value="labels"),
        questionary.Choice("📋 Dados do Negócio", value="business"),
        questionary.Choice("📦 Carregar Preset", value="preset"),
        questionary.Separator(),
        questionary.Choice("🗑️  Limpar Progresso", value="clear"),
        questionary.Choice("❌ Sair", value="exit"),
    ]

    result = questionary.select(
        "O que deseja fazer?",
        choices=choices,
        style=CLI_STYLE,
        instruction="(use ↑ ↓ para navegar, Enter para selecionar)",
    ).ask()

    return result or "exit"


# =====================================================================
# AÇÕES
# =====================================================================

def configure_labels(config: dict, cm: ConfigManager) -> dict:
    """Tela de configuração de etiquetas."""
    print_banner()
    print_divider("ETIQUETAS DE INCLUSÃO")
    print(f"  {C.DIM}Contatos com essas tags serão{C.RESET} {C.GREEN}EXTRAÍDOS{C.RESET}")
    print(f"  {C.DIM}Use ESPAÇO para marcar/desmarcar, ENTER para confirmar{C.RESET}")
    print()

    current_include = config.get("labels", {}).get("include", [])

    if questionary:
        include = questionary.checkbox(
            "Etiquetas para INCLUIR:",
            choices=[
                questionary.Choice(label, checked=(label in current_include))
                for label in KNOWN_LABELS
            ],
            style=CLI_STYLE,
            instruction="(espaço = marcar, enter = confirmar)",
        ).ask()
    else:
        include = _manual_checkbox("INCLUIR", KNOWN_LABELS, current_include)

    if include is None:
        return config

    print()
    print_divider("ETIQUETAS DE EXCLUSÃO")
    print(f"  {C.DIM}Contatos com essas tags serão{C.RESET} {C.RED}BLOQUEADOS{C.RESET}")
    print()

    current_exclude = config.get("labels", {}).get("exclude", [])

    if questionary:
        exclude = questionary.checkbox(
            "Etiquetas para EXCLUIR:",
            choices=[
                questionary.Choice(label, checked=(label in current_exclude))
                for label in KNOWN_LABELS
            ],
            style=CLI_STYLE,
            instruction="(espaço = marcar, enter = confirmar)",
        ).ask()
    else:
        exclude = _manual_checkbox("EXCLUIR", KNOWN_LABELS, current_exclude)

    if exclude is None:
        return config

    # Escolher modo
    print()
    print_divider("MODO DE FILTRAGEM")

    if questionary:
        mode = questionary.select(
            "Como o bot deve filtrar?",
            choices=[
                questionary.Choice("📌 Etiquetas (Recomendado)", value="labels"),
                questionary.Choice("🔤 Palavras-chave (Legado)", value="keywords"),
                questionary.Choice("🔀 Híbrido (Labels + Keywords)", value="hybrid"),
            ],
            style=CLI_STYLE,
        ).ask()
    else:
        print(f"  {C.GREEN}1{C.RESET} 📌 Etiquetas (Recomendado)")
        print(f"  {C.CYAN}2{C.RESET} 🔤 Palavras-chave (Legado)")
        print(f"  {C.CYAN}3{C.RESET} 🔀 Híbrido")
        c = input(f"\n  {C.BOLD}Escolha: {C.RESET}").strip()
        mode = {"1": "labels", "2": "keywords", "3": "hybrid"}.get(c, "labels")

    config["labels"] = {"include": include, "exclude": exclude}
    if mode:
        config["filter_mode"] = mode

    cm.save(config)
    print()
    print_success("Etiquetas salvas com sucesso!")
    press_enter()
    return config


def configure_business(config: dict, cm: ConfigManager) -> dict:
    """Tela de configuração dos dados do negócio."""
    print_banner()
    print_divider("DADOS DO NEGÓCIO")
    print()

    if questionary:
        name = questionary.text(
            "Nome do negócio:",
            default=config.get("business_name", ""),
            style=CLI_STYLE,
        ).ask()

        number = questionary.text(
            "Seu número WhatsApp (ex: 5521994538190):",
            default=config.get("own_number", ""),
            style=CLI_STYLE,
        ).ask()

        blacklist = questionary.text(
            "Nomes para ignorar (separados por vírgula):",
            default=", ".join(config.get("blacklist_names", [])),
            style=CLI_STYLE,
        ).ask()
    else:
        name = input(f"  Nome do negócio [{config.get('business_name', '')}]: ").strip()
        number = input(f"  Seu número [{config.get('own_number', '')}]: ").strip()
        blacklist = input(f"  Lista negra [{', '.join(config.get('blacklist_names', []))}]: ").strip()

    if name:
        config["business_name"] = name
    if number:
        config["own_number"] = number
    if blacklist is not None:
        config["blacklist_names"] = [
            n.strip() for n in blacklist.split(",") if n.strip()
        ]

    cm.save(config)
    print()
    print_success("Dados salvos!")
    press_enter()
    return config


def load_preset(config: dict, cm: ConfigManager) -> dict:
    """Tela de carregamento de preset."""
    print_banner()
    print_divider("PRESETS DE NEGÓCIO")
    print(f"  {C.DIM}Configurações prontas por tipo de negócio{C.RESET}")
    print()

    presets = cm.list_presets()
    if not presets:
        print_error("Nenhum preset encontrado em presets/")
        press_enter()
        return config

    if questionary:
        choice = questionary.select(
            "Selecione o tipo de negócio:",
            choices=[
                questionary.Choice(p.replace("_", " ").title(), value=p)
                for p in presets
            ],
            style=CLI_STYLE,
        ).ask()
    else:
        for i, p in enumerate(presets, 1):
            print(f"  {C.CYAN}{i}{C.RESET} {p.replace('_', ' ').title()}")
        c = input(f"\n  {C.BOLD}Escolha: {C.RESET}").strip()
        try:
            choice = presets[int(c) - 1]
        except (ValueError, IndexError):
            print_error("Opção inválida")
            press_enter()
            return config

    if choice:
        try:
            preset = cm.load_preset(choice)
            cm.save(preset)
            print()
            print_success(f"Preset '{choice.replace('_', ' ').title()}' carregado!")
            press_enter()
            return preset
        except FileNotFoundError as e:
            print_error(str(e))
            press_enter()

    return config


def start_extraction(config: dict, cm: ConfigManager):
    """Inicia a extração com feedback visual."""
    print_banner()
    print_divider("PRÉ-VÔOO")
    print()

    # Validar
    errors = cm.validate(config)
    if errors:
        print_warning("Problemas encontrados:")
        for err in errors:
            print(f"  {C.RED}  • {err}{C.RESET}")
        print()
        if not confirm_action("Continuar mesmo assim?"):
            return
    else:
        print_success("Configuração válida")

    print()
    show_config_summary(config)

    if not confirm_action("Iniciar extração agora?"):
        return

    print()
    print(f"  {C.CYAN}{'═' * 50}{C.RESET}")
    print(f"  {C.BOLD}{C.GREEN}  🚀 EXTRAINDO LEADS...{C.RESET}")
    print(f"  {C.DIM}  Pressione Ctrl+C para interromper com segurança{C.RESET}")
    print(f"  {C.CYAN}{'═' * 50}{C.RESET}")
    print()

    try:
        from core.facade import PegadorDeContato
        pegador = PegadorDeContato()
        pegador.start()
    except KeyboardInterrupt:
        print(f"\n  {C.YELLOW}⏹ Interrompido pelo usuário. Progresso salvo.{C.RESET}")
    except Exception as e:
        print_error(f"Erro: {e}")
    finally:
        if 'pegador' in dir() and pegador:
            pegador.cleanup()

    press_enter()


def clear_progress():
    """Limpa dados de progresso."""
    from infra.exporters import CSVExporter
    exporter = CSVExporter()

    if confirm_action("Apagar todo o progresso e leads salvos?"):
        exporter.limpar_dados()
        print()
        print_success("Progresso limpo! Pronto para nova extração.")
    else:
        print_info("Cancelado.")

    press_enter()


def _manual_checkbox(title: str, options: list, current: list) -> list:
    """Fallback para checkbox sem questionary."""
    print(f"\n  {C.DIM}Tags disponíveis para {title}:{C.RESET}")
    for i, opt in enumerate(options, 1):
        mark = f"{C.GREEN}x{C.RESET}" if opt in current else " "
        print(f"  [{mark}] {C.CYAN}{i:2d}{C.RESET} {opt}")
    print()
    nums = input(f"  {C.BOLD}Números para selecionar (ex: 1,3,7): {C.RESET}").strip()
    if not nums:
        return current
    try:
        indices = [int(n.strip()) - 1 for n in nums.split(",")]
        return [options[i] for i in indices if 0 <= i < len(options)]
    except (ValueError, IndexError):
        return current


# =====================================================================
# LOOP PRINCIPAL
# =====================================================================

def run_cli():
    """Executa o menu principal do CLI."""
    if questionary is None:
        print(f"\n  {C.YELLOW}⚠ questionary não instalado — usando modo manual{C.RESET}")
        print(f"  {C.DIM}Para menus interativos: venv/bin/pip install questionary{C.RESET}\n")

    config_manager = ConfigManager()
    config = config_manager.load()

    while True:
        print_banner()
        show_config_summary(config)
        action = show_main_menu()

        if action == "exit":
            print(f"\n  {C.CYAN}👋 Até a próxima!{C.RESET}\n")
            break
        elif action == "start":
            start_extraction(config, config_manager)
        elif action == "labels":
            config = configure_labels(config, config_manager)
        elif action == "business":
            config = configure_business(config, config_manager)
        elif action == "preset":
            config = load_preset(config, config_manager)
        elif action == "clear":
            clear_progress()
        else:
            print_error("Opção inválida")
            press_enter()


if __name__ == "__main__":
    run_cli()
