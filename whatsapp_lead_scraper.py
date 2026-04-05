import time
import random
import re
import csv
import shutil
import os
import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
)

# =================================================================================
# CONFIGURAÇÕES
# =================================================================================

CHROME_ORIGINAL = os.path.expanduser("~/.config/google-chrome-unstable")
CHROME_ROBO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile_robo")
CHROME_BIN = "/opt/google/chrome-unstable/google-chrome-unstable"
PROGRESSO_ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "progresso.json")
CSV_SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads_remarketing.csv")
LOG_ARQUIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper.log")

# Configura logging dual: terminal + arquivo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_ARQUIVO, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def log(msg):
    """Substitui print() — grava no terminal E no arquivo scraper.log."""
    logging.info(msg)

# Quantas vezes rolar para cima dentro de cada conversa
SCROLLS_INTERNOS = 20

# Limite de contatos (None = sem limite, processar todos)
MAX_CONTATOS = None

# Número da própria conta WhatsApp (excluído dos resultados)
# +55 21 99453-8190
NUMERO_PROPRIO = '5521994538190'

# =================================================================================
# FILTROS
# =================================================================================

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
    # Opções de botão
    'tenho uma duvida especifica',
    'quero agendar minha consulta',
    'quero agendar minha avaliação',
    'como funciona o tratamento',
]

TERMOS_EXCLUSAO = [
    'agendada com sucesso', 'agendado com sucesso',
    'agendada', 'agendado', 'comprovante',
    'transferência', 'pagamento',
    'passando para lembrar', 'passando pra lembrar',
    'lembrar do seu atendimento', 'confirmado', 'confirmada'
]

NOMES_AUTO_LEAD = ['anúncio', 'anuncio', 'ads']

NOMES_IGNORAR = [
    'orlangia', 'ana mkt', 'vivi pimentel',
    'clinica de n.c', 'yasmin orlangia'
]
# =================================================================================
# FUNÇÕES AUXILIARES
# =================================================================================

def copiar_perfil_chrome():
    if os.path.exists(CHROME_ROBO):
        log("[*] Perfil do robô já existe. Reutilizando...\n")
        return
    log("[*] Copiando perfil do Chrome...")
    pasta_origem = os.path.join(CHROME_ORIGINAL, "Default")
    pasta_destino = os.path.join(CHROME_ROBO, "Default")
    if not os.path.exists(pasta_origem):
        log(f"[!] ERRO: {pasta_origem} não encontrada!"); exit(1)
    os.makedirs(CHROME_ROBO, exist_ok=True)
    shutil.copytree(pasta_origem, pasta_destino,
        ignore=shutil.ignore_patterns(
            'SingletonLock','SingletonSocket','SingletonCookie',
            'lockfile','LOCK','Cache','Code Cache','GPUCache',
            'Service Worker','DawnCache','GrShaderCache'),
        dirs_exist_ok=True)
    local_state = os.path.join(CHROME_ORIGINAL, "Local State")
    if os.path.exists(local_state):
        shutil.copy2(local_state, os.path.join(CHROME_ROBO, "Local State"))
    log("[✓] Copiado!\n")


def sleep_min():
    time.sleep(random.uniform(0.3, 0.6))

def sleep_load():
    time.sleep(random.uniform(0.7, 1.2))


def limpar_numero(texto):
    n = re.sub(r'\D', '', texto)
    if n and not n.startswith('55'):
        n = '55' + n
    return n


def titulo_e_numero(titulo):
    """Retorna o número limpo se o título for um telefone, senão None."""
    digitos = re.sub(r'\D', '', titulo)
    if len(digitos) >= 10:
        n = digitos if digitos.startswith('55') else '55' + digitos
        return n if len(n) >= 12 else None
    return None


def atende_criterios(texto):
    t = texto.lower()
    return any(termo in t for termo in TODOS_OS_TERMOS)

def contem_exclusao(texto):
    t = texto.lower()
    return any(termo in t for termo in TERMOS_EXCLUSAO)


