import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
import subprocess
import sys
import json
import math

from organizer import process_folder, undo_last_run
import classifier

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

if DND_AVAILABLE:
    class DnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    DnDCTk = ctk.CTk


def parse_dropped_path(data):
    data = data.strip()
    parts = []
    current = ""
    in_brace = False
    for ch in data:
        if ch == "{":
            in_brace = True
            continue
        if ch == "}":
            in_brace = False
            continue
        if ch == " " and not in_brace:
            if current:
                parts.append(current)
                current = ""
            continue
        current += ch
    if current:
        parts.append(current)
    return parts[0] if parts else data

RECENT_FOLDERS_PATH = Path(__file__).parent / "recent_folders.json"
MAX_RECENT_FOLDERS = 6

CATEGORY_COLORS = {
    "Invoice": "#4FD1C5",
    "Resume": "#63B3ED",
    "Certificate": "#F6E05E",
    "Contract": "#F687B3",
    "Report": "#B794F4",
    "Offer Letter": "#68D391",
    "Duplicates": "#FC8181",
    "Unsorted": "#A0AEC0",
}


def load_recent_folders():
    if not RECENT_FOLDERS_PATH.exists():
        return []
    try:
        with open(RECENT_FOLDERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [p for p in data if isinstance(p, str)]
    except Exception:
        pass
    return []


def save_recent_folder(folder_path):
    folder_str = str(folder_path)
    recent = load_recent_folders()
    recent = [p for p in recent if p != folder_str]
    recent.insert(0, folder_str)
    recent = recent[:MAX_RECENT_FOLDERS]
    try:
        with open(RECENT_FOLDERS_PATH, "w", encoding="utf-8") as f:
            json.dump(recent, f, indent=2)
    except Exception:
        pass
    return recent


class CategoryEditorWindow(ctk.CTkToplevel):
    def __init__(self, parent, on_saved=None):
        super().__init__(parent)
        self.on_saved = on_saved
        self.title("Category Editor")
        self.geometry("760x520")
        self.minsize(640, 440)
        self.transient(parent)
        self.grab_set()

        config = classifier.get_current_config()
        self.categories = config["categories"]
        self.scoring = config["scoring"]
        self.current_category = None
        self.dirty = False

        self._build_layout()
        self._populate_category_list()

        if self.categories:
            first_name = next(iter(self.categories))
            self._select_category(first_name)

    def _build_layout(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        left = ctk.CTkFrame(container, fg_color="#1A202C", corner_radius=12, width=220)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        ctk.CTkLabel(
            left, text="Categories", font=ctk.CTkFont(size=13, weight="bold"), text_color="#E2E8F0"
        ).pack(anchor="w", padx=14, pady=(12, 6))

        self.category_list_frame = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.category_list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        ctk.CTkButton(
            left, text="+ New Category", height=34, corner_radius=8,
            fg_color="#2B6CB0", hover_color="#2C5282",
            command=self._new_category
        ).pack(fill="x", padx=8, pady=(0, 12))

        right = ctk.CTkFrame(container, fg_color="#1A202C", corner_radius=12)
        right.pack(side="left", fill="both", expand=True)

        name_row = ctk.CTkFrame(right, fg_color="transparent")
        name_row.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkLabel(
            name_row, text="Category Name", font=ctk.CTkFont(size=12, weight="bold"), text_color="#E2E8F0"
        ).pack(anchor="w")
        self.name_entry = ctk.CTkEntry(name_row, height=36, corner_radius=8, font=ctk.CTkFont(size=13))
        self.name_entry.pack(fill="x", pady=(4, 0))

        self.strong_box = self._build_keyword_section(
            right, "Strong keywords (near-certain — one per line)"
        )
        self.weak_box = self._build_keyword_section(
            right, "Weak keywords (supporting signals — one per line)"
        )
        self.exclude_box = self._build_keyword_section(
            right, "Exclude keywords (any match vetoes this category — one per line)"
        )

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=(0, 16))

        self.delete_btn = ctk.CTkButton(
            bottom, text="🗑 Delete Category", height=38, corner_radius=8,
            fg_color="#9C4221", hover_color="#7B341E",
            command=self._delete_current_category
        )
        self.delete_btn.pack(side="left")

        ctk.CTkButton(
            bottom, text="Cancel", height=38, corner_radius=8, width=100,
            fg_color="#2D3748", hover_color="#4A5568",
            command=self._on_cancel
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            bottom, text="💾 Save All Changes", height=38, corner_radius=8, width=180,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#2F855A", hover_color="#276749",
            command=self._save_all
        ).pack(side="right")

    def _build_keyword_section(self, parent, label_text):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=(6, 0))

        ctk.CTkLabel(
            frame, text=label_text, font=ctk.CTkFont(size=11), text_color="#A0AEC0"
        ).pack(anchor="w")

        box = ctk.CTkTextbox(
            frame, height=64, fg_color="#171923", font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=8, wrap="word"
        )
        box.pack(fill="both", expand=True, pady=(4, 0))
        return box

    def _populate_category_list(self):
        for widget in self.category_list_frame.winfo_children():
            widget.destroy()

        self.category_buttons = {}
        for name in self.categories:
            btn = ctk.CTkButton(
                self.category_list_frame, text=name, height=32, corner_radius=6,
                anchor="w", fg_color="transparent", hover_color="#2D3748",
                font=ctk.CTkFont(size=12),
                command=lambda n=name: self._select_category(n)
            )
            btn.pack(fill="x", pady=2)
            self.category_buttons[name] = btn

        self._highlight_selected()

    def _highlight_selected(self):
        for name, btn in self.category_buttons.items():
            if name == self.current_category:
                btn.configure(fg_color="#2B6CB0")
            else:
                btn.configure(fg_color="transparent")

    def _save_current_edits_to_memory(self):
        if self.current_category is None:
            return
        new_name = self.name_entry.get().strip()
        if not new_name:
            return

        strong = [line.strip() for line in self.strong_box.get("1.0", "end").splitlines() if line.strip()]
        weak = [line.strip() for line in self.weak_box.get("1.0", "end").splitlines() if line.strip()]
        exclude = [line.strip() for line in self.exclude_box.get("1.0", "end").splitlines() if line.strip()]

        if new_name != self.current_category:
            self.categories.pop(self.current_category, None)

        self.categories[new_name] = {"strong": strong, "weak": weak, "exclude": exclude}
        self.current_category = new_name

    def _select_category(self, name):
        self._save_current_edits_to_memory()

        self.current_category = name
        data = self.categories.get(name, {"strong": [], "weak": [], "exclude": []})

        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, name)

        self.strong_box.delete("1.0", "end")
        self.strong_box.insert("1.0", "\n".join(data.get("strong", [])))

        self.weak_box.delete("1.0", "end")
        self.weak_box.insert("1.0", "\n".join(data.get("weak", [])))

        self.exclude_box.delete("1.0", "end")
        self.exclude_box.insert("1.0", "\n".join(data.get("exclude", [])))

        if name not in self.category_buttons:
            self._populate_category_list()
        else:
            self._highlight_selected()

    def _new_category(self):
        self._save_current_edits_to_memory()

        base_name = "New Category"
        name = base_name
        counter = 1
        while name in self.categories:
            counter += 1
            name = f"{base_name} {counter}"

        self.categories[name] = {"strong": [], "weak": [], "exclude": []}
        self._populate_category_list()
        self._select_category(name)
        self.name_entry.focus()
        self.name_entry.select_range(0, "end")

    def _delete_current_category(self):
        if self.current_category is None:
            return
        if len(self.categories) <= 1:
            messagebox.showwarning("Cannot Delete", "At least one category must remain.")
            return

        confirm = messagebox.askyesno(
            "Delete Category", f"Delete the category '{self.current_category}'?\nFiles will fall back to Unsorted for this category going forward."
        )
        if not confirm:
            return

        self.categories.pop(self.current_category, None)
        self.current_category = None
        self._populate_category_list()

        if self.categories:
            self._select_category(next(iter(self.categories)))
        else:
            self.name_entry.delete(0, "end")
            self.strong_box.delete("1.0", "end")
            self.weak_box.delete("1.0", "end")
            self.exclude_box.delete("1.0", "end")

    def _save_all(self):
        self._save_current_edits_to_memory()

        empty_names = [name for name in self.categories if not name.strip()]
        if empty_names:
            messagebox.showerror("Invalid Category", "Category names cannot be empty.")
            return

        success, error = classifier.write_config(self.categories, self.scoring)
        if not success:
            messagebox.showerror("Save Failed", error)
            return

        messagebox.showinfo("Saved", f"Saved {len(self.categories)} categories to config.yaml.")
        if self.on_saved:
            self.on_saved()
        self.destroy()

    def _on_cancel(self):
        self.destroy()


