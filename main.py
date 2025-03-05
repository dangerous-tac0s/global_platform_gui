import pprint
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import re

import requests
import threading
import os


class GPManagerApp:
    file_to_aid = {
    "FIDO2.cap": "A0000006472F0001",
    "javacard-memory.cap": "A0000008466D656D6F727901",
    "keycard.cap": "7465736C614C6F67696330303201",
    "openjavacard-ndef-full.cap": "D276000124010304000A000000000000",
    # "openjavacard-ndef-tiny.cap": "A0000005272102",
    #"SatoChip.cap": "A00000039654534E00",
    #"Satodime.cap": "A00000039654534E01",
    #"SeedKeeper.cap": "A00000039654534E02",
    "SmartPGPApplet-default.cap": "A000000151000000",
    "SmartPGPApplet-large.cap": "A000000151000001",
    "U2FApplet.cap": "A0000006472F0002",
    "vivokey-otp.cap": "A0000005272101014150455801",
    "YkHMACApplet.cap": "A000000527200101"
}


    aid_to_file = {name: aid for aid, name in file_to_aid.items()}

    def __init__(self, root):
        def get_os():
            if os.name == 'nt' or os.name == "posix":
                return os.name
            else:
                return 'Unknown'

        self.root = root
        self.root.title("GlobalPlatformPro App Manager")

        # UI Layout
        self.setup_ui()

        self.os = get_os()
        self.gp = {
             "posix":
                ["java", "-jar", "gp.jar"],
            "nt": ["gp.exe"]        }

        if self.os == "Unknown":
            messagebox.showerror("Error", f"Unable to determine OS.")

        # Data Containers
        self.installed_apps = []
        self.available_apps = []

        self.current_release = None

        # Startup Processes
        self.fetch_available_apps()

        self.detect_card_readers()
        threading.Thread(target=self.wait_for_card, daemon=True).start()


    def setup_ui(self):
        # Card Reader Selection
        self.reader_label = ttk.Label(self.root, text="Card Reader:")
        self.reader_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.reader_var = tk.StringVar()
        self.reader_dropdown = ttk.Combobox(self.root, textvariable=self.reader_var, state="readonly")
        self.reader_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.reader_dropdown.bind("<<ComboboxSelected>>", self.on_reader_selected)

        # Installed Apps List
        self.installed_label = ttk.Label(self.root, text="Installed Apps")
        self.installed_label.grid(row=1, column=0, padx=5, pady=5)

        self.installed_listbox = tk.Listbox(self.root, height=15, width=40)
        self.installed_listbox.grid(row=2, column=0, padx=5, pady=5)

        self.uninstall_button = ttk.Button(self.root, text="Uninstall", command=self.uninstall_app, state=tk.DISABLED)
        self.uninstall_button.grid(row=3, column=0, padx=5, pady=5)

        # Available Apps List
        self.available_label = ttk.Label(self.root, text="Available Apps")
        self.available_label.grid(row=1, column=1, padx=5, pady=5)

        self.available_listbox = tk.Listbox(self.root, height=15, width=40)
        self.available_listbox.grid(row=2, column=1, padx=5, pady=5)

        self.install_button = ttk.Button(self.root, text="Install", command=self.install_app, state=tk.DISABLED)
        self.install_button.grid(row=3, column=1, padx=5, pady=5)

    def on_reader_selected(self, event):
        selected_reader = self.reader_var.get()
        print(f"Selected reader: {selected_reader}")
        # Add logic here to handle reader selection

    def fetch_available_apps(self):
        """Fetch available apps from the latest GitHub release using the API."""
        repo = "DangerousThings/flexsecure-applets"
        url = f"https://api.github.com/repos/{repo}/releases/latest"

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

                self.available_apps = [link.split('/')[-1] for link in cap_files]
                self.update_available_list()
            else:
                print(f"GitHub API error: {response.status_code} - {response.text}")

                self.available_apps = []
                self.update_available_list()
        except Exception as e:
            print(f"Error: {e}")



    def detect_card_readers(self):
        """Detects connected smart card readers."""
        try:
            if self.os == "nt":
                # Windows: Use PySCARD
                import smartcard.System
                readers = [str(reader) for reader in smartcard.System.readers()]
            else:
                # Linux/macOS: Use pcsc_list_readers
                result = subprocess.run(["pcsc_scan", "-r"], capture_output=True, text=True)
                readers = [line.strip() for line in result.stdout.splitlines() if line.strip()]

            if readers:
                self.reader_dropdown["values"] = readers
                self.reader_var.set(readers[0])  # Select first reader by default
            else:
                messagebox.showwarning("No Readers Found", "No smart card readers detected.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to detect card readers: {e}")

    def detect_reader_and_wait_for_card(self):
        """Detects card readers and waits for a card to be presented."""
        try:
            self.detect_card_readers()
            if len(self.reader_dropdown['values']) > 0:
                self.wait_for_card()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to detect card readers: {e}")

    def wait_for_card(self):
        """Waits until a card is presented."""
        while True:
            result = subprocess.run([*self.gp[self.os], "-l"], capture_output=True, text=True)
            if "No card present" not in result.stdout:
                self.get_installed_apps()
                self.install_button["state"] = tk.NORMAL
                self.uninstall_button["state"] = tk.NORMAL
                break

    def get_installed_apps(self):
        """Fetch installed apps from gp.exe and map AIDs to names."""
        result = subprocess.run([*self.gp[self.os], "-l"], capture_output=True, text=True)
        output_lines = result.stdout.splitlines()

        aid_pattern = re.compile(r"(APP|Applet):\s([A-Fa-f0-9]+)")
        installed_aids = [match.group(2) for line in output_lines if (match := aid_pattern.search(line))]
        print(installed_aids)
        pprint.pprint(self.aid_to_file)

        self.installed_apps = [
            self.aid_to_file.get(aid, f"Unknown ({aid})") for aid in installed_aids
        ]

        # self.installed_apps = [ app for app in installed_aids if "Unknown" not in app]

        pprint.pprint(result)
        pprint.pprint(self.installed_apps)
        self.update_installed_list()

    def update_installed_list(self):
        self.installed_listbox.delete(0, tk.END)
        for app in sorted(self.installed_apps):
            self.installed_listbox.insert(tk.END, app)
        self.update_available_list()

    def update_available_list(self):
        self.available_listbox.delete(0, tk.END)
        for app in [each for each in sorted(self.available_apps) if each not in self.installed_apps]:
            self.available_listbox.insert(tk.END, app)

    def install_app(self):
        """Installs the selected app."""
        selected = self.available_listbox.curselection()
        if selected:
            app = self.available_listbox.get(selected[0])

            app_url = f"{self.current_release}/{app}"
            try:
                response = requests.get(app_url)
                if response.status_code == 200:
                    # Save the file locally
                    cap_file_path = app
                    with open(cap_file_path, 'wb') as f:
                        f.write(response.content)
                    print(f"Downloaded {app} to {cap_file_path}")
                else:
                    print(f"Failed to download {app}. Status code: {response.status_code}")
                    return  # If download fails, exit the method
            except requests.RequestException as e:
                print(f"Error downloading {app}: {e}")
                return

            # Install the app using gp.exe
            result = subprocess.run([*self.gp[self.os], "--install", app], capture_output=True, text=True)

            if "Install Success" in result.stdout:
                self.available_apps.remove(app)
                self.installed_apps.append(app)
                self.update_installed_list()
                # self.update_available_list()
            else:
                print(result)

            if os.path.exists(cap_file_path):
                os.remove(cap_file_path)  # Remove the CAP file after installation
                print(f"Removed the downloaded file: {cap_file_path}")
            else:
                print(f"CAP file not found for {app}.")

    def uninstall_app(self):
        """Uninstalls the selected app."""
        selected = self.installed_listbox.curselection()
        if selected:
            app = self.installed_listbox.get(selected[0])
            result = subprocess.run([*self.gp[self.os], "--uninstall", app], capture_output=True, text=True)
            if "Uninstall Success" in result.stdout:
                self.installed_apps.remove(app)
                self.available_apps.append(app)
                self.update_installed_list()
                self.update_available_list()


if __name__ == "__main__":
    root = tk.Tk()
    app = GPManagerApp(root)
    root.mainloop()
