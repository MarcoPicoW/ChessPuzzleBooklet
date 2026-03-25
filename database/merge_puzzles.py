"""
merge_puzzles.py
================
Legge tutti i file di puzzle scacchistici e produce un unico file JSON unificato.

File sorgente supportati
------------------------
  m8n2.txt        – Mate in 2  (formato: "Giocatore vs Giocatore, Luogo, Anno")
  m8n3.txt        – Mate in 3
  m8n4.txt        – Mate in 4
  puzzle_rush.txt – Puzzle Rush Lichess (FEN + soluzione, sezioni segnate --------N)
  puzzle_over_2000_ELO.txt – Puzzle ELO 2000+ con sezioni pt.i/ii… e lettere a)/b)/c)

CSV Lichess (opzionale)
-----------------------
  lichess_db_puzzle_reduced.csv  colonne: PuzzleId,FEN,Moves,Rating,Themes
  Passare il percorso come secondo argomento: python merge_puzzles.py . puzzle.csv

Uso
---
  python merge_puzzles.py [cartella_input] [file_csv_lichess] [output.json]

  Valori predefiniti:
    cartella_input  = . (directory corrente)
    file_csv_lichess= (nessuno)
    output.json     = puzzles.json

Schema JSON prodotto
--------------------
{
  "id":               "m2_0042",          # sorgente + indice progressivo
  "source":           "m8n2",             # nome file senza estensione
  "category":         "Mate in 2",        # Mate in 2/3/4 | Puzzle Rush | ELO 2000+ | Lichess DB
  "rating":           null,               # intero o null
  "themes":           ["mateIn2"],        # lista stringhe
  "fen":              "r2qkb1r/...",
  "moves":            "Nf6+ gxf6 Bxf7#", # mosse grezze (UCI o SAN senza numerazione)
  "solution_display": "1. Nf6+ gxf6 2. Bxf7#",  # pronto per LaTeX
  "white":            "Paul Morphy",      # null se sconosciuto
  "black":            "Duke Isouard",
  "location":        "Paris",
  "year":             1858,               # intero o null
  "note":             null,               # es. "White mates in 2."
  "section":          null,               # es. "pt. ii, b)"
  "color_to_move":    "white"             # "white" | "black"
}
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# ─────────────────────────────── struttura dati ────────────────────────────

@dataclass
class Puzzle:
    id: str = ""
    source: str = ""
    category: str = ""
    rating: Optional[int] = None
    themes: list = field(default_factory=list)
    fen: str = ""
    moves: str = ""
    solution_display: str = ""
    white: Optional[str] = None
    black: Optional[str] = None
    location: Optional[str] = None
    year: Optional[int] = None
    note: Optional[str] = None
    section: Optional[str] = None
    color_to_move: str = "white"

    def to_dict(self) -> dict:
        return asdict(self)


# ────────────────────────────── utilità comuni ─────────────────────────────

FEN_RE = re.compile(
    r"^[pnbrqkPNBRQK1-8]{1,8}(?:/[pnbrqkPNBRQK1-8]{1,8}){7}"
    r"\s+([wb])\s+[KQkq-]+\s+[a-h1-8-]+\s+\d+\s+\d+$"
)

HEADER_RE = re.compile(
    r"^(.+?)\s+vs[sa]?\s+(.+?),\s+(.+?),\s+(\d{4})\s*$",
    re.IGNORECASE,
)

def color_from_fen(fen: str) -> str:
    parts = fen.split()
    return "black" if len(parts) > 1 and parts[1] == "b" else "white"


def strip_move_numbers(solution: str) -> str:
    """
    Rimuove i numeri di mossa per ottenere la sequenza grezza.
    "1. Nf6+ gxf6 2. Bxf7#"  →  "Nf6+ gxf6 Bxf7#"
    "1... Bc5+ 2. Kxc5"       →  "Bc5+ Kxc5"
    """
    s = re.sub(r"\d+\.{1,3}\s*", "", solution)
    return " ".join(s.split())


def infer_themes(category: str, note: Optional[str], solution: str) -> list[str]:
    themes = []
    text = (note or "") + " " + category
    if re.search(r"mate in 2", text, re.I) or "mateIn2" in themes:
        themes.append("mateIn2")
    elif re.search(r"mate in 3", text, re.I):
        themes.append("mateIn3")
    elif re.search(r"mate in 4", text, re.I):
        themes.append("mateIn4")
    elif re.search(r"mate in (\d+)", text, re.I):
        n = re.search(r"mate in (\d+)", text, re.I).group(1)
        themes.append(f"mateIn{n}")
    if "#" in solution:
        if not themes:
            themes.append("mate")
    return themes


# ──────────────────────────── parser m8nN.txt ──────────────────────────────

def parse_mate_in_n(path: Path, n: int) -> list[Puzzle]:
    """
    Blocchi separati da doppia riga vuota.
    Struttura del blocco:
        Giocatore vs Giocatore, Luogo, Anno   ← riga opzionale
        FEN
        1. mossa1 mossa2 2. mossa3#           ← soluzione (una o più righe)
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_blocks = re.split(r"\n{2,}", text.strip())

    source = path.stem  # "m8n2"
    category = f"Mate in {n}"
    puzzles: list[Puzzle] = []

    for idx, block in enumerate(raw_blocks):
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            continue

        # Trova la riga FEN
        fen_idx = next(
            (i for i, l in enumerate(lines) if FEN_RE.match(l)), None
        )
        if fen_idx is None:
            continue

        fen = lines[fen_idx]
        white = black = location = None
        year = None

        # Intestazione sopra il FEN
        if fen_idx > 0:
            m = HEADER_RE.match(lines[fen_idx - 1])
            if m:
                white, black, location, year_s = m.groups()
                year = int(year_s)
                white = white.strip()
                black = black.strip()
                location = location.strip()

        # Soluzione sotto il FEN
        sol_raw = " ".join(lines[fen_idx + 1:]).strip()
        moves_raw = strip_move_numbers(sol_raw)

        p = Puzzle(
            id=f"{source}_{idx:04d}",
            source=source,
            category=category,
            fen=fen,
            moves=moves_raw,
            solution_display=sol_raw,
            white=white,
            black=black,
            location=location,
            year=year,
            themes=infer_themes(category, None, sol_raw),
            color_to_move=color_from_fen(fen),
        )
        puzzles.append(p)

    return puzzles


