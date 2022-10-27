#!/usr/bin/env python
import argparse
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold
from sklearn import preprocessing
parser = argparse.ArgumentParser(description="Fits a Logistic Regression model and predicts labels for a dataset")
parser.add_argument("train", help="csv file with training dataset")
parser.add_argument("unlabeled", help="csv file with unlabeled dataset")
parser.add_argument("--output", help="output file", default="results.txt")
parser.add_argument("--predictions_base", \
    help="prefix for files to output predictions", default="predictions")
# parser.add_argument("--train_predictions_base", \
    # help="prefix for files to output predictions on training set", default="X_pred.csv")
parser.add_argument("--penalty", help="penalty for the model", default="l2")
parser.add_argument("--Cs", \
    help="values to test for C, the inverse strength of regularization", default=[.01,.1,1,10,100])
parser.add_argument("--splits", help="number of splits to use for cross-validation", default=5)
args = parser.parse_args()

def main(args):
    # Data Loading 
    data = pd.read_csv(args.train, header=0, index_col=0)
    X = data.drop(["RP to CMD","CMD to NARR"], axis=1)
    kf = KFold(shuffle=True, random_state=23, n_splits=args.splits)
    data["CMD to NARR"].fillna(-1,inplace=True)
    data["RP to CMD or CMD to NARR"] = data[["RP to CMD", "CMD to NARR"]].max(axis=1)
    data["RP to CMD and CMD to NARR"] = data[["RP to CMD", "CMD to NARR"]].min(axis=1)
    targets = ["RP to CMD", "CMD to NARR", "RP to CMD or CMD to NARR", "RP to CMD and CMD to NARR"]
    ys = {target : data[target] for target in targets}
    best_Cs = {}
    val_accs = {target : {C : [] for C in args.Cs} for target in targets} # val_accs[target][C] 
    scaler = preprocessing.StandardScaler().fit(X)
    X_scaled = scaler.transform(X)

    # Run K-Fold CV
    for train_index, val_index in kf.split(X):
        X_train, X_val = X.iloc[train_index], X.iloc[val_index]
        scaler = preprocessing.StandardScaler().fit(X_train)
        X_train_scaled = scaler.transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        for target in targets:
            y_train = ys[target].iloc[train_index]
            y_val = ys[target].iloc[val_index]
            for C in args.Cs:
                model = LogisticRegression(penalty=args.penalty, C=C).fit(X_train_scaled,y_train)
                val_acc = model.score(X_val_scaled, y_val)
                val_accs[target][C].append(val_acc)

    # Find best C for each target by mean validation accuracy
    for target in targets:
        best_val_acc = 0
        for C in args.Cs:
            t_val_acc = np.mean(val_accs[target][C])
            if t_val_acc > best_val_acc:
                best_C = C
                best_val_acc = t_val_acc
        best_Cs[target] = best_C
          
    # Run Logistic Regression over the whole dataset with selected C values
    full = pd.read_csv(args.unlabeled, header=0, index_col=0)
    X_full = full.copy()
    scaler = scaler.fit(X_full)
    X_full_scaled = scaler.transform(X_full)
    with open(args.output, 'w') as f:
        for target in targets:
            model = LogisticRegression(penalty=args.penalty, C = best_Cs[target]).fit(X_scaled,ys[target])
            full[f"{target}_pred"] = model.predict(X_full_scaled)
            full[f"{target}_pred_prob"] = model.predict_proba(X_full_scaled)[:,1]
            out = full[[f"{target}_pred",f"{target}_pred_prob"]]
            out.to_csv(args.predictions_base+f"_{target}.csv")
            f.write(f"Train Accuracy for {target}: {model.score(X_scaled,ys[target])}\n")
if __name__ == "__main__":
    main(args)