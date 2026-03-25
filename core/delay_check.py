import aiohttp
import asyncio
import time
import datetime
import contextlib

class DelayChecker:
    def __init__(self, timeout=5, max_delay=1500, tcp_precheck=True, precheck_timeout=1.2, fast_mode=True):
        self.timeout = timeout
        self.max_delay = max_delay
        self.tcp_precheck = tcp_precheck
        self.precheck_timeout = precheck_timeout
        self.fast_mode = fast_mode
        self.logfile = "delay_check.log"
        self._init_log()
        self.test_urls = ["https://cp.cloudflare.com/generate_204"] if fast_mode else [
            "https://cp.cloudflare.com/generate_204",
            "https://www.gstatic.com/generate_204",
        ]

    async def _tcp_probe(self, host, port):
        """快速TCP连通预检：成功建立TCP即认为节点入口可达。"""
        writer = None
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(str(host), int(port)),
                timeout=self.precheck_timeout
            )
            return True, ""
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
        finally:
            if writer is not None:
                writer.close()
                with contextlib.suppress(Exception):
                    await writer.wait_closed()

    async def batch_tcp_precheck(self, nodes, max_thread=200):
        total = len(nodes)
        self._log(f"[TCP预检开始] 节点总数={total} | 并发={max_thread}")
        print(f"⏳ 开始TCP预检，共 {total} 个节点，并发 {max_thread}，每 10 秒刷新进度...")

        semaphore = asyncio.Semaphore(max_thread)
        completed = [0]
        passed = []
        failed = []

        async def limited_probe(node):
            async with semaphore:
                ok, reason = await self._tcp_probe(node.server, node.port)
            completed[0] += 1
            if ok:
                passed.append(node)
                self._log(f"[TCP预检] ✅ 通过 | {node.server}:{node.port} | {node.name}")
            else:
                failed.append(node)
                self._log(f"[TCP预检] ❌ 失败 | {node.server}:{node.port} | {node.name} | 原因: {reason}")

        async def progress_reporter():
            while True:
                await asyncio.sleep(10)
                done = completed[0]
                pct = done / total * 100 if total else 100
                print(f"⏳ TCP预检进度: {done}/{total}  {pct:.1f}%")

        progress_task = asyncio.create_task(progress_reporter())
        tasks = [asyncio.create_task(limited_probe(node)) for node in nodes]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self._log(f"[TCP预检取消] 已完成={completed[0]} | 总数={total}")
            raise
        finally:
            progress_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await progress_task

        print(f"✅ TCP预检完成: {completed[0]}/{total}  100.0%")
        self._log(
            f"[TCP预检完成] 总计={total} | 通过={len(passed)} | 不通过={len(failed)} | 通过率={len(passed)/total*100:.1f}%"
            if total else "[TCP预检完成] 总计=0 | 通过=0 | 不通过=0 | 通过率=0.0%"
        )
        return passed

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

    async def _check_node_inner(self, node, port, xray_holder):
        """实际检测逻辑，供 check_node 套超时用"""
        from core.xray_runner import XrayRunner
        xray = XrayRunner(
            pretest=(not self.fast_mode),
            port_wait_timeout=1.2 if self.fast_mode else 2.5,
        )
        xray_holder.append(xray)
        xray.generate_config(node, port)

        xray_ok = await asyncio.to_thread(xray.start)
        if not xray_ok:
            return False, False, 0, xray.last_error or "Xray启动失败"

        proxy = f"socks5://127.0.0.1:{port}"
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=None),
            timeout=aiohttp.ClientTimeout(total=self.timeout, connect=self.timeout, sock_connect=self.timeout)
        ) as session:
            try:
                async def _do_request(url):
                    async with session.get(
                        url,
                        proxy=proxy,
                        allow_redirects=False,
                    ) as resp:
                        return resp.status

                errors = []
                for url in self.test_urls:
                    try:
                        req_start = time.time()
                        status = await asyncio.wait_for(_do_request(url), timeout=self.timeout)
                        if status in (200, 204):
                            return True, True, round((time.time() - req_start) * 1000), ""
                        errors.append(f"{url} -> HTTP {status}")
                    except Exception as e:
                        errors.append(f"{url} -> {type(e).__name__}: {e}")

                return True, False, 0, " | ".join(errors[:2])

            except asyncio.TimeoutError:
                return True, False, 0, f"请求超时(限制={self.timeout}s)"
            except Exception as e:
                return True, False, 0, f"{type(e).__name__}: {e}"

    async def check_node(self, node, port):
        node_name = node.name
        t_start = datetime.datetime.now()
        start = time.time()

        result_ok   = False
        result_ms   = 0
        xray_ok     = False
        fail_reason = ""
        cancelled   = False
        xray_holder = []   # 用列表让 finally 能拿到 xray 实例

        total_timeout = self.timeout + (6 if self.fast_mode else 9)   # 快模式下收紧总超时
        try:
            if self.tcp_precheck:
                pre_ok, pre_reason = await self._tcp_probe(node.server, node.port)
                if not pre_ok:
                    fail_reason = f"TCP预检失败({node.server}:{node.port}) | {pre_reason}"
                    raise RuntimeError("TCP_PRECHECK_FAILED")

            xray_ok_inner, http_ok, ms_override, reason = await asyncio.wait_for(
                self._check_node_inner(node, port, xray_holder),
                timeout=total_timeout
            )
            xray_ok = xray_ok_inner
            if not xray_ok:
                fail_reason = reason
            elif http_ok:
                result_ms = ms_override if ms_override else round((time.time() - start) * 1000)
                node.delay = result_ms
                result_ok = True
            else:
                fail_reason = reason

        except asyncio.TimeoutError:
            fail_reason = f"整体超时(限制={total_timeout}s)"
            xray_ok = True   # 进程已起，但卡住了
        except RuntimeError as e:
            if str(e) != "TCP_PRECHECK_FAILED":
                fail_reason = f"RuntimeError: {e}"
        except asyncio.CancelledError:
            cancelled = True
            fail_reason = "任务已取消"
            if xray_holder and xray_holder[0].proc is not None:
                xray_ok = xray_holder[0].proc.poll() is None
            raise
        except Exception as e:
            fail_reason = f"{type(e).__name__}: {e}"

        finally:
            t_end = datetime.datetime.now()
            elapsed = round(time.time() - start, 3)
            if xray_holder:
                try:
                    xray_holder[0].stop()
                except Exception as e:
                    fail_reason = (fail_reason + f" | Xray停止异常:{type(e).__name__}").lstrip(" | ")

            if cancelled:
                status_str = "⏹ 已取消"
            else:
                status_str = "✅ 成功" if result_ok else "❌ 失败"
            xray_str   = "✅ 正常" if xray_ok   else "❌ 失败"
            ms_str     = f"{result_ms}ms" if result_ok else "—"
            reason_str = f" | 原因: {fail_reason}" if fail_reason else ""

            self._log(
                f"[{status_str}] "
                f"节点: {node_name} | "
                f"端口: {port} | "
                f"Xray启动: {xray_str} | "
                f"延迟: {ms_str} | "
                f"耗时: {elapsed}s | "
                f"开始: {t_start.strftime('%H:%M:%S.%f')[:-3]} | "
                f"结束: {t_end.strftime('%H:%M:%S.%f')[:-3]}"
                f"{reason_str}"
            )

        result_msg = f"✅ {result_ms}ms" if result_ok else fail_reason
        return node, result_ok, result_ms, result_msg

    async def batch_check(self, nodes, max_thread=30):
        base_port = 53000
        total = len(nodes)
        self._log(f"[批量开始] 节点总数={total} | 并发={max_thread} | 基础端口={base_port}")
        print(f"⏳ 开始测速，共 {total} 个节点，并发 {max_thread}，每 10 秒刷新进度...")

        if total == 0:
            self._log("[批量完成] 总计=0 | 可用=0 | 不可用=0 | 可用率=0.0%")
            print("✅ 测速完成: 0/0  100.0%")
            return []

        semaphore = asyncio.Semaphore(max_thread)
        completed = [0]  # 用列表以便闭包内修改

        async def limited_check(node, port):
            async with semaphore:
                result = await self.check_node(node, port)
            completed[0] += 1
            return result

        async def progress_reporter():
            while True:
                await asyncio.sleep(10)
                done = completed[0]
                pct = done / total * 100
                print(f"⏳ 进度: {done}/{total}  {pct:.1f}%")

        progress_task = asyncio.create_task(progress_reporter())

        tasks = [
            asyncio.create_task(limited_check(n, base_port + idx))
            for idx, n in enumerate(nodes)
        ]

        try:
            results = await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self._log(f"[批量取消] 已完成={completed[0]} | 总数={total}")
            raise
        finally:
            progress_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await progress_task

        print(f"✅ 测速完成: {completed[0]}/{total}  100.0%")

        available = []
        failed = []
        for node, ok, ms, msg in results:
            if ok:
                available.append(node)
                self._log(f"[结果] ✅ 可用 | {ms}ms | {node.name}")
            else:
                failed.append(node)
                self._log(f"[结果] ❌ 不可用 | {msg} | {node.name}")

        self._log(
            f"[批量完成] 总计={total} | 可用={len(available)} | "
            f"不可用={len(failed)} | "
            f"可用率={len(available)/total*100:.1f}%"
        )
        if available:
            delays = [n.delay for n in available if hasattr(n, 'delay') and n.delay]
            if delays:
                self._log(
                    f"[延迟统计] 最小={min(delays)}ms | 最大={max(delays)}ms | "
                    f"平均={sum(delays)//len(delays)}ms"
                )
        return available