# ──────────────────────────── parser puzzle_rush.txt ───────────────────────

def parse_puzzle_rush(path: Path) -> list[Puzzle]:
    """
    Formato: blocchi FEN + soluzione separati da riga vuota.
    Marcatori di punteggio "--------------N" vengono ignorati.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Rimuovi i marcatori di punteggio
    text = re.sub(r"-{5,}\d+", "", text)
    raw_blocks = re.split(r"\n{2,}", text.strip())

    source = "puzzle_rush"
    puzzles: list[Puzzle] = []

    for idx, block in enumerate(raw_blocks):
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            continue

        fen_idx = next(
            (i for i, l in enumerate(lines) if FEN_RE.match(l)), None
        )
        if fen_idx is None:
            continue

        fen = lines[fen_idx]
        sol_raw = " ".join(lines[fen_idx + 1:]).strip()
        moves_raw = strip_move_numbers(sol_raw)

        p = Puzzle(
            id=f"{source}_{idx:04d}",
            source=source,
            category="Puzzle Rush",
            fen=fen,
            moves=moves_raw,
            solution_display=sol_raw,
            themes=infer_themes("Puzzle Rush", None, sol_raw),
            color_to_move=color_from_fen(fen),
        )
        puzzles.append(p)

    return puzzles


# ──────────────────────── parser puzzle_over_2000_ELO.txt ──────────────────

def parse_elo_puzzles(path: Path) -> list[Puzzle]:
    """
    Formato:
        Puzzles rated 2000-2099, pt. ii.
        The color disk on the diagram indicates who moves first.
        a)
        [Nota opzionale: "White mates in 2."]
        Giocatore vs Giocatore, lichess, (Rating)
        FEN
        [ Soluzione ]
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    SECTION_RE = re.compile(r"^Puzzles rated.*?pt\.\s*(\w+)\.", re.I)
    LABEL_RE   = re.compile(r"^([a-z])\)\s*$")
    NOTE_RE    = re.compile(r"^(White|Black)\s+mates\s+in\s+\d+\.", re.I)
    SKIP_RE    = re.compile(r"^The color disk", re.I)
    ELO_HDR_RE = re.compile(
        r"^(.+?)\s+vs[sa]?\s+(.+?),\s+\S+,\s+\((\d+)\)\s*$", re.I
    )
    SOL_RE = re.compile(r"^\[(.+)\]\s*$")

    source = "elo2000"
    puzzles: list[Puzzle] = []

    current_section = "pt. i"
    current_label   = ""
    current_note    = None
    current_white   = None
    current_black   = None
    current_rating  = None
    pending_header  = False
    idx = 0

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # Riga di sezione
        sm = SECTION_RE.match(line)
        if sm:
            current_section = f"pt. {sm.group(1)}"
            current_note = None
            i += 1
            continue

        # Riga da saltare
        if SKIP_RE.match(line):
            i += 1
            continue

        # Etichetta lettera a)/b)/…
        lm = LABEL_RE.match(line)
        if lm:
            current_label = lm.group(1) + ")"
            current_note  = None
            pending_header = False
            i += 1
            continue

        # Nota opzionale
        nm = NOTE_RE.match(line)
        if nm:
            current_note = line
            i += 1
            continue

        # Intestazione giocatori
        hm = ELO_HDR_RE.match(line)
        if hm:
            current_white  = hm.group(1).strip()
            current_black  = hm.group(2).strip()
            current_rating = int(hm.group(3))
            pending_header = True
            i += 1
            continue

        # FEN
        fm = FEN_RE.match(line)
        if fm:
            fen = line
            # Cerca la soluzione nella prossima riga non vuota
            sol_raw = ""
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if nxt:
                    sm2 = SOL_RE.match(nxt)
                    if sm2:
                        sol_raw = sm2.group(1).strip()
                    else:
                        # soluzione senza parentesi quadre
                        sol_raw = nxt
                    j += 1
                    break
                j += 1

            moves_raw = strip_move_numbers(sol_raw)

            # Determina temi
            themes = []
            if current_note:
                themes = infer_themes("ELO 2000+", current_note, sol_raw)
            if not themes:
                themes = infer_themes("ELO 2000+", None, sol_raw)

            p = Puzzle(
                id=f"{source}_{idx:04d}",
                source=source,
                category="ELO 2000+",
                rating=current_rating,
                themes=themes,
                fen=fen,
                moves=moves_raw,
                solution_display=sol_raw,
                white=current_white,
                black=current_black,
                note=current_note,
                section=f"{current_section}, {current_label}",
                color_to_move=color_from_fen(fen),
            )
            puzzles.append(p)
            idx += 1

            # Reset stato corrente
            current_note   = None
            current_white  = None
            current_black  = None
            current_rating = None
            pending_header = False

            i = j
            continue

        i += 1

    return puzzles


