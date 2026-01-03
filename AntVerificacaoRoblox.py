import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import shutil
import threading
import time

# --- CONFIGURAÇÕES ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

NOME_PASTA_ROBLOX_ROOT = "local_assets" 

# Diretórios Locais
DIRETORIO_BASE = os.path.dirname(os.path.abspath(__file__))
BIBLIOTECA_SEGURA = os.path.join(DIRETORIO_BASE, "MinhaBibliotecaRoblox")
PASTA_RPG_SEGURA = os.path.join(BIBLIOTECA_SEGURA, "RPG")

class RobloxAssetManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Roblox Asset Injector - RPG Backup & Sync")
        self.geometry("1100x650")
        self.minsize(900, 500)

        if not os.path.exists(PASTA_RPG_SEGURA):
            os.makedirs(PASTA_RPG_SEGURA)

        self.monitorando = False
        self.drag_data = {"item": None, "x": 0, "y": 0}

        # --- LAYOUT ---
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)

        # ESQUERDA
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="RPG MANAGER", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 10))
        ctk.CTkButton(self.sidebar, text="+ Add Arquivo", command=self.adicionar_arquivo).pack(pady=10, padx=20)
        ctk.CTkButton(self.sidebar, text="Nova Sub-Pasta", fg_color="gray", command=self.criar_pasta).pack(pady=5, padx=20)
        ctk.CTkButton(self.sidebar, text="Deletar Item", fg_color="#FF5555", hover_color="#DD3333", command=self.deletar_item).pack(pady=5, padx=20)

        # --- NAVEGAÇÃO ---
        ctk.CTkLabel(self.sidebar, text="Navegação:", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(20, 5))
        
        self.btn_open_safe = ctk.CTkButton(self.sidebar, text="📂 Abrir Backup (PC)", fg_color="#555555", hover_color="#333333", command=self.abrir_pasta_backup)
        self.btn_open_safe.pack(pady=5, padx=20)

        self.btn_open_roblox = ctk.CTkButton(self.sidebar, text="🚀 Abrir Pasta Roblox", fg_color="#3B8ED0", hover_color="#1F6AA5", command=self.abrir_pasta_destino_roblox)
        self.btn_open_roblox.pack(pady=5, padx=20)

        # --- SYNC ---
        ctk.CTkLabel(self.sidebar, text="Recuperação:", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(20, 5))
        self.lbl_info = ctk.CTkLabel(self.sidebar, text="Roblox atualizou?\nClique para re-enviar.", font=("Arial", 11), text_color="gray")
        self.lbl_info.pack(pady=5)
        
        self.btn_sync = ctk.CTkButton(self.sidebar, text="RE-ENVIAR ARQUIVOS", fg_color="#00AA00", hover_color="#008800", height=40, command=self.sincronizar_manual)
        self.btn_sync.pack(pady=5, padx=20)

        ctk.CTkLabel(self.sidebar, text="Automático:", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10, 5))
        self.switch_monitor = ctk.CTkSwitch(self.sidebar, text="Auto-Sync", command=self.toggle_monitoramento)
        self.switch_monitor.pack(pady=5, padx=20)
        self.lbl_status_monitor = ctk.CTkLabel(self.sidebar, text="Parado", text_color="gray", font=("Arial", 10))
        self.lbl_status_monitor.pack(pady=0)

        # CENTRO
        self.center_frame = ctk.CTkFrame(self)
        self.center_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.center_frame.grid_rowconfigure(1, weight=1)
        self.center_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.center_frame, text="🗂️ Seus Arquivos (Salvos no PC)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.tree = ttk.Treeview(self.center_frame, selectmode='browse', show='tree')
        self.tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        sb = ctk.CTkScrollbar(self.center_frame, command=self.tree.yview)
        sb.grid(row=1, column=1, sticky="ns", pady=5)
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.bind("<<TreeviewSelect>>", self.ao_selecionar_arquivo)
        self.tree.bind("<ButtonPress-1>", self.on_drag_start)
        self.tree.bind("<B1-Motion>", self.on_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_drag_drop)

        # DIREITA
        self.preview_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.preview_frame.grid(row=0, column=2, rowspan=2, sticky="nsew")
        
        ctk.CTkLabel(self.preview_frame, text="ID / CAMINHO ROBLOX", font=ctk.CTkFont(weight="bold", size=14)).pack(pady=(40, 20))
        
        self.entry_path = ctk.CTkEntry(self.preview_frame, placeholder_text="Selecione um arquivo...")
        self.entry_path.pack(pady=5, padx=20, fill="x")
        
        self.btn_copy = ctk.CTkButton(self.preview_frame, text="Copiar ID", command=self.copiar_caminho)
        self.btn_copy.pack(pady=10, padx=20)
        
        self.lbl_explain = ctk.CTkLabel(self.preview_frame, text="Esse caminho só funciona\napós clicar em 'Re-Enviar'\nou usar o Auto-Sync.", text_color="#FF5555", font=("Arial", 11))
        self.lbl_explain.pack(pady=20, padx=20)

        self.popular_treeview()
        self.after(1000, self.sincronizar_manual)

    # --- DRAG AND DROP (CORRIGIDO) ---
    def on_drag_start(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return

        # Proíbe arrastar a pasta raiz (Mestre)
        parent_id = self.tree.parent(item_id)
        if parent_id == '':
            self.drag_data["item"] = None
            return

        self.drag_data["item"] = item_id

    def on_drag_motion(self, event):
        if self.drag_data["item"]: 
            self.configure(cursor="fleur")
        else:
            self.configure(cursor="")

    def on_drag_drop(self, event):
        self.configure(cursor="")
        origem = self.drag_data["item"]
        self.drag_data["item"] = None # Reseta
        
        if not origem: return
        
        destino = self.tree.identify_row(event.y)
        if not destino: return 
        
        # Pega caminhos
        path_origem = self.tree.item(origem)['values'][0]
        path_dest = self.tree.item(destino)['values'][0]
        
        # Se soltou em cima de arquivo, assume que quer por na pasta do arquivo
        if os.path.isfile(path_dest): 
            path_dest = os.path.dirname(path_dest)
        
        # --- VERIFICAÇÕES DE SEGURANÇA ---
        # 1. Se soltou no mesmo lugar
        if path_origem == path_dest:
            return 

        # 2. Se já está na pasta de destino (mover para onde já está)
        if os.path.dirname(path_origem) == path_dest:
            return

        # 3. Se é pasta, verifica se está tentando colocar dentro dela mesma
        if os.path.isdir(path_origem):
            # Se o destino começa com o caminho da origem, é um loop
            if path_dest.startswith(path_origem):
                messagebox.showwarning("Ação Bloqueada", "Você não pode mover uma pasta para dentro dela mesma.")
                return
        # -------------------------------

        try:
            shutil.move(path_origem, os.path.join(path_dest, os.path.basename(path_origem)))
            self.popular_treeview()
            self.sincronizar_manual()
        except Exception as e: 
            messagebox.showerror("Erro ao mover", str(e))

    # --- DEMAIS FUNÇÕES ---
    def ao_selecionar_arquivo(self, event):
        sel = self.tree.selection()
        if not sel: return
        item = self.tree.item(sel[0])
        caminho_real_pc = item['values'][0]
        rel_path = os.path.relpath(caminho_real_pc, BIBLIOTECA_SEGURA).replace("\\", "/")
        roblox_path = f"rbxasset://{NOME_PASTA_ROBLOX_ROOT}/{rel_path}"
        self.entry_path.delete(0, "end")
        self.entry_path.insert(0, roblox_path)

    def sincronizar_manual(self):
        self.lbl_explain.configure(text="Enviando arquivos...", text_color="yellow")
        self.update()
        threading.Thread(target=self._sync_process).start()

    def _sync_process(self):
        base_versions = os.path.expandvars(r'%LOCALAPPDATA%\Roblox\Versions')
        targets_found = []

        if os.path.exists(base_versions):
            for entry in os.scandir(base_versions):
                if entry.is_dir():
                    is_studio = os.path.exists(os.path.join(entry.path, "RobloxStudioBeta.exe"))
                    is_player = os.path.exists(os.path.join(entry.path, "RobloxPlayerBeta.exe"))
                    if is_studio or is_player:
                        content_path = os.path.join(entry.path, "content")
                        if os.path.exists(content_path):
                            dest_final = os.path.join(content_path, NOME_PASTA_ROBLOX_ROOT)
                            targets_found.append(dest_final)

        count = 0
        for target in targets_found:
            try:
                if os.path.exists(target): shutil.rmtree(target)
                shutil.copytree(BIBLIOTECA_SEGURA, target)
                count += 1
            except: pass

        if count > 0:
            self.lbl_explain.configure(text=f"Sucesso!\nAtualizado em {count} locais.", text_color="#00FF00")
        else:
            self.lbl_explain.configure(text="Erro: Roblox não achado.", text_color="red")

    def popular_treeview(self):
        abertos = []
        def salvar_estado(item):
            if self.tree.item(item, "open"):
                abertos.append(self.tree.item(item)['values'][0])
                for c in self.tree.get_children(item): salvar_estado(c)
        for i in self.tree.get_children(): salvar_estado(i)

        self.tree.delete(*self.tree.get_children())
        root = self.tree.insert('', 'end', text="Pasta RPG (Mestre)", open=True, values=(PASTA_RPG_SEGURA,))
        
        def ler_pasta(path, parent):
            try:
                for entry in os.scandir(path):
                    if entry.is_dir():
                        node = self.tree.insert(parent, 'end', text=f"📁 {entry.name}", open=entry.path in abertos, values=(entry.path,))
                        ler_pasta(entry.path, node)
                    elif entry.is_file():
                        icon = "🎵" if entry.name.endswith(('.mp3','.ogg')) else "🖼️"
                        self.tree.insert(parent, 'end', text=f"{icon} {entry.name}", values=(entry.path,))
            except: pass     
        ler_pasta(PASTA_RPG_SEGURA, root)

    def abrir_pasta_backup(self):
        os.startfile(PASTA_RPG_SEGURA)

    def abrir_pasta_destino_roblox(self):
        base = os.path.expandvars(r'%LOCALAPPDATA%\Roblox\Versions')
        caminho_encontrado = None
        if os.path.exists(base):
            vers = []
            for entry in os.scandir(base):
                if entry.is_dir() and os.path.exists(os.path.join(entry.path, "RobloxStudioBeta.exe")):
                    vers.append(entry.path)
            if vers:
                latest = max(vers, key=os.path.getmtime)
                target = os.path.join(latest, "content", NOME_PASTA_ROBLOX_ROOT)
                if os.path.exists(target): caminho_encontrado = target
                else: caminho_encontrado = os.path.join(latest, "content")

        if caminho_encontrado: os.startfile(caminho_encontrado)
        else: messagebox.showerror("Erro", "Pasta do Roblox não encontrada.\nFaça o 'Re-Enviar Arquivos' primeiro!")

    def adicionar_arquivo(self):
        sel = self.tree.selection()
        dest = self.tree.item(sel[0])['values'][0] if sel else PASTA_RPG_SEGURA
        if os.path.isfile(dest): dest = os.path.dirname(dest)
        arqs = filedialog.askopenfilenames()
        if arqs:
            for a in arqs: shutil.copy(a, dest)
            self.popular_treeview()
            self.sincronizar_manual()

    def criar_pasta(self):
        sel = self.tree.selection()
        dest = self.tree.item(sel[0])['values'][0] if sel else PASTA_RPG_SEGURA
        if os.path.isfile(dest): dest = os.path.dirname(dest)
        nome = simpledialog.askstring("Nova Pasta", "Nome:")
        if nome:
            os.makedirs(os.path.join(dest, nome), exist_ok=True)
            self.popular_treeview()
            self.sincronizar_manual()

    def deletar_item(self):
        sel = self.tree.selection()
        if not sel: return
        path = self.tree.item(sel[0])['values'][0]
        if path == PASTA_RPG_SEGURA: return
        if messagebox.askyesno("Apagar", "Confirma?"):
            if os.path.isdir(path): shutil.rmtree(path)
            else: os.remove(path)
            self.popular_treeview()
            self.sincronizar_manual()

    def toggle_monitoramento(self):
        self.monitorando = self.switch_monitor.get() == 1
        if self.monitorando:
            threading.Thread(target=self._monitor_loop, daemon=True).start()
            self.lbl_status_monitor.configure(text="Ativo", text_color="#00FF00")
        else:
            self.lbl_status_monitor.configure(text="Parado", text_color="gray")

    def _monitor_loop(self):
        while self.monitorando:
            time.sleep(5)
            self.sincronizar_manual()

    def copiar_caminho(self):
        if self.entry_path.get():
            self.clipboard_clear()
            self.clipboard_append(self.entry_path.get())
            messagebox.showinfo("Copiado", "Link copiado!")

if __name__ == "__main__":
    app = RobloxAssetManagerApp()
    app.mainloop()