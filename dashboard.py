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
import tempfile
import threading
import traceback
import tkinter as tk
from tkinter import filedialog
from typing import Literal

import customtkinter as ctk
import pandas as pd

from app import (
    load_table,
    run_format,
    run_merge_company,
    run_merge_emails,
    run_merge_full_pipeline,
)

CSV_EXT = ".csv"
XLSX_EXT = ".xlsx"
XLS_EXT = ".xls"

FILE_TYPES = [
    ("CSV or Excel", f"*{CSV_EXT} *{XLSX_EXT} *{XLS_EXT}"),
    ("CSV", f"*{CSV_EXT}"),
    ("Excel", f"*{XLSX_EXT} *{XLS_EXT}"),
    ("All files", "*.*"),
]
SUPPORTED_INPUT_EXTS = (CSV_EXT, XLSX_EXT, XLS_EXT)
OUTPUT_EXT = XLSX_EXT

# Canonical base columns used when multiple base files are combined.
# Aliases are normalized with lowercase + alnum only.
BASE_COLUMN_ALIASES = {
    "name": "Name",
    "fullname": "Name",
    "personname": "Name",
    "company": "Company",
    "companyname": "Company",
    "organization": "Company",
    "organisation": "Company",
    "position": "Position",
    "title": "Position",
    "jobtitle": "Position",
    "designation": "Position",
    "linkedin": "LinkedIn",
    "linkedinurl": "LinkedIn",
    "linkedinprofile": "LinkedIn",
    "email": "Email",
    "emailaddress": "Email",
    "mails": "Email",
    "website": "Website",
    "companywebsite": "Website",
}

ACCENT = "#3b82f6"
WIN_BG = "#1e1e26"
WIN_BORDER = "#3d3d4d"
BG = "#16161c"
MUTED = "#8b8b9a"

# Default export-filter keywords — comma-separated, one line (phrases may contain spaces, not commas).
# Prefix with '-' to exclude rows containing those terms.
_DEFAULT_FILTER_PARTS = (
    "-University",
    "-College",
    "-School",
    "-Institute",
    "-Laboratory",
    "-Lab",
    "-Software",
    "-Consulting",
    "-Consultants",
    "-Media",
    "-Press",
    "-News",
    "-Communications",
    "-PR",
    "-Public Relations",
    "-Analyst",
    "-Analysis",
    "-Coordinator",
    "-Representative",
    "-Recruiter",
    "-Intern",
    "-Fellow",
    "-Student",
    "-PHD",
    "-PhD",
    "-Professor",
    "-Researcher",
    "-Human Resource",
    "-HR",
    "-Journalist",
    "-Reporter",
    "-Correspondent",
    "-Photographer",
    "-Social Media",
    "-Marketing",
    "-Editorial",
    "-Editor",
    "-Staff",
    "-Sales",
    "-Business Development",
    "-Customer Success",
    "-Partnerships",
    "-Manager",
    "-Deputy",
    "-Engineer",
)
DEFAULT_EXPORT_FILTER_KEYWORDS = ", ".join(_DEFAULT_FILTER_PARTS)

Action = Literal["none", "format", "company", "emails", "full"]


