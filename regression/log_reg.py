#!/usr/bin/env python
import argparse
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold
parser = argparse.ArgumentParser(description="Fits a Logistic Regression model and predicts labels for a dataset")
parser.add_argument("train", help="csv file with training dataset")
parser.add_argument("unlabeled", help="csv file with unlabeled dataset")
parser.add_argument("--output", help="output file", default="results.txt")
parser.add_argument("--predictions", help="file to output predictions", default="predictions.csv")
parser.add_argument("--train_predictions", help="file to output predictions on training set", default="X_pred.csv")
parser.add_argument("--penalty", help="penalty for the model", default="l2")
parser.add_argument("--Cs", help="values to test for C, the inverse strength of regularization", default=[.01,.1,1,10,100])
parser.add_argument("--splits", help="number of splits to use for cross-validation", default=5)
args = parser.parse_args()

def main(args):
    data = pd.read_csv(args.train, header=0, index_col=0)
    X = data.drop(["RP to CMD","CMD to NARR"], axis=1)
    kf = KFold(shuffle=True, random_state=23, n_splits=args.splits)
    data["CMD to NARR"].fillna(-1,inplace=True)
    data["RP to CMD or CMD to NARR"] = data[["RP to CMD", "CMD to NARR"]].max(axis=1)
    data["RP to CMD and CMD to NARR"] = data[["RP to CMD", "CMD to NARR"]].min(axis=1)
    number_to_label = {0:"RP to CMD", 1:"CMD to NARR", 2:"RP to CMD or CMD to NARR",3:"RP to CMD and CMD to NARR"}

    y0 = data["RP to CMD"]
    y1 = data["CMD to NARR"]
    y2 = data["RP to CMD or CMD to NARR"]
    y3 = data["RP to CMD and CMD to NARR"]
    ys = [y0,y1,y2,y3]

    for train_index, val_index in kf.split(X):
        X_train, X_val = X[train_index], X[val_index]
        y_trains, y_vals = [y[train_index] for y in ys], [y[val_index] for y in ys]
        for C in args.Cs:
            models = [LogisticRegression(penalty=args.penalty, C=C).fit(X_train,y_train) for y_train in y_trains]
            #TODO: Select best C for each y by validation accuracy
    #TODO: Run Logistic Regression over the whole dataset with selected C values
    data.to_csv(args.train_predictions)

    full = pd.read_csv(args.unlabeled, header=0, index_col=0)
    X_full = full.copy()
    pred_cols = []
    for i,model in enumerate(models):
        full[f"{number_to_label[i]}_pred"] = model.predict(X_full)
        full[f"{number_to_label[i]}_pred_prob"] = model.predict_proba(X_full)[:,1]
        pred_cols.append(f"{number_to_label[i]}_pred")
        pred_cols.append(f"{number_to_label[i]}_pred_prob")
    full[pred_cols].to_csv(args.predictions)
if __name__ == "__main__":
    main(args)