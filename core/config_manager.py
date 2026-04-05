"""
core/config_manager.py — Gerenciador de Configuração
=====================================================
Carrega, valida e salva configurações do negócio a partir
de um arquivo JSON externo (Configuration Pattern).

O objetivo é que NENHUMA regra de negócio fique hardcoded
no código. Tudo vem do config.json, editável pela GUI.
"""

import os
import json
import logging
import copy

log = logging.getLogger("lead_miner")


# Configuração padrão — usada na primeira execução
DEFAULT_CONFIG = {
    "business_name": "Meu Negócio",
    "own_number": "",
    "chrome": {
        "profile_path": "~/.config/google-chrome",
        "binary": "auto"
    },
    "labels": {
        "include": ["Lead Anuncio"],
        "exclude": ["Agendada", "Consulta paga"]
    },
    "filter_mode": "labels",
    "keywords": {
        "include": [
            "valor", "preço", "consulta", "agendar",
            "avaliação", "como funciona", "quero agendar"
        ],
        "exclude": [
            "agendada com sucesso", "comprovante",
            "pagamento", "confirmado"
        ]
    },
    "auto_lead_names": ["anúncio", "anuncio", "ads"],
    "blacklist_names": [],
    "scraper": {
        "max_contacts": None,
        "internal_scrolls": 20
    }
}

# Lista de todas as etiquetas conhecidas do WhatsApp Business
# (serve como referência na GUI — o usuário pode adicionar mais)
KNOWN_LABELS = [
    "Lead Anuncio",
    "Remarcar",
    "Para Viviane",
    "Urgente",
    "Repescagem",
    "Andreza",
    "Marcella",
    "Agendada",
    "Consulta paga",
    "Instagram",
    "Esperando resposta",
    "Aguardando pagamento",
    "Dar retorno",
    "yasmim",
]


class ConfigManager:
    """
    Gerencia a configuração do negócio (config.json).

    Design Pattern: Configuration Pattern
        Separa as regras de negócio do código. O ConfigManager
        lê/grava um arquivo JSON que pode ser editado pela GUI
        ou manualmente, sem mexer no código Python.

    Uso:
        cm = ConfigManager()
        config = cm.load()
        config["labels"]["include"].append("Nova Tag")
        cm.save(config)
    """

    def __init__(self, config_path: str = None):
        """
        Args:
            config_path: Caminho absoluto para o config.json.
                         Se None, usa 'config.json' na raiz do projeto.
        """
        if config_path is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base, "config.json")
        self.config_path = config_path

    def load(self) -> dict:
        """
        Carrega a configuração do arquivo JSON.
        Se o arquivo não existir, cria um com os padrões.

        Returns:
            Dicionário de configuração completo
        """
        if not os.path.exists(self.config_path):
            log.info("[*] config.json não encontrado, criando padrão...")
            self.save(DEFAULT_CONFIG)
            return copy.deepcopy(DEFAULT_CONFIG)

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Mescla com defaults para garantir campos faltantes
        merged = copy.deepcopy(DEFAULT_CONFIG)
        self._deep_merge(merged, config)
        return merged

    def save(self, config: dict) -> None:
        """
        Salva a configuração no arquivo JSON.

        Args:
            config: Dicionário de configuração a salvar
        """
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        log.info(f"[✓] Configuração salva em {self.config_path}")

    def load_preset(self, preset_name: str) -> dict:
        """
        Carrega um preset de configuração por tipo de negócio.

        Args:
            preset_name: Nome do preset (ex: 'clinica_estetica')

        Returns:
            Dicionário de configuração do preset

        Raises:
            FileNotFoundError: Se o preset não existir
        """
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        preset_path = os.path.join(base, "presets", f"{preset_name}.json")

        if not os.path.exists(preset_path):
            raise FileNotFoundError(f"Preset '{preset_name}' não encontrado: {preset_path}")

        with open(preset_path, 'r', encoding='utf-8') as f:
            preset = json.load(f)

        log.info(f"[✓] Preset carregado: {preset_name}")
        return preset

    def list_presets(self) -> list[str]:
        """
        Lista todos os presets disponíveis.

        Returns:
            Lista de nomes de presets (sem extensão .json)
        """
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        presets_dir = os.path.join(base, "presets")

        if not os.path.exists(presets_dir):
            return []

        return [
            f[:-5] for f in os.listdir(presets_dir)
            if f.endswith('.json')
        ]

    def validate(self, config: dict) -> list[str]:
        """
        Valida a configuração e retorna lista de erros.

        Args:
            config: Dicionário de configuração a validar

        Returns:
            Lista de strings de erro (vazia = válido)
        """
        errors = []

        if not config.get("own_number"):
            errors.append("Número próprio não configurado")

        labels = config.get("labels", {})
        if not labels.get("include"):
            errors.append("Nenhuma etiqueta de inclusão selecionada")

        chrome = config.get("chrome", {})
        binary = chrome.get("binary", "auto")
        if binary != "auto" and not os.path.exists(binary):
            errors.append(f"Binário do Chrome não encontrado: {binary}")

        mode = config.get("filter_mode", "labels")
        if mode not in ("labels", "keywords", "hybrid"):
            errors.append(f"Modo de filtro inválido: {mode}")

        return errors

    def get_known_labels(self) -> list[str]:
        """Retorna a lista de etiquetas conhecidas para exibição na GUI."""
        return KNOWN_LABELS.copy()

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> None:
        """
        Mescla override em base recursivamente.
        Campos de override sobrescrevem base; campos faltantes mantêm o default.
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                ConfigManager._deep_merge(base[key], value)
            else:
                base[key] = value
