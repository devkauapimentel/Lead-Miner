"""
infra/logger.py — Sistema de Logging com Observer
==================================================
Logger dual (arquivo + terminal) que implementa o Observer Pattern
para receber eventos do ScraperEngine e registrá-los.
"""

import os
import logging


def setup_logger(log_dir: str = None) -> logging.Logger:
    """
    Configura e retorna o logger global do projeto.

    O logger escreve simultaneamente para:
        1. O terminal (StreamHandler) — feedback em tempo real
        2. Um arquivo .log (FileHandler) — auditoria permanente

    Args:
        log_dir: Diretório onde o arquivo scraper.log será criado.
                 Se None, usa o diretório 'data/' relativo à raiz do projeto.

    Returns:
        Logger configurado com nome 'pegador'
    """
    if log_dir is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base, "data")

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "scraper.log")

    logger = logging.getLogger("pegador")

    # Evitar handlers duplicados se chamado múltiplas vezes
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # Handler de arquivo
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler de terminal
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


class LogObserver:
    """
    Observer que registra eventos do ScraperEngine no logger.

    Design Pattern: Observer
        O Engine emite eventos ('lead_found', 'contact_skipped', etc.)
        e este Observer os converte em mensagens de log formatadas.

    Uso:
        engine.add_observer(LogObserver())
    """

    def __init__(self):
        self.logger = logging.getLogger("pegador")

    def on_event(self, event_type: str, data: dict) -> None:
        """
        Recebe um evento do Engine e loga com formatação apropriada.

        Args:
            event_type: Tipo do evento (ex: 'lead_found', 'contact_skipped')
            data: Dicionário com dados do evento
        """
        idx = data.get("index", "?")
        name = data.get("name", "?")
        total_leads = data.get("total_leads", 0)

        formatters = {
            "lead_found": lambda: (
                f"  [{idx}] ✅ LEAD #{total_leads}: "
                f"{data.get('phone', '?')} ← {name}"
            ),
            "lead_duplicate": lambda: (
                f"  [{idx}] ✅ Duplicado: {name} → {data.get('phone', '?')}"
            ),
            "contact_excluded": lambda: (
                f"  [{idx}] 🚫 Excluído ({data.get('reason', '')}): {name}"
            ),
            "contact_skipped": lambda: (
                f"  [{idx}] ⏭ {data.get('reason', 'Pulado')}: {name}"
            ),
            "contact_no_match": lambda: (
                f"  [{idx}] ❌ Sem match: {name}"
            ),
            "contact_no_phone": lambda: (
                f"  [{idx}] ⚠️ Match mas sem número: {name}"
            ),
            "error": lambda: (
                f"  [{idx}] ⚠️ Erro: {data.get('message', '')[:60]}"
            ),
            "progress": lambda: (
                f"\n  --- {data.get('processed', 0)} processados | "
                f"{total_leads} leads | {data.get('elapsed', 0)}s ---\n"
            ),
            "scroll": lambda: (
                f"      🔄 Scroll: {data.get('done', 0)}/{data.get('total', 0)}"
                f"{' (parou no topo)' if data.get('hit_top') else ''}"
            ),
            "started": lambda: "[✓] Extração iniciada!",
            "finished": lambda: self._format_summary(data),
        }

        formatter = formatters.get(event_type)
        if formatter:
            self.logger.info(formatter())
        else:
            self.logger.info(f"  [{idx}] {event_type}: {data}")

    def _format_summary(self, data: dict) -> str:
        """Formata o relatório final de extração."""
        lines = [
            f"\n{'=' * 50}",
            f"  Processados: {data.get('processed', 0)}",
            f"  Leads novos: {data.get('new_leads', 0)}",
            f"  Total leads: {data.get('total_leads', 0)}",
            f"  Taxa conversão: {data.get('rate', 'N/A')}",
            f"  Velocidade: {data.get('speed', 'N/A')}",
            f"  Tempo: {data.get('time', 'N/A')}",
            f"  CSV: {data.get('csv_path', 'N/A')}",
        ]

        ddds = data.get("ddds", {})
        if ddds:
            lines.append(f"\n  Por DDD:")
            for ddd, qtd in sorted(ddds.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"    {ddd}: {qtd} leads")

        lines.append(f"{'=' * 50}")
        return "\n".join(lines)
