"""
generate_booklet.py
===================
Generates a weekly A5 chess puzzle booklet in LaTeX.

Layout (mirrors the reference document):
  - Title page: title, week number, author name
  - 10 puzzle pages (one per page), each with:
      * section heading: "Puzzle N  <difficulty>"
      * game/source line
      * chessboard (chessboard package, showmover=true)
      * task line: "Mate in N moves." or "Find the best move."
      * gridpages{1} for note-taking space
  - Solutions page: numbered table

Difficulty selection:
  4 easy      -> Mate in 2
  3 medium    -> Mate in 3
  2 hard      -> Mate in 4
  1 grandmaster -> ELO 2000+

Seed = year * 100 + week  ->  reproducible, changes every week.

Usage:
  python generate_booklet.py [puzzles.json] [week] [year] [author] [output.tex]

Defaults:
  puzzles.json  -> puzzles.json
  week          -> current ISO week
  year          -> current year
  author        -> "Marco Keller"
  output.tex    -> booklet_weekNN.tex
"""

import json
import random
import sys
import datetime
from pathlib import Path


# ─────────────────────────── puzzle selection ──────────────────────────────

def select_puzzles(puzzles: list[dict], seed: int) -> list[dict]:
    rng = random.Random()
    # if you want to be sure that the booklet stay the same for the wohle week activete the seed, every week it generats a new seed and even if you rerun this program the output will stay the same
    #rng = random.Random(seed)

    m2  = [p for p in puzzles if p["category"] == "Mate in 2"]
    m3  = [p for p in puzzles if p["category"] == "Mate in 3"]
    m4  = [p for p in puzzles if p["category"] == "Mate in 4"]
    gm  = [p for p in puzzles if p["category"] == "ELO 2000+"]

    return (
        rng.sample(m2, 4) +
        rng.sample(m3, 3) +
        rng.sample(m4, 2) +
        rng.sample(gm, 1)
    )


# ─────────────────────────── LaTeX helpers ─────────────────────────────────

def tex(s: str) -> str:
    """Escape special LaTeX characters."""
    if not s:
        return ""
    for char, repl in [
        ("\\", r"\textbackslash{}"),
        ("&",  r"\&"),
        ("%",  r"\%"),
        ("$",  r"\$"),
        ("#",  r"\#"),
        ("_",  r"\_"),
        ("{",  r"\{"),
        ("}",  r"\}"),
        ("~",  r"\textasciitilde{}"),
        ("^",  r"\^{}"),
    ]:
        s = s.replace(char, repl)
    return s


def difficulty_label(category: str) -> str:
    return {
        "Mate in 2": "Mate in 2",
        "Mate in 3": "Mate in 3",
        "Mate in 4": "Mate in 4",
        "ELO 2000+": "Grandmaster",
    }.get(category, category)


def task_line(p: dict) -> str:
    cat  = p["category"]
    note = p.get("note") or ""
    # If source file already has a note like "White mates in 2.", use it
    if note:
        return tex(note)
    if cat == "Mate in 2":
        return "Mate in 2 moves."
    if cat == "Mate in 3":
        return "Mate in 3 moves."
    if cat == "Mate in 4":
        return "Mate in 4 moves."
    return "Find the best move."


def source_line(p: dict) -> str:
    """
    Build the small italic game attribution line.
    Examples:
      Rotlevi vs Suchting, Vienna, 1911
      FM Scarlet_dawn vs CM Kingscrusher, Lichess  (ELO 2067)
    """
    parts = []
    if p.get("white") and p.get("black"):
        parts.append(f"{tex(p['white'])} vs {tex(p['black'])}")
    elif p.get("white"):
        parts.append(tex(p["white"]))

    location = tex(p.get("location") or "")
    year     = str(p["year"]) if p.get("year") else ""

    if location and year:
        parts.append(f"{location}, {year}")
    elif location:
        parts.append(location)
    elif year:
        parts.append(year)

    if p["source"] == "elo2000":
        parts.append("Lichess")
        if p.get("rating"):
            parts.append(f"(ELO~{p['rating']})")

    return ", ".join(parts) if parts else ""


def solution_tex(p: dict) -> str:
    """Format solution for the solutions table."""
    sol = p.get("solution_display") or p.get("moves") or "—"
    # Already in displayable form; just escape underscores etc.
    return tex(sol)


# ─────────────────────────── document sections ─────────────────────────────

def make_preamble(week: int, year: int, author: str) -> str:
    return r"""\documentclass[11pt, a5paper]{article}

% ── packages ──────────────────────────────────────────────────────────────
\usepackage[a5paper, top=20mm, bottom=22mm, left=16mm, right=16mm]{geometry}
\usepackage{chessboard}
\usepackage{skak}
\usepackage{fancyhdr}
\usepackage{booktabs}
\usepackage[
    pattern=std,
    majorcolor=black!25,
    minorcolor=black!25,
    patternsize=4.5mm,
    fullpage,
    manualactivation
]{gridpapers}

% ── chessboard settings ───────────────────────────────────────────────────
\setchessboard{
  showmover     = true,
  boardfontsize = 20pt,
  labelfont     = \small\sffamily,
}

% ── spacing ───────────────────────────────────────────────────────────────
\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}

\begin{document}
"""