# ──────────────────────────── parser CSV Lichess ───────────────────────────

def parse_lichess_csv(path: Path) -> list[Puzzle]:
    """
    Colonne attese: PuzzleId, FEN, Moves, Rating, [RatingDeviation],
                    [Popularity], [NbPlays], Themes, [GameUrl], [OpeningTags]
    Moves è già in formato UCI (e2e4 e7e5 …).
    """
    import csv

    puzzles: list[Puzzle] = []
    source = "lichess_db"

    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            fen      = row.get("FEN", "").strip()
            moves    = row.get("Moves", "").strip()
            pid      = row.get("PuzzleId", f"lc_{idx:06d}").strip()
            rating_s = row.get("Rating", "").strip()
            themes_s = row.get("Themes", "").strip()

            if not FEN_RE.match(fen):
                continue

            rating  = int(rating_s) if rating_s.isdigit() else None
            themes  = [t for t in themes_s.split() if t]

            # Costruisci solution_display (UCI → leggibile)
            # Manteniamo le mosse UCI grezze; il generatore LaTeX le mostrerà come tali
            p = Puzzle(
                id=f"{source}_{pid}",
                source=source,
                category="Lichess DB",
                rating=rating,
                themes=themes,
                fen=fen,
                moves=moves,
                solution_display=moves,   # mosse UCI, nessuna numerazione
                color_to_move=color_from_fen(fen),
            )
            puzzles.append(p)

    return puzzles


