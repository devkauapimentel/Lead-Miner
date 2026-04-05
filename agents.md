# Regras de Negócio e Comportamento — Pegador de Contatos

> Documento canônico de regras de negócio, lógica de filtragem, arquitetura técnica e procedimentos operacionais do projeto **Pegador de Contato** (extrator de leads do WhatsApp Web).
> Última atualização: 2026-04-04

---

## 1. Visão Geral

O script automatiza um navegador Chrome via **Selenium** acessando o **WhatsApp Web**. Ele percorre a lista completa de contatos no painel lateral (`pane-side`), de cima para baixo, analisando individualmente se cada contato se enquadra como **LEAD** — potencial cliente que demonstrou interesse inicial mas que **ainda não agendou nem pagou**.

### 1.1 Objetivo de Negócio
Gerar uma lista limpa de telefones (`leads_remarketing.csv`) para alimentar campanhas de remarketing (SMS, ligação, WhatsApp Business API), resgatando oportunidades que esfriaram no funil comercial.

### 1.2 Contexto Operacional
- **Nicho:** Clínica de estética (procedimento Criodefine)
- **Fonte de tráfego:** Facebook/Instagram Ads → WhatsApp
- **Ciclo de vida:** Lead frio → Consulta agendada → Pagamento → Procedimento
- **Alvo do scraper:** Leads que estão **entre o primeiro contato e o agendamento** (funil intermediário)

---

## 2. Arquitetura Técnica

### 2.1 Stack

| Componente       | Tecnologia              | Versão     |
|------------------|-------------------------|------------|
| Linguagem        | Python                  | 3.12+      |
| Automação        | Selenium WebDriver      | 4.18.1     |
| Navegador        | Google Chrome (Dev/Unstable) | latest |
| Ambiente         | venv (isolado)          | —          |
| SO alvo          | Linux (Ubuntu/Debian)   | —          |

### 2.2 Arquivos do Sistema

| Arquivo / Diretório       | Tipo        | Sensível | Descrição                                                      |
|---------------------------|-------------|----------|----------------------------------------------------------------|
| `whatsapp_lead_scraper.py`| Código      | ❌       | Script principal — toda lógica em arquivo único                |
| `leads_remarketing.csv`   | Dados       | ✅ LGPD  | Telefones extraídos (escrita incremental O(1))                 |
| `progresso.json`          | Estado      | ✅       | Checkpoint de retomada — nomes processados + leads acumulados  |
| `scraper.log`             | Log         | ⚠️       | Log dual (terminal + arquivo) com timestamps                   |
| `chrome_profile_robo/`    | Perfil      | ✅ CRÍTICO | Cookies e sessão logada do WhatsApp — **nunca versionar**     |
| `requirements.txt`        | Config      | ❌       | Dependência única: `selenium==4.18.1`                          |

### 2.3 Diagrama de Fluxo Principal

