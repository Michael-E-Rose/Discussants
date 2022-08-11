#!/usr/bin/env python3
# Author:  Michael E. Rose <michael.ernst.rose@gmail.com>
"""Collects gender estimates from genderize.io.

This script was written for free usage of genderize, which
allows 1000 requests/day.  Run this script continuously on separate days
to obtain all the information.
"""

from collections import OrderedDict
from pathlib import Path

import genderize
import pandas as pd
from tqdm import tqdm

NBER_FILE = Path("./012_presentations/entries.csv")
TARGET_FILE = Path("./030_gender_estimates/genderize.csv")


def get_firstname(auth_id, refresh=False):
    """Return usable first name of Scopus Author profile."""
    from unicodedata import normalize

    from pybliometrics.scopus import AuthorRetrieval

    au = AuthorRetrieval(auth_id, refresh=refresh)
    given = au.given_name
    new = normalize('NFKD', given).encode('ascii', 'ignore').decode("utf8")
    firsts = [part for part in new.split() if
              len(part) > 1 and not part.endswith(".")]
    try:
        return firsts[0]
    except IndexError:
        print(f">>> {given} will not produce results")
        return None


def main():
    # Read in
    nber = pd.read_csv(NBER_FILE, index_col=0)
    try:  # Use already collected information
        collected = pd.read_csv(TARGET_FILE, index_col=0)
        collected.index = collected.index.astype(str)
        print(f">>> Skipping {collected.shape[0]} collected authors")
    except FileNotFoundError:
        collected = pd.DataFrame()

    # Get discussants
    nber = nber.dropna(subset=["discussant"])
    discussants = set([d for l in nber["discussant"] for d in l.split(";")])
    try:
        discussants.remove("-")
    except KeyError:
        pass

    # Get firstnames
    df = pd.DataFrame(index=sorted(discussants))
    df = df.drop(index=collected.index, errors="ignore").dropna()
    print(f">>> Getting usable first name of {df.shape[0]} discussants")
    df["first"] = df.index.map(get_firstname)
    df = df.dropna(subset=["first"])

    # Estimate gender for each name
    search_for = set(df["first"].unique())
    print(f">>> Looking up gender of {len(search_for):,} distinct names")
    estimates = OrderedDict()
    for name in tqdm(search_for):
        try:
            resp = genderize.Genderize().get([name])
            estimates[name] = resp[0]
        except genderize.GenderizeException:  # Daily quota exceeded
            break

    # Write out
    if estimates:
        new = pd.DataFrame(estimates).T
        df = df.join(new, how="right", on="first")
        df = df[["count", "gender", "name", "probability"]]
        collected = pd.concat([collected, df])
        collected = collected.sort_index()
        collected["count"] = collected["count"].fillna(0).astype(int).replace(0, "")
        collected.to_csv(TARGET_FILE, index_label="ID")

    # Statistics
    print(pd.value_counts(collected["gender"]))
    no_missing = collected["gender"].isnull().sum()
    share = round(no_missing/float(collected.shape[0]), 2)
    print(f">>> No estimates for {no_missing} out of {collected.shape[0]:,} "
          f"({share:.2%}) names.")


if __name__ == '__main__':
    main()
