---
description: Como seguir as regras principais de isolamento, ciclo de teste e segurança (Software Workflow)
---

# Regras de Ciclo de Vida do Software (Workflow)

Este fluxo documenta como iniciar alterações, testá-las corretamente, manter a estabilidade do extrator frente às atualizações do WhatsApp e garantir conformidade de segurança (LGPD).

---

## 1. Isolamento de Dependências — Obrigatório

Todas as execuções — desenvolvimento, teste e produção — devem acontecer dentro do **Ambiente Virtual** (`venv`). Isso evita poluição do sistema, garante reprodutibilidade e mantém o versionamento de dependências sob controle.

### 1.1 Ativação do Ambiente

```bash
# Ativar o venv
source venv/bin/activate

# Confirmar que está no ambiente correto
which python
# Esperado: .../Pegador-De-Contato/venv/bin/python
```

### 1.2 Instalação e Atualização de Dependências

```bash
# Instalar dependências a partir do requirements.txt
pip install -r requirements.txt

# Se adicionar uma nova dependência, congele após instalar:
pip install <nome-do-pacote>
pip freeze | grep -i <nome-do-pacote> >> requirements.txt
```

### 1.3 Criação do Ambiente (Primeiro Setup)

```bash
# Criar venv (apenas na primeira vez)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> ⚠️ **Regra:** Nunca execute `pip install` fora do venv. Se o prompt não mostrar `(venv)`, o ambiente **não está ativo**.

---

## 2. Validação Contínua — Ciclo de Testes

Alterações neste projeto afetam diretamente **seletores XPath/CSS** e **manipulações do DOM do WhatsApp** (Selenium). A página web do WhatsApp altera estruturas de mensagens, contatos e *Drawers* **sem aviso prévio**.

### 2.1 Regra de Ouro

> **Nunca declarar como finalizado** nenhum script baseado em seletores sem validação visual local. Seletores antigos podem ter sido silenciosamente invalidados pela Meta.

### 2.2 Procedimento de Teste Local

**Antes de qualquer commit ou merge:**

```bash
# 1. Ativar o ambiente
source venv/bin/activate

# 2. Fechar TODAS as instâncias do Chrome (obrigatório)
pkill -f "chrome" 2>/dev/null; sleep 2

# 3. Configurar modo de teste — editar no topo do script:
#    MAX_CONTATOS = 10

# 4. Executar e observar VISUALMENTE
python whatsapp_lead_scraper.py
```

### 2.3 Checklist de Validação Visual

Durante a execução de teste, observe e confirme:

| Item                                  | O que verificar                                                    |
|---------------------------------------|------------------------------------------------------------------  |
| **Login do WhatsApp**                 | Sessão abriu automaticamente, sem QR Code                          |
| **Scroll lateral**                    | Painel esquerdo rola suavemente, novos contatos aparecem           |
| **Abertura de conversa**              | Clique no contato carrega o `#main` sem timeout                    |
| **Leitura de mensagens**              | Texto é capturado sem erros de `StaleElementReference`             |
| **Scroll interno**                    | Page Up funciona, spinner de loading some corretamente             |
| **Abertura do Drawer**                | Clique no header abre painel lateral direito                       |
| **Extração de número**                | RegExp captura o telefone formatado corretamente                   |
| **Fechamento do Drawer**              | `ESC` fecha o painel sem travar a interface                        |
| **CSV atualizado**                    | `leads_remarketing.csv` recebe novos registros em tempo real       |
| **Sem exceções no console**           | Terminal mostra apenas logs normais, sem stack traces               |

### 2.4 Teste de Retomada

Valide que a retomada de progresso funciona:

```bash
# Executar com limite baixo
# (editar MAX_CONTATOS = 5 no script)
python whatsapp_lead_scraper.py

# Interromper com Ctrl+C (simula queda)
# Verificar que progresso.json foi salvo
cat progresso.json | python -m json.tool | head -5

# Reexecutar — deve retomar e não reprocessar os mesmos
python whatsapp_lead_scraper.py
```

### 2.5 Teste de Regressão de Seletores

Quando houver suspeita de breaking change do WhatsApp:

```bash
# Testar especificamente a extração de drawer
# 1. Abrir o WhatsApp Web manualmente
# 2. Inspecionar os seletores no DevTools do Chrome:
#    - div[@data-testid='chat-info-drawer']
#    - div[@data-testid='contact-info-drawer']
#    - div[@role='row']
#    - div.message-in
#    - span[@data-testid='default-group']
# 3. Se mudaram, abrir hotfix/ (ver /git-workflow)
```

---

## 3. Segurança Rígida — LGPD e Gitignore

### 3.1 Arquivos Sensíveis — NUNCA Versionar

Estes arquivos contêm **dados pessoais (LGPD)** ou **sessões autenticadas** e **jamais** devem entrar no controle de versão:

| Arquivo / Diretório       | Classificação   | Risco se vazado                                      |
|---------------------------|-----------------|------------------------------------------------------|
| `leads_remarketing.csv`   | 🔴 LGPD         | Vazamento de telefones pessoais de leads              |
| `scraper.log`             | 🟡 Sensível     | Pode conter nomes e números de contatos no log        |
| `progresso.json`          | 🟡 Sensível     | Contém nomes completos de contatos processados        |
| `chrome_profile_robo/`    | 🔴 CRÍTICO      | Cookies e sessão do WhatsApp — acesso total à conta   |

### 3.2 Verificação Pré-Commit Obrigatória

**Sempre** execute antes de qualquer `git add`:

