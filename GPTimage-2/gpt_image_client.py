"""
gpt-image-2 / gpt-image-2.5 图片生成客户端
=============================================
基于中转站 rtoc.cc 的 image-generation 端点协议

文档来源:文档.md (GPT Image 2 图片接口)

端点:
  - 文生图:        POST /v1/images/generations  (application/json)
  - 图生图/编辑:   POST /v1/images/edits         (multipart/form-data)

注意事项:
  1. 资源组里可用的图片模型(2026-09 实测):
       - gpt-image-2            ✅ 可用,~87s/张(1024x1024/low)
       - gpt-image-2.5          ❌ 503 No available compatible accounts(渠道缺货)
       - gpt-image-2.5-flare    ✅ 可用,~48s/张(实测比 2 还快,推测更便宜)
       - gpt-image-2.5-sunburst (列表可见,未实测)
       建议先 client.list_models() 看一下当前可用列表。
  2. gpt-image-2 不要发到 /v1/chat/completions。
  3. 客户端超时建议至少 180 秒(实测 1024x1024/low 质量约 48~87 秒;复杂请求可能接近 2 分钟)。
  4. size 约束:两条边都必须是 16 的倍数;最长边不超过 3840;
               长短边比例不超过 3:1;总像素 655,360 ~ 8,294,400。
  5. gpt-image-2 不支持 background=transparent;也不接受 input_fidelity 字段。
  6. 多张参考图时,image[] 字段重复传入同名字段。
"""

import os
import base64
import json
import sys
import re
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union, Dict, Any, Iterable, Callable, TypeVar

import requests

# 优先从项目根目录的 .env 加载,失败则用系统环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()  # 自动找当前工作目录或父目录的 .env
except ImportError:
    def load_dotenv(*args, **kwargs):  # type: ignore
        return False


T = TypeVar("T")


# ANSI 颜色(Windows 10+ / Windows Terminal / PowerShell 7+ 默认支持)
_ANSI = {
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "dim":    "\033[90m",
    "cyan":   "\033[36m",
    "green":  "\033[32m",
    "yellow": "\033[33m",
    "red":    "\033[31m",
}


