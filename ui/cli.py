"""
ui/cli.py — Interface de Terminal (Lead Miner)
==============================================
Terminal interativo com design moderno, cores e UX pensada
para leigos: explicações claras em cada passo.
"""

import os
import sys
import time
import logging

try:
    import questionary
    from questionary import Style
    HAS_QUESTIONARY = True
except ImportError:
    HAS_QUESTIONARY = False

# Adicionar raiz ao path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.config_manager import ConfigManager, KNOWN_LABELS

log = logging.getLogger("lead_miner")


# ═════════════════════════════════════════════════════════════════════
# CORES ANSI
# ═════════════════════════════════════════════════════════════════════

class C:
    R   = "\033[0m"       # Reset
    B   = "\033[1m"       # Bold
    D   = "\033[2m"       # Dim
    RED = "\033[38;5;203m"
    GRN = "\033[38;5;114m"
    YLW = "\033[38;5;221m"
    BLU = "\033[38;5;111m"
    CYN = "\033[38;5;80m"
    MAG = "\033[38;5;176m"
    WHT = "\033[97m"
    GRY = "\033[38;5;244m"
    ORG = "\033[38;5;208m"

# Estilo questionary
Q_STYLE = Style([
    ('qmark', 'fg:#e94560 bold'),
    ('question', 'fg:#ffffff bold'),
    ('answer', 'fg:#7bed9f bold'),
    ('pointer', 'fg:#e94560 bold'),
    ('highlighted', 'fg:#e94560 bold'),
    ('selected', 'fg:#7bed9f'),
    ('separator', 'fg:#636e72'),
    ('instruction', 'fg:#636e72 italic'),
]) if HAS_QUESTIONARY else None


# ═════════════════════════════════════════════════════════════════════
# COMPONENTES VISUAIS
# ═════════════════════════════════════════════════════════════════════

def cls():
    os.system('clear' if os.name != 'nt' else 'cls')


def banner():
    cls()
    print(f"""
  {C.CYN}╔{'═' * 52}╗
  ║{C.R}                                                    {C.CYN}║
  ║{C.R}   {C.B}{C.WHT}⛏️  L E A D   M I N E R{C.R}                      {C.CYN}║
  ║{C.R}   {C.GRY}v2.0.0-beta — WhatsApp Lead Extractor{C.R}          {C.CYN}║
  ║{C.R}                                                    {C.CYN}║
  ╚{'═' * 52}╝{C.R}
""")


def line(text="", char="─", width=52):
    if text:
        pad = width - len(text) - 2
        left = pad // 2
        right = pad - left
        print(f"  {C.GRY}{char * left} {C.B}{C.WHT}{text} {C.GRY}{char * right}{C.R}")
    else:
        print(f"  {C.GRY}{char * width}{C.R}")


def ok(msg):
    print(f"  {C.GRN}✓{C.R} {msg}")


def err(msg):
    print(f"  {C.RED}✗{C.R} {msg}")


def warn(msg):
    print(f"  {C.YLW}!{C.R} {msg}")


def info(msg):
    print(f"  {C.BLU}›{C.R} {msg}")


def hint(msg):
    print(f"  {C.D}{msg}{C.R}")


def field(label, value, label_color=C.GRY, value_color=C.WHT):
    dots = "." * max(1, 22 - len(label))
    print(f"  {label_color}{label}{C.R}{C.GRY}{dots}{C.R} {value_color}{value}{C.R}")


def tag_chips(tags, color):
    """Mostra tags como chips visuais inline."""
    if not tags:
        print(f"  {C.D}  (nenhuma selecionada){C.R}")
        return
    line_str = "  "
    for t in tags:
        line_str += f" {color}[{C.B}{t}{C.R}{color}]{C.R}"
    print(line_str)


def wait_enter():
    input(f"\n  {C.D}↵ Pressione Enter...{C.R}")


def ask_yes(msg):
    if HAS_QUESTIONARY:
        return questionary.confirm(msg, default=True, style=Q_STYLE).ask()
    r = input(f"  {C.YLW}?{C.R} {msg} {C.D}(S/n){C.R} ").strip().lower()
    return r in ('', 's', 'sim', 'y', 'yes')


# ═════════════════════════════════════════════════════════════════════
# RESUMO DA CONFIGURAÇÃO
# ═════════════════════════════════════════════════════════════════════

def show_resume(config):
    """Mostra um resumo visual da configuração ativa."""
    line("SEU PERFIL")
    print()
    field("Negócio", config.get("business_name") or f"{C.RED}Não definido")
    num = config.get("own_number")
    field("Número", num if num else f"{C.RED}⚠ Configure seu número!")
    field("Modo", config.get("filter_mode", "labels").upper())
    print()

    inc = config.get("labels", {}).get("include", [])
    exc = config.get("labels", {}).get("exclude", [])

    print(f"  {C.GRN}{C.B}INCLUIR{C.R} {C.D}(contatos com essas tags viram leads):{C.R}")
    tag_chips(inc, C.GRN)
    print()
    print(f"  {C.RED}{C.B}EXCLUIR{C.R} {C.D}(contatos com essas tags são bloqueados):{C.R}")
    tag_chips(exc, C.RED)
    print()


