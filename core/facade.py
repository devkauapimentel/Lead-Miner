"""
core/facade.py — Fachada do Sistema (Facade Pattern)
=====================================================
Ponto de entrada único que esconde toda a complexidade.
A GUI e o CLI chamam APENAS esta classe.
"""

import logging

from core.config_manager import ConfigManager
from core.filters import create_filter
from core.engine import ScraperEngine
from infra.chrome import ChromeManager
from infra.logger import setup_logger, LogObserver
from infra.exporters import CSVExporter

log = logging.getLogger("pegador")


class PegadorDeContato:
    """
    Fachada principal do sistema.

    Design Pattern: Facade
        Esconde a complexidade de configurar Chrome, Filter,
        Engine, Observers, etc. atrás de uma API de 3 métodos:
        start(), stop(), e status().

    Uso pela GUI:
        pegador = PegadorDeContato()
        pegador.start()  # faz TUDO
        pegador.stop()   # para a execução

    Uso pelo CLI:
        pegador = PegadorDeContato(config_path="meu_config.json")
        pegador.start()
    """

    def __init__(self, config_path: str = None):
        """
        Args:
            config_path: Caminho para o config.json.
                         Se None, usa o padrão na raiz do projeto.
        """
        # Configurar logger
        setup_logger()

        # Carregar configuração
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load()

        # Componentes (inicializados no start)
        self.engine = None
        self.driver = None
        self.csv_exporter = None
        self._gui_observer = None

    def start(self) -> None:
        """
        Inicia a extração completa.

        Fluxo:
            1. Valida configuração
            2. Cria FilterStrategy baseada no config
            3. Cria ChromeManager e abre Chrome
            4. Cria ScraperEngine
            5. Registra Observers (Log, CSV, GUI)
            6. Carrega progresso anterior (se houver)
            7. Executa o loop de extração
        """
        # Validar configuração
        errors = self.config_manager.validate(self.config)
        if errors:
            for e in errors:
                log.error(f"[!] Erro de configuração: {e}")
            raise ValueError(f"Configuração inválida: {'; '.join(errors)}")

        log.info(f"[*] Negócio: {self.config.get('business_name', '?')}")
        log.info(f"[*] Modo: {self.config.get('filter_mode', 'labels')}")

        # Criar filtro (Strategy Pattern)
        filter_strategy = create_filter(self.config)
        log.info(f"[*] Filtro: {type(filter_strategy).__name__}")

        # Criar Chrome (ChromeManager)
        chrome_manager = ChromeManager(self.config)
        self.driver = chrome_manager.criar_driver()

        # Criar Engine
        self.engine = ScraperEngine(self.config, filter_strategy, self.driver)

        # Registrar Observers
        log_observer = LogObserver()
        self.engine.add_observer(log_observer)

        self.csv_exporter = CSVExporter()
        self.engine.add_observer(self.csv_exporter)

        # Registrar observer da GUI se configurado
        if self._gui_observer:
            self.engine.add_observer(self._gui_observer)

        # Carregar progresso anterior
        processados, leads = self.csv_exporter.carregar_progresso()
        self.engine.set_progress(processados, leads)

        # Executar!
        log.info("[*] Iniciando extração...")
        self.engine.run()

    def stop(self) -> None:
        """Para a execução em andamento."""
        if self.engine:
            self.engine.stop()

    def cleanup(self) -> None:
        """Libera recursos (fecha Chrome)."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass

    def set_gui_observer(self, observer) -> None:
        """
        Registra um observer da GUI para receber eventos em tempo real.

        Args:
            observer: Objeto com método on_event(event_type, data)
        """
        self._gui_observer = observer

    def update_config(self, new_config: dict) -> None:
        """
        Atualiza a configuração em memória e salva no arquivo.

        Args:
            new_config: Novo dicionário de configuração
        """
        self.config = new_config
        self.config_manager.save(new_config)

    def get_config(self) -> dict:
        """Retorna a configuração atual."""
        return self.config

    def get_presets(self) -> list[str]:
        """Retorna lista de presets disponíveis."""
        return self.config_manager.list_presets()

    def load_preset(self, preset_name: str) -> dict:
        """Carrega um preset e atualiza a configuração."""
        preset = self.config_manager.load_preset(preset_name)
        self.config = preset
        return preset

    def clear_progress(self) -> None:
        """Limpa dados de execução anterior para recomeço."""
        if self.csv_exporter:
            self.csv_exporter.limpar_dados()
        log.info("[✓] Progresso limpo — pronto para nova extração")
