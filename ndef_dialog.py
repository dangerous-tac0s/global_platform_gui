import tkinter as tk
from tkinter import ttk


class NDEFDialog(tk.Toplevel):
    """
    This returns the params for openNDEF-full
    """

    permissions_text_to_hex = {
        "open access": "00",
        "no access": "FF",
        "write once": "F1",
        "contact only": "F0",
    }

    permissions_hex_to_text = {v: k for k, v in permissions_text_to_hex.items()}

    def __init__(self, parent):
        super().__init__(parent)

        self.title("NDEF Configuration")
        self.update_idletasks()
        self.grab_set()

        self.initial_load = True
        self.result = None

        self.read_byte_value = tk.StringVar(value="open access")
        self.write_byte_value = tk.StringVar(value="open access")

        self.selected_size = tk.StringVar(value="1kB")

        # Create notebook and attach it to the window
        self.notebook = ttk.Notebook(self, width=450)
        self.notebook.pack(fill="both", expand=True)

        # Add tabs
        self.notebook.add(BasicTab(self.notebook, self), text="Basic")
        self.notebook.add(AdvancedTab(self.notebook, self), text="Advanced")

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        # Button frame
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

    def on_tab_change(self, event):
        if self.initial_load:
            self.initial_load = False
        else:
            selected_tab_index = self.notebook.index("current")
            selected_tab_text = self.notebook.tab(selected_tab_index, "text").lower()

            if selected_tab_text == "basic":
                # print("basic")
                pass
            elif selected_tab_text == "data":
                # print("data")
                pass
            elif selected_tab_text == "advanced":
                # print("advanced")
                pass
            else:
                print(f"Error changing tabs: {selected_tab_text}[{selected_tab_index}]")
                pass

    def ndef_data_entry(self):
        frame = tk.Frame(self.notebook)
        return frame

    def on_ok(self):
        """
        Generates our params for Global Platform Pro
        :return:
        """
        size = int(self.selected_size.get()[0:-2])
        size_in_bytes = size * 1024
        if size == 32:  # 32kB is 8000--highest we can go is 7FFF
            size_in_bytes -= 1

        self.result = f"8102{self.permissions_text_to_hex[self.read_byte_value.get()]}{self.permissions_text_to_hex[self.write_byte_value.get()]}8202{size_in_bytes:04X}"
        self.destroy()


class BasicTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller

        label = tk.Label(self, text="Choose an option:")
        label.pack(pady=10)

        options = ["1kB", "2kB", "4kB", "8kB", "16kB", "32kB"]

        size_dropdown = ttk.Combobox(
            self,
            textvariable=self.controller.selected_size,
            values=options,
            state="readonly",
        )
        size_dropdown.pack(pady=5)

        self.write_once_value = tk.IntVar(value=0)
        self.checkbox = tk.Checkbutton(
            self,
            text="Write Once",
            variable=self.write_once_value,
            command=self.on_checkbox_change,
        )
        self.checkbox.pack(pady=5)

    def on_checkbox_change(self):
        self.controller.write_byte_value.set(
            self.controller.permissions_hex_to_text[
                "00" if self.write_once_value.get() == 0 else "F1"
            ]
        )


class AdvancedTab(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller

        # Initial Data
        data_label = tk.Label(
            self,
            text="80 XX -- Data",
            font=("TkDefaultFont", 12, "bold"),
        )
        data_label.grid(row=0, column=0, columnspan=2, pady=10, padx=5, sticky="w")
        data_note = tk.Label(
            self, text="Optional", font=("TkDefaultFont", 10, "italic")
        )
        data_note.grid(row=0, column=2, columnspan=2, pady=10, padx=(0, 25), sticky="e")

        self.read_write_label = tk.Label(
            self,
            text="",
            font=("TkDefaultFont", 12, "bold"),
        )
        self.read_write_label.grid(
            row=1, column=0, columnspan=4, pady=10, padx=5, sticky="w"
        )

        read_label = tk.Label(self, text="Read Byte:")
        read_label.grid(row=2, column=0, pady=5, padx=5, sticky="w")
        self.read_dropdown = ttk.Combobox(
            self,
            textvariable=self.controller.read_byte_value,
            values=[
                x
                for x in list(self.controller.permissions_text_to_hex.keys())
                if x != "write once"
            ],
            state="readonly",
            width=10,
        )
        self.read_dropdown.grid(row=2, column=1, pady=5, padx=5)

        write_label = tk.Label(self, text="Write Byte:")
        write_label.grid(row=2, column=2, pady=5, padx=5, sticky="w")
        self.write_dropdown = ttk.Combobox(
            self,
            textvariable=self.controller.write_byte_value,
            values=list(self.controller.permissions_text_to_hex.keys()),
            state="readonly",
            width=10,
        )
        self.write_dropdown.grid(row=2, column=3, pady=5, padx=5)

        self.size_label = tk.Label(
            self,
            text="",
            font=("TkDefaultFont", 12, "bold"),
        )
        self.size_label.grid(row=3, column=0, columnspan=2, pady=10, padx=5, sticky="w")
        size_note = tk.Label(
            self, text="Optional", font=("TkDefaultFont", 10, "italic")
        )
        size_note.grid(row=3, column=2, columnspan=2, pady=10, padx=(0, 25), sticky="e")

        size_label = tk.Label(
            self,
            text="Container Size:",
        )
        size_label.grid(row=4, column=0, columnspan=2, pady=10, padx=5, sticky="w")
        options = ["1kB", "2kB", "4kB", "8kB", "16kB", "32kB"]
        self.size_dropdown = ttk.Combobox(
            self,
            textvariable=self.controller.selected_size,
            values=options,
            state="readonly",
        )
        self.size_dropdown.grid(row=4, column=2, columnspan=2, pady=5)

        # Update label when read/write values change
        self.controller.read_byte_value.trace_add("write", self.update_rw_label)
        self.controller.write_byte_value.trace_add("write", self.update_rw_label)
        self.controller.selected_size.trace_add("write", self.update_size_label)

        # Set initial label
        self.update_rw_label()
        self.update_size_label()

    def update_rw_label(self, *args):
        """Update the label text whenever read/write values change."""
        read_value = self.controller.read_byte_value.get()
        write_value = self.controller.write_byte_value.get()

        self.read_write_label.config(
            text=f"81 02 {self.controller.permissions_text_to_hex[read_value]} {self.controller.permissions_text_to_hex[write_value]} -- R/W Permissions"
        )

    def update_size_label(self, *args):
        decimal = int(self.controller.selected_size.get()[0:-2])
        bytes = decimal * 1024
        if decimal == 32:
            bytes -= 1

        hex_string = " ".join(
            f"{byte:02X}"
            for byte in bytes.to_bytes((bytes.bit_length() + 7) // 8, byteorder="big")
        )

        self.size_label.config(text=f"82 02 {hex_string}")
