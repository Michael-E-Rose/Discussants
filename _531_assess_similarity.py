#!/usr/bin/env python3
# Author:  Michael E. Rose <michael.ernst.rose@gmail.com>
"""Computes reference overlap between papers and groups."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from _012_list_presentations import MEETINGS_WITH

REF_FOLDER = Path("./130_references")
OUTPUT_FOLDER = Path("./990_output")


def average_similarity(m):
    """Compute average using lower triangular of cosine matrix."""
    tril = np.tril(m.values, k=-1)
    return np.nanmean(tril)


def compute_cosine_matrix(docs):
    """Compute cosine matrix of text similiarity."""
    m = TfidfVectorizer(tokenizer=pipe_tokenize).fit_transform(docs)
    return pd.DataFrame((m * m.T).toarray()), m


def pipe_tokenize(text):
    """Return tokens of document deprived of numbers and interpunctuation."""
    return text.split("|")


def make_dataframe(df, col, label="group"):
    """Return DataFrame with new column filled with `col`."""
    df[label] = col
    return df[["journals", "group"]]


def main():
    # Read in
    ref_docs = {}
    for fname in sorted(REF_FOLDER.glob("*.csv")):
        key = fname.stem
        new = pd.read_csv(fname, index_col=0).drop(columns="references")
        ref_docs[key] = new.dropna(subset=["journals"])

    # Average similarity by journal with journal-specific weights
    print(">>> Average similarity by origin of document w/ journal weights:")
    for label, df in ref_docs.items():
        docs = df["journals"].tolist()
        cos, _ = compute_cosine_matrix(docs)
        print(f"... {label}: {round(average_similarity(cos), 3)}")

    # Average similarity by journal with global weights
    print(">>> Average similarity by origin of document w/ global weights:")
    refs_joint = pd.concat([make_dataframe(df.copy(), label) for label, df
                            in ref_docs.items()], axis=0)
    cos, _ = compute_cosine_matrix(refs_joint["journals"].tolist())
    cos.columns = cos.index = refs_joint["group"]
    for group in refs_joint["group"].unique():
        m = cos.loc[group, group]
        print(f"... {group}: {round(average_similarity(m), 3)}")

    # Similarity between discussant groups
    refs = ref_docs["NBER"]
    refs = refs[refs["group"].str.find("-") == -1]
    refs_with = refs[refs["has_discussion"] == 1]
    refs_without = refs[refs["has_discussion"] == 0]
    docs_with = "|".join(refs_with["journals"].dropna().tolist())
    docs_without = "|".join(refs_without["journals"].dropna().tolist())
    cos, m = compute_cosine_matrix([docs_with, docs_without])
    cos = cos.round(2)[0][1]
    print(f">>> Similarity between all discussed and non-discussed groups {cos}")
    full = pd.DataFrame(m.toarray()).T
    both = full.replace(0, np.nan).dropna()
    share = both.shape[0]/full.shape[0]
    print(f">>> Journals cited in both groups: {share:.2%}")

    # Similarity within discussant groups
    print(">>> Similiarity within groups (with, without):")
    for df in [refs_with.copy(), refs_without.copy()]:
        df["journals"] = df["journals"] + "|"
        grouped = df.groupby("group")[["journals"]].sum()
        docs = grouped["journals"].str.strip("|").tolist()
        cos, _ = compute_cosine_matrix(docs)
        cos.index = cos.columns = grouped.index
        print(cos.round(2))
        print(average_similarity(cos))

    # Similarity across all NBER groups
    refs["journals"] = refs["journals"] + "|"
    grouped = refs.groupby("group")[["journals"]].sum()
    docs = grouped["journals"].str.strip("|").tolist()
    cos, _ = compute_cosine_matrix(docs)
    # Sort matrix
    cos.index = cos.columns = grouped.index
    cos = cos.sort_values("EFCE", ascending=False)
    cos = cos[cos.index]
    mask = np.tril(cos.values) != 0
    cos = cos.where(mask).round(2)
    print(f">>> Average similiarity of groups: {average_similarity(cos):.3}")
    print("... similarity matrix:")
    print(cos)

    # Write out
    fname = OUTPUT_FOLDER/"Tables"/"group_similarity.tex"
    labels = [f"\\textbf{{{c}}}" if c in MEETINGS_WITH else c
              for c in cos.index]
    cos.index = cos.columns = labels
    cos = cos.fillna("").astype(str).replace("1.0", "1")
    cos.to_latex(fname, escape=False)


if __name__ == '__main__':
    main()
