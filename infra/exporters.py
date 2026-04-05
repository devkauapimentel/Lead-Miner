"""
infra/exporters.py — Exportadores de Dados
============================================
Exportadores que implementam o Observer Pattern para salvar leads
conforme são encontrados pelo ScraperEngine.
"""

import os
import csv
import json
import logging

log = logging.getLogger("lead_miner")


class CSVExporter:
    """
    Exporta leads encontrados para um arquivo CSV.

    Design Pattern: Observer
        Recebe eventos 'lead_found' do Engine e grava
        o número no CSV imediatamente (append O(1)).

    Também gerencia o arquivo de progresso (progresso.json)
    para permitir retomada de execução interrompida.
    """

    def __init__(self, data_dir: str = None):
        """
        Args:
            data_dir: Diretório onde os arquivos de dados serão salvos.
                      Se None, usa 'data/' relativo à raiz do projeto.
        """
        if data_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base, "data")

        os.makedirs(data_dir, exist_ok=True)

        self.csv_path = os.path.join(data_dir, "leads_remarketing.csv")
        self.progress_path = os.path.join(data_dir, "progresso.json")
        self._inicializar_csv()

    def _inicializar_csv(self) -> None:
        """Cria o CSV com header se ele não existir ou estiver vazio."""
        if not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0:
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(['Phone'])

    def on_event(self, event_type: str, data: dict) -> None:
        """
        Observer: Reage a eventos do Engine.

        Args:
            event_type: Tipo do evento
            data: Dados do evento
        """
        if event_type == "lead_found":
            self._append_csv(data.get("phone", ""))

        elif event_type == "progress":
            self._salvar_progresso(
                data.get("processed_set", set()),
                data.get("leads_set", set())
            )

        elif event_type == "finished":
            self._salvar_csv_completo(data.get("leads_set", set()))
            self._salvar_progresso(
                data.get("processed_set", set()),
                data.get("leads_set", set())
            )

    def _append_csv(self, numero: str) -> None:
        """Adiciona UM lead ao final do CSV — O(1)."""
        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([numero])

    def _salvar_csv_completo(self, leads: set) -> None:
        """Reescreve o CSV inteiro (safety net no encerramento)."""
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['Phone'])
            for lead in sorted(leads):
                w.writerow([lead])

    def _salvar_progresso(self, processados: set, leads: set) -> None:
        """Grava estado atual no progresso.json para retomada."""
        with open(self.progress_path, 'w', encoding='utf-8') as f:
            json.dump({
                "processados": list(processados),
                "leads": list(leads)
            }, f, ensure_ascii=False)

    def carregar_progresso(self) -> tuple[set, set]:
        """
        Carrega o progresso de uma execução anterior.

        Returns:
            Tupla (processados: set, leads: set) para retomada
        """
        if os.path.exists(self.progress_path):
            with open(self.progress_path, 'r', encoding='utf-8') as f:
                d = json.load(f)
                return set(d.get("processados", [])), set(d.get("leads", []))
        return set(), set()

    def limpar_dados(self) -> None:
        """Remove todos os arquivos de dados (para recomeço limpo)."""
        for path in [self.csv_path, self.progress_path]:
            if os.path.exists(path):
                os.remove(path)
        self._inicializar_csv()
        log.info("[✓] Dados de execução limpos")