```
┌─────────────────────────────────────────────────────────────────────┐
│                    INICIALIZAÇÃO                                    │
│  Copiar perfil Chrome → Carregar progresso → Inicializar CSV       │
│  Abrir Chrome → Navegar WhatsApp Web → Aguardar pane-side          │
│  Refresh (dados frescos) → Aguardar recarga                        │
└─────────────────────────────┬───────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LOOP DE VARREDURA                                │
│  Para cada contato visível em pane-side:                            │
│                                                                     │
│  ┌──────────────────────────┐                                       │
│  │ FILTRO DE EXCLUSÃO       │                                       │
│  │ • É grupo/comunidade?    │──SIM──▶ PULA                         │
│  │ • Está na lista negra?   │──SIM──▶ PULA                         │
│  │ • É o número próprio?    │──SIM──▶ PULA                         │
│  │ • Já foi processado?     │──SIM──▶ PULA                         │
│  │ • Limite MAX atingido?   │──SIM──▶ ENCERRA                      │
│  └──────────┬───────────────┘                                       │
│             ▼                                                       │
│  ┌──────────────────────────┐                                       │
│  │ DECISÃO DE CAMINHO       │                                       │
│  │ Título = número puro?    │──SIM──▶ [CAMINHO 1A] salva direto    │
│  │ Nome contém auto-lead?   │──SIM──▶ [CAMINHO 1B] extrai painel   │
│  │ Contato salvo comum?     │──SIM──▶ [CAMINHO 2] análise msgs     │
│  └──────────────────────────┘                                       │
│                                                                     │
│  Scroll lateral ─▶ Novas conversas ─▶ Repetir                      │
│  3 tentativas sem progresso ─▶ FIM                                  │
└─────────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RELATÓRIO FINAL                                  │
│  Processados • Leads novos • Taxa de conversão • Velocidade        │
│  Tempo total • Distribuição por DDD geográfico                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Condições de Pulo e Exclusões Primárias

Antes de avaliar qualquer conversa, o contato é **sumariamente descartado** se atender a qualquer um destes critérios (avaliados em sequência):

| #  | Critério                    | Detecção                                                                 | Ação     |
|----|-----------------------------|--------------------------------------------------------------------------|----------|
| 1  | Grupo ou Comunidade         | Presença de `span[@data-testid='default-group\|default-community']`      | Pula     |
| 2  | Lista Negra (`NOMES_IGNORAR`) | Nome contém substring da lista (case-insensitive)                       | Pula     |
| 3  | Número Próprio              | Título resolve para `NUMERO_PROPRIO` via `titulo_e_numero()`             | Pula     |
| 4  | Já Processado               | Nome presente no `set(processados)` carregado do `progresso.json`        | Pula     |
| 5  | Limite de Teste             | `total > MAX_CONTATOS` quando `MAX_CONTATOS is not None`                 | Encerra  |

### 3.1 Lista Negra Atual

```python
NOMES_IGNORAR = [
    'orlangia',             # Filial / unidade diferente
    'ana mkt',              # Equipe interna de marketing
    'vivi pimentel',        # Colaboradora interna
    'clinica de n.c',       # Contato institucional
    'yasmin orlangia'       # Colaboradora da filial
]
```

> **Regra:** A comparação é `substring in nome.lower()` — ou seja, "Ana Mkt Digital" também seria filtrado.

---

## 4. Caminho 1: Filtro Rápido — Auto-Lead

Contatos marcados como Auto-Lead **poupam tempo** ao pular completamente a análise de mensagens. A premissa de negócio é: se o contato não foi nem salvo na agenda, ou possui nome de tag de anúncio, ele é tráfego frio e naturalmente um lead não convertido.

### 4.1 Caminho 1A — Número Não Salvo (≈ 0.1s por contato)

- **Condição:** O título da conversa é composto exclusivamente por dígitos (≥ 10 dígitos).
- **Ação:** Extrai o número diretamente do título, sem clicar na conversa.
- **Custo:** Nenhuma interação com o DOM além da leitura do painel lateral.

### 4.2 Caminho 1B — Nome de Anúncio (≈ 2s por contato)

- **Condição:** O título contém uma das palavras em `NOMES_AUTO_LEAD`: `anúncio`, `anuncio`, `ads`.
- **Ação:** Clica na conversa → ignora leitura de mensagens → abre diretamente "Dados do Contato" (drawer lateral) → extrai o número por RegExp → fecha o drawer com `ESC`.

```python
NOMES_AUTO_LEAD = ['anúncio', 'anuncio', 'ads']
```

---

## 5. Caminho 2: Análise Aprofundada — Contatos Salvos

Se o contato é um usuário regular salvo na agenda, a conversa é aberta e o **conteúdo das mensagens** determina seu destino.

### 5.1 Passo 1 — Leitura Imediata (Tela Visível)

Duas verificações ocorrem **simultaneamente** sobre o conteúdo visível:

#### Exclusão (qualquer remetente)
Lê-se **todo o texto visível** (`main.text`) procurando por `TERMOS_EXCLUSAO`. Se encontrado, significa que o lead **já converteu** (agendou, pagou, confirmou) → **descarte imediato**.

```python
TERMOS_EXCLUSAO = [
    'agendada com sucesso', 'agendado com sucesso',
    'agendada', 'agendado', 'comprovante',
    'transferência', 'pagamento',
    'passando para lembrar', 'passando pra lembrar',
    'lembrar do seu atendimento', 'confirmado', 'confirmada'
]
```

> **Diferencial**: Os termos de exclusão são buscados em **todas as mensagens** (tanto enviadas quanto recebidas), porque tanto a clínica quanto o cliente podem usar essas palavras como evidência de conversão.

#### Inclusão (somente mensagens do cliente)
Verifica **exclusivamente as mensagens recebidas** (`div.message-in`) procurando por `TODOS_OS_TERMOS`. A restrição a `message-in` impede falsos positivos de templates/mensagens automáticas da clínica.

```python
TODOS_OS_TERMOS = [
    # Saudações de anúncio e interesse
    'ola eu gostaria de saber sobre o procedimento cridefine',
    'essas fotos mostram bem porque a nossa criodefine',
    'essas fotos mostram bem',
    'que bom ter você aqui',
    'queria saber como agendo',
    'como funciona exatamente',
    'valor', 'preço', 'criodefine', 'crio', 'instagram',
    'consulta', 'avaliação', 'diastase', 'agendar', 'resultados',
    # Opções de botão (respostas pré-configuradas do WhatsApp)
    'tenho uma duvida especifica',
    'quero agendar minha consulta',
    'quero agendar minha avaliação',
    'como funciona o tratamento',
]
```

### 5.2 Passo 2 — Rolagem de Histórico (Scroll Interno)

Se **nenhuma** evidência clara (nem exclusão, nem inclusão) for encontrada na tela visível:

1. O robô executa até **20 `PAGE_UP`** (`SCROLLS_INTERNOS = 20`) na conversa.
2. Cada scroll aguarda o spinner de loading sumir (`progressbar` / `msg-loading`).
3. Verifica se o `scrollTop` mudou — se parado por 1 iteração, atingiu o topo do histórico.
4. Repete a análise de exclusão/inclusão sobre o conteúdo expandido.

### 5.3 Matriz de Decisão Final

| Exclusão encontrada? | Inclusão encontrada? | Resultado                        |
|-----------------------|----------------------|----------------------------------|
| ✅ SIM                | (irrelevante)        | 🚫 Descartado — já é cliente    |
| ❌ NÃO                | ✅ SIM               | ✅ LEAD — extrair número        |
| ❌ NÃO                | ❌ NÃO               | ❌ Sem match — pula             |

> **Exclusão sempre tem prioridade.** Um contato que demonstrou interesse mas depois agendou é descartado corretamente.

---

## 6. Extração e Tratamento do Número de Telefone

Quando o script determina que a conversa atende aos critérios de lead:

### 6.1 Pipeline de Extração

1. **Abertura do Drawer:** Clica no header do contato (`div[@role='button']`, `img`, ou `span[@dir='auto']`).
2. **Localização do Drawer:** Tenta múltiplos seletores em cascata de especificidade:
   - `chat-info-drawer` → `contact-info-drawer` → qualquer `drawer` → `section`
   - **Fallback:** subtrai `main.text` e `pane-side.text` do `body.text` (o resíduo é o drawer).
3. **Extração RegExp:** Aplica o padrão `\+?\d{2,3}\s?\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4}` sobre o texto do drawer.
4. **Fechamento:** Envia `ESC` ao body para fechar o painel.

### 6.2 Normalização do Número

```
Entrada bruta       → Regex strip     → DDI check      → Validação
"+55 (21) 99453-8190" → "5521994538190" → já tem "55"  → len ≥ 12 ✅
"(21) 99453-8190"     → "21994538190"   → add "55"      → len ≥ 12 ✅
"9945-3819"           → "99453819"      → add "55"      → len < 12 ❌
```

### 6.3 Validações Pós-Extração

- Comprimento mínimo de **12 dígitos** (DDI + DDD + número).
- Não pode ser igual ao `NUMERO_PROPRIO`.
- Deduplicação contra o `set(leads)` em memória.

---

## 7. Persistência de Dados

### 7.1 CSV Incremental (`leads_remarketing.csv`)

- **Formato:** Coluna única `Phone`, sem formatação, apenas dígitos com DDI.
- **Escrita:** Append O(1) via `append_csv()` a cada lead capturado — sem recarregar o arquivo.
- **Safety net:** No encerramento (`finally`), `salvar_csv_completo()` reescreve o CSV inteiro ordenado como última garantia.

### 7.2 Checkpoint de Continuidade (`progresso.json`)

```json
{
  "processados": ["Nome 1", "Nome 2", ...],
  "leads": ["5521999999999", "5511988888888", ...]
}
```

- **Intervalo de salvamento:** A cada **20 contatos** processados e a cada scroll lateral.
- **Retomada:** Na inicialização, carrega ambos os sets e filtra contatos já processados.
- **Resiliência:** Quedas de internet, `Ctrl+C`, crash do Chrome, ou OOM não invalidam o progresso.

---

## 8. Gestão de Sessão do Chrome

### 8.1 Perfil Clonado (`chrome_profile_robo/`)

O script **nunca** opera diretamente sobre o perfil nativo do Chrome. No primeiro run, ele clona `~/.config/google-chrome-unstable/Default` para a pasta local `chrome_profile_robo/`, ignorando locks e caches desnecessários:

```
Ignorados: SingletonLock, SingletonSocket, SingletonCookie,
           lockfile, LOCK, Cache, Code Cache, GPUCache,
           Service Worker, DawnCache, GrShaderCache
