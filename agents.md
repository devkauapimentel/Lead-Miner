# Regras de Negócio e Comportamento — Lead Miner v2.0.0-beta

Este documento descreve as regras de negócio completas, lógicas de filtragem e procedimentos técnicos do projeto **Lead Miner** (extrator de leads do WhatsApp Web).

> **⚠️ LEITURA OBRIGATÓRIA ANTES DE QUALQUER ALTERAÇÃO:**
> Leia o arquivo [`CHANGELOG.md`](./CHANGELOG.md) para entender o histórico completo de mudanças, bugs resolvidos e decisões técnicas já tomadas. Isso evita regressões e retrabalho.

---

## 0. Protocolo de Modificações (CHANGELOG)

### Regra de Ouro

**Toda** modificação no código — seja `feat`, `fix`, `refactor`, `hotfix` ou `chore` com impacto funcional — **deve** ser registrada no arquivo `CHANGELOG.md` na raiz do projeto **antes ou junto ao commit**.

### Quando atualizar o CHANGELOG

| Situação | Ação no CHANGELOG |
|----------|-------------------|
| Nova funcionalidade (`feat`) | Adicionar em **Adicionado** |
| Correção de bug (`fix`) | Adicionar em **Corrigido** |
| Refatoração com mudança de API/comportamento (`refactor`) | Adicionar em **Alterado** |
| Remoção de código/funcionalidade | Adicionar em **Removido** |
| Correção de segurança (`hotfix`) | Adicionar em **Segurança** |
| Alteração de dependência com impacto (`chore(deps)`) | Adicionar em **Alterado** |
| Apenas formatação, espaçamento, typo (`style`, `docs`) | **NÃO** precisa registrar |

### Formato obrigatório

Seguir **Keep a Changelog** com entradas claras, citando o arquivo alterado:

```markdown
### Adicionado
- **Descrição curta:** Explicação do que faz e por quê (`arquivo_afetado.py`).

### Corrigido
- **Nome do bug:** O que estava errado e como foi resolvido (`arquivo_afetado.py`).
```

### Seções de versão

- Alterações em progresso ficam sob `## [Não Lançado]` com o nome da branch.
- Ao criar uma `release/`, mover o conteúdo de `[Não Lançado]` para uma nova seção `## [X.Y.Z] — YYYY-MM-DD`.

### Checklist de Commit atualizado

Antes de qualquer commit, confirme:

- [ ] `CHANGELOG.md` foi atualizado se a alteração tem impacto funcional.
- [ ] `agents.md` foi atualizado se alguma regra de negócio mudou.
- [ ] `git status` limpo — nenhum arquivo sensível tracked (ver `/versioning-workflow`).
- [ ] A mensagem de commit segue o padrão Conventional Commits (ver `/git-workflow`).

---

## 1. Visão Geral

O **Lead Miner v2.0.0-beta** (anteriormente Pegador de Contato) é um sistema modular e reutilizável de extração de leads do WhatsApp Business Web. Ele automatiza o processo de percorrer conversas, identificar potenciais clientes (leads) através de **Etiquetas (Labels)** do WhatsApp Business, e salvar seus números em um CSV para campanhas de remarketing.

### Evolução do Projeto
| Aspecto | v1.0.0 (Legacy) | v2.0.0-beta (Atual) |
|---------|---------------|--------------|
| Nome | Pegador de Contato | **Lead Miner** |
| Filtragem | Palavras-chave no chat | Etiquetas do WhatsApp Business |
| Config | Hardcoded no Python | Arquivo JSON externo |
| Interface | Nenhuma (editar código) | GUI (CustomTkinter) + CLI (questionary) |
| Arquitetura | Monolito (1 arquivo) | Modular (core/, infra/, ui/) |
| Reutilização | Apenas 1 clínica | Qualquer negócio via Presets |
| Chrome | Modo único (clone) | 3 modos: Nativo, Clonado, Zerado |

## 2. Arquitetura

O sistema utiliza 4 Design Patterns:
- **Strategy Pattern** (filtros): Permite trocar a lógica de filtragem sem alterar o motor
- **Configuration Pattern** (config.json): Regras de negócio fora do código
- **Observer Pattern** (eventos): Motor emite eventos; Log, CSV e GUI reagem
- **Facade Pattern** (LeadMinerFacade): Ponto de entrada único

### Estrutura de Camadas
```
Interface (GUI/CLI) → Fachada → Motor + Filtros → Chrome + CSV + Logger
```