class MergeDashboard(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Merge Studio")
        self.geometry("1000x720")
        self.minsize(900, 660)
        self.configure(fg_color=BG)

        self._paths: dict[str, str | None] = {"base": None, "company": None, "emails": None}
        self._base_paths: list[str] = []
        self._output_dir: str = os.getcwd()
        self._output_name = ctk.StringVar(value="")  # filename stem only (no .xlsx)
        self._filter_export = ctk.BooleanVar(value=False)
        self._require_linkedin = ctk.BooleanVar(value=False)
        self._filter_keywords = ctk.StringVar(value="")
        self._action: Action = "none"
        self._drop_queue: queue.Queue[tuple[str, list[str]]] = queue.Queue()
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
        slots.pack(fill="x", padx=20, pady=(8, 8))
        slots.grid_columnconfigure(0, weight=1, uniform="slot")
        slots.grid_columnconfigure(1, weight=1, uniform="slot")
        slots.grid_columnconfigure(2, weight=1, uniform="slot")

        self._slot_base = self._small_window(
            slots,
            col=0,
            key="base",
            title="Base",
            hint="Main table(s) · CSV / Excel · drop or choose (multi-select)",
        )
        self._slot_company = self._small_window(
            slots, col=1, key="company", title="Companies", hint="Company + website · drop or choose"
        )
        self._slot_emails = self._small_window(
            slots, col=2, key="emails", title="Emails", hint="LinkedIn + email / Mails · drop or choose"
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
        filt_header = ctk.CTkFrame(filt_fr, fg_color="transparent")
        filt_header.pack(fill="x", padx=12, pady=(10, 2))
        self._chk_filter = ctk.CTkCheckBox(
            filt_header,
            text="Filter rows by keywords",
            variable=self._filter_export,
            font=ctk.CTkFont(size=12),
            command=self._on_filter_toggle,
            fg_color=ACCENT,
            hover_color="#2563eb",
        )
        self._chk_filter.pack(side="right", anchor="e")
        self._chk_require_linkedin = ctk.CTkCheckBox(
            filt_header,
            text="Drop rows without LinkedIn",
            variable=self._require_linkedin,
            font=ctk.CTkFont(size=12),
            fg_color=ACCENT,
            hover_color="#2563eb",
        )
        self._chk_require_linkedin.pack(side="right", anchor="e", padx=(0, 14))
        ctk.CTkLabel(
            filt_header,
            text="Export filter (optional)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e4e4e7",
        ).pack(side="left", anchor="w")
        filter_entry_row = ctk.CTkFrame(filt_fr, fg_color="transparent")
        filter_entry_row.pack(fill="x", padx=12, pady=(0, 10))
        self._filter_entry = ctk.CTkEntry(
            filter_entry_row,
            textvariable=self._filter_keywords,
            height=32,
            font=ctk.CTkFont(size=11),
            border_color="#3f3f4e",
            fg_color="#14141a",
            text_color="#e4e4e7",
            placeholder_text="Use keywords, or -keyword to exclude rows",
            state="disabled",
        )
        self._filter_entry.pack(side="top", fill="x")
        self._filter_hscroll = ctk.CTkScrollbar(
            filter_entry_row,
            orientation="horizontal",
            height=12,
            fg_color="#2d2d3a",
            button_color="#4b4b5a",
            button_hover_color="#5c5c6a",
            command=lambda *a: self._filter_entry._entry.xview(*a),
        )
        self._filter_entry._entry.configure(xscrollcommand=self._filter_hscroll.set)
        self._filter_hscroll.pack(side="top", fill="x", pady=(4, 0))

        def _filter_entry_update_hscroll(_event: object | None = None) -> None:
            try:
                e = self._filter_entry._entry
                e.update_idletasks()
                lo, hi = e.xview()
                self._filter_hscroll.set(lo, hi)
            except (tk.TclError, ValueError):
                pass

        self._filter_entry._entry.bind("<KeyRelease>", _filter_entry_update_hscroll)
        self._filter_entry._entry.bind("<ButtonRelease-1>", _filter_entry_update_hscroll)

        self._set_filter_text_content(DEFAULT_EXPORT_FILTER_KEYWORDS)
        self._filter_entry.configure(state="disabled")
        self._sync_filter_entry_scroll()

        self._hint = ctk.CTkLabel(
            body,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=MUTED,
            wraplength=900,
            justify="center",
        )
        self._hint.pack(anchor="center", pady=(6, 10))

        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 10))
        self._action_btn = ctk.CTkButton(
            btn_row,
            text="",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=ACCENT,
            hover_color="#2563eb",
            command=self._on_action_click,
        )
        self._action_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._btn_open_location = ctk.CTkButton(
            btn_row,
            text="Open file location",
            width=158,
            height=44,
            font=ctk.CTkFont(size=13),
            state="disabled",
            fg_color="#374151",
            hover_color="#4b5563",
            command=self._open_file_location,
        )
        self._btn_open_location.pack(side="left")

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
        # sticky=new: stretch horizontally but not vertically — avoids tall empty gaps inside cards
        win.grid(row=0, column=col, padx=6, sticky="new")

        ctk.CTkLabel(
            win,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f4f4f5",
        ).pack(anchor="w", padx=10, pady=(8, 0))
        ctk.CTkLabel(
            win,
            text=hint,
            font=ctk.CTkFont(size=10),
            text_color=MUTED,
            justify="left",
            wraplength=280,
        ).pack(anchor="w", padx=10, pady=(2, 4))

        path_var = ctk.StringVar(value="— none —")
        ctk.CTkLabel(
            win,
            textvariable=path_var,
            font=ctk.CTkFont(size=10),
            text_color="#a1a1aa",
            anchor="w",
            wraplength=280,
            justify="left",
            height=26,
        ).pack(fill="x", padx=10, pady=(0, 6))

        def browse() -> None:
            if key == "base":
                picks = list(filedialog.askopenfilenames(filetypes=FILE_TYPES))
                if picks:
                    self._set_base_paths(picks)
                return
            p = filedialog.askopenfilename(filetypes=FILE_TYPES)
            if p:
                self._set_slot_path(key, p)

        ctk.CTkButton(
            win,
            text="Choose file(s)…" if key == "base" else "Choose file…",
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#3f3f50",
            hover_color="#52525e",
            command=browse,
        ).pack(fill="x", padx=10, pady=(0, 8))

        setattr(self, f"_path_label_{key}", path_var)
        setattr(self, f"_card_{key}", win)
        return win

    def _set_base_paths(self, paths: list[str]) -> None:
        clean_paths: list[str] = []
        seen: set[str] = set()
        for raw in paths:
            p = os.path.normpath(str(raw))
            if not p or not os.path.isfile(p):
                continue
            ext = os.path.splitext(p)[1].lower()
            if ext not in SUPPORTED_INPUT_EXTS:
                continue
            uniq = os.path.normcase(os.path.abspath(p))
            if uniq in seen:
                continue
            seen.add(uniq)
            clean_paths.append(p)

        self._base_paths = clean_paths
        self._paths["base"] = clean_paths[0] if clean_paths else None
        var = getattr(self, "_path_label_base", None)
        if var:
            if not clean_paths:
                var.set("— none —")
            elif len(clean_paths) == 1:
                var.set(self._short_path(clean_paths[0], 34))
            else:
                first = self._short_path(clean_paths[0], 24)
                var.set(f"{len(clean_paths)} files selected · first: {first}")
        self._on_paths_changed()

    def _set_slot_path(self, key: str, path: str) -> None:
        if key == "base":
            self._set_base_paths([path])
            return
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
                key, paths = self._drop_queue.get_nowait()
                valid: list[str] = []
                for p in paths:
                    path = os.path.normpath(p)
                    if not path or not os.path.isfile(path):
                        continue
                    ext = os.path.splitext(path)[1].lower()
                    if ext not in SUPPORTED_INPUT_EXTS:
                        continue
                    valid.append(path)
                if not valid:
                    continue
                if key == "base":
                    self._set_base_paths(valid)
                else:
                    self._set_slot_path(key, valid[0])
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
                    dropped = [self._decode_drop_path(raw) for raw in files]
                    if dropped:
                        self._drop_queue.put_nowait((key, dropped))
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
        """Same folder + stem as base, extension .xlsx. If same as input, use stem_N.xlsx."""
        directory = os.path.dirname(os.path.abspath(base_path)) or os.getcwd()
        stem = os.path.splitext(os.path.basename(base_path))[0]
        candidate = os.path.join(directory, f"{stem}{OUTPUT_EXT}")

        def same_file(a: str, b: str) -> bool:
            return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))

        if not same_file(candidate, base_path):
            return candidate

        n = 1
        while True:
            alt = os.path.join(directory, f"{stem}_{n}{OUTPUT_EXT}")
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
            defaultextension=OUTPUT_EXT,
            filetypes=[("Excel", f"*{OUTPUT_EXT}")],
            initialdir=initial_dir if os.path.isdir(initial_dir) else None,
            initialfile=f"{initial_name}{OUTPUT_EXT}",
        )
        if p:
            self._set_output_from_full_path(p)

    def _set_filter_text_content(self, text: str) -> None:
        self._filter_keywords.set(text.strip())

    def _sync_filter_entry_scroll(self) -> None:
        def bump() -> None:
            try:
                e = self._filter_entry._entry
                e.update_idletasks()
                e.xview_moveto(0)
                lo, hi = e.xview()
                self._filter_hscroll.set(lo, hi)
            except (tk.TclError, ValueError):
                pass

        self.after_idle(bump)

    def _on_filter_toggle(self) -> None:
        if self._filter_export.get():
            self._filter_entry.configure(state="normal")
        else:
            self._filter_entry.configure(state="disabled")

    def _parse_filter_keywords(self) -> list[str]:
        raw = self._filter_keywords.get().replace("\n", ",")
        out: list[str] = []
        for part in raw.split(","):
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
                "-Filter by keywords is on — enter at least one comma-separated keyword or -keyword."
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
        return os.path.normpath(os.path.join(self._output_dir, f"{stem}{OUTPUT_EXT}"))

    def _prepare_base_path_for_run(self) -> tuple[str, int, str | None]:
        base_files = [p for p in self._base_paths if os.path.isfile(p)]
        if not base_files:
            b = self._paths.get("base")
            if b and os.path.isfile(b):
                base_files = [b]
        if not base_files:
            raise ValueError("Select at least one base file.")
        if len(base_files) == 1:
            return base_files[0], 1, None

        frames = [self._normalize_base_columns(load_table(p)) for p in base_files]
        merged = pd.concat(frames, ignore_index=True, sort=False)
        tmp = tempfile.NamedTemporaryFile(prefix="merge_studio_base_", suffix=".xlsx", delete=False)
        tmp_path = os.path.normpath(tmp.name)
        tmp.close()
        merged.to_excel(tmp_path, index=False)
        return tmp_path, len(base_files), tmp_path

    def _normalize_base_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map known aliases to fixed column names and coalesce duplicate columns."""
        out = df.copy()

        def norm_key(text: object) -> str:
            s = str(text).strip().lower()
            return "".join(ch for ch in s if ch.isalnum())

        rename_map: dict[str, str] = {}
        for col in out.columns:
            nk = norm_key(col)
            canonical = BASE_COLUMN_ALIASES.get(nk)
            if canonical:
                rename_map[col] = canonical
        if rename_map:
            out = out.rename(columns=rename_map)

        unique_cols: list[str] = []
        for col in out.columns:
            if col in unique_cols:
                continue
            dup = out.loc[:, out.columns == col]
            if dup.shape[1] > 1:
                filled = dup.replace(r"^\s*$", pd.NA, regex=True).bfill(axis=1).iloc[:, 0]
                out = out.drop(columns=col)
                out[col] = filled
            unique_cols.append(col)

        return out

    def _clear_log(self) -> None:
        try:
            self._log.delete("1.0", "end")
        except tk.TclError:
            pass

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

        self._clear_log()
        self._btn_open_location.configure(state="disabled")
        self._log_line("Running…")
        threading.Thread(target=work, daemon=True).start()

    def _do_format(self) -> None:
        b, base_n, temp_path = self._prepare_base_path_for_run()
        try:
            out = self._output_or_fail()
            kw = self._keyword_filter_for_run()
            n = run_format(
                b,
                out,
                table_name="Data",
                keyword_filter=kw,
                require_linkedin=self._require_linkedin.get(),
            )
            log_msg = f"Formatted {n} rows → {out}"
            if base_n > 1:
                log_msg = f"Merged {base_n} base files first.\n{log_msg}"
            self.after(
                0,
                lambda o=out, msg=log_msg: self._finish_success(o, msg),
            )
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def _do_merge_company(self) -> None:
        b, base_n, temp_path = self._prepare_base_path_for_run()
        c = self._paths["company"]
        if not c:
            raise ValueError("Need base + company files.")
        try:
            out = self._output_or_fail()
            kw = self._keyword_filter_for_run()
            rows, matched = run_merge_company(
                b,
                c,
                out,
                table_name="EnergyTech",
                keyword_filter=kw,
                require_linkedin=self._require_linkedin.get(),
            )
            log_msg = f"Rows: {rows}, websites matched: {matched}\n→ {out}"
            if base_n > 1:
                log_msg = f"Merged {base_n} base files first.\n{log_msg}"
            self.after(
                0,
                lambda o=out, msg=log_msg: self._finish_success(o, msg),
            )
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def _do_merge_emails(self) -> None:
        b, base_n, temp_path = self._prepare_base_path_for_run()
        e = self._paths["emails"]
        if not e:
            raise ValueError("Need base + email lookup files.")
        try:
            out = self._output_or_fail()
            kw = self._keyword_filter_for_run()
            rows, matched = run_merge_emails(
                b,
                e,
                out,
                table_name="WithEmails",
                keyword_filter=kw,
                require_linkedin=self._require_linkedin.get(),
            )
            log_msg = f"Rows: {rows}, emails matched: {matched}\n→ {out}"
            if base_n > 1:
                log_msg = f"Merged {base_n} base files first.\n{log_msg}"
            self.after(
                0,
                lambda o=out, msg=log_msg: self._finish_success(o, msg),
            )
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def _do_full(self) -> None:
        b, base_n, temp_path = self._prepare_base_path_for_run()
        c, e = self._paths["company"], self._paths["emails"]
        if not c or not e:
            raise ValueError("Need all three files for the full pipeline.")
        try:
            out = self._output_or_fail()
            kw = self._keyword_filter_for_run()
            rows, web_n, em_n = run_merge_full_pipeline(
                b,
                c,
                e,
                out,
                table_name="Merged",
                keyword_filter=kw,
                require_linkedin=self._require_linkedin.get(),
            )
            log_msg = f"Rows: {rows}, websites filled: {web_n}, emails matched: {em_n}\n→ {out}"
            if base_n > 1:
                log_msg = f"Merged {base_n} base files first.\n{log_msg}"
            self.after(
                0,
                lambda o=out, msg=log_msg: self._finish_success(o, msg),
            )
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = MergeDashboard()
    app.mainloop()


if __name__ == "__main__":
    main()
