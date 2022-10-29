#!/usr/bin/env python
<<<<<<< HEAD
"""This script will run logistic regression on a training dataset and output 
training and validation metrics, and predictions for an unlabeled dataset."""
=======
>>>>>>> bbaf5f2a0e58f57fb6cbf1d15989a220812b4e94
import argparse
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold
from sklearn import preprocessing
<<<<<<< HEAD
from sklearn.metrics import f1_score, accuracy_score, classification_report
parser = argparse.ArgumentParser(description="Fits a Logistic Regression model and predicts labels for a dataset")
parser.add_argument("train", help="csv file with training dataset")
parser.add_argument("unlabeled", help="csv file with unlabeled dataset")
parser.add_argument("--train_out", type=str, \
    help="output file for training metrics", default="train_metrics.txt") #TODO: Change to separate train and val files
parser.add_argument("--val_out", type=str, \
    help="output file", default="val_metrics.txt")
=======
parser = argparse.ArgumentParser(description="Fits a Logistic Regression model and predicts labels for a dataset")
parser.add_argument("train", help="csv file with training dataset")
parser.add_argument("unlabeled", help="csv file with unlabeled dataset")
parser.add_argument("--output", help="output file", default="results.txt")
>>>>>>> bbaf5f2a0e58f57fb6cbf1d15989a220812b4e94
parser.add_argument("--predictions_base", \
    help="prefix for files to output predictions", default="predictions")
# parser.add_argument("--train_predictions_base", \
    # help="prefix for files to output predictions on training set", default="X_pred.csv")
parser.add_argument("--penalty", help="penalty for the model", default="l2")
parser.add_argument("--Cs", \
    help="values to test for C, the inverse strength of regularization", default=[.01,.1,1,10,100])
<<<<<<< HEAD
parser.add_argument("--class_weight", \
    help="class weight for logisitic regression", default='balanced')
parser.add_argument("--metric", type=str, \
    help="Evaluation metric", default="f1", choices=["f1","accuracy"])
=======
>>>>>>> bbaf5f2a0e58f57fb6cbf1d15989a220812b4e94
parser.add_argument("--splits", help="number of splits to use for cross-validation", default=5)
args = parser.parse_args()

def main(args):
    # Data Loading 
    data = pd.read_csv(args.train, header=0, index_col=0)
<<<<<<< HEAD
    targets = ["RP to CMD", "CMD to NARR", "RP to CMD or CMD to NARR", "RP to CMD and CMD to NARR"]
    X = data.drop(targets, axis=1)
    kf = KFold(shuffle=True, random_state=23, n_splits=args.splits)
    ys = {target : data[target] for target in targets}
    best_Cs = {}
    val_scores = {target : {C : [] for C in args.Cs} for target in targets} # val_accs[target][C] 
    scaler = preprocessing.StandardScaler().fit(X)
    X_scaled = scaler.transform(X)
    metric = f1_score if args.metric == "f1" else accuracy_score
=======
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

>>>>>>> bbaf5f2a0e58f57fb6cbf1d15989a220812b4e94
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
<<<<<<< HEAD
                model = LogisticRegression(penalty=args.penalty, C=C, class_weight=args.class_weight).fit(X_train_scaled,y_train)
                val_scores[target][C].append(metric(y_val, model.predict(X_val_scaled)))

    # Find best C for each target by mean validation accuracy
    with open(args.val_out, 'w') as f:
        for target in targets:
            best_val_score = 0
            for C in args.Cs:
                t_val_score = np.mean(val_scores[target][C])
                if t_val_score > best_val_score:
                    best_C = C
                    best_val_score = t_val_score
                    best_val_report = classification_report(y_val, model.predict(X_val_scaled))
            best_Cs[target] = best_C
            f.write("Best C for {} is {} with mean {} score of {}\n".format(target, best_C, args.metric, best_val_score))
            f.write(best_val_report)
=======
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
>>>>>>> bbaf5f2a0e58f57fb6cbf1d15989a220812b4e94
          
    # Run Logistic Regression over the whole dataset with selected C values
    full = pd.read_csv(args.unlabeled, header=0, index_col=0)
    X_full = full.copy()
    scaler = scaler.fit(X_full)
    X_full_scaled = scaler.transform(X_full)
<<<<<<< HEAD
    with open(args.train_out, 'w') as f:
        for target in targets:
            model = LogisticRegression(penalty=args.penalty, C = best_Cs[target],\
                 class_weight=args.class_weight).fit(X_scaled,ys[target])
=======
    with open(args.output, 'w') as f:
        for target in targets:
            model = LogisticRegression(penalty=args.penalty, C = best_Cs[target]).fit(X_scaled,ys[target])
>>>>>>> bbaf5f2a0e58f57fb6cbf1d15989a220812b4e94
            full[f"{target}_pred"] = model.predict(X_full_scaled)
            full[f"{target}_pred_prob"] = model.predict_proba(X_full_scaled)[:,1]
            out = full[[f"{target}_pred",f"{target}_pred_prob"]]
            out.to_csv(args.predictions_base+f"_{target}.csv")
<<<<<<< HEAD
            f.write(f"Train {args.metric} score for {target}: {metric(model.predict(X_scaled),ys[target])}\n")
            f.write(classification_report(model.predict(X_scaled),ys[target]))
if __name__ == "__main__":
    main(args)
    # log validation metrics, add F1, metrics for each class DONE
    # try class weights DONE, improved F1
    # stratified k-fold 
    # output list of instance ids
    # Automate train data generation
    # Try SVM, NaiveBayes
    # PCA?
=======
            f.write(f"Train Accuracy for {target}: {model.score(X_scaled,ys[target])}\n")
if __name__ == "__main__":
    main(args)
>>>>>>> bbaf5f2a0e58f57fb6cbf1d15989a220812b4e94
