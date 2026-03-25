import time
import subprocess
import os
import json
import tempfile
from urllib.parse import urlparse, parse_qs

# ===================== 你的固定配置 =====================
NODE_FILE = r"C:\Users\Administrator\Desktop\测速\cache\unique_v2rayn.txt"
XRAY_PATH = r"C:\Users\Administrator\Desktop\测速\xray.exe"
TEST_URL = "https://www.gstatic.com/generate_204"
OUTPUT_FILE = r"C:\Users\Administrator\Desktop\可用节点.txt"
TEST_DELAY = 1
TEST_TIMEOUT = 8
SOCKS_PORT = 10809
# ======================================================

def parse_trojan_full(link):
    try:
        u = urlparse(link)
        query = parse_qs(u.query)
        return {
            "protocol": "trojan",
            "password": u.username,
            "address": u.hostname,
            "port": u.port,
            "sni": query.get("sni", [u.hostname])[0],
            "allowInsecure": query.get("allowInsecure", ["0"])[0] == "1"
        }
    except:
        return None

def make_xray_config(node):
    return {
        "log": {"loglevel": "none"},
        "inbounds": [{
            "port": SOCKS_PORT,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {"auth": "noauth"}
        }],
        "outbounds": [{
            "protocol": "trojan",
            "settings": {
                "servers": [{
                    "address": node["address"],
                    "port": node["port"],
                    "password": node["password"],
                    "tls": {
                        "serverName": node["sni"],
                        "allowInsecure": node["allowInsecure"]
                    }
                }]
            },
            "streamSettings": {"security": "tls"}
        }]
    }

def test_one_node(node_line, idx, total):
    print(f"\n=== 测试第 {idx}/{total} 个节点 ===")
    print(f"节点: {node_line[:70]}...")

    node = parse_trojan_full(node_line)
    if not node:
        print("❌ 解析失败")
        return False, 0

    cfg = make_xray_config(node)
    cfg_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(cfg, cfg_file)
    cfg_file.close()
    cfg_path = cfg_file.name

    xray_proc = None
    try:
        xray_proc = subprocess.Popen(
            [XRAY_PATH, "run", "-c", cfg_path],
            creationflags=0x08000000,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2)

        # 最简最稳写法，所有 curl 都支持，无报错
        cmd = [
            "curl", "-s", "-m", str(TEST_TIMEOUT),
            "--socks5-hostname", "127.0.0.1:10809",
            "-w", "%{http_code} %{time_total}",
            TEST_URL, "-o", "NUL"
        ]
        
        res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        output = res.stdout.strip()
        
        try:
            http_code, time_total = output.split()
            ms = round(float(time_total) * 1000)
        except:
            http_code = "000"
            ms = 0

        print(f"HTTP 状态: {http_code}")
        print(f"延迟: {ms} ms")

        if http_code == "204":
            print("✅ 节点可用！")
            return True, ms
        else:
            print("❌ 不可用")
            return False, ms

    finally:
        try:
            xray_proc.terminate()
            xray_proc.kill()
        except:
            pass
        os.unlink(cfg_path)

def main():
    print("=" * 60)
    print("              ✅ Xray 测速最终版（无报错）")
    print("=" * 60)

    with open(NODE_FILE, "r", encoding="utf-8") as f:
        nodes = [l.strip() for l in f if l.strip()]

    valid_nodes = []
    total = len(nodes)
    
    for i, line in enumerate(nodes, 1):
        ok, ms = test_one_node(line, i, total)
        if ok:
            valid_nodes.append(line)
        time.sleep(TEST_DELAY)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(valid_nodes))

    print("\n" + "="*60)
    print(f"🎉 测试完成！可用：{len(valid_nodes)}/{total}")
    print(f"📁 可用节点已保存到桌面！")
    print("="*60)
    input("按回车退出...")

if __name__ == "__main__":
    main()