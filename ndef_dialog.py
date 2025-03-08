import tkinter as tk
from tkinter import ttk


class NDEFDialog(tk.Toplevel):
    """
    This returns the params for openNDEF-full
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.title("Select an Option")
        self.geometry("300x180")
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

        self.write_once_value = tk.IntVar()
        self.checkbox = tk.Checkbutton(
            self, text="Write Once", variable=self.write_once_value
        )
        self.checkbox.pack(pady=5)

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
        size = int(self.selected_value.get()[0:-2])
        size_in_bytes = size * 1024
        if size == 32:  # 32kB is 8000--highest we can go is 7FFF
            size_in_bytes -= 1
        """
        80      -> Data Initial
                XX  -> Length
                X+  -> Data in hex
                
        Container will be sized to this record if Data Size is not provided.
        """
        """
        81 02   -> Data Access
        Options:
                00  ->  Open Access
                FF  ->  No Access
                F1  ->  Write Once
                F0  ->  Contact Only
        """
        read_permissions = "00"
        write_permissions = "00" if self.write_once_value.get() == 0 else "F1"
        """
        82 02   -> Data Size
            XX XX   -> Size of container in bytes--in hex. 0100 to 7FFF
        """

        self.result = (
            f"8102{read_permissions}{write_permissions}8202{size_in_bytes:04X}"
        )
        self.destroy()
