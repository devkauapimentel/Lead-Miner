# 🤖 Pegador de Contato — WhatsApp Lead Scraper

Extrator automático de leads do WhatsApp Web para remarketing.
Percorre todas as conversas, filtra por palavras-chave de anúncios do Facebook Ads, e salva os números de telefone em CSV.

---

## 🚀 Como Usar

### 1. Primeira vez (configuração)

```bash
cd ~/Documents/Projects/Pegador-De-Contato

# Instalar dependências (uma vez só)
sudo apt install python3.12-venv -y
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 2. Rodar a extração

```bash
# Fechar Chrome, limpar dados anteriores, e iniciar
pkill -f "chrome-unstable" 2>/dev/null; sleep 2
cd ~/Documents/Projects/Pegador-De-Contato
rm -f progresso.json leads_remarketing.csv scraper.log
source venv/bin/activate
python whatsapp_lead_scraper.py
```

> **⚠️ Importante:** Feche TODAS as janelas do Chrome antes de rodar!

O script vai:
1. Abrir o Chrome com sua sessão salva (WhatsApp já logado)
2. Percorrer cada conversa da lista lateral
3. Filtrar por palavras-chave
4. Extrair os números de telefone
5. Salvar em `leads_remarketing.csv`

### 3. Retomar de onde parou

Se o script for interrompido (Ctrl+C, queda de energia, etc.), basta rodar novamente **sem** deletar os arquivos:

```bash
source venv/bin/activate
python whatsapp_lead_scraper.py
```

Ele retoma do último contato processado automaticamente (progresso salvo em `progresso.json`).

### 4. Recomeçar do zero

```bash
rm -f progresso.json leads_remarketing.csv scraper.log
source venv/bin/activate
python whatsapp_lead_scraper.py
```

---

## 📁 Arquivos do Projeto

| Arquivo | Descrição |
|---|---|
| `whatsapp_lead_scraper.py` | Script principal |
| `leads_remarketing.csv` | CSV com os leads extraídos (atualizado em tempo real) |
| `progresso.json` | Progresso da execução (para retomar) |
| `scraper.log` | Log completo com timestamps |
| `chrome_profile_robo/` | Cópia do perfil do Chrome (sessão do WhatsApp) |
| `requirements.txt` | Dependências Python |

---

## ⚙️ Configurações

Edite o topo do arquivo `whatsapp_lead_scraper.py`:

```python
SCROLLS_INTERNOS = 5          # Scrolls para cima em cada conversa
MAX_CONTATOS = None            # None = todos, 10 = teste rápido
NUMERO_PROPRIO = '5521994538190'   # Seu número (excluído dos resultados)
NUMERO_BUSINESS = '5521987642940'  # Número Business (excluído)
```

### Filtros de palavras-chave

```python
TODOS_OS_TERMOS = [
    'criodefine', 'valor', 'preço', 'agendar',
    'consulta', 'avaliação', 'resultados', ...
]
```

Adicione ou remova termos conforme seus anúncios.

---

## 🔍 Como Funciona a Filtragem

```
Contato não salvo (número no título)?
  └─ SIM → É lead novo! Salva o número direto (sem clicar) ⚡
  └─ NÃO → Abre a conversa:
       └─ Palavras-chave nas mensagens visíveis?
            └─ SIM → Abre "Dados do contato" → Extrai número
            └─ NÃO → Scroll para cima (busca saudações antigas)
                 └─ Encontrou? → Extrai número
                 └─ Não? → Pula ❌
```

---

## 📊 Relatório Final

Ao terminar, o script exibe:

```
==================================================
  Processados: 5000
  Leads novos: 847
  Taxa conversão: 16.9%
  Velocidade: 4.2s/contato
  Tempo: 5h 49min

  Por DDD:
    21 (RJ): 612 leads
    11 (SP): 98 leads
==================================================
```

---

## ❓ Problemas Comuns

### "Chrome instance exited"
→ Feche todas as janelas do Chrome antes de rodar.

### "Sessão do WhatsApp expirou / QR Code"
→ Delete a pasta `chrome_profile_robo/` e rode novamente. Na primeira execução, será criada uma nova cópia do seu perfil.

```bash
rm -rf chrome_profile_robo/
```

### "O script parou no meio"
→ Rode novamente sem deletar `progresso.json` — ele retoma de onde parou.

### "Quero ver o que aconteceu durante a noite"
→ Abra o arquivo `scraper.log` — contém o log completo com horários.
