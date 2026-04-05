"""
infra/chrome.py — ChromeManager
================================
Gerencia perfil do Chrome e configuração do WebDriver.
Suporta detecção automática do binário do Chrome no Linux.
"""

import os
import shutil
import logging

from selenium import webdriver

log = logging.getLogger("pegador")


# Localizações comuns do Chrome no Linux
CHROME_PATHS = [
    "/opt/google/chrome/google-chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/opt/google/chrome-unstable/google-chrome-unstable",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
]

# Localizações comuns do perfil do Chrome
PROFILE_PATHS = [
    os.path.expanduser("~/.config/google-chrome"),
    os.path.expanduser("~/.config/google-chrome-stable"),
    os.path.expanduser("~/.config/google-chrome-unstable"),
    os.path.expanduser("~/.config/chromium"),
]


class ChromeManager:
    """
    Gerencia a inicialização do Chrome para automação Selenium.

    Responsabilidades:
        - Detectar automaticamente o binário do Chrome instalado
        - Copiar o perfil do Chrome do usuário para isolamento
        - Configurar as Chrome Options para anti-detecção
        - Criar e retornar a instância do WebDriver

    Design Pattern:
        Encapsula toda a complexidade de configuração do Chrome
        atrás de uma API simples (Facade de infra).
    """

    def __init__(self, config: dict):
        """
        Args:
            config: Dicionário de configuração vindo do ConfigManager.
                    Espera config["chrome"]["profile_path"] e config["chrome"]["binary"]
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        chrome_cfg = config.get("chrome", {})
        self.profile_path = os.path.expanduser(
            chrome_cfg.get("profile_path", "~/.config/google-chrome")
        )
        self.binary = chrome_cfg.get("binary", "auto")
        self.robo_profile = os.path.join(base_dir, "chrome_profile_robo")

    def detectar_binario(self) -> str:
        """
        Encontra o binário do Chrome instalado no sistema.
        Se o usuário configurou 'auto', tenta caminhos conhecidos.

        Returns:
            Caminho absoluto para o binário do Chrome

        Raises:
            FileNotFoundError: Se nenhum Chrome for encontrado
        """
        if self.binary != "auto" and os.path.exists(self.binary):
            log.info(f"Chrome configurado: {self.binary}")
            return self.binary

        for path in CHROME_PATHS:
            if os.path.exists(path):
                log.info(f"Chrome detectado: {path}")
                return path

        raise FileNotFoundError(
            "Chrome não encontrado no sistema. "
            "Instale o Google Chrome ou configure o caminho manualmente em config.json"
        )

    def detectar_perfil(self) -> str:
        """
        Encontra o perfil do Chrome do usuário.

        Returns:
            Caminho absoluto para o diretório do perfil
        """
        if os.path.exists(self.profile_path):
            return self.profile_path

        for path in PROFILE_PATHS:
            if os.path.exists(path):
                log.info(f"Perfil detectado: {path}")
                return path

        raise FileNotFoundError(
            "Perfil do Chrome não encontrado. "
            "Abra o Chrome manualmente uma vez para criar o perfil."
        )

    def copiar_perfil(self) -> None:
        """
        Copia o perfil do Chrome do usuário para um diretório isolado
        do robô, evitando conflitos com o Chrome aberto.

        Ignora arquivos de lock, cache e Service Workers para
        reduzir tamanho e evitar conflitos.
        """
        if os.path.exists(self.robo_profile):
            log.info("[*] Perfil do robô já existe. Reutilizando...")
            return

        perfil_origem = self.detectar_perfil()
        pasta_origem = os.path.join(perfil_origem, "Default")
        pasta_destino = os.path.join(self.robo_profile, "Default")

        if not os.path.exists(pasta_origem):
            raise FileNotFoundError(
                f"Pasta 'Default' não encontrada em {perfil_origem}. "
                "Abra o Chrome e faça login no WhatsApp Web primeiro."
            )

        log.info("[*] Copiando perfil do Chrome...")
        os.makedirs(self.robo_profile, exist_ok=True)

        shutil.copytree(
            pasta_origem,
            pasta_destino,
            ignore=shutil.ignore_patterns(
                'SingletonLock', 'SingletonSocket', 'SingletonCookie',
                'lockfile', 'LOCK', 'Cache', 'Code Cache', 'GPUCache',
                'Service Worker', 'DawnCache', 'GrShaderCache'
            ),
            dirs_exist_ok=True
        )

        # Copiar Local State (necessário para sessão)
        local_state = os.path.join(perfil_origem, "Local State")
        if os.path.exists(local_state):
            shutil.copy2(local_state, os.path.join(self.robo_profile, "Local State"))

        log.info("[✓] Perfil copiado com sucesso!")

    def criar_driver(self) -> webdriver.Chrome:
        """
        Cria e retorna uma instância do Chrome WebDriver
        configurada com anti-detecção e perfil isolado.

        Returns:
            Instância do selenium.webdriver.Chrome pronta para uso
        """
        self.copiar_perfil()
        binary = self.detectar_binario()

        options = webdriver.ChromeOptions()
        options.add_argument(f"--user-data-dir={self.robo_profile}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--remote-allow-origins=*")
        options.add_argument("--disable-gpu")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.binary_location = binary

        driver = webdriver.Chrome(options=options)
        log.info("[✓] Chrome WebDriver criado")
        return driver

    def limpar_perfil(self) -> None:
        """Remove o perfil clonado do robô (útil para reset de sessão)."""
        if os.path.exists(self.robo_profile):
            shutil.rmtree(self.robo_profile)
            log.info("[✓] Perfil do robô removido")
