import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
import numpy as np
import lasio
import segyio
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


from modules.file_scanner import LASFileScanner, SEGYFileScanner
from modules.curve_validator import CurveValidator
from modules.seismic_2d_validator import Seismic2DValidator
from modules.seismic_3d_validator import Seismic3DValidator


# ===================== LOG DETAIL POPUP WINDOW =====================
class LogDetailPopupWindow:
    """Popup window showing detailed log information with tabbed interface"""
    
    def __init__(self, parent, filepath, validator):
        self.filepath = filepath
        self.validator = validator
        
        self.window = tk.Toplevel(parent)
        self.window.title(f"Log Details - {os.path.basename(filepath)}")
        self.window.geometry("750x550")
        
        # Read LAS file once
        self.las = LASFileScanner.read_las_file(self.filepath)
        
        if not self.las:
            ttk.Label(
                self.window,
                text=f"Error: Unable to read LAS file\n{self.filepath}",
                font=("Segoe UI", 10),
                foreground="red"
            ).pack(expand=True)
            return
        
        # Get detailed curve information
        self.detailed_info = self.validator.get_detailed_curve_info(self.las)
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        self._create_information_tab()
        self._create_log_plot_tab()
    
    def _create_information_tab(self):
        """Create the Information tab with well details and curve information"""
        info_frame = ttk.Frame(self.notebook)
        self.notebook.add(info_frame, text="Information")
        
        # Header frame with well info
        header_frame = ttk.LabelFrame(info_frame, text="Well Information")
        header_frame.pack(fill="x", padx=10, pady=10)
        
        well_name = self.validator.get_well_name_from_las(self.las)
        depth_info = self.validator.get_depth_info_from_las(self.las)
        
        info_text = f"Well Name: {well_name}\n"
        info_text += f"File: {os.path.basename(self.filepath)}\n"
        info_text += f"Depth Range: {depth_info['start']} - {depth_info['stop']} {depth_info['depth_unit']} | LMF: {depth_info['lmf']} | ELZ: {depth_info['elz']}\n"
        info_text += f"Step: {depth_info['step']} {depth_info['depth_unit']}\n"
        info_text += f"PD: {depth_info['pd']} | EPD: {depth_info['epd']} | EKB: {depth_info['ekb']} | EGL: {depth_info['egl']}"
        
        ttk.Label(
            header_frame,
            text=info_text,
            font=("Segoe UI", 9),
            justify="left"
        ).pack(anchor="w", padx=10, pady=8)
        
        # Curve details frame
        detail_frame = ttk.LabelFrame(info_frame, text="Curve Details")
        detail_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Create treeview for curve details
        tree_frame = ttk.Frame(detail_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame)
        scrollbar.pack(side="right", fill="y")
        
        columns = ("Curve", "Mnemonic", "Min", "Max", "% Filled", "Unit", "Description")
        detail_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=15,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=detail_tree.yview)
        
        # Configure columns
        detail_tree.heading("Curve", text="Curve")
        detail_tree.heading("Mnemonic", text="Mnemonic")
        detail_tree.heading("Min", text="Min Value")
        detail_tree.heading("Max", text="Max Value")
        detail_tree.heading("% Filled", text="% Filled")
        detail_tree.heading("Unit", text="Unit")
        detail_tree.heading("Description", text="Description")
        
        detail_tree.column("Curve", width=80, anchor="center")
        detail_tree.column("Mnemonic", width=80, anchor="center")
        detail_tree.column("Min", width=100, anchor="center")
        detail_tree.column("Max", width=100, anchor="center")
        detail_tree.column("% Filled", width=80, anchor="center")
        detail_tree.column("Unit", width=70, anchor="center")
        detail_tree.column("Description", width=150, anchor="w")
        
        detail_tree.pack(fill="both", expand=True)
        
        # Populate treeview
        for curve_name, info in self.detailed_info.items():
            if info["found"]:
                tag = "found"
            else:
                tag = "missing"
            
            values = (
                curve_name,
                info["mnemonic"],
                info["min"],
                info["max"],
                info["percent_filled"] + "%" if info["percent_filled"] != "N/A" else "N/A",
                info["unit"],
                info["description"]
            )
            
            detail_tree.insert("", "end", values=values, tags=(tag,))
        
        # Apply tags for color coding
        detail_tree.tag_configure("found", foreground="green")
        detail_tree.tag_configure("missing", foreground="red")
        
        # Summary and Close button
        bottom_frame = ttk.Frame(info_frame)
        bottom_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        found_count = sum(1 for info in self.detailed_info.values() if info["found"])
        total_count = len(self.detailed_info)
        
        summary_text = f"Summary: {found_count}/{total_count} curves found"
        ttk.Label(bottom_frame, text=summary_text, font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
        
        ttk.Button(bottom_frame, text="Close", command=self.window.destroy).pack(side="right", padx=5)
    
    def _create_log_plot_tab(self):
        """Create the Log Plot tab with plot button and canvas"""
        plot_tab = ttk.Frame(self.notebook)
        self.notebook.add(plot_tab, text="Log Plot")
        
        # Info label
        info_label = ttk.Label(
            plot_tab,
            text="Click 'Plot Curves' to generate curve plots for all found curves",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        info_label.pack(pady=20)
        
        # Button frame
        btn_frame = ttk.Frame(plot_tab)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Plot Curves", command=self._plot_curves).pack(padx=5)
        
        # Placeholder for plot
        self.plot_container = ttk.Frame(plot_tab)
        self.plot_container.pack(fill="both", expand=True, padx=10, pady=10)
        
    def _plot_curves(self):
        """Plot all found curves in the Log Plot tab"""
        # Clear existing plot
        for widget in self.plot_container.winfo_children():
            widget.destroy()
        
        # Get only found curves
        found_curves = {name: info for name, info in self.detailed_info.items() if info["found"]}
        if not found_curves:
            messagebox.showwarning("No Data", "No curves found to plot.")
            return
        
        # Main scrollable frame
        main_frame = ttk.Frame(self.plot_container)
        main_frame.pack(fill="both", expand=True)
        
        # Create canvas and scrollbars
        scroll_canvas = tk.Canvas(main_frame)
        scroll_canvas.pack(side="left", fill="both", expand=True)
        
        v_scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=scroll_canvas.yview)
        v_scrollbar.pack(side="right", fill="y")
        
        h_scrollbar = ttk.Scrollbar(self.plot_container, orient="horizontal", command=scroll_canvas.xview)
        h_scrollbar.pack(side="bottom", fill="x")
        
        scroll_canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        # Inner frame for the plot
        canvas_frame = ttk.Frame(scroll_canvas)
        scroll_canvas.create_window((0, 0), window=canvas_frame, anchor="nw")
        
        # Create plots
        num_curves = len(found_curves)
        fixed_subplot_width_inch = 2.0
        total_width = num_curves * fixed_subplot_width_inch
        fig_height = 6
        
        fig, axes = plt.subplots(
            1, num_curves,
            figsize=(total_width, fig_height),
            sharey=True,
            gridspec_kw={'width_ratios': [1] * num_curves}
        )
        fig.suptitle(f"Well: {self.validator.get_well_name_from_las(self.las)}",
                    fontsize=9, fontweight='bold', y=0.995)
        
        if num_curves == 1:
            axes = [axes]
        
        depth_curve = self.las.index
        depth_info = self.validator.get_depth_info_from_las(self.las)
        depth_unit = depth_info['depth_unit']
        
        for idx, (curve_name, info) in enumerate(found_curves.items()):
            ax = axes[idx]
            mnemonic = info['mnemonic']
            try:
                curve_data = self.las[mnemonic]
                ax.plot(curve_data, depth_curve, color='black', linewidth=0.8)
                
                if idx == 0:
                    ax.set_ylabel(f'Depth ({depth_unit})', fontsize=9, fontweight='bold', rotation=90, ha='right')
                    ax.tick_params(axis='y', labelrotation=90)
                
                ax.set_xlabel(f'{curve_name}\n({info["unit"]})', fontsize=9)
                ax.set_title(f'{mnemonic}', fontweight='bold', fontsize=9, pad=3)
                ax.grid(True, alpha=0.3, linewidth=0.5)
                if idx == 0:
                    ax.invert_yaxis()
                ax.tick_params(axis='both', labelsize=5)
                
            except Exception as e:
                ax.text(0.5, 0.5, f'Error:\n{str(e)}',
                        ha='center', va='center', transform=ax.transAxes, fontsize=8)
                ax.set_title(f'{curve_name}\n(Error)', fontweight='bold', fontsize=9)
        
        # Embed into Tkinter
        canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(padx=20, pady=5)
        
        # Update scroll region
        def _update_scroll_region(event=None):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        canvas_frame.bind("<Configure>", _update_scroll_region)
        
        # Toolbar
        toolbar_frame = ttk.Frame(self.plot_container)
        toolbar_frame.pack(side="bottom", fill="x")
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        
        # Mousewheel scrolling
        def _on_mousewheel(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel)


# ===================== SETTINGS DIALOG =====================

class SettingsDialog:
    """Dialog for managing curve configuration and scan options"""
    
    def __init__(self, parent, current_config, config_file_path, filter_enabled, filter_text, callback):
        self.callback = callback
        self.current_config = current_config
        self.config_file_path = config_file_path
        
        self.window = tk.Toplevel(parent)
        self.window.title("Settings")
        self.window.geometry("600x450")
        
        # === Curve Configuration Section ===
        config_frame = ttk.LabelFrame(self.window, text="Curve Configuration")
        config_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # JSON file selection
        file_frame = ttk.Frame(config_frame)
        file_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(file_frame, text="Configuration File:").pack(side="left", padx=(0, 5))
        self.config_file_var = tk.StringVar()
        if config_file_path:
            self.config_file_var.set(os.path.basename(config_file_path))
        else:
            self.config_file_var.set("Using default configuration")
        ttk.Entry(file_frame, textvariable=self.config_file_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=5
        )
        ttk.Button(file_frame, text="Browse JSON...", command=self.browse_json).pack(side="left", padx=3)
        ttk.Button(file_frame, text="Edit", command=self.edit_config).pack(side="left", padx=3)
        
        # Display current config
        preview_label = ttk.Label(config_frame, text="Current Configuration Preview:")
        preview_label.pack(anchor="w", padx=10, pady=(5, 2))
        
        self.preview_text = scrolledtext.ScrolledText(
            config_frame,
            wrap=tk.WORD,
            width=60,
            height=8,
            font=("Consolas", 9),
            state="disabled"
        )
        self.preview_text.pack(fill="both", expand=True, padx=10, pady=5)
        self._update_preview()
        
        # === Scan Options Section ===
        options_frame = ttk.LabelFrame(self.window, text="Filename Filter Options")
        options_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Filter checkbox
        self.filter_enabled_var = tk.BooleanVar(value=filter_enabled)
        filter_check = ttk.Checkbutton(
            options_frame,
            text="Enable filename filter (only scan files containing the text below)",
            variable=self.filter_enabled_var,
            command=self._toggle_filter_entry
        )
        filter_check.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Filter text input
        filter_input_frame = ttk.Frame(options_frame)
        filter_input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ttk.Label(filter_input_frame, text="Filter text:").pack(side="left", padx=(0, 5))
        self.filter_text_var = tk.StringVar(value=filter_text)
        self.filter_entry = ttk.Entry(filter_input_frame, textvariable=self.filter_text_var, width=30)
        self.filter_entry.pack(side="left", padx=5)
        
        ttk.Label(
            filter_input_frame,
            text="(case-insensitive)",
            foreground="gray"
        ).pack(side="left", padx=5)
        
        # Set initial state
        self._toggle_filter_entry()
        
        # === Buttons ===
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="Apply", command=self.apply_settings).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.window.destroy).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Save Config As...", command=self.save_config).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Reset Default", command=self.reset_default).pack(side="left", padx=5)
    
    def _toggle_filter_entry(self):
        """Enable/disable filter text entry based on checkbox"""
        if self.filter_enabled_var.get():
            self.filter_entry.config(state="normal")
        else:
            self.filter_entry.config(state="disabled")
    
    def _update_preview(self):
        """Update the configuration preview text"""
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", tk.END)
        config_json = json.dumps(self.current_config, indent=2)
        self.preview_text.insert("1.0", config_json)
        self.preview_text.config(state="disabled")
    
    def browse_json(self):
        """Browse and load JSON configuration file"""
        filepath = filedialog.askopenfilename(
            title="Select Curve Configuration File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'r') as f:
                new_config = json.load(f)
            
            # Validate configuration
            self._validate_config(new_config)
            
            self.current_config = new_config
            self.config_file_path = filepath
            self.config_file_var.set(os.path.basename(filepath))
            self._update_preview()
            
            messagebox.showinfo("Success", f"Configuration loaded from:\n{filepath}")
        
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Error", f"Invalid JSON format:\n{str(e)}")
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration:\n{str(e)}")
    
    def edit_config(self):
        """Open text editor for manual configuration editing"""
        editor_window = tk.Toplevel(self.window)
        editor_window.title("Edit Configuration")
        editor_window.geometry("700x500")
        
        # Instructions
        ttk.Label(
            editor_window,
            text="Edit the curve configuration below (JSON format):",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Text editor
        text_editor = scrolledtext.ScrolledText(
            editor_window,
            wrap=tk.WORD,
            width=80,
            height=20,
            font=("Consolas", 10)
        )
        text_editor.pack(fill="both", expand=True, padx=10, pady=5)
        text_editor.insert("1.0", json.dumps(self.current_config, indent=2))
        
        # Buttons
        btn_frame = ttk.Frame(editor_window)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        def apply_edit():
            try:
                config_text = text_editor.get("1.0", tk.END)
                new_config = json.loads(config_text)
                self._validate_config(new_config)
                
                self.current_config = new_config
                self.config_file_path = None
                self.config_file_var.set("Manually edited configuration")
                self._update_preview()
                
                messagebox.showinfo("Success", "Configuration updated successfully!")
                editor_window.destroy()
            
            except json.JSONDecodeError as e:
                messagebox.showerror("JSON Error", f"Invalid JSON format:\n{str(e)}")
            except ValueError as e:
                messagebox.showerror("Validation Error", str(e))
        
        ttk.Button(btn_frame, text="Apply", command=apply_edit).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=editor_window.destroy).pack(side="left", padx=5)
        
        # Help text
        help_text = """
Format: {"CURVE_NAME": {"aliases": ["ALIAS1", "ALIAS2"], "description": "Description"}}
Example: {"GR": {"aliases": ["GR", "GAMMA"], "description": "Gamma Ray"}}
        """.strip()
        ttk.Label(editor_window, text=help_text, font=("Courier", 8), foreground="gray").pack(padx=10, pady=5)
    
    def save_config(self):
        """Save current configuration to JSON file"""
        filepath = filedialog.asksaveasfilename(
            title="Save Configuration As",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'w') as f:
                json.dump(self.current_config, f, indent=2)
            
            self.config_file_path = filepath
            self.config_file_var.set(os.path.basename(filepath))
            messagebox.showinfo("Success", f"Configuration saved to:\n{filepath}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration:\n{str(e)}")
    
    def reset_default(self):
        """Reset to default configuration"""
        default_config = {
            "GR": {
                "aliases": ["GR", "GAMMA", "GAPI"],
                "description": "Gamma Ray"
            },
            "DT": {
                "aliases": ["DT", "DTC", "AC"],
                "description": "Sonic Transit Time"
            },
            "RHOB": {
                "aliases": ["RHOB", "RHOZ", "DEN"],
                "description": "Bulk Density"
            },
            "NPHI": {
                "aliases": ["NPHI", "NPOR", "PHIN"],
                "description": "Neutron Porosity"
            }
        }
        
        self.current_config = default_config
        self.config_file_path = None
        self.config_file_var.set("Using default configuration")
        self._update_preview()
        messagebox.showinfo("Reset", "Configuration reset to default values.")
    
    def _validate_config(self, config):
        """Validate configuration structure"""
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")
        
        for key, value in config.items():
            if not isinstance(value, dict):
                raise ValueError(f"Each curve config must be a dictionary: {key}")
            if "aliases" not in value or "description" not in value:
                raise ValueError(f"Missing 'aliases' or 'description' for: {key}")
            if not isinstance(value["aliases"], list):
                raise ValueError(f"'aliases' must be a list for: {key}")
    
    def apply_settings(self):
        """Apply settings and close dialog"""
        filter_enabled = self.filter_enabled_var.get()
        filter_text = self.filter_text_var.get().strip()
        
        # Warn if filter is enabled but text is empty
        if filter_enabled and not filter_text:
            response = messagebox.askyesno(
                "Empty Filter Text",
                "Filter is enabled but filter text is empty. This will exclude all files.\n\n"
                "Do you want to disable the filter instead?"
            )
            if response:
                filter_enabled = False
                self.filter_enabled_var.set(False)
        
        self.callback(self.current_config, self.config_file_path, filter_enabled, filter_text)
        messagebox.showinfo("Settings Applied", "Settings have been applied successfully!")
        self.window.destroy()


# ===================== MAIN GUI TAB - LOG =====================

class LogDataCheckerTab:
    """Main tab for log data checking"""
    
    def __init__(self, parent):
        self.parent = parent
        self.curve_config = self._get_default_config()
        self.config_file_path = None
        self.filter_enabled = False
        self.filter_text = ""
        self.validator = CurveValidator(self.curve_config)
        self.file_paths = {}
        
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="Log")
        
        self._setup_ui()
    
    def _get_default_config(self):
        """Return default curve configuration"""
        return {
            "CALI": {
                "aliases": ["CALI", "CAL", "CALIPER", "HCAL", "CALX"],
                "description": "Caliper"
            },
            "GR": {
                "aliases": ["GR", "GAMMA", "GAPI"],
                "description": "Gamma Ray"
            },
            "RES D": {
                "aliases": ["RD", "RT", "LLD", "ILD", "RILD", "ID", "IND", "RDEP"],
                "description": "Resistivity Deep"
            },
            "RES S": {
                "aliases": ["RS", "RSH", "RTS", "RESS", "LLS", "SFL", "MSFL", "SN", "LN"],
                "description": "Resistivity Shallow"
            },
            "DT": {
                "aliases": ["DT", "DTC", "AC"],
                "description": "Sonic Transit Time"
            },
            "RHOB": {
                "aliases": ["RHOB", "RHOZ", "DEN"],
                "description": "Bulk Density"
            },
            "NPHI": {
                "aliases": ["NPHI", "NPOR", "PHIN"],
                "description": "Neutron Porosity"
            },
            "SP": {
                "aliases": ["SP"],
                "description": "Self Potential"
            },
            "PHID": {
                "aliases": ["PHID", "DPHI"],
                "description": "PHID"
            },
        }
    
    def clear_table(self):
        """Clear all table rows with confirmation"""
        if not self.tree.get_children():
            messagebox.showinfo("Info", "The table is already empty.")
            return

        confirm = messagebox.askyesno(
            "Confirm Clear", 
            "Are you sure you want to clear all results?"
        )
        if not confirm:
            return

        try:
            if hasattr(self, 'clear_btn'):
                self.clear_btn.config(state=tk.DISABLED)
            
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            self.file_paths.clear()
            self.status_var.set("Table cleared. Ready to scan.")
            
        finally:
            if hasattr(self, 'clear_btn'):
                self.clear_btn.config(state=tk.NORMAL)
    
    def export_to_csv(self):
        if not self.tree.get_children():
            messagebox.showinfo("No Data", "There's no data to export.")
            return

        try:
            # Ask user for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile="well_log_qc_report.csv",
                title="Export to CSV"
            )

            if not file_path:
                return  # User canceled the file dialog
            
            # Disable export button during processing
            self.export_btn.config(state=tk.DISABLED)
            self.status_var.set("Exporting data to CSV...")
            self.frame.update()

            # Process each file
            total_files = len(self.file_paths)
            processed = 0
        
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                # headers = [self.tree.heading(col)["text"] for col in self.tree["columns"]] + ["Curve", "Mnemonic", "Min", "Max", "% Filled", "Unit", "Description"]
                headers = [self.tree.heading(col)["text"] for col in self.tree["columns"]]
                writer.writerow(headers)

                # Write data
                for item_id in self.tree.get_children():
                    try:
                        # Update progress
                        processed += 1
                        self.status_var.set(f"Exporting {processed}/{total_files}: {os.path.basename(file_path)}")
                        self.frame.update()

                        values = self.tree.item(item_id)["values"]

                        writer.writerow(values)

                        # filepath = self.file_paths.get(item_id)
                        
                        # if filepath:
                        #     las = LASFileScanner.read_las_file(filepath)
                        #     if las:
                        #         detailed_info = self.validator.get_detailed_curve_info(las)
                                # for curve, info in detailed_info.items():
                                #     detail_row = [
                                #         curve,
                                #         info["mnemonic"],
                                #         info["min"],
                                #         info["max"],
                                #         info["percent_filled"],
                                #         info["unit"],
                                #         info["description"]
                                #     ]
                                #     writer.writerow(values + detail_row)
                        #     else:
                        #         writer.writerow(values + ["Error reading LAS file"] * len(headers))
                        # else:
                        #     writer.writerow(values + ["File path not found"] * len(headers))
                    
                    except Exception as e:
                        # Write error row for this file
                        writer.writerow([os.path.basename(file_path), f'Error: {str(e)}'] + ['N/A'] * (len(headers) - 2))
            
            self.status_var.set(f"Export complete: {total_files} files exported to CSV.")
            messagebox.showinfo("Export Successful", f"Data exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"An error occurred while exporting: {str(e)}")
        finally:
            self.export_btn.config(state=tk.NORMAL)

    def _setup_ui(self):
        """Setup the user interface"""
        # Folder selection frame
        top_frame = ttk.LabelFrame(self.frame, text="Select Data Folder")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        self.folder_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.folder_var).pack(
            side="left", fill="x", expand=True, padx=(10, 5), pady=5
        )
        ttk.Button(top_frame, text="Browse..", command=self.browse_folder).pack(side="left", padx=3)
        ttk.Button(top_frame, text="Scan", command=self.scan_folder).pack(side="left", padx=3)
        ttk.Button(top_frame, text="Settings", command=self.open_settings).pack(side="left", padx=3)
        
        # # Treeview for results
        # self.tree = ttk.Treeview(self.frame, show="headings", height=14)
        # self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        # self._setup_table_columns()

        # Frame for Treeview and Scrollbars
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        # Treeview for results
        self.tree = ttk.Treeview(tree_frame, show="headings", height=14)
        
        # Vertical Scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        
        # Horizontal Scrollbar
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=hsb.set)

        # Grid layout for Treeview and Scrollbars
        self.tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')

        # Configure grid weights
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self._setup_table_columns()
        
        # Bind double-click event
        self.tree.bind("<Double-Button-1>", self.on_row_double_click)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Double-click any row to see detailed log information.")
        ttk.Label(self.frame, textvariable=self.status_var, anchor="w").pack(fill="x", padx=10, pady=3)

        # Bottom button
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.export_btn = ttk.Button(btn_frame, text="Export", command=self.export_to_csv)
        self.export_btn.pack(side=tk.RIGHT, padx=5)
        
        self.clear_btn = ttk.Button(btn_frame, text="Clear Table", command=self.clear_table)
        self.clear_btn.pack(side=tk.RIGHT, padx=5)
    
    def on_row_double_click(self, event):
        """Handle double-click on tree row"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        
        if item_id in self.file_paths:
            filepath = self.file_paths[item_id]
            # Use LogDetailPopupWindow for LAS files
            LogDetailPopupWindow(self.frame, filepath, self.validator)
        else:
            messagebox.showwarning("Error", "Unable to find file path for selected row.")
    
    def _setup_table_columns(self):
        """Setup treeview columns based on current config"""
        columns = ["File", "Well Name", "Depth Unit", "PD", "EPD", "EKB", "EGL", "LMF", "ELZ", "Start", "Stop", "Step"] + list(self.curve_config.keys())
        self.tree["columns"] = columns
        
        for col in columns:
            self.tree.heading(col, text=col)
            if col == "File":
                width = 120
            elif col == "Well Name":
                width = 100
            elif col in ["PD", "EPD","EKB", "EGL", "LMF", "ELZ", "Start", "Stop", "Step"]:
                width = 50
            elif col == "Unit Depth":
                width = 50
            else:
                width = 50
            self.tree.column(col, anchor="center", width=width)

    def browse_folder(self):
        """Open folder browser dialog"""
        folder = filedialog.askdirectory(title="Select Log Data Folder")
        if folder:
            self.folder_var.set(folder)
            self.status_var.set(f"Selected folder: {folder}")
    
    def scan_folder(self):
        """Scan selected folder for LAS files and validate"""
        folder = self.folder_var.get()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return
        
        # Clear existing results
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.file_paths.clear()
        
        # Scan for LAS files with custom filter
        scanner = LASFileScanner(folder, self.filter_text, self.filter_enabled)
        las_files = scanner.find_all_las_files()
        
        if not las_files:
            filter_msg = ""
            if self.filter_enabled and self.filter_text:
                filter_msg = f" (filename filter: '{self.filter_text}')"
            messagebox.showinfo("No LAS Files", f"No .LAS files found in the selected folder{filter_msg}.")
            return
        
        # Process each file
        total = len(las_files)
        complete, missing = 0, 0
        
        for i, filepath in enumerate(las_files):
            self.status_var.set(f"Processing {i+1}/{total} LAS files...")
            self.frame.update()
            las = scanner.read_las_file(filepath)
            if not las:
                missing += 1
                continue
            
            # Validate curves
            result = self.validator.validate_las_file(las)
            
            # Extract well information
            file_name = os.path.basename(filepath)
            well_name = self.validator.get_well_name_from_las(las)
            depth_info = self.validator.get_depth_info_from_las(las)
            
            # Build table row
            values = [
                file_name, 
                well_name, 
                depth_info['depth_unit'],
                depth_info['pd'],
                depth_info['epd'],
                depth_info['ekb'],
                depth_info['egl'],
                depth_info['lmf'],
                depth_info['elz'],                
                depth_info['start'],
                depth_info['stop'],
                depth_info['step']                
            ]
            values += [result[key]["status"] for key in self.curve_config.keys()]
            
            item_id = self.tree.insert("", "end", values=values)
            
            # Store filepath for this row
            self.file_paths[item_id] = filepath
            
            # Count complete vs missing
            if all(r["status"] == "Y" for r in result.values()):
                complete += 1
            else:
                missing += 1
        
        filter_msg = ""
        if self.filter_enabled and self.filter_text:
            filter_msg = f" (filter: '{self.filter_text}')"
        
        self.status_var.set(
            f"Scan complete{filter_msg}: {total} LAS files. {complete} complete, {missing} with missing/invalid data. Double-click any row for details."
        )
    
    def open_settings(self):
        """Open settings dialog"""
        SettingsDialog(
            self.frame, 
            self.curve_config, 
            self.config_file_path, 
            self.filter_enabled,
            self.filter_text,
            self.update_settings
        )
    
    def update_settings(self, new_config, config_file_path, filter_enabled, filter_text):
        """Update curve configuration and scan options"""
        self.curve_config = new_config
        self.config_file_path = config_file_path
        self.filter_enabled = filter_enabled
        self.filter_text = filter_text
        self.validator.update_config(new_config)
        self._setup_table_columns()
        
        filter_status = f"ON ('{filter_text}')" if filter_enabled and filter_text else "OFF"
        self.status_var.set(f"Settings updated: {', '.join(self.curve_config.keys())} | Filter: {filter_status}")

# ===================== SEISMIC 3D DETAIL POPUP WINDOW (COMPREHENSIVE) =====================

class Seismic3DDetailPopupWindow:
    """Popup window showing comprehensive 3D seismic QC information with plotting"""
    
    def __init__(self, parent, filepath, validator):
        self.popup = tk.Toplevel(parent)
        self.popup.title(f"3D Seismic Details - {os.path.basename(filepath)}")
        self.popup.geometry("900x700")
        
        self.filepath = filepath
        self.validator = validator
        
        # Read SEGY file for plot ranges
        segy = SEGYFileScanner.read_segy_file(filepath, '3D')

        # Get comprehensive QC information
        self.qc_info = validator.get_comprehensive_info(segy)

        if segy:
            try:
                self.ilines = list(segy.ilines)
                self.xlines = list(segy.xlines)
                self.samples = list(segy.samples)
                self.inline_range = (min(self.ilines), max(self.ilines))
                self.crossline_range = (min(self.xlines), max(self.xlines))
            except:
                self.ilines = []
                self.xlines = []
                self.samples = []
                self.inline_range = (None, None)
                self.crossline_range = (None, None)
            segy.close()
        else:
            self.ilines = []
            self.xlines = []
            self.samples = []
            self.inline_range = (None, None)
            self.crossline_range = (None, None)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.popup)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab 1: Seismic Information
        self._create_information_tab()
        
        # Tab 2: Seismic Plot
        self._create_seismic_plot_tab()
        
        # Close button
        ttk.Button(self.popup, text="Close", command=self.popup.destroy).pack(pady=10)
    
    def _create_information_tab(self):
        """Create the Information tab with unified 3D Seismic Information (no outer scroll)"""
        info_tab = ttk.Frame(self.notebook)
        self.notebook.add(info_tab, text="Information")

        # --- Unified Information Section ---
        unified_frame = ttk.LabelFrame(
            info_tab, text="3D Seismic Information", padding=10
        )
        unified_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create Treeview for all parameters
        tree = ttk.Treeview(
            unified_frame,
            columns=("Parameter", "Value"),
            show="headings",
            height=25
        )
        tree.heading("Parameter", text="Parameter")
        tree.heading("Value", text="Value")
        tree.column("Parameter", width=300, anchor="w")
        tree.column("Value", width=480, anchor="w")

        # List of parameters
        all_parameters = [
            # --- Basic Information --- 
            # "Full Path"
            "Filename", "Total Traces",
            "Samples per Trace", "Sample Interval (ms)", "Trace Length (ms)",
            "Time Range", "Data Format", "Sorting",
            # --- 3D Geometry ---
            "Inline Range", "Crossline Range", "Inline Spacing",
            "Crossline Spacing", "Estimated Volume",
            # --- Signal Characteristics ---
            "Amplitude Range", "Amplitude Mean", "Amplitude Std Dev",
            "Nyquist Frequency (Hz)", "Dominant Frequency (Hz)",
            # --- Trace Quality ---
            "Null/Dead Traces", "Valid Traces",
            # --- Binary Header ---
            "Binary Format Code", "Trace Sorting", "Endian Type",
            "Measurement System"
        ]

        # Insert parameters and values
        for param in all_parameters:
            value = self.qc_info.get(param, "N/A")
            tree.insert("", "end", values=(param, value))

        # Add scrollbar (only for the tree)
        tree_scrollbar = ttk.Scrollbar(unified_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=tree_scrollbar.set)

        # Pack the tree and its scrollbar
        tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.pack(side="right", fill="y")

    def _create_seismic_plot_tab(self):
        """Create the Seismic Plot tab with controls and plot display"""
        self.plot_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.plot_tab, text="Seismic Plot")
        
        # Control Frame
        control_frame = ttk.LabelFrame(self.plot_tab, text="Plot Controls", padding=15)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # Line Type Selection
        ttk.Label(control_frame, text="Line Type:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.line_type_var = tk.StringVar(value="inline")
        line_type_frame = ttk.Frame(control_frame)
        line_type_frame.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        ttk.Radiobutton(line_type_frame, text="Inline", variable=self.line_type_var, 
                       value="inline", command=self._update_range_display).pack(side="left", padx=5)
        ttk.Radiobutton(line_type_frame, text="Crossline", variable=self.line_type_var, 
                       value="crossline", command=self._update_range_display).pack(side="left", padx=5)
        
        # Line Number/Index Input
        ttk.Label(control_frame, text="Line Number:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.line_number_var = tk.StringVar()
        line_entry = ttk.Entry(control_frame, textvariable=self.line_number_var, width=20)
        line_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        # Range display
        self.range_label = ttk.Label(control_frame, text="", foreground="blue")
        self.range_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=5)
        self._update_range_display()
        
        # Plot Button
        plot_button = ttk.Button(control_frame, text="Plot Seismic", 
                                command=self._plot_seismic, width=20)
        plot_button.grid(row=3, column=0, columnspan=2, pady=15)
        
        # Status Label
        self.status_label = ttk.Label(control_frame, text="Ready to plot", foreground="green")
        self.status_label.grid(row=4, column=0, columnspan=2)
        
        # Plot Container (for displaying plots within the tab)
        self.plot_container = ttk.Frame(self.plot_tab)
        self.plot_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Initial instructions
        instructions_frame = ttk.Frame(self.plot_container)
        instructions_frame.pack(expand=True)
        
        instruction_text = (
            "📊 Instructions:\n\n"
            "1. Select line type (Inline or Crossline)\n"
            "2. Enter the line number within the valid range\n"
            "3. Click 'Plot Seismic' to display the seismic section\n\n"
            "The plot will be displayed in this area."
        )
        ttk.Label(instructions_frame, text=instruction_text, justify="left", 
                 font=("Arial", 10), foreground="gray").pack(pady=20)
    
    def _update_range_display(self):
        """Update the range display based on selected line type"""
        if self.line_type_var.get() == "inline":
            if self.inline_range[0] is not None:
                range_text = f"Available Inline Range: {self.inline_range[0]} - {self.inline_range[1]}"
            else:
                range_text = "Inline range not available"
        else:
            if self.crossline_range[0] is not None:
                range_text = f"Available Crossline Range: {self.crossline_range[0]} - {self.crossline_range[1]}"
            else:
                range_text = "Crossline range not available"
        
        self.range_label.config(text=range_text)
    
    def _plot_seismic(self):
        """Plot seismic inline or crossline using segyio cube method"""
        
        line_type = self.line_type_var.get()
        line_number = self.line_number_var.get().strip()
        
        if not line_number:
            messagebox.showwarning("Input Required", "Please enter a line number")
            return
        
        try:
            line_number = int(line_number)
        except ValueError:
            messagebox.showerror("Invalid Input", "Line number must be an integer")
            return
        
        self.status_label.config(text="Loading seismic data...", foreground="orange")
        self.popup.update()
        
        try:
            # Clear previous plot
            for widget in self.plot_container.winfo_children():
                widget.destroy()
            
            # Show loading message
            loading_label = ttk.Label(
                self.plot_container, 
                text="Loading seismic data, please wait...", 
                font=("Arial", 12)
            )
            loading_label.pack(expand=True)
            self.popup.update()
            
            # Open SEGY file and read the entire 3D cube
            with segyio.open(self.filepath, 'r', ignore_geometry=False) as f:
                # Read the entire 3D data cube into a NumPy array
                data = segyio.tools.cube(f)
                
                # Get inline, crossline, and time/depth samples
                ilines = f.ilines
                xlines = f.xlines
                times = f.samples
                
                # Extract the requested slice
                if line_type == "inline":
                    # Validate inline number
                    if line_number not in ilines:
                        loading_label.destroy()
                        messagebox.showerror("Error", 
                                           f"Inline {line_number} not found in SEGY file.\n"
                                           f"Valid range: {min(ilines)} - {max(ilines)}")
                        self.status_label.config(text="Plot failed", foreground="red")
                        self._show_instructions()
                        return
                    
                    # Get inline index and extract slice
                    inline_index = list(ilines).index(line_number)
                    slice_data = data[inline_index, :, :]
                    
                    title = f"Inline {line_number}"
                    xlabel = "Crossline Number"
                    extent = [xlines.min(), xlines.max(), times.max(), times.min()]
                    
                else:  # crossline
                    # Validate crossline number
                    if line_number not in xlines:
                        loading_label.destroy()
                        messagebox.showerror("Error", 
                                           f"Crossline {line_number} not found in SEGY file.\n"
                                           f"Valid range: {min(xlines)} - {max(xlines)}")
                        self.status_label.config(text="Plot failed", foreground="red")
                        self._show_instructions()
                        return
                    
                    # Get crossline index and extract slice
                    crossline_index = list(xlines).index(line_number)
                    slice_data = data[:, crossline_index, :]
                    
                    title = f"Crossline {line_number}"
                    xlabel = "Inline Number"
                    extent = [ilines.min(), ilines.max(), times.max(), times.min()]
                
                # Remove loading message
                loading_label.destroy()
                
                # Create matplotlib figure
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Calculate amplitude range for symmetric colormap (use 99th percentile)
                vmax = np.percentile(np.abs(slice_data), 99)
                
                # Plot seismic data
                im = ax.imshow(slice_data.T, 
                              aspect='auto', 
                              cmap='seismic',
                              vmin=-vmax, 
                              vmax=vmax,
                              extent=extent,
                              interpolation='bilinear')
                
                ax.set_xlabel(xlabel, fontsize=11, fontweight='bold')
                ax.set_ylabel('Time (ms)' if times[0] < 10 else 'Depth', fontsize=11, fontweight='bold')
                ax.set_title(title, fontsize=12, fontweight='bold', pad=15)
                
                # Add colorbar
                cbar = plt.colorbar(im, ax=ax, label='Amplitude', pad=0.02)
                cbar.ax.tick_params(labelsize=9)
                
                # Add grid
                ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
                
                plt.tight_layout()
                
                # Embed plot in tkinter
                canvas = FigureCanvasTkAgg(fig, master=self.plot_container)
                canvas.draw()
                canvas_widget = canvas.get_tk_widget()
                canvas_widget.pack(fill="both", expand=True)
                
                # Add navigation toolbar
                toolbar_frame = ttk.Frame(self.plot_container)
                toolbar_frame.pack(fill="x", side="bottom")
                toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
                toolbar.update()
                
                # Save button
                def save_plot():
                    from tkinter import filedialog
                    filename = filedialog.asksaveasfilename(
                        defaultextension=".png",
                        filetypes=[("PNG files", "*.png"), 
                                  ("PDF files", "*.pdf"), 
                                  ("JPEG files", "*.jpg"),
                                  ("All files", "*.*")]
                    )
                    if filename:
                        fig.savefig(filename, dpi=300, bbox_inches='tight')
                        messagebox.showinfo("Success", f"Plot saved to:\n{filename}")
                
                # save_btn_frame = ttk.Frame(self.plot_container)
                # save_btn_frame.pack(fill="x", side="bottom", pady=5)
                # ttk.Button(save_btn_frame, text="Save Plot", 
                #           command=save_plot).pack(side="right", padx=10)
                
                self.status_label.config(text="Plot displayed successfully", foreground="green")
            
        except Exception as e:
            # Clear plot container
            for widget in self.plot_container.winfo_children():
                widget.destroy()
            
            # Show error
            self._show_error_in_plot_tab(f"Failed to plot seismic:\n{str(e)}")
            messagebox.showerror("Plot Error", f"Failed to plot seismic:\n{str(e)}")
            self.status_label.config(text="Plot failed", foreground="red")
            import traceback
            print(traceback.format_exc())
    
    def _show_instructions(self):
        """Show instructions in plot container"""
        instructions_frame = ttk.Frame(self.plot_container)
        instructions_frame.pack(expand=True)
        
        instruction_text = (
            "📊 Instructions:\n\n"
            "1. Select line type (Inline or Crossline)\n"
            "2. Enter the line number within the valid range\n"
            "3. Click 'Plot Seismic' to display the seismic section\n\n"
            "The plot will be displayed in this area."
        )
        ttk.Label(instructions_frame, text=instruction_text, justify="left", 
                 font=("Arial", 10), foreground="gray").pack(pady=20)
    
    def _show_error_in_plot_tab(self, error_msg):
        """Display error message in the plot tab"""
        error_frame = ttk.Frame(self.plot_container)
        error_frame.pack(expand=True)
        
        ttk.Label(
            error_frame,
            text="❌ Failed to plot seismic data",
            font=("Arial", 12, "bold"),
            foreground="red"
        ).pack(pady=10)
        
        ttk.Label(
            error_frame,
            text=error_msg,
            font=("Arial", 10),
            foreground="darkred",
            wraplength=600
        ).pack(pady=5)
    
    def _create_info_tree(self, parent, info_dict):
        """Create treeview for basic information"""
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=("Property", "Value"), show="headings", height=10)
        tree.heading("Property", text="Property")
        tree.heading("Value", text="Value")
        tree.column("Property", width=200, anchor="w")
        tree.column("Value", width=450, anchor="w")
        
        for key, value in info_dict.items():
            tree.insert("", "end", values=(key, value))
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_qc_tree(self, parent, qc_results, validator):
        """Create treeview for QC results"""
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True)
        
        tree = ttk.Treeview(tree_frame, columns=("Status", "Check", "Result"), show="headings", height=10)
        tree.heading("Status", text="Y/N")
        tree.heading("Check", text="QC Check")
        tree.heading("Result", text="Result")
        tree.column("Status", width=50, anchor="center")
        tree.column("Check", width=200, anchor="w")
        tree.column("Result", width=400, anchor="w")
        
        for key, result in qc_results.items():
            check_name = validator.qc_config[key]
            item_id = tree.insert("", "end", values=(
                result["status"],
                check_name,
                result["reason"]
            ))
            
            # Color code based on status
            if result["status"] == "N":
                tree.item(item_id, tags=("failed",))
        
        # Configure tag colors
        tree.tag_configure("failed", foreground="red")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class Seismic2DDetailPopupWindow:
    """Enhanced popup window showing comprehensive seismic information"""
    
    def __init__(self, parent, filepath, validator):
        self.popup = tk.Toplevel(parent)
        self.popup.title(f"2D Seismic Details - {os.path.basename(filepath)}")
        self.popup.geometry("1000x750")
        self.filepath = filepath
        self.validator = validator
        
        # Read SEGY file
        segy = SEGYFileScanner.read_segy_file(filepath, '2D')
        if not segy:
            messagebox.showerror("Error", f"Failed to read SEGY file:\n{filepath}")
            self.popup.destroy()
            return
        
        # Get comprehensive information
        self.comprehensive_info = validator.get_comprehensive_info(segy)
        
        # Close SEGY file early (will reopen for plotting if needed)
        segy.close()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.popup)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab 1: Information
        self._create_information_tab()
        
        # Tab 2: Seismic Plot
        self._create_seismic_plot_tab()
        
        # Button frame at bottom
        btn_frame = ttk.Frame(self.popup)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # # Add export button
        # ttk.Button(btn_frame, text="Export Info", 
        #           command=self._export_info).pack(side="left", padx=5)
        
        # Add close button
        ttk.Button(btn_frame, text="Close", 
                  command=self.popup.destroy).pack(side="right", padx=5)
    
    def _create_information_tab(self):
        info_tab = ttk.Frame(self.notebook)
        self.notebook.add(info_tab, text="Information")

        # Direct content placement (no canvas or scrollbar)
        info_frame = ttk.LabelFrame(info_tab, text="2D Seismic Information", padding=10)
        info_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Populate the info table/tree directly
        self._create_comprehensive_info_tree(info_frame, self.comprehensive_info)

    
    def _create_comprehensive_info_tree(self, parent, info_dict):
        """Create treeview for comprehensive information"""
        # Create frame for tree and scrollbar
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True)
        
        # Create treeview
        tree = ttk.Treeview(
            tree_frame, 
            columns=("Property", "Value"), 
            show="headings",
            height=25
        )
        tree.heading("Property", text="Property")
        tree.heading("Value", text="Value")
        tree.column("Property", width=300, anchor="w")
        tree.column("Value", width=550, anchor="w")
        
        # Add data to tree with categories
        for key, value in info_dict.items():
            # Color code certain important fields
            item_id = tree.insert("", "end", values=(key, value))
            
            # Highlight potential issues
            if "Error" in str(value) or value == "N/A":
                tree.item(item_id, tags=("warning",))
            elif key == "Clipping Detected" and value.startswith("Yes"):
                tree.item(item_id, tags=("error",))
            elif key == "Null/Dead Traces":
                try:
                    percent = float(value.split('(')[1].split('%')[0])
                    if percent > 5.0:
                        tree.item(item_id, tags=("warning",))
                except:
                    pass
        
        # Configure tag colors
        tree.tag_configure("warning", foreground="orange")
        tree.tag_configure("error", foreground="red")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _create_seismic_plot_tab(self):
        """Create the Seismic Plot tab with plot button and canvas"""
        self.plot_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.plot_tab, text="Seismic Plot")
        
        # Info label
        info_label = ttk.Label(
            self.plot_tab,
            text="Click 'Plot Seismic' to visualize seismic data",
            font=("Arial", 11),
            foreground="gray"
        )
        info_label.pack(pady=20)
        
        # Warning label
        warning_label = ttk.Label(
            self.plot_tab,
            text="⚠ Large files may take time to load",
            font=("Arial", 9),
            foreground="orange"
        )
        warning_label.pack(pady=5)
        
        # Button frame
        btn_frame = ttk.Frame(self.plot_tab)
        btn_frame.pack(pady=15)
        
        ttk.Button(btn_frame, text="Plot Seismic", 
                  command=self._plot_2D_seismic).pack(padx=5)
        
        # Placeholder for plot
        self.plot_container = ttk.Frame(self.plot_tab)
        self.plot_container.pack(fill="both", expand=True, padx=10, pady=10)
    
    def _plot_2D_seismic(self):
        """Plot 2D seismic data from SEG-Y file in the Seismic Plot tab"""
        if not self.filepath:
            messagebox.showerror("Error", "File path is not set!")
            return
        
        try:
            # Clear previous content
            for widget in self.plot_container.winfo_children():
                widget.destroy()
            
            # Show loading message
            loading_label = ttk.Label(
                self.plot_container, 
                text="Loading seismic data, please wait...", 
                font=("Arial", 12)
            )
            loading_label.pack(expand=True)
            self.popup.update()
            
            # Open and read SEG-Y file
            with segyio.open(self.filepath, 'r', strict=False) as f:
                # Get basic information
                n_traces = f.tracecount
                n_samples = f.samples.size
                
                # Read all traces into NumPy array
                seismic_data = np.zeros((n_traces, n_samples))
                for i in range(n_traces):
                    seismic_data[i, :] = f.trace[i][:]
                
                # Normalize data for better visualization
                # max_amp = np.max(np.abs(seismic_data))
                # if max_amp > 0:
                #     seismic_data = seismic_data / max_amp
                # else:
                #     messagebox.showwarning("Warning", "Seismic data has zero amplitude!")
                
                # Create time axis
                # time_axis = f.samples / 1000  # Convert to seconds
            
            # Remove loading message
            loading_label.destroy()
            
            # Create matplotlib figure
            fig, ax = plt.subplots(figsize=(12, 7))
            
            # Plot seismic section
            im = ax.imshow(
                seismic_data.T,
                aspect='auto',
                cmap='seismic',
                # vmin=-1, 
                # vmax=1,
                # extent=[0, n_traces, time_axis[-1], time_axis[0]],
                interpolation='bilinear'
            )
            
            # Labels and title
            ax.set_xlabel('Trace Number', fontsize=11, fontweight='bold')
            ax.set_ylabel('Time (ms)', fontsize=11, fontweight='bold')
            ax.set_title(
                f'2D Seismic Section - {os.path.basename(self.filepath)}', 
                fontsize=12, 
                fontweight='bold', 
                pad=15
            )
            
            # Add grid
            ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
            
            # Add colorbar with better formatting
            cbar = plt.colorbar(im, ax=ax, label='Amplitude', pad=0.02)
            cbar.ax.tick_params(labelsize=9)
            
            # Adjust layout
            fig.tight_layout()
            
            # Embed plot in tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.plot_container)
            canvas.draw()
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill=tk.BOTH, expand=True)
            
            # Add navigation toolbar
            toolbar_frame = ttk.Frame(self.plot_container)
            toolbar_frame.pack(fill=tk.X, side=tk.BOTTOM)
            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.update()
            
        except FileNotFoundError:
            self._show_error_in_plot_tab(f"SEG-Y file not found:\n{self.filepath}")
            messagebox.showerror("File Error", f"SEG-Y file not found at:\n{self.filepath}")
            
        except MemoryError:
            self._show_error_in_plot_tab("Not enough memory to load seismic data")
            messagebox.showerror("Memory Error", 
                               "File is too large. Try using a smaller file or increase system memory.")
            
        except Exception as e:
            self._show_error_in_plot_tab(f"Error: {str(e)}")
            messagebox.showerror("Plotting Error", f"An error occurred while plotting:\n{str(e)}")
    
    def _show_error_in_plot_tab(self, error_msg):
        """Display error message in the plot tab"""
        # Clear plot tab
        for widget in self.plot_container.winfo_children():
            widget.destroy()
        
        # Show error message
        error_frame = ttk.Frame(self.plot_container)
        error_frame.pack(expand=True)
        
        ttk.Label(
            error_frame,
            text="❌ Failed to plot seismic data",
            font=("Arial", 12, "bold"),
            foreground="red"
        ).pack(pady=10)
        
        ttk.Label(
            error_frame,
            text=error_msg,
            font=("Arial", 10),
            foreground="darkred",
            wraplength=600
        ).pack(pady=5)

# ===================== SEISMIC QC TAB =====================

class Seismic2DQCTab:
    """Main tab for 2D seismic data QC checking"""
    
    def __init__(self, parent):
        self.parent = parent
        self.validator = Seismic2DValidator()
        self.file_paths = {}
        
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="2D Seismic")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Folder selection frame
        top_frame = ttk.LabelFrame(self.frame, text="Select Seismic Data Folder")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        self.folder_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.folder_var).pack(
            side="left", fill="x", expand=True, padx=(10, 5), pady=5
        )
        ttk.Button(top_frame, text="Browse..", command=self.browse_folder).pack(side="left", padx=3)
        ttk.Button(top_frame, text="Scan", command=self.scan_folder).pack(side="left", padx=3)
        
        # Create frame for treeview with scrollbars
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        
        # Create vertical scrollbar
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")
        
        # Create horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Treeview for results
        self.tree = ttk.Treeview(
            tree_frame, 
            show="headings", 
            height=14,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        self.tree.pack(side="left", fill="both", expand=True)
        
        # Configure scrollbars
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
        
        self._setup_table_columns()
        
        # Bind double-click event
        self.tree.bind("<Double-Button-1>", self.on_row_double_click)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Double-click any row to see detailed information.")
        ttk.Label(self.frame, textvariable=self.status_var, anchor="w").pack(fill="x", padx=10, pady=3)
        
        # Bottom button
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.export_btn = ttk.Button(btn_frame, text="Export", command=self._export_to_csv)
        self.export_btn.pack(side=tk.RIGHT, padx=5)
        
        self.clear_btn = ttk.Button(btn_frame, text="Clear Table", command=self.clear_table)
        self.clear_btn.pack(side=tk.RIGHT, padx=5)
    
    def _setup_table_columns(self):
        """Setup treeview columns"""
        columns = [
            "File", "Line Name", "Traces", "Samples", "Interval (ms)", 
            "Length (ms)", "Format"
        ]
        
        self.tree["columns"] = columns
        
        widths = {
            "File": 180,
            "Line Name": 150,
            "Traces": 80,
            "Samples": 80,
            "Interval (ms)": 100,
            "Length (ms)": 100,
            "Format": 100,
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            width = widths.get(col, 80)
            self.tree.column(col, anchor="center", width=width)
    
    def browse_folder(self):
        """Open folder browser dialog"""
        folder = filedialog.askdirectory(title="Select 2D Seismic Data Folder")
        if folder:
            self.folder_var.set(folder)
            self.status_var.set(f"Selected folder: {folder}")
    
    def scan_folder(self):
        """Scan selected folder for SEGY files and validate"""
        folder = self.folder_var.get()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return
        
        # Clear existing results
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.file_paths.clear()
        
        # Scan for SEGY files
        scanner = SEGYFileScanner(folder)
        segy_files = scanner.find_all_segy_files()
        
        if not segy_files:
            messagebox.showinfo("No SEGY Files", "No .sgy or .segy files found in the selected folder.")
            return
        
        # Process each file
        total = len(segy_files)
        success_count = 0
        
        self.status_var.set(f"Processing {total} SEGY files...")
        self.frame.update()
        
        for i, filepath in enumerate(segy_files):
            segy = scanner.read_segy_file(filepath, '2D')
            if not segy:
                continue
            
            # Get basic info
            info = self.validator.get_basic_info(segy)
            
            # Build table row
            values = [
                info.get("filename", "N/A"),
                info.get("line_name", "N/A"),
                info.get("trace_count", "N/A"),
                info.get("sample_count", "N/A"),
                info.get("sample_interval", "N/A"),
                info.get("trace_length", "N/A"),
                info.get("format", "N/A"),
                info.get("cdp_range", "N/A")
            ]
            
            item_id = self.tree.insert("", "end", values=values)
            self.file_paths[item_id] = filepath
            
            success_count += 1
            
            # Update progress
            self.status_var.set(f"Processing {i+1}/{total}...")
            self.frame.update()
            
            # Close file
            segy.close()
        
        self.status_var.set(
            f"Scan complete: {success_count}/{total} SEGY files processed successfully. Double-click any row for detailed QC."
        )
    
    def on_row_double_click(self, event):
        """Handle double-click on tree row"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        
        if item_id in self.file_paths:
            filepath = self.file_paths[item_id]
            # Use Seismic2DDetailPopupWindow for 2D SEGY files
            Seismic2DDetailPopupWindow(self.frame, filepath, self.validator)
        else:
            messagebox.showwarning("Error", "Unable to find file path for selected row.")
    
    def clear_table(self):
        """Clear all table rows with confirmation"""
        if not self.tree.get_children():
            messagebox.showinfo("Info", "The table is already empty.")
            return
        
        confirm = messagebox.askyesno(
            "Confirm Clear", 
            "Are you sure you want to clear all results?"
        )
        if not confirm:
            return
        
        try:
            self.clear_btn.config(state=tk.DISABLED)
            
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            self.file_paths.clear()
            self.status_var.set("Table cleared. Ready to scan.")
            
        finally:
            self.clear_btn.config(state=tk.NORMAL)

    def _export_to_csv(self):
        """Export all seismic files and their comprehensive parameters to CSV"""
        if not self.file_paths:
            messagebox.showwarning("No Data", "No data to export. Please scan files first.")
            return
        
        try:
            # Ask user for save location
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile="seismic_2d_qc_report.csv"
            )
            
            if not filepath:
                return
            
            # Disable export button during processing
            self.export_btn.config(state=tk.DISABLED)
            self.status_var.set("Exporting data to CSV...")
            self.frame.update()
            
            # Open CSV file for writing
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header row with all comprehensive parameters
                headers = [
                    'Filename',
                    'Line Name',
                    'Format',
                    'Trace Count',
                    'Samples per Trace',
                    'Sample Interval (ms)',
                    'CDP Range',
                    'Coordinate Range X',
                    'Coordinate Range Y',
                    'Amplitude Range',
                    'RMS Amplitude',
                    'Nyquist Frequency',
                    'Dominant Frequency',
                    'Null/Dead Traces',
                    'Trace Length Uniformity',
                    'Clipping Detected',
                    'Average Trace Spacing (m)',
                    'Min Trace Spacing (m)',
                    'Max Trace Spacing (m)',
                    'Straight Line Distance (m)',
                    'Est. Total Line Length (km)',
                    'Line Sinuosity',
                    'Line Shape',
                    'Coordinate Order',
                    'Binary',
                    'Format Code',
                    'Trace Sorting',
                    'Endian Type',
                    'Measurement System',
                    'Signal Std Dev',
                    'Signal Mean',
                    'Skewness',
                    'Kurtosis',
                    'Est. SNR (dB)'
                ]
                
                writer.writerow(headers)
                
                # Process each file
                total_files = len(self.file_paths)
                processed = 0
                
                scanner = SEGYFileScanner(self.folder_var.get())
                
                for item_id, file_path in self.file_paths.items():
                    try:
                        # Update progress
                        processed += 1
                        self.status_var.set(f"Exporting {processed}/{total_files}: {os.path.basename(file_path)}")
                        self.frame.update()
                        
                        # Open SEGY file
                        segy = scanner.read_segy_file(file_path, '2D')
                        if not segy:
                            # Write error row
                            writer.writerow([os.path.basename(file_path)] + ['Error reading file'] * (len(headers) - 1))
                            continue
                        
                        # Get comprehensive information
                        info = self.validator.get_comprehensive_info(segy)
                        
                        # Close file
                        segy.close()
                        
                        # Build data row matching headers
                        row_data = [
                            info.get('Filename', 'N/A'),
                            info.get('Line Name', 'N/A'),
                            info.get('Format', 'N/A'),
                            info.get('Trace Count', 'N/A'),
                            info.get('Samples per Trace', 'N/A'),
                            info.get('Sample Interval (ms)', 'N/A'),
                            info.get('CDP Range', 'N/A'),
                            info.get('Coordinate Range X', 'N/A'),
                            info.get('Coordinate Range Y', 'N/A'),
                            info.get('Amplitude Range', 'N/A'),
                            info.get('RMS Amplitude', 'N/A'),
                            info.get('Nyquist Frequency', 'N/A'),
                            info.get('Dominant Frequency', 'N/A'),
                            info.get('Null/Dead Traces', 'N/A'),
                            info.get('Trace Length Uniformity', 'N/A'),
                            info.get('Clipping Detected', 'N/A'),
                            info.get('Average Trace Spacing (m)', 'N/A'),
                            info.get('Min Trace Spacing (m)', 'N/A'),
                            info.get('Max Trace Spacing (m)', 'N/A'),
                            info.get('Straight Line Distance (m)', 'N/A'),
                            info.get('Est. Total Line Length (km)', 'N/A'),
                            info.get('Line Sinuosity', 'N/A'),
                            info.get('Line Shape', 'N/A'),
                            info.get('Coordinate Order', 'N/A'),
                            info.get('Binary', 'N/A'),
                            info.get('Format Code', 'N/A'),
                            info.get('Trace Sorting', 'N/A'),
                            info.get('Endian Type', 'N/A'),
                            info.get('Measurement System', 'N/A'),
                            info.get('Signal Std Dev', 'N/A'),
                            info.get('Signal Mean', 'N/A'),
                            info.get('Skewness', 'N/A'),
                            info.get('Kurtosis', 'N/A'),
                            info.get('Est. SNR (dB)', 'N/A')
                        ]
                        
                        writer.writerow(row_data)
                        
                    except Exception as e:
                        # Write error row for this file
                        writer.writerow([os.path.basename(file_path), f'Error: {str(e)}'] + ['N/A'] * (len(headers) - 2))
                
                # Write metadata at the end
                # writer.writerow([])
                # writer.writerow(['Report Generated', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                # writer.writerow(['Total Files Processed', total_files])
                # writer.writerow(['Source Folder', self.folder_var.get()])
            
            self.status_var.set(f"Export complete: {total_files} files exported to CSV.")
            messagebox.showinfo("Export Successful", f"Data exported successfully to:\n{filepath}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export to CSV:\n{str(e)}")
            self.status_var.set("Export failed.")
            
        finally:
            self.export_btn.config(state=tk.NORMAL)