# ─────────────────────────────────── main ──────────────────────────────────

def main():
    args = sys.argv[1:]

    base_dir   = Path(args[0]) if len(args) > 0 else Path(".")
    csv_path   = Path(args[1]) if len(args) > 1 else None
    out_path   = Path(args[2]) if len(args) > 2 else Path("puzzles.json")

    all_puzzles: list[Puzzle] = []

    # ── Mate in N ──────────────────────────────────────────────────────────
    for n, fname in [(2, "m8n2.txt"), (3, "m8n3.txt"), (4, "m8n4.txt")]:
        p = base_dir / fname
        if p.exists():
            parsed = parse_mate_in_n(p, n)
            print(f"  {fname}: {len(parsed)} puzzle")
            all_puzzles.extend(parsed)
        else:
            print(f"  [ATTENZIONE] {fname} non trovato, saltato.")

    # ── Puzzle Rush ────────────────────────────────────────────────────────
    p = base_dir / "puzzle_rush.txt"
    if p.exists():
        parsed = parse_puzzle_rush(p)
        print(f"  puzzle_rush.txt: {len(parsed)} puzzle")
        all_puzzles.extend(parsed)
    else:
        print("  [ATTENZIONE] puzzle_rush.txt non trovato, saltato.")

    # ── ELO 2000+ ──────────────────────────────────────────────────────────
    p = base_dir / "puzzle_over_2000_ELO.txt"
    if p.exists():
        parsed = parse_elo_puzzles(p)
        print(f"  puzzle_over_2000_ELO.txt: {len(parsed)} puzzle")
        all_puzzles.extend(parsed)
    else:
        print("  [ATTENZIONE] puzzle_over_2000_ELO.txt non trovato, saltato.")

    # ── CSV Lichess (opzionale) ────────────────────────────────────────────
    if csv_path and csv_path.exists():
        parsed = parse_lichess_csv(csv_path)
        print(f"  {csv_path.name}: {len(parsed)} puzzle")
        all_puzzles.extend(parsed)
    elif csv_path:
        print(f"  [ATTENZIONE] {csv_path} non trovato, saltato.")

    # ── Rimozione duplicati per FEN ────────────────────────────────────────
    seen_fens: dict[str, int] = {}
    unique: list[Puzzle] = []
    dupes = 0
    for p in all_puzzles:
        fen_key = p.fen.split()[0]  # solo la posizione, ignora turno/arrocco/en-passant
        if fen_key in seen_fens:
            dupes += 1
        else:
            seen_fens[fen_key] = 1
            unique.append(p)

    print(f"\n  Totale prima del dedup : {len(all_puzzles)}")
    print(f"  Duplicati rimossi      : {dupes}")
    print(f"  Puzzle unici           : {len(unique)}")

    # ── Scrivi JSON ────────────────────────────────────────────────────────
    output = {
        "meta": {
            "total": len(unique),
            "sources": list({p.source for p in unique}),
            "categories": list({p.category for p in unique}),
        },
        "puzzles": [p.to_dict() for p in unique],
    }

    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n  ✓ Scritto: {out_path}  ({out_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    print("=== merge_puzzles.py ===\n")
    main()
