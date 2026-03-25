import os
import yaml
import json
import base64
import hashlib
import urllib.parse
import datetime
from typing import List
from core.node_parser import Node

class NodeSaver:
    def __init__(self, cache_dir="cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _resolve_path(self, relative_path: str):
        path = os.path.join(self.cache_dir, relative_path)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return path

    def _save_yaml_nodes(self, nodes: List[Node], filename: str, label: str):
        path = self._resolve_path(filename)
        data = {"proxies": [n.config for n in nodes]}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        print(f"[保存] {label}Clash → {path}")

    def save_named_nodes(self, nodes: List[Node], yaml_name: str, v2rayn_name: str, label: str, subdir: str = ""):
        yaml_path = os.path.join(subdir, yaml_name) if subdir else yaml_name
        v2rayn_path = os.path.join(subdir, v2rayn_name) if subdir else v2rayn_name
        self._save_yaml_nodes(nodes, yaml_path, label)
        self.save_v2rayn_format(nodes, v2rayn_path)

    def save_subscription_snapshot(self, records):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        folder = os.path.join(self.cache_dir, "subscriptions", ts)
        os.makedirs(folder, exist_ok=True)

        index = []
        for i, r in enumerate(records, start=1):
            src = str(r.get("source_url", ""))
            target = str(r.get("target_url", ""))
            ok = bool(r.get("ok", False))
            status = int(r.get("status", 0) or 0)
            error = str(r.get("error", ""))
            content = str(r.get("content", "") or "")
            digest = hashlib.md5(src.encode("utf-8", errors="ignore")).hexdigest()[:8]
            filename = f"{i:03d}_{'ok' if ok else 'fail'}_{digest}.yaml"

            with open(os.path.join(folder, filename), "w", encoding="utf-8") as f:
                f.write(content)

            index.append({
                "id": i,
                "source_url": src,
                "target_url": target,
                "ok": ok,
                "status": status,
                "error": error,
                "file": filename,
            })

        with open(os.path.join(folder, "index.yaml"), "w", encoding="utf-8") as f:
            yaml.dump({"subscriptions": index}, f, allow_unicode=True, sort_keys=False)

        print(f"[保存] 订阅快照 → {folder}")
        return folder

    # 去重后保存
    def save_unique_nodes(self, nodes: List[Node]):
        self._save_yaml_nodes(nodes, os.path.join("unique", "unique_nodes.yaml"), "去重")

    def save_v2rayn_format(self, nodes: List[Node], suffix="unique_v2rayn.txt"):
        path = self._resolve_path(suffix)
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
        self.save_named_nodes(nodes, "delay_available_nodes.yaml", "delay_available_v2rayn.txt", "可用", subdir="delay")

    # === 工具 ===
    def _q(self, s):
        return urllib.parse.quote(str(s or ""), safe="")

    def _bool01(self, value):
        return "1" if bool(value) else "0"

    def _join_alpn(self, value):
        if isinstance(value, list):
            return ",".join(str(x) for x in value if x)
        return str(value or "")

    def _fingerprint(self, c):
        return c.get("client-fingerprint") or "chrome"

    def _vmess(self, n):
        c = n.config
        network = c.get("network", "tcp")
        ws_opts = c.get("ws-opts") or {}
        ws_headers = ws_opts.get("headers") or {}
        host = ws_headers.get("Host") or c.get("host", "")
        path = ws_opts.get("path") or c.get("path", "")
        tls_enabled = bool(c.get("tls", False))
        cfg = {
            "v": "2", "ps": n.name, "add": c["server"], "port": c["port"],
            "id": c.get("uuid", ""), "aid": c.get("alterId", 0),
            "scy": c.get("cipher", "auto"), "net": network,
            "type": "none",
            "host": host, "path": path,
            "tls": "tls" if tls_enabled else "",
            "sni": c.get("servername") or c.get("sni") or "",
            "alpn": self._join_alpn(c.get("alpn")),
            "fp": c.get("client-fingerprint", ""),
            "insecure": self._bool01(c.get("skip-cert-verify", False)),
        }
        return "vmess://" + base64.b64encode(json.dumps(cfg, ensure_ascii=False).encode()).decode()

    def _vless(self, n):
        c = n.config
        network = c.get("network", "tcp")
        ws_opts = c.get("ws-opts") or {}
        ws_headers = ws_opts.get("headers") or {}
        host = ws_headers.get("Host") or c.get("host", "")
        path = ws_opts.get("path") or c.get("path", "")
        security = "tls" if c.get("tls", False) else "none"
        reality_opts = c.get("reality-opts") or {}
        if reality_opts:
            security = "reality"
        params = [
            "encryption=none",
            f"security={security}",
            f"type={network}",
            f"insecure={self._bool01(c.get('skip-cert-verify', False))}",
            f"allowInsecure={self._bool01(c.get('skip-cert-verify', False))}",
        ]
        if host:
            params.append(f"host={self._q(host)}")
        if path:
            params.append(f"path={self._q(path)}")
        sni = c.get("servername") or c.get("sni") or ""
        if sni:
            params.append(f"sni={self._q(sni)}")
        if c.get("flow"):
            params.append(f"flow={self._q(c.get('flow'))}")
        fp = c.get("client-fingerprint")
        if fp:
            params.append(f"fp={self._q(fp)}")
        alpn = self._join_alpn(c.get("alpn"))
        if alpn:
            params.append(f"alpn={self._q(alpn)}")
        if reality_opts:
            if reality_opts.get("public-key"):
                params.append(f"pbk={self._q(reality_opts.get('public-key'))}")
            if reality_opts.get("short-id"):
                params.append(f"sid={self._q(reality_opts.get('short-id'))}")
            if reality_opts.get("spider-x"):
                params.append(f"spx={self._q(reality_opts.get('spider-x'))}")
        return f"vless://{c.get('uuid')}@{c['server']}:{c['port']}?{'&'.join(params)}#{self._q(n.name)}"

    def _trojan(self, n):
        c = n.config
        sni = c.get("servername") or c.get("sni") or ""
        params = [
            "security=tls",
            f"insecure={self._bool01(c.get('skip-cert-verify', False))}",
            f"allowInsecure={self._bool01(c.get('skip-cert-verify', False))}",
            f"type={c.get('network', 'tcp')}",
            "headerType=none",
        ]
        if sni:
            params.append(f"sni={self._q(sni)}")
        fp = c.get("client-fingerprint")
        if fp:
            params.append(f"fp={self._q(fp)}")
        alpn = self._join_alpn(c.get("alpn"))
        if alpn:
            params.append(f"alpn={self._q(alpn)}")
        pwd = self._q(c.get("password", ""))
        return f"trojan://{pwd}@{c['server']}:{c['port']}?{'&'.join(params)}#{self._q(n.name)}"

    def _ss(self, n):
        c = n.config
        method = c.get("cipher") or c.get("method") or ""
        u = f"{method}:{c.get('password', '')}"
        b64 = base64.b64encode(u.encode()).decode().rstrip("=")
        return f"ss://{b64}@{c['server']}:{c['port']}#{self._q(n.name)}"