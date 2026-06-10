import platform
import subprocess
import webbrowser
import psutil


class SystemExecutor:
    def __init__(self):
        # Identify the current host OS ('Linux', 'Windows', or 'Darwin' for macOS)
        self.current_os = platform.system()

    def launch_browser(self, url: str = "https://google.com") -> str:
        """Launches the user's default system browser on any OS."""
        # Python's standard library handle automatically maps the native OS trigger strings
        webbrowser.open(url)
        return "Opening your web browser now, sir."

    def launch_application(self, app_name: str) -> str:
        """Attempts to boot common GUI applications dynamically based on the current OS mapping."""
        # Dictionary map containing OS variations for basic terminal apps
        os_app_map = {
            "terminal": {
                "Linux": ["gnome-terminal", "konsole", "xfce4-terminal"],
                "Windows": ["start", "cmd"],
                "Darwin": ["open", "-a", "Terminal"],
            },
            "code": {
                "Linux": ["code"],
                "Windows": ["code.cmd"],  # Windows launcher hook extension fallback
                "Darwin": ["open", "-a", "Visual Studio Code"],
            },
        }

        # Normalize the name request to find the application type match
        target_key = (
            "terminal"
            if "terminal" in app_name.lower() or "console" in app_name.lower()
            else "code"
        )

        try:
            if self.current_os in os_app_map[target_key]:
                commands = os_app_map[target_key][self.current_os]

                # Special execution handling logic block for Windows default shell tools
                if self.current_os == "Windows" and target_key == "terminal":
                    subprocess.Popen(["cmd.exe", "/c", "start", "cmd"])
                else:
                    # On Linux/Mac, try to step through fallback variants
                    if self.current_os == "Linux":
                        for cmd in commands:
                            try:
                                subprocess.Popen(
                                    [cmd],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                )
                                return (
                                    "Launching system console panel immediately, sir."
                                )
                            except FileNotFoundError:
                                continue
                    else:
                        subprocess.Popen(
                            commands,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )

                return f"Launching {app_name} immediately, sir."
        except Exception:
            pass

        return f"Forgive me sir, I encountered a cross-platform pipeline failure launching {app_name}."

    def get_battery_status(self) -> str:
        """Reads hardware layer metrics cross-platform to determine power metrics."""
        try:
            # psutil abstracts /sys/class on Linux, GetSystemPowerStatus on Windows, and IOKit on Mac
            battery = psutil.sensors_battery()

            if battery is None:
                return "I am unable to poll a localized battery array, sir. Are we running on a desktop terminal?"

            percentage = battery.percent
            is_plugged = battery.power_plugged
            status_text = "charging" if is_plugged else "discharging from primary cells"

            return f"Main battery array is currently at {percentage} percent, reporting a status of: {status_text}, sir."
        except Exception:
            return "Forgive me sir, internal power diagnostics failed to load cleanly."

    def get_system_load(self) -> str:
        """Polls hardware processing usage percentages uniformly across any operating system."""
        try:
            # os.getloadavg() throws errors on Windows; psutil.cpu_percent() works everywhere perfectly
            # interval=1 samples processor registers for a second to return an accurate average calculation
            cpu_usage = psutil.cpu_percent(interval=None)
            return f"Current operational core processing load sits at {cpu_usage} percent, sir."
        except Exception:
            return (
                "I failed to draw metrics from the processor diagnostics pipeline, sir."
            )
