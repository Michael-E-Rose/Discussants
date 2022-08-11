#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Lists EIDs, sourced and year of publications for each author
and each discussant.
"""

from pathlib import Path

import pandas as pd
from tqdm import tqdm

NBER_FILE = Path("./119_NBER_sample/manuscripts.csv")
TARGET_FILE = Path("./311_publication_lists/publications.csv")

YEAR_CUTOFF = 2014
DOC_TYPES = ("re", "ar", "cp", "no", "ip", "sh")


def parse_publications(res):
    """Return EIDs, publication name (source) and publication year."""
    return [(p.eid, p.publicationName, p.coverDate[:4]) for p in res
            if int(p.coverDate[:4]) < YEAR_CUTOFF and p.subtype in DOC_TYPES]


def perform_query(q, refresh=100):
    """Access ScopusSearch API to retrieve EIDs, sources and
    publication years.
    """
    from pybliometrics.scopus import ScopusSearch

    try:
        res = ScopusSearch(q, refresh=refresh).results
        info = parse_publications(res)
    except (KeyError, TypeError):
        res = ScopusSearch(q, refresh=True).results
        info = parse_publications(res)
    if not info:
        return None, None, None
    eids, sources, years = zip(*info)
    return eids, sources, years


def main():
    # Authors and Discussants of NBER sample
    nber = pd.read_csv(NBER_FILE, usecols=["author_scopus", "discussant"],
                       dtype="str")
    authors = set([a for l in nber["author_scopus"].dropna() for a in l.split(";")])
    discussants = set([a for l in nber["discussant"].dropna() for a in l.split(";")
                       if a.isnumeric()])
    researchers = authors | discussants
    researchers.remove("-")

    # List publications
    out = {}
    print(f">>> Parsing publications of {len(researchers):,} researchers")
    for auth_id in tqdm(researchers):
        q = f"AU-ID({auth_id})"
        try:
            eids, sources, years = perform_query(q)
        except Exception as e:
            print(auth_id, e)
        if not eids or not sources or not years:
            print(f"{auth_id} lacks information")
            continue
        sources = [s or "-" for s in sources]  # Replace missing journal names
        out[auth_id] = {"eids": "|".join(eids), "sources": "|".join(sources),
                        "years": "|".join(years)}

    # Write out
    df = pd.DataFrame(out).T.sort_index()
    df.to_csv(TARGET_FILE, index_label="researcher")


if __name__ == '__main__':
    main()
