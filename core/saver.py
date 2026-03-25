import os
import yaml
import json
import base64
from typing import List
from core.node_parser import Node

class NodeSaver:
    def __init__(self, cache_dir="cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    # 去重后保存
    def save_unique_nodes(self, nodes: List[Node]):
        path = os.path.join(self.cache_dir, "unique_nodes.yaml")
        data = {"proxies": [n.config for n in nodes]}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        print(f"[保存] 去重Clash → {path}")

    def save_v2rayn_format(self, nodes: List[Node], suffix="unique_v2rayn.txt"):
        path = os.path.join(self.cache_dir, suffix)
        lines = []
        for n in nodes:
            try:
                if n.type == "vmess":
                    lines.append(self._vmess(n))
                elif n.type == "vless":
                    lines.append(self._vless(n))
                elif n.type == "trojan":
                    lines.append(self._trojan(n))
                elif n.type in ["ss", "shadowsocks"]:
                    lines.append(self._ss(n))
            except:
                continue
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"[保存] V2RayN → {path}")

    # 保存【延迟可用】节点
    def save_delay_available(self, nodes: List[Node]):
        path = os.path.join(self.cache_dir, "delay_available_nodes.yaml")
        data = {"proxies": [n.config for n in nodes]}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        print(f"[保存] 可用Clash → {path}")
        self.save_v2rayn_format(nodes, "delay_available_v2rayn.txt")

    # === 工具 ===
    def _vmess(self, n):
        c = n.config
        cfg = {
            "v": "2", "ps": n.name, "add": c["server"], "port": c["port"],
            "id": c.get("uuid", ""), "aid": c.get("alterId", 0),
            "scy": c.get("cipher", "auto"), "net": c.get("network", "tcp"),
            "host": c.get("host", ""), "path": c.get("path", ""),
            "tls": c.get("tls", ""), "sni": c.get("servername", "")
        }
        return "vmess://" + base64.b64encode(json.dumps(cfg, ensure_ascii=False).encode()).decode()

    def _vless(self, n):
        c = n.config
        return f"vless://{c.get('uuid')}@{c['server']}:{c['port']}?type={c.get('network','tcp')}&host={c.get('host','')}&path={c.get('path','')}&tls={c.get('tls','')}&sni={c.get('servername','')}#{n.name}"

    def _trojan(self, n):
        c = n.config
        return f"trojan://{c.get('password')}@{c['server']}:{c['port']}?sni={c.get('servername','')}#{n.name}"

    def _ss(self, n):
        c = n.config
        u = f"{c.get('method')}:{c.get('password')}"
        return f"ss://{base64.b64encode(u.encode()).decode()}@{c['server']}:{c['port']}#{n.name}"