def carregar_progresso():
    if os.path.exists(PROGRESSO_ARQUIVO):
        with open(PROGRESSO_ARQUIVO, 'r', encoding='utf-8') as f:
            d = json.load(f)
            return set(d.get("processados", [])), set(d.get("leads", []))
    return set(), set()

def salvar_progresso(processados, leads):
    with open(PROGRESSO_ARQUIVO, 'w', encoding='utf-8') as f:
        json.dump({"processados": list(processados), "leads": list(leads)}, f, ensure_ascii=False)

def inicializar_csv():
    """Cria o CSV com header se ele não existir ou estiver vazio."""
    if not os.path.exists(CSV_SAIDA) or os.path.getsize(CSV_SAIDA) == 0:
        with open(CSV_SAIDA, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['Phone'])


def append_csv(numero):
    """Adiciona UM lead ao final do CSV — O(1) em vez de reescrever tudo."""
    with open(CSV_SAIDA, 'a', newline='', encoding='utf-8') as f:
        csv.writer(f).writerow([numero])


def salvar_csv_completo(leads):
    """Reescreve o CSV inteiro (usado apenas no encerramento como safety net)."""
    with open(CSV_SAIDA, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['Phone'])
        for l in sorted(leads): w.writerow([l])


def scroll_conversa_para_cima(driver, nome_contato):
    """
    Rola a conversa para cima usando Page Up.
    Espera o spinner de mensagens antigas carregar. Para no topo.
    Modificado para focar na caixa de texto e evitar "Element Click Intercepted".
    """
    try:
        main = driver.find_element(By.ID, "main")

        # Foca diretamente na caixa de texto para mandar PageUp em segurança
        caixas_texto = driver.find_elements(By.XPATH, "//div[@contenteditable='true'][@data-tab='10']")
        if caixas_texto:
            elemento_foco = caixas_texto[0]
            elemento_foco.click()
        else:
            elemento_foco = main
            main.click()

        time.sleep(0.3)

        # Pega o scrollTop ANTES para comparar
        scroll_antes = driver.execute_script("""
            var main = document.getElementById('main');
            var divs = main.querySelectorAll('div');
            for (var i = 0; i < divs.length; i++) {
                if (divs[i].scrollHeight > divs[i].clientHeight + 50) return divs[i].scrollTop;
            }
            return 0;
        """)

        scrolls_feitos = 0
        for i in range(SCROLLS_INTERNOS):
            elemento_foco.send_keys(Keys.PAGE_UP)

            # ESPERAR O SPINNER DE LOADING SUMIR SE APARECER
            try:
                WebDriverWait(driver, 1.5).until_not(
                    EC.presence_of_element_located((By.XPATH, "//div[@role='progressbar'] | //span[@data-testid='msg-loading']"))
                )
            except:
                pass

            time.sleep(0.4)

            # Verifica se o scroll mudou (se não mudou, chegou ao topo)
            scroll_atual = driver.execute_script("""
                var main = document.getElementById('main');
                var divs = main.querySelectorAll('div');
                for (var i = 0; i < divs.length; i++) {
                    if (divs[i].scrollHeight > divs[i].clientHeight + 50) return divs[i].scrollTop;
                }
                return 0;
            """)
            scrolls_feitos += 1

            if scroll_atual == scroll_antes:
                # Chegou ao topo — não precisa continuar
                break
            scroll_antes = scroll_atual

        log(f"      🔄 Scroll: {scrolls_feitos}/{SCROLLS_INTERNOS} (parou no topo)" if scrolls_feitos < SCROLLS_INTERNOS
              else f"      🔄 Scroll: {scrolls_feitos}/{SCROLLS_INTERNOS}")

        time.sleep(0.5)  # Espera mensagens carregarem
        return True

    except Exception as e:
        log(f"      ⚠️ Erro no scroll: {str(e)[:50]}")
        return False


