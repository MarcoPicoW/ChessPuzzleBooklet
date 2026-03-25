# Chess Booklet Generator

A small Python pipeline that merges chess puzzle collections into a single JSON database and generates weekly A5 PDF booklets using LaTeX.

---

## Repository Structure

```
.
├── generate_booklet.py     # Step 2 – select 10 puzzles → weekly .tex file
├── puzzles.json            # Generated puzzle database (2221 puzzles)
│
├── database
    ├── csv_pandas.py           # Helper – pre-process the Lichess CSV download
    ├── merge_puzzles.py        # Step 1 – parse all source files → puzzles.json
    ├── m8n2.txt                # Source: Mate-in-2 puzzles (221)
    ├── m8n3.txt                # Source: Mate-in-3 puzzles (488)
    ├── m8n4.txt                # Source: Mate-in-4 puzzles (462)
    ├── puzzle_rush.txt         # Source: Lichess Puzzle Rush games (984)
    └── puzzle_over_2000_ELO.txt # Source: Lichess puzzles rated 2000–2099 (66)
```

---

## Quick Start

### 1 – Build the puzzle database

```bash
python merge_puzzles.py
```

This reads all source files in the current directory and writes `puzzles.json`.

To also include the full Lichess puzzle CSV (optional, several GB):

```bash
# First reduce the CSV with the helper script
python csv_pandas.py

# Then pass it to the merger
python merge_puzzles.py . lichess_db_puzzle_reduced.csv puzzles.json
```

### 2 – Generate a booklet

```bash
# Current week, default author
python generate_booklet.py

# Specific week / author
python generate_booklet.py puzzles.json 14 2026 "Marco Keller"

# Full syntax
python generate_booklet.py [puzzles.json] [week] [year] [author] [output.tex]
```

### 3 – Compile the PDF

```bash
pdflatex booklet_week14.tex
pdflatex booklet_week14.tex    # second pass needed for page references
```

---

## Booklet Layout

Each booklet is A5, black and white, and contains:

| Page | Content |
|------|---------|
| 1 | Title page – title, week number |
| 2 – 11 | One puzzle per page with chessboard diagram and note-taking grid |
| 12 | Solutions table |

The 10 puzzles are always ordered by increasing difficulty:

| # | Difficulty | Source |
|---|-----------|--------|
| 1 – 4 | Easy | Mate in 2 |
| 5 – 7 | Medium | Mate in 3 |
| 8 – 9 | Hard | Mate in 4 |
| 10 | Grandmaster | ELO 2000+ |

The selection is seeded with `year × 100 + week`, so each week produces a different but reproducible set of puzzles.

---

## Source File Formats

The merger handles three different input formats automatically.

**`m8n2.txt`, `m8n3.txt`, `m8n4.txt`** – classic games, one block per puzzle:
```
Paul Morphy vs Duke Isouard, Paris, 1858
4kb1r/p2n1ppp/4q3/4p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 1 0
1. Qb8+ Nxb8 2. Rd8#
```

**`puzzle_rush.txt`** – FEN and solution only, no player info:
```
r1bq1rk1/ppn1bppp/4pn2/1B6/2P5/5NB1/PP2QPPP/RN3RK1 w - - 1 0
13.Rd1 Bd7 14.Bxd7 Nxd7 15.Ne5
```

**`puzzle_over_2000_ELO.txt`** – Lichess games with ELO rating, grouped into sections:
```
Puzzles rated 2000-2099, pt. ii.
a)
CGilligan vs Yeah_YEah, lichess, (2003)
r1b1k2r/pp1n1ppp/2n1p3/2bpP3/5B2/2NB1N2/PqPQ1PPP/R3K2R w KQkq - 1 0
[ Rb1 Qa3 Nb5 ]
```

**Lichess CSV** (optional) – standard Lichess puzzle database export:
```
PuzzleId,FEN,Moves,Rating,Themes,...
```
Download from [database.lichess.org](https://database.lichess.org/#puzzles).

---

## JSON Schema

Each entry in `puzzles.json` follows this structure:

```json
{
  "id":               "m8n2_0042",
  "source":           "m8n2",
  "category":         "Mate in 2",
  "rating":           null,
  "themes":           ["mateIn2"],
  "fen":              "4kb1r/p2n1ppp/4q3/4p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 1 0",
  "moves":            "Qb8+ Nxb8 Rd8#",
  "solution_display": "1. Qb8+ Nxb8 2. Rd8#",
  "white":            "Paul Morphy",
  "black":            "Duke Isouard",
  "location":         "Paris",
  "year":             1858,
  "note":             null,
  "section":          null,
  "color_to_move":    "white"
}
```

---

## Requirements

**Python** – 3.10 or later, no external dependencies.

**LaTeX packages** – install via TeX Live or MiKTeX:

| Package | Purpose |
|---------|---------|
| `chessboard` | Renders the chessboard diagrams |
| `skak` | Chess fonts |
| `gridpapers` | Note-taking grid below each puzzle (install the version from my Repo or it is not going to work)|
| `fancyhdr` | Header and footer |
| `booktabs` | Solutions table |
| `geometry` | A5 page layout |


---

## License

Puzzle content sourced from [Lichess](https://lichess.org) (Creative Commons CC0) and historical game collections. Scripts are MIT licensed.