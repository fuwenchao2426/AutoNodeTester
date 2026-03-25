import subprocess
import time
import os
import json
import tempfile
import platform

class XrayRunner:
    def __init__(self):
        self.xray = "xray.exe" if platform.system() == "Windows" else "xray"
        self.proc = None
        self.cfg = None

    def generate_config(self, node, port):
        c = node.config
        protocol = node.type.lower()

        stream = {
            "network": c.get("network", "tcp"),
            "security": "tls" if c.get("tls", False) else "none",
            "tlsSettings": {
                "serverName": c.get("servername", ""),
                "fingerprint": "chrome"
            }
        }

        if stream["network"] == "ws":
            stream["wsSettings"] = {
                "path": c.get("path", ""),
                "headers": {"Host": c.get("host", "")}
            }

        out = None
        if protocol == "vmess":
            out = {
                "protocol": "vmess",
                "settings": {"vnext": [{
                    "address": c["server"],
                    "port": c["port"],
                    "users": [{"id": c.get("uuid", ""), "security": "auto"}]
                }]},
                "streamSettings": stream
            }
        elif protocol == "vless":
            out = {
                "protocol": "vless",
                "settings": {"vnext": [{
                    "address": c["server"],
                    "port": c["port"],
                    "users": [{"id": c.get("uuid", ""), "encryption": "none"}]
                }]},
                "streamSettings": stream
            }
        elif protocol == "trojan":
            out = {
                "protocol": "trojan",
                "settings": {"servers": [{
                    "address": c["server"],
                    "port": c["port"],
                    "password": c.get("password", "")
                }]},
                "streamSettings": stream
            }
        elif protocol in ["ss", "shadowsocks"]:
            out = {
                "protocol": "shadowsocks",
                "settings": {"servers": [{
                    "address": c["server"],
                    "port": c["port"],
                    "method": c.get("method", ""),
                    "password": c.get("password", "")
                }]}
            }

        config = {
            "log": {"loglevel": "none"},
            "inbounds": [{"port": port, "listen": "127.0.0.1", "protocol": "socks", "settings": {"auth": "noauth"}}],
            "outbounds": [out]
        }

        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(path, "w") as f:
            json.dump(config, f)
        self.cfg = path
        return port

    def start(self):
        if not self.cfg:
            return False
        try:
            self.proc = subprocess.Popen(
                [self.xray, "run", "-c", self.cfg],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000
            )
            time.sleep(0.7)
            return self.proc.poll() is None
        except:
            return False

    def stop(self):
        try:
            self.proc.terminate()
        except:
            pass
        try:
            os.unlink(self.cfg)
        except:
            pass
        self.proc = None
        self.cfg = None