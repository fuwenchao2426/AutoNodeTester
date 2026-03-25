import subprocess
import time
import os
import json
import tempfile
import platform
import socket

class XrayRunner:
    def __init__(self, pretest=True, port_wait_timeout=1.2):
        self.xray = "xray.exe" if platform.system() == "Windows" else "xray"
        self.proc = None
        self.cfg = None
        self.listen_port = None
        self.errfile = None
        self.last_error = ""
        self.pretest = pretest
        self.port_wait_timeout = port_wait_timeout

    def _build_stream_settings(self, c):
        network = c.get("network", "tcp")
        server_name = c.get("servername") or c.get("sni") or ""
        fingerprint = c.get("client-fingerprint") or "chrome"
        allow_insecure = c.get("skip-cert-verify", False)

        stream = {
            "network": network,
            "security": "none"
        }

        reality_opts = c.get("reality-opts") or {}
        if reality_opts:
            stream["security"] = "reality"
            stream["realitySettings"] = {
                "serverName": server_name,
                "fingerprint": fingerprint,
                "publicKey": reality_opts.get("public-key", ""),
                "shortId": reality_opts.get("short-id", ""),
                "spiderX": reality_opts.get("spider-x", "")
            }
        elif c.get("tls", False):
            stream["security"] = "tls"
            stream["tlsSettings"] = {
                "serverName": server_name,
                "fingerprint": fingerprint,
                "allowInsecure": allow_insecure,
            }
            if c.get("alpn"):
                stream["tlsSettings"]["alpn"] = c.get("alpn")

        if network == "ws":
            ws_opts = c.get("ws-opts") or {}
            ws_headers = ws_opts.get("headers") or {}
            stream["wsSettings"] = {
                "path": ws_opts.get("path", c.get("path", "")),
                "headers": {
                    "Host": ws_headers.get("Host", c.get("host", ""))
                }
            }

        return stream

    def _wait_for_port(self, timeout=1.2):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                self.last_error = self._read_error_output() or f"Xray 进程提前退出，退出码={self.proc.returncode}"
                return False
            try:
                with socket.create_connection(("127.0.0.1", self.listen_port), timeout=0.2):
                    return True
            except OSError:
                time.sleep(0.05)
        self.last_error = self._read_error_output() or f"本地 socks 端口 {self.listen_port} 未在超时内就绪"
        return False

    def _read_error_output(self):
        if not self.errfile or not os.path.exists(self.errfile):
            return ""
        try:
            with open(self.errfile, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            return self._summarize_output(text)
        except:
            return ""

    def _summarize_output(self, text, limit=1000):
        if not text:
            return ""
        lines = [line.strip() for line in str(text).splitlines() if line.strip()]
        if not lines:
            return ""
        summary = " || ".join(lines[-8:])
        if len(summary) > limit:
            summary = summary[:limit] + "..."
        return summary

    def _test_config(self):
        try:
            proc = subprocess.run(
                [self.xray, "run", "-test", "-c", self.cfg],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                creationflags=0x08000000
            )
            if proc.returncode == 0:
                return True

            output = self._summarize_output((proc.stderr or "") + "\n" + (proc.stdout or ""))
            self.last_error = (
                f"Xray 配置测试失败，退出码={proc.returncode} | {output}"
                if output else
                f"Xray 配置测试失败，退出码={proc.returncode}"
            )
            return False
        except Exception as e:
            self.last_error = f"Xray 配置测试异常: {type(e).__name__}: {e}"
            return False

    def generate_config(self, node, port):
        c = node.config
        protocol = node.type.lower()
        stream = self._build_stream_settings(c)

        out = None
        if protocol == "vmess":
            out = {
                "protocol": "vmess",
                "settings": {"vnext": [{
                    "address": c["server"],
                    "port": c["port"],
                    "users": [{
                        "id": c.get("uuid", ""),
                        "security": c.get("cipher", "auto"),
                        "alterId": c.get("alterId", 0)
                    }]
                }]},
                "streamSettings": stream
            }
        elif protocol == "vless":
            user = {
                "id": c.get("uuid", ""),
                "encryption": "none"
            }
            if c.get("flow"):
                user["flow"] = c.get("flow")
            out = {
                "protocol": "vless",
                "settings": {"vnext": [{
                    "address": c["server"],
                    "port": c["port"],
                    "users": [user]
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
            # Clash 用 cipher 字段，v2ray 用 method，两者兼容
            cipher = c.get("cipher") or c.get("method") or ""
            # Xray 支持的 SS 加密算法白名单
            _SS_SUPPORTED = {
                "aes-128-gcm", "aes-256-gcm",
                "chacha20-ietf-poly1305", "xchacha20-ietf-poly1305",
                "2022-blake3-aes-128-gcm", "2022-blake3-aes-256-gcm",
                "2022-blake3-chacha20-poly1305",
                "none", "plain"
            }
            if cipher not in _SS_SUPPORTED:
                self.last_error = f"不支持的 SS 加密算法: {cipher!r}"
                return None
            out = {
                "protocol": "shadowsocks",
                "settings": {"servers": [{
                    "address": c["server"],
                    "port": c["port"],
                    "method": cipher,
                    "password": c.get("password", "")
                }]}
            }

        if out is None:
            self.last_error = f"不支持的节点协议: {protocol!r}"
            return None

        config = {
            "log": {"loglevel": "warning"},
            "inbounds": [{"port": port, "listen": "127.0.0.1", "protocol": "socks", "settings": {"auth": "noauth"}}],
            "outbounds": [out]
        }

        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(path, "w") as f:
            json.dump(config, f)
        self.cfg = path
        self.listen_port = port
        return path  # 返回路径（之前也隐式可用）

    def start(self):
        if not self.cfg:
            # generate_config 返回 None 说明协议不支持，last_error 已设置
            return False
        try:
            if self.pretest and (not self._test_config()):
                return False

            errfd, self.errfile = tempfile.mkstemp(suffix=".log")
            os.close(errfd)
            err_handle = open(self.errfile, "w", encoding="utf-8", errors="ignore")
            self.proc = subprocess.Popen(
                [self.xray, "run", "-c", self.cfg],
                stdout=subprocess.DEVNULL,
                stderr=err_handle,
                creationflags=0x08000000
            )
            err_handle.close()
            if self.proc.poll() is not None:
                self.last_error = self._read_error_output() or f"Xray 进程启动后立即退出，退出码={self.proc.returncode}"
                return False
            return self._wait_for_port(timeout=self.port_wait_timeout)
        except Exception as e:
            self.last_error = f"{type(e).__name__}: {e}"
            return False

    def stop(self):
        try:
            self.proc.terminate()
        except:
            pass
        try:
            if self.proc is not None:
                self.proc.wait(timeout=1)
        except:
            pass
        try:
            os.unlink(self.cfg)
        except:
            pass
        try:
            if self.errfile:
                os.unlink(self.errfile)
        except:
            pass
        self.proc = None
        self.cfg = None
        self.listen_port = None
        self.errfile = None