```bash
# Verificar status — NENHUM arquivo sensível deve aparecer
git status

# Se algum arquivo sensível aparecer staged/untracked:
# → NÃO faça git add .
# → Adicione apenas os arquivos seguros individualmente:
git add whatsapp_lead_scraper.py
git add requirements.txt
git add README.md
git add agents.md
```

### 3.3 Garantia do `.gitignore`

Estes padrões **devem** estar no `.gitignore` do projeto:

```gitignore
# Dados pessoais (LGPD)
leads_remarketing.csv
progresso.json
scraper.log

# Sessão autenticada do navegador
chrome_profile_robo/

# Ambiente virtual Python
venv/

# Caches e artefatos
__pycache__/
*.pyc
.pytest_cache/

# IDE
.vscode/
.idea/
```

### 3.4 Auditoria Periódica

Periodicamente, confirme que o `.gitignore` está ativo e que nenhum arquivo sensível está rastreado no histórico:

```bash
# Listar todos os arquivos tracked pelo git
git ls-files

# Confirmar que NENHUM destes aparece:
# ❌ leads_remarketing.csv
# ❌ progresso.json
# ❌ scraper.log
# ❌ chrome_profile_robo/

# Se algum já foi commitado no passado, remover do tracking:
git rm --cached leads_remarketing.csv
git rm --cached progresso.json
git rm --cached scraper.log
git rm -r --cached chrome_profile_robo/
git commit -m "chore(segurança): remover arquivos sensíveis do tracking"
```

---

## 4. Fluxo Completo de Desenvolvimento

Um ciclo completo de alteração segue este caminho:

```
┌──────────────────────────────────────────────────────────────────┐
│  1. PREPARAR                                                     │
│     source venv/bin/activate                                     │
│     git checkout develop && git pull origin develop               │
│     git checkout -b feature/minha-mudança                        │
├──────────────────────────────────────────────────────────────────┤
│  2. DESENVOLVER                                                  │
│     Editar whatsapp_lead_scraper.py                              │
│     Atualizar agents.md se regras de negócio mudaram             │
├──────────────────────────────────────────────────────────────────┤
│  3. TESTAR                                                       │
│     MAX_CONTATOS = 10                                            │
│     pkill -f chrome; python whatsapp_lead_scraper.py             │
│     Observar visualmente o checklist da Seção 2.3                │
├──────────────────────────────────────────────────────────────────┤
│  4. VALIDAR SEGURANÇA                                            │
│     git status (confirmar zero arquivos sensíveis)               │
│     git diff (revisar alterações)                                │
├──────────────────────────────────────────────────────────────────┤
│  5. COMMIT E PR                                                  │
│     git add <arquivos-seguros>                                   │
│     git commit -m "feat(scraper): descrição clara"               │
│     git push origin feature/minha-mudança                        │
│     Abrir PR → develop                                           │
├──────────────────────────────────────────────────────────────────┤
│  6. PÓS-MERGE                                                   │
│     Restaurar MAX_CONTATOS = None no script produtivo            │
│     Limpar: rm -f progresso.json leads_remarketing.csv           │
│     Deletar branch: git branch -d feature/minha-mudança          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Gestão de Dependências

### 5.1 Atualização do Selenium

O Selenium e o ChromeDriver devem ser mantidos compatíveis. Ao atualizar:

```bash
source venv/bin/activate

# Verificar versão atual
pip show selenium

# Atualizar
pip install --upgrade selenium

# Atualizar requirements.txt
pip freeze | grep selenium > requirements.txt

# TESTAR IMEDIATAMENTE com MAX_CONTATOS = 10
python whatsapp_lead_scraper.py
```

### 5.2 Compatibilidade Chrome ↔ ChromeDriver

| Chrome Channel    | Binário                                          |
|-------------------|--------------------------------------------------|
| Unstable (Dev)    | `/opt/google/chrome-unstable/google-chrome-unstable` |
| Stable (futuro)   | `/opt/google/chrome/google-chrome`               |

> O Selenium 4.18+ gerencia o ChromeDriver automaticamente via `selenium-manager`. Se houver incompatibilidade, atualize o Selenium primeiro.

---

## 6. Procedimento de Recuperação de Desastres

### 6.1 WhatsApp Pediu QR Code Novamente

```bash
# Deletar perfil clonado (sessão expirada)
rm -rf chrome_profile_robo/

# Abrir o Chrome real, fazer login no WhatsApp Web
# Fechar o Chrome
# Executar o script (ele vai clonar o perfil novo)
python whatsapp_lead_scraper.py
```

### 6.2 CSV Corrompido ou Perdido

```bash
# O progresso.json contém todos os números capturados
# Reconstruir o CSV a partir dele:
python3 -c "
import json
with open('progresso.json') as f:
    data = json.load(f)
leads = sorted(data.get('leads', []))
with open('leads_remarketing.csv', 'w') as f:
    f.write('Phone\n')
    for lead in leads:
        f.write(lead + '\n')
print(f'CSV reconstruído: {len(leads)} leads')
"
```

### 6.3 Breaking Change da Meta (UI do WhatsApp)

1. **Identificar** quais seletores quebraram (inspecionar DevTools).
2. **Abrir `hotfix/`** a partir de `main` (ver `/git-workflow` Seção 2.3).
3. **Corrigir** paliativamente os XPath/CSS afetados.
4. **Testar** com `MAX_CONTATOS = 10`.
5. **Merge emergencial** em `main`, depois sincronizar `develop`.
6. **Atualizar** `agents.md` se a mudança alterou regras de negócio.
