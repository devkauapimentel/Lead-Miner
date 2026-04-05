---
description: Regras e padrão de ramificação adotado na extração (Git Flow)
---

# Git Workflow do Projeto

Este projeto de extração com Selenium precisa de um modelo tático de ramificação que garanta **estabilidade máxima**. A escolha pelo Git Flow como regra universal se deve à propensão do projeto de sofrer **breaking changes forçadas pela Meta** — quando o WhatsApp Web altera sua UI, todos os seletores XPath/CSS podem quebrar sem aviso.

---

## 1. Branches Principais (Permanentes)

Estas branches **nunca são deletadas** e representam os dois ambientes do projeto:

### `main` — Produção

- Reflete **estritamente** o ambiente em operação real.
- Quando a ferramenta é acionada para extração produtiva, ela roda a partir daqui.
- **Nenhum commit direto** é permitido nesta branch.
- Recebe merges apenas de `release/*` (via PR aprovado) ou `hotfix/*` (emergencial).

### `develop` — Homologação

- É a **espinha dorsal** do desenvolvimento contínuo.
- Onde nascem e são mescladas todas as aprovações, refatorações e atualizações de dependências.
- Testes extensivos do Selenium ocorrem aqui antes de qualquer promoção a release.
- **Origem** de todas as branches `feature/*` e `bugfix/*`.

```
  main ──────────────●──────────────●──────────── (somente releases e hotfixes)
                    ╱              ╱
  develop ────●────●────●────●────●────●──────── (desenvolvimento ativo)
             ╱         ╱         ╱
  feature/  ●─────────●        ╱
  bugfix/              ●──────●
```

---

## 2. Branches Secundárias (Efêmeras)

Criadas sob demanda e **deletadas após o merge**.

### 2.1 `feature/` — Novos Módulos e Adições

**Quando usar:** Adicionar funcionalidade nova, como suporte a banco de dados, modo headless, filtro por labels do WhatsApp, etc.

**Origem:** `develop`
**Destino:** `develop` (via Pull Request)

```bash
# Criar branch
git checkout develop
git pull origin develop
git checkout -b feature/filtro-por-labels

# ... desenvolver e testar com MAX_CONTATOS = 10 ...

# Submeter PR
git push origin feature/filtro-por-labels
# Abrir Pull Request: feature/filtro-por-labels → develop
```

**Convenções de nomenclatura:**
- `feature/suporte-headless`
- `feature/integracao-supabase`
- `feature/filtro-por-labels`
- `feature/exportar-csv-avancado`

---

### 2.2 `bugfix/` — Manutenções Corriqueiras

**Quando usar:** Corrigir bugs que não impedem a produção mas afetam a qualidade — como RegExp imprecisa, loop infinito de scroll, falso positivo em filtro de termos.

**Origem:** `develop`
**Destino:** `develop` (via Pull Request)

```bash
git checkout develop
git pull origin develop
git checkout -b bugfix/regex-extrai-numero-curto
```

**Convenções de nomenclatura:**
- `bugfix/scroll-infinito-sem-parada`
- `bugfix/falso-positivo-exclusao`
- `bugfix/timeout-drawer-lento`
- `bugfix/duplicata-csv`

---

### 2.3 `hotfix/` — Ações Emergenciais de Bloqueio

**Quando usar:** A produção **quebrou**. O cenário mais comum: o WhatsApp mudou a UI na calada da noite e todos os XPath/CSS seletores pararam de funcionar (Breaking Change de UI).

**Origem:** `main` ⚠️ (NÃO é `develop`)
**Destino:** `main` (merge direto e imediato) **E** `develop` (sincronia obrigatória)

