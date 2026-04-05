"""
ui/cli.py — Interface de Linha de Comando Interativa
=====================================================
Menu interativo no terminal usando questionary.
Alternativa à GUI para terminais sem suporte gráfico
ou para usuários que preferem terminal.
"""

import os
import sys
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
from core.facade import PegadorDeContato

log = logging.getLogger("pegador")

# Estilo visual do CLI
CLI_STYLE = Style([
    ('qmark', 'fg:#e94560 bold'),
    ('question', 'fg:#ffffff bold'),
    ('answer', 'fg:#53e683 bold'),
    ('pointer', 'fg:#e94560 bold'),
    ('highlighted', 'fg:#e94560 bold'),
    ('selected', 'fg:#53e683'),
    ('separator', 'fg:#6c6c6c'),
    ('instruction', 'fg:#6c6c6c'),
])


def print_header():
    """Exibe o header estilizado."""
    print("\n" + "=" * 55)
    print("  ⚡ PEGADOR DE CONTATO v2.0")
    print("  Extrator de Leads do WhatsApp Business")
    print("=" * 55 + "\n")


def print_config_summary(config: dict):
    """Exibe resumo da configuração atual."""
    print("\n📋 Configuração Atual:")
    print(f"   Negócio: {config.get('business_name', '?')}")
    print(f"   Número:  {config.get('own_number', '?')}")
    print(f"   Modo:    {config.get('filter_mode', 'labels')}")

    labels = config.get("labels", {})
    inc = labels.get("include", [])
    exc = labels.get("exclude", [])
    print(f"   Include: {', '.join(inc) if inc else '(nenhuma)'}")
    print(f"   Exclude: {', '.join(exc) if exc else '(nenhuma)'}")
    print()


def run_cli():
    """
    Executa o menu interativo no terminal.

    Fluxo:
        1. Exibe configuração atual
        2. Permite configurar tags, número, etc.
        3. Confirma e inicia extração
    """
    if questionary is None:
        print("❌ questionary não instalado.")
        print("   Rode: pip install questionary")
        print("   Ou use a GUI: python main.py")
        sys.exit(1)

    print_header()

    config_manager = ConfigManager()
    config = config_manager.load()

    while True:
        print_config_summary(config)

        action = questionary.select(
            "O que deseja fazer?",
            choices=[
                "🚀 Iniciar Extração",
                "⚙️  Configurar Etiquetas",
                "📋 Configurar Dados do Negócio",
                "📦 Carregar Preset",
                "🗑️  Limpar Progresso",
                "❌ Sair",
            ],
            style=CLI_STYLE,
        ).ask()

        if action is None or "Sair" in action:
            print("\n👋 Até a próxima!\n")
            break

        elif "Iniciar" in action:
            _start_extraction(config, config_manager)

        elif "Etiquetas" in action:
            config = _configure_labels(config, config_manager)

        elif "Dados" in action:
            config = _configure_business(config, config_manager)

        elif "Preset" in action:
            config = _load_preset(config, config_manager)

        elif "Limpar" in action:
            _clear_progress()


def _configure_labels(config: dict, cm: ConfigManager) -> dict:
    """Menu para selecionar etiquetas de inclusão/exclusão."""
    print("\n📌 Selecione as etiquetas para INCLUIR (Remarketing):")
    print("   Use ESPAÇO para marcar, ENTER para confirmar\n")

    current_include = config.get("labels", {}).get("include", [])
    include_choices = questionary.checkbox(
        "Etiquetas de INCLUSÃO:",
        choices=[
            questionary.Choice(label, checked=(label in current_include))
            for label in KNOWN_LABELS
        ],
        style=CLI_STYLE,
    ).ask()

    if include_choices is None:
        return config

    print()
    current_exclude = config.get("labels", {}).get("exclude", [])
    exclude_choices = questionary.checkbox(
        "Etiquetas de EXCLUSÃO (Bloquear):",
        choices=[
            questionary.Choice(label, checked=(label in current_exclude))
            for label in KNOWN_LABELS
        ],
        style=CLI_STYLE,
    ).ask()

    if exclude_choices is None:
        return config

    config["labels"] = {
        "include": include_choices,
        "exclude": exclude_choices,
    }

    # Escolher modo de filtro
    mode = questionary.select(
        "Modo de filtragem:",
        choices=[
            questionary.Choice("📌 Etiquetas (Recomendado)", value="labels"),
            questionary.Choice("🔤 Palavras-chave (Legado)", value="keywords"),
            questionary.Choice("🔀 Híbrido (Labels + Keywords)", value="hybrid"),
        ],
        style=CLI_STYLE,
    ).ask()

    if mode:
        config["filter_mode"] = mode

    cm.save(config)
    print("\n✅ Etiquetas salvas!\n")
    return config


def _configure_business(config: dict, cm: ConfigManager) -> dict:
    """Menu para configurar dados do negócio."""
    name = questionary.text(
        "Nome do negócio:",
        default=config.get("business_name", ""),
        style=CLI_STYLE,
    ).ask()

    if name:
        config["business_name"] = name

    number = questionary.text(
        "Seu número (ex: 5521994538190):",
        default=config.get("own_number", ""),
        style=CLI_STYLE,
    ).ask()

    if number:
        config["own_number"] = number

    blacklist = questionary.text(
        "Nomes para ignorar (separados por vírgula):",
        default=", ".join(config.get("blacklist_names", [])),
        style=CLI_STYLE,
    ).ask()

    if blacklist is not None:
        config["blacklist_names"] = [
            n.strip() for n in blacklist.split(",") if n.strip()
        ]

    cm.save(config)
    print("\n✅ Configuração salva!\n")
    return config


def _load_preset(config: dict, cm: ConfigManager) -> dict:
    """Carrega um preset selecionado."""
    presets = cm.list_presets()
    if not presets:
        print("\n❌ Nenhum preset encontrado em presets/\n")
        return config

    choice = questionary.select(
        "Selecione o preset:",
        choices=presets,
        style=CLI_STYLE,
    ).ask()

    if choice:
        try:
            preset = cm.load_preset(choice)
            cm.save(preset)
            print(f"\n✅ Preset '{choice}' carregado e salvo!\n")
            return preset
        except FileNotFoundError as e:
            print(f"\n❌ {e}\n")

    return config


def _start_extraction(config: dict, cm: ConfigManager):
    """Inicia a extração de leads."""
    # Validar
    errors = cm.validate(config)
    if errors:
        print("\n⚠️ Erros na configuração:")
        for e in errors:
            print(f"   ❌ {e}")
        print()
        return

    confirm = questionary.confirm(
        "Iniciar extração agora?",
        default=True,
        style=CLI_STYLE,
    ).ask()

    if not confirm:
        return

    print("\n" + "=" * 55)
    print("  🚀 EXTRAINDO LEADS...")
    print("  Pressione Ctrl+C para interromper")
    print("=" * 55 + "\n")

    try:
        pegador = PegadorDeContato()
        pegador.start()
    except KeyboardInterrupt:
        print("\n⏹ Interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
    finally:
        if 'pegador' in dir() and pegador:
            pegador.cleanup()

    print()


def _clear_progress():
    """Limpa dados de progresso."""
    from infra.exporters import CSVExporter
    exporter = CSVExporter()
    exporter.limpar_dados()
    print("\n🗑️ Progresso limpo! Pronto para nova extração.\n")


if __name__ == "__main__":
    run_cli()