def make_title_page(week: int, year: int, author: str) -> str:
    return r"""
% ══════════════════════════════════════════════════════
%  TITLE PAGE
% ══════════════════════════════════════════════════════
\thispagestyle{empty}
\vspace*{40mm}

\begin{center}
  {\LARGE\bfseries\sffamily Chess Booklet}\\[4mm]
  """ + \
f"{{\\large\\sffamily Week {week} / {year}}}\\\\[12mm]\n" + \
r"""
\end{center}

\clearpage
"""


def make_puzzle_page(num: int, p: dict) -> str:
    diff   = difficulty_label(p["category"])
    src    = source_line(p)
    task   = task_line(p)
    fen    = p["fen"]

    lines = []
    lines.append(f"% {'═'*52}")
    lines.append(f"%  PUZZLE {num}")
    lines.append(f"% {'═'*52}")
    lines.append(f"\\section*{{Puzzle {num} \\hfill \\normalfont\\normalsize {diff}}}")
    lines.append("")
    if src:
        lines.append(f"{{\\small {src}}}")
        lines.append("")
    lines.append("\\bigskip")
    lines.append("\\begin{center}")
    lines.append(f"\\chessboard[setfen={{{fen}}}]")
    lines.append("\\end{center}")
    lines.append("")
    lines.append(f"\\medskip")
    lines.append(f"{task}")
    lines.append("")
    lines.append("\\gridpages{1}")

    return "\n".join(lines)


def make_solutions_page(puzzles: list[dict]) -> str:
    lines = []
    lines.append("% ══════════════════════════════════════════════════════")
    lines.append("%  SOLUTIONS")
    lines.append("% ══════════════════════════════════════════════════════")
    lines.append(r"\label{solutions}")
    lines.append(r"\section*{Solutions}")
    lines.append("")
    lines.append(r"\bigskip")
    lines.append(r"\begin{tabular}{@{} r l @{}}")
    lines.append(r"\toprule")
    lines.append(r"\textbf{N.} & \textbf{Solution} \\")
    lines.append(r"\midrule")

    for i, p in enumerate(puzzles, 1):
        sol = solution_tex(p)
        # add a separator line between difficulty groups
        if i in (5, 8, 10):
            lines.append(r"\midrule")
        lines.append(f" {i:2d} & {sol} \\\\[3pt]")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    return "\n".join(lines)


# ────────────────────────────── assembler ──────────────────────────────────

def build_document(puzzles: list[dict], week: int, year: int, author: str) -> str:
    parts = []
    parts.append(make_preamble(week, year, author))
    parts.append(make_title_page(week, year, author))

    for i, p in enumerate(puzzles, 1):
        parts.append(make_puzzle_page(i, p))
        parts.append("\n\\clearpage\n")

    parts.append(make_solutions_page(puzzles))
    parts.append("\n\\end{document}\n")

    return "\n".join(parts)


# ──────────────────────────────── main ────────────────────────────────────

def main():
    args = sys.argv[1:]

    json_path = Path(args[0]) if len(args) > 0 else Path("puzzles.json")
    today     = datetime.date.today()
    iso       = today.isocalendar()

    week   = int(args[1]) if len(args) > 1 else iso[1]
    year   = int(args[2]) if len(args) > 2 else iso[0]
    author = args[3]      if len(args) > 3 else "Marco Keller"
    out    = Path(args[4]) if len(args) > 4 else Path(f"booklet_week{week:02d}.tex")

    seed = year * 100 + week

    data    = json.loads(json_path.read_text(encoding="utf-8"))
    puzzles_all = data["puzzles"]
    selected    = select_puzzles(puzzles_all, seed)

    print(f"Chess Booklet Generator")
    print(f"Week {week} / {year}  —  seed {seed}")
    print()
    labels = ["Easy"] * 4 + ["Medium"] * 3 + ["Hard"] * 2 + ["Grandmaster"]
    for i, (p, lbl) in enumerate(zip(selected, labels), 1):
        white = p.get("white") or "?"
        black = p.get("black") or "?"
        yr    = p.get("year") or p.get("rating") or "–"
        print(f"  {i:2d}. [{lbl:<12}] {white} vs {black} ({yr})")

    doc = build_document(selected, week, year, author)
    out.write_text(doc, encoding="utf-8")
    print(f"\n  ✓  Written: {out}")
    print(f"     Compile: pdflatex {out}  (run twice)")


if __name__ == "__main__":
    main()