```bash
# 1. Criar a branch a partir de MAIN (produção quebrada)
git checkout main
git pull origin main
git checkout -b hotfix/redefinicao-dom-whatsapp-2026-04

# 2. Corrigir paliativamente os seletores quebrarados
#    Foco: restaurar funcionalidade mínima, NÃO refatorar

# 3. Merge emergencial em main (o mais rápido possível)
git checkout main
git merge hotfix/redefinicao-dom-whatsapp-2026-04
git push origin main

# 4. OBRIGATÓRIO: retroalimentar develop para sincronia
git checkout develop
git merge hotfix/redefinicao-dom-whatsapp-2026-04
git push origin develop

# 5. Deletar a branch hotfix
git branch -d hotfix/redefinicao-dom-whatsapp-2026-04
```

> ⚠️ **Regra de Ouro:** Hotfixes são **paliativos**. Após estabilizar a produção, abra uma `feature/` ou `bugfix/` em `develop` para refinamento técnico da correção.

**Convenções de nomenclatura:**
- `hotfix/redefinicao-dom-whatsapp-YYYY-MM`
- `hotfix/sessao-cookies-expirados`
- `hotfix/chromedriver-incompativel`

---

### 2.4 `release/` — Promoção para Produção

**Quando usar:** O código em `develop` está estável e passou por testes extensivos (20+ contatos processados sem erros). Pronto para ir para produção.

**Origem:** `develop`
**Destino:** `main` (via PR com tag de versão) **E** retroalimentar `develop`

```bash
# Criar branch de release
git checkout develop
git pull origin develop
git checkout -b release/v1.2.0

# Ajustes finais: bumpar versão no README, revisar logs
# Testar uma última vez com MAX_CONTATOS = 20

# Merge em main com tag
git checkout main
git merge release/v1.2.0
git tag -a v1.2.0 -m "Versão 1.2.0 - Filtro por labels"
git push origin main --tags

# Retroalimentar develop
git checkout develop
git merge release/v1.2.0
git push origin develop
```

---

## 3. Regras de Commit

### 3.1 Formato de Mensagem

Usar **Conventional Commits** em português:

```
<tipo>(<escopo>): <descrição breve>

[corpo opcional — contexto técnico]
```

**Tipos permitidos:**

| Tipo       | Uso                                                      |
|------------|----------------------------------------------------------|
| `feat`     | Nova funcionalidade ou módulo                            |
| `fix`      | Correção de bug                                          |
| `refactor` | Reestruturação sem alterar comportamento                 |
| `docs`     | Apenas documentação (README, agents.md, workflows)       |
| `style`    | Formatação, espaçamento (sem lógica alterada)            |
| `test`     | Adição ou alteração de testes                            |
| `chore`    | Tarefas de manutenção (deps, gitignore, configs)         |
| `hotfix`   | Correção emergencial de produção                         |

**Exemplos:**
```
feat(scraper): adicionar filtro por labels do whatsapp
fix(extração): corrigir regex que truncava DDDs com 3 dígitos
hotfix(xpath): atualizar seletores após breaking change da meta
docs(agents): documentar lógica de auto-lead no agents.md
chore(deps): atualizar selenium de 4.18.1 para 4.20.0
```

### 3.2 Regras de Integridade

- **Nunca** faça `git push --force` em `main` ou `develop`.
- **Sempre** faça `git pull` antes de iniciar qualquer branch nova.
- **Squash** commits de trabalho em progresso antes do merge para `develop`.
- **Resolva** conflitos **localmente** antes de subir o PR.

---

## 4. Checklist Pré-Merge

Antes de abrir qualquer Pull Request, confirme:

- [ ] `git status` limpo — nenhum arquivo sensível tracked (ver `/versioning-workflow`).
- [ ] Testou com `MAX_CONTATOS = 10` localmente sem erros de exceção.
- [ ] Os seletores XPath/CSS estão funcionando na versão atual do WhatsApp Web.
- [ ] O `requirements.txt` está atualizado se alguma dependência mudou.
- [ ] O `agents.md` foi atualizado se alguma regra de negócio mudou.
- [ ] A mensagem de commit segue o padrão Conventional Commits.
- [ ] Nenhum dado pessoal (CSV, log, JSON de progresso, perfil Chrome) está no commit.
