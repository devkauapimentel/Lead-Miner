"""
infra/phone_utils.py — Utilitários de Telefone
================================================
Funções puras de limpeza e formatação de números.
Extraídas do monolito whatsapp_lead_scraper.py para reutilização.
"""

import re


def limpar_numero(texto: str) -> str:
    """
    Remove todos os caracteres não-numéricos de um texto
    e garante que o resultado comece com o DDI do Brasil (55).

    Exemplos:
        '+55 (21) 99453-8190'  → '5521994538190'
        '21994538190'          → '5521994538190'
        '(11) 98765-4321'      → '5511987654321'
    """
    n = re.sub(r'\D', '', texto)
    if n and not n.startswith('55'):
        n = '55' + n
    return n


def titulo_e_numero(titulo: str) -> str | None:
    """
    Se o título de uma conversa do WhatsApp for composto apenas
    por dígitos (ex: "+55 21 96496-9820"), extrai e retorna o
    número limpo. Se for um nome de contato salvo, retorna None.

    Lógica:
        1. Remove tudo que não é dígito
        2. Se restaram 10+ dígitos, é um telefone
        3. Normaliza com DDI 55
        4. Valida se o resultado tem 12+ dígitos

    Args:
        titulo: Texto do título da conversa no WhatsApp

    Returns:
        Número formatado (ex: '5521964969820') ou None
    """
    digitos = re.sub(r'\D', '', titulo)
    if len(digitos) >= 10:
        n = digitos if digitos.startswith('55') else '55' + digitos
        return n if len(n) >= 12 else None
    return None


def extrair_numeros_do_texto(texto: str) -> list[str]:
    """
    Encontra todos os padrões de telefone em um bloco de texto
    usando regex. Retorna lista de números limpos e deduplicados.

    Padrão reconhecido:
        +55 (21) 99453-8190
        5521994538190
        21 99453 8190
        +55 21 96496-9820
    """
    padrao = r'\+?\d{2,3}\s?\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4}'
    encontrados = re.findall(padrao, texto)

    numeros_validos = []
    for e in encontrados:
        limpo = limpar_numero(e)
        if len(limpo) >= 12 and limpo not in numeros_validos:
            numeros_validos.append(limpo)

    return numeros_validos


def formatar_para_exibicao(numero: str) -> str:
    """
    Formata um número limpo para exibição humana.

    Exemplo:
        '5521994538190' → '+55 (21) 99453-8190'
    """
    if len(numero) < 12:
        return numero

    ddi = numero[:2]
    ddd = numero[2:4]
    rest = numero[4:]

    if len(rest) == 9:
        return f"+{ddi} ({ddd}) {rest[:5]}-{rest[5:]}"
    elif len(rest) == 8:
        return f"+{ddi} ({ddd}) {rest[:4]}-{rest[4:]}"
    else:
        return f"+{ddi} ({ddd}) {rest}"
