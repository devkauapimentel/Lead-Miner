"""
core/filters.py — Estratégias de Filtragem (Strategy Pattern)
==============================================================
Cada Strategy decide se um contato deve ser INCLUÍDO ou EXCLUÍDO
da lista de leads, usando critérios diferentes.

O Engine chama filter.should_include() e filter.should_exclude()
sem saber QUAL estratégia está ativa — isso é o Strategy Pattern.
"""

from abc import ABC, abstractmethod
import logging

log = logging.getLogger("lead_miner")


class FilterStrategy(ABC):
    """
    Interface base para todas as estratégias de filtragem.

    Design Pattern: Strategy
        Define um contrato (métodos abstratos) que toda
        estratégia é obrigada a implementar. O Engine
        usa a interface, não a implementação concreta.

    Qualquer nova forma de filtrar (por data, por cidade,
    por IA, etc.) só precisa herdar desta classe e implementar
    os dois métodos.
    """

    @abstractmethod
    def should_include(self, contact_info: dict) -> bool:
        """
        Verifica se o contato atende aos critérios de INCLUSÃO.

        Args:
            contact_info: Dicionário com dados do contato:
                - 'name': Nome do contato
                - 'labels': Lista de etiquetas (str[])
                - 'messages': Texto das mensagens (str, opcional)
                - 'is_unsaved': Se é número não salvo (bool)

        Returns:
            True se o contato deve ser incluído como lead
        """
        pass

    @abstractmethod
    def should_exclude(self, contact_info: dict) -> bool:
        """
        Verifica se o contato atende aos critérios de EXCLUSÃO.
        A exclusão tem PRIORIDADE sobre a inclusão.

        Args:
            contact_info: Mesmo dicionário de should_include

        Returns:
            True se o contato deve ser excluído (mesmo que passe na inclusão)
        """
        pass

    def evaluate(self, contact_info: dict) -> tuple[bool, str]:
        """
        Avalia um contato e retorna o veredicto final.
        Exclusão SEMPRE tem prioridade sobre inclusão.

        Returns:
            Tupla (is_lead: bool, reason: str)
        """
        if self.should_exclude(contact_info):
            return False, "Excluído por regra de exclusão"
        if self.should_include(contact_info):
            return True, "Incluído por regra de inclusão"
        return False, "Sem match"


class LabelFilterStrategy(FilterStrategy):
    """
    [PRINCIPAL] Filtra contatos por Etiquetas do WhatsApp Business.

    Como funciona:
        - Include: Se o contato tiver QUALQUER etiqueta da lista
                   de inclusão, ele é um lead.
        - Exclude: Se o contato tiver QUALQUER etiqueta da lista
                   de exclusão, é bloqueado (mesmo se tiver inclusão).

    Exemplo:
        include_labels = ["Lead Anuncio", "Repescagem"]
        exclude_labels = ["Agendada", "Consulta paga"]

        Contato com labels ["Lead Anuncio", "Agendada"]
        → should_exclude retorna True → NÃO vira lead
    """

    def __init__(self, include_labels: list[str], exclude_labels: list[str]):
        self.include_labels = [l.lower().strip() for l in include_labels]
        self.exclude_labels = [l.lower().strip() for l in exclude_labels]

    def should_include(self, contact_info: dict) -> bool:
        contact_labels = [l.lower().strip() for l in contact_info.get("labels", [])]
        return any(label in self.include_labels for label in contact_labels)

    def should_exclude(self, contact_info: dict) -> bool:
        contact_labels = [l.lower().strip() for l in contact_info.get("labels", [])]
        return any(label in self.exclude_labels for label in contact_labels)


class KeywordFilterStrategy(FilterStrategy):
    """
    [LEGADO] Filtra contatos por palavras-chave no histórico de chat.

    Esta é a lógica original do v1.0. Mantida para compatibilidade
    com contas que NÃO usam WhatsApp Business (sem etiquetas).

    Como funciona:
        - Include: Se as MENSAGENS DO CLIENTE contiverem qualquer
                   termo de interesse (valor, preço, agendar, etc.)
        - Exclude: Se QUALQUER mensagem (cliente ou própria) contiver
                   termos de exclusão (agendado, comprovante, etc.)
    """

    def __init__(self, include_terms: list[str], exclude_terms: list[str]):
        self.include_terms = [t.lower().strip() for t in include_terms]
        self.exclude_terms = [t.lower().strip() for t in exclude_terms]

    def should_include(self, contact_info: dict) -> bool:
        # Verifica nas mensagens do cliente (message-in)
        client_msgs = contact_info.get("client_messages", "").lower()
        return any(term in client_msgs for term in self.include_terms)

    def should_exclude(self, contact_info: dict) -> bool:
        # Verifica em TODAS as mensagens (cliente + próprias)
        all_msgs = contact_info.get("messages", "").lower()
        return any(term in all_msgs for term in self.exclude_terms)


class HybridFilterStrategy(FilterStrategy):
    """
    [AVANÇADO] Combina Labels + Keywords para máxima precisão.

    Primeiro verifica etiquetas (rápido). Se não houver labels,
    cai para verificação de palavras-chave (lento mas robusto).

    Útil para contas onde nem todos os contatos estão etiquetados.
    """

    def __init__(
        self,
        include_labels: list[str],
        exclude_labels: list[str],
        include_terms: list[str],
        exclude_terms: list[str],
    ):
        self.label_filter = LabelFilterStrategy(include_labels, exclude_labels)
        self.keyword_filter = KeywordFilterStrategy(include_terms, exclude_terms)

    def should_include(self, contact_info: dict) -> bool:
        # Se tem labels, usa labels. Senão, usa keywords.
        if contact_info.get("labels"):
            return self.label_filter.should_include(contact_info)
        return self.keyword_filter.should_include(contact_info)

    def should_exclude(self, contact_info: dict) -> bool:
        # Exclusão: verifica AMBOS os sistemas
        if self.label_filter.should_exclude(contact_info):
            return True
        return self.keyword_filter.should_exclude(contact_info)


def create_filter(config: dict) -> FilterStrategy:
    """
    Factory function — cria a Strategy correta baseada na configuração.

    Args:
        config: Dicionário de configuração do negócio

    Returns:
        Instância da FilterStrategy apropriada
    """
    mode = config.get("filter_mode", "labels")

    if mode == "labels":
        labels = config.get("labels", {})
        return LabelFilterStrategy(
            include_labels=labels.get("include", []),
            exclude_labels=labels.get("exclude", []),
        )

    elif mode == "keywords":
        keywords = config.get("keywords", {})
        return KeywordFilterStrategy(
            include_terms=keywords.get("include", []),
            exclude_terms=keywords.get("exclude", []),
        )

    elif mode == "hybrid":
        labels = config.get("labels", {})
        keywords = config.get("keywords", {})
        return HybridFilterStrategy(
            include_labels=labels.get("include", []),
            exclude_labels=labels.get("exclude", []),
            include_terms=keywords.get("include", []),
            exclude_terms=keywords.get("exclude", []),
        )

    else:
        log.warning(f"Modo de filtro desconhecido: {mode}. Usando 'labels'.")
        labels = config.get("labels", {})
        return LabelFilterStrategy(
            include_labels=labels.get("include", []),
            exclude_labels=labels.get("exclude", []),
        )
