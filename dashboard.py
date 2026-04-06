"""
Dark-themed desktop UI for format / merge-company / merge-emails workflows.
Run: python dashboard.py

Drag-and-drop (Windows): uses windnd; drop callbacks only enqueue paths — the main Tk
thread drains the queue and updates the UI (avoids GIL / PyEval_RestoreThread issues).
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import traceback
from tkinter import filedialog
from typing import Literal

import customtkinter as ctk

from app import (
    run_format,
    run_merge_company,
    run_merge_emails,
    run_merge_full_pipeline,
)

FILE_TYPES = [
    ("CSV or Excel", "*.csv *.xlsx *.xls"),
    ("CSV", "*.csv"),
    ("Excel", "*.xlsx *.xls"),
    ("All files", "*.*"),
]

ACCENT = "#3b82f6"
WIN_BG = "#1e1e26"
WIN_BORDER = "#3d3d4d"
BG = "#16161c"
MUTED = "#8b8b9a"

Action = Literal["none", "format", "company", "emails", "full"]


class MergeDashboard(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Merge Studio")
        self.geometry("1000x740")
        self.minsize(900, 660)
        self.configure(fg_color=BG)

        self._paths: dict[str, str | None] = {"base": None, "company": None, "emails": None}
        self._output_dir: str = os.getcwd()
        self._output_name = ctk.StringVar(value="")  # filename stem only (no .xlsx)
        self._filter_export = ctk.BooleanVar(value=False)
        self._action: Action = "none"
        self._drop_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._last_success_output: str | None = None

        self._build()
        self._refresh_ui()
        self.after(50, self._poll_drop_queue)
        self._setup_drag_drop()

    def _build(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 10))

        ctk.CTkLabel(
            top,
            text="Merge Studio",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#f4f4f5",
        ).pack(anchor="w")
        ctk.CTkLabel(
            top,
            text="Drag a file onto a panel or use Choose file… · one action button",
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
        ).pack(anchor="w", pady=(2, 0))

        slots = ctk.CTkFrame(self, fg_color="transparent")
        slots.pack(fill="x", padx=20, pady=14)
        slots.grid_columnconfigure(0, weight=1, uniform="slot")
        slots.grid_columnconfigure(1, weight=1, uniform="slot")
        slots.grid_columnconfigure(2, weight=1, uniform="slot")

        self._slot_base = self._small_window(
            slots, col=0, key="base", title="Base", hint="Main table\n(CSV / Excel)"
        )
        self._slot_company = self._small_window(
            slots, col=1, key="company", title="Companies", hint="Company +\nWebsite"
        )
        self._slot_emails = self._small_window(
            slots, col=2, key="emails", title="Emails", hint="LinkedIn +\nEmail / Mails"
        )

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        out_fr = ctk.CTkFrame(
            body, fg_color=WIN_BG, corner_radius=10, border_width=1, border_color=WIN_BORDER
        )
        out_fr.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            out_fr,
            text="Output (.xlsx)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e4e4e7",
        ).pack(anchor="w", padx=12, pady=(10, 2))
        self._output_dir_label = ctk.CTkLabel(
            out_fr,
            text=self._format_dir_label(self._output_dir),
            font=ctk.CTkFont(size=9),
            text_color="#5c5c6a",
            anchor="w",
            wraplength=860,
            justify="left",
        )
        self._output_dir_label.pack(anchor="w", padx=12, pady=(0, 6))
        row = ctk.CTkFrame(out_fr, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=(0, 10))
        self._entry_out = ctk.CTkEntry(
            row,
            textvariable=self._output_name,
            placeholder_text="File name",
            height=36,
            font=ctk.CTkFont(size=12),
            border_color="#3f3f4e",
            fg_color="#14141a",
        )
        self._entry_out.pack(side="left", fill="x", expand=True, padx=(4, 8))
        ctk.CTkButton(
            row,
            text="Browse…",
            width=90,
            height=36,
            fg_color="#3f3f50",
            hover_color="#52525e",
            command=self._browse_output,
        ).pack(side="right")

        filt_fr = ctk.CTkFrame(
            body, fg_color=WIN_BG, corner_radius=10, border_width=1, border_color=WIN_BORDER
        )
        filt_fr.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            filt_fr,
            text="Export filter (optional)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e4e4e7",
        ).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            filt_fr,
            text="When enabled, only rows containing any keyword (any column, case-insensitive) are written to Excel.",
            font=ctk.CTkFont(size=10),
            text_color=MUTED,
            anchor="w",
            justify="left",
            wraplength=860,
        ).pack(anchor="w", padx=12, pady=(0, 6))
        filt_row = ctk.CTkFrame(filt_fr, fg_color="transparent")
        filt_row.pack(fill="x", padx=8, pady=(0, 6))
        self._chk_filter = ctk.CTkCheckBox(
            filt_row,
            text="Filter rows by keywords",
            variable=self._filter_export,
            font=ctk.CTkFont(size=12),
            command=self._on_filter_toggle,
            fg_color=ACCENT,
            hover_color="#2563eb",
        )
        self._chk_filter.pack(side="left", padx=(4, 12))
        self._filter_text = ctk.CTkTextbox(
            filt_fr,
            height=72,
            font=ctk.CTkFont(size=11),
            fg_color="#14141a",
            border_color="#3f3f4e",
            text_color="#e4e4e7",
            state="disabled",
        )
        self._filter_text.pack(fill="x", padx=12, pady=(0, 10))

        self._hint = ctk.CTkLabel(
            body,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=MUTED,
            wraplength=900,
            justify="center",
        )
        self._hint.pack(anchor="center", pady=(6, 10))

        self._action_btn = ctk.CTkButton(
            body,
            text="",
            height=46,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=ACCENT,
            hover_color="#2563eb",
            command=self._on_action_click,
        )
        self._action_btn.pack(fill="x", pady=(0, 8))

        # Above the log (not below) so it stays visible when the log expands.
        self._btn_open_location = ctk.CTkButton(
            body,
            text="Open file location",
            height=38,
            font=ctk.CTkFont(size=13),
            state="disabled",
            fg_color="#374151",
            hover_color="#4b5563",
            command=self._open_file_location,
        )
        self._btn_open_location.pack(fill="x", pady=(0, 10))

        self._log = ctk.CTkTextbox(
            body,
            height=180,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#0f0f14",
            border_color="#2d2d3a",
            text_color="#a1a1aa",
        )
        self._log.pack(fill="both", expand=True)

    def _small_window(
        self,
        parent: ctk.CTkFrame,
        *,
        col: int,
        key: str,
        title: str,
        hint: str,
    ) -> ctk.CTkFrame:
        """Compact bordered panel (small window look)."""
        win = ctk.CTkFrame(
            parent,
            fg_color=WIN_BG,
            corner_radius=10,
            border_width=1,
            border_color=WIN_BORDER,
        )
        win.grid(row=0, column=col, padx=6, sticky="nsew")

        ctk.CTkLabel(
            win,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f4f4f5",
        ).pack(anchor="w", padx=12, pady=(12, 2))
        ctk.CTkLabel(
            win,
            text=hint,
            font=ctk.CTkFont(size=11),
            text_color=MUTED,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 4))
        ctk.CTkLabel(
            win,
            text="Drop .csv / .xlsx here",
            font=ctk.CTkFont(size=10),
            text_color="#6b6b7a",
        ).pack(anchor="w", padx=12, pady=(0, 8))

        path_var = ctk.StringVar(value="— none —")
        ctk.CTkLabel(
            win,
            textvariable=path_var,
            font=ctk.CTkFont(size=10),
            text_color="#a1a1aa",
            anchor="w",
            wraplength=240,
            justify="left",
            height=36,
        ).pack(fill="x", padx=12, pady=(0, 8))

        def browse() -> None:
            p = filedialog.askopenfilename(filetypes=FILE_TYPES)
            if p:
                self._set_slot_path(key, p)

        ctk.CTkButton(
            win,
            text="Choose file…",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#3f3f50",
            hover_color="#52525e",
            command=browse,
        ).pack(fill="x", padx=12, pady=(0, 12))

        setattr(self, f"_path_label_{key}", path_var)
        setattr(self, f"_card_{key}", win)
        return win

    def _set_slot_path(self, key: str, path: str) -> None:
        self._paths[key] = path
        var = getattr(self, f"_path_label_{key}", None)
        if var:
            var.set(self._short_path(path, 34))
        self._on_paths_changed()

    def _decode_drop_path(self, raw: object) -> str:
        if isinstance(raw, bytes):
            for enc in ("utf-8", "mbcs"):
                try:
                    return raw.decode(enc).strip("\0").strip()
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace").strip("\0").strip()
        return str(raw).strip("\0").strip()

    def _poll_drop_queue(self) -> None:
        try:
            while True:
                key, path = self._drop_queue.get_nowait()
                path = os.path.normpath(path)
                if not path or not os.path.isfile(path):
                    continue
                ext = os.path.splitext(path)[1].lower()
                if ext not in (".csv", ".xlsx", ".xls"):
                    continue
                self._set_slot_path(key, path)
        except queue.Empty:
            pass
        self.after(80, self._poll_drop_queue)

    def _setup_drag_drop(self) -> None:
        try:
            import windnd  # type: ignore
        except ImportError:
            return

        def make_handler(key: str):
            def on_drop(files) -> None:
                if not files:
                    return
                try:
                    p = self._decode_drop_path(files[0])
                    self._drop_queue.put_nowait((key, p))
                except Exception:
                    pass

            return on_drop

        for key in ("base", "company", "emails"):
            card = getattr(self, f"_card_{key}", None)
            if card is None:
                continue
            try:
                windnd.hook_dropfiles(card, func=make_handler(key))
            except Exception:
                pass

    def _short_path(self, p: str, max_len: int) -> str:
        p = os.path.normpath(p)
        name = os.path.basename(p)
        if len(name) <= max_len:
            return name
        return name[: max_len - 1] + "…"

    def _format_dir_label(self, directory: str) -> str:
        d = os.path.normpath(directory or os.getcwd())
        prefix = "Folder: "
        cap = 90
        rest = d
        if len(prefix) + len(rest) > cap:
            rest = "…" + rest[-(cap - len(prefix) - 1) :]
        return prefix + rest

    def _update_dir_label(self) -> None:
        self._output_dir_label.configure(text=self._format_dir_label(self._output_dir))

    def _set_output_from_full_path(self, full_path: str) -> None:
        full_path = os.path.normpath(os.path.abspath(full_path))
        self._output_dir = os.path.dirname(full_path) or os.getcwd()
        stem = os.path.splitext(os.path.basename(full_path))[0]
        self._output_name.set(stem)
        self._update_dir_label()

    def _on_paths_changed(self) -> None:
        self._suggest_output()
        self._refresh_ui()

    def _default_output_xlsx(self, base_path: str) -> str:
        """Same folder + stem as base, extension .xlsx. If that path is the input file itself, use stem_N.xlsx."""
        directory = os.path.dirname(os.path.abspath(base_path)) or os.getcwd()
        stem = os.path.splitext(os.path.basename(base_path))[0]
        candidate = os.path.join(directory, f"{stem}.xlsx")

        def same_file(a: str, b: str) -> bool:
            return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))

        if not same_file(candidate, base_path):
            return candidate

        n = 1
        while True:
            alt = os.path.join(directory, f"{stem}_{n}.xlsx")
            if same_file(alt, base_path):
                n += 1
                continue
            if not os.path.isfile(alt):
                return alt
            n += 1

    def _suggest_output(self) -> None:
        base = self._paths.get("base")
        if not base:
            return
        if self._output_name.get().strip():
            return
        suggested = self._default_output_xlsx(base)
        self._set_output_from_full_path(suggested)

    def _browse_output(self) -> None:
        b = self._paths.get("base")
        initial_dir = self._output_dir
        if not initial_dir or not os.path.isdir(initial_dir):
            initial_dir = os.path.dirname(os.path.abspath(b)) if b else os.getcwd()
        initial_name = self._output_name.get().strip() or "output"
        p = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialdir=initial_dir if os.path.isdir(initial_dir) else None,
            initialfile=f"{initial_name}.xlsx",
        )
        if p:
            self._set_output_from_full_path(p)

    def _on_filter_toggle(self) -> None:
        if self._filter_export.get():
            self._filter_text.configure(state="normal")
        else:
            self._filter_text.configure(state="disabled")

    def _parse_filter_keywords(self) -> list[str]:
        raw = self._filter_text.get("1.0", "end")
        out: list[str] = []
        for line in raw.splitlines():
            for part in line.split(","):
                t = part.strip()
                if t:
                    out.append(t)
        return out

    def _keyword_filter_for_run(self) -> list[str] | None:
        if not self._filter_export.get():
            return None
        kws = self._parse_filter_keywords()
        if not kws:
            raise ValueError(
                "Filter by keywords is on — enter at least one keyword (comma or newline separated)."
            )
        return kws

    def _resolve_action(self) -> Action:
        b, c, e = self._paths["base"], self._paths["company"], self._paths["emails"]
        if not b:
            return "none"
        if c and e:
            return "full"
        if c:
            return "company"
        if e:
            return "emails"
        return "format"

    def _refresh_ui(self) -> None:
        self._action = self._resolve_action()

        if self._action == "none":
            self._action_btn.configure(
                state="disabled",
                text="Select base file first",
            )
            self._hint.configure(
                text="Add your main spreadsheet in the left window. Optional: company list and email list in the other two."
            )
        elif self._action == "format":
            self._action_btn.configure(
                state="normal",
                text="Format to Excel",
            )
            self._hint.configure(
                text="Only the base file is set — output will be a styled Excel copy (same data, formatted table & links)."
            )
        elif self._action == "company":
            self._action_btn.configure(
                state="normal",
                text="Merge company websites",
            )
            self._hint.configure(
                text="Base + company lookup — Website column will be filled by matching company names."
            )
        elif self._action == "emails":
            self._action_btn.configure(
                state="normal",
                text="Merge person emails",
            )
            self._hint.configure(
                text="Base + email lookup — Email column will be filled by matching LinkedIn URLs."
            )
        else:
            self._action_btn.configure(
                state="normal",
                text="Merge websites & emails",
            )
            self._hint.configure(
                text="All three files set — company websites are merged first, then emails by LinkedIn."
            )

    def _output_or_fail(self) -> str:
        stem = self._output_name.get().strip()
        stem = stem.replace("\\", "").replace("/", "").strip()
        stem = os.path.basename(stem) if stem else ""
        if not stem:
            raise ValueError("Enter an output file name (or use Browse…).")
        base = self._paths.get("base")
        if not self._output_dir or not os.path.isdir(self._output_dir):
            self._output_dir = os.path.dirname(os.path.abspath(base)) if base else os.getcwd()
            self._update_dir_label()
        if not os.path.isdir(self._output_dir):
            raise ValueError(f"Output folder is not valid: {self._output_dir}")
        return os.path.normpath(os.path.join(self._output_dir, f"{stem}.xlsx"))

    def _log_line(self, msg: str) -> None:
        self._log.insert("end", msg + "\n")
        self._log.see("end")

    def _finish_success(self, output_path: str, log_msg: str) -> None:
        self._log_line(log_msg)
        self._last_success_output = os.path.normpath(output_path)
        if os.path.isfile(self._last_success_output):
            self._set_output_from_full_path(self._last_success_output)
            self._btn_open_location.configure(state="normal")

    def _open_file_location(self) -> None:
        path = self._last_success_output
        if not path or not os.path.isfile(path):
            return
        path = os.path.normpath(path)
        try:
            if sys.platform == "win32":
                subprocess.run(["explorer", "/select,", path], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", path], check=False)
            else:
                subprocess.run(["xdg-open", os.path.dirname(path)], check=False)
        except OSError:
            pass

    def _on_action_click(self) -> None:
        act = self._action
        if act == "none":
            return
        if act == "format":
            self._run_async(self._do_format)
        elif act == "company":
            self._run_async(self._do_merge_company)
        elif act == "emails":
            self._run_async(self._do_merge_emails)
        else:
            self._run_async(self._do_full)

    def _run_async(self, fn) -> None:
        def work() -> None:
            try:
                fn()
            except Exception as ex:
                err = f"{ex}\n{traceback.format_exc()}"
                self.after(0, lambda: self._log_line(err))

        self.after(0, lambda: self._btn_open_location.configure(state="disabled"))
        self._log_line("Running…")
        threading.Thread(target=work, daemon=True).start()

    def _do_format(self) -> None:
        b = self._paths["base"]
        if not b:
            raise ValueError("Select a base file.")
        out = self._output_or_fail()
        kw = self._keyword_filter_for_run()
        n = run_format(b, out, table_name="Data", keyword_filter=kw)
        self.after(
            0,
            lambda n=n, o=out: self._finish_success(o, f"Formatted {n} rows → {o}"),
        )

    def _do_merge_company(self) -> None:
        b, c = self._paths["base"], self._paths["company"]
        if not b or not c:
            raise ValueError("Need base + company files.")
        out = self._output_or_fail()
        kw = self._keyword_filter_for_run()
        rows, matched = run_merge_company(b, c, out, table_name="EnergyTech", keyword_filter=kw)
        self.after(
            0,
            lambda r=rows, m=matched, o=out: self._finish_success(
                o,
                f"Rows: {r}, websites matched: {m}\n→ {o}",
            ),
        )

    def _do_merge_emails(self) -> None:
        b, e = self._paths["base"], self._paths["emails"]
        if not b or not e:
            raise ValueError("Need base + email lookup files.")
        out = self._output_or_fail()
        kw = self._keyword_filter_for_run()
        rows, matched = run_merge_emails(b, e, out, table_name="WithEmails", keyword_filter=kw)
        self.after(
            0,
            lambda r=rows, m=matched, o=out: self._finish_success(
                o,
                f"Rows: {r}, emails matched: {m}\n→ {o}",
            ),
        )

    def _do_full(self) -> None:
        b, c, e = self._paths["base"], self._paths["company"], self._paths["emails"]
        if not b or not c or not e:
            raise ValueError("Need all three files for the full pipeline.")
        out = self._output_or_fail()
        kw = self._keyword_filter_for_run()
        rows, web_n, em_n = run_merge_full_pipeline(
            b, c, e, out, table_name="Merged", keyword_filter=kw
        )
        self.after(
            0,
            lambda r=rows, w=web_n, m=em_n, o=out: self._finish_success(
                o,
                f"Rows: {r}, websites filled: {w}, emails matched: {m}\n→ {o}",
            ),
        )

def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = MergeDashboard()
    app.mainloop()


if __name__ == "__main__":
    main()
