import aiohttp
import asyncio
import time
import datetime

class DelayChecker:
    def __init__(self, timeout=5, max_delay=1500):
        self.timeout = timeout
        self.max_delay = max_delay
        self.logfile = "delay_check.log"
        self._init_log()

    def _init_log(self):
        with open(self.logfile, "w", encoding="utf-8") as f:
            f.write(f"=== 延迟检测日志 | {datetime.datetime.now()} ===\n")

    def _log(self, msg):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        try:
            with open(self.logfile, "a", encoding="utf-8") as f:
                f.write(f"[{now}] {msg}\n")
                f.flush()
        except:
            pass

    async def check_node(self, node, port):
        node_name = node.name[:30]
        start = time.time()
        self._log(f"开始 | 端口={port} | {node_name}")

        try:
            from core.xray_runner import XrayRunner
            xray = XrayRunner()
            xray.generate_config(node, port)

            # --------------------------
            # 🔥 核心修复：丢到线程池！
            # --------------------------
            ok = await asyncio.to_thread(xray.start)
            
            if not ok:
                self._log(f"Xray 启动失败 | {node_name}")
                return node, False, 0, "❌ Xray启动失败"

            proxy = f"socks5://127.0.0.1:{port}"
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False, limit=None),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                try:
                    async with session.get(
                        "https://www.gstatic.com/generate_204",
                        proxy=proxy
                    ) as resp:
                        ms = round((time.time() - start) * 1000)
                        if resp.status == 204:
                            node.delay = ms
                            self._log(f"✅ 成功 | {ms}ms | {node_name}")
                            return node, True, ms, f"✅ {ms}ms"
                        else:
                            self._log(f"❌ 状态错误 | {node_name}")
                            return node, False, 0, "❌ 状态错误"

                except asyncio.TimeoutError:
                    self._log(f"⏱ 超时 | {node_name}")
                    return node, False, 0, "⏱ 超时"
                except Exception as e:
                    self._log(f"🔌 连接失败 | {node_name}")
                    return node, False, 0, "🔌 连接失败"

        except Exception as e:
            self._log(f"⚠️ 异常 | {node_name}")
            return node, False, 0, "⚠️ 异常"

        finally:
            try:
                await asyncio.to_thread(xray.stop)
            except:
                pass
            self._log(f"结束 | {node_name}")

    async def batch_check(self, nodes, max_thread=30):
        base_port = 53000
        self._log(f"真·异步并发开始 | 并发={max_thread}")
        print(f"🚀 真·异步测速 | 并发 {max_thread}\n")

        tasks = []
        for idx, n in enumerate(nodes):
            task = asyncio.create_task(
                self.check_node(n, base_port + idx)
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        available = []
        for node, ok, ms, msg in results:
            if ok:
                available.append(node)
            print(f"{msg} | {node.name[:30]}")

        self._log(f"完成 | 可用={len(available)}")
        return available