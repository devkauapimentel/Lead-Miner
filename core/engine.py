"""
core/engine.py — Motor Principal de Extração (ScraperEngine)
=============================================================
Controla o Selenium, navega no WhatsApp, aplica a Strategy
de filtragem e emite eventos (Observer Pattern).

Este é o arquivo mais complexo do projeto. Ele refatora e
melhora a lógica do whatsapp_lead_scraper_legacy.py.
"""

import time
import random
import re
import logging
from collections import Counter

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
)

from infra.phone_utils import limpar_numero, titulo_e_numero, extrair_numeros_do_texto

log = logging.getLogger("pegador")


class ScraperEngine:
    """
    Motor principal de extração de leads do WhatsApp.

    Design Patterns aplicados:
        - Observer: Notifica observers (Log, CSV, GUI) sobre eventos
        - Strategy: Usa FilterStrategy para decidir inclusão/exclusão
        - Facade (usado pelo facade.py): Expõe interface simples

    Fluxo:
        1. Abre Chrome → WhatsApp Web
        2. Para cada contato na lista lateral:
           a. Clica na conversa
           b. Abre 'Dados do contato' para ler etiquetas
           c. Aplica filter.should_exclude() → pula
           d. Aplica filter.should_include() → extrai número
           e. Emite evento 'lead_found' ou 'contact_skipped'
        3. Ao finalizar, emite 'finished' com estatísticas
    """

    def __init__(self, config: dict, filter_strategy, driver=None):
        """
        Args:
            config: Dicionário de configuração do ConfigManager
            filter_strategy: Instância de FilterStrategy
            driver: WebDriver (se None, será criado pelo ChromeManager)
        """
        self.config = config
        self.filter = filter_strategy
        self.driver = driver
        self.observers = []
        self.running = False

        # Estado de execução
        self.processados = set()
        self.leads = set()
        self.total = 0

        # Configuração
        self.own_number = config.get("own_number", "")
        self.blacklist = [n.lower() for n in config.get("blacklist_names", [])]
        self.auto_lead_names = [n.lower() for n in config.get("auto_lead_names", [])]
        self.max_contacts = config.get("scraper", {}).get("max_contacts")
        self.internal_scrolls = config.get("scraper", {}).get("internal_scrolls", 20)
        self.filter_mode = config.get("filter_mode", "labels")

    # =====================================================================
    # OBSERVER PATTERN
    # =====================================================================

    def add_observer(self, observer) -> None:
        """Registra um observer para receber eventos."""
        self.observers.append(observer)

    def remove_observer(self, observer) -> None:
        """Remove um observer."""
        self.observers.remove(observer)

    def notify(self, event_type: str, data: dict) -> None:
        """Notifica todos os observers sobre um evento."""
        for observer in self.observers:
            try:
                observer.on_event(event_type, data)
            except Exception as e:
                log.warning(f"Erro no observer: {e}")

    # =====================================================================
    # CONTROLE DE EXECUÇÃO
    # =====================================================================

    def set_progress(self, processados: set, leads: set) -> None:
        """Carrega progresso de uma execução anterior para retomada."""
        self.processados = processados
        self.leads = leads
        if processados:
            log.info(
                f"[*] Retomando: {len(processados)} processados, "
                f"{len(leads)} leads."
            )

    def run(self) -> None:
        """
        Loop principal de extração. Navega pelo WhatsApp e extrai leads.
        Emite eventos durante toda a execução.
        """
        self.running = True
        leads_antes = len(self.leads)
        inicio = time.time()

        try:
            self._navegar_whatsapp()
            self._processar_conversas(inicio, leads_antes)
        except KeyboardInterrupt:
            log.info("\n[!] Interrompido (Ctrl+C). Progresso salvo!")
        finally:
            self._finalizar(inicio, leads_antes)

    def stop(self) -> None:
        """Para a execução do loop principal."""
        self.running = False
        log.info("[*] Parando extração...")

    # =====================================================================
    # NAVEGAÇÃO NO WHATSAPP
    # =====================================================================

    def _navegar_whatsapp(self) -> None:
        """Navega até o WhatsApp Web e aguarda carregamento."""
        self.driver.get("https://web.whatsapp.com")
        log.info("Aguardando WhatsApp Web...")

        WebDriverWait(self.driver, 120).until(
            EC.presence_of_element_located((By.ID, "pane-side"))
        )
        log.info("[✓] WhatsApp carregado!")

        # Refresh para dados atualizados
        self.driver.refresh()
        log.info("[*] Página recarregada para dados frescos.")
        WebDriverWait(self.driver, 60).until(
            EC.presence_of_element_located((By.ID, "pane-side"))
        )
        self._sleep_load()
        time.sleep(1)

    def _processar_conversas(self, inicio: float, leads_antes: int) -> None:
        """Loop principal que percorre a lista de conversas."""
        painel = self.driver.find_element(By.ID, "pane-side")
        tentativas_fim = 0

        while self.running:
            conversas = self.driver.find_elements(
                By.XPATH, "//div[@id='pane-side']//div[@role='row']"
            )

            for conv in conversas:
                if not self.running:
                    break
                try:
                    self._processar_contato(conv)
                except (StaleElementReferenceException, Exception) as err:
                    msg = str(err).splitlines()[0][:60] if str(err) else ""
                    if msg:
                        self.notify("error", {
                            "index": self.total,
                            "name": "?",
                            "message": msg
                        })
                    continue

            # Verificar limite de teste
            if self.max_contacts and self.total >= self.max_contacts:
                log.info(f"\n[TESTE] Limite de {self.max_contacts} contatos atingido!")
                break

            # Scroll da lista lateral
            h = self.driver.execute_script("return arguments[0].clientHeight", painel)
            self.driver.execute_script(
                "arguments[0].scrollBy(0, arguments[1]);", painel, h
            )
            self._sleep_load()

            topo = self.driver.execute_script("return arguments[0].scrollTop", painel)
            total_h = self.driver.execute_script(
                "return arguments[0].scrollHeight", painel
            )

            if topo + h >= total_h:
                tentativas_fim += 1
                if tentativas_fim >= 3:
                    log.info("\n[✓] Fim da lista de conversas!")
                    break
            else:
                tentativas_fim = 0

            # Salvar progresso e notificar
            tempo = int(time.time() - inicio)
            self.notify("progress", {
                "processed": self.total,
                "total_leads": len(self.leads),
                "elapsed": tempo,
                "processed_set": self.processados,
                "leads_set": self.leads,
            })

    def _processar_contato(self, conv) -> None:
        """Processa um único contato da lista lateral."""
        # Extrair título do contato
        titulo_els = conv.find_elements(By.XPATH, ".//span[@title]")
        if not titulo_els:
            return

        nome = titulo_els[0].get_attribute("title")
        if nome in self.processados:
            return

        self.processados.add(nome)
        self.total += 1

        # Verificar limite
        if self.max_contacts and self.total > self.max_contacts:
            return

        # Pular grupos
        icone_grupo = conv.find_elements(By.XPATH,
            ".//span[@data-testid='default-group'] | "
            ".//span[@data-testid='default-community']"
        )
        if icone_grupo:
            self.notify("contact_skipped", {
                "index": self.total, "name": nome, "reason": "Grupo"
            })
            return

        # Pular lista negra
        if any(ignorar in nome.lower() for ignorar in self.blacklist):
            self.notify("contact_skipped", {
                "index": self.total, "name": nome, "reason": "Lista Negra"
            })
            return

        # Verificar se é número próprio
        numero_titulo = titulo_e_numero(nome)
        if numero_titulo == self.own_number:
            self.notify("contact_skipped", {
                "index": self.total, "name": nome, "reason": "Própria conta"
            })
            return

        # =====================================================
        # FLUXO RÁPIDO: Número não salvo (título é o telefone)
        # =====================================================
        if numero_titulo is not None:
            if self.filter_mode == "labels":
                # Se estamos no modo labels, precisamos abrir o contato
                # para verificar as etiquetas dele
                self._processar_com_labels(conv, nome)
            else:
                # Modo keywords/legacy: salva direto (Auto-Lead)
                self._salvar_lead(numero_titulo, nome)
            return

        # =====================================================
        # FLUXO COM CLIQUE: Auto-Lead ou contato regular
        # =====================================================
        is_auto_lead = any(n in nome.lower() for n in self.auto_lead_names)

        if self.filter_mode == "labels":
            # Modo Labels: abre contato e lê etiquetas
            self._processar_com_labels(conv, nome)
        elif is_auto_lead:
            # Modo Keywords + Auto-Lead: extrai direto
            self._clicar_conversa(conv)
            self._sleep_load()
            numero = self._extrair_numero_painel()
            if numero:
                self._salvar_lead(numero, nome)
        else:
            # Modo Keywords: lê mensagens
            self._processar_com_keywords(conv, nome)

    # =====================================================================
    # PROCESSAMENTO POR ETIQUETAS (NOVO - v2.0)
    # =====================================================================

    def _processar_com_labels(self, conv, nome: str) -> None:
        """
        Abre o contato, lê as etiquetas do painel lateral
        e aplica as regras de inclusão/exclusão.
        """
        self._clicar_conversa(conv)
        self._sleep_load()

        try:
            WebDriverWait(self.driver, 4).until(
                EC.presence_of_element_located((By.ID, "main"))
            )
        except TimeoutException:
            self.notify("contact_skipped", {
                "index": self.total, "name": nome, "reason": "Timeout ao abrir"
            })
            return

        # Abrir painel 'Dados do contato'
        labels = self._extrair_labels_do_painel()
        numero = self._extrair_numero_painel_aberto()

        # Preparar info do contato para a Strategy
        contact_info = {
            "name": nome,
            "labels": labels,
            "is_unsaved": titulo_e_numero(nome) is not None,
        }

        # Avaliar com a Strategy
        is_lead, reason = self.filter.evaluate(contact_info)

        if not is_lead:
            self.notify("contact_excluded" if "Exclu" in reason else "contact_no_match", {
                "index": self.total,
                "name": nome,
                "reason": reason,
                "total_leads": len(self.leads),
            })
            # Fechar drawer com ESC
            self._fechar_drawer()
            return

        # É lead! Extrair número
        if numero:
            self._salvar_lead(numero, nome)
        else:
            self.notify("contact_no_phone", {
                "index": self.total,
                "name": nome,
                "total_leads": len(self.leads),
            })

        self._fechar_drawer()

    def _extrair_labels_do_painel(self) -> list[str]:
        """
        Abre o painel 'Dados do contato' e extrai as etiquetas.
        As etiquetas no WhatsApp Web aparecem como chips/badges
        dentro do drawer de informações do contato.

        Returns:
            Lista de nomes das etiquetas encontradas
        """
        try:
            main = self.driver.find_element(By.ID, "main")
            header = main.find_element(By.TAG_NAME, "header")

            # Clica no header para abrir drawer
            botoes = header.find_elements(
                By.XPATH,
                ".//div[@role='button'] | .//img | .//span[@dir='auto']"
            )
            if botoes:
                botoes[0].click()
            else:
                header.click()

            self._sleep_load()
            time.sleep(0.8)

            # Buscar labels no drawer
            labels = []

            # Tentativa 1: buscar por data-testid de labels
            label_elements = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@data-testid, 'label')] | "
                "//span[contains(@data-testid, 'label')]"
            )

            for el in label_elements:
                text = el.text.strip()
                if text and text not in labels:
                    labels.append(text)

            # Tentativa 2: buscar por elementos de chips/badges no drawer
            if not labels:
                drawers = self.driver.find_elements(
                    By.XPATH,
                    "//div[@data-testid='chat-info-drawer'] | "
                    "//div[@data-testid='contact-info-drawer'] | "
                    "//div[contains(@data-testid, 'drawer')]"
                )
                for drawer in drawers:
                    # Labels geralmente têm cor de fundo e texto curto
                    chips = drawer.find_elements(
                        By.XPATH,
                        ".//div[contains(@style, 'background')] | "
                        ".//span[contains(@class, 'label')] | "
                        ".//div[@role='listitem']"
                    )
                    for chip in chips:
                        text = chip.text.strip()
                        # Filtrar textos muito longos ou vazios
                        if text and len(text) < 50 and text not in labels:
                            labels.append(text)

            # Tentativa 3: buscar pelo texto completo do drawer
            if not labels:
                for drawer_sel in [
                    "//div[@data-testid='chat-info-drawer']",
                    "//div[@data-testid='contact-info-drawer']",
                    "//div[contains(@data-testid, 'drawer')]",
                    "//div[@id='app']//section",
                ]:
                    els = self.driver.find_elements(By.XPATH, drawer_sel)
                    if els:
                        drawer_text = els[-1].text
                        # Buscar nomes de labels conhecidos no texto
                        from core.config_manager import KNOWN_LABELS
                        for known in KNOWN_LABELS:
                            if known.lower() in drawer_text.lower():
                                labels.append(known)
                        break

            if labels:
                log.info(f"      🏷️ Labels: {', '.join(labels)}")

            return labels

        except Exception as e:
            log.warning(f"      ⚠️ Erro ao ler labels: {str(e)[:50]}")
            return []

    def _extrair_numero_painel_aberto(self) -> str | None:
        """
        Extrai o número de telefone do painel lateral já aberto.
        Busca o número no drawer de dados do contato.

        Returns:
            Número limpo ou None
        """
        try:
            texto_drawer = ""

            seletores = [
                "//div[@data-testid='chat-info-drawer']",
                "//div[@data-testid='contact-info-drawer']",
                "//div[contains(@data-testid, 'drawer')]",
                "//div[@id='app']//section",
            ]

            for sel in seletores:
                els = self.driver.find_elements(By.XPATH, sel)
                if els:
                    texto_drawer = els[-1].text
                    break

            if not texto_drawer:
                main = self.driver.find_element(By.ID, "main")
                todo_texto = self.driver.find_element(By.TAG_NAME, "body").text
                main_texto = main.text
                pane_texto = ""
                try:
                    pane_texto = self.driver.find_element(By.ID, "pane-side").text
                except Exception:
                    pass
                texto_drawer = todo_texto.replace(main_texto, "").replace(pane_texto, "")

            numeros = extrair_numeros_do_texto(texto_drawer)

            # Filtrar número próprio
            numeros = [n for n in numeros if n != self.own_number]

            return numeros[0] if numeros else None

        except Exception as e:
            log.warning(f"      Erro ao extrair número: {str(e)[:60]}")
            return None

    # =====================================================================
    # PROCESSAMENTO POR KEYWORDS (LEGADO - v1.0)
    # =====================================================================

    def _processar_com_keywords(self, conv, nome: str) -> None:
        """
        Abre a conversa, lê mensagens e aplica filtro por keywords.
        Lógica preservada do whatsapp_lead_scraper_legacy.py
        """
        self._clicar_conversa(conv)
        self._sleep_load()

        try:
            WebDriverWait(self.driver, 4).until(
                EC.presence_of_element_located((By.ID, "main"))
            )
            WebDriverWait(self.driver, 2).until_not(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//div[@role='progressbar'] | //span[@data-testid='msg-loading']"
                ))
            )
        except TimeoutException:
            self.notify("contact_skipped", {
                "index": self.total, "name": nome, "reason": "Timeout ao abrir"
            })
            return

        main = self.driver.find_element(By.ID, "main")

        # Leitura de mensagens
        texto_visivel = main.text
        msgs_cliente = main.find_elements(By.CSS_SELECTOR, "div.message-in")
        texto_cliente = " ".join([m.text for m in msgs_cliente])

        contact_info = {
            "name": nome,
            "messages": texto_visivel,
            "client_messages": texto_cliente,
        }

        tem_exclusao = self.filter.should_exclude(contact_info)
        tem_inclusao = self.filter.should_include(contact_info)

        # Se não tem exclusão visível, tenta scroll para histórico
        if not tem_exclusao:
            self._scroll_conversa(nome)
            texto_completo = self.driver.find_element(By.ID, "main").text
            msgs_completas = self.driver.find_elements(By.CSS_SELECTOR, "div.message-in")
            texto_cliente_completo = " ".join([m.text for m in msgs_completas])

            contact_info["messages"] = texto_completo
            contact_info["client_messages"] = texto_cliente_completo

            tem_exclusao = self.filter.should_exclude(contact_info)
            if not tem_inclusao:
                tem_inclusao = self.filter.should_include(contact_info)

        if tem_exclusao:
            self.notify("contact_excluded", {
                "index": self.total,
                "name": nome,
                "reason": "Já Agendou",
                "total_leads": len(self.leads),
            })
            return

        if not tem_inclusao:
            self.notify("contact_no_match", {
                "index": self.total,
                "name": nome,
                "total_leads": len(self.leads),
            })
            return

        # Match! Extrair número
        numero = self._extrair_numero_painel()
        if numero:
            self._salvar_lead(numero, nome)
        else:
            self.notify("contact_no_phone", {
                "index": self.total,
                "name": nome,
                "total_leads": len(self.leads),
            })

    def _extrair_numero_painel(self) -> str | None:
        """
        Abre o painel 'Dados do contato' e extrai o número.
        (Método completo que abre e fecha o drawer)
        """
        try:
            main = self.driver.find_element(By.ID, "main")
            header = main.find_element(By.TAG_NAME, "header")

            botoes = header.find_elements(
                By.XPATH,
                ".//div[@role='button'] | .//img | .//span[@dir='auto']"
            )
            if botoes:
                botoes[0].click()
            else:
                header.click()

            self._sleep_load()
            time.sleep(0.8)

            numero = self._extrair_numero_painel_aberto()

            self._fechar_drawer()
            return numero

        except Exception as e:
            log.warning(f"      Erro ao extrair do painel: {str(e)[:60]}")
            self._fechar_drawer()
            return None

    # =====================================================================
    # UTILITÁRIOS SELENIUM
    # =====================================================================

    def _clicar_conversa(self, conv) -> None:
        """Rola até a conversa e clica nela."""
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", conv
        )
        self._sleep_min()
        try:
            conv.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", conv)

    def _fechar_drawer(self) -> None:
        """Fecha o drawer lateral com ESC."""
        try:
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        except Exception:
            pass
        self._sleep_min()

    def _scroll_conversa(self, nome: str) -> bool:
        """Rola a conversa para cima para carregar histórico."""
        try:
            main = self.driver.find_element(By.ID, "main")
            caixas = self.driver.find_elements(
                By.XPATH, "//div[@contenteditable='true'][@data-tab='10']"
            )
            foco = caixas[0] if caixas else main
            try:
                foco.click()
            except Exception:
                main.click()

            time.sleep(0.3)

            scroll_antes = self.driver.execute_script("""
                var main = document.getElementById('main');
                var divs = main.querySelectorAll('div');
                for (var i = 0; i < divs.length; i++) {
                    if (divs[i].scrollHeight > divs[i].clientHeight + 50)
                        return divs[i].scrollTop;
                }
                return 0;
            """)

            scrolls_feitos = 0
            for _ in range(self.internal_scrolls):
                foco.send_keys(Keys.PAGE_UP)
                try:
                    WebDriverWait(self.driver, 1.5).until_not(
                        EC.presence_of_element_located((
                            By.XPATH,
                            "//div[@role='progressbar'] | "
                            "//span[@data-testid='msg-loading']"
                        ))
                    )
                except Exception:
                    pass

                time.sleep(0.4)
                scroll_atual = self.driver.execute_script("""
                    var main = document.getElementById('main');
                    var divs = main.querySelectorAll('div');
                    for (var i = 0; i < divs.length; i++) {
                        if (divs[i].scrollHeight > divs[i].clientHeight + 50)
                            return divs[i].scrollTop;
                    }
                    return 0;
                """)
                scrolls_feitos += 1
                if scroll_atual == scroll_antes:
                    break
                scroll_antes = scroll_atual

            self.notify("scroll", {
                "index": self.total,
                "name": nome,
                "done": scrolls_feitos,
                "total": self.internal_scrolls,
                "hit_top": scrolls_feitos < self.internal_scrolls,
            })
            time.sleep(0.5)
            return True

        except Exception as e:
            log.warning(f"      ⚠️ Erro no scroll: {str(e)[:50]}")
            return False

    def _salvar_lead(self, numero: str, nome: str) -> None:
        """Registra um lead e notifica observers."""
        if numero not in self.leads:
            self.leads.add(numero)
            self.notify("lead_found", {
                "index": self.total,
                "name": nome,
                "phone": numero,
                "total_leads": len(self.leads),
            })
        else:
            self.notify("lead_duplicate", {
                "index": self.total,
                "name": nome,
                "phone": numero,
                "total_leads": len(self.leads),
            })

    def _finalizar(self, inicio: float, leads_antes: int) -> None:
        """Emite evento de finalização com estatísticas."""
        try:
            tempo_total = int(time.time() - inicio)
        except Exception:
            tempo_total = 0

        novos = len(self.leads) - leads_antes
        total = max(self.total, 1)
        velocidade = f"{tempo_total / total:.1f}s/contato" if self.total else "N/A"
        taxa = f"{(len(self.leads) / total) * 100:.1f}%" if self.total else "N/A"
        tempo_str = f"{tempo_total // 60}min {tempo_total % 60}s"

        # Distribuição por DDD
        ddds = {}
        for num in self.leads:
            ddd = num[2:4] if len(num) >= 4 else "??"
            ddds[ddd] = ddds.get(ddd, 0) + 1

        self.notify("finished", {
            "index": self.total,
            "name": "FINAL",
            "processed": self.total,
            "new_leads": novos,
            "total_leads": len(self.leads),
            "rate": taxa,
            "speed": velocidade,
            "time": tempo_str,
            "csv_path": "data/leads_remarketing.csv",
            "ddds": ddds,
            "processed_set": self.processados,
            "leads_set": self.leads,
        })

    @staticmethod
    def _sleep_min():
        time.sleep(random.uniform(0.3, 0.6))

    @staticmethod
    def _sleep_load():
        time.sleep(random.uniform(0.7, 1.2))
