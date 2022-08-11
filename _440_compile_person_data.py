#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Combines all per-person data for authors and discussants."""

from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
from pybliometrics.scopus import AffiliationRetrieval, ScopusSearch
from tqdm import tqdm

from _311_list_publications import DOC_TYPES, YEAR_CUTOFF

CENTRALITIES_FOLDER = Path("./220_centralities/")
METRICS_FILE = Path("./313_author_metrics/metrics.csv")
GENDER_FILE = Path("./030_gender_estimates/genderize.csv")
EDITOR_FOLDER = Path("./035_person_auxiliary/")
TARGET_FILE = Path("./440_person_data/all.csv")

FILTER_INSTITUTIONS = {"60020337", "60016621"}


def find_most_common(s):
    """Return most common entry from a list."""
    try:
        return Counter(s).most_common(1)[0][0]
    except TypeError:
        return None


def get_yearly_affiliation_types(author_ids):
    """Find yearly affiliations for each author."""
    affiliations = {}
    for auth_id in tqdm(author_ids):
        s = ScopusSearch(f"AU-ID({auth_id})")
        new = defaultdict(lambda: list())
        for p in s.results:
            year = int(p.coverDate[:4])
            if year < 1998 or year > YEAR_CUTOFF:
                continue
            if p.subtype not in DOC_TYPES:
                continue
            auth_idx = p.author_ids.split(";").index(str(auth_id))
            try:
                affs = p.author_afids.split(";")[auth_idx]
                for aff_id in affs.split("-"):
                    if aff_id in FILTER_INSTITUTIONS:
                        continue
                    aff = AffiliationRetrieval(aff_id)
                    new[year].append(aff.org_type)
            except (AttributeError, ValueError):
                continue
        affiliations[auth_id] = new
    return affiliations


def read_centralities(files):
    """Read all centrality files into DataFrame."""
    df = pd.DataFrame()
    for fname in files:
        netw, year = fname.stem.split("_")
        new = pd.read_csv(fname, index_col=0).add_prefix(netw + "_")
        new['year'] = int(year)
        new.index = new.index.astype(str)
        df = pd.concat([df, new], axis=0, sort=False)
    return df.reset_index().sort_values(['node', 'year'])


def main():
    # Read in
    df = pd.read_csv(METRICS_FILE)
    first_year = df.groupby("researcher")["year"].transform("first")

    # Compute affiliation type
    print(">>> Finding yearly affiliation types")
    types = get_yearly_affiliation_types(df["researcher"].unique())
    types = pd.DataFrame.from_dict(types).T.reset_index()
    types = types.rename(columns={"index": "researcher"})
    types = types.melt(id_vars='researcher', var_name="year", value_name="aff_type")
    types = types.sort_values(["researcher", "year"])
    types["aff_type"] = types.groupby("researcher")["aff_type"].fillna(method="ffill")
    types["aff_type"] = types["aff_type"].apply(find_most_common)
    df = df.merge(types, how="left", on=["researcher", "year"])

    # Compute variables
    df['experience'] = df['year'] - first_year

    # Merge with centralities
    df = df.rename(columns={"researcher": "node"})
    df["node"] = df["node"].astype(str)
    for netw in ("informal", "coauth"):
        files = CENTRALITIES_FOLDER.glob(f"*{netw}*.csv")
        new = read_centralities(files)
        new = new[new['node'].astype(str).str.isdigit()]
        df = df.merge(new, "outer", on=['node', 'year'])

    # Merge with gender
    gender = pd.read_csv(GENDER_FILE, usecols=["ID", "gender"], dtype=object)
    gender = gender.set_index("ID")
    gender["female"] = (gender["gender"] == "female").astype("uint8")
    df = df.join(gender[["female"]], how='left', on='node')

    # Merge with editorial positions
    editor = pd.read_csv(EDITOR_FOLDER/"persons_editors.csv",
                         dtype={"scopus_id": "str"})
    editor_cols = [c for c in editor.columns if "editor" in c]
    editor["editor_journal"] = editor[editor_cols].fillna("").apply(
        lambda s: "; ".join([x for x in s if x]), axis=1)
    for c in editor_cols:
        editor[c] = (~editor[c].isnull()).astype(int)

    df = df.merge(editor, "left", left_on=["node", "year"],
                  right_on=["scopus_id", "year"])
    df = df.drop(columns="scopus_id")

    # Mark discussants w/o editorial positions
    info_avail = set(pd.read_csv(EDITOR_FOLDER/"no_editors.csv", dtype="str")["scopus_id"])
    info_avail.update(editor["scopus_id"])
    mask = df["node"].isin(info_avail)
    for c in editor_cols:
        df.loc[mask & (df[c].isnull()), c] = 0
    df.loc[mask & (df["editor_journal"].isnull()), "editor_journal"] = "-"

    # Write out
    df.set_index(['node', 'year']).to_csv(TARGET_FILE)


if __name__ == '__main__':
    main()
