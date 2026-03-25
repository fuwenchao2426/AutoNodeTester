import base64
import yaml
import json
from typing import List, Dict

# 节点结构
class Node:
    def __init__(self, name: str, type: str, server: str, port: int, config: Dict):
        self.name = name
        self.type = type
        self.server = server
        self.port = port
        self.config = config  # 完整配置
        self.delay = None
        self.country = None
        self.speed = None
        self.grade = None
        self.unlock = {}  # 网站解锁状态

    # 去重唯一标识
    def unique_key(self):
        return f"{self.type}://{self.server}:{self.port}"

class NodeParser:
    def __init__(self):
        self.nodes: List[Node] = []

    # 解析 Clash/Clash Meta YAML 订阅
    def parse_clash_yaml(self, content: str) -> List[Node]:
        try:
            data = yaml.safe_load(content)
            proxies = data.get("proxies", [])
            nodes = []
            for p in proxies:
                name = p.get("name", "Unknown")
                type = p.get("type", "unknown")
                server = p.get("server", "")
                port = p.get("port", 0)
                if not server or port == 0:
                    continue
                nodes.append(Node(name, type, server, port, p))
            return nodes
        except:
            return []

    # 批量解析所有订阅内容
    def parse_all(self, contents: List[str]) -> List[Node]:
        nodes = []
        for c in contents:
            nodes += self.parse_clash_yaml(c)
        self.nodes = nodes
        return nodes

    # 去重
    def deduplicate(self, nodes: List[Node]) -> List[Node]:
        unique = {}
        for n in nodes:
            key = n.unique_key()
            if key not in unique:
                unique[key] = n
        return list(unique.values())