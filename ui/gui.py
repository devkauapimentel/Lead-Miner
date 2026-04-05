"""
ui/gui.py — Interface Visual (Lead Miner)
=============================================
Janela moderna com dark mode, 2 abas:
  1. Configuração — selecionar tags, número, chrome, presets
  2. Execução — iniciar, progresso, log, exportar

⛏️ Powered by Lead Miner v2.0.0-beta
"""

import os
import sys
import threading
import time
import logging
import re

# === Temas Premium (Lead Miner) ===
COLOR_EMERALD = "#1DB954"  # Verde Esmeralda Vibrante
COLOR_GOLD = "#FFD700"     # Ouro
COLOR_BG_DARK = "#121212"  # Fundo extra escuro


try:
    import customtkinter as ctk
except ImportError:
    raise ImportError(
        "customtkinter não instalado ou tkinter do sistema ausente. "
        "Rode: sudo apt install python3-tk && venv/bin/pip install customtkinter"
    )

# Adicionar raiz do projeto ao path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.config_manager import ConfigManager, KNOWN_LABELS
from core.facade import LeadMinerFacade

log = logging.getLogger("lead_miner")


class GUIObserver:
    """
    Observer que atualiza a GUI em tempo real com eventos do Engine.
    Roda na thread principal através de after() do Tkinter.
    """

    def __init__(self, app: 'LeadMinerApp'):
        self.app = app

    def on_event(self, event_type: str, data: dict) -> None:
        """Recebe evento e agenda atualização na thread da GUI."""
        # Usar after() para thread-safety com Tkinter
        try:
            self.app.after(0, self._handle_event, event_type, data)
        except Exception:
            pass  # GUI pode ter sido fechada

    def _handle_event(self, event_type: str, data: dict):
        """Manipula evento na thread principal da GUI."""
        idx = data.get("index", 0)
        name = data.get("name", "?")
        total_leads = data.get("total_leads", 0)

        if event_type == "lead_found":
            phone = data.get("phone", "?")
            self.app.add_log(f"✅ LEAD #{total_leads}: {phone} ← {name}")
            self.app.update_stats(
                processed=idx,
                leads=total_leads,
            )

        elif event_type == "lead_duplicate":
            self.app.add_log(f"✅ Duplicado: {name}")

        elif event_type == "contact_excluded":
            reason = data.get("reason", "")
            self.app.add_log(f"🚫 Excluído ({reason}): {name}")
            self.app.update_stats(processed=idx, leads=total_leads)

        elif event_type == "contact_skipped":
            reason = data.get("reason", "")
            self.app.add_log(f"⏭ {reason}: {name}")
            self.app.update_stats(processed=idx, leads=total_leads)

        elif event_type == "contact_no_match":
            self.app.add_log(f"❌ Sem match: {name}")
            self.app.update_stats(processed=idx, leads=total_leads)

        elif event_type == "contact_no_phone":
            self.app.add_log(f"⚠️ Match mas sem número: {name}")

        elif event_type == "error":
            msg = data.get("message", "")
            self.app.add_log(f"⚠️ Erro: {msg}")

        elif event_type == "progress":
            processed = data.get("processed", 0)
            self.app.update_stats(processed=processed, leads=total_leads)

        elif event_type == "finished":
            self.app.on_finished(data)


