import tkinter as tk
from tkinter import ttk


class NDEFDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Select an Option")
        self.geometry("300x150")
        # self.transient(self)
        self.grab_set()

        self.result = None

        self.label = tk.Label(self, text="Choose an option:")
        self.label.pack(pady=10)

        options = ["1kB", "2kB", "4kB", "8kB", "16kB", "32kB"]
        self.selected_value = tk.StringVar(value=options[0])

        self.dropdown = ttk.Combobox(
            self, textvariable=self.selected_value, values=options, state="readonly"
        )
        self.dropdown.pack(pady=5)

        self.button_frame = tk.Frame(self)
        self.button_frame.pack(pady=10)

        ttk.Button(self.button_frame, text="Cancel", command=self.destroy).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(
            self.button_frame,
            text="Create",
            command=self.on_ok,
        ).pack(side=tk.RIGHT, padx=5)

    def on_ok(self):
        self.result = self.selected_value.get()
        self.destroy()