# ═════════════════════════════════════════════════════════════════════
# MENU PRINCIPAL
# ═════════════════════════════════════════════════════════════════════

def main_menu():
    line("O QUE DESEJA FAZER?")
    print()

    if HAS_QUESTIONARY:
        return questionary.select(
            "",
            choices=[
                questionary.Choice(
                    f"{'🚀 Iniciar Extração':.<40s} Começa a pegar os leads agora",
                    value="start"),
                questionary.Separator(f"  {'─' * 48}"),
                questionary.Choice(
                    f"{'📌 Configurar Etiquetas':.<40s} Define quais tags incluir/excluir",
                    value="labels"),
                questionary.Choice(
                    f"{'📋 Dados do Negócio':.<40s} Nome, número, lista negra",
                    value="business"),
                questionary.Choice(
                    f"{'📦 Carregar Preset':.<40s} Config pronta por tipo de negócio",
                    value="preset"),
                questionary.Separator(f"  {'─' * 48}"),
                questionary.Choice(
                    f"{'🗑️  Limpar Progresso':.<40s} Apaga leads e recomeça do zero",
                    value="clear"),
                questionary.Choice(
                    f"{'❌ Sair':.<40s}",
                    value="exit"),
            ],
            style=Q_STYLE,
            instruction="  ↑↓ navegar  ·  Enter selecionar",
        ).ask()
    else:
        opts = [
            ("1", "🚀", "Iniciar Extração", "Começa a pegar os leads"),
            ("2", "📌", "Configurar Etiquetas", "Tags de inclusão/exclusão"),
            ("3", "📋", "Dados do Negócio", "Nome, número, lista negra"),
            ("4", "📦", "Carregar Preset", "Config pronta por segmento"),
            ("5", "🗑️ ", "Limpar Progresso", "Apaga e recomeça do zero"),
            ("0", "❌", "Sair", ""),
        ]
        for num, icon, name, desc in opts:
            desc_str = f" {C.D}— {desc}{C.R}" if desc else ""
            print(f"   {C.CYN}{C.B}{num}{C.R}  {icon}  {name}{desc_str}")
        print()
        c = input(f"  {C.B}›{C.R} ").strip()
        return {"1": "start", "2": "labels", "3": "business",
                "4": "preset", "5": "clear", "0": "exit"}.get(c, "")


# ═════════════════════════════════════════════════════════════════════
# CONFIGURAR ETIQUETAS
# ═════════════════════════════════════════════════════════════════════

