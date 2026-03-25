import asyncio
import os
import platform
from core.config_loader import ConfigLoader
from core.subscription import SubscriptionFetcher
from core.node_parser import NodeParser, Node
from core.saver import NodeSaver
from core.delay_check import DelayChecker

# ── 临时调试开关：True = 跳过拉取订阅，直接从 cache/unique_nodes.yaml 加载 ──
USE_CACHED_NODES = False
PRECHECK_MAX_THREAD = 300
DELAY_MAX_THREAD = 30

async def clean_xray():
    try:
        if platform.system() == "Windows":
            os.system("taskkill /f /im xray.exe >nul 2>&1")
        await asyncio.sleep(0.2)
    except:
        pass

def load_from_cache(path="cache/unique/unique_nodes.yaml"):
    """从缓存 YAML 直接重建 Node 列表，无需重新拉取订阅。"""
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    nodes = []
    for p in data.get("proxies", []):
        name   = p.get("name", "Unknown")
        ntype  = p.get("type", "unknown")
        server = p.get("server", "")
        port   = p.get("port", 0)
        if server and port:
            nodes.append(Node(name, ntype, server, port, p))
    return nodes

async def main():
    print("=" * 50)
    print("    全自动节点检测工具 正式主线版")
    print("=" * 50)

    await clean_xray()

    if not os.path.exists("xray.exe"):
        print("❌ 请放入 xray.exe")
        return

    print("✅ Xray 就绪")
    saver = NodeSaver()

    cache_unique_new = "cache/unique/unique_nodes.yaml"
    cache_unique_old = "cache/unique_nodes.yaml"
    if USE_CACHED_NODES and (os.path.exists(cache_unique_new) or os.path.exists(cache_unique_old)):
        print("\n[跳过 1-2/4] 使用缓存去重节点...")
        nodes = load_from_cache(cache_unique_new if os.path.exists(cache_unique_new) else cache_unique_old)
        print(f"✅ 从缓存加载：{len(nodes)} 个")
    else:
        cfg = ConfigLoader()
        main_cfg = cfg.get_main()
        subs = cfg.subscriptions()
        fallbacks = cfg.fallback_proxies()

        print("\n[1/4] 拉取订阅...")
        fetcher = SubscriptionFetcher(fallbacks)
        records = await fetcher.fetch_all(subs)
        saver.save_subscription_snapshot(records)
        contents = [r["content"] for r in records if r.get("ok") and r.get("content")]
        print(f"✅ 拉取成功：{len(contents)}/{len(records)}")

        print("\n[2/4] 解析去重...")
        parser = NodeParser()
        nodes = parser.deduplicate(parser.parse_all(contents))
        print(f"✅ 去重完成：{len(nodes)} 个")

        saver.save_unique_nodes(nodes)
        saver.save_v2rayn_format(nodes, "unique/unique_v2rayn.txt")

    checker = DelayChecker(timeout=6, tcp_precheck=True, precheck_timeout=1.8, fast_mode=True)

    print("\n[3/5] 高并发TCP预检...\n")
    prechecked_nodes = await checker.batch_tcp_precheck(nodes, max_thread=PRECHECK_MAX_THREAD)
    print(f"\n🎯 预检通过节点：{len(prechecked_nodes)} 个")

    print("\n[4/5] 保存预检结果...")
    saver.save_named_nodes(prechecked_nodes, "precheck_available_nodes.yaml", "precheck_available_v2rayn.txt", "预检通过", subdir="precheck")

    print("\n[5/5] 多线程延迟测速...\n")
    checker.tcp_precheck = False
    if prechecked_nodes:
        available = await checker.batch_check(prechecked_nodes, max_thread=DELAY_MAX_THREAD)
    else:
        print("⚠️ 预检后无可测速节点，跳过真延时测速")
        available = []

    print(f"\n🎉 可用节点：{len(available)} 个")

    print("\n[补充保存] 真延时结果...")
    saver.save_delay_available(available)

    print("\n✅ 全部完成！")
    await clean_xray()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹ 已手动停止测速")