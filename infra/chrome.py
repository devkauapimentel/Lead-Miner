"""
infra/chrome.py — ChromeManager
================================
Gerencia perfil do Chrome e configuração do WebDriver.
Suporta 2 modos:
  - "profile": Copia perfil do Chrome e abre nova instância
  - "remote":  Conecta a um Chrome JÁ ABERTO (via Debug Port)
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

    Modos de conexão:
        - "profile" (padrão): Copia o perfil do Chrome do usuário e
          abre uma nova instância isolada. Útil para primeira vez.
        - "remote": Conecta a um Chrome que JÁ ESTÁ ABERTO com
          o WhatsApp logado. Útil para evitar re-login.

    Para usar o modo remote, inicie o Chrome com:
        google-chrome --remote-debugging-port=9222

    Depois selecione "Usar Chrome Aberto" na GUI.
    """

    def __init__(self, config: dict):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        chrome_cfg = config.get("chrome", {})
        self.mode = chrome_cfg.get("mode", "profile")
        self.debug_port = chrome_cfg.get("debug_port", 9222)
        self.exact_profile_path = os.path.expanduser(
            chrome_cfg.get("profile_path", "~/.config/google-chrome/Default")
        )
        self.binary = chrome_cfg.get("binary", "auto")
        self.robo_profile = os.path.join(base_dir, "chrome_profile_robo")

    def criar_driver(self) -> webdriver.Chrome:
        """
        Cria o WebDriver baseado no modo configurado.

        Returns:
            Instância do selenium.webdriver.Chrome
        """
        if self.mode == "remote":
            return self._criar_driver_remoto()
        else:
            return self._criar_driver_perfil()

    def _criar_driver_remoto(self) -> webdriver.Chrome:
        """
        Conecta a um Chrome já aberto via Remote Debugging Protocol.

        O usuário precisa ter aberto o Chrome com:
            google-chrome --remote-debugging-port=9222

        Ou selecionar "Usar Chrome Aberto" na GUI que faz isso automaticamente.
        """
        log.info(f"[*] Conectando ao Chrome na porta {self.debug_port}...")

        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", f"localhost:{self.debug_port}")

        try:
            driver = webdriver.Chrome(options=options)
            log.info("[✓] Conectado ao Chrome aberto!")
            return driver
        except Exception as e:
            raise ConnectionError(
                f"Não conseguiu conectar ao Chrome na porta {self.debug_port}. "
                f"Verifique se o Chrome está aberto com --remote-debugging-port={self.debug_port}\n"
                f"Erro: {e}"
            )

    def _criar_driver_perfil(self) -> webdriver.Chrome:
        """
        Cria nova instância do Chrome com perfil copiado.
        Modo padrão — abre um Chrome novo.
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

    def detectar_binario(self) -> str:
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

    def detectar_perfil_exato(self) -> str:
        if os.path.exists(self.exact_profile_path):
            return self.exact_profile_path

        # Tentar fallbacks comuns
        for base_path in PROFILE_PATHS:
            for sub_profile in ["Default", "Profile 1", "Profile 2", "Profile 3"]:
                chute = os.path.join(base_path, sub_profile)
                if os.path.exists(chute):
                    log.info(f"Perfil detectado automaticamente: {chute}")
                    return chute

        raise FileNotFoundError(
            "Caminho exato do perfil do Chrome não encontrado. "
            "Abra o Chrome no perfil correto, acesse chrome://version, "
            "copie o 'Caminho de perfil' e cole na área de Configuração da Interface."
        )

    def copiar_perfil(self) -> None:
        if os.path.exists(self.robo_profile):
            log.info("[*] Perfil do robô já existe. Limpando locks residuais e reutilizando...")
            # Limpar lockfiles que sobram após um crash ou pkill
            for lock_file in ['SingletonLock', 'SingletonSocket', 'SingletonCookie']:
                lock_path = os.path.join(self.robo_profile, lock_file)
                if os.path.exists(lock_path) or os.path.islink(lock_path):
                    try:
                        if os.path.islink(lock_path):
                            os.unlink(lock_path)
                        else:
                            os.remove(lock_path)
                    except Exception:
                        pass
            return

        pasta_origem = self.detectar_perfil_exato()
        pasta_destino = os.path.join(self.robo_profile, "Default")

        if not os.path.exists(pasta_origem):
            raise FileNotFoundError(
                f"Pasta do perfil não encontrada em {pasta_origem}. "
                "Verifique o Caminho de Perfil preenchido nas Configurações."
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

        # Copiar Local State que fica uma pasta acima do perfil (no base_dir)
        base_dir = os.path.dirname(pasta_origem)
        local_state = os.path.join(base_dir, "Local State")
        if os.path.exists(local_state):
            shutil.copy2(local_state, os.path.join(self.robo_profile, "Local State"))

        log.info("[✓] Perfil copiado com sucesso!")

    def limpar_perfil(self) -> None:
        """Remove o perfil clonado do robô (útil para reset de sessão)."""
        if os.path.exists(self.robo_profile):
            shutil.rmtree(self.robo_profile)
            log.info("[✓] Perfil do robô removido")

    @staticmethod
    def iniciar_chrome_debug(port: int = 9222) -> None:
        """
        Inicia o Chrome com remote debugging habilitado.
        Útil para o modo "Usar Chrome Aberto".
        """
        import subprocess
        for path in CHROME_PATHS:
            if os.path.exists(path):
                log.info(f"[*] Iniciando Chrome com debug na porta {port}...")
                subprocess.Popen(
                    [path, f"--remote-debugging-port={port}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
        raise FileNotFoundError("Chrome não encontrado para iniciar com debug")
