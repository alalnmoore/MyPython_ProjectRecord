"""
gpt_image_client.py 的常见用法示例(交互式 CLI)

运行前:
  1. 把 .env.example 复制为 .env,填入 RTOC_API_KEY
  2. (可选)把参考图放到 ./refs/ 目录,文件名避免中文和空格

运行:
  python examples.py
"""
import os
import sys
from pathlib import Path

# 让脚本所在目录的 .env 生效
HERE = Path(__file__).resolve().parent
os.chdir(HERE)

from gpt_image_client import (  # noqa: E402 必须在 chdir 之后
    GPTImageClient,
    SIZE_PRESETS,
    QUALITY_PRESETS,
    FORMAT_PRESETS,
)


REFS_DIR = HERE / "refs"
OUTPUT_DIR = HERE / "output"

# 实测可用的生图模型(2026-09);想加新模型直接在这里追加
# 格式:(菜单上显示的文本, 实际传给 API 的模型名)
AVAILABLE_MODELS = [
    ("gpt-image-2            ✅ 标准版,~87 秒/张",     "gpt-image-2"),
    ("gpt-image-2.5-flare    ⚡ 快速变体,~48 秒/张",   "gpt-image-2.5-flare"),
    ("gpt-image-2.5-sunburst  ☀️  sunburst 变体",       "gpt-image-2.5-sunburst"),
]


def _prompt(label: str, default: str = "") -> str:
    """带默认值的输入提示"""
    suffix = f" [{default}]" if default else ""
    val = input(f"{label}{suffix}: ").strip()
    return val or default


def _read_prompt(label: str = "提示词") -> str:
    """
    读取用户提示词。三种输入方式自动识别:

    1) 单行:粘贴一行内容,直接回车(适合短 prompt)
    2) 多行:粘贴多段文字,以单独一行 <<END>> 结束(适合 Windows 终端粘贴)
    3) 文件:第一行直接是一个已存在文件的绝对路径,自动读整个文件
       (适合特别长 / 想反复复用的 prompt)

    为什么需要多行模式:
      Windows cmd / PowerShell 粘贴带 \n 的多段文本时,每个 \n 都会触发一次 input()。
      如果只读一行,buffer 里剩下的多段会"自动回车"掉后面所有步骤。
      用 <<END>> 作为显式结束标记,程序才知道 prompt 到哪一行完。
    """
    print(f"\n{label}:")
    print("  · 短 prompt:粘贴一行 + 再回车 结束")
    print("  · 长 prompt:粘贴多行 + 单独一行 <<END>> 结束")
    print("  · 文件:直接粘贴文件路径(如 C:/.../prompt.txt)")
    print()

    first = input(f"{label}: ")
    first_stripped = first.strip().strip('"\'')

    # 文件模式:第一行就是一个存在的文件路径
    if first_stripped:
        candidate = Path(first_stripped)
        if candidate.is_file():
            content = candidate.read_text(encoding="utf-8").strip()
            print(f"  📄 已从文件读取,长度 {len(content)} 字符")
            return content

    # 多行模式:继续读直到 <<END>> 或空行(已有内容后再按一次回车)
    lines = [first]
    while True:
        try:
            line = input()
        except EOFError:
            break
        stripped = line.strip()
        if stripped == "<<END>>":
            break
        # 单行场景:输入完直接再按一次回车 = 结束
        if stripped == "" and lines and lines[-1].strip() != "":
            break
        lines.append(line)

    return "\n".join(lines).strip()


def _pick(label: str, options, default_idx: int = 0):
    """
    让用户从列表中选一项,返回对应的 value。

    options 可以是:
      - 字符串列表:显示和返回值相同
      - [(display, value), ...] 二元组:显示 display,返回 value
    """
    display_list = []
    value_list = []
    for o in options:
        if isinstance(o, tuple) and len(o) == 2:
            display_list.append(o[0])
            value_list.append(o[1])
        else:
            display_list.append(str(o))
            value_list.append(o)

    print(f"\n{label}:")
    for i, display in enumerate(display_list):
        marker = " *" if i == default_idx else "  "
        print(f"  {marker}{i + 1}. {display}")
    raw = input(f"选第几个 [{default_idx + 1}]: ").strip()
    if not raw:
        return value_list[default_idx]
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(value_list):
            return value_list[idx]
    except ValueError:
        pass
    return value_list[default_idx]


