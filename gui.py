import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from pathlib import Path

from organizer import process_folder


class OrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Bulk Organizer")
        self.root.geometry("640x480")
        self.root.resizable(True, True)

        self.folder_path = tk.StringVar()

        self._build_layout()

    def _build_layout(self):
        top_frame = tk.Frame(self.root, padx=12, pady=12)
        top_frame.pack(fill="x")

        tk.Label(top_frame, text="Folder Location", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        path_frame = tk.Frame(top_frame)
        path_frame.pack(fill="x", pady=(4, 0))

        self.path_entry = tk.Entry(path_frame, textvariable=self.folder_path, font=("Segoe UI", 10))
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=4)

        browse_btn = tk.Button(path_frame, text="Browse...", command=self.browse_folder)
        browse_btn.pack(side="left", padx=(8, 0))

        button_frame = tk.Frame(self.root, padx=12, pady=8)
        button_frame.pack(fill="x")

        self.dry_run_btn = tk.Button(
            button_frame, text="Preview (Dry Run)", command=self.run_dry_run,
            bg="#2E6F95", fg="white", font=("Segoe UI", 10, "bold"), padx=10, pady=6
        )
        self.dry_run_btn.pack(side="left")

        self.organize_btn = tk.Button(
            button_frame, text="Organize Now", command=self.run_organize,
            bg="#1F8A47", fg="white", font=("Segoe UI", 10, "bold"), padx=10, pady=6
        )
        self.organize_btn.pack(side="left", padx=(8, 0))

        self.status_label = tk.Label(self.root, text="Choose a folder to begin.", anchor="w", padx=12)
        self.status_label.pack(fill="x")

        log_frame = tk.Frame(self.root, padx=12, pady=8)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="Log", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.log_box = scrolledtext.ScrolledText(log_frame, wrap="word", font=("Consolas", 9), state="disabled")
        self.log_box.pack(fill="both", expand=True, pady=(4, 0))

    def browse_folder(self):
        selected = filedialog.askdirectory(title="Select the folder containing your PDFs")
        if selected:
            self.folder_path.set(selected)

    def _append_log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
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

    def run_dry_run(self):
        folder = self._validate_folder()
        if not folder:
            return
        self._clear_log()
        self.status_label.config(text="Previewing changes (no files touched)...")
        self.root.update_idletasks()

        results = process_folder(folder, dry_run=True, on_action=self._append_log)

        self.status_label.config(text=f"Preview complete — {len(results)} file(s) reviewed.")

    def run_organize(self):
        folder = self._validate_folder()
        if not folder:
            return

        confirm = messagebox.askyesno(
            "Confirm Organize",
            "This will move and rename PDF files in the selected folder.\n\nProceed?"
        )
        if not confirm:
            return

        self._clear_log()
        self.status_label.config(text="Organizing files...")
        self.root.update_idletasks()

        results = process_folder(
            folder, dry_run=False, log_path=str(folder / "organizer_log.txt"), on_action=self._append_log
        )

        self.status_label.config(text=f"Done — {len(results)} file(s) organized.")
        messagebox.showinfo("Complete", f"Organized {len(results)} file(s).\nLog saved to organizer_log.txt")


def main():
    root = tk.Tk()
    OrganizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()