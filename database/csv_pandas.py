# Download the csv from https://database.lichess.org/lichess_db_puzzle.csv.zst
import pandas as pd
df = pd.read_csv("Puzzle/lichess_db_puzzle.csv")
#PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl,OpeningTags
df = df.drop(columns=['RatingDeviation', 'Popularity', 'NbPlays', 'GameUrl', 'OpeningTags'])
df.to_csv('Puzzle/lichess_db_puzzle_reduced.csv', index=False)