def text_to_image_flow():
    """文生图完整流程"""
    print("\n" + "=" * 50)
    print("🎨 文生图模式")
    print("=" * 50)

    client = GPTImageClient()  # 自动从 .env 读 RTOC_API_KEY

    model = _pick("选择模型", AVAILABLE_MODELS, default_idx=0)
    prompt = _read_prompt("提示词(必填)")
    if not prompt:
        print("❌ 提示词不能为空")
        return

    size_label = _pick("选择尺寸", list(SIZE_PRESETS.keys()), default_idx=0)
    size = SIZE_PRESETS[size_label]
    quality = _pick("选择质量", QUALITY_PRESETS, default_idx=1)
    output_format = _pick("输出格式", FORMAT_PRESETS, default_idx=0)
    n = int(_prompt("生成张数 n", "1") or "1")

    print(f"\n→ 调用 {model},size={size}, quality={quality}, n={n}")
    images = client.text_to_image(
        model=model, prompt=prompt,
        size=size, quality=quality,
        output_format=output_format, n=n,
    )
    for i, img in enumerate(images):
        out = OUTPUT_DIR / client.generate_filename(
            mode="t2i", model=model, size=size,
            quality=quality, ext=output_format, index=i if n > 1 else 0,
        )
        client.save(img, out)
        print(f"✅ 已保存: {out}")


def image_to_image_flow():
    """图生图完整流程"""
    print("\n" + "=" * 50)
    print("🖼️  图生图模式")
    print("=" * 50)

    client = GPTImageClient()

    # 扫描 refs/ 目录
    refs = GPTImageClient.list_local_images(REFS_DIR)
    if not refs:
        print(f"❌ 参考图目录为空: {REFS_DIR}")
        print("   请先把参考图放到该目录下再试")
        return

    print(f"\n📁 在 {REFS_DIR} 找到 {len(refs)} 张参考图:")
    for i, p in enumerate(refs):
        print(f"  {i + 1}. {p.name}  ({p.stat().st_size // 1024} KB)")

    raw = input("\n输入要用的编号,逗号分隔(如 1,3) [全选]: ").strip()
    if raw:
        try:
            idxs = [int(x) - 1 for x in raw.split(",") if x.strip()]
            chosen = [refs[i] for i in idxs if 0 <= i < len(refs)]
        except ValueError:
            print("❌ 输入格式错误")
            return
    else:
        chosen = refs
    if not chosen:
        print("❌ 没选到任何图")
        return

    model = _pick("选择模型", AVAILABLE_MODELS, default_idx=0)
    prompt = _read_prompt("提示词(必填)")
    if not prompt:
        print("❌ 提示词不能为空")
        return

    size_label = _pick("选择尺寸", list(SIZE_PRESETS.keys()), default_idx=0)
    size = SIZE_PRESETS[size_label]
    quality = _pick("选择质量", QUALITY_PRESETS, default_idx=1)
    output_format = _pick("输出格式", FORMAT_PRESETS, default_idx=0)
    n = int(_prompt("生成张数 n", "1") or "1")

    print(f"\n→ 调用 {model},参考图={[p.name for p in chosen]}")
    images = client.image_to_image(
        model=model, prompt=prompt,
        image_paths=chosen,
        size=size, quality=quality,
        output_format=output_format, n=n,
    )
    for i, img in enumerate(images):
        out = OUTPUT_DIR / client.generate_filename(
            mode="i2i", model=model, size=size,
            quality=quality, ext=output_format, index=i if n > 1 else 0,
        )
        client.save(img, out)
        print(f"✅ 已保存: {out}")


def list_models_flow():
    """查询可用模型"""
    print("\n" + "=" * 50)
    print("📋 模型列表")
    print("=" * 50)
    client = GPTImageClient()
    data = client.list_models().get("data", [])
    ids = [m.get("id") for m in data]
    print(f"\n当前 key 可见的模型({len(ids)} 个):")
    for i in ids:
        marker = "🖼️ " if "image" in (i or "").lower() else "  "
        print(f"  {marker}{i}")


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    print("🚀 GPT Image 客户端示例")
    while True:
        print("\n主菜单:")
        print("  1. 文生图")
        print("  2. 图生图(从 refs/ 目录选参考图)")
        print("  3. 查看可用模型")
        print("  0. 退出")
        choice = input("\n选哪项: ").strip()
        if choice == "1":
            text_to_image_flow()
        elif choice == "2":
            image_to_image_flow()
        elif choice == "3":
            list_models_flow()
        elif choice in ("0", "q", "Q"):
            print("👋 bye")
            break
        else:
            print("❓ 无效选项")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 用户中断,bye")
        sys.exit(0)