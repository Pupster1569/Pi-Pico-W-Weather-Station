class ConfigParser:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigParser, cls).__new__(cls)
            cls._instance.config = {}
            cls._instance.file_read = False
        return cls._instance

    def read(self, filename):
        if self.file_read:
            return

        current_section = None
        try:
            with open(filename, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1].strip()
                        self.config[current_section] = {}
                    elif '=' in line and current_section is not None:
                        if '#' in line:
                            line = line.split('#')[0].strip()
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        self.config[current_section][key] = value
            self.file_read = True
        except Exception as e:
            print(f"Error reading file: {e}")

    def __getitem__(self, section):
        try:
            return ConfigSection(self.config[section])
        except KeyError:
            raise KeyError(f"Section '{section}' not found in the configuration.")

    def get(self, section, option, fallback=None):
        try:
            return self.config[section][option]
        except KeyError:
            return fallback

    def getint(self, section, option, fallback=None):
        value = self.get(section, option, fallback)
        return int(value) if value is not None else None

    def getfloat(self, section, option, fallback=None):
        value = self.get(section, option, fallback)
        return float(value) if value is not None else None

    def getboolean(self, section, option, fallback=None):
        value = self.get(section, option, fallback)
        if value is None:
            return None
        return value.lower() in ('true', 'yes', 'on', '1')

class ConfigSection:
    def __init__(self, section_dict):
        self.section_dict = section_dict

    def __getitem__(self, key):
        try:
            return self.section_dict[key]
        except KeyError:
            raise KeyError(f"Option '{key}' not found in this section.")

# Usage example:
# config = ConfigParser()
# config.read('settings.ini')
# wifi_ssid = config["Wi-Fi Settings"]["Wi-Fi SSID"]