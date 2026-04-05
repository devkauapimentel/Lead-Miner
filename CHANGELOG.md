# Changelog — Pegador de Contato

Todas as alterações relevantes do projeto são documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e o versionamento adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [Não Lançado] — feature/refactor-v2-labels-gui

### Adicionado
- **Modo Chrome Nativo (Real):** Selenium herda o perfil autêntico do Chrome do usuário com GNOME Keyring, eliminando a necessidade de QR Code recorrente (`infra/chrome.py`).
- **Modo Chrome Clonado (Isolated):** Cópia segura do perfil real para um diretório isolado, preservando Service Worker e IndexedDB do WhatsApp (`infra/chrome.py`).
- **Modo Chrome Zerado (Clean):** Perfil vazio para login com QR Code do zero, voltado a contas secundárias (`infra/chrome.py`).
- **Autoformatação de telefone:** Campo "Meu Número" na GUI formata em tempo real para `+55 (DD) XXXXX-XXXX` (`ui/gui.py`).
- **Seleção de sub-perfis do Chrome:** Campo "Caminho do Perfil" aceita qualquer sub-perfil (Default, Profile 1, etc.) obtido via `chrome://version` (`ui/gui.py`, `infra/chrome.py`).
- **Presets por segmento:** Sistema de presets JSON em `presets/` para configuração rápida por tipo de negócio (`core/config_manager.py`, `ui/gui.py`).
- **Proteção de presets:** Presets não sobrescrevem `own_number` nem as configurações de Chrome do usuário (`ui/gui.py`).

### Corrigido
- **Clone do Service Worker:** Removida exclusão da pasta `Service Worker` no `shutil.copytree`, que causava reset da sessão do WhatsApp no modo Isolado (`infra/chrome.py`).
- **Limpeza de SingletonLock:** Locks residuais (`SingletonLock`, `SingletonSocket`, `SingletonCookie`) são removidos automaticamente ao reaproveitar perfil clonado (`infra/chrome.py`).
- **Scroll da lista lateral:** Corrigido cálculo de scroll que pulava contatos ou não atingia o fim da lista (`core/engine.py`).
- **Menu Offset:** Resolvido bug onde o menu da GUI era deslocado após abrir a aba de Execução e voltar à Configuração (`ui/gui.py`).
- **Botão Parar:** Resolvido delay no flag `running = False` que causava processamento de contatos extras após clicar em Parar (`core/engine.py`, `ui/gui.py`).
- **NameError no collect_config:** Variável `chrome_profile` renomeada corretamente para `self.entry_chrome_profile.get()` (`ui/gui.py`).
- **Import time ausente:** Restaurada a importação de `time` no bloco do Modo Real após refatoração (`infra/chrome.py`).

### Alterado
- **Arquitetura v2.0:** Refatoração completa do monolito `whatsapp_lead_scraper.py` em arquitetura modular com 4 Design Patterns: Strategy, Observer, Facade, Configuration.
- **Estrutura de diretórios:** Separação em `core/` (engine, filters, facade, config), `infra/` (chrome, exporters, logger, phone_utils), `ui/` (gui, cli).
- **Interface dual:** GUI via CustomTkinter + CLI via questionary, acionadas pelo mesmo `main.py`.
- **Filtragem por Labels:** Sistema primário de filtragem agora usa Etiquetas do WhatsApp Business (Labels) em vez de palavras-chave na conversa.

---

## [1.0.0] — 2026-03-XX

### Adicionado
- Monolito `whatsapp_lead_scraper.py` (615 LOC).
- Filtragem por palavras-chave no histórico de mensagens.
- Exportação CSV incremental com `leads_remarketing.csv`.
- Retomada de progresso via `progresso.json`.
- Scroll interno de conversas para carregar histórico.
- Detecção automática de Chrome e ChromeDriver.
- Auto-lead por título numérico (contatos não salvos).