def configure_labels(config, cm):
    banner()

    # ── Passo 1: INCLUSÃO ──
    line("PASSO 1 DE 2 — ETIQUETAS DE INCLUSÃO", "═")
    print()
    print(f"  {C.GRN}{C.B}Quais etiquetas identificam um LEAD?{C.R}")
    print(f"  {C.D}Contatos com essas tags serão extraídos para o CSV.{C.R}")
    print(f"  {C.D}Ex: Se você marcar \"Lead Anuncio\", todo contato que{C.R}")
    print(f"  {C.D}tiver essa etiqueta no WhatsApp será puxado.{C.R}")
    print()

    current_inc = config.get("labels", {}).get("include", [])

    if HAS_QUESTIONARY:
        print(f"  {C.D}  ESPAÇO = marcar/desmarcar  ·  ENTER = confirmar{C.R}\n")
        include = questionary.checkbox(
            "Marque as etiquetas de INCLUSÃO:",
            choices=[
                questionary.Choice(
                    f"{label}  {C.D}{'← selecionada' if label in current_inc else ''}{C.R}",
                    value=label,
                    checked=(label in current_inc),
                )
                for label in KNOWN_LABELS
            ],
            style=Q_STYLE,
            instruction="",
        ).ask()
    else:
        include = _fallback_checkbox("INCLUIR", KNOWN_LABELS, current_inc, C.GRN)

    if include is None:
        return config

    # ── Passo 2: EXCLUSÃO ──
    banner()
    line("PASSO 2 DE 2 — ETIQUETAS DE EXCLUSÃO", "═")
    print()
    print(f"  {C.RED}{C.B}Quais etiquetas devem BLOQUEAR um contato?{C.R}")
    print(f"  {C.D}Se um contato tiver uma dessas tags, ele NÃO será{C.R}")
    print(f"  {C.D}extraído — mesmo que tambem tenha tag de inclusão.{C.R}")
    print(f"  {C.D}Ex: \"Agendada\" bloqueia um lead que já virou cliente.{C.R}")
    print()

    current_exc = config.get("labels", {}).get("exclude", [])

    if HAS_QUESTIONARY:
        print(f"  {C.D}  ESPAÇO = marcar/desmarcar  ·  ENTER = confirmar{C.R}\n")
        exclude = questionary.checkbox(
            "Marque as etiquetas de EXCLUSÃO:",
            choices=[
                questionary.Choice(
                    f"{label}  {C.D}{'← selecionada' if label in current_exc else ''}{C.R}",
                    value=label,
                    checked=(label in current_exc),
                )
                for label in KNOWN_LABELS
            ],
            style=Q_STYLE,
            instruction="",
        ).ask()
    else:
        exclude = _fallback_checkbox("EXCLUIR", KNOWN_LABELS, current_exc, C.RED)

    if exclude is None:
        return config

    # ── Confirmação visual ──
    banner()
    line("CONFIRME SUA CONFIGURAÇÃO")
    print()
    print(f"  {C.GRN}{C.B}INCLUIR:{C.R}")
    tag_chips(include, C.GRN)
    print()
    print(f"  {C.RED}{C.B}EXCLUIR:{C.R}")
    tag_chips(exclude, C.RED)
    print()

    # Mostrar exemplo prático
    line("EXEMPLO DE COMO FUNCIONA")
    print()
    if include and exclude:
        print(f"  {C.D}Contato com tag [{C.GRN}{include[0]}{C.D}]")
        print(f"  → {C.GRN}✓ Será extraído como lead{C.R}")
        print()
        print(f"  {C.D}Contato com tag [{C.GRN}{include[0]}{C.D}] + [{C.RED}{exclude[0]}{C.D}]")
        print(f"  → {C.RED}✗ Bloqueado! A exclusão sempre vence{C.R}")
    print()

    if ask_yes("Salvar essas configurações?"):
        config["labels"] = {"include": include, "exclude": exclude}
        cm.save(config)
        print()
        ok("Etiquetas salvas com sucesso!")
    else:
        warn("Cancelado — nada foi alterado")

    wait_enter()
    return config


