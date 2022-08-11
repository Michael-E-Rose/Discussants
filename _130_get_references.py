#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Gathers references and cited journals from published articles."""

from pathlib import Path

import pandas as pd
from tqdm import tqdm
from pybliometrics.scopus import ScopusSearch

from _012_list_presentations import DATA_RANGE

SOURCE_FILE = Path("./119_NBER_sample/manuscripts.csv")
TARGET_FOLDER = Path("./130_references")

JOURNALS = (("AER", 22697), ("ECTMA", 19482), ("JPE", 24404),
            ("REStud", 24202), ("QJE", 29431))


def get_references(eid, refresh=False):
    """Retrieve list of resolved (=indexed) references for a document."""
    from pybliometrics.scopus import AbstractRetrieval
    ab = AbstractRetrieval(eid, view='REF', refresh=refresh)
    ref_list = ab.references or []
    if not ref_list:
        ab = AbstractRetrieval(eid, view='REF', refresh=2)
        ref_list = ab.references or []
    ref_list = [ref for ref in ref_list if ref.type == "resolvedReference"]
    refs = "|".join([r.id for r in ref_list])
    journals = "|".join([r.sourcetitle for r in ref_list if r.sourcetitle])
    return {"references": refs, "journals": journals}


def main():
    # Get references for publications in NBER sample
    cols = ["eid", "year", "group", "has_discussion"]
    df = pd.read_csv(SOURCE_FILE, usecols=cols).dropna(subset=["eid"])
    df = df.set_index("eid")
    print(f">>> Retrieving references for {df.shape[0]:,} NBER publications")
    refs = {}
    for eid in tqdm(df.index):
        refs[eid] = get_references(eid)
    refs = pd.DataFrame(refs).T
    out = pd.concat([df, refs], axis=1)
    out.to_csv(TARGET_FOLDER/"NBER.csv", index_label="eid")

    # Get references for publications in other journals
    for key, source_id in JOURNALS:
        pubs = []
        for y in DATA_RANGE:
            q = f"SOURCE-ID({source_id}) AND PUBYEAR IS {y}"
            s = ScopusSearch(q, refresh=200)
            pubs.extend(s.results)
        print(f">>> Retrieving references for {len(pubs):,} {key} publications")
        refs = {}
        for pub in tqdm(pubs):
            eid = pub.eid
            new = {"year": pub.coverDate[:4]}
            new.update(get_references(eid))
            refs[eid] = new
        out = pd.DataFrame(refs).T
        out.to_csv((TARGET_FOLDER/key).with_suffix(".csv"), index_label="eid")


if __name__ == '__main__':
    main()