### Estrutura de Diretórios
```
Lead-Miner/
├── main.py                  # Ponto de entrada (GUI ou CLI)
├── config.json              # Configuração ativa do negócio
├── CHANGELOG.md             # ⬅️ Histórico de todas as modificações
├── agents.md                # Este arquivo (regras de negócio)
├── requirements.txt         # Dependências Python
├── core/
│   ├── engine.py            # Motor de extração (ScraperEngine)
│   ├── facade.py            # Fachada (LeadMinerFacade)
│   ├── filters.py           # Estratégias de filtragem
│   └── config_manager.py    # Gerenciador de configuração
├── infra/
│   ├── chrome.py            # ChromeManager (3 modos de browser)
│   ├── exporters.py         # CSVExporter (Observer)
│   ├── logger.py            # Logger dual + LogObserver
│   └── phone_utils.py       # Funções puras de telefone
├── ui/
│   ├── gui.py               # Interface visual (CustomTkinter)
│   └── cli.py               # Interface terminal (questionary)
├── presets/                  # Configs prontas por segmento
├── assets/                  # Identidade Visual (branding)
├── data/                    # Dados de execução (CSV, logs, progresso)
└── .agents/workflows/       # Regras de Git e Versionamento
```

## 3. Modos de Navegador (Chrome)

O sistema suporta 3 estratégias de inicialização do Chrome, configuráveis pela GUI:

| Modo | Valor config | Descrição | Quando usar |
|------|-------------|-----------|-------------|
| **Nativo** | `real` | Selenium assume o perfil real do Chrome com GNOME Keyring | Conta principal já logada |
| **Clonado** | `isolated` | Cópia do perfil real em diretório isolado, incluindo Service Worker | Automação segura sem fechar o Chrome pessoal |
| **Zerado** | `clean` | Perfil vazio — exige escaneio de QR Code | Contas secundárias ou primeiro login |

> **Decisão técnica:** O modo `real` executa `pkill -f chrome` antes de abrir e NÃO aplica `--no-sandbox` para preservar acesso ao cofre de senhas do GNOME Keyring.

## 4. Modos de Filtragem

O sistema suporta 3 modos configuráveis:

### 4.1 Labels (Recomendado)
Filtra contatos pelas **etiquetas do WhatsApp Business**. O bot abre o painel "Dados do Contato", lê as etiquetas e aplica regras de inclusão/exclusão.

**Regra de Prioridade:** A exclusão SEMPRE vence a inclusão. Se um contato tem `Lead Anuncio` E `Agendada`, ele é **EXCLUÍDO**.

### 4.2 Keywords (Legado)
Filtra por palavras-chave no histórico de mensagens. Mantido para compatibilidade com contas sem WhatsApp Business.

### 4.3 Hybrid (Avançado)
Combina Labels + Keywords. Se o contato tem etiquetas, usa Labels. Senão, cai para Keywords.

## 5. Condições de Pulo e Exclusões

Antes de avaliar qualquer conversa, o contato é ignorado se:
- **Grupos ou Comunidades:** Possui ícone de grupo/comunidade
- **Lista Negra:** Nome contém palavras configuradas em `blacklist_names`
- **Número Próprio:** Número igual ao `own_number` do config.json
- **Já Processado:** Presente no `progresso.json` (retomada)
- **Limite de Teste:** Se `max_contacts` está definido

## 6. Configuração via config.json

Todas as regras de negócio são controladas pelo arquivo `config.json`:
```json
{
  "business_name": "Nome do Negócio",
  "own_number": "5521994538190",
  "chrome": {
    "mode": "isolated",
    "profile_path": "/home/user/.config/google-chrome/Default",
    "binary": "auto"
  },
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

## 7. Presets por Tipo de Negócio

Configurações prontas em `presets/`:
- `clinica_estetica.json` — Clínicas de estética/dermatologia
- `dentista.json` — Consultórios odontológicos
- `advogado.json` — Escritórios de advocacia
- `imobiliaria.json` — Corretores de imóveis

## 8. Persistência de Dados

- **CSV Incremental:** Leads gravados em `data/leads_remarketing.csv` via append O(1)
- **Progresso:** Estado salvo em `data/progresso.json` para retomada
- **Logs:** Registro dual (arquivo + terminal) em `data/scraper.log`

## 9. Interface

### GUI (Padrão)
Janela visual com CustomTkinter (dark mode):
- **Aba Config:** Checkboxes para etiquetas, dados do negócio, presets, modo Chrome
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

## 10. Referências Obrigatórias

Antes de fazer qualquer alteração neste projeto, **consulte estes documentos na ordem**:

1. **[`CHANGELOG.md`](./CHANGELOG.md)** — O que já foi feito, bugs já resolvidos, decisões técnicas passadas.
2. **[`/git-workflow`](./.agents/workflows/git-workflow.md)** — Regras de branching, commits e merges.
3. **[`/versioning-workflow`](./.agents/workflows/versioning-workflow.md)** — Isolamento, testes, segurança LGPD.