def configure_business(config, cm):
    """Dados do negócio."""
    banner()
    line("DADOS DO NEGÓCIO")
    print()
    hint("Essas informações identificam sua conta no sistema.")
    print()

    if HAS_QUESTIONARY:
        name = questionary.text(
            "Nome do negócio:",
            default=config.get("business_name", ""),
            style=Q_STYLE,
            instruction="(ex: Clínica Dra. Rosângela)",
        ).ask()

        number = questionary.text(
            "Seu número WhatsApp:",
            default=config.get("own_number", ""),
            style=Q_STYLE,
            instruction="(formato: 5521994538190 — sem espaços ou traços)",
        ).ask()

        curr_bl = ", ".join(config.get("blacklist_names", []))
        blacklist = questionary.text(
            "Nomes para ignorar:",
            default=curr_bl,
            style=Q_STYLE,
            instruction="(separados por vírgula, ex: ana mkt, clinica teste)",
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
        config["blacklist_names"] = [n.strip() for n in blacklist.split(",") if n.strip()]

    cm.save(config)
    print()
    ok("Dados salvos!")
    wait_enter()
    return config


def load_preset(config, cm):
    """Carregar preset por tipo de negócio."""
    banner()
    line("PRESETS DE NEGÓCIO")
    print()
    hint("Presets são configurações prontas para cada tipo de negócio.")
    hint("Eles configuram as etiquetas de inclusão/exclusão automaticamente.")
    print()

    presets = cm.list_presets()
    if not presets:
        err("Nenhum preset encontrado na pasta presets/")
        wait_enter()
        return config

    friendly = {
        "clinica_estetica": "🏥 Clínica de Estética",
        "dentista": "🦷 Consultório Odontológico",
        "advogado": "⚖️  Escritório de Advocacia",
        "imobiliaria": "🏠 Imobiliária / Corretor",
    }

    if HAS_QUESTIONARY:
        choice = questionary.select(
            "Selecione o tipo de negócio:",
            choices=[
                questionary.Choice(friendly.get(p, p.replace("_", " ").title()), value=p)
                for p in presets
            ],
            style=Q_STYLE,
            instruction="  ↑↓ navegar  ·  Enter selecionar",
        ).ask()
    else:
        for i, p in enumerate(presets, 1):
            label = friendly.get(p, p.replace("_", " ").title())
            print(f"   {C.CYN}{C.B}{i}{C.R}  {label}")
        print()
        c = input(f"  {C.B}›{C.R} ").strip()
        try:
            choice = presets[int(c) - 1]
        except (ValueError, IndexError):
            err("Opção inválida")
            wait_enter()
            return config

    if choice:
        try:
            preset = cm.load_preset(choice)

            # Mostrar o que será configurado
            print()
            line(f"PRESET: {friendly.get(choice, choice).upper()}")
            print()
            inc = preset.get("labels", {}).get("include", [])
            exc = preset.get("labels", {}).get("exclude", [])
            print(f"  {C.GRN}{C.B}Incluir:{C.R}")
            tag_chips(inc, C.GRN)
            print(f"  {C.RED}{C.B}Excluir:{C.R}")
            tag_chips(exc, C.RED)
            print()

            if ask_yes("Aplicar essas configurações?"):
                cm.save(preset)
                ok(f"Preset aplicado!")
                wait_enter()
                return preset
        except FileNotFoundError as e:
            err(str(e))

    wait_enter()
    return config


def start_extraction(config, cm):
    """Iniciar a extração."""
    banner()
    line("PRÉ-VERIFICAÇÃO")
    print()

    # Validar
    errors = cm.validate(config)
    has_errors = bool(errors)

    if has_errors:
        warn("Problemas encontrados:")
        for e in errors:
            print(f"    {C.RED}• {e}{C.R}")
        print()
        if not ask_yes("Continuar mesmo assim?"):
            return
    else:
        ok("Configuração válida")

    # Resumo antes de iniciar
    print()
    show_resume(config)

    if not ask_yes("Iniciar extração agora?"):
        return

    # GO!
    banner()
    print(f"""
  {C.CYN}{'═' * 52}{C.R}

      {C.GRN}{C.B}🚀  EXTRAÇÃO EM ANDAMENTO...{C.R}

      {C.D}Os leads estão sendo capturados.
      O Chrome vai abrir automaticamente.

      Pressione {C.YLW}Ctrl+C{C.D} para parar com segurança.{C.R}

  {C.CYN}{'═' * 52}{C.R}
""")

    try:
        from core.facade import LeadMinerFacade
        miner = LeadMinerFacade()
        miner.start()
    except KeyboardInterrupt:
        print(f"\n  {C.YLW}⏹ Interrompido pelo usuário. Progresso salvo.{C.R}")
    except Exception as e:
        err(f"Erro: {e}")
    finally:
        if 'miner' in dir() and miner:
            miner.cleanup()

    wait_enter()


def clear_progress():
    """Limpar progresso."""
    if ask_yes("Apagar todo o progresso e leads salvos?"):
        from infra.exporters import CSVExporter
        CSVExporter().limpar_dados()
        print()
        ok("Progresso limpo! Pronto pra nova extração.")
    else:
        info("Cancelado.")
    wait_enter()


# ═════════════════════════════════════════════════════════════════════
# FALLBACK SEM QUESTIONARY
# ═════════════════════════════════════════════════════════════════════

def _fallback_checkbox(title, options, current, color):
    """Checkbox manual para terminais sem questionary."""
    for i, opt in enumerate(options, 1):
        is_sel = opt in current
        mark = f"{C.GRN}✓{C.R}" if is_sel else f"{C.D}·{C.R}"
        print(f"   {mark}  {color}{C.B}{i:2d}{C.R}  {opt}")
    print()
    hint("Digite os números separados por vírgula (ex: 1,3,5)")
    hint("Ou Enter para manter a seleção atual")
    nums = input(f"\n  {C.B}›{C.R} ").strip()
    if not nums:
        return current
    try:
        indices = [int(n.strip()) - 1 for n in nums.split(",")]
        return [options[i] for i in indices if 0 <= i < len(options)]
    except (ValueError, IndexError):
        warn("Entrada inválida, mantendo seleção anterior")
        return current


# ═════════════════════════════════════════════════════════════════════
# LOOP PRINCIPAL
# ═════════════════════════════════════════════════════════════════════

def run_cli():
    """Ponto de entrada do CLI."""
    if not HAS_QUESTIONARY:
        print(f"\n  {C.YLW}⚠ Modo simplificado (questionary não instalado){C.R}")
        print(f"  {C.D}Para menus interativos: venv/bin/pip install questionary{C.R}\n")
        time.sleep(1)

    cm = ConfigManager()
    config = cm.load()

    while True:
        banner()
        show_resume(config)
        action = main_menu()

        if action == "exit" or action is None:
            print(f"\n  {C.CYN}👋 Até a próxima!{C.R}\n")
            break
        elif action == "start":
            start_extraction(config, cm)
        elif action == "labels":
            config = configure_labels(config, cm)
        elif action == "business":
            config = configure_business(config, cm)
        elif action == "preset":
            config = load_preset(config, cm)
        elif action == "clear":
            clear_progress()
        else:
            err("Opção inválida")
            wait_enter()


if __name__ == "__main__":
    run_cli()
