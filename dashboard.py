"""
Dark-themed desktop UI: Merge workflows and CSV split chunks.
Run: python dashboard.py

Drag-and-drop (Windows): uses windnd; drop callbacks enqueue paths — the main Tk
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
    split_csv_chunks,
)

csvExt = ".csv"
xlsxExt = ".xlsx"
xlsExt = ".xls"
mergeFileTypes = [
    ("CSV or Excel", f"*{csvExt} *{xlsxExt} *{xlsExt}"),
    ("CSV", f"*{csvExt}"),
    ("Excel", f"*{xlsxExt} *{xlsExt}"),
    ("All files", "*.*"),
]
splitFileTypes = [("CSV", f"*{csvExt}"), ("All files", "*.*")]
supportedMergeInputExts = (csvExt, xlsxExt, xlsExt)
splitInputExts = (csvExt,)
mergeOutputExt = xlsxExt

baseColumnAliases = {
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

accentColor = "#3b82f6"
windowSurface = "#1e1e26"
windowBorder = "#3d3d4d"
appBackground = "#16161c"
mutedText = "#8b8b9a"

defaultFilterParts = (
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
defaultExportFilterKeywords = ", ".join(defaultFilterParts)

Action = Literal["none", "format", "company", "emails", "full"]


class StudioApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Merge and Split")
        self.geometry("1100x780")
        self.minsize(1000, 700)
        self.configure(fg_color=appBackground)

        self.paths: dict[str, str | None] = {"base": None, "company": None, "emails": None}
        self.basePaths: list[str] = []
        self.outputDir = os.getcwd()
        self.outputStem = ctk.StringVar(value="")
        self.filterExport = ctk.BooleanVar(value=False)
        self.requireLinkedin = ctk.BooleanVar(value=False)
        self.filterKeywords = ctk.StringVar(value="")
        self.action: Action = "none"
        self.dropQueue: queue.Queue[tuple[str, list[str]]] = queue.Queue()
        self.lastSuccessOutput: str | None = None

        self.splitInputPath: str | None = None
        self.splitOutputPattern = ctk.StringVar(value="")

        self.buildUi()
        self.after(50, self.pollDropQueue)
        self.setupDragDrop()

    def buildUi(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 6))

        ctk.CTkLabel(
            top,
            text="Merge and Split",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#f4f4f5",
        ).pack(anchor="w")
        ctk.CTkLabel(
            top,
            text="Drag files onto a card or use Choose… · One action button runs merge (if Base is set) or Split CSV · Clear resets all cards",
            font=ctk.CTkFont(size=12),
            text_color=mutedText,
        ).pack(anchor="w", pady=(2, 0))

        mainFrame = ctk.CTkFrame(self, fg_color="transparent")
        mainFrame.pack(fill="both", expand=True, padx=16, pady=(4, 8))
        self.buildMergeTab(mainFrame)

        self.logBox = ctk.CTkTextbox(
            self,
            height=160,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#0f0f14",
            border_color="#2d2d3a",
            text_color="#a1a1aa",
        )
        self.logBox.pack(fill="both", expand=False, padx=24, pady=(0, 16))

    def buildMergeTab(self, parent: ctk.CTkFrame) -> None:
        slots = ctk.CTkFrame(parent, fg_color="transparent")
        slots.pack(fill="x", padx=4, pady=(8, 8))
        slots.grid_columnconfigure(0, weight=1, uniform="slot")
        slots.grid_columnconfigure(1, weight=1, uniform="slot")
        slots.grid_columnconfigure(2, weight=1, uniform="slot")
        slots.grid_columnconfigure(3, weight=1, uniform="slot")

        cardWrap = 200
        self.smallWindow(
            slots,
            col=0,
            key="base",
            title="Base",
            hint="Main table(s) · CSV / Excel · drop or choose (multi-select)",
            wrapLength=cardWrap,
        )
        self.smallWindow(
            slots,
            col=1,
            key="company",
            title="Companies",
            hint="Company + website · drop or choose",
            wrapLength=cardWrap,
        )
        self.smallWindow(
            slots,
            col=2,
            key="emails",
            title="Emails",
            hint="LinkedIn + email / Mails · drop or choose",
            wrapLength=cardWrap,
        )
        self.smallWindow(
            slots,
            col=3,
            key="split",
            title="Split",
            hint="CSV to chunk · drop or choose (40 rows per file)",
            wrapLength=cardWrap,
        )

        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        outFr = ctk.CTkFrame(
            body, fg_color=windowSurface, corner_radius=10, border_width=1, border_color=windowBorder
        )
        outFr.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            outFr,
            text="Output",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e4e4e7",
        ).pack(anchor="w", padx=12, pady=(10, 2))
        self.outputHelperLabel = ctk.CTkLabel(
            outFr,
            text="Choose a Base file for Excel output and/or a CSV in Split for chunk filenames.",
            font=ctk.CTkFont(size=11),
            text_color=mutedText,
            wraplength=1000,
            justify="left",
        )
        self.mergeOutputBlock = ctk.CTkFrame(outFr, fg_color="transparent")
        ctk.CTkLabel(
            self.mergeOutputBlock,
            text="Merge → Excel (.xlsx)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#d4d4d8",
        ).pack(anchor="w", padx=12, pady=(4, 2))
        self.mergeOutputDirLabel = ctk.CTkLabel(
            self.mergeOutputBlock,
            text=self.formatDirLabel(self.outputDir),
            font=ctk.CTkFont(size=9),
            text_color="#5c5c6a",
            anchor="w",
            wraplength=1000,
            justify="left",
        )
        self.mergeOutputDirLabel.pack(anchor="w", padx=12, pady=(0, 6))
        mergeRow = ctk.CTkFrame(self.mergeOutputBlock, fg_color="transparent")
        mergeRow.pack(fill="x", padx=8, pady=(0, 8))
        self.mergeOutputEntry = ctk.CTkEntry(
            mergeRow,
            textvariable=self.outputStem,
            placeholder_text="File name (no extension)",
            height=36,
            font=ctk.CTkFont(size=12),
            border_color="#3f3f4e",
            fg_color="#14141a",
        )
        self.mergeOutputEntry.pack(side="left", fill="x", expand=True, padx=(4, 8))
        ctk.CTkButton(
            mergeRow,
            text="Browse…",
            width=90,
            height=36,
            fg_color="#3f3f50",
            hover_color="#52525e",
            command=self.browseMergeOutput,
        ).pack(side="right")

        self.splitOutputBlock = ctk.CTkFrame(outFr, fg_color="transparent")
        ctk.CTkLabel(
            self.splitOutputBlock,
            text="Split → CSV chunks (40 rows each)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#d4d4d8",
        ).pack(anchor="w", padx=12, pady=(4, 2))
        ctk.CTkLabel(
            self.splitOutputBlock,
            text='Pattern must include one {} (e.g. …\\people_{}.csv → people_1.csv, people_2.csv, …)',
            font=ctk.CTkFont(size=10),
            text_color=mutedText,
            wraplength=1000,
            justify="left",
        ).pack(anchor="w", padx=12, pady=(0, 4))
        self.splitPatternDirLabel = ctk.CTkLabel(
            self.splitOutputBlock,
            text="",
            font=ctk.CTkFont(size=9),
            text_color="#5c5c6a",
            anchor="w",
            wraplength=1000,
            justify="left",
        )
        self.splitPatternDirLabel.pack(anchor="w", padx=12, pady=(0, 4))
        splitProw = ctk.CTkFrame(self.splitOutputBlock, fg_color="transparent")
        splitProw.pack(fill="x", padx=8, pady=(0, 10))
        self.splitPatternEntry = ctk.CTkEntry(
            splitProw,
            textvariable=self.splitOutputPattern,
            height=36,
            font=ctk.CTkFont(size=12),
            border_color="#3f3f4e",
            fg_color="#14141a",
            text_color="#e4e4e7",
        )
        self.splitPatternEntry.pack(side="left", fill="x", expand=True, padx=(4, 8))
        self.splitPatternEntry.bind("<KeyRelease>", lambda _e: self.updateSplitPatternDirLabel())
        ctk.CTkButton(
            splitProw,
            text="Browse folder…",
            width=120,
            height=36,
            fg_color="#3f3f50",
            hover_color="#52525e",
            command=self.browseSplitOutputFolder,
        ).pack(side="right")

        filtFr = ctk.CTkFrame(
            body, fg_color=windowSurface, corner_radius=10, border_width=1, border_color=windowBorder
        )
        filtFr.pack(fill="x", pady=(0, 10))
        filtHeader = ctk.CTkFrame(filtFr, fg_color="transparent")
        filtHeader.pack(fill="x", padx=12, pady=(10, 2))
        self.mergeChkFilter = ctk.CTkCheckBox(
            filtHeader,
            text="Filter rows by keywords",
            variable=self.filterExport,
            font=ctk.CTkFont(size=12),
            command=self.onFilterToggle,
            fg_color=accentColor,
            hover_color="#2563eb",
        )
        self.mergeChkFilter.pack(side="right", anchor="e")
        self.mergeChkRequireLinkedin = ctk.CTkCheckBox(
            filtHeader,
            text="Drop rows without LinkedIn",
            variable=self.requireLinkedin,
            font=ctk.CTkFont(size=12),
            fg_color=accentColor,
            hover_color="#2563eb",
        )
        self.mergeChkRequireLinkedin.pack(side="right", anchor="e", padx=(0, 14))
        ctk.CTkLabel(
            filtHeader,
            text="Export filter (optional)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e4e4e7",
        ).pack(side="left", anchor="w")
        filterEntryRow = ctk.CTkFrame(filtFr, fg_color="transparent")
        filterEntryRow.pack(fill="x", padx=12, pady=(0, 10))
        self.mergeFilterEntry = ctk.CTkEntry(
            filterEntryRow,
            textvariable=self.filterKeywords,
            height=32,
            font=ctk.CTkFont(size=11),
            border_color="#3f3f4e",
            fg_color="#14141a",
            text_color="#e4e4e7",
            placeholder_text="Use keywords, or -keyword to exclude rows",
            state="disabled",
        )
        self.mergeFilterEntry.pack(side="top", fill="x")
        self.mergeFilterHscroll = ctk.CTkScrollbar(
            filterEntryRow,
            orientation="horizontal",
            height=12,
            fg_color="#2d2d3a",
            button_color="#4b4b5a",
            button_hover_color="#5c5c6a",
            command=lambda *a: self.mergeFilterEntry._entry.xview(*a),
        )
        self.mergeFilterEntry._entry.configure(xscrollcommand=self.mergeFilterHscroll.set)
        self.mergeFilterHscroll.pack(side="top", fill="x", pady=(4, 0))

        def filterEntryUpdateHscroll(_event: object | None = None) -> None:
            try:
                e = self.mergeFilterEntry._entry
                e.update_idletasks()
                lo, hi = e.xview()
                self.mergeFilterHscroll.set(lo, hi)
            except (tk.TclError, ValueError):
                pass

        self.mergeFilterEntry._entry.bind("<KeyRelease>", filterEntryUpdateHscroll)
        self.mergeFilterEntry._entry.bind("<ButtonRelease-1>", filterEntryUpdateHscroll)

        self.setFilterTextContent(defaultExportFilterKeywords)
        self.mergeFilterEntry.configure(state="disabled")
        self.syncFilterEntryScroll()

        self.mergeHint = ctk.CTkLabel(
            body,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=mutedText,
            wraplength=900,
            justify="center",
        )
        self.mergeHint.pack(anchor="center", pady=(6, 10))

        btnRow = ctk.CTkFrame(body, fg_color="transparent")
        btnRow.pack(fill="x", pady=(0, 6))
        self.mergeActionBtn = ctk.CTkButton(
            btnRow,
            text="",
            height=44,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=accentColor,
            hover_color="#2563eb",
            command=self.onPrimaryActionClick,
        )
        self.mergeActionBtn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.mergeOpenBtn = ctk.CTkButton(
            btnRow,
            text="Open file location",
            width=158,
            height=44,
            font=ctk.CTkFont(size=13),
            state="disabled",
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.openFileLocation,
        )
        self.mergeOpenBtn.pack(side="left", padx=(0, 8))
        self.clearSelectionsBtn = ctk.CTkButton(
            btnRow,
            text="Clear",
            width=88,
            height=44,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#4b5563",
            hover_color="#6b7280",
            command=self.clearAllFileSelections,
        )
        self.clearSelectionsBtn.pack(side="left")

        self.updateOutputSections()
        self.refreshMergeUi()

    def updateOutputSections(self) -> None:
        hasBase = bool(self.paths.get("base"))
        hasSplit = bool(self.splitInputPath and os.path.isfile(self.splitInputPath))
        self.outputHelperLabel.pack_forget()
        self.mergeOutputBlock.pack_forget()
        self.splitOutputBlock.pack_forget()
        if not hasBase and not hasSplit:
            self.outputHelperLabel.pack(anchor="w", padx=12, pady=(0, 10))
        if hasBase:
            self.mergeOutputBlock.pack(fill="x", padx=4, pady=(0, 6))
        if hasSplit:
            self.splitOutputBlock.pack(fill="x", padx=4, pady=(0, 10))

    def smallWindow(
        self,
        parent: ctk.CTkFrame,
        *,
        col: int,
        key: str,
        title: str,
        hint: str,
        wrapLength: int = 280,
    ) -> ctk.CTkFrame:
        win = ctk.CTkFrame(
            parent,
            fg_color=windowSurface,
            corner_radius=10,
            border_width=1,
            border_color=windowBorder,
        )
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
            text_color=mutedText,
            justify="left",
            wraplength=wrapLength,
        ).pack(anchor="w", padx=10, pady=(2, 4))

        pathVar = ctk.StringVar(value="— none —")
        ctk.CTkLabel(
            win,
            textvariable=pathVar,
            font=ctk.CTkFont(size=10),
            text_color="#a1a1aa",
            anchor="w",
            wraplength=wrapLength,
            justify="left",
            height=26,
        ).pack(fill="x", padx=10, pady=(0, 6))

        def browse() -> None:
            if key == "base":
                picks = list(filedialog.askopenfilenames(filetypes=mergeFileTypes))
                if picks:
                    self.setBasePaths(picks)
                return
            if key == "split":
                p = filedialog.askopenfilename(filetypes=splitFileTypes)
                if p:
                    self.setSplitInputPath(p)
                return
            p = filedialog.askopenfilename(filetypes=mergeFileTypes)
            if p:
                self.setSlotPath(key, p)

        if key == "base":
            chooseLabel = "Choose file(s)…"
        elif key == "split":
            chooseLabel = "Choose CSV…"
        else:
            chooseLabel = "Choose file…"
        ctk.CTkButton(
            win,
            text=chooseLabel,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#3f3f50",
            hover_color="#52525e",
            command=browse,
        ).pack(fill="x", padx=10, pady=(0, 8))

        setattr(self, f"pathLabel{key.title()}", pathVar)
        setattr(self, f"mergeCard{key.title()}", win)
        return win

    def setSplitInputPath(self, path: str) -> None:
        path = os.path.normpath(path)
        if not os.path.isfile(path) or os.path.splitext(path)[1].lower() != csvExt:
            return
        self.splitInputPath = path
        var = getattr(self, "pathLabelSplit", None)
        if var:
            var.set(self.shortPath(path, 34))
        directory = os.path.dirname(os.path.abspath(path))
        stem = os.path.splitext(os.path.basename(path))[0]
        pattern = os.path.join(directory, f"{stem}_{{}}.csv")
        self.splitOutputPattern.set(pattern)
        self.updateSplitPatternDirLabel()
        self.refreshMergeUi()

    def updateSplitPatternDirLabel(self) -> None:
        raw = self.splitOutputPattern.get().strip()
        if not raw:
            self.splitPatternDirLabel.configure(text="")
            return
        directory = os.path.dirname(os.path.normpath(raw.replace("{}", "0")))
        if directory:
            self.splitPatternDirLabel.configure(text=self.formatDirLabel(directory))
        else:
            self.splitPatternDirLabel.configure(text="Folder: (same as pattern path)")

    def primaryRunKind(self) -> str | None:
        if self.paths.get("base"):
            return "merge"
        if self.splitInputPath and os.path.isfile(self.splitInputPath):
            return "split"
        return None

    def browseSplitOutputFolder(self) -> None:
        init = self.splitInputPath
        initialDir = os.path.dirname(os.path.abspath(init)) if init else self.outputDir
        if not initialDir or not os.path.isdir(initialDir):
            initialDir = os.getcwd()
        folder = filedialog.askdirectory(initialdir=initialDir)
        if not folder:
            return
        if init:
            stem = os.path.splitext(os.path.basename(init))[0]
        else:
            rawPat = self.splitOutputPattern.get().strip()
            stem = os.path.splitext(os.path.basename(rawPat))[0] if rawPat else "output"
            stem = stem.replace("{}", "").strip("_").strip() or "output"
        pattern = os.path.join(os.path.normpath(folder), f"{stem}_{{}}.csv")
        self.splitOutputPattern.set(pattern)
        self.updateSplitPatternDirLabel()
        self.refreshMergeUi()

    def setBasePaths(self, paths: list[str]) -> None:
        cleanPaths: list[str] = []
        seen: set[str] = set()
        for raw in paths:
            p = os.path.normpath(str(raw))
            if not p or not os.path.isfile(p):
                continue
            ext = os.path.splitext(p)[1].lower()
            if ext not in supportedMergeInputExts:
                continue
            uniq = os.path.normcase(os.path.abspath(p))
            if uniq in seen:
                continue
            seen.add(uniq)
            cleanPaths.append(p)

        self.basePaths = cleanPaths
        self.paths["base"] = cleanPaths[0] if cleanPaths else None
        var = getattr(self, "pathLabelBase", None)
        if var:
            if not cleanPaths:
                var.set("— none —")
            elif len(cleanPaths) == 1:
                var.set(self.shortPath(cleanPaths[0], 34))
            else:
                first = self.shortPath(cleanPaths[0], 24)
                var.set(f"{len(cleanPaths)} files selected · first: {first}")
        self.onPathsChanged()

    def setSlotPath(self, key: str, path: str) -> None:
        if key == "base":
            self.setBasePaths([path])
            return
        self.paths[key] = path
        var = getattr(self, f"pathLabel{key.title()}", None)
        if var:
            var.set(self.shortPath(path, 34))
        self.onPathsChanged()

    def decodeDropPath(self, raw: object) -> str:
        if isinstance(raw, bytes):
            for enc in ("utf-8", "mbcs"):
                try:
                    return raw.decode(enc).strip("\0").strip()
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace").strip("\0").strip()
        return str(raw).strip("\0").strip()

    def pollDropQueue(self) -> None:
        try:
            while True:
                key, paths = self.dropQueue.get_nowait()
                valid: list[str] = []
                for p in paths:
                    path = os.path.normpath(p)
                    if not path or not os.path.isfile(path):
                        continue
                    ext = os.path.splitext(path)[1].lower()
                    if key == "split":
                        if ext in splitInputExts:
                            valid.append(path)
                    else:
                        if ext in supportedMergeInputExts:
                            valid.append(path)
                if not valid:
                    continue
                if key == "split":
                    self.setSplitInputPath(valid[0])
                elif key == "base":
                    self.setBasePaths(valid)
                else:
                    self.setSlotPath(key, valid[0])
        except queue.Empty:
            pass
        self.after(80, self.pollDropQueue)

    def setupDragDrop(self) -> None:
        try:
            import windnd  # type: ignore
        except ImportError:
            return

        def makeHandler(key: str):
            def onDrop(files) -> None:
                if not files:
                    return
                try:
                    dropped = [self.decodeDropPath(raw) for raw in files]
                    if dropped:
                        self.dropQueue.put_nowait((key, dropped))
                except Exception:
                    pass

            return onDrop

        for key in ("base", "company", "emails", "split"):
            card = getattr(self, f"mergeCard{key.title()}", None)
            if card is None:
                continue
            try:
                windnd.hook_dropfiles(card, func=makeHandler(key))
            except Exception:
                pass

    def shortPath(self, p: str, maxLen: int) -> str:
        p = os.path.normpath(p)
        name = os.path.basename(p)
        if len(name) <= maxLen:
            return name
        return name[: maxLen - 1] + "…"

    def formatDirLabel(self, directory: str) -> str:
        d = os.path.normpath(directory or os.getcwd())
        prefix = "Folder: "
        cap = 90
        rest = d
        if len(prefix) + len(rest) > cap:
            rest = "…" + rest[-(cap - len(prefix) - 1) :]
        return prefix + rest

    def updateMergeDirLabel(self) -> None:
        self.mergeOutputDirLabel.configure(text=self.formatDirLabel(self.outputDir))

    def setOutputFromFullPath(self, fullPath: str) -> None:
        fullPath = os.path.normpath(os.path.abspath(fullPath))
        self.outputDir = os.path.dirname(fullPath) or os.getcwd()
        stem = os.path.splitext(os.path.basename(fullPath))[0]
        self.outputStem.set(stem)
        self.updateMergeDirLabel()

    def onPathsChanged(self) -> None:
        self.suggestMergeOutput()
        self.refreshMergeUi()

    def defaultMergeOutputXlsx(self, basePath: str) -> str:
        directory = os.path.dirname(os.path.abspath(basePath)) or os.getcwd()
        stem = os.path.splitext(os.path.basename(basePath))[0]
        candidate = os.path.join(directory, f"{stem}{mergeOutputExt}")

        def sameFile(a: str, b: str) -> bool:
            return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))

        if not sameFile(candidate, basePath):
            return candidate

        n = 1
        while True:
            alt = os.path.join(directory, f"{stem}_{n}{mergeOutputExt}")
            if sameFile(alt, basePath):
                n += 1
                continue
            if not os.path.isfile(alt):
                return alt
            n += 1

    def suggestMergeOutput(self) -> None:
        base = self.paths.get("base")
        if not base:
            return
        if self.outputStem.get().strip():
            return
        suggested = self.defaultMergeOutputXlsx(base)
        self.setOutputFromFullPath(suggested)

    def browseMergeOutput(self) -> None:
        b = self.paths.get("base")
        initialDir = self.outputDir
        if not initialDir or not os.path.isdir(initialDir):
            initialDir = os.path.dirname(os.path.abspath(b)) if b else os.getcwd()
        initialName = self.outputStem.get().strip() or "output"
        p = filedialog.asksaveasfilename(
            defaultextension=mergeOutputExt,
            filetypes=[("Excel", f"*{mergeOutputExt}")],
            initialdir=initialDir if os.path.isdir(initialDir) else None,
            initialfile=f"{initialName}{mergeOutputExt}",
        )
        if p:
            self.setOutputFromFullPath(p)

    def setFilterTextContent(self, text: str) -> None:
        self.filterKeywords.set(text.strip())

    def syncFilterEntryScroll(self) -> None:
        def bump() -> None:
            try:
                e = self.mergeFilterEntry._entry
                e.update_idletasks()
                e.xview_moveto(0)
                lo, hi = e.xview()
                self.mergeFilterHscroll.set(lo, hi)
            except (tk.TclError, ValueError):
                pass

        self.after_idle(bump)

    def onFilterToggle(self) -> None:
        if self.filterExport.get():
            self.mergeFilterEntry.configure(state="normal")
        else:
            self.mergeFilterEntry.configure(state="disabled")

    def parseFilterKeywords(self) -> list[str]:
        raw = self.filterKeywords.get().replace("\n", ",")
        out: list[str] = []
        for part in raw.split(","):
            t = part.strip()
            if t:
                out.append(t)
        return out

    def keywordFilterForRun(self) -> list[str] | None:
        if not self.filterExport.get():
            return None
        kws = self.parseFilterKeywords()
        if not kws:
            raise ValueError(
                "Filter by keywords is on — enter at least one comma-separated keyword or -keyword."
            )
        return kws

    def resolveMergeAction(self) -> Action:
        b, c, e = self.paths["base"], self.paths["company"], self.paths["emails"]
        if not b:
            return "none"
        if c and e:
            return "full"
        if c:
            return "company"
        if e:
            return "emails"
        return "format"

    def refreshMergeUi(self) -> None:
        self.action = self.resolveMergeAction()
        self.updateOutputSections()
        kind = self.primaryRunKind()
        splitSideNote = ""
        if self.splitInputPath and os.path.isfile(self.splitInputPath) and kind == "merge":
            splitSideNote = " Split is ready too — clear Base to run Split from the same button."

        if kind == "merge":
            if self.action == "format":
                self.mergeActionBtn.configure(state="normal", text="Format to Excel")
                self.mergeHint.configure(
                    text="Only the base file is set — output will be a styled Excel copy (same data, formatted table & links)."
                    + splitSideNote
                )
            elif self.action == "company":
                self.mergeActionBtn.configure(state="normal", text="Merge company websites")
                self.mergeHint.configure(
                    text="Base + company lookup — Website column will be filled by matching company names."
                    + splitSideNote
                )
            elif self.action == "emails":
                self.mergeActionBtn.configure(state="normal", text="Merge person emails")
                self.mergeHint.configure(
                    text="Base + email lookup — Email column will be filled by matching LinkedIn URLs."
                    + splitSideNote
                )
            else:
                self.mergeActionBtn.configure(state="normal", text="Merge websites & emails")
                self.mergeHint.configure(
                    text="All three files set — company websites are merged first, then emails by LinkedIn."
                    + splitSideNote
                )
        elif kind == "split":
            self.mergeActionBtn.configure(state="normal", text="Split CSV")
            self.mergeHint.configure(
                text="Writes chunk files using the pattern in Output (one {} for the chunk index, 40 data rows per file plus header)."
            )
        else:
            self.mergeActionBtn.configure(state="disabled", text="Select Base or Split CSV")
            self.mergeHint.configure(
                text="Add a Base file for Excel merge/format, and/or choose a CSV in Split — outputs appear in the Output card when you select files."
            )

    def mergeOutputOrFail(self) -> str:
        stem = self.outputStem.get().strip()
        stem = stem.replace("\\", "").replace("/", "").strip()
        stem = os.path.basename(stem) if stem else ""
        if not stem:
            raise ValueError("Enter an output file name (or use Browse…).")
        base = self.paths.get("base")
        if not self.outputDir or not os.path.isdir(self.outputDir):
            self.outputDir = os.path.dirname(os.path.abspath(base)) if base else os.getcwd()
            self.updateMergeDirLabel()
        if not os.path.isdir(self.outputDir):
            raise ValueError(f"Output folder is not valid: {self.outputDir}")
        return os.path.normpath(os.path.join(self.outputDir, f"{stem}{mergeOutputExt}"))

    def prepareBasePathForRun(self) -> tuple[str, int, str | None]:
        baseFiles = [p for p in self.basePaths if os.path.isfile(p)]
        if not baseFiles:
            b = self.paths.get("base")
            if b and os.path.isfile(b):
                baseFiles = [b]
        if not baseFiles:
            raise ValueError("Select at least one base file.")
        if len(baseFiles) == 1:
            return baseFiles[0], 1, None

        frames = [self.normalizeBaseColumns(load_table(p)) for p in baseFiles]
        merged = pd.concat(frames, ignore_index=True, sort=False)
        tmp = tempfile.NamedTemporaryFile(prefix="merge_studio_base_", suffix=".xlsx", delete=False)
        tmpPath = os.path.normpath(tmp.name)
        tmp.close()
        merged.to_excel(tmpPath, index=False)
        return tmpPath, len(baseFiles), tmpPath

    def normalizeBaseColumns(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()

        def normKey(text: object) -> str:
            s = str(text).strip().lower()
            return "".join(ch for ch in s if ch.isalnum())

        renameMap: dict[str, str] = {}
        for col in out.columns:
            nk = normKey(col)
            canonical = baseColumnAliases.get(nk)
            if canonical:
                renameMap[col] = canonical
        if renameMap:
            out = out.rename(columns=renameMap)

        uniqueCols: list[str] = []
        for col in out.columns:
            if col in uniqueCols:
                continue
            dup = out.loc[:, out.columns == col]
            if dup.shape[1] > 1:
                filled = dup.replace(r"^\s*$", pd.NA, regex=True).bfill(axis=1).iloc[:, 0]
                out = out.drop(columns=col)
                out[col] = filled
            uniqueCols.append(col)

        return out

    def clearLog(self) -> None:
        try:
            self.logBox.delete("1.0", "end")
        except tk.TclError:
            pass

    def logLine(self, msg: str) -> None:
        self.logBox.insert("end", msg + "\n")
        self.logBox.see("end")

    def finishSuccess(self, outputPath: str, logMsg: str) -> None:
        self.logLine(logMsg)
        self.lastSuccessOutput = os.path.normpath(outputPath)
        if os.path.isfile(self.lastSuccessOutput):
            if self.lastSuccessOutput.lower().endswith(mergeOutputExt):
                self.setOutputFromFullPath(self.lastSuccessOutput)
            self.mergeOpenBtn.configure(state="normal")

    def openFileLocation(self) -> None:
        path = self.lastSuccessOutput
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

    def onPrimaryActionClick(self) -> None:
        if self.paths.get("base"):
            self.onMergeActionClick()
        elif self.splitInputPath and os.path.isfile(self.splitInputPath):
            self.runAsync(self.doSplitCsv)

    def onMergeActionClick(self) -> None:
        act = self.action
        if act == "none":
            return
        if act == "format":
            self.runAsync(self.doFormat)
        elif act == "company":
            self.runAsync(self.doMergeCompany)
        elif act == "emails":
            self.runAsync(self.doMergeEmails)
        else:
            self.runAsync(self.doFullMerge)

    def clearAllFileSelections(self) -> None:
        self.paths = {"base": None, "company": None, "emails": None}
        self.basePaths = []
        self.splitInputPath = None
        for key in ("base", "company", "emails", "split"):
            var = getattr(self, f"pathLabel{key.title()}", None)
            if var:
                var.set("— none —")
        self.outputStem.set("")
        self.splitOutputPattern.set("")
        self.outputDir = os.getcwd()
        self.updateMergeDirLabel()
        self.updateSplitPatternDirLabel()
        self.lastSuccessOutput = None
        self.mergeOpenBtn.configure(state="disabled")
        self.onPathsChanged()

    def runAsync(self, fn) -> None:
        def work() -> None:
            try:
                fn()
            except Exception as ex:
                err = f"{ex}\n{traceback.format_exc()}"
                self.after(0, lambda m=err: self.logLine(m))
            finally:
                self.after(0, lambda: self.clearSelectionsBtn.configure(state="normal"))

        self.clearLog()
        self.mergeOpenBtn.configure(state="disabled")
        self.clearSelectionsBtn.configure(state="disabled")
        self.logLine("Running…")
        threading.Thread(target=work, daemon=True).start()

    def doFormat(self) -> None:
        b, baseN, tempPath = self.prepareBasePathForRun()
        try:
            out = self.mergeOutputOrFail()
            kw = self.keywordFilterForRun()
            n = run_format(
                b,
                out,
                table_name="Data",
                keyword_filter=kw,
                require_linkedin=self.requireLinkedin.get(),
            )
            logMsg = f"Formatted {n} rows → {out}"
            if baseN > 1:
                logMsg = f"Merged {baseN} base files first.\n{logMsg}"
            self.after(
                0,
                lambda o=out, msg=logMsg: self.finishSuccess(o, msg),
            )
        finally:
            if tempPath:
                try:
                    os.unlink(tempPath)
                except OSError:
                    pass

    def doMergeCompany(self) -> None:
        b, baseN, tempPath = self.prepareBasePathForRun()
        c = self.paths["company"]
        if not c:
            raise ValueError("Need base + company files.")
        try:
            out = self.mergeOutputOrFail()
            kw = self.keywordFilterForRun()
            rows, matched = run_merge_company(
                b,
                c,
                out,
                table_name="EnergyTech",
                keyword_filter=kw,
                require_linkedin=self.requireLinkedin.get(),
            )
            logMsg = f"Rows: {rows}, websites matched: {matched}\n→ {out}"
            if baseN > 1:
                logMsg = f"Merged {baseN} base files first.\n{logMsg}"
            self.after(
                0,
                lambda o=out, msg=logMsg: self.finishSuccess(o, msg),
            )
        finally:
            if tempPath:
                try:
                    os.unlink(tempPath)
                except OSError:
                    pass

    def doMergeEmails(self) -> None:
        b, baseN, tempPath = self.prepareBasePathForRun()
        e = self.paths["emails"]
        if not e:
            raise ValueError("Need base + email lookup files.")
        try:
            out = self.mergeOutputOrFail()
            kw = self.keywordFilterForRun()
            rows, matched = run_merge_emails(
                b,
                e,
                out,
                table_name="WithEmails",
                keyword_filter=kw,
                require_linkedin=self.requireLinkedin.get(),
            )
            logMsg = f"Rows: {rows}, emails matched: {matched}\n→ {out}"
            if baseN > 1:
                logMsg = f"Merged {baseN} base files first.\n{logMsg}"
            self.after(
                0,
                lambda o=out, msg=logMsg: self.finishSuccess(o, msg),
            )
        finally:
            if tempPath:
                try:
                    os.unlink(tempPath)
                except OSError:
                    pass

    def doFullMerge(self) -> None:
        b, baseN, tempPath = self.prepareBasePathForRun()
        c, e = self.paths["company"], self.paths["emails"]
        if not c or not e:
            raise ValueError("Need all three files for the full pipeline.")
        try:
            out = self.mergeOutputOrFail()
            kw = self.keywordFilterForRun()
            rows, webN, emN = run_merge_full_pipeline(
                b,
                c,
                e,
                out,
                table_name="Merged",
                keyword_filter=kw,
                require_linkedin=self.requireLinkedin.get(),
            )
            logMsg = f"Rows: {rows}, websites filled: {webN}, emails matched: {emN}\n→ {out}"
            if baseN > 1:
                logMsg = f"Merged {baseN} base files first.\n{logMsg}"
            self.after(
                0,
                lambda o=out, msg=logMsg: self.finishSuccess(o, msg),
            )
        finally:
            if tempPath:
                try:
                    os.unlink(tempPath)
                except OSError:
                    pass

    def doSplitCsv(self) -> None:
        inp = self.splitInputPath
        if not inp or not os.path.isfile(inp):
            raise ValueError("Select a CSV file to split.")
        pattern = self.splitOutputPattern.get().strip()
        if pattern.count("{}") != 1:
            raise ValueError(
                "Output pattern must contain exactly one '{}' for the chunk number "
                "(example: C:\\\\data\\\\people_{}.csv)."
            )
        created = split_csv_chunks(inp, pattern, rows_per_file=40)
        if not created:
            raise ValueError("No output files were created.")
        first = created[0]
        logMsg = "\n".join(f"Created: {p}" for p in created)
        self.after(0, lambda f=first, m=logMsg: self.finishSuccess(f, m))


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = StudioApp()
    app.mainloop()


if __name__ == "__main__":
    main()