class LeadMinerApp(ctk.CTk):
    """
    Aplicação principal Lead Miner com CustomTkinter.

    2 Abas:
        - Config: Editar regras de negócio, chrome, presets
        - Execução: Iniciar/parar, progresso, log, stats
    """

    def __init__(self):
        super().__init__()

        # Configuração da janela
        self.title("⛏️ Lead Miner v2.0.0-beta")
        self.geometry("650x550")
        self.minsize(550, 450)

        # Aparência
        ctk.set_appearance_mode("dark")
        # ctk.set_default_color_theme("blue") # Substituído por customização manual


        # Estado
        self.pegador = None
        self.running = False
        self.start_time = None
        self.timer_job = None
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load()

        # Construir UI
        self._build_ui()
        self._load_config_to_ui()

    def _build_ui(self):
        """Constrói toda a interface."""
        # === Header ===
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            header,
            text="⛏️ Lead Miner",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=COLOR_EMERALD
        ).pack(side="left")


        ctk.CTkLabel(
            header,
            text="v2.0.0-beta",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).pack(side="left", padx=(8, 0), pady=(8, 0))

        # === Tabs ===
        self.tabview = ctk.CTkTabview(
            self, 
            segmented_button_selected_color=COLOR_EMERALD,
            segmented_button_selected_hover_color="#189e47",
            segmented_button_unselected_hover_color="#333333"
        )

        self.tabview.pack(fill="both", expand=True, padx=20, pady=10)

        self.tab_config = self.tabview.add("⚙️ Configuração")
        self.tab_run = self.tabview.add("🚀 Execução")

        self._build_config_tab()
        self._build_run_tab()

    def _build_config_tab(self):
        """Aba de Configuração."""
        tab = self.tab_config

        # Scroll frame
        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Negócio ---
        ctk.CTkLabel(scroll, text="📋 Dados do Negócio",
                      font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(10, 5))

        row_biz = ctk.CTkFrame(scroll, fg_color="transparent")
        row_biz.pack(fill="x", pady=2)
        ctk.CTkLabel(row_biz, text="Nome:").pack(
            side="left", padx=(0, 8))
        self.entry_business = ctk.CTkEntry(row_biz, placeholder_text="Ex: Clínica Dra. Rosa")
        self.entry_business.pack(side="left", fill="x", expand=True)

        row_num = ctk.CTkFrame(scroll, fg_color="transparent")
        row_num.pack(fill="x", pady=2)
        ctk.CTkLabel(row_num, text="Meu Número:").pack(
            side="left", padx=(0, 8))
            
        self.number_var = ctk.StringVar()
        self.number_var.trace_add("write", self._format_phone)
        
        self.entry_number = ctk.CTkEntry(row_num, placeholder_text="+55 (21) 99453-8190", textvariable=self.number_var)
        self.entry_number.pack(side="left", fill="x", expand=True)

        # --- Chrome ---
        ctk.CTkLabel(scroll, text="🌐 Estratégia de Navegador",
                      font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(15, 5))
            
        self.chrome_mode_var = ctk.StringVar(value=self.config.get("chrome", {}).get("mode", "real"))
        
        radio_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        radio_frame.pack(fill="x", pady=(2, 10))
        
        ctk.CTkRadioButton(radio_frame, text="💻 Chrome Nativo (Login Direto. Feche seu navegador antes de rodar)", variable=self.chrome_mode_var, value="real").pack(anchor="w", pady=5)
        ctk.CTkRadioButton(radio_frame, text="🛡️ Chrome Clonado Seguro (Copia a sessão atual em background)", variable=self.chrome_mode_var, value="isolated").pack(anchor="w", pady=5)
        ctk.CTkRadioButton(radio_frame, text="📱 Chrome Zerado (Abre vazio para ler um NOVO QR Code do 0)", variable=self.chrome_mode_var, value="clean").pack(anchor="w", pady=5)

        row_chrome_bin = ctk.CTkFrame(scroll, fg_color="transparent")
        row_chrome_bin.pack(fill="x", pady=2)
        ctk.CTkLabel(row_chrome_bin, text="Binário:").pack(
            side="left", padx=(0, 8))
        self.entry_chrome_bin = ctk.CTkEntry(
            row_chrome_bin, placeholder_text="auto (detecta automaticamente)")
        self.entry_chrome_bin.pack(side="left", fill="x", expand=True)

        row_chrome_profile = ctk.CTkFrame(scroll, fg_color="transparent")
        row_chrome_profile.pack(fill="x", pady=2)
        ctk.CTkLabel(row_chrome_profile, text="Caminho do Perfil\n(veja chrome://version):", justify="left").pack(
            side="left", padx=(0, 8))
        self.entry_chrome_profile = ctk.CTkEntry(
            row_chrome_profile, placeholder_text="Ex: ~/.config/google-chrome/Profile 1")
        self.entry_chrome_profile.pack(side="left", fill="x", expand=True)

        # --- Modo de Filtro ---
        ctk.CTkLabel(scroll, text="🔍 Modo de Filtragem",
                      font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(15, 5))

        self.filter_mode_var = ctk.StringVar(value="labels")
        row_mode = ctk.CTkFrame(scroll, fg_color="transparent")
        row_mode.pack(fill="x", pady=2)
        for mode, label in [
            ("labels", "📌 Etiquetas (Recomendado)"),
            ("keywords", "🔤 Palavras-chave (Legado)"),
            ("hybrid", "🔀 Híbrido (Labels + Keywords)")
        ]:
            ctk.CTkRadioButton(
                row_mode, text=label,
                variable=self.filter_mode_var, value=mode,
            ).pack(anchor="w", pady=2, padx=10)

        # --- Labels Inclusão ---
        ctk.CTkLabel(scroll, text="✅ Etiquetas para INCLUIR (Remarketing)",
                      font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(15, 5))
        ctk.CTkLabel(scroll, text="Contatos com estas tags serão extraídos",
                      text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w")

        self.include_vars = {}
        self.include_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.include_frame.pack(fill="x", pady=5)

        for label in KNOWN_LABELS:
            var = ctk.BooleanVar(value=False)
            self.include_vars[label] = var
            ctk.CTkCheckBox(
                self.include_frame, text=label, variable=var,
                checkbox_width=20, checkbox_height=20,
            ).pack(anchor="w", padx=15, pady=1)

        # Custom include entry
        row_custom_inc = ctk.CTkFrame(scroll, fg_color="transparent")
        row_custom_inc.pack(fill="x", pady=2)
        self.entry_custom_include = ctk.CTkEntry(
            row_custom_inc, placeholder_text="Adicionar etiqueta personalizada...")
        self.entry_custom_include.pack(side="left", fill="x", expand=True, padx=(15, 5))
        ctk.CTkButton(
            row_custom_inc, text="＋", width=40,
            command=self._add_custom_include
        ).pack(side="left")

        # --- Labels Exclusão ---
        ctk.CTkLabel(scroll, text="🚫 Etiquetas para EXCLUIR (Bloquear)",
                      font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(15, 5))
        ctk.CTkLabel(scroll, text="Contatos com estas tags serão ignorados",
                      text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w")

        self.exclude_vars = {}
        self.exclude_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.exclude_frame.pack(fill="x", pady=5)

        for label in KNOWN_LABELS:
            var = ctk.BooleanVar(value=False)
            self.exclude_vars[label] = var
            ctk.CTkCheckBox(
                self.exclude_frame, text=label, variable=var,
                checkbox_width=20, checkbox_height=20,
            ).pack(anchor="w", padx=15, pady=1)

        # Custom exclude entry
        row_custom_exc = ctk.CTkFrame(scroll, fg_color="transparent")
        row_custom_exc.pack(fill="x", pady=2)
        self.entry_custom_exclude = ctk.CTkEntry(
            row_custom_exc, placeholder_text="Adicionar etiqueta personalizada...")
        self.entry_custom_exclude.pack(side="left", fill="x", expand=True, padx=(15, 5))
        ctk.CTkButton(
            row_custom_exc, text="＋", width=40,
            command=self._add_custom_exclude
        ).pack(side="left")

        # --- Lista Negra ---
        ctk.CTkLabel(scroll, text="⛔ Lista Negra (Nomes para Ignorar)",
                      font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(15, 5))

        self.entry_blacklist = ctk.CTkEntry(
            scroll, placeholder_text="nome1, nome2, nome3 (separados por vírgula)")
        self.entry_blacklist.pack(fill="x", padx=15, pady=2)

        # --- Lead Automático ---
        ctk.CTkLabel(scroll, text="🤖 Lead Automático (Nomes)",
                      font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(15, 5))
        ctk.CTkLabel(scroll, text="Contatos com estes nomes serão tratados como lead independente de etiquetas",
                      text_color="gray", font=ctk.CTkFont(size=11)).pack(anchor="w")

        self.entry_auto_names = ctk.CTkEntry(
            scroll, placeholder_text="anúncio, ads, lead (separados por vírgula)")
        self.entry_auto_names.pack(fill="x", padx=15, pady=2)

        # --- Limites e Performance ---
        ctk.CTkLabel(scroll, text="⚡ Limites e Performance",
                      font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(15, 5))

        row_limits = ctk.CTkFrame(scroll, fg_color="transparent")
        row_limits.pack(fill="x", pady=2)
        
        # Max Contacts
        frame_max = ctk.CTkFrame(row_limits, fg_color="transparent")
        frame_max.pack(side="left", fill="x", expand=True, padx=(5, 10))
        ctk.CTkLabel(frame_max, text="Máx. Contatos (0 = ilimitado):", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.entry_max_contacts = ctk.CTkEntry(frame_max, placeholder_text="Ex: 50")
        self.entry_max_contacts.pack(fill="x")

        # Internal Scrolls
        frame_scrolls = ctk.CTkFrame(row_limits, fg_color="transparent")
        frame_scrolls.pack(side="left", fill="x", expand=True, padx=(10, 5))
        ctk.CTkLabel(frame_scrolls, text="Deep Scroll (mensagens):", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.entry_scrolls = ctk.CTkEntry(frame_scrolls, placeholder_text="Padrão: 20")
        self.entry_scrolls.pack(fill="x")


        # --- Presets ---
        ctk.CTkLabel(scroll, text="📦 Presets por Tipo de Negócio",
                      font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", pady=(15, 5))

        presets = self.config_manager.list_presets()
        preset_names = presets if presets else ["nenhum"]
        
        self.preset_var = ctk.StringVar(value="")
        self.preset_selector = ctk.CTkSegmentedButton(
            scroll, values=preset_names, variable=self.preset_var,
            command=self._load_preset_by_name
        )
        self.preset_selector.pack(fill="x", padx=15, pady=5)

        # --- Botão Salvar ---
        ctk.CTkButton(
            scroll, text="💾  Salvar Configuração",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color=COLOR_EMERALD,
            hover_color="#189e47",
            command=self._save_config,
        ).pack(fill="x", padx=15, pady=(20, 10))


    def _build_run_tab(self):
        """Aba de Execução."""
        tab = self.tab_run

        # --- Botões ---
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(15, 10))

        self.btn_start = ctk.CTkButton(
            btn_frame, text="⛏️  INICIAR MINERAÇÃO",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=45, fg_color=COLOR_EMERALD, hover_color="#189e47",
            command=self._start_extraction,
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 5))


        self.btn_stop = ctk.CTkButton(
            btn_frame, text="⏹  PARAR",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=45, width=140, fg_color="#c0392b", hover_color="#96281b",
            command=self._stop_extraction,
            state="disabled",
        )
        self.btn_stop.pack(side="left")

        # --- Stats ---
        stats_frame = ctk.CTkFrame(tab)
        stats_frame.pack(fill="x", padx=10, pady=5)

        stats_grid = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_grid.pack(fill="x", padx=15, pady=10)

        self.lbl_processed = self._stat_label(stats_grid, "Processados", "0", 0)
        self.lbl_leads = self._stat_label(stats_grid, "Leads", "0", 1)
        self.lbl_rate = self._stat_label(stats_grid, "Taxa", "0%", 2)
        self.lbl_time = self._stat_label(stats_grid, "Tempo", "00:00", 3)

        stats_grid.columnconfigure((0, 1, 2, 3), weight=1)

        # Progress bar
        self.progress = ctk.CTkProgressBar(tab, progress_color=COLOR_EMERALD)
        self.progress.pack(fill="x", padx=10, pady=5)
        self.progress.set(0)


        # --- Log ---
        ctk.CTkLabel(tab, text="📝 Log em Tempo Real",
                      font=ctk.CTkFont(size=13, weight="bold")).pack(
            anchor="w", padx=15, pady=(10, 3))

        self.log_box = ctk.CTkTextbox(tab, height=250, state="disabled",
                                       font=ctk.CTkFont(family="monospace", size=11))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        # --- Footer ---
        footer = ctk.CTkFrame(tab, fg_color="transparent")
        footer.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            footer, text="🗑️ Limpar Progresso",
            fg_color="gray30", hover_color="gray40",
            command=self._clear_progress, width=140,
        ).pack(side="left")

        ctk.CTkButton(
            footer, text="📥 Abrir CSV",
            command=self._open_csv, width=120,
        ).pack(side="right")

    def _stat_label(self, parent, title: str, value: str, col: int) -> ctk.CTkLabel:
        """Cria um label de estatística no grid."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=col, padx=5, sticky="ew")

        ctk.CTkLabel(frame, text=title.upper(), text_color=COLOR_EMERALD,
                      font=ctk.CTkFont(size=10, weight="bold")).pack()
        lbl = ctk.CTkLabel(frame, text=value, text_color=COLOR_GOLD,
                            font=ctk.CTkFont(size=22, weight="bold"))
        lbl.pack()
        return lbl

    # =====================================================================
    # AÇÕES
    # =====================================================================

    def _save_config(self):
        """Salva a configuração atual da GUI no config.json."""
        config = self._collect_config()
        self.config_manager.save(config)
        self.config = config
        self.add_log("💾 Configuração salva com sucesso!")

    def _collect_config(self) -> dict:
        """Coleta todos os valores da GUI e monta o dicionário de config."""
        include_labels = [
            label for label, var in self.include_vars.items() if var.get()
        ]
        exclude_labels = [
            label for label, var in self.exclude_vars.items() if var.get()
        ]

        blacklist_text = self.entry_blacklist.get().strip()
        blacklist = [
            n.strip() for n in blacklist_text.split(",") if n.strip()
        ] if blacklist_text else []

        chrome_bin = self.entry_chrome_bin.get().strip() or "auto"
        
        import re
        raw_number = re.sub(r'\D', '', self.entry_number.get())

        auto_names_text = self.entry_auto_names.get().strip()
        auto_names = [n.strip() for n in auto_names_text.split(",")] if auto_names_text else []

        try:
            max_c = int(self.entry_max_contacts.get() or 0)
        except ValueError:
            max_c = 0

        try:
            scr = int(self.entry_scrolls.get() or 20)
        except ValueError:
            scr = 20

        return {
            "business_name": self.entry_business.get().strip() or "Meu Negócio",
            "own_number": raw_number,
            "chrome": {
                "mode": self.chrome_mode_var.get(),
                "profile_path": self.entry_chrome_profile.get().strip() or "~/.config/google-chrome/Default",
                "binary": chrome_bin,
            },
            "labels": {
                "include": include_labels,
                "exclude": exclude_labels,
            },
            "filter_mode": self.filter_mode_var.get(),
            "keywords": self.config.get("keywords", {}),
            "auto_lead_names": auto_names,
            "blacklist_names": blacklist,
            "scraper": {
                "max_contacts": max_c if max_c > 0 else None,
                "internal_scrolls": scr
            },
        }


    def _load_config_to_ui(self):
        """Carrega a configuração atual nos campos da GUI."""
        c = self.config

        self.entry_business.delete(0, "end")
        self.entry_business.insert(0, c.get("business_name", ""))

        self.entry_number.delete(0, "end")
        self.entry_number.insert(0, c.get("own_number", ""))

        chrome = c.get("chrome", {})
        self.chrome_mode_var.set(chrome.get("mode", "profile"))
        
        self.entry_chrome_bin.delete(0, "end")
        chrome_bin = chrome.get("binary", "auto")
        if chrome_bin != "auto":
            self.entry_chrome_bin.insert(0, chrome_bin)

        self.entry_chrome_profile.delete(0, "end")
        self.entry_chrome_profile.insert(0, chrome.get("profile_path", ""))

        self.filter_mode_var.set(c.get("filter_mode", "labels"))

        # Labels
        inc_labels = c.get("labels", {}).get("include", [])
        for label, var in self.include_vars.items():
            var.set(label in inc_labels)

        exc_labels = c.get("labels", {}).get("exclude", [])
        for label, var in self.exclude_vars.items():
            var.set(label in exc_labels)

        blacklist = c.get("blacklist_names", [])
        self.entry_blacklist.delete(0, "end")
        self.entry_blacklist.insert(0, ", ".join(blacklist))

        auto_names = c.get("auto_lead_names", [])
        self.entry_auto_names.delete(0, "end")
        self.entry_auto_names.insert(0, ", ".join(auto_names))

        scr_cfg = c.get("scraper", {})
        self.entry_max_contacts.delete(0, "end")
        m_c = scr_cfg.get("max_contacts")
        if m_c: self.entry_max_contacts.insert(0, str(m_c))

        self.entry_scrolls.delete(0, "end")
        self.entry_scrolls.insert(0, str(scr_cfg.get("internal_scrolls", 20)))


    def _load_preset_by_name(self, value):
        """Carrega e aplica o preset clicado pelo botão."""
        if value and value != "nenhum":
            try:
                preset_data = self.config_manager.load_preset(value)
                # Remover dados específicos do usuário para não sobescrever
                preset_data.pop("own_number", None)
                preset_data.pop("chrome", None)
                
                # Merge into current config
                self.config.update(preset_data)
                self._load_config_to_ui()
                self.add_log(f"📥 Preset '{value}' carregado com sucesso!")
                
                # Reseta a seleção do botão
                self.preset_var.set("")
            except FileNotFoundError as e:
                self.add_log(f"❌ {e}")

    def _add_custom_include(self):
        """Adiciona etiqueta personalizada na lista de inclusão."""
        text = self.entry_custom_include.get().strip()
        if not text or text in self.include_vars:
            return
        var = ctk.BooleanVar(value=True)
        self.include_vars[text] = var
        ctk.CTkCheckBox(
            self.include_frame, text=text, variable=var,
            checkbox_width=20, checkbox_height=20,
        ).pack(anchor="w", padx=15, pady=1)
        self.entry_custom_include.delete(0, "end")

    def _add_custom_exclude(self):
        """Adiciona etiqueta personalizada na lista de exclusão."""
        text = self.entry_custom_exclude.get().strip()
        if not text or text in self.exclude_vars:
            return
        var = ctk.BooleanVar(value=True)
        self.exclude_vars[text] = var
        ctk.CTkCheckBox(
            self.exclude_frame, text=text, variable=var,
            checkbox_width=20, checkbox_height=20,
        ).pack(anchor="w", padx=15, pady=1)
        self.entry_custom_exclude.delete(0, "end")

    def _start_extraction(self):
        """Inicia a extração em uma thread separada."""
        if self.running:
            return

        # Salvar config primeiro
        self._save_config()

        self.miner = None
        self.running = True
        self.start_time = time.time()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.progress.set(0)
        self.add_log("🚀 Iniciando extração...")

        # Ir para aba de execução
        self.tabview.set("🚀 Execução")

        # Iniciar timer
        self._update_timer()

        # Rodar em thread separada (Selenium bloqueia)
        self.extraction_thread = threading.Thread(
            target=self._run_extraction, daemon=True
        )
        self.extraction_thread.start()

    def _run_extraction(self):
        """Executa a extração (roda em thread separada)."""
        try:
            self.miner = LeadMinerFacade()
            gui_observer = GUIObserver(self)
            self.miner.set_gui_observer(gui_observer)
            self.miner.start()
        except Exception as e:
            self.after(0, self.add_log, f"❌ Erro: {str(e)}")
        finally:
            self.after(0, self._on_extraction_done)

    def _stop_extraction(self):
        """Para a extração."""
        if self.miner:
            self.miner.stop()
        self.add_log("⏹ Parando extração...")

    def _on_extraction_done(self):
        """Callback quando a extração termina."""
        self.running = False
        if self.timer_job:
            self.after_cancel(self.timer_job)
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")

        if self.miner:
            self.miner.cleanup()

        self.add_log("✅ Extração finalizada!")

    def _clear_progress(self):
        """Limpa dados de progresso para recomeço."""
        from infra.exporters import CSVExporter
        exporter = CSVExporter()
        exporter.limpar_dados()
        self.add_log("🗑️ Progresso limpo!")
        self.update_stats(0, 0)
        self.progress.set(0)

    def _open_csv(self):
        """Abre o CSV no programa padrão."""
        csv_path = os.path.join(BASE_DIR, "data", "leads_remarketing.csv")
        if os.path.exists(csv_path):
            os.system(f'xdg-open "{csv_path}" &')
            self.add_log(f"📂 Abrindo {csv_path}")
        else:
            self.add_log("❌ Nenhum CSV encontrado ainda")

    def on_finished(self, data: dict):
        """Callback do Observer para o evento 'finished'."""
        processed = data.get("processed", 0)
        total_leads = data.get("total_leads", 0)
        rate = data.get("rate", "0%")
        self.update_stats(processed, total_leads)
        self.lbl_rate.configure(text=rate)
        self.progress.set(1.0)

    # =====================================================================
    # ATUALIZAÇÕES DE UI
    # =====================================================================

    def add_log(self, message: str):
        """Adiciona mensagem ao log da GUI."""
        self.log_box.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.log_box.insert("end", f"{ts} | {message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def update_stats(self, processed: int = None, leads: int = None):
        """Atualiza os contadores de estatísticas."""
        if processed is not None:
            self.lbl_processed.configure(text=str(processed))
        if leads is not None:
            self.lbl_leads.configure(text=str(leads))
            if processed and processed > 0:
                rate = f"{(leads / processed) * 100:.1f}%"
                self.lbl_rate.configure(text=rate)

    def _update_timer(self):
        """Atualiza o timer de tempo decorrido."""
        if self.running and self.start_time:
            elapsed = int(time.time() - self.start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.lbl_time.configure(text=f"{mins:02d}:{secs:02d}")
            self.timer_job = self.after(1000, self._update_timer)


    def _format_phone(self, *args):
        """Formata automaticamente o número no entry em tempo real."""
        if getattr(self, "_is_formatting", False):
            return
            
        raw = self.number_var.get()
        import re
        digits = re.sub(r'\D', '', raw)
        
        if not digits:
            if raw != "":
                self._is_formatting = True
                self.number_var.set("")
                self._is_formatting = False
            return
            
        cursor_pos = self.entry_number.index(ctk.INSERT)
        was_at_end = cursor_pos >= len(raw) - 1
            
        formatted = f"+{digits[:2]}"
        if len(digits) > 2:
            formatted += f" ({digits[2:4]})"
        if len(digits) > 4:
            if len(digits) > 9:
                formatted += f" {digits[4:9]}-{digits[9:13]}"
            else:
                formatted += f" {digits[4:]}"
                
        if raw != formatted:
            self._is_formatting = True
            self.number_var.set(formatted)
            self._is_formatting = False
            
            if was_at_end:
                self.entry_number.after(10, lambda: self.entry_number.icursor("end"))
            else:
                self.entry_number.after(10, lambda: self.entry_number.icursor(cursor_pos))


def run_gui():
    """Função de entrada para iniciar a GUI."""
    app = LeadMinerApp()
    app.mainloop()


if __name__ == "__main__":
    run_gui()