def extrair_numero_do_painel(driver):
    """
    Abre o painel 'Dados do contato' clicando no header,
    extrai o número de telefone e fecha o painel.
    Busca especificamente no drawer lateral, não no body inteiro.
    Retorna o número limpo ou None.
    """
    try:
        main = driver.find_element(By.ID, "main")
        header = main.find_element(By.TAG_NAME, "header")

        # Clica no nome/foto/info dentro do header para abrir drawer
        botoes = header.find_elements(By.XPATH, ".//div[@role='button'] | .//img | .//span[@dir='auto']")
        if botoes:
            botoes[0].click()
        else:
            header.click()

        sleep_load()
        time.sleep(0.8)  # Espera o drawer abrir completamente

        # === BUSCA DIRECIONADA no drawer de contato ===
        # Tenta múltiplos seletores, do mais específico ao mais genérico
        texto_drawer = ""

        # Tentativa 1: drawer com data-testid específico
        seletores = [
            "//div[@data-testid='chat-info-drawer']",
            "//div[@data-testid='contact-info-drawer']",
            "//div[contains(@data-testid, 'drawer')]",
            "//div[@id='app']//section",
        ]

        for sel in seletores:
            els = driver.find_elements(By.XPATH, sel)
            if els:
                texto_drawer = els[-1].text  # Pega o último (mais recente/relevante)
                break

        # Fallback: se não encontrou drawer, tenta a região à direita do main
        if not texto_drawer:
            # Pega o texto da página MAS exclui o #main (mensagens) e #pane-side (lista)
            todo_texto = driver.find_element(By.TAG_NAME, "body").text
            main_texto = main.text
            pane_texto = ""
            try:
                pane_texto = driver.find_element(By.ID, "pane-side").text
            except:
                pass
            # O drawer é o que sobra
            texto_drawer = todo_texto.replace(main_texto, "").replace(pane_texto, "")

        # Regex para capturar padrões de telefone
        padrao = r'\+?\d{2,3}\s?\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4}'
        encontrados = re.findall(padrao, texto_drawer)

        # Limpa, deduplica, e filtra números excluídos
        numeros_validos = []
        for e in encontrados:
            limpo = limpar_numero(e)
            if len(limpo) >= 12 and limpo not in numeros_validos and limpo != NUMERO_PROPRIO:
                numeros_validos.append(limpo)

        # Fecha o drawer: ESC
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except:
            pass
        sleep_min()

        # Retorna o primeiro número válido encontrado
        if numeros_validos:
            return numeros_validos[0]

    except Exception as e:
        log(f"      Erro ao extrair do painel: {str(e)[:60]}")
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except:
            pass

    return None


# =================================================================================
# LÓGICA PRINCIPAL
# =================================================================================

