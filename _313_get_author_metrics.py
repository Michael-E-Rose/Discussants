#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Crawls citations for authors on a yearly basis and computes the Euclidean
index of citations.

You need a special API key by Scopus to access the citation view.
"""

from pathlib import Path

import pandas as pd
from scholarmetrics import euclidean
from pybliometrics.scopus import CitationOverview
from tqdm import tqdm

SOURCE_FILE = Path("./311_publication_lists/publications.csv")
TARGET_FILE = Path("./313_author_metrics/metrics.csv")


def compute_euclid(df):
    """Return yearly Euclidean index except when all entries are nan."""
    return df.dropna(how="all", axis=1).cumsum(axis=1).apply(euclidean)


def get_yearly_citations(sid, pubyear, refresh=False):
    """Return dict of yearly citations."""
    try:
        co = CitationOverview([sid], pubyear, refresh=refresh)
        return {y: c for y, c in co.cc[0] if int(y) < 2021}
    except Exception as e:
        print(e, sid)
        return {}


def nan_preserving_sum(df):
    """Sum values except when all entries are nan."""
    return df.dropna(how="all", axis=1).fillna(0).sum(axis=0)


def main():
    # Read in
    df = pd.read_csv(SOURCE_FILE, index_col="researcher")
    years = (df["years"].str.split("|", expand=True).stack().to_frame("year")
               .droplevel(1).reset_index())
    years["year"] = years["year"].astype("uint16")
    eids = (df["eids"].str.split("|", expand=True).stack().to_frame("eid")
              .droplevel(1).reset_index())
    eids["sid"] = eids["eid"].str.split("-").str[-1]

    # Yearly citation count
    info = set(zip(eids["sid"], years["year"]))
    print(f">>> Searching yearly citation counts for {len(info):,} articles")
    yearly_cites = {e: get_yearly_citations(e, y) for e, y in tqdm(info)}
    yearly_cites = pd.DataFrame(yearly_cites).T
    yearly_cites = yearly_cites[sorted(yearly_cites.columns)]
    eid_cites = eids.join(yearly_cites, on="sid")
    eid_cites = eid_cites.drop(columns=["eid", "sid"]).set_index("researcher")
    grouped = eid_cites.groupby(eid_cites.index)
    cites = grouped.apply(nan_preserving_sum)
    cites = cites.to_frame("yearly_cites")

    # Euclidean index of citations
    euclid = grouped.apply(compute_euclid)
    euclid = euclid.to_frame("euclid")

    # Write out
    euclid = euclid.sort_index()
    euclid.to_csv(TARGET_FILE, index_label=["researcher", "year"])


if __name__ == '__main__':
    main()
