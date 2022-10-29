"""Reads a csv of predictions and returns a list of instance ids with positive predictions"""
import pandas as pd
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('predictions', type=str, help='Path to predictions csv')
parser.add_argument('--output', type=str, help='name of output file')

def main(args):
    df = pd.read_csv(args.predictions, header=0, index_col=0)
    print(df.head())
    df = df[df.iloc[:,0] == 1]
    with open(args.output, 'w') as f:
        for id in df.index.tolist():
            f.write(id + '\n')
if __name__ == "__main__":
    args = parser.parse_args()
    main(args)