def _now_str() -> str:
    """返回当前墙钟时间,精确到毫秒 (HH:MM:SS.mmm)"""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _call_with_progress(label: str, func: Callable[..., T], *args, **kwargs) -> T:
    """
    带可视化计时效果的同步函数调用。生图是阻塞式 requests.post(),会让人
    误以为卡死了,所以:

      - 后台线程跑 func,把结果/异常塞进 holder dict
      - 主线程每 500ms 打印一行新内容(不是同行刷新)
        显示:spinner 字符 | 当前墙钟时间(毫秒精度) | 已等待时长(ms)
      - 完成后单独打印一行总耗时

    为什么**每 500ms 打印新行**而不是同行 `\r` 刷新:
      - 某些 Windows 旧版 cmd 不支持 ANSI `\r` 覆盖(光标控制)
      - 用户复制终端日志时,`\r` 同行刷新会被折叠掉,误以为没运行
      - 每行新打印在任何终端、任何 stdout 捕获场景下都稳定可见
    """
    result_holder: Dict[str, Any] = {}
    error_holder: Dict[str, Any] = {}

    def runner():
        try:
            result_holder["result"] = func(*args, **kwargs)
        except BaseException as e:  # noqa: BLE001  转发一切异常到主线程
            error_holder["error"] = e

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()

    start_perf = time.perf_counter()  # 单调时钟,用于精确计时

    # 终端宽度:进度条宽度自适应,最少 30、最多 50
    try:
        term_width = shutil.get_terminal_size().columns
    except Exception:
        term_width = 80
    bar_width = max(30, min(50, term_width // 3))

    # 起始:任务标签(单行)
    print(f"\n⏳  {_ANSI['bold']}{label}{_ANSI['reset']}", flush=True)

    spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    tick = 0

    try:
        while thread.is_alive():
            elapsed_ms = (time.perf_counter() - start_perf) * 1000
            elapsed_s = elapsed_ms / 1000

            spin_char = spinner[tick % len(spinner)]
            # 进度条:每秒填 2 格,封顶 bar_width(30 格的进度条约 15 秒填满,
            # 适合生图 50-90 秒的场景)
            filled = min(bar_width, int(elapsed_s * 2))
            bar = "█" * filled + "░" * (bar_width - filled)

            # 单行 \r 刷新:spinner + 时间 + 进度条
            line = (
                f"\r{_ANSI['cyan']}{spin_char}{_ANSI['reset']}  "
                f"+{_ANSI['bold']}{elapsed_s:5.1f}s{_ANSI['reset']}  "
                f"{_ANSI['cyan']}[{bar}]{_ANSI['reset']}"
            )
            sys.stdout.write(line)
            sys.stdout.flush()

            time.sleep(0.1)
            tick += 1
    except KeyboardInterrupt:
        # 用户 Ctrl+C:等当前 IO 跑完再退出
        thread.join()
        raise

    thread.join()

    # 完成:换行后打印总结(绿色 ✓ + 总耗时)
    total_ms = (time.perf_counter() - start_perf) * 1000
    total_s = total_ms / 1000
    final_bar = "█" * bar_width  # 完成时进度条全满
    sys.stdout.write(
        f"\r{_ANSI['green']}✓{_ANSI['reset']}  "
        f"{_ANSI['bold']}{_ANSI['green']}完成!{_ANSI['reset']}  "
        f"总耗时 {_ANSI['bold']}{total_s:.3f}s{_ANSI['reset']}  "
        f"{_ANSI['dim']}({int(total_ms)} ms){_ANSI['reset']}  "
        f"{_ANSI['cyan']}[{final_bar}]{_ANSI['reset']}\n"
    )
    sys.stdout.flush()

    if error_holder:
        raise error_holder["error"]
    return result_holder["result"]


BASE_URL = "https://api.rtoc.cc"
DEFAULT_TIMEOUT = 180  # 秒,文档建议至少 180

# ---------------------------------------------------------------------------
# 常用尺寸 / 分辨率预设(文档中给出的合法值)
# ---------------------------------------------------------------------------
# size 约束:两边都是 16 的倍数、最长边 ≤3840、长短边比例 ≤3:1、总像素 655360~8294400
SIZE_PRESETS: Dict[str, str] = {
    "1024x1024 (1:1 方形)":   "1024x1024",
    "1536x1024 (3:2 横版)":   "1536x1024",
    "1024x1536 (2:3 竖版)":   "1024x1536",
    "2048x1152 (16:9 横版)":  "2048x1152",
    "1152x2048 (9:16 竖版)":  "1152x2048",
    "2048x2048 (2K 方形)":    "2048x2048",
    "3840x2160 (4K 横版)":    "3840x2160",
    "2160x3840 (4K 竖版)":    "2160x3840",
}

QUALITY_PRESETS: List[str] = ["low", "medium", "high", "auto"]

FORMAT_PRESETS: List[str] = ["png", "jpeg", "webp"]

# 兼容的参考图后缀
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------
class GPTImageError(RuntimeError):
    """调用 gpt-image 接口失败时抛出"""

    def __init__(self, message: str, status_code: Optional[int] = None,
                 payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


# ---------------------------------------------------------------------------
# 客户端
# ---------------------------------------------------------------------------
class GPTImageClient:
    """
    gpt-image-2 / gpt-image-2.5 客户端封装。

    用法:
        client = GPTImageClient(api_key="sk-xxx")
        images = client.text_to_image(model="gpt-image-2",
                                      prompt="一只橘猫在窗台晒太阳")
        client.save(images[0], "cat.png")

        # 图生图
        images = client.image_to_image(
            model="gpt-image-2",
            prompt="把背景换成海滩日落",
            image_paths=["cat.png"],
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key or os.environ.get("RTOC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "需要 API Key。可直接传入 api_key='sk-xxx',"
                " 或设置环境变量 RTOC_API_KEY。"
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.api_key}"

    # --------------------------- 文生图 ----------------------------------
    def text_to_image(
        self,
        prompt: str,
        model: str = "gpt-image-2",
        size: str = "1024x1024",
        quality: str = "medium",
        output_format: str = "png",
        n: int = 1,
        show_progress: bool = True,
    ) -> List[bytes]:
        """
        文生图。

        参数:
            prompt:         提示词(必填)
            model:          模型名,默认 gpt-image-2
            size:           1024x1024 / 1536x1024 / 1024x1536 / 2048x2048 /
                            2048x1152 / 3840x2160 / 2160x3840,或 "auto"
            quality:        low / medium / high / auto
            output_format:  png / jpeg / webp
            n:              返回图片数量(默认 1)
            show_progress:  是否在终端显示 spinner 进度条(默认 True)

        返回:
            List[bytes]:每张图片的二进制内容(已按 output_format 解码)
        """
        url = f"{self.base_url}/v1/images/generations"
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "output_format": output_format,
            "n": n,
        }

        def _do_request() -> List[bytes]:
            resp = self.session.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
            data = self._parse_json_response(resp)
            return self._extract_images(data, output_format)

        if show_progress:
            label = f"🖼️  {model} 文生图 ({size}, {quality})"
            return _call_with_progress(label, _do_request)
        return _do_request()

    # --------------------------- 图生图 / 编辑 / 遮罩 ---------------------
    def image_to_image(
        self,
        prompt: str,
        image_paths: List[Union[str, Path]],
        model: str = "gpt-image-2",
        mask_path: Optional[Union[str, Path]] = None,
        size: str = "1024x1024",
        quality: str = "medium",
        output_format: str = "png",
        n: int = 1,
        show_progress: bool = True,
    ) -> List[bytes]:
        """
        图生图 / 参考图编辑 / 遮罩编辑。

        参数:
            prompt:         提示词(必填)
            image_paths:    本地图片路径列表;多张参考图时按顺序传。
                            字段名固定为 image[],多图时重复同名字段。
            mask_path:      可选 PNG 遮罩;需与第一张参考图同格式、同尺寸、
                            含 alpha 通道、< 50MB。
            model/size/quality/output_format/n: 同 text_to_image
            show_progress:  是否在终端显示 spinner 进度条(默认 True)

        返回:
            List[bytes]:每张图片的二进制内容
        """
        if not image_paths:
            raise ValueError("image_paths 至少包含一张")

        url = f"{self.base_url}/v1/images/edits"

        # 准备 multipart/form-data 的 data 和 files
        form_data = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "output_format": output_format,
            "n": str(n),
        }

        def _do_request() -> List[bytes]:
            files: list = []
            opened_files: list = []
            try:
                for img_path in image_paths:
                    p = Path(img_path)
                    if not p.exists():
                        raise FileNotFoundError(f"参考图不存在: {p}")
                    mime = self._guess_mime(p)
                    fh = open(p, "rb")
                    opened_files.append(fh)
                    files.append(("image[]", (p.name, fh, mime)))

                if mask_path:
                    mp = Path(mask_path)
                    if not mp.exists():
                        raise FileNotFoundError(f"遮罩图不存在: {mp}")
                    m_f = open(mp, "rb")
                    opened_files.append(m_f)
                    files.append(("mask", (mp.name, m_f, "image/png")))

                resp = self.session.post(
                    url,
                    data=form_data,
                    files=files,
                    timeout=self.timeout,
                )
            finally:
                for fh in opened_files:
                    try:
                        fh.close()
                    except Exception:
                        pass

            data = self._parse_json_response(resp)
            return self._extract_images(data, output_format)

        if show_progress:
            extra = f", {len(image_paths)} 张参考图" + (" + mask" if mask_path else "")
            label = f"🖼️  {model} 图生图 ({size}, {quality}{extra})"
            return _call_with_progress(label, _do_request)
        return _do_request()

    # --------------------------- 模型列表查询 -----------------------------
    def list_models(self) -> Dict[str, Any]:
        """方便确认 gpt-image-2.5 是否在可用模型中"""
        url = f"{self.base_url}/v1/models"
        resp = self.session.get(url, timeout=self.timeout)
        return self._parse_json_response(resp)

    # --------------------------- 工具方法 ---------------------------------
    @staticmethod
    def generate_filename(
        mode: str = "img",
        model: str = "unknown",
        size: str = "1024x1024",
        quality: str = "medium",
        ext: str = "png",
        index: int = 0,
        when: Optional["datetime"] = None,
    ) -> str:
        """
        生成带时间戳的文件名,毫秒精度,绝不重复。

        命名格式:
            {mode}_{YYYYMMDD_HHMMSS}_{ms}_{model}_{size}_{quality}[_{idx}].{ext}

        例:
            t2i_20260909_202110_587_gpt-image-2.5-flare_1024x1024_medium.png
            i2i_20260909_202111_123_gpt-image-2_2048x1152_high_2.png   ← 第 2 张

        参数:
            mode:  t2i (text-to-image) / i2i (image-to-image) / 任意字符串
            model: 模型名,会自动清理非法字符
            size:  1024x1024 等
            quality: low / medium / high / auto
            ext:   png / jpeg / webp
            index: 同批次内的第几张(从 0 开始)。只有 >=1 时才追加 _N 后缀。
            when:  自定义时间,默认当前时刻(测试用)。
        """
        ts = when or datetime.now()
        date_part = ts.strftime("%Y%m%d_%H%M%S")
        ms_part = f"{ts.microsecond // 1000:03d}"  # 微秒取前 3 位 = 毫秒
        # 模型名安全化:把路径分隔符和 Windows 不允许的字符替换成 -
        safe_model = re.sub(r"[<>:\"/\\|?*\s]", "-", model) if model else "unknown"
        safe_model = re.sub(r"-+", "-", safe_model).strip("-") or "unknown"
        idx_suffix = f"_{index + 1}" if index > 0 else ""
        return f"{mode}_{date_part}_{ms_part}_{safe_model}_{size}_{quality}{idx_suffix}.{ext}"

    @staticmethod
    def save(image_bytes: bytes, path: Union[str, Path]) -> Path:
        """保存图片到本地"""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(image_bytes)
        return p

    @staticmethod
    def list_local_images(directory: Union[str, Path],
                          exts: Optional[Iterable[str]] = None) -> List[Path]:
        """
        扫描目录,返回所有图片路径(按文件名排序,过滤子目录)。
        默认识别 .png / .jpg / .jpeg / .webp / .gif。
        """
        d = Path(directory)
        if not d.exists():
            return []
        allowed = set(exts) if exts else IMAGE_EXTS
        return sorted(
            p for p in d.iterdir()
            if p.is_file() and p.suffix.lower() in allowed
        )

    @staticmethod
    def save_b64(b64_str: str, path: Union[str, Path]) -> Path:
        """保存 base64 字符串到本地"""
        img_bytes = base64.b64decode(b64_str)
        return GPTImageClient.save(img_bytes, path)

    # --------------------------- 内部辅助 ---------------------------------
    @staticmethod
    def _guess_mime(p: Path) -> str:
        suffix = p.suffix.lower()
        return {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(suffix, "application/octet-stream")

    def _parse_json_response(self, resp: requests.Response) -> Dict[str, Any]:
        if resp.status_code >= 400:
            try:
                payload = resp.json()
            except Exception:
                payload = {"raw": resp.text}
            raise GPTImageError(
                f"接口返回 {resp.status_code}: {payload}",
                status_code=resp.status_code,
                payload=payload,
            )
        try:
            return resp.json()
        except json.JSONDecodeError as e:
            raise GPTImageError(f"返回内容不是 JSON: {resp.text[:200]}") from e

    @staticmethod
    def _extract_images(data: Dict[str, Any], output_format: str) -> List[bytes]:
        items = data.get("data") or []
        if not items:
            raise GPTImageError(f"返回中没有 data 字段: {data}")
        ext = (output_format or "png").lower()
        results: List[bytes] = []
        for item in items:
            # 优先 b64_json,否则 url
            b64 = item.get("b64_json")
            if b64:
                results.append(base64.b64decode(b64))
            elif item.get("url"):
                # url 模式:再下载一次
                r = requests.get(item["url"], timeout=120)
                r.raise_for_status()
                results.append(r.content)
            else:
                raise GPTImageError(f"单张结果既无 b64_json 也无 url: {item}")
        return results


# ---------------------------------------------------------------------------
# 命令行 demo
# ---------------------------------------------------------------------------
def _demo():
    """简易 demo:从环境变量读取 key,做一次文生图 + 一次图生图"""
    import argparse

    parser = argparse.ArgumentParser(description="gpt-image-2 / 2.5 调用 demo")
    parser.add_argument("--model", default="gpt-image-2",
                        help="模型名,默认 gpt-image-2,可换 gpt-image-2.5")
    parser.add_argument("--prompt", required=True, help="文生图提示词")
    parser.add_argument("--ref", nargs="*", default=None,
                        help="参考图路径列表;提供则走图生图")
    parser.add_argument("--out", default="out.png", help="输出文件路径")
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--quality", default="medium")
    parser.add_argument("--format", default="png", dest="output_format")
    args = parser.parse_args()

    client = GPTImageClient()

    if args.ref:
        images = client.image_to_image(
            prompt=args.prompt,
            image_paths=args.ref,
            model=args.model,
            size=args.size,
            quality=args.quality,
            output_format=args.output_format,
        )
    else:
        images = client.text_to_image(
            prompt=args.prompt,
            model=args.model,
            size=args.size,
            quality=args.quality,
            output_format=args.output_format,
        )

    saved = client.save(images[0], args.out)
    print(f"✅ 已保存 {len(images)} 张图,首张: {saved}")


if __name__ == "__main__":
    _demo()