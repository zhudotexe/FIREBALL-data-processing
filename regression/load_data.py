#!/usr/bin/env python
"""This script will create a dataset of instances for regression from 
a csv file with labels and one with heuristic features"""
import argparse
import pandas as pd
import sklearn
parser = argparse.ArgumentParser(description="create a dataset of instances for regression from \
    a csv file with labels and one with heuristic features")
parser.add_argument("labels", help="csv file with labels")
parser.add_argument("features", help="csv file with heuristic features (from explorer server)")
parser.add_argument("output", help="output file")
args = parser.parse_args()

def main(args):
    """main function"""
    labels = pd.read_csv(args.labels, header=True, index_col=0)
    features = pd.read_csv(args.features, header=True, index_col=0)
    dataset = pd.join(features, labels, how="inner", on="Instance ID")
    dataset.to_csv(args.output)
if __name__ == "__main__":
    main(args)
