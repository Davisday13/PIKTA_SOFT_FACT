def setup_cierre_history(self):
        """Configura la pestaña para ver el historial de cierres de caja."""
        for w in self.cierre_history_frame.winfo_children():
            w.destroy()

        # Logo Pik'ta en la cabecera
        logo_path = os.path.join('Imagenes', 'pikta2.png')
        if os.path.exists(logo_path):
            img = load_image(logo_path, size=(80, 80))
            if img:
                lbl = ttk.Label(self.cierre_history_frame, image=img)
                lbl.image = img
                lbl.pack(pady=5)

        ttk.Label(self.cierre_history_frame, text="📊 HISTORIAL DE CIERRES DE CAJA", font=(None, 18, 'bold')).pack(pady=10)

        main_c = ttk.Frame(self.cierre_history_frame)
        main_c.pack(fill='both', expand=True)

        # Lista de cierres (Lado Izquierdo)
        left = ttk.Frame(main_c, width=300)
        left.pack(side='left', fill='y', padx=10)

        ttk.Label(left, text="Seleccione un Cierre:", font=(None, 11, 'bold')).pack(pady=5)

        self.cierre_list = ttk.Treeview(left, columns=('ID', 'Fecha', 'Total'), show='headings', height=15)
        self.cierre_list.heading('ID', text='ID')
        self.cierre_list.heading('Fecha', text='Fecha')
        self.cierre_list.heading('Total', text='Total')
        self.cierre_list.column('ID', width=50)
        self.cierre_list.column('Fecha', width=150)
        self.cierre_list.column('Total', width=80)
        self.cierre_list.pack(fill='both', expand=True)

        # Vista del Reporte (Lado Derecho)
        right = ttk.Frame(main_c)
        right.pack(side='right', fill='both', expand=True, padx=10)

        ttk.Label(right, text="Vista del Reporte:", font=(None, 11, 'bold')).pack(pady=5)
        self.cierre_view = tk.Text(right, font=("Courier", 11), bg="#f0f0f0", state='disabled')
        self.cierre_view.pack(fill='both', expand=True)

        def on_cierre_select(e):
            sel = self.cierre_list.selection()
            if not sel: return
            cid = self.cierre_list.item(sel[0])['values'][0]

            res = self.db.fetch_one("SELECT reporte_texto FROM caja_sesiones WHERE id = ?", (cid,))
            if res:
                self.cierre_view.config(state='normal')
                self.cierre_view.delete('1.0', 'end')
                self.cierre_view.insert('1.0', res[0] or "Sin texto de reporte")
                self.cierre_view.config(state='disabled')

        self.cierre_list.bind('<<TreeviewSelect>>', on_cierre_select)

        # Botones de Acción
        btn_f = ttk.Frame(self.cierre_history_frame)
        btn_f.pack(fill='x', pady=10)

        ttk.Button(btn_f, text="🔄 ACTUALIZAR LISTA", command=self.refresh_cierres, bootstyle="info").pack(side='left', padx=10)

        def print_historical():
            txt = self.cierre_view.get('1.0', 'end-1c')
            if not txt.strip():
                messagebox.showwarning("Aviso", "Seleccione un cierre primero.")
                return
            
            temp_dir = os.path.join(os.environ.get('TEMP', 'C:\\temp'), 'PiktaInvoices')
            if not os.path.exists(temp_dir): os.makedirs(temp_dir)
            
            base_name = f"cierre_historial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filename = os.path.join(temp_dir, base_name)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(txt)
            os.startfile(filename)
            messagebox.showinfo("Impresión", "Reporte enviado a imprimir.")

        ttk.Button(btn_f, text="🖨 IMPRIMIR SELECCIONADO", command=print_historical, bootstyle="success").pack(side='left', padx=10)

        self.refresh_cierres()

    def refresh_cierres(self):
        """Actualiza la lista de cierres de caja."""
        if hasattr(self, 'cierre_list'):
            self.cierre_list.delete(*self.cierre_list.get_children())
            rows = self.db.fetch_all("SELECT id, cierre_at, cierre_total FROM caja_sesiones WHERE estado='CERRADO' ORDER BY id DESC")
            for r in rows:
                fecha = datetime.fromisoformat(r[1]).strftime('%d/%m/%Y %H:%M') if r[1] else "N/A"
                self.cierre_list.insert('', 'end', values=(r[0], fecha, f"${r[2]:.2f}"))

    def setup_admin_tools(self, parent):
        """Herramientas especiales para el administrador con un diseño destacado."""
        tools_frame = ttk.Frame(parent, padding=(0, 40, 0, 0))
        tools_frame.pack(fill='x', side='bottom')

        # Línea divisoria
        ttk.Separator(tools_frame, orient='horizontal').pack(fill='x', pady=20)

        ttk.Label(tools_frame, text="🛠️ Herramientas de Mantenimiento Avanzado", font=(None, 14, 'bold'), bootstyle="secondary").pack(anchor='w', padx=10, pady=(0, 15))
        
        btn_container = ttk.Frame(tools_frame)
        btn_container.pack(fill='x')
        
        # Botones con iconos y estilos claros
        btn_clear = ttk.Button(btn_container, text="🧹 LIMPIAR PEDIDOS (REINICIAR COCINA)", 
                  command=self.clear_all_orders, bootstyle="danger", padding=12)
        btn_clear.pack(side='left', padx=10)
        
        btn_reset = ttk.Button(btn_container, text="📦 REINICIAR INVENTARIO A CERO", 
                  command=self.reset_inventory, bootstyle="warning", padding=12)
        btn_reset.pack(side='left', padx=10)
        
        btn_backup = ttk.Button(btn_container, text="💾 CREAR RESPALDO DE SEGURIDAD (BACKUP)", 
                  command=self.manual_backup, bootstyle="success", padding=12)
        btn_backup.pack(side='left', padx=10)

        ttk.Label(tools_frame, text="Nota: Estas acciones son irreversibles. Use con precaución.", font=(None, 9, 'italic'), bootstyle="muted").pack(anchor='w', padx=15, pady=10)

    def clear_all_orders(self):
        """Elimina todos los pedidos de la base de datos para empezar de cero."""
        if messagebox.askyesno("Confirmar Limpieza", "¿Está seguro de eliminar TODOS los pedidos? Esta acción no se puede deshacer."):
            try:
                with self.db.get_connection() as conn:
                    conn.execute("DELETE FROM pedidos")
                messagebox.showinfo("Éxito", "Todos los pedidos han sido eliminados. La cocina está limpia.")
                # Si hay una instancia de KDS abierta, refrescarla si es posible
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo limpiar los pedidos: {e}")

    def reset_inventory(self):
        """Reinicia los valores de inventario a cero."""
        if messagebox.askyesno("Confirmar Reinicio", "¿Desea poner todas las existencias de inventario en cero?"):
            try:
                with self.db.get_connection() as conn:
                    conn.execute("UPDATE inventario SET cantidad = 0")
                messagebox.showinfo("Éxito", "Inventario reiniciado correctamente.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo reiniciar el inventario: {e}")

    