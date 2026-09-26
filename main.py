#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yt-dlp GUI - 图形界面视频下载器
基于 yt-dlp Python API 构建，打包后为单文件 EXE，内置 FFmpeg，无需任何环境。
"""

import sys
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox

# ── PyInstaller --noconsole 模式下 stdout/stderr 为 None，重定向防止崩溃 ──
if getattr(sys, "frozen", False):
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import yt_dlp


def get_ffmpeg_location():
    """返回打包内置的 FFmpeg 目录；开发环境返回 None（走系统 PATH）。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return None


# ── 下载格式预设 ──────────────────────────────────────────────────
FORMAT_PRESETS = {
    "最佳画质 MP4": {
        "format": "bestvideo*+bestaudio/best",
        "merge_output_format": "mp4",
    },
    "1080p MP4": {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "merge_output_format": "mp4",
    },
    "720p MP4": {
        "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "merge_output_format": "mp4",
    },
    "480p MP4": {
        "format": "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "merge_output_format": "mp4",
    },
    "仅音频 MP3 (192kbps)": {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    },
}


def _fmt_size(b):
    if b is None:
        return "?"
    if b >= 1024 * 1024:
        return f"{b / 1024 / 1024:.1f}MB"
    if b >= 1024:
        return f"{b / 1024:.1f}KB"
    return f"{b:.0f}B"


def _fmt_speed(s):
    if not s:
        return ""
    if s >= 1024 * 1024:
        return f"{s / 1024 / 1024:.1f}MB/s"
    if s >= 1024:
        return f"{s / 1024:.1f}KB/s"
    return f"{s:.0f}B/s"


class YtDlpGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("yt-dlp GUI - 视频下载器")
        self.root.geometry("720x600")
        self.root.minsize(620, 520)

        # 线程间通信队列（下载线程写，GUI 线程读）
        self.msg_queue = queue.Queue()
        self.download_thread = None
        self.is_downloading = False

        self._build_ui()
        self._poll_queue()

    # ──────────────── UI 构建 ────────────────
    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")  # Windows 原生主题
        except tk.TclError:
            pass

        pad = {"padx": 12, "pady": 5}

        # 视频链接
        url_frame = ttk.LabelFrame(self.root, text="视频链接", padding=8)
        url_frame.pack(fill="x", **pad)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var,
                                   font=("Segoe UI", 10))
        self.url_entry.pack(fill="x")
        self.url_entry.bind("<Return>", lambda _e: self._start_download())
        self.url_entry.focus_set()

        # 格式 + 保存目录
        opt_frame = ttk.Frame(self.root)
        opt_frame.pack(fill="x", **pad)

        ttk.Label(opt_frame, text="格式:").pack(side="left")
        self.format_var = tk.StringVar(value="最佳画质 MP4")
        ttk.Combobox(opt_frame, textvariable=self.format_var,
                     values=list(FORMAT_PRESETS.keys()),
                     state="readonly", width=20).pack(side="left", padx=(4, 16))

        ttk.Label(opt_frame, text="保存到:").pack(side="left")
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.output_var = tk.StringVar(value=default_dir)
        ttk.Entry(opt_frame, textvariable=self.output_var).pack(
            side="left", fill="x", expand=True, padx=(4, 6))
        ttk.Button(opt_frame, text="浏览...",
                   command=self._browse_output).pack(side="left")

        # 按钮行
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", **pad)
        self.download_btn = ttk.Button(btn_frame, text="开始下载",
                                       command=self._start_download)
        self.download_btn.pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="打开下载文件夹",
                   command=self._open_output).pack(side="left")

        # 进度
        prog_frame = ttk.LabelFrame(self.root, text="下载进度", padding=8)
        prog_frame.pack(fill="x", **pad)
        self.progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(prog_frame, variable=self.progress_var,
                        maximum=100).pack(fill="x")
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(prog_frame, textvariable=self.status_var,
                  font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))

        # 日志
        log_frame = ttk.LabelFrame(self.root, text="日志", padding=8)
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=12, font=("Consolas", 9),
            state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

    # ──────────────── 辅助方法 ────────────────
    def _browse_output(self):
        d = filedialog.askdirectory(initialdir=self.output_var.get() or os.getcwd())
        if d:
            self.output_var.set(d)

    def _open_output(self):
        path = self.output_var.get()
        if os.path.isdir(path):
            os.startfile(path)
        else:
            messagebox.showwarning("提示", "下载目录不存在")

    def _append_log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    # ──────────────── 线程安全通信 ────────────────
    def _log(self, msg):
        self.msg_queue.put(("log", msg))

    def _set_progress(self, pct, status=""):
        self.msg_queue.put(("progress", pct, status))

    def _set_downloading(self, downloading):
        self.msg_queue.put(("state", downloading))

    def _poll_queue(self):
        try:
            while True:
                item = self.msg_queue.get_nowait()
                if item[0] == "log":
                    self._append_log(item[1])
                elif item[0] == "progress":
                    self.progress_var.set(item[1])
                    if item[2]:
                        self.status_var.set(item[2])
                elif item[0] == "state":
                    self.is_downloading = item[1]
                    self.download_btn.config(
                        state="normal" if not item[1] else "disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    # ──────────────── 下载逻辑 ────────────────
    def _start_download(self):
        if self.is_downloading:
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入视频链接")
            return
        outdir = self.output_var.get().strip()
        if not outdir:
            messagebox.showwarning("提示", "请选择保存目录")
            return
        os.makedirs(outdir, exist_ok=True)

        fmt_key = self.format_var.get()
        preset = FORMAT_PRESETS[fmt_key]

        self.progress_var.set(0)
        self.status_var.set("正在解析...")
        self._append_log("=" * 54)
        self._log(f"[信息] 链接: {url}")
        self._log(f"[信息] 格式: {fmt_key}")
        self._log(f"[信息] 保存到: {outdir}")
        self._log("[信息] 正在解析视频信息...")

        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(url, outdir, preset),
            daemon=True,
        )
        self.download_thread.start()
        self._set_downloading(True)

    def _progress_hook(self, d):
        """yt-dlp 进度回调，在下载线程中执行。"""
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed", 0)
            eta = d.get("eta", 0)
            pct = (downloaded / total * 100) if total > 0 else 0

            parts = [f"下载中: {_fmt_size(downloaded)} / {_fmt_size(total)}"]
            sp = _fmt_speed(speed)
            if sp:
                parts.append(sp)
            if eta:
                parts.append(f"剩余 {int(eta)}s")
            self._set_progress(min(pct, 99.9), " | ".join(parts))

        elif status == "finished":
            self._log("[信息] 数据下载完成，正在合并/转码...")

    def _download_worker(self, url, outdir, preset):
        try:
            ydl_opts = {
                "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
                "progress_hooks": [self._progress_hook],
                "retries": 3,
                "fragment_retries": 3,
            }
            ffmpeg_dir = get_ffmpeg_location()
            if ffmpeg_dir:
                ydl_opts["ffmpeg_location"] = ffmpeg_dir
                self._log("[信息] 已加载内置 FFmpeg")

            ydl_opts.update(preset)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    title = info.get("title", "未知")
                    self._log(f"[完成] 标题: {title}")

            self._set_progress(100, "下载完成！")
            self._log("[完成] 文件已保存到指定目录")
        except Exception as e:
            self._log(f"[错误] {e}")
            self._set_progress(0, "下载失败，请查看日志")
        finally:
            self._set_downloading(False)


def main():
    root = tk.Tk()
    YtDlpGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
