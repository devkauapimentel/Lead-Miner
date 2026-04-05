# Changelog — Lead Miner

Todas as alterações relevantes do projeto são documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e o versionamento adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [2.0.0-beta] — 2026-04-05

### Adicionado
- **Rebranding Oficial:** O projeto agora se chama **Lead Miner**.
- **Novo Logo:** Identidade visual mineradora em emerald green e gold (`assets/logo.png`).
- **Versão Beta:** Lançamento da refatoração v2.0 com suporte a GUI e Labels.
- **Modo Chrome Nativo (Real):** Selenium herda o perfil autêntico do Chrome do usuário com GNOME Keyring (`infra/chrome.py`).
- **Modo Chrome Clonado (Isolated):** Cópia segura do perfil real para um diretório isolado (`infra/chrome.py`).
- **Modo Chrome Zerado (Clean):** Perfil vazio para login com QR Code do zero (`infra/chrome.py`).
- **Presets por segmento:** Sistema de presets JSON em `presets/` para configuração rápida (`core/config_manager.py`).

### Alterado
- **Nome do Projeto:** Transição de "Pegador de Contato" para "Lead Miner".
- **Docstrings e Headers:** Todos os arquivos fonte atualizados com o novo branding.
- **Interface Terminal (CLI):** Novo banner ASCII "LEAD MINER" de alto impacto.

---

## [1.0.0] — 2026-03-XX

### Adicionado
- Projeto original (Pegador de Contato).
- Monolito `whatsapp_lead_scraper.py` (615 LOC).
- Filtragem por palavras-chave no histórico de mensagens.
- Exportação CSV incremental com `leads_remarketing.csv`.
- Retomada de progresso via `progresso.json`.