```

**Por quê:** Evita conflitos de sessão com o Chrome pessoal e preserva os cookies de login do WhatsApp.

### 8.2 Flags do Chrome

| Flag                          | Motivação                                         |
|-------------------------------|---------------------------------------------------|
| `--user-data-dir`             | Usa o perfil clonado                              |
| `--disable-dev-shm-usage`    | Evita crash em containers/VMs com pouca `/dev/shm`|
| `--no-sandbox`                | Necessário em alguns ambientes Linux               |
| `--remote-allow-origins=*`   | Evita erros de CORS no WebDriver                  |
| `--disable-gpu`               | Estabilidade em servidores headless               |
| `excludeSwitches: enable-automation` | Remove banner "Chrome is controlled by..."  |

---

## 9. Reconhecimento de Fim de Execução

O script **não conhece** a quantidade total de contatos com antecedência. O fim é detectado organicamente:

1. Após processar todos os contatos visíveis, o script rola o painel lateral (`pane-side`) um bloco (`clientHeight`) para baixo.
2. Compara o novo `scrollTop` com `scrollHeight`.
3. Se `scrollTop + clientHeight >= scrollHeight` por **3 iterações consecutivas**, a lista acabou.
4. Dispara o relatório final com métricas.

### 9.1 Métricas do Relatório Final

- **Processados:** Total de contatos visitados
- **Leads novos:** Capturados nesta sessão (delta)
- **Total leads:** Acumulado incluindo sessões anteriores
- **Taxa de conversão:** `leads / processados × 100`
- **Velocidade:** `tempo_total / processados` (segundos por contato)
- **Tempo total:** Duração da execução (`Xmin Ys`)
- **Distribuição por DDD:** Top 10 DDDs geográficos (posições `[2:4]` do número)

---

## 10. Tratamento de Erros e Resiliência

| Cenário                          | Comportamento                                                  |
|----------------------------------|----------------------------------------------------------------|
| `StaleElementReferenceException` | Loga o erro truncado e continua para o próximo contato          |
| Timeout ao abrir conversa         | Loga e pula o contato (4s de timeout no `#main`)               |
| Erro no scroll interno            | Loga e retorna `False`, processamento continua                  |
| Erro na extração do painel        | Loga, tenta fechar o drawer com `ESC`, retorna `None`          |
| `KeyboardInterrupt` (Ctrl+C)     | Salva progresso + CSV antes de encerrar                         |
| Crash / Kill do processo          | Retomável pelo `progresso.json` salvo a cada 20 contatos       |