class LiquidProgressBar(ctk.CTkFrame):
    def __init__(self, master, width=280, height=42,
                 fill_color="#2B6CB0", fill_color_dark="#234E70",
                 track_color="#171923", text_color="#F7FAFC", **kwargs):
        super().__init__(master, fg_color=track_color, corner_radius=height // 3, **kwargs)

        self.bar_width = width
        self.bar_height = height
        self.fill_color = fill_color
        self.fill_color_dark = fill_color_dark
        self.track_color = track_color
        self.text_color = text_color

        self.target_percent = 0.0
        self.display_percent = 0.0
        self.phase = 0.0
        self.animating = False
        self._after_id = None

        self.canvas = tk.Canvas(
            self, width=width, height=height, highlightthickness=0, bg=track_color, bd=0
        )
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)

        self._tick()

    def start(self):
        self.animating = True

    def stop(self):
        self.animating = False

    def set(self, fraction):
        self.target_percent = max(0.0, min(1.0, fraction)) * 100

    def _tick(self):
        speed = 0.18 if self.animating else 0.06
        self.display_percent += (self.target_percent - self.display_percent) * speed

        phase_speed = 0.35 if self.animating else 0.08
        self.phase += phase_speed

        self._render_wave()
        self._after_id = self.after(45, self._tick)

    def _render_wave(self):
        c = self.canvas
        c.delete("all")

        w, h = self.bar_width, self.bar_height
        fill_x = (self.display_percent / 100.0) * w

        amplitude_bg = 4 if self.animating else 1.5
        amplitude_fg = 2.5 if self.animating else 1

        bg_points = []
        for y_step in range(0, h + 1, 3):
            offset = amplitude_bg * math.sin((y_step / max(h, 1)) * (math.pi * 2) + self.phase * 0.8)
            bg_points.append((fill_x + offset, y_step))

        fg_points = []
        for y_step in range(0, h + 1, 3):
            offset = amplitude_fg * math.sin((y_step / max(h, 1)) * (math.pi * 2.4) + self.phase * 1.3 + 1.2)
            fg_points.append((fill_x + offset, y_step))

        if fill_x > 1:
            bg_poly = [(0, 0)] + bg_points + [(0, h)]
            flat_bg = [coord for point in bg_poly for coord in point]
            c.create_polygon(flat_bg, fill=self.fill_color_dark, outline="", smooth=True)

            fg_poly = [(0, 0)] + fg_points + [(0, h)]
            flat_fg = [coord for point in fg_poly for coord in point]
            c.create_polygon(flat_fg, fill=self.fill_color, outline="", smooth=True)

        percent_text = f"{int(round(self.display_percent))}%"
        c.create_text(
            w / 2 + 1, h / 2 + 1, text=percent_text,
            font=("Segoe UI Semibold", 13), fill="#000000", anchor="center"
        )
        c.create_text(
            w / 2, h / 2, text=percent_text,
            font=("Segoe UI Semibold", 13), fill=self.text_color, anchor="center"
        )


class OrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Bulk Organizer")
        self.root.geometry("820x600")
        self.root.minsize(700, 520)

        self.folder_path = ctk.StringVar()
        self.is_running = False
        self.stop_event = threading.Event()

        self._build_header()
        self._build_input_row()
        self._build_action_row()
        self._build_config_row()
        self._build_status_row()
        self._build_summary_row()
        self._build_log_area()
        self._setup_drag_and_drop()

    def _build_header(self):
        header = ctk.CTkFrame(self.root, fg_color="#1A202C", corner_radius=0, height=90)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="📁 PDF Bulk Organizer",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color="#4FD1C5"
        ).pack(anchor="w", padx=24, pady=(14, 0))

        ctk.CTkLabel(
            header, text="Point it at a folder — it reads, classifies, and sorts your PDFs.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#A0AEC0"
        ).pack(anchor="w", padx=24)

    def _build_input_row(self):
        frame = ctk.CTkFrame(self.root, fg_color="transparent")
        frame.pack(fill="x", padx=24, pady=(20, 8))

        ctk.CTkLabel(
            frame, text="Folder Location", font=ctk.CTkFont(size=13, weight="bold"), text_color="#E2E8F0"
        ).pack(anchor="w")

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=(6, 0))

        self.path_entry = ctk.CTkEntry(
            row, textvariable=self.folder_path,
            placeholder_text="Paste a path, click Browse, or drag a folder here...",
            height=42, font=ctk.CTkFont(size=13), corner_radius=10
        )
        self.path_entry.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            row, text="Browse", width=110, height=42, corner_radius=10,
            fg_color="#2D3748", hover_color="#4A5568",
            command=self.browse_folder
        ).pack(side="left", padx=(10, 0))

        recent = load_recent_folders()
        self.recent_menu = ctk.CTkOptionMenu(
            row, width=130, height=42, corner_radius=10,
            values=recent if recent else ["No recent folders"],
            fg_color="#2D3748", button_color="#4A5568", button_hover_color="#718096",
            dropdown_fg_color="#2D3748",
            command=self.select_recent_folder
        )
        self.recent_menu.set("Recent ▾")
        self.recent_menu.pack(side="left", padx=(10, 0))

    def _build_action_row(self):
        row = ctk.CTkFrame(self.root, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(14, 0))

        self.dry_run_btn = ctk.CTkButton(
            row, text="🔍  Preview (Dry Run)", height=46, corner_radius=12,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2B6CB0", hover_color="#2C5282",
            command=self.run_dry_run
        )
        self.dry_run_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.organize_btn = ctk.CTkButton(
            row, text="✅  Organize Now", height=46, corner_radius=12,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2F855A", hover_color="#276749",
            command=self.run_organize
        )
        self.organize_btn.pack(side="left", fill="x", expand=True, padx=(8, 8))

        self.undo_btn = ctk.CTkButton(
            row, text="↩  Undo Last Run", height=46, corner_radius=12,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#9C4221", hover_color="#7B341E",
            command=self.run_undo
        )
        self.undo_btn.pack(side="left", fill="x", expand=True, padx=(8, 8))

        self.stop_btn = ctk.CTkButton(
            row, text="⏹  Stop", height=46, corner_radius=12, width=90,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#C53030", hover_color="#9B2C2C",
            state="disabled",
            command=self.request_stop
        )
        self.stop_btn.pack(side="left", padx=(8, 0))

    def _build_config_row(self):
        frame = ctk.CTkFrame(self.root, fg_color="transparent")
        frame.pack(fill="x", padx=24, pady=(10, 0))

        self.config_status_label = ctk.CTkLabel(
            frame, text="", font=ctk.CTkFont(size=11), text_color="#718096", anchor="w"
        )
        self.config_status_label.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            frame, text="⚙ Edit Categories", width=140, height=30, corner_radius=8,
            font=ctk.CTkFont(size=11), fg_color="#2D3748", hover_color="#4A5568",
            command=self.open_category_editor
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            frame, text="↻ Reload Config", width=130, height=30, corner_radius=8,
            font=ctk.CTkFont(size=11), fg_color="#2D3748", hover_color="#4A5568",
            command=self.reload_config
        ).pack(side="left", padx=(8, 0))

        self._refresh_config_status()

    def _refresh_config_status(self):
        status = classifier.get_config_status()
        if status["error"]:
            text = f"⚠ Config issue: {status['error']} — using built-in defaults"
            color = "#F6AD55"
        else:
            text = f"Categories loaded from: {status['source']} ({status['category_count']} categories)"
            color = "#718096"
        self.config_status_label.configure(text=text, text_color=color)

    def open_config(self):
        config_path = classifier.CONFIG_PATH
        if not config_path.exists():
            messagebox.showwarning(
                "Config Not Found",
                f"No config.yaml found at:\n{config_path}\n\nThe app is using built-in defaults."
            )
            return
        try:
            if sys.platform == "win32":
                import os
                os.startfile(str(config_path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(config_path)])
            else:
                subprocess.Popen(["xdg-open", str(config_path)])
        except Exception as exc:
            messagebox.showerror("Could Not Open File", f"Please open this file manually:\n{config_path}\n\n{exc}")

    def open_category_editor(self):
        CategoryEditorWindow(self.root, on_saved=self._on_categories_saved)

    def _on_categories_saved(self):
        self._refresh_config_status()

    def reload_config(self):
        classifier.reload_config()
        self._refresh_config_status()
        status = classifier.get_config_status()
        if status["error"]:
            messagebox.showwarning("Config Reloaded With Issues", status["error"])
        else:
            messagebox.showinfo("Config Reloaded", f"Loaded {status['category_count']} categories from config.yaml.")

    def _build_status_row(self):
        frame = ctk.CTkFrame(self.root, fg_color="transparent")
        frame.pack(fill="x", padx=24, pady=(14, 4))

        self.status_label = ctk.CTkLabel(
            frame, text="Choose a folder to begin.",
            font=ctk.CTkFont(size=12), text_color="#A0AEC0", anchor="w"
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        self.progress = LiquidProgressBar(frame, width=220, height=40)
        self.progress.pack(side="right", padx=(16, 0))

    def _build_summary_row(self):
        self.summary_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.summary_frame.pack(fill="x", padx=24, pady=(0, 4))
        self.summary_chip_widgets = []

    def _clear_summary(self):
        for widget in self.summary_chip_widgets:
            widget.destroy()
        self.summary_chip_widgets = []

    def _render_summary(self, category_counts):
        self._clear_summary()
        if not category_counts:
            return
        for category, count in category_counts.items():
            color = CATEGORY_COLORS.get(category, "#A0AEC0")
            chip = ctk.CTkLabel(
                self.summary_frame, text=f"{category}: {count}",
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=color, text_color="#1A202C",
                corner_radius=14, padx=12, pady=4
            )
            chip.pack(side="left", padx=(0, 8))
            self.summary_chip_widgets.append(chip)

    def _build_log_area(self):
        frame = ctk.CTkFrame(self.root, fg_color="#171923", corner_radius=12)
        frame.pack(fill="both", expand=True, padx=24, pady=(8, 20))

        ctk.CTkLabel(
            frame, text="Activity Log", font=ctk.CTkFont(size=12, weight="bold"), text_color="#718096"
        ).pack(anchor="w", padx=14, pady=(10, 0))

        self.log_box = ctk.CTkTextbox(
            frame, fg_color="#171923", font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word", activate_scrollbars=True
        )
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_box.configure(state="disabled")

        raw_text_widget = self.log_box._textbox
        for category, color in CATEGORY_COLORS.items():
            raw_text_widget.tag_config(category, foreground=color)
        raw_text_widget.tag_config("plain", foreground="#CBD5E0")

    def _setup_drag_and_drop(self):
        if not DND_AVAILABLE:
            self.status_label.configure(
                text="Tip: install tkinterdnd2 to enable drag-and-drop folder support.",
                text_color="#718096"
            )
            return

        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self._on_drop)

        self.path_entry.drop_target_register(DND_FILES)
        self.path_entry.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        if self.is_running:
            return
        dropped_path = parse_dropped_path(event.data)
        path = Path(dropped_path)

        if not path.exists():
            messagebox.showerror("Invalid Drop", f"Could not find:\n{dropped_path}")
            return

        if path.is_file():
            messagebox.showwarning(
                "Drop a Folder, Not a File",
                "Please drag and drop the folder containing your PDFs, not an individual file."
            )
            return

        if not path.is_dir():
            messagebox.showerror("Invalid Drop", "That doesn't look like a folder.")
            return

        self.folder_path.set(str(path))
        self.status_label.configure(text=f"Folder set from drag-and-drop: {path.name}", text_color="#68D391")

    def browse_folder(self):
        selected = filedialog.askdirectory(title="Select the folder containing your PDFs")
        if selected:
            self.folder_path.set(selected)

    def select_recent_folder(self, choice):
        if choice and choice != "No recent folders":
            self.folder_path.set(choice)

    def _refresh_recent_menu(self):
        recent = load_recent_folders()
        self.recent_menu.configure(values=recent if recent else ["No recent folders"])
        self.recent_menu.set("Recent ▾")

    def _append_log(self, text):
        self.log_box.configure(state="normal")
        tag = "plain"
        for category in CATEGORY_COLORS:
            if f"-> {category}/" in text or f"->  {category}/" in text:
                tag = category
                break
        self.log_box.insert("end", text + "\n", tag)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _validate_folder(self):
        folder = self.folder_path.get().strip()
        if not folder:
            messagebox.showwarning("No Location Entered", "Please enter or browse to a folder location first.")
            return None
        path = Path(folder)
        if not path.exists() or not path.is_dir():
            messagebox.showerror("Invalid Location", f"This folder does not exist:\n{folder}")
            return None
        return path

    def _set_buttons_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.dry_run_btn.configure(state=state)
        self.organize_btn.configure(state=state)
        self.undo_btn.configure(state=state)
        self.stop_btn.configure(state="disabled" if enabled else "normal")

    def request_stop(self):
        self.stop_event.set()
        self.status_label.configure(text="Stopping after the current file...", text_color="#F6AD55")
        self.stop_btn.configure(state="disabled")

    def run_dry_run(self):
        folder = self._validate_folder()
        if not folder or self.is_running:
            return
        self._run_in_thread(folder, dry_run=True)

    def run_organize(self):
        folder = self._validate_folder()
        if not folder or self.is_running:
            return
        confirm = messagebox.askyesno(
            "Confirm Organize",
            "This will move and rename PDF files in the selected folder.\n\nProceed?"
        )
        if not confirm:
            return
        self._run_in_thread(folder, dry_run=False)

    def run_undo(self):
        folder = self._validate_folder()
        if not folder or self.is_running:
            return
        confirm = messagebox.askyesno(
            "Confirm Undo",
            "This will restore files from the last real Organize run back to their original names and location.\n\nProceed?"
        )
        if not confirm:
            return

        self.is_running = True
        self._set_buttons_enabled(False)
        self._clear_log()
        self._clear_summary()
        self.progress.start()
        self.status_label.configure(text="Undoing last run...", text_color="#F6AD55")

        def worker():
            log_path = str(folder / "organizer_log.txt")
            restored, skipped, error = undo_last_run(folder, log_path)
            self.root.after(0, self._finish_undo, restored, skipped, error)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_undo(self, restored, skipped, error):
        self.progress.stop()
        self.progress.set(0)
        self._set_buttons_enabled(True)
        self.is_running = False

        if error:
            self._append_log(error)
            self.status_label.configure(text=error, text_color="#FC8181")
            return

        for line in restored:
            self._append_log(f"[RESTORED] {line}")
        for line in skipped:
            self._append_log(f"[SKIPPED]  {line}")

        self.status_label.configure(
            text=f"Undo complete — {len(restored)} restored, {len(skipped)} skipped.",
            text_color="#F6AD55"
        )
        messagebox.showinfo("Undo Complete", f"Restored {len(restored)} file(s).\nSkipped {len(skipped)} file(s).")

    def _run_in_thread(self, folder, dry_run):
        self.is_running = True
        self.stop_event.clear()
        self._set_buttons_enabled(False)
        self._clear_log()
        self._clear_summary()
        self.progress.start()
        self.status_label.configure(
            text="Previewing changes (no files touched)..." if dry_run else "Organizing files...",
            text_color="#63B3ED" if dry_run else "#68D391"
        )

        def worker():
            log_path = str(folder / "organizer_log.txt") if not dry_run else None

            def report_progress(current, total):
                fraction = current / total if total else 0
                self.root.after(0, self.progress.set, fraction)
                self.root.after(
                    0, self.status_label.configure,
                    {"text": f"Processing file {current} of {total}..."}
                )

            results, category_counts, stopped_early = process_folder(
                folder, dry_run=dry_run, log_path=log_path,
                on_action=lambda line: self.root.after(0, self._append_log, line),
                on_progress=report_progress,
                stop_check=self.stop_event.is_set
            )
            save_recent_folder(folder)
            self.root.after(0, self._refresh_recent_menu)
            self.root.after(0, self._finish_run, folder, results, category_counts, dry_run, stopped_early)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_run(self, folder, results, category_counts, dry_run, stopped_early):
        self.progress.stop()
        self.progress.set(0)
        self._set_buttons_enabled(True)
        self.is_running = False
        self._render_summary(category_counts)

        count = len(results)

        if stopped_early and not dry_run:
            self.status_label.configure(
                text=f"Stopped — {count} file(s) sorted before stopping.", text_color="#F6AD55"
            )
            self._prompt_stop_choice(folder, count)
            return

        if stopped_early and dry_run:
            self.status_label.configure(
                text=f"Preview stopped — {count} file(s) reviewed before stopping.", text_color="#F6AD55"
            )
            return

        if dry_run:
            self.status_label.configure(
                text=f"Preview complete — {count} file(s) reviewed.", text_color="#63B3ED"
            )
        else:
            self.status_label.configure(
                text=f"Done — {count} file(s) organized.", text_color="#68D391"
            )
            messagebox.showinfo("Complete", f"Organized {count} file(s).\nLog saved to organizer_log.txt")

    def _prompt_stop_choice(self, folder, sorted_count):
        undo_choice = messagebox.askyesno(
            "Sorting Stopped",
            f"You stopped the process. {sorted_count} file(s) were already sorted before stopping — "
            f"the rest remain untouched in the original folder.\n\n"
            f"Undo the {sorted_count} file(s) already sorted, putting them back exactly as they were?\n\n"
            f"Yes = Undo those {sorted_count} file(s) back to original names/location\n"
            f"No = Keep those {sorted_count} file(s) sorted as-is; the rest stay unsorted until you run again"
        )
        if undo_choice:
            self._run_stop_undo(folder)
        else:
            self.status_label.configure(
                text=f"Kept {sorted_count} sorted file(s) as-is. Remaining files are still unsorted.",
                text_color="#68D391"
            )

    def _run_stop_undo(self, folder):
        self.is_running = True
        self._set_buttons_enabled(False)
        self.progress.start()
        self.status_label.configure(text="Undoing sorted files...", text_color="#F6AD55")

        def worker():
            log_path = str(folder / "organizer_log.txt")
            restored, skipped, error = undo_last_run(folder, log_path)
            self.root.after(0, self._finish_undo, restored, skipped, error)

        threading.Thread(target=worker, daemon=True).start()


def main():
    root = DnDCTk()
    OrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()