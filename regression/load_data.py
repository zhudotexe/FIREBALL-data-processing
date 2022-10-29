#!/usr/bin/env python
"""This script will create a dataset of instances for regression from 
a csv file with labels and one with heuristic features"""
import argparse
import pandas as pd
# import sklearn
parser = argparse.ArgumentParser(description="create a dataset of instances for regression from \
    a csv file with labels and one with heuristic features")
parser.add_argument("labels", help="csv file with labels")
parser.add_argument("features", help="csv file with heuristic features (from explorer server)")
parser.add_argument("output", help="output file")
args = parser.parse_args()

def main(args):
    """main function"""
    labels = pd.read_csv(args.labels, header=0, index_col=0)
    features = pd.read_csv(args.features, header=0, index_col=0)
    print(labels.head(10), features.head(10))
    dataset = features.join(labels, how="inner", on="instance_id")
<<<<<<< HEAD
    dataset["RP to CMD"].fillna(-1,inplace=True)
    dataset["CMD to NARR"].fillna(-1,inplace=True)
    dataset["RP to CMD or CMD to NARR"] = dataset[["RP to CMD", "CMD to NARR"]].max(axis=1)
    dataset["RP to CMD and CMD to NARR"] = dataset[["RP to CMD", "CMD to NARR"]].min(axis=1)
=======
>>>>>>> bbaf5f2a0e58f57fb6cbf1d15989a220812b4e94
    dataset.to_csv(args.output)
if __name__ == "__main__":
    main(args)
