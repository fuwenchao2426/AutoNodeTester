# AutoNodeTester

一个基于 `Xray + Python asyncio` 的节点批量检测工具，支持：

- 订阅并发拉取（带镜像自救）
- Clash 节点解析与去重
- 高并发 TCP 预检
- 真延时测速（通过本地 Xray SOCKS 出口）
- 结果导出为 Clash YAML 和 v2rayN 链接
- 每次订阅原文快照归档，便于后续对比

---

## 1. 环境要求

- Windows（当前项目已在 Windows 下使用）
- Python 3.10+
- `xray.exe`（放在项目根目录）

依赖见 [requirements.txt](requirements.txt)。

---

## 2. 快速开始

1) 安装依赖

```bash
pip install -r requirements.txt
```

2) 准备配置

- 主配置：[config/config.yaml](config/config.yaml)
- 订阅列表：[config/list/subscriptions.txt](config/list/subscriptions.txt)
- 备用镜像：[config/list/fallback_proxies.txt](config/list/fallback_proxies.txt)

3) 放置 `xray.exe` 到项目根目录

4) 运行

```bash
python main.py
```

---

## 3. 主流程说明

入口文件：[main.py](main.py)

默认流程：

1. 拉取订阅并保存快照
2. 解析并去重
3. 高并发 TCP 预检
4. 保存预检通过结果
5. 对预检通过节点进行真延时测速
6. 保存真延时可用结果

你可以在 [main.py](main.py) 中调整：

- `USE_CACHED_NODES`：是否直接从缓存去重结果开始
- `PRECHECK_MAX_THREAD`：TCP 预检并发
- `DELAY_MAX_THREAD`：真延时测速并发

---

## 4. 输出目录

所有输出位于 [cache](cache) 下，按阶段分目录保存：

### 4.1 去重结果

- [cache/unique/unique_nodes.yaml](cache/unique/unique_nodes.yaml)
- [cache/unique/unique_v2rayn.txt](cache/unique/unique_v2rayn.txt)

### 4.2 TCP 预检通过结果

- [cache/precheck/precheck_available_nodes.yaml](cache/precheck/precheck_available_nodes.yaml)
- [cache/precheck/precheck_available_v2rayn.txt](cache/precheck/precheck_available_v2rayn.txt)

### 4.3 真延时可用结果

- [cache/delay/delay_available_nodes.yaml](cache/delay/delay_available_nodes.yaml)
- [cache/delay/delay_available_v2rayn.txt](cache/delay/delay_available_v2rayn.txt)

### 4.4 订阅快照（用于对比）

- [cache/subscriptions](cache/subscriptions) 下按时间戳分目录
- 每次拉取会生成：
  - 多个原始订阅文件（成功/失败）
  - `index.yaml`（记录源 URL、目标 URL、状态、错误、文件名映射）

### 4.5 运行日志

- [delay_check.log](delay_check.log)

---

## 5. 项目结构（核心）

- [main.py](main.py)：主流程编排
- [core/subscription.py](core/subscription.py)：订阅拉取与镜像自救
- [core/node_parser.py](core/node_parser.py)：节点解析与去重
- [core/delay_check.py](core/delay_check.py)：预检与延时检测
- [core/xray_runner.py](core/xray_runner.py)：Xray 配置生成与进程控制
- [core/saver.py](core/saver.py)：结果保存与 v2rayN 导出
- [core/config_loader.py](core/config_loader.py)：配置与列表加载

---

## 6. 说明

本项目仅用于网络连通性测试与研究，请在合法合规范围内使用。