---

## 11. Tempos e Delays Operacionais

Os delays servem para **evitar detecção de bot** e **aguardar renderizações** da interface do WhatsApp.

| Função         | Range          | Uso                                          |
|----------------|----------------|----------------------------------------------|
| `sleep_min()`  | 0.3s – 0.6s   | Micro-interações (clique, foco)              |
| `sleep_load()` | 0.7s – 1.2s   | Carregamento de conversa/drawer              |
| Fixo 0.3s      | 0.3s           | Foco no campo de texto antes de PageUp       |
| Fixo 0.4s      | 0.4s           | Intervalo entre scrolls internos             |
| Fixo 0.5s      | 0.5s           | Aguarda mensagens após scroll completo       |
| Fixo 0.8s      | 0.8s           | Espera drawer abrir completamente            |
| Fixo 1.0s      | 1.0s           | Pausa pós-refresh da página                  |

---

## 12. Glossário

| Termo           | Definição no Contexto                                                    |
|-----------------|--------------------------------------------------------------------------|
| **Lead**        | Contato que demonstrou interesse mas ainda não agendou/pagou             |
| **Auto-Lead**   | Contato filtrado sem análise de mensagens (número puro ou nome de ad)    |
| **Drawer**      | Painel lateral direito do WhatsApp ("Dados do contato")                  |
| **pane-side**   | Div do painel lateral esquerdo (lista de conversas)                      |
| **message-in**  | Classe CSS das mensagens recebidas pelo WhatsApp (do cliente)            |
| **message-out** | Classe CSS das mensagens enviadas (da clínica)                           |
| **Scroll Interno** | Rolagem para cima dentro de uma conversa individual                   |
| **Scroll Lateral** | Rolagem para baixo no painel de lista de conversas                    |
| **Breaking Change** | Mudança na UI do WhatsApp que invalida seletores XPath/CSS           |
| **Progresso**   | Estado salvo em JSON para permitir retomada após interrupção             |
| **Criodefine**  | Procedimento estético — produto principal da clínica                     |

---

## 13. Regras de Evolução e Roadmap

> ⚠️ **Evolução planejada:** Migração da lógica de filtro baseada em texto (`TODOS_OS_TERMOS` / `TERMOS_EXCLUSAO`) para **labels/etiquetas do WhatsApp** (ex: "Lead Anúncio", "Agendada", "Consulta Paga"). Isso tornará a filtragem significativamente mais rápida e precisa, eliminando a necessidade de scroll de histórico na maioria dos casos.

### Regras para Contribuidores (Agentes de IA ou Humanos)

1. **Nunca modifique** `NUMERO_PROPRIO` sem confirmar com o operador.
2. **Sempre teste** alterações de XPath/CSS com `MAX_CONTATOS = 10` antes de submeter.
3. **Documente** novos termos adicionados a `TODOS_OS_TERMOS` ou `TERMOS_EXCLUSAO` com comentário explicando o _porquê_.
4. **Respeite a hierarquia exclusão > inclusão** — nunca inverta a lógica de prioridade.
5. **Qualquer novo arquivo gerado** com dados pessoais deve ser adicionado ao `.gitignore` imediatamente.
6. **Consulte o `/git-workflow`** e o `/versioning-workflow`** antes de abrir qualquer branch ou PR.