def extrair_leads():
    copiar_perfil_chrome()

    processados, leads = carregar_progresso()
    inicializar_csv()
    if processados:
        log(f"[*] Retomando: {len(processados)} processados, {len(leads)} leads.\n")

    log("Iniciando o Chrome...")
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={CHROME_ROBO}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.binary_location = CHROME_BIN

    driver = webdriver.Chrome(options=options)
    total = 0
    leads_antes = len(leads)
    inicio = time.time()

    try:
        driver.get("https://web.whatsapp.com")
        log("Aguardando WhatsApp Web...")

        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.ID, "pane-side"))
        )
        log("[✓] WhatsApp carregado!")

        # Refresh para garantir dados atualizados (evita cache de mensagens antigas)
        driver.refresh()
        log("[*] Página recarregada para dados frescos.")
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.ID, "pane-side"))
        )
        sleep_load()
        time.sleep(1)

        painel = driver.find_element(By.ID, "pane-side")
        tentativas_fim = 0

        while True:
            conversas = driver.find_elements(By.XPATH, "//div[@id='pane-side']//div[@role='row']")

            for conv in conversas:
                try:
                    # --- Título do contato ---
                    titulo_els = conv.find_elements(By.XPATH, ".//span[@title]")
                    if not titulo_els:
                        continue
                    nome = titulo_els[0].get_attribute("title")
                    if nome in processados:
                        continue
                    processados.add(nome)
                    total += 1

                    # Limite de teste
                    if MAX_CONTATOS and total > MAX_CONTATOS:
                        break

                    # --- Pular grupos ---
                    icone_grupo = conv.find_elements(By.XPATH,
                        ".//span[@data-testid='default-group'] | .//span[@data-testid='default-community']")
                    if icone_grupo:
                        log(f"  [{total}] ⏭ Grupo: {nome}")
                        continue

                    # --- Pular Nomes Ignorados (Lista Negra) ---
                    if any(ignorar in nome.lower() for ignorar in NOMES_IGNORAR):
                        log(f"  [{total}] ⏭ Ignorado (Lista Negra): {nome}")
                        continue

                    # ==========================================================
                    # NOVO FLUXO RÁPIDO OTIMIZADO:
                    # Se for Auto-Lead (Ex: "Anúncio", "Paciente" ou Número Seco), pula o filtro
                    # de conversa e extrai imediatamente! Assumimos que a própria existência
                    # desse perfil sem nome definitivo já diz que ele não fechou pacote.
                    # ==========================================================
                    numero_titulo = titulo_e_numero(nome)

                    if numero_titulo == NUMERO_PROPRIO:
                        log(f"  [{total}] ⏭ Própria conta: {nome}")
                        continue

                    # Verifica se deve ser incluído automaticamente ("Anúncio" no nome ou Não Salvo)
                    is_auto_lead = numero_titulo is not None or any(
                        n in nome.lower() for n in NOMES_AUTO_LEAD
                    )

                    # --- CAMINHO 1: AUTO LEAD (Super Rápido) ---
                    if is_auto_lead:
                        if numero_titulo:
                            # Se for MENSAGEM DE NÚMERO, Salva em 0.1s Sem Clicar!
                            numero = numero_titulo
                            if numero not in leads:
                                leads.add(numero)
                                log(f"  [{total}] 📱 LEAD #{len(leads)}: {numero} ← {nome} (não salvo)")
                                append_csv(numero)
                            else:
                                log(f"  [{total}] 📱 Duplicado: {nome}")
                            continue
                        else:
                            # Se for "Anúncio Rosangela", abre rápido, NÃO LÊ MENSAGEM, Pega o Perfil e sai!
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", conv)
                            sleep_min()
                            try:
                                conv.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", conv)
                            sleep_load()

                            log(f"  [{total}] ✅ Match (Auto-Lead): {nome}")
                            numero = extrair_numero_do_painel(driver)

                            if numero and numero not in leads:
                                leads.add(numero)
                                log(f"  [{total}] ✅ LEAD #{len(leads)}: {numero} ← {nome}")
                                append_csv(numero)
                            elif numero:
                                log(f"  [{total}] ✅ Duplicado: {nome} → {numero}")
                            else:
                                log(f"  [{total}] ⚠️ Match mas sem número: {nome}")

                            continue

                    # --- CAMINHO 2: CONTATO SALVO COMUM (Analisa Mensagens) ---
                    # Tenta abrir para verificar EXCLUSÕES (agendado) ou INCLUSÕES
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", conv)
                    sleep_min()
                    try:
                        conv.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", conv)
                    sleep_load()

                    try:
                        WebDriverWait(driver, 4).until(
                            EC.presence_of_element_located((By.ID, "main"))
                        )
                        # Espera loading local de histórico novo terminar
                        WebDriverWait(driver, 2).until_not(
                            EC.presence_of_element_located((By.XPATH, "//div[@role='progressbar'] | //span[@data-testid='msg-loading']"))
                        )
                    except TimeoutException:
                        log(f"  [{total}] ⏭ Timeout ao abrir: {nome}")
                        continue

                    main = driver.find_element(By.ID, "main")

                    # PASSO 1: Lê mensagens da tela
                    # Exclusão pode vir de mim ("agendada com sucesso") ou dele ("comprovante", "confirmado")
                    texto_visivel = main.text

                    # Inclusão ("qual o valor?", etc) TEM QUE VIR SOMENTE DO CLIENTE (message-in)
                    msgs_cliente = main.find_elements(By.CSS_SELECTOR, "div.message-in")
                    texto_cliente_visivel = " ".join([m.text for m in msgs_cliente])

                    tem_exclusao = contem_exclusao(texto_visivel)
                    tem_inclusao = atende_criterios(texto_cliente_visivel)

                    # PASSO 2: Se não houver prova na tela que foi agendado, damos o scroll pra trás
                    # Se houver, foi agendado, e ele é excluído IMEDIATAMENTE.
                    if not tem_exclusao:
                        rolou = scroll_conversa_para_cima(driver, nome)
                        if rolou:
                            texto_completo = driver.find_element(By.ID, "main").text
                            msgs_cliente_completo = driver.find_elements(By.CSS_SELECTOR, "div.message-in")
                            texto_cliente_completo = " ".join([m.text for m in msgs_cliente_completo])

                            tem_exclusao = contem_exclusao(texto_completo)
                            if not tem_inclusao:
                                tem_inclusao = atende_criterios(texto_cliente_completo)

                    if tem_exclusao:
                        log(f"  [{total}] 🚫 Já Agendou (Excluído): {nome}")
                        continue

                    if not tem_inclusao:
                        log(f"  [{total}] ❌ Sem match: {nome}")
                        continue

                    log(f"  [{total}] ✅ Match: {nome}")
                    numero = extrair_numero_do_painel(driver)

                    if numero and numero not in leads:
                        leads.add(numero)
                        log(f"  [{total}] ✅ LEAD #{len(leads)}: {numero} ← {nome}")
                        append_csv(numero)
                    elif numero:
                        log(f"  [{total}] ✅ Duplicado: {nome} → {numero}")
                    else:
                        log(f"  [{total}] ⚠️ Match mas sem número: {nome}")

                    # Salvar progresso a cada 20 contatos
                    if total % 20 == 0:
                        salvar_progresso(processados, leads)

                except (StaleElementReferenceException, Exception) as err:
                    msg = str(err).splitlines()[0][:60] if str(err) else ""
                    if msg:
                        log(f"  [{total}] ⚠️ Erro: {msg}")
                    continue

            # Limite de teste
            if MAX_CONTATOS and total >= MAX_CONTATOS:
                log(f"\n[TESTE] Limite de {MAX_CONTATOS} contatos atingido!")
                break

            # === Scroll da lista lateral ===
            h = driver.execute_script("return arguments[0].clientHeight", painel)
            driver.execute_script("arguments[0].scrollBy(0, arguments[1]);", painel, h)
            sleep_load()

            topo = driver.execute_script("return arguments[0].scrollTop", painel)
            total_h = driver.execute_script("return arguments[0].scrollHeight", painel)

            if topo + h >= total_h:
                tentativas_fim += 1
                if tentativas_fim >= 3:
                    log("\n[✓] Fim da lista de conversas!")
                    break
            else:
                tentativas_fim = 0

            salvar_progresso(processados, leads)
            tempo = int(time.time() - inicio)
            log(f"\n  --- Scroll: {total} processados | {len(leads)} leads | {tempo}s ---\n")

    except KeyboardInterrupt:
        log("\n\n[!] Interrompido (Ctrl+C). Progresso salvo!")

    finally:
        try:
            tempo_total = int(time.time() - inicio)
        except:
            tempo_total = 0

        salvar_progresso(processados, leads)
        salvar_csv_completo(leads)

        novos = len(leads) - leads_antes
        velocidade = f"{tempo_total / max(total, 1):.1f}s/contato" if total else "N/A"
        taxa = f"{(len(leads) / max(total, 1)) * 100:.1f}%" if total else "N/A"

        log(f"\n{'='*50}")
        log(f"  Processados: {total}")
        log(f"  Leads novos: {novos}")
        log(f"  Total leads: {len(leads)}")
        log(f"  Taxa conversão: {taxa}")
        log(f"  Velocidade: {velocidade}")
        log(f"  Tempo: {tempo_total // 60}min {tempo_total % 60}s")
        log(f"  CSV: {CSV_SAIDA}")

        # Distribuição por DDD
        if leads:
            from collections import Counter
            ddds = Counter()
            for num in leads:
                # DDI(55) + DDD(2 dig) = posições [2:4]
                ddd = num[2:4] if len(num) >= 4 else "??"
                ddds[ddd] += 1
            log(f"\n  Por DDD:")
            for ddd, qtd in ddds.most_common(10):
                log(f"    {ddd}: {qtd} leads")

        log(f"{'='*50}")

        try: driver.quit()
        except: pass


if __name__ == "__main__":
    extrair_leads()
