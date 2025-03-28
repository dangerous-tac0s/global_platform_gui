import queue
import time
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
from smartcard.System import readers
from smartcard.CardConnection import CardConnection
from smartcard.util import toHexString

import re
import requests
import threading
import os

from measure import get_memory
from ndef_dialog import NDEFDialog

DEFAULT_KEY = "404142434445464748494A4B4C4D4E4F"


class GPManagerApp:
    file_to_aid = {
        "FIDO2.cap": "A0000006472F000101",
        "javacard-memory.cap": "A0000008466D656D6F727901",
        "keycard.cap": "A0000008040001",
        "openjavacard-ndef-full.cap": "D2760000850101",
        # "openjavacard-ndef-tiny.cap": "D2760000850101",
        "SatoChip.cap": "5361746F4368697000",
        "Satodime.cap": "5361746F44696D6500",
        "SeedKeeper.cap": "536565644B656570657200",
        "SmartPGPApplet-default.cap": "D276000124010304000A000000000000",
        "SmartPGPApplet-large.cap": "D276000124010304000A000000000000",
        "U2FApplet.cap": "A0000006472F0002",
        "vivokey-otp.cap": "A0000005272101014150455801",
        "YkHMACApplet.cap": "A000000527200101",
    }

    unsupported_apps = ["FIDO2.cap", "openjavacard-ndef-tiny.cap", "keycard.cap"]

    aid_to_file = {name: aid for aid, name in file_to_aid.items()}

    def __init__(self, root):
        def get_os():
            if os.name == "nt" or os.name == "posix":
                return os.name
            else:
                return "Unknown"

        self.root = root
        self.root.title("GlobalPlatformPro App Manager")

        # UI Layout
        self.setup_ui()

        self.os = get_os()

        # Get status label width
        self.root.update_idletasks()
        # Account for x padding
        self.status_label_width = (
            self.status_label.winfo_width() - 20 if self.os == "nt" else 0
        )
        self.status_label.config(width=self.status_label_width)

        self.status_queue = queue.Queue()
        self.process_status_messages()
        self.memory = None

        self.loading = True
        self.card_detected = False
        self.card_present = False  # Used to track state changes
        self.running = False  # Used to stop the thread if needed

        if self.os == "Unknown":
            messagebox.showerror("Error", f"Unable to determine OS.")

        self.current_release = None
        # Data Containers
        self.installed_apps = []
        self.available_apps = []

        self.gp = {
            "posix": [
                "java",
                "-jar",
                "gp.jar",
                "-k",
                DEFAULT_KEY,
                "--reader",
                self.reader_var.get(),
            ],
            "nt": [
                "gp.exe",
                "-k",
                DEFAULT_KEY,
                "--reader",
                self.reader_var.get(),
            ],
        }

        # Startup Processes
        self.fetch_available_apps()
        self.detect_card_readers()

    def setup_ui(self):
        self.reader_var = tk.StringVar()
        self.reader_dropdown = ttk.Combobox(
            self.root, textvariable=self.reader_var, state=tk.DISABLED
        )
        self.reader_dropdown.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.reader_dropdown.bind("<<ComboboxSelected>>", self.on_reader_selected)

        self.status_label = ttk.Label(self.root, text="Starting...")
        self.status_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        frame = tk.Frame(root, height=1, bg="gray")
        frame.grid(row=1, column=0, columnspan=2, sticky="ew")

        # Installed Apps List
        self.installed_label = ttk.Label(self.root, text="Installed Apps")
        self.installed_label.grid(row=2, column=0, padx=5, pady=5)

        self.installed_listbox = tk.Listbox(self.root, height=15, width=40)
        self.installed_listbox.grid(row=3, column=0, padx=5, ipady=5)

        self.uninstall_button = ttk.Button(
            self.root, text="Uninstall", command=self.uninstall_app, state=tk.DISABLED
        )
        self.uninstall_button.grid(row=4, column=0, padx=5, pady=5)

        # Available Apps List
        self.available_label = ttk.Label(self.root, text="Available Apps")
        self.available_label.grid(row=2, column=1, padx=5, pady=10)

        self.available_listbox = tk.Listbox(self.root, height=15, width=40)
        self.available_listbox.grid(row=3, column=1, padx=5, ipady=5)

        self.install_button = ttk.Button(
            self.root, text="Install", command=self.install_app, state=tk.DISABLED
        )
        self.install_button.grid(row=4, column=1, padx=5, pady=10)

    def is_jcop3(self, atr_string):
        result = subprocess.run(
            [*self.gp[self.os], "--info"], capture_output=True, text=True
        )

        is_v3 = False
        if len(result.stderr) == 0 or (
            len(result.stderr) > 0 and "WARN" in result.stderr
        ):
            for each in result.stdout.splitlines():
                if "JavaCard v3" in each:
                    is_v3 = True
                    break
        return is_v3

    def on_reader_selected(self, event):
        selected_reader = self.reader_var.get()
        print(f"Selected reader: {selected_reader}")

    def fetch_available_apps(self):
        """Fetch available apps from the latest GitHub release using the API."""
        repo = "DangerousThings/flexsecure-applets"
        url = f"https://api.github.com/repos/{repo}/releases/latest"

        self.set_loading(True)
        self.update_status(f"Finding latest release...")

        try:
            response = requests.get(url)
            if response.status_code == 200:
                release_data = response.json()
                cap_files = [
                    asset["browser_download_url"]
                    for asset in release_data.get("assets", [])
                    if asset["name"].endswith(".cap")
                ]

                chunked = cap_files[0].split("/")
                chunked.pop()
                self.current_release = "/".join(chunked)

                self.available_apps = [link.split("/")[-1] for link in cap_files]
                self.available_apps = [
                    link
                    for link in self.available_apps
                    if link not in self.unsupported_apps
                ]
                self.update_available_list()
                self.update_status(
                    f"Available apps fetched: {len(self.available_apps) if len(self.available_apps) > 0 else 'None'}"
                )
            else:
                self.update_status(f"Unable to fetch current release.")
                print(f"GitHub API error: {response.status_code} - {response.text}")

                self.available_apps = []
                self.update_available_list()
        except Exception as e:
            print(f"Error: {e}")

        self.set_loading(False)

    def detect_card_readers(self, retry=True, delay=2000):
        """Detects connected smart card readers. Retries if none are found."""
        try:
            result = subprocess.run(
                # Slice the command to exclude the selected reader as we are getting our options now
                [*self.gp[self.os][0 : 5 if self.os == "posix" else 3], "-r"],
                capture_output=True,
                text=True,
            )

            reader_list = [
                line.strip().replace("- ", "")
                for line in result.stdout.splitlines()
                if line.strip() and "Available" not in line
            ]

            if reader_list and len(reader_list) > 0:
                self.reader_dropdown["values"] = reader_list
                self.reader_dropdown.config(state="readonly")

                # Was this a retry? Is our previously selected reader still present?
                if self.reader_var.get() not in reader_list:
                    # Not a retry or old reader not connected
                    self.reader_var.set(
                        reader_list[0]
                    )  # Select first reader by default
                self.update_status(f"Reader detected: {reader_list[0]}")

                # If the card detection thread isn't running, start it
                if not self.running:
                    self.running = True
                    self.card_thread = threading.Thread(
                        target=self.detect_card_loop, daemon=True
                    )
                    self.card_thread.start()
            else:
                if len(self.reader_dropdown["values"]) != 0:
                    self.reader_dropdown.config(state=tk.DISABLED)
                    self.reader_dropdown["values"] = []
                    self.reader_var.set("")
                if "No readers" not in self.status_label.cget("text"):
                    self.update_status("No readers found")
                if retry:
                    self.root.after(
                        delay, self.detect_card_readers
                    )  # Retry after delay
        except Exception as e:
            if "No readers" not in self.status_label.cget("text"):
                self.update_status("No readers found")
            print(f"Error detecting card readers: {e}")
            if retry:
                self.root.after(delay, self.detect_card_readers)  # Retry after delay

    def detect_card_loop(self):
        """Continuously checks for smartcard presence in the background."""
        r = readers()
        # No readers found on app startup
        if len(r) == 0:
            self.running = False
            self.detect_card_readers()
            return

        reader_strings = [str(reader) for reader in r]
        selected_reader = self.reader_var.get()
        reader_index = reader_strings.index(selected_reader)
        reader = r[reader_index]
        connection = reader.createConnection()

        while self.running:
            # App is doing something--don't step on its updates
            if self.loading:
                time.sleep(2)
                pass

            r = readers()
            # Readers connected have changed -- recheck
            if len(r) != len(self.reader_dropdown["values"]):
                self.detect_card_readers()
                self.running = False
                return

            try:
                connection.connect(CardConnection.T1_protocol)
                atr = connection.getATR()
                atr_str = toHexString(atr)

                if self.is_jcop3(atr_str):  # JCOP detected
                    if (
                        not self.card_present
                        or "Memory Free:" not in self.status_label.cget("text")
                        or "Card present." not in self.status_label.cget("text")
                    ):
                        if self.memory is None:
                            self.update_status("Card present.")
                        else:
                            self.update_status(
                                f"Memory Free: {self.memory["persistent"]["free"]/1024:.0f}kB -- ({self.memory["persistent"]["percent_free"]:.0%})"
                            )
                        self.card_detected = True

                        if not self.card_present:  # First time detecting card
                            self.card_present = True
                            self.get_installed_apps()
                            self.update_button_state(False)
                            self.update_memory()

                else:  # Card detected but not JCOP
                    self.update_status(f"Card detected, but not JCOP.")
                    self.card_detected = True
                    self.update_button_state(True)

            except Exception:  # No card present
                self.card_detected = False
                if (
                    self.card_present
                    or self.status_label.cget("text") != "No card present."
                ):  # Only update if it was previously detected
                    self.card_present = False
                    self.update_status("No card present.")
                    self.update_button_state(True)

            time.sleep(1)  # Polling interval (adjust if needed)

    def get_installed_apps(self):
        """Fetch installed apps from gp.exe and map AIDs to names."""
        self.update_status("Getting installed apps...")

        result = subprocess.run(
            [*self.gp[self.os], "-l"], capture_output=True, text=True
        )
        output_lines = result.stdout.splitlines()

        aid_pattern = re.compile(r"(APP|Applet):\s+([A-Fa-f0-9]+)")

        installed_aids = [
            match.group(2)
            for line in output_lines
            if (match := aid_pattern.search(line))
        ]
        # The AID might be matched on multiple lines of the same record
        installed_aids = list(set(installed_aids))

        self.installed_apps = [
            self.aid_to_file.get(aid, f"Unknown ({aid})") for aid in installed_aids
        ]

        self.update_installed_list()
        self.update_status(
            f"Found {len(self.installed_apps) if len(self.installed_apps) != 0 else "no"} apps."
        )

    def update_installed_list(self):
        self.installed_listbox.delete(0, tk.END)
        for app in sorted(self.installed_apps):
            self.installed_listbox.insert(tk.END, app)
        self.update_available_list()

    def update_available_list(self):
        self.available_listbox.delete(0, tk.END)
        for app in [
            each
            for each in sorted(self.available_apps)
            if each not in self.installed_apps
        ]:
            self.available_listbox.insert(tk.END, app)

    def get_app(self, app: str):
        app_url = f"{self.current_release}/{app}"
        try:
            response = requests.get(app_url)
            if response.status_code == 200:
                # Save the file locally
                cap_file_path = app
                with open(cap_file_path, "wb") as f:
                    f.write(response.content)
                print(f"Downloaded {app}")
                return app
            else:
                print(f"Failed to download {app}. Status code: {response.status_code}")
                return None
        except requests.RequestException as e:
            print(f"Error downloading {app}: {e}")
            return None

    def cleanup_app(self, app: str):
        if os.path.exists(app):
            os.remove(app)  # Remove the CAP file after installation
            print(f"Removed the downloaded file: {app}")
        else:
            print(f"CAP file not found for {app}.")

    def install_app(self):
        """Installs the selected app."""
        selected = self.available_listbox.curselection()
        if selected:
            app = self.available_listbox.get(selected[0])
            if app in self.unsupported_apps:
                self.update_status(f"That app is not supported by this application.")
                return

            self.set_loading(True)

            self.update_status("Downloading latest version...")
            file = self.get_app(app)
            self.update_status("Keep smartcard on reader!")

            if file:
                install_command = [*self.gp[self.os], "--install", file]
                if "ndef" in app:
                    res = self.open_ndef_dialog()

                    # Cancel was pressed
                    if not res:
                        self.cleanup_app(app)
                        return

                    # Updating command with params
                    print(f"Params string: {res}")
                    install_command.append("--params")
                    install_command.append(res)

                # Install the app using gp.exe
                result = subprocess.run(
                    install_command,
                    capture_output=True,
                    text=True,
                )

                if len(result.stderr) == 0:
                    self.available_apps.remove(app)
                    self.installed_apps.append(app)
                    self.update_installed_list()
                    self.update_status(f"{app} installed")
                    self.update_available_list()
                    self.update_memory()
                else:
                    self.update_status("Installation failed")
                    print(result.stderr)

            self.cleanup_app(app)
            self.set_loading(False)

    def uninstall_app(self):
        """Uninstalls the selected app."""
        selected = self.installed_listbox.curselection()
        if selected and not self.loading:
            app = self.installed_listbox.get(selected[0])

            if "Unknown" in app:
                # Attempt to remove an app that likely came preinstalled
                self.update_status("Uninstalling...")
                match = re.search(r"\(([A-Z0-9]+)\)$", app)
                if match:
                    aid = match.group(1)

                    result = subprocess.run(
                        [*self.gp[self.os], "--delete", aid, "--force"],
                        capture_output=True,
                        text=True,
                    )
                    if len(result.stderr) == 0:
                        if app in self.installed_apps:
                            self.installed_apps.remove(app)
                            self.update_installed_list()
                        self.update_memory()
                    else:
                        self.update_status("Unable to uninstall")
                        print(result.stderr)
                return

            self.set_loading(True)
            self.update_status(f"Uninstalling {app}...")

            file = self.get_app(app)

            if file:
                result = subprocess.run(
                    [*self.gp[self.os], "--uninstall", app],
                    capture_output=True,
                    text=True,
                )

                if app == "FIDO2.cap" and "not present" in result.stderr:
                    # Probably U2F
                    file = self.get_app("U2FApplet.cap")

                    if file:
                        result = subprocess.run(
                            [*self.gp[self.os], "--uninstall", file],
                            capture_output=True,
                            text=True,
                        )

                        self.cleanup_app(file)

                if len(result.stderr) == 0:
                    if app in self.installed_apps:
                        self.installed_apps.remove(app)
                        self.update_installed_list()
                    if app not in self.available_apps:
                        self.available_apps.append(app)
                        self.update_available_list()
                    self.update_status(f"{app} uninstalled")
                    self.set_loading(False)
                    self.update_memory()
                else:
                    # The actual gp -uninstall command
                    self.update_status("Error during uninstallation")
                    print(result.stderr)
                self.cleanup_app(app)
            else:
                self.update_status("Unable to get cap file")

            self.set_loading(False)

    def update_status(self, message):
        """Queue a status message to be processed in the main thread."""
        self.status_queue.put(message)

    def process_status_messages(self):
        """Process queued status messages to update the UI immediately."""
        while not self.status_queue.empty():
            message = self.status_queue.get()
            self.status_label.config(text=f"{message:<{self.status_label_width}}")
            self.root.update_idletasks()  #
            time.sleep(1)

        self.root.after(10, self.process_status_messages)

    def update_button_state(self, disable_buttons):
        """Enable or disable buttons immediately based on card presence."""
        state = tk.DISABLED if disable_buttons else tk.NORMAL
        if self.install_button.cget("state") != state:
            self.install_button.config(state=state)
            self.uninstall_button.config(state=state)
            self.root.update_idletasks()

    def set_loading(self, loading: bool):
        if loading != self.loading:
            self.loading = loading
        self.update_button_state(loading if self.card_present else True)

    def update_memory(self):
        self.memory = get_memory()

    def open_ndef_dialog(self):
        dialog = NDEFDialog(root)
        root.wait_window(dialog)

        return dialog.result


if __name__ == "__main__":
    root = tk.Tk()
    app = GPManagerApp(root)
    root.mainloop()
