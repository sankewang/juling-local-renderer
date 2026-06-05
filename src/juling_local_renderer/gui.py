from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from juling_local_renderer.cli import (
    CLI_VERSION,
    RenderError,
    default_output_path,
    find_ffmpeg,
    manifest_languages,
    package_summary,
    render_language,
    validate_package,
)


LANGUAGE_LABELS = {
    "zh": "中文",
    "en": "英语",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "it": "意大利语",
    "es": "西班牙语",
    "pt": "葡萄牙语",
    "ru": "俄语",
}


class JulingRendererApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.package_path = StringVar()
        self.output_dir = StringVar()
        self.render_all = BooleanVar(value=True)
        self.burn_subtitles = BooleanVar(value=True)
        self.language = StringVar()
        self.languages: list[str] = []
        self.is_working = False

        self.root.title("剧灵绘本地渲染器")
        self.root.geometry("760x560")
        self.root.minsize(720, 520)
        self._build_ui()
        self._poll_queue()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        frame = ttk.Frame(self.root, padding=18)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(7, weight=1)

        title = ttk.Label(frame, text="剧灵绘本地渲染器", font=("", 18, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w")

        subtitle = ttk.Label(
            frame,
            text="选择从剧灵绘AI漫剧平台下载的本地渲染素材包 ZIP，点击开始渲染即可生成 MP4。",
        )
        subtitle.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 16))

        ttk.Label(frame, text="素材包 ZIP").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.package_path).grid(row=2, column=1, sticky="ew", padx=(10, 8))
        ttk.Button(frame, text="选择素材包", command=self.choose_package).grid(row=2, column=2, sticky="ew")

        ttk.Label(frame, text="输出文件夹").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.output_dir).grid(row=3, column=1, sticky="ew", padx=(10, 8))
        ttk.Button(frame, text="选择输出目录", command=self.choose_output_dir).grid(row=3, column=2, sticky="ew")

        options = ttk.Frame(frame)
        options.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 4))
        options.columnconfigure(4, weight=1)
        ttk.Checkbutton(options, text="渲染全部语言", variable=self.render_all, command=self.update_language_state).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(options, text="单语言").grid(row=0, column=1, sticky="w", padx=(24, 8))
        self.language_select = ttk.Combobox(options, textvariable=self.language, state="disabled", width=18)
        self.language_select.grid(row=0, column=2, sticky="w")
        ttk.Checkbutton(options, text="烧录字幕", variable=self.burn_subtitles).grid(row=0, column=3, sticky="w", padx=(24, 0))

        actions = ttk.Frame(frame)
        actions.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(14, 10))
        actions.columnconfigure(3, weight=1)
        self.check_button = ttk.Button(actions, text="检查素材包", command=self.check_package)
        self.check_button.grid(row=0, column=0, sticky="w")
        self.render_button = ttk.Button(actions, text="开始渲染", command=self.start_render)
        self.render_button.grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Button(actions, text="打开输出文件夹", command=self.open_output_dir).grid(row=0, column=2, sticky="w", padx=(10, 0))

        self.status = ttk.Label(frame, text="状态：请选择素材包", foreground="#555")
        self.status.grid(row=6, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self.log = ScrolledText(frame, height=15, wrap="word")
        self.log.grid(row=7, column=0, columnspan=3, sticky="nsew")
        self.log.configure(state="disabled")

    def choose_package(self) -> None:
        path = filedialog.askopenfilename(
            title="选择本地渲染素材包 ZIP",
            filetypes=[("ZIP 素材包", "*.zip"), ("所有文件", "*.*")],
        )
        if not path:
            return
        self.package_path.set(path)
        package = Path(path)
        if not self.output_dir.get():
            self.output_dir.set(str(package.parent / "exports"))
        self.check_package()

    def choose_output_dir(self) -> None:
        path = filedialog.askdirectory(title="选择输出文件夹")
        if path:
            self.output_dir.set(path)

    def update_language_state(self) -> None:
        self.language_select.configure(state="disabled" if self.render_all.get() else "readonly")

    def check_package(self) -> None:
        package = self._package_or_warn()
        if not package:
            return
        try:
            validation = validate_package(package, require_ffmpeg_check=True)
            summary = package_summary(package)
            self.languages = manifest_languages(package)
            self.language_select["values"] = [self._language_label(lang) for lang in self.languages]
            if self.languages and not self.language.get():
                self.language.set(self._language_label(self.languages[0]))
            self.update_language_state()

            self._log("")
            self._log(f"素材包：{package}")
            self._log(f"任务名称：{summary.get('name') or '-'}")
            self._log(f"输出规格：{summary.get('resolution') or '-'} / {summary.get('aspect_ratio') or '-'}")
            self._log(f"目标语言：{'、'.join(self._language_label(lang) for lang in self.languages) or '-'}")
            if validation["ffmpeg"]:
                self._log(f"FFmpeg：{validation['ffmpeg']}")
            for warning in validation["warnings"]:
                self._log(f"提醒：{warning}")
            if validation["ok"]:
                self._set_status("状态：素材包检查通过，可以开始渲染")
            else:
                self._set_status("状态：素材包检查失败")
                for error in validation["errors"]:
                    self._log(f"错误：{error}")
                messagebox.showerror("素材包检查失败", "\n".join(validation["errors"]))
        except Exception as exc:
            self._set_status("状态：素材包检查失败")
            self._log(f"错误：{exc}")
            messagebox.showerror("素材包检查失败", str(exc))

    def start_render(self) -> None:
        if self.is_working:
            return
        package = self._package_or_warn()
        if not package:
            return
        output_dir = Path(self.output_dir.get() or package.parent / "exports")
        if not find_ffmpeg():
            messagebox.showerror(
                "缺少 FFmpeg",
                "没有找到 FFmpeg。\n\n请安装 FFmpeg 并加入系统 PATH，或把 ffmpeg.exe 放到本工具同一个文件夹。",
            )
            return
        try:
            validation = validate_package(package, require_ffmpeg_check=True)
            if not validation["ok"]:
                messagebox.showerror("素材包不可渲染", "\n".join(validation["errors"]))
                return
            langs = manifest_languages(package) if self.render_all.get() else [self._selected_language_code()]
            langs = [lang for lang in langs if lang]
            if not langs:
                messagebox.showerror("没有可渲染语言", "素材包里没有找到目标语言音轨。")
                return
        except Exception as exc:
            messagebox.showerror("无法开始渲染", str(exc))
            return

        self._set_working(True)
        self._log("")
        self._log(f"开始渲染，输出目录：{output_dir}")
        thread = threading.Thread(
            target=self._render_worker,
            args=(package, output_dir, langs, self.burn_subtitles.get()),
            daemon=True,
        )
        thread.start()

    def _render_worker(self, package: Path, output_dir: Path, langs: list[str], burn_subtitles: bool) -> None:
        try:
            for lang in langs:
                output = default_output_path(package, lang, output_dir)
                self.queue.put(("log", f"正在渲染 {self._language_label(lang)}：{output.name}"))
                render_language(package, lang, output, burn_subtitles=burn_subtitles)
                self.queue.put(("log", f"完成：{output}"))
            self.queue.put(("done", output_dir))
        except RenderError as exc:
            self.queue.put(("error", str(exc)))
        except Exception as exc:
            self.queue.put(("error", f"渲染失败：{exc}"))

    def open_output_dir(self) -> None:
        path = Path(self.output_dir.get() or ".").resolve()
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    self._log(str(payload))
                elif kind == "done":
                    self._set_working(False)
                    self._set_status("状态：渲染完成")
                    self._log("全部渲染完成。")
                    messagebox.showinfo("渲染完成", f"视频已输出到：\n{payload}")
                elif kind == "error":
                    self._set_working(False)
                    self._set_status("状态：渲染失败")
                    self._log(str(payload))
                    messagebox.showerror("渲染失败", str(payload))
        except queue.Empty:
            pass
        self.root.after(150, self._poll_queue)

    def _selected_language_code(self) -> str:
        selected = self.language.get()
        for lang in self.languages:
            if selected == self._language_label(lang):
                return lang
        return self.languages[0] if self.languages else ""

    def _language_label(self, lang: str) -> str:
        return f"{LANGUAGE_LABELS.get(lang, lang)} ({lang})"

    def _package_or_warn(self) -> Path | None:
        value = self.package_path.get().strip()
        if not value:
            messagebox.showwarning("请选择素材包", "请先选择从剧灵绘AI漫剧平台下载的本地渲染素材包 ZIP。")
            return None
        return Path(value).resolve()

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def _set_working(self, working: bool) -> None:
        self.is_working = working
        state = "disabled" if working else "normal"
        self.check_button.configure(state=state)
        self.render_button.configure(state=state)
        self.render_button.configure(text="渲染中..." if working else "开始渲染")

    def _log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


def main() -> None:
    root = Tk()
    JulingRendererApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
