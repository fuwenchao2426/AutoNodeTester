# AutoNodeTester

一个基于 `Xray + Python asyncio` 的节点批量检测工具，支持：

- 订阅并发拉取（带镜像自救）
- Clash 节点解析与去重
- 高并发 TCP 预检
- 真延时测速（通过本地 Xray SOCKS 出口）
- 结果导出为 Clash YAML 和 v2rayN 链接
- 每次订阅原文快照归档，便于后续对比


```log
==================================================
    全自动节点检测工具 正式主线版
==================================================
✅ Xray 就绪

[1/4] 拉取订阅...

[自救] 自动测试可用镜像...
[自救] ✅ 可用镜像：https://download.serein.cc/
[保存] 订阅快照 → cache\subscriptions\20260325_150822
✅ 拉取成功：46/48

[2/4] 解析去重...
✅ 去重完成：8677 个
[保存] 去重Clash → cache\unique\unique_nodes.yaml
[保存] V2RayN → cache\unique/unique_v2rayn.txt

[3/5] 高并发TCP预检...

⏳ 开始TCP预检，共 8677 个节点，并发 300，每 10 秒刷新进度...
⏳ TCP预检进度: 1908/8677  22.0%
⏳ TCP预检进度: 3569/8677  41.1%
⏳ TCP预检进度: 5845/8677  67.4%
⏳ TCP预检进度: 8324/8677  95.9%
✅ TCP预检完成: 8677/8677  100.0%

🎯 预检通过节点：2243 个

[4/5] 保存预检结果...
[保存] 预检通过Clash → cache\precheck\precheck_available_nodes.yaml
[保存] V2RayN → cache\precheck\precheck_available_v2rayn.txt

[5/5] 多线程延迟测速...

⏳ 开始测速，共 2243 个节点，并发 30，每 10 秒刷新进度...
⏳ 进度: 106/2243  4.7%
⏳ 进度: 185/2243  8.2%
⏳ 进度: 247/2243  11.0%
⏳ 进度: 310/2243  13.8%
⏳ 进度: 377/2243  16.8%
⏳ 进度: 449/2243  20.0%
⏳ 进度: 600/2243  26.7%
⏳ 进度: 659/2243  29.4%
⏳ 进度: 722/2243  32.2%
⏳ 进度: 774/2243  34.5%
⏳ 进度: 827/2243  36.9%
⏳ 进度: 877/2243  39.1%
⏳ 进度: 930/2243  41.5%
⏳ 进度: 962/2243  42.9%
⏳ 进度: 1025/2243  45.7%
⏳ 进度: 1081/2243  48.2%
⏳ 进度: 1145/2243  51.0%
⏳ 进度: 1201/2243  53.5%
⏳ 进度: 1267/2243  56.5%
⏳ 进度: 1327/2243  59.2%
⏳ 进度: 1393/2243  62.1%
⏳ 进度: 1477/2243  65.8%
⏳ 进度: 1576/2243  70.3%
⏳ 进度: 1664/2243  74.2%
⏳ 进度: 1759/2243  78.4%
⏳ 进度: 1866/2243  83.2%
⏳ 进度: 1961/2243  87.4%
⏳ 进度: 2061/2243  91.9%
⏳ 进度: 2118/2243  94.4%
⏳ 进度: 2194/2243  97.8%
✅ 测速完成: 2243/2243  100.0%

🎉 可用节点：23 个

[补充保存] 真延时结果...
[保存] 可用Clash → cache\delay\delay_available_nodes.yaml
[保存] V2RayN → cache\delay\delay_available_v2rayn.txt

✅ 全部完成！
```


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