# ===================== SEISMIC 3D QC TAB =====================

class Seismic3DQCTab:
    """Main tab for 3D seismic data QC checking"""
    
    def __init__(self, parent):
        self.parent = parent
        self.validator = Seismic3DValidator()
        self.file_paths = {}
        
        self.frame = ttk.Frame(parent)
        parent.add(self.frame, text="3D Seismic")
        
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface"""
        # Folder selection frame
        top_frame = ttk.LabelFrame(self.frame, text="Select 3D Seismic Data Folder")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        self.folder_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.folder_var).pack(
            side="left", fill="x", expand=True, padx=(10, 5), pady=5
        )
        ttk.Button(top_frame, text="Browse..", command=self.browse_folder).pack(side="left", padx=3)
        ttk.Button(top_frame, text="Scan", command=self.scan_folder).pack(side="left", padx=3)\
		
		# Create frame for treeview with scrollbars
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))
		
        # Create vertical scrollbar
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")
        
        # Create horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Treeview for results
        self.tree = ttk.Treeview(
            tree_frame, 
            show="headings", 
            height=14,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )
        self.tree.pack(side="left", fill="both", expand=True)
		
		# Configure scrollbars
        v_scrollbar.config(command=self.tree.yview)
        h_scrollbar.config(command=self.tree.xview)
		
        self._setup_table_columns()
        
        # Bind double-click event
        self.tree.bind("<Double-Button-1>", self.on_row_double_click)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Double-click any row to see detailed 3D information.")
        ttk.Label(self.frame, textvariable=self.status_var, anchor="w").pack(fill="x", padx=10, pady=3)
        
        # Bottom button
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.export_btn = ttk.Button(btn_frame, text="Export", command=self._export_to_csv)
        self.export_btn.pack(side=tk.RIGHT, padx=5)

        self.clear_btn = ttk.Button(btn_frame, text="Clear Table", command=self.clear_table)
        self.clear_btn.pack(side=tk.RIGHT, padx=5)
    
    def _setup_table_columns(self):
        """Setup treeview columns"""
        columns = [
            "File", "Traces", "Samples", "Interval (ms)", 
            "Length (ms)", "Format", "Inline Range", "Crossline Range"
        ]
        
        self.tree["columns"] = columns
        
        widths = {
            "File": 160,
            "Traces": 90,
            "Samples": 80,
            "Interval (ms)": 90,
            "Length (ms)": 90,
            "Format": 90,
            "Inline Range": 110,
            "Crossline Range": 120
        }
        
        for col in columns:
            self.tree.heading(col, text=col)
            width = widths.get(col, 80)
            self.tree.column(col, anchor="center", width=width)
    
    def browse_folder(self):
        """Open folder browser dialog"""
        folder = filedialog.askdirectory(title="Select 3D Seismic Data Folder")
        if folder:
            self.folder_var.set(folder)
            self.status_var.set(f"Selected folder: {folder}")
    
    def scan_folder(self):
        """Scan selected folder for SEGY files and validate"""
        folder = self.folder_var.get()
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return
        
        # Clear existing results
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.file_paths.clear()
        
        # Scan for SEGY files
        scanner = SEGYFileScanner(folder)
        segy_files = scanner.find_all_segy_files()
        
        if not segy_files:
            messagebox.showinfo("No SEGY Files", "No .sgy or .segy files found in the selected folder.")
            return
        
        # Process each file
        total = len(segy_files)
        success_count = 0
        
        self.status_var.set(f"Processing {total} 3D SEGY files...")
        self.frame.update()
        
        for i, filepath in enumerate(segy_files):
            segy = scanner.read_segy_file(filepath, '3D')
            if not segy:
                continue
            
            # Get basic info
            info = self.validator.get_basic_info(segy)
            
            # Build table row
            values = [
                info.get("filename", "N/A"),
                # info.get("survey_name", "N/A"),
                info.get("trace_count", "N/A"),
                info.get("sample_count", "N/A"),
                info.get("sample_interval", "N/A"),
                info.get("trace_length", "N/A"),
                info.get("format", "N/A"),
                info.get("inline_range", "N/A"),
                info.get("crossline_range", "N/A")
            ]
            
            item_id = self.tree.insert("", "end", values=values)
            self.file_paths[item_id] = filepath
            
            success_count += 1
            
            # Update progress
            self.status_var.set(f"Processing {i+1}/{total}...")
            self.frame.update()
            
            # Close file
            segy.close()
        
        self.status_var.set(
            f"Scan complete: {success_count}/{total} 3D SEGY files processed. Double-click any row for detailed QC."
        )
    
    def on_row_double_click(self, event):
        """Handle double-click on tree row"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        
        if item_id in self.file_paths:
            filepath = self.file_paths[item_id]
            # Use Seismic3DDetailPopupWindow for 3D SEGY files
            Seismic3DDetailPopupWindow(self.frame, filepath, self.validator)
        else:
            messagebox.showwarning("Error", "Unable to find file path for selected row.")
    
    def clear_table(self):
        """Clear all table rows with confirmation"""
        if not self.tree.get_children():
            messagebox.showinfo("Info", "The table is already empty.")
            return
        
        confirm = messagebox.askyesno(
            "Confirm Clear", 
            "Are you sure you want to clear all results?"
        )
        if not confirm:
            return
        
        try:
            self.clear_btn.config(state=tk.DISABLED)
            
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            self.file_paths.clear()
            self.status_var.set("Table cleared. Ready to scan.")
            
        finally:
            self.clear_btn.config(state=tk.NORMAL)


    def _export_to_csv(self):
        """Export all seismic files and their comprehensive parameters to CSV"""
        if not self.file_paths:
            messagebox.showwarning("No Data", "No data to export. Please scan files first.")
            return
        
        try:
            # Ask user for save location
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile="seismic_3d_qc_report.csv"
            )
            
            if not filepath:
                return
            
            # Disable export button during processing
            self.export_btn.config(state=tk.DISABLED)
            self.status_var.set("Exporting data to CSV...")
            self.frame.update()
            
            # Open CSV file for writing
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header row with all comprehensive parameters
                headers = [
                    'Filename',
                    'Total Traces',
                    'Samples per Trace',
                    'Sample Interval (ms)',
                    'Trace Length (ms)',
                    'Time Range',
                    'Data Format',
                    'Sorting',
                    'Inline Range',
                    'Crossline Range',
                    'Estimated Volume',
                    'Amplitude Range',
                    'Amolitude Mean',
                    'Amplitude Std Dev',
                    'Nyquist Frequency (Hz)',
                    'Dominant Frequency (Hz)',
                    'Null/Dead Traces',
                    'Valid Traces',
                    'Binary Format Code',
                    'Trace Sorting',
                    'Endian Type',
                    'Measurement System'
                ]
                
                writer.writerow(headers)
                
                # Process each file
                total_files = len(self.file_paths)
                processed = 0
                
                scanner = SEGYFileScanner(self.folder_var.get())
                
                for item_id, file_path in self.file_paths.items():
                    try:
                        # Update progress
                        processed += 1
                        self.status_var.set(f"Exporting {processed}/{total_files}: {os.path.basename(file_path)}")
                        self.frame.update()
                        
                        # Open SEGY file
                        segy = scanner.read_segy_file(file_path, '3D')
                        if not segy:
                            # Write error row
                            writer.writerow([os.path.basename(file_path)] + ['Error reading file'] * (len(headers) - 1))
                            continue

                        # Get comprehensive information
                        info = self.validator.get_comprehensive_info(segy)

                        # Close file
                        segy.close()
                        
                        # Build data row matching headers
                        row_data = [
                            info.get('Filename', 'N/A'),
                            info.get('Total Traces', 'N/A'),
                            info.get('Samples per Trace', 'N/A'),
                            info.get('Sample Interval (ms)', 'N/A'),
                            info.get('Trace Length (ms)', 'N/A'),
                            info.get('Time Range', 'N/A'),
                            info.get('Data Format', 'N/A'),
                            info.get('Sorting', 'N/A'),
                            info.get('Inline Range', 'N/A'),
                            info.get('Crossline Range', 'N/A'),
                            info.get('Estimated Volume', 'N/A'),
                            info.get('Amplitude Range', 'N/A'),
                            info.get('Amplitude Mean', 'N/A'),
                            info.get('Amplitude Std Dev', 'N/A'),
                            info.get('Nyquist Frequency (Hz)', 'N/A'),
                            info.get('Dominant Frequency (Hz)', 'N/A'),
                            info.get('Null/Dead Traces', 'N/A'),
                            info.get('Valid Traces', 'N/A'),
                            info.get('Binary Format Code', 'N/A'),
                            info.get('Trace Sorting', 'N/A'),
                            info.get('Endian Type', 'N/A'),
                            info.get('Measurement System', 'N/A')
                        ]
                        
                        writer.writerow(row_data)
                        
                    except Exception as e:
                        # Write error row for this file
                        writer.writerow([os.path.basename(file_path), f'Error: {str(e)}'] + ['N/A'] * (len(headers) - 2))
            
            self.status_var.set(f"Export complete: {total_files} files exported to CSV.")
            messagebox.showinfo("Export Successful", f"Data exported successfully to:\n{filepath}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export to CSV:\n{str(e)}")
            self.status_var.set("Export failed.")
            
        finally:
            self.export_btn.config(state=tk.NORMAL)

# ===================== MAIN APPLICATION =====================

class ExplorationDataCheckerApp:
    """Main application window"""
    
    def __init__(self, root):
        root.title("Exploration Data Checker")
        root.geometry("1050x600")
        
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)
        
        self.log_tab = LogDataCheckerTab(notebook)
        self.seismic_2D_tab = Seismic2DQCTab(notebook)
        self.seismic_3D_tab = Seismic3DQCTab(notebook)


# ===================== RUN APP =====================
if __name__ == "__main__":
    root = tk.Tk()
    app = ExplorationDataCheckerApp(root)
    root.mainloop()