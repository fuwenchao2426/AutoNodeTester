import yaml
import os
from typing import List, Dict

class ConfigLoader:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.config = self._load_yaml("config.yaml")
        self.list_dir = os.path.join(config_dir, "list")

    def _load_yaml(self, filename: str) -> Dict:
        path = os.path.join(self.config_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_list(self, filename: str) -> List[str]:
        path = os.path.join(self.list_dir, filename)
        result = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    result.append(line)
        return result

    # 主配置
    def get_main(self) -> Dict: return self.config

    # 列表
    def subscriptions(self) -> List[str]: return self._load_list("subscriptions.txt")
    def region_blacklist(self) -> List[str]: return self._load_list("region_blacklist.txt")
    def region_whitelist(self) -> List[str]: return self._load_list("region_whitelist.txt")
    def check_websites(self) -> List[str]: return self._load_list("check_websites.txt")
    def require_websites(self) -> List[str]: return self._load_list("require_websites.txt")
    def fallback_proxies(self) -> List[str]: return self._load_list("fallback_proxies.txt")