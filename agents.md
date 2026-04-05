# Regras de Negócio e Comportamento - Pegador de Contatos v2.0

Este documento descreve as regras de negócio completas, lógicas de filtragem e procedimentos técnicos do projeto **Pegador de Contato** (extrator de leads do WhatsApp Web).

## 1. Visão Geral

O software v2.0 é um sistema modular e reutilizável de extração de leads do WhatsApp Business Web. Ele automatiza o processo de percorrer conversas, identificar potenciais clientes (leads) através de **Etiquetas (Labels)** do WhatsApp Business, e salvar seus números em um CSV para campanhas de remarketing.

### Diferenças da v1.0 para a v2.0
| Aspecto | v1.0 (Legacy) | v2.0 (Atual) |
|---------|---------------|--------------|
| Filtragem | Palavras-chave no chat | Etiquetas do WhatsApp Business |
| Config | Hardcoded no Python | Arquivo JSON externo |
| Interface | Nenhuma (editar código) | GUI (CustomTkinter) + CLI (questionary) |
| Arquitetura | Monolito (1 arquivo) | Modular (core/, infra/, ui/) |
| Reutilização | Apenas 1 clínica | Qualquer negócio via Presets |

## 2. Arquitetura

O sistema utiliza 4 Design Patterns:
- **Strategy Pattern** (filtros): Permite trocar a lógica de filtragem sem alterar o motor
- **Configuration Pattern** (config.json): Regras de negócio fora do código
- **Observer Pattern** (eventos): Motor emite eventos; Log, CSV e GUI reagem
- **Facade Pattern** (PegadorDeContato): Ponto de entrada único

### Estrutura de Camadas
```
Interface (GUI/CLI) → Fachada → Motor + Filtros → Chrome + CSV + Logger
```

## 3. Modos de Filtragem

O sistema suporta 3 modos configuráveis:

### 3.1 Labels (Recomendado)
Filtra contatos pelas **etiquetas do WhatsApp Business**. O bot abre o painel "Dados do Contato", lê as etiquetas e aplica regras de inclusão/exclusão.

**Regra de Prioridade:** A exclusão SEMPRE vence a inclusão. Se um contato tem `Lead Anuncio` E `Agendada`, ele é **EXCLUÍDO**.

### 3.2 Keywords (Legado)
Filtra por palavras-chave no histórico de mensagens. Mantido para compatibilidade com contas sem WhatsApp Business.

### 3.3 Hybrid (Avançado)
Combina Labels + Keywords. Se o contato tem etiquetas, usa Labels. Senão, cai para Keywords.

## 4. Condições de Pulo e Exclusões

Antes de avaliar qualquer conversa, o contato é ignorado se:
- **Grupos ou Comunidades:** Possui ícone de grupo/comunidade
- **Lista Negra:** Nome contém palavras configuradas em `blacklist_names`
- **Número Próprio:** Número igual ao `own_number` do config.json
- **Já Processado:** Presente no `progresso.json` (retomada)
- **Limite de Teste:** Se `max_contacts` está definido

## 5. Configuração via config.json

Todas as regras de negócio são controladas pelo arquivo `config.json`:
```json
{
  "business_name": "Nome do Negócio",
  "own_number": "5521994538190",
  "labels": {
    "include": ["Lead Anuncio", "Repescagem"],
    "exclude": ["Agendada", "Consulta paga"]
  },
  "filter_mode": "labels",
  "blacklist_names": ["nome1", "nome2"],
  "scraper": {
    "max_contacts": null,
    "internal_scrolls": 20
  }
}
```

## 6. Presets por Tipo de Negócio

Configurações prontas em `presets/`:
- `clinica_estetica.json` — Clínicas de estética/dermatologia
- `dentista.json` — Consultórios odontológicos
- `advogado.json` — Escritórios de advocacia
- `imobiliaria.json` — Corretores de imóveis

## 7. Persistência de Dados

- **CSV Incremental:** Leads gravados em `data/leads_remarketing.csv` via append O(1)
- **Progresso:** Estado salvo em `data/progresso.json` para retomada
- **Logs:** Registro dual (arquivo + terminal) em `data/scraper.log`

## 8. Interface

### GUI (Padrão)
Janela visual com CustomTkinter (dark mode):
- **Aba Config:** Checkboxes para etiquetas, dados do negócio, presets
- **Aba Execução:** Botão START/STOP, barra de progresso, log em tempo real

### CLI (Terminal)
Menu interativo no terminal:
- Seleção por espaço/enter das etiquetas
- Fallback para ambientes sem display gráfico

### Uso
```bash
python main.py        # Abre GUI
python main.py --cli  # Abre terminal interativo
```
