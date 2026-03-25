import asyncio
import os
import platform
from core.config_loader import ConfigLoader
from core.subscription import SubscriptionFetcher
from core.node_parser import NodeParser
from core.saver import NodeSaver
from core.delay_check import DelayChecker

async def clean_xray():
    try:
        if platform.system() == "Windows":
            os.system("taskkill /f /im xray.exe >nul 2>&1")
        await asyncio.sleep(0.2)
    except:
        pass

async def main():
    print("=" * 50)
    print("    全自动节点检测工具 正式主线版")
    print("=" * 50)

    await clean_xray()

    if not os.path.exists("xray.exe"):
        print("❌ 请放入 xray.exe")
        return

    print("✅ Xray 就绪")
    cfg = ConfigLoader()
    main_cfg = cfg.get_main()
    subs = cfg.subscriptions()
    fallbacks = cfg.fallback_proxies()

    print("\n[1/4] 拉取订阅...")
    fetcher = SubscriptionFetcher(fallbacks)
    contents = await fetcher.fetch_all(subs)

    print("\n[2/4] 解析去重...")
    parser = NodeParser()
    nodes = parser.deduplicate(parser.parse_all(contents))
    print(f"✅ 去重完成：{len(nodes)} 个")

    print("\n[3/4] 多线程延迟测速...\n")
    checker = DelayChecker(timeout=5)
    available = await checker.batch_check(nodes, max_thread=20)

    print(f"\n🎉 可用节点：{len(available)} 个")

    print("\n[4/4] 保存...")
    saver = NodeSaver()
    saver.save_delay_available(available)

    print("\n✅ 全部完成！")
    await clean_xray()

if __name__ == "__main__":
    asyncio.run(main())