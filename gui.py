import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
import subprocess
import sys
import json

from organizer import process_folder, undo_last_run
import classifier

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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


class OrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Bulk Organizer")
        self.root.geometry("820x600")
        self.root.minsize(700, 520)

        self.folder_path = ctk.StringVar()
        self.is_running = False

        self._build_header()
        self._build_input_row()
        self._build_action_row()
        self._build_config_row()
        self._build_status_row()
        self._build_summary_row()
        self._build_log_area()

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
            placeholder_text="Paste a folder path or click Browse...",
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
        self.undo_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

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
            command=self.open_config
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

        self.progress = ctk.CTkProgressBar(frame, height=6, corner_radius=3, mode="indeterminate")
        self.progress.pack(side="right", fill="x", expand=True, padx=(16, 0))
        self.progress.set(0)

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
            results, category_counts = process_folder(
                folder, dry_run=dry_run, log_path=log_path,
                on_action=lambda line: self.root.after(0, self._append_log, line)
            )
            save_recent_folder(folder)
            self.root.after(0, self._refresh_recent_menu)
            self.root.after(0, self._finish_run, results, category_counts, dry_run)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_run(self, results, category_counts, dry_run):
        self.progress.stop()
        self.progress.set(0)
        self._set_buttons_enabled(True)
        self.is_running = False
        self._render_summary(category_counts)

        count = len(results)
        if dry_run:
            self.status_label.configure(
                text=f"Preview complete — {count} file(s) reviewed.", text_color="#63B3ED"
            )
        else:
            self.status_label.configure(
                text=f"Done — {count} file(s) organized.", text_color="#68D391"
            )
            messagebox.showinfo("Complete", f"Organized {count} file(s).\nLog saved to organizer_log.txt")


def main():
    root = ctk.CTk()
    OrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()