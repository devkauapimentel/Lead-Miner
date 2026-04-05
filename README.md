# 🤖 Pegador de Contato v2.0 — WhatsApp Lead Scraper

Extrator automático de leads do WhatsApp Business Web para remarketing.
Filtra contatos por **Etiquetas (Labels)** do WhatsApp e salva os números em CSV.

> **v2.0** — Agora com GUI visual, configuração por arquivo, presets por tipo de negócio, e filtragem por etiquetas do WhatsApp Business.

---

## 🚀 Como Usar

### 1. Primeira vez (configuração)

```bash
cd ~/Documents/01\ -\ Projects/Pegador-De-Contato

# Criar ambiente virtual e instalar dependências
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. Abrir a Interface Visual (GUI)

```bash
# Fechar Chrome antes!
pkill -f "chrome" 2>/dev/null; sleep 2

venv/bin/python main.py
```

A janela vai abrir com 2 abas:
1. **⚙️ Configuração** — Selecione suas etiquetas de inclusão/exclusão, dados do negócio, preset
2. **🚀 Execução** — Clique em INICIAR e acompanhe em tempo real

### 3. Usar pelo Terminal (CLI)

```bash
venv/bin/python main.py --cli
```

Menu interativo com setas e espaço para selecionar etiquetas.

### 4. Retomar de onde parou

Basta rodar novamente sem limpar os dados:
```bash
venv/bin/python main.py
```

### 5. Recomeçar do zero

Na GUI: clique em "🗑️ Limpar Progresso".

Ou manualmente:
```bash
rm -f data/progresso.json data/leads_remarketing.csv data/scraper.log
```

---

## 📁 Estrutura do Projeto

```
Pegador-De-Contato/
├── main.py                  # Ponto de entrada (GUI ou --cli)
├── config.json              # Suas regras de negócio
│
├── core/                    # Lógica de negócio
│   ├── config_manager.py    # Gerenciador de configuração
│   ├── engine.py            # Motor de extração (Selenium)
│   ├── facade.py            # Fachada (ponto de entrada único)
│   └── filters.py           # Estratégias de filtragem
│
├── infra/                   # Infraestrutura
│   ├── chrome.py            # Gerenciador do Chrome
│   ├── exporters.py         # Exportador CSV
│   ├── logger.py            # Logger dual
│   └── phone_utils.py       # Utilitários de telefone
│
├── ui/                      # Interfaces
│   ├── gui.py               # Interface visual (CustomTkinter)
│   └── cli.py               # Interface terminal (questionary)
│
├── presets/                  # Configurações por tipo de negócio
│   ├── clinica_estetica.json
│   ├── dentista.json
│   ├── advogado.json
│   └── imobiliaria.json
│
├── data/                    # Dados de execução (gerados)
│   ├── leads_remarketing.csv
│   ├── progresso.json
│   └── scraper.log
│
└── whatsapp_lead_scraper_legacy.py  # Script original v1.0
```

---

## ⚙️ Configuração

Edite via GUI ou diretamente no `config.json`:

```json
{
  "business_name": "Clínica Dra. Rosângela",
  "own_number": "5521994538190",
  "labels": {
    "include": ["Lead Anuncio", "Repescagem"],
    "exclude": ["Agendada", "Consulta paga"]
  },
  "filter_mode": "labels"
}
```

### Presets

Carregar configuração pronta:
- `clinica_estetica` — Clínicas de estética
- `dentista` — Consultórios odontológicos
- `advogado` — Escritórios de advocacia
- `imobiliaria` — Corretores de imóveis

---

## 🔍 Como Funciona a Filtragem

```
Contato na lista lateral
  └─ É Grupo? → PULA
  └─ Na Lista Negra? → PULA
  └─ Número Próprio? → PULA
  └─ Já Processado? → PULA
  └─ Abre 'Dados do Contato'
     └─ Lê Etiquetas
        └─ Tem tag de EXCLUSÃO? (Agendada, Consulta paga) → PULA 🚫
        └─ Tem tag de INCLUSÃO? (Lead Anuncio, Repescagem) → EXTRAI ✅
        └─ Nenhuma tag relevante → PULA ❌
```

---

## 📊 Relatório Final

Ao terminar, exibe no log e na GUI:
- Processados, Leads novos, Taxa de conversão
- Velocidade por contato, Tempo total
- Distribuição por DDD

---

## ❓ Problemas Comuns

### "Chrome instance exited"
→ Feche todas as janelas do Chrome antes.

### "Sessão do WhatsApp expirou / QR Code"
→ Delete `chrome_profile_robo/` e rode novamente.

### "Nenhuma etiqueta selecionada"
→ Configure na aba "⚙️ Configuração" da GUI.

### "customtkinter não instalado"
→ Rode: `venv/bin/pip install -r requirements.txt`
