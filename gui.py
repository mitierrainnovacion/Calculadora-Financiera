import customtkinter as ctk
from tkinter import ttk
from tkinter import messagebox
import calculadora_financiera as cf
import pandas as pd
import copy

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# VENTANA DE DIÁLOGO PARA AÑADIR/EDITAR INVERSIONES
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
class InvestmentItemDialog(ctk.CTkToplevel):
    def __init__(self, parent, existing_item=None):
        super().__init__(parent)
        self.transient(parent)
        self.title("Elemento de Inversión")
        self.geometry("400x250")
        self.result = None

        self.item_label = ctk.CTkLabel(self, text="Item:")
        self.item_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.item_entry = ctk.CTkEntry(self, width=200)
        self.item_entry.grid(row=0, column=1, padx=20, pady=10)

        self.monto_label = ctk.CTkLabel(self, text="Monto:")
        self.monto_label.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.monto_entry = ctk.CTkEntry(self, width=200)
        self.monto_entry.grid(row=1, column=1, padx=20, pady=10)

        self.mes_label = ctk.CTkLabel(self, text="Mes:")
        self.mes_label.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.mes_entry = ctk.CTkEntry(self, width=200)
        self.mes_entry.grid(row=2, column=1, padx=20, pady=10)

        self.tag_label = ctk.CTkLabel(self, text="Tag Sensibilidad:")
        self.tag_label.grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.tag_entry = ctk.CTkEntry(self, width=200)
        self.tag_entry.grid(row=3, column=1, padx=20, pady=10)

        if existing_item:
            self.item_entry.insert(0, existing_item["item"])
            self.monto_entry.insert(0, existing_item["monto"])
            self.mes_entry.insert(0, existing_item["mes"])
            self.tag_entry.insert(0, existing_item["tag_sensibilidad"] if existing_item["tag_sensibilidad"] else "")

        self.ok_button = ctk.CTkButton(self, text="OK", command=self.on_ok)
        self.ok_button.grid(row=4, column=0, columnspan=2, pady=10)
        
        self.grab_set()
        self.wait_window()

    def on_ok(self):
        try:
            self.result = {
                "item": self.item_entry.get(),
                "monto": float(self.monto_entry.get()),
                "mes": int(self.mes_entry.get()),
                "tag_sensibilidad": self.tag_entry.get() if self.tag_entry.get() else None
            }
            self.destroy()
        except ValueError:
            messagebox.showerror("Error de Entrada", "Por favor, introduce valores numéricos válidos para Monto y Mes.")

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# CLASE PRINCIPAL DE LA APLICACIÓN
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Calculadora Financiera de Proyectos Inmobiliarios")
        self.geometry(f"{1800}x950")

        self.grid_columnconfigure(0, weight=0, minsize=900)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Barra lateral de parámetros
        self.sidebar_frame = ctk.CTkFrame(self, width=900, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_columnconfigure(0, weight=1) # Ensure contents fill width
        self.sidebar_frame.grid_propagate(False) # Force width=900
        self.sidebar_frame.grid_rowconfigure(1, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Parámetros del Proyecto", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.input_scrollable_frame = ctk.CTkScrollableFrame(self.sidebar_frame, label_text="")
        self.input_scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=5)
        self.input_scrollable_frame.grid_columnconfigure(0, weight=1)
        
        self.entries = {}
        self.create_input_widgets()

        self.calculate_button = ctk.CTkButton(self.sidebar_frame, text="Calcular Análisis", command=self.calculate_analysis)
        self.calculate_button.grid(row=2, column=0, padx=20, pady=10)

        # Panel principal de resultados
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.results_label = ctk.CTkLabel(self.main_frame, text="Resultados del Análisis", font=ctk.CTkFont(size=20, weight="bold"))
        self.results_label.grid(row=0, column=0, padx=20, pady=(10, 5))
        
        self.output_tabview = ctk.CTkTabview(self.main_frame, width=250)
        self.output_tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.output_tabview.add("Resumen")
        self.output_tabview.add("Proyección Operativa")
        self.output_tabview.add("Detalle Deuda")
        self.output_tabview.add("Sensibilidad VAN")
        self.output_tabview.add("Sensibilidad TIR")

        self._create_output_widgets()

    def _create_output_widgets(self):
        # --- Pestaña de Resumen ---
        summary_frame = self.output_tabview.tab("Resumen")
        summary_frame.grid_columnconfigure(0, weight=1)
        
        # Frame para resultados base
        base_results_frame = ctk.CTkFrame(summary_frame)
        base_results_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        base_results_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(base_results_frame, text="MÉTRICAS DEL PROYECTO (Escenario Base)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=5)
        
        self.base_results_labels = {
            "inv_total": self._create_result_label(base_results_frame, "Inversión Total Proyectada:", 1),
            "capital_requerido": self._create_result_label(base_results_frame, "Capital Propio Requerido:", 2),
            "wacc": self._create_result_label(base_results_frame, "WACC (Costo Promedio Capital):", 3),
            "van_proyecto": self._create_result_label(base_results_frame, "VAN del Proyecto (No Apalancado):", 4),
            "tir_proyecto": self._create_result_label(base_results_frame, "TIR del Proyecto (No Apalancado):", 5),
            "van_inversionista": self._create_result_label(base_results_frame, "VAN del Inversionista (Apalancado):", 6),
            "tir_inversionista": self._create_result_label(base_results_frame, "TIR del Inversionista (ROE esperado):", 7),
            "roi_total": self._create_result_label(base_results_frame, "Retorno sobre Inversión (ROI Total):", 8),
            "multiplo_capital": self._create_result_label(base_results_frame, "Múltiplo de Capital (MOIC):", 9),
        }
        
        # --- Pestañas de Sensibilidad ---
        van_sens_frame = self.output_tabview.tab("Sensibilidad VAN")
        ctk.CTkLabel(van_sens_frame, text="Sensibilidad del VAN del Inversionista", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        self.van_sensitivity_tree = self._create_treeview(van_sens_frame, ["Variable", "-20%", "-10%", "0%", "10%", "20%"])
        
        tir_sens_frame = self.output_tabview.tab("Sensibilidad TIR")
        ctk.CTkLabel(tir_sens_frame, text="Sensibilidad de la TIR del Inversionista", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        self.tir_sensitivity_tree = self._create_treeview(tir_sens_frame, ["Variable", "-20%", "-10%", "0%", "10%", "20%"])
        
        # --- Pestaña de Detalle Deuda ---
        deuda_frame = self.output_tabview.tab("Detalle Deuda")
        ctk.CTkLabel(deuda_frame, text="Cronograma de Amortización (Sistema Alemán)", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        # Resumen de Deuda (Totalizadores)
        self.deuda_summary_frame = ctk.CTkFrame(deuda_frame)
        self.deuda_summary_frame.pack(pady=5, padx=20, fill="x")
        
        self.total_interes_label = ctk.CTkLabel(self.deuda_summary_frame, text="Total Intereses: $ -", font=ctk.CTkFont(weight="bold"))
        self.total_interes_label.pack(side="left", padx=20)
        
        self.total_amort_label = ctk.CTkLabel(self.deuda_summary_frame, text="Total Amortización: $ -", font=ctk.CTkFont(weight="bold"))
        self.total_amort_label.pack(side="left", padx=20)

        self.deuda_tree = self._create_treeview(deuda_frame, ["Mes", "Saldo Inicial", "Intereses", "Amortización", "Saldo Final"])
        
        # --- Pestaña de Proyección Operativa ---
        proy_frame = self.output_tabview.tab("Proyección Operativa")
        ctk.CTkLabel(proy_frame, text="Proyección Mensual de Ventas y Gastos", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        self.proy_tree = self._create_treeview(proy_frame, [
            "Mes", "Lotes Vendidos", "Inventario", "Ingr. Pies", "Ingr. Cuotas (V)", "Otros Ingr.", "Ingr. Totales",
            "Gastos Dinámicos", "EBITDA"
        ])
        
    def _create_result_label(self, parent, text, row):
        ctk.CTkLabel(parent, text=text, anchor="w").grid(row=row, column=0, padx=10, pady=2, sticky="ew")
        value_label = ctk.CTkLabel(parent, text="-", anchor="e", font=ctk.CTkFont(weight="bold"))
        value_label.grid(row=row, column=1, padx=10, pady=2, sticky="ew")
        return value_label

    def create_input_widgets(self):
        default_params = cf.parametros

        # --- Inversión ---
        investment_frame = ctk.CTkFrame(self.input_scrollable_frame)
        investment_frame.pack(pady=10, padx=10, fill="x", expand=True)
        ctk.CTkLabel(investment_frame, text="Cronograma de Inversión (CAPEX)", font=ctk.CTkFont(weight="bold")).pack()
        
        self.investment_tree = self._create_treeview(investment_frame, ["Item", "Monto", "Mes", "Tag"])
        for item in default_params["cronograma_inversion"]:
            self.investment_tree.insert("", "end", values=(item["item"], item["monto"], item["mes"], item.get("tag_sensibilidad", "")))
            
        inv_button_frame = ctk.CTkFrame(investment_frame)
        inv_button_frame.pack(pady=5)
        ctk.CTkButton(inv_button_frame, text="Añadir", width=120, command=self._add_investment_item).pack(side="left", padx=5)
        ctk.CTkButton(inv_button_frame, text="Modificar", width=120, command=self._edit_investment_item).pack(side="left", padx=5)
        ctk.CTkButton(inv_button_frame, text="Eliminar", width=120, command=self._remove_investment_item, fg_color="red").pack(side="left", padx=5)

        # --- Ítems Periódicos ---
        periodic_frame = ctk.CTkFrame(self.input_scrollable_frame)
        periodic_frame.pack(pady=10, padx=10, fill="x", expand=True)
        ctk.CTkLabel(periodic_frame, text="Ingresos/Gastos Periódicos", font=ctk.CTkFont(weight="bold")).pack()
        
        self.periodic_tree = self._create_treeview(periodic_frame, ["Nombre", "Monto/%", "Base Cálculo", "Mes Ini", "Mes Fin", "Tipo"], height=6)
        
        periodic_btn_frame = ctk.CTkFrame(periodic_frame)
        periodic_btn_frame.pack(pady=5)
        ctk.CTkButton(periodic_btn_frame, text="Añadir Ítem", width=120, command=self._add_periodic_item).pack(side="left", padx=5)
        ctk.CTkButton(periodic_btn_frame, text="Eliminar", width=120, command=self._remove_periodic_item, fg_color="red").pack(side="left", padx=5)


        # --- Parámetros Simples ---
        self._create_simple_inputs(default_params)
        
    def _create_simple_inputs(self, params):
        # --- Frame de Parámetros Generales ---
        general_frame = ctk.CTkFrame(self.input_scrollable_frame)
        general_frame.pack(pady=10, padx=10, fill="x", expand=True)
        ctk.CTkLabel(general_frame, text="Configuración Global", font=ctk.CTkFont(weight="bold")).pack()
        self._create_entry(general_frame, "Meses del Proyecto", "horizonte_meses", params["horizonte_meses"])
        self._create_entry(general_frame, "Crecimiento Precio Lote % (Anual)", ("ventas", "crecimiento_precio_anual"), params["ventas"]["crecimiento_precio_anual"] * 100)

        # --- Planes de Venta ---
        planes_frame = ctk.CTkFrame(self.input_scrollable_frame)
        planes_frame.pack(pady=10, padx=10, fill="x", expand=True)
        ctk.CTkLabel(planes_frame, text="Planes de Venta (Inmobiliaria)", font=ctk.CTkFont(weight="bold")).pack()
        
        self.planes_tree = self._create_treeview(planes_frame, ["Nombre", "Tipo", "Mes Ini", "Lotes", "Vel.", "Pie", "Cuota", "Freq", "Cant"], height=4)
        for p_v in params.get("planes_venta", []):
            self.planes_tree.insert("", "end", values=(
                p_v["nombre"],
                p_v.get("tipo", "Dinámico"),
                p_v.get("mes_inicio", 1),
                p_v["cantidad_lotes"],
                p_v.get("velocidad", 0),
                p_v["monto_pie"],
                p_v["monto_cuota"],
                p_v["frecuencia"],
                p_v["cantidad_cuotas"]
            ))
        
        planes_btn_frame = ctk.CTkFrame(planes_frame)
        planes_btn_frame.pack(pady=5)
        ctk.CTkButton(planes_btn_frame, text="Añadir Plan", width=120, command=self._add_venta_plan).pack(side="left", padx=5)
        ctk.CTkButton(planes_btn_frame, text="Eliminar Plan", width=120, command=self._remove_venta_plan, fg_color="red").pack(side="left", padx=5)


        finan_frame = ctk.CTkFrame(self.input_scrollable_frame)
        finan_frame.pack(pady=10, padx=10, fill="x", expand=True)
        ctk.CTkLabel(finan_frame, text="Financiamiento y Fiscal", font=ctk.CTkFont(weight="bold")).pack()
        self._create_entry(finan_frame, "Monto de Préstamo ($)", ("financiamiento", "monto_deuda"), params["financiamiento"]["monto_deuda"])
        self._create_entry(finan_frame, "Tasa Deuda % (Anual)", ("financiamiento", "costo_deuda_anual"), params["financiamiento"]["costo_deuda_anual"] * 100)
        self._create_entry(finan_frame, "Plazo (meses)", ("financiamiento", "plazo_deuda_meses"), params["financiamiento"]["plazo_deuda_meses"])
        
        # Capitalización selector
        cap_frame = ctk.CTkFrame(finan_frame)
        cap_frame.pack(pady=4, padx=10, fill="x", expand=True)
        ctk.CTkLabel(cap_frame, text="Capitalización de Intereses", width=450, anchor="w").pack(side="left", padx=10)
        self.capitalizacion_var = ctk.StringVar(value=params["financiamiento"].get("capitalizacion", "Mensual"))
        cap_combo = ctk.CTkComboBox(cap_frame, values=["Mensual", "Trimestral", "Semestral", "Anual"], variable=self.capitalizacion_var, width=200)
        cap_combo.pack(side="left", padx=10, fill="x", expand=True)

        self._create_entry(finan_frame, "Costo Capital Propio %", ("financiamiento", "costo_capital_propio_anual"), params["financiamiento"]["costo_capital_propio_anual"] * 100)
        self._create_entry(finan_frame, "Impuesto Renta %", ("financiamiento", "tasa_impuesto_renta"), params["financiamiento"]["tasa_impuesto_renta"] * 100)
        
    def _create_entry(self, parent, label, key, default):
        frame = ctk.CTkFrame(parent)
        frame.pack(pady=4, padx=10, fill="x", expand=True)
        ctk.CTkLabel(frame, text=label, width=450, anchor="w", font=ctk.CTkFont(size=13)).pack(side="left", padx=10)
        entry = ctk.CTkEntry(frame, height=35, width=200) # Increased height and added base width
        entry.pack(side="left", fill="x", expand=True, padx=10)
        entry.insert(0, str(default))
        self.entries[key] = entry
        
    def _create_treeview(self, parent, columns, height=6):
        style = ttk.Style()
        style.theme_use("default")
        
        bg_color = self._get_appearance_mode_color(["#2a2d2e", "#e6e6e6"])
        fg_color = self._get_appearance_mode_color(["white", "black"])
        selected_bg_color = self._get_appearance_mode_color(["#22559b", "#9bbdd9"])
        
        style.configure("Treeview", background=bg_color, foreground=fg_color, fieldbackground=bg_color, borderwidth=0, font=('Calibri', 10))
        style.map('Treeview', background=[('selected', '#22559b')])
        style.configure("Treeview.Heading", background="#565b5e", foreground="white", font=('Calibri', 10,'bold'))
        
        tree = ttk.Treeview(parent, columns=columns, show='headings', height=height)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=80, anchor="center")
        tree.pack(pady=5, padx=5, fill="both", expand=True)
        return tree

    def _get_appearance_mode_color(self, colors):
        return colors[0] if ctk.get_appearance_mode() == "Dark" else colors[1]

    def _add_investment_item(self):
        dialog = InvestmentItemDialog(self)
        if dialog.result:
            self.investment_tree.insert("", "end", values=(dialog.result["item"], dialog.result["monto"], dialog.result["mes"], dialog.result["tag_sensibilidad"]))

    def _edit_investment_item(self):
        selected_id = self.investment_tree.selection()
        if not selected_id: return
        selected_values = self.investment_tree.item(selected_id[0], "values")
        existing_item = {"item": selected_values[0], "monto": selected_values[1], "mes": selected_values[2], "tag_sensibilidad": selected_values[3]}
        dialog = InvestmentItemDialog(self, existing_item)
        if dialog.result:
            self.investment_tree.item(selected_id[0], values=(dialog.result["item"], dialog.result["monto"], dialog.result["mes"], dialog.result["tag_sensibilidad"]))

    def _remove_investment_item(self):
        selected_id = self.investment_tree.selection()
        if not selected_id: return
        for item_id in selected_id:
            self.investment_tree.delete(item_id)
            
    def _add_periodic_item(self):
        dialog = PeriodicItemDialog(self)
        if dialog.result:
            self.periodic_tree.insert("", "end", values=(
                dialog.result["nombre"], 
                dialog.result["monto"], 
                dialog.result["base_calculo"],
                dialog.result["mes_inicio"], 
                dialog.result["mes_fin"], 
                dialog.result["tipo"]
            ))

    def _remove_periodic_item(self):
        selected_id = self.periodic_tree.selection()
        if not selected_id: return
        for item_id in selected_id:
            self.periodic_tree.delete(item_id)


    def _add_venta_plan(self):
        dialog = VentaPlanDialog(self)
        if dialog.result:
            self.planes_tree.insert("", "end", values=(
                dialog.result["nombre"], 
                dialog.result["tipo"],
                dialog.result["mes_inicio"],
                dialog.result["cantidad_lotes"],
                dialog.result["velocidad"],
                dialog.result["monto_pie"], 
                dialog.result["monto_cuota"], 
                dialog.result["frecuencia"], 
                dialog.result["cantidad_cuotas"]
            ))

    def _remove_venta_plan(self):
        selected_id = self.planes_tree.selection()
        if not selected_id: return
        for item_id in selected_id:
            self.planes_tree.delete(item_id)
    def calculate_analysis(self):
        try:
            params = self._get_params_from_gui()
            
            # Ejecutar modelo
            inv_total = cf.calcular_inversion_total(params)
            monto_deuda = params["financiamiento"]["monto_deuda"]
            monto_equity = inv_total - monto_deuda
            porc_deuda = monto_deuda / inv_total if inv_total > 0 else 0
            params["financiamiento"]["porcentaje_deuda"] = porc_deuda
            
            capex = cf.construir_cronograma_inversiones(params)
            deuda = cf.crear_tabla_amortizacion(params, monto_deuda)
            modelo_df = cf.generar_modelo_financiero_detallado(params, capex, deuda, monto_deuda)

            fcf_proyecto = modelo_df["FCF No Apalancado (FCFF)"]
            fcf_inversionista = modelo_df["Flujo Caja Neto Inversionista"]

            # DEBUGGING: Imprimir diagnostico de flujos
            print("\n--- DIAGNÓSTICO DE FLUJOS (GUI) ---")
            print(f"FCF Proyecto: Sum={fcf_proyecto.sum():,.2f}, Min={fcf_proyecto.min():,.2f}, Max={fcf_proyecto.max():,.2f}")
            print(f"FCF Inversionista: Sum={fcf_inversionista.sum():,.2f}, Min={fcf_inversionista.min():,.2f}, Max={fcf_inversionista.max():,.2f}")
            print(f"Deuda Total Input: {params['financiamiento']['monto_deuda']:,.2f}")
            print(f"Inversión Total: {inv_total:,.2f}")
            print("-----------------------------------")

            wacc = cf.WACC(params)
            ke = params["financiamiento"]["costo_capital_propio_anual"]
            
            van_p = cf.VAN(fcf_proyecto, wacc)
            tir_p = cf.TIR_anual(fcf_proyecto)
            van_i = cf.VAN(fcf_inversionista, ke)
            tir_i = cf.TIR_anual(fcf_inversionista)

            # Cálculo de Métricas Adicionales (ROI y Múltiplo)
            # El capital total invertido es la suma de todas las salidas (flujos negativos del inversionista)
            # Esto captura mejor las "llamadas de capital" diferidas si las hubiere.
            flujos_inv = fcf_inversionista.values
            invested_equity = sum(-f for f in flujos_inv if f < 0)  
            
            # Total retornado es la suma de todas las distribuciones positivas
            total_retornado = sum(f for f in flujos_inv if f > 0)
            
            multiplo = (total_retornado / invested_equity) if invested_equity > 0 else 0
            roi_total = ((total_retornado - invested_equity) / invested_equity) if invested_equity > 0 else 0

            # Actualizar GUI
            self.base_results_labels["inv_total"].configure(text=f"$ {inv_total:,.0f}")
            self.base_results_labels["capital_requerido"].configure(text=f"$ {monto_equity:,.0f}")
            self.base_results_labels["wacc"].configure(text=f"{wacc:.2%}")
            self.base_results_labels["van_proyecto"].configure(text=f"$ {van_p:,.0f}")
            self.base_results_labels["tir_proyecto"].configure(text=f"{tir_p:.2%}" if tir_p is not None else "N/A")
            self.base_results_labels["van_inversionista"].configure(text=f"$ {van_i:,.0f}")
            self.base_results_labels["tir_inversionista"].configure(text=f"{tir_i:.2%}" if tir_i is not None else "N/A")
            self.base_results_labels["roi_total"].configure(text=f"{roi_total:.2%}")
            self.base_results_labels["multiplo_capital"].configure(text=f"{multiplo:.2f}x")

            # Sensibilidad
            df_van, df_tir = self._run_sensitivity_analysis(params)
            self._update_sensitivity_treeview(self.van_sensitivity_tree, df_van, lambda x: f"$ {x:,.0f}")
            self._update_sensitivity_treeview(self.tir_sensitivity_tree, df_tir, lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
            
            self.output_tabview.set("Resumen")
            
            # 5. Actualizar Detalle de Deuda
            self._update_deuda_treeview(modelo_df)
            
            # 6. Actualizar Proyección Operativa
            self._update_proy_treeview(modelo_df)
            
            messagebox.showinfo("Éxito", "Análisis financiero completado.")

        except Exception as e:
            messagebox.showerror("Error", f"Error en el cálculo: {str(e)}")

    def _get_params_from_gui(self):
        params = copy.deepcopy(cf.parametros)
        params["horizonte_meses"] = int(self.entries["horizonte_meses"].get())
        params["ventas"]["crecimiento_precio_anual"] = float(self.entries[("ventas", "crecimiento_precio_anual")].get()) / 100
        
        params["planes_venta"] = []
        for item_id in self.planes_tree.get_children():
            v = self.planes_tree.item(item_id, "values")
            params["planes_venta"].append({
                "nombre": v[0],
                "tipo": v[1],
                "mes_inicio": int(v[2]),
                "cantidad_lotes": int(v[3]),
                "velocidad": int(v[4]),
                "monto_pie": float(v[5]),
                "monto_cuota": float(v[6]),
                "frecuencia": int(v[7]),
                "cantidad_cuotas": int(v[8])
            })
        params["financiamiento"]["monto_deuda"] = float(self.entries[("financiamiento", "monto_deuda")].get())
        params["financiamiento"]["costo_deuda_anual"] = float(self.entries[("financiamiento", "costo_deuda_anual")].get()) / 100
        params["financiamiento"]["plazo_deuda_meses"] = int(self.entries[("financiamiento", "plazo_deuda_meses")].get())
        params["financiamiento"]["capitalizacion"] = self.capitalizacion_var.get()
        params["financiamiento"]["costo_capital_propio_anual"] = float(self.entries[("financiamiento", "costo_capital_propio_anual")].get()) / 100
        params["financiamiento"]["tasa_impuesto_renta"] = float(self.entries[("financiamiento", "tasa_impuesto_renta")].get()) / 100
        
        params["cronograma_inversion"] = []
        for item_id in self.investment_tree.get_children():
            v = self.investment_tree.item(item_id, "values")
            params["cronograma_inversion"].append({"item": v[0], "monto": float(v[1]), "mes": int(v[2]), "tag_sensibilidad": v[3] if v[3] else None})
            
        params["items_periodicos"] = []
        for item_id in self.periodic_tree.get_children():
            v = self.periodic_tree.item(item_id, "values")
            params["items_periodicos"].append({
                "nombre": v[0], 
                "monto": float(v[1]), 
                "base_calculo": v[2],
                "mes_inicio": int(v[3]), 
                "mes_fin": int(v[4]), 
                "tipo": v[5]
            })
            
        return params

    def _update_deuda_treeview(self, df):
        for item in self.deuda_tree.get_children():
            self.deuda_tree.delete(item)
        
        total_interes = 0
        total_amort = 0
        
        # Filtrar solo meses con saldo o actividad de deuda
        # Saldo Deuda inicial está en t=0
        for mes in df.index:
            saldo_inicial = df.loc[mes-1, "Saldo Deuda"] if mes > 0 else 0
            interes = df.loc[mes, "Intereses"]
            amort = abs(df.loc[mes, "Amortización Principal"])
            saldo_final = df.loc[mes, "Saldo Deuda"]
            
            total_interes += interes
            total_amort += amort
            
            # Mostrar solo si hay deuda o si es el mes de entrada (t=0)
            if mes == 0 or saldo_inicial > 0 or amort > 0:
                self.deuda_tree.insert("", "end", values=(
                    mes,
                    f"$ {saldo_inicial:,.0f}",
                    f"$ {interes:,.0f}",
                    f"$ {amort:,.0f}",
                    f"$ {saldo_final:,.0f}"
                ))
        
        self.total_interes_label.configure(text=f"Total Intereses: $ {total_interes:,.0f}")
        self.total_amort_label.configure(text=f"Total Amortización: $ {total_amort:,.0f}")

    def _run_sensitivity_analysis(self, p_base):
        escenarios = {
            "Crecimiento Precio": ("ventas", "crecimiento_precio_anual"),
            "Tasa Préstamo": ("financiamiento", "costo_deuda_anual"),
            "Monto Préstamo": ("financiamiento", "monto_deuda"),
        }
        variaciones = [-0.2, -0.1, 0.0, 0.1, 0.2]
        res = []
        for var_name, (sec, key) in escenarios.items():
            for v in variaciones:
                p = copy.deepcopy(p_base)
                if sec == "cronograma_inversion":
                    for item in p[sec]:
                        if item.get("tag_sensibilidad") == key: item["monto"] *= (1+v)
                else: p[sec][key] = p[sec][key] * (1+v)
                
                inv = cf.calcular_inversion_total(p)
                mto_d = p["financiamiento"]["monto_deuda"]
                cpx = cf.construir_cronograma_inversiones(p)
                deu = cf.crear_tabla_amortizacion(p, mto_d)
                mod = cf.generar_modelo_financiero_detallado(p, cpx, deu, mto_d)
                flj = mod["Flujo Caja Neto Inversionista"]
                ke = p["financiamiento"]["costo_capital_propio_anual"]
                res.append({"Variable": var_name, "Var": f"{v:+.0%}", "VAN": cf.VAN(flj, ke), "TIR": cf.TIR_anual(flj)})
        
        df = pd.DataFrame(res)
        return df.pivot(index="Variable", columns="Var", values="VAN"), df.pivot(index="Variable", columns="Var", values="TIR")

    def _update_sensitivity_treeview(self, tree, df, format_func):
        tree["columns"] = ["Variable"] + df.columns.tolist()
        for col in tree["columns"]:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="center")
        tree.column("Variable", width=150, anchor="w")
        for item in tree.get_children(): tree.delete(item)
        for idx, row in df.iterrows():
            tree.insert("", "end", values=[idx] + [format_func(x) for x in row.values])

    def _update_proy_treeview(self, df):
        for item in self.proy_tree.get_children():
            self.proy_tree.delete(item)
            
        for mes in df.index:
            # Mostrar solo si hay actividad o es el principio
            if mes == 0 or df.loc[mes, "Ingresos Totales"] != 0 or df.loc[mes, "Costos Operativos Dinámicos"] != 0:
                self.proy_tree.insert("", "end", values=(
                    mes,
                    f"{df.loc[mes, 'Lotes Vendidos']:.0f}",
                    f"{df.loc[mes, 'Lotes en Inventario']:.0f}",
                    f"$ {df.loc[mes, 'Ingresos Ventas Pies']:,.0f}",
                    f"$ {df.loc[mes, 'Ingresos Ventas Cuotas']:,.0f}",
                    f"$ {df.loc[mes, 'Otros Ingresos']:,.0f}",
                    f"$ {df.loc[mes, 'Ingresos Totales']:,.0f}",
                    f"$ {df.loc[mes, 'Costos Operativos Dinámicos']:,.0f}",
                    f"$ {df.loc[mes, 'EBITDA']:,.0f}"
                ))

class VentaPlanDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Nuevo Plan de Venta")
        self.geometry("450x650")
        self.result = None
        
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.grid_columnconfigure(0, weight=1)
        
        self._add_field("Nombre del Plan:", "nombre", "Ej: Lanzamiento")
        
        ctk.CTkLabel(self.scroll, text="Tipo de Plan:").pack(pady=(10, 0))
        self.tipo_var = ctk.StringVar(value="Dinámico")
        self.tipo_combo = ctk.CTkComboBox(self.scroll, values=["Dinámico", "Programado"], variable=self.tipo_var, command=self._on_type_change)
        self.tipo_combo.pack(pady=5, padx=20, fill="x")

        self._add_field("Mes de Inicio:", "mes_inicio", "1")
        self._add_field("Cantidad de Lotes:", "cantidad_lotes", "100")
        
        self.velocidad_label = ctk.CTkLabel(self.scroll, text="Velocidad (lotes/mes):")
        self.velocidad_label.pack(pady=(10, 0))
        self.velocidad_entry = ctk.CTkEntry(self.scroll)
        self.velocidad_entry.pack(pady=5, padx=20, fill="x")
        self.velocidad_entry.insert(0, "5")

        self._add_field("Monto del Pie ($):", "monto_pie", "30000")
        self._add_field("Monto de cada Cuota ($):", "monto_cuota", "2000")
        self._add_field("Frecuencia (cada N meses):", "frecuencia", "1")
        self._add_field("Cantidad de Cuotas:", "cantidad_cuotas", "60")
        
        ctk.CTkButton(self.scroll, text="Aceptar", command=self.on_accept).pack(pady=20)
        
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    def _on_type_change(self, value):
        if value == "Programado":
            self.velocidad_entry.configure(state="disabled", fg_color="gray")
        else:
            self.velocidad_entry.configure(state="normal", fg_color=["#F9F9FA", "#343638"])

    def _add_field(self, label_text, attr, default):
        ctk.CTkLabel(self.scroll, text=label_text).pack(pady=(10, 0))
        entry = ctk.CTkEntry(self.scroll)
        entry.pack(pady=5, padx=20, fill="x")
        entry.insert(0, default)
        setattr(self, f"{attr}_entry", entry)

    def on_accept(self):
        try:
            self.result = {
                "nombre": self.nombre_entry.get(),
                "tipo": self.tipo_var.get(),
                "mes_inicio": int(self.mes_inicio_entry.get()),
                "cantidad_lotes": int(self.cantidad_lotes_entry.get()),
                "velocidad": int(self.velocidad_entry.get()) if self.tipo_var.get() == "Dinámico" else 0,
                "monto_pie": float(self.monto_pie_entry.get()),
                "monto_cuota": float(self.monto_cuota_entry.get()),
                "frecuencia": int(self.frecuencia_entry.get()),
                "cantidad_cuotas": int(self.cantidad_cuotas_entry.get())
            }
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Por favor ingresa valores numéricos válidos.")

class PeriodicItemDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Ingreso/Gasto Periódico")
        self.geometry("400x550")
        self.result = None
        
        self.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self, text="Nombre Concepto:").pack(pady=(10, 0))
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(self, text="Tipo:").pack(pady=(10, 0))
        self.type_var = ctk.StringVar(value="Gasto")
        self.type_combo = ctk.CTkComboBox(self, values=["Ingreso", "Gasto"], variable=self.type_var)
        self.type_combo.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(self, text="Base de Cálculo:").pack(pady=(10, 0))
        self.base_var = ctk.StringVar(value="Monto Fijo")
        self.base_combo = ctk.CTkComboBox(self, values=["Monto Fijo", "% Ventas", "Por Lote Inventario", "% Utilidad"], variable=self.base_var)
        self.base_combo.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(self, text="Monto / Porcentaje:").pack(pady=(10, 0))
        self.amount_entry = ctk.CTkEntry(self)
        self.amount_entry.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(self, text="Mes Inicio:").pack(pady=(10, 0))
        self.start_entry = ctk.CTkEntry(self)
        self.start_entry.pack(pady=5, padx=20, fill="x")
        self.start_entry.insert(0, "1")
        
        ctk.CTkLabel(self, text="Mes Fin:").pack(pady=(10, 0))
        self.end_entry = ctk.CTkEntry(self)
        self.end_entry.pack(pady=5, padx=20, fill="x")
        self.end_entry.insert(0, "120")
        
        ctk.CTkButton(self, text="Aceptar", command=self.on_accept).pack(pady=20)
        
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    def on_accept(self):
        try:
            self.result = {
                "nombre": self.name_entry.get(),
                "monto": float(self.amount_entry.get()),
                "base_calculo": self.base_var.get(),
                "mes_inicio": int(self.start_entry.get()),
                "mes_fin": int(self.end_entry.get()),
                "tipo": self.type_var.get()
            }
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Entrada inválida. Verifica los números.")


if __name__ == "__main__":
    app = App()
    app.mainloop()
