#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Gets list of titles and corresponding discussants of papers presented
at specific NBER Summer Institutes and writes statistics of presentations.
"""

from pathlib import Path

import pandas as pd

NBER_FILE = "https://raw.githubusercontent.com/Michael-E-Rose/"\
            "NBERSummerInstitutes/master/output/by_title.csv"
SCOPUS_FILE = Path("./005_identifiers/discussants.csv")
AFFMAP_FILE = Path("./010_affiliation_mappings/tilburg.csv")
TARGET_FILE = Path("./012_presentations/entries.csv")
OUTPUT_FOLDER = Path("./990_output")

MEETINGS_WITH = ['IFM', 'EFEL', 'AP', 'CF', 'RISK', 'AMRE', 'REAL', 'PERE']
MEETINGS_WITHOUT = ['EFCE', 'EFFE', 'ME']
MISSING_DIS = ("INFORMAL FINANCIAL NETWORKS: BROKERAGE AND THE FINANCING OF COMMERCIAL PROPERTIES",)
DATA_RANGE = range(2000, 2009+1)
TITLE_CORRECTION = {
    "FINANCIAL LIBERALIZATION AND THE ALLOCATION OF INVESTMENT: MICRO EVIDENCE FROM DEVELOPING COUNTRIES": "DOES FINANCIAL LIBERALIZATION IMPROVE THE ALLOCATION OF INVESTMENT? MICRO EVIDENCE FROM DEVELOPING COUNTRIES"
}
# Ignore these affiliations
PLATFORMS = ("NBER", "CEPR", "ECGI", "CREST", "IZA", "BREAD", "WIAS", "RIETI",
             "CREI", "CREI", "SIFR")
_aff_map = pd.read_csv(AFFMAP_FILE, index_col=0)["new"].dropna().to_dict()
_aff_correction = {"UC, ": "UNIVERSITY OF CALIFORNIA, "}


def clean_discussant(s):
    """Clean entries of discussants and prepare for merge."""
    s = str(s).replace(".0", "").replace("nan", "")
    return s + ";"


def find_affiliations(authors, sep=";"):
    """Extract affiliation information from author information."""
    def clean_aff(name):
        """Clean affiliation string following the author name."""
        name = name.replace("JR.,", "")
        if "," not in name:
            return None
        aff = name.split(",", 1)[-1].strip()
        for a in PLATFORMS:
            aff = aff.replace(" " + a, "")
        if aff.endswith(" and"):
            aff = aff[:-4]
        return aff.strip().strip(",")
    affs = [clean_aff(x) for x in authors.split(sep)]
    return sep.join(list(filter(None, affs)))


def get_affiliations(df, col):
    """Extract affiliations from an author's name."""
    idx_cols = ["title", "year"]
    affs = (df.set_index(idx_cols)[col].dropna().apply(find_affiliations)
              .to_frame("aff").reset_index())
    affs = affs[affs["title"] != "-"]
    affs = (affs.set_index(idx_cols)["aff"].str.split(";", expand=True)
                .stack().to_frame("aff")
                .reset_index(drop=True, level=len(idx_cols)).reset_index())
    affs["aff"] = affs["aff"].str.upper().replace(_aff_map)
    for old, new in _aff_correction.items():
        affs["aff"] = affs["aff"].str.replace(old, new)
    return affs


def read_tilburg_rankings(interpolated=True):
    """Read unweighted and JIF weighted Tilburg Economics Ranking."""
    # Create URLs
    TILBURG_URL = 'https://raw.githubusercontent.com/Michael-E-Rose/'\
                  'TilburgEconomicsRanking/master/combined/'
    unweighted = TILBURG_URL + "Tilburg_University"
    weighted = TILBURG_URL + "Journal_Impact_Factor"
    if interpolated:
        unweighted += "_interpolated"
        weighted += "_interpolated"
    unweighted += ".csv"
    weighted += ".csv"
    # Read in
    df1 = (pd.read_csv(unweighted, index_col=[0, 1])
             .add_prefix("Tilburg_").add_suffix("_unweighted"))
    df2 = (pd.read_csv(weighted, index_col=[0, 1])
             .add_prefix("Tilburg_").add_suffix("_weighted"))
    return (df1.join(df2, how="outer").reset_index()
               .rename(columns={"University": "aff"}))


def write_stats(stat_dct):
    """Write out textfiles as "filename: content" pair."""
    for key, cont in stat_dct.items():
        fname = (OUTPUT_FOLDER/"Statistics"/key).with_suffix(".txt")
        with open(fname, "w") as out:
            out.write(f"{int(cont):,}")


def main():
    # Read in and subset
    nber = pd.read_csv(NBER_FILE).drop(columns="session")
    nber["link"] = (~nber["link"].isnull())*1
    nber["title"] = nber["title"].str.upper().replace(TITLE_CORRECTION)
    idx_cols = list(nber.columns)
    idx_cols.remove("group")
    nber = (nber.set_index(idx_cols)["group"].str.split("; ", expand=True)
                .stack().to_frame("group")
                .reset_index(drop=True, level=len(idx_cols)).reset_index())
    mask = (nber["year"].isin(DATA_RANGE) &
            nber["group"].isin(MEETINGS_WITH+MEETINGS_WITHOUT))
    nber = nber[mask]
    nber = nber.drop_duplicates(subset=["title", "group", "year", "start"])

    # Affiliation ranks of authors and discussants
    auth_affs = get_affiliations(nber, col="author")
    dis_affs = get_affiliations(nber, col="discussant")
    ranks = read_tilburg_rankings()
    merge_cols = ["aff", "year"]
    auth_affs = auth_affs.merge(ranks, "left", on=merge_cols, indicator=True)
    dis_affs = dis_affs.merge(ranks, "left", on=merge_cols, indicator=True)
    dis_unmerged = dis_affs[dis_affs["_merge"] == "left_only"][merge_cols]
    auth_unmerged = auth_affs[auth_affs["_merge"] == "left_only"][merge_cols]
    unmerged = pd.concat([auth_unmerged, dis_unmerged])
    if not unmerged.empty:
        unmerged_counts = unmerged["aff"].value_counts()
        print(f">>> {unmerged_counts.shape[0]:,} institutions w/o ranks")
        with pd.option_context('display.max_rows', None):
            print(unmerged_counts)
    auth_affs = (auth_affs.drop(columns=["_merge", "year"])
                          .groupby("title").mean())
    dis_affs = (dis_affs.drop(columns=["_merge", "year"])
                        .groupby("title").mean())

    # Compare propensity to link to the manuscript
    nber["Group status"] = nber["group"].apply(
        lambda x: "with" if x in MEETINGS_WITH else "without")
    grouped = nber.groupby("Group status")["link"].agg(["sum", "count"])
    print(">>> Share of papers with link in program by category")
    print((grouped["sum"]/grouped["count"])*100)
    nber = nber.drop(columns=["venue", "date", "link", "Group status"])

    # Merge discussant IDs
    groupby_cols = ['year', 'title', 'author', 'start', 'end', 'group', 'organizer']
    nber = (nber.set_index(groupby_cols)["discussant"].fillna("").str.split("; ", expand=True)
                .stack().to_frame("discussant")
                .reset_index(drop=True, level=len(groupby_cols)).reset_index())
    nber["discussant"] = (nber["discussant"].str.split(",").str[0]
                                            .str.upper().str.replace(".", ""))
    dis = pd.read_csv(SCOPUS_FILE, index_col=0, usecols=["Name", "Scopus_ID"])
    dummy = pd.DataFrame({"-": {"Scopus_ID": "-"}, "": {"Scopus_ID": ""}}).T
    dis = pd.concat([dis, dummy])
    nber = nber.merge(dis, "left", left_on=["discussant"], right_index=True,
                      indicator=True)
    if "left_only" in nber["_merge"].unique():
        print(">>> Unmerged discussants:")
        mask = ((nber["_merge"] == "left_only") & (nber["discussant"] != ""))
        unmerged = nber[mask]["discussant"].unique()
        print("; ".join(unmerged))
    nber = (nber.drop(columns=["_merge", "discussant"])
                .rename(columns={"Scopus_ID": "discussant"}))
    nber.loc[nber["title"].isin(MISSING_DIS), "discussant"] = "-"

    # Combine disussants if same presentation has multiple discussants
    nber["discussant"] = nber["discussant"].apply(clean_discussant)
    before = nber.shape[0]
    nber = nber.groupby(groupby_cols)["discussant"].sum().reset_index()
    n_pres_dis_mult = before - nber.shape[0]
    nber["discussant"] = nber["discussant"].str.rstrip(";")

    # Compute duration
    corrections = (("12:00 AM", "12:00 PM"), ("12:15 AM", "12:15 PM"),
                   ("12:30 AM", "12:30 PM"), (".", ""), (" n", " pm"),
                   (" N", " PM"))
    for col in ("start", "end"):
        for s, repl in corrections:
            nber[col] = nber[col].str.replace(s, repl)
        nber[col] = nber["year"].astype(str) + " " + nber[col]
        nber[col] = pd.to_datetime(nber[col], format="%Y %B %d, %I:%M %p")
    nber["duration"] = (nber["end"] - nber["start"]).dt.seconds/60

    # Correct duration for presentations in same slot
    group_cols = ["group", "year", "start", "end"]
    factor = nber.groupby(group_cols)["duration"].transform('size')
    nber["duration"] = nber["duration"]/factor

    # Merge average affiliation ranks
    rank_cols = ['Tilburg_Rank_unweighted', 'Tilburg_Rank_weighted']
    nber = nber.join(auth_affs[rank_cols], on="title")
    nber = nber.join(dis_affs[rank_cols], on="title", lsuffix="_auth", rsuffix="_dis")

    # Write out
    nber = nber.sort_values(by=['title', "group"])
    rank_cols = [c for c in nber.columns if c.startswith("Tilburg_")]
    order = ['title', 'author', 'discussant', 'group', 'organizer', 'year',
             'duration', 'start'] + rank_cols
    nber[order].to_csv(TARGET_FILE, index=False)

    # Statistics for presentations
    mask_joint = nber.duplicated(subset=["title", "start"])
    presentations = nber[~mask_joint]
    pres_dis = [x for x in presentations["discussant"] if x != ""]
    dis = [a for l in pres_dis for a in l.split(";")]
    dis_sco = {a for a in set(dis) if a.isdigit()}
    print(f">>> {len(dis_sco):,} distinct known discussants")
    nber["year"] = nber["year"].astype(str)
    all_meetings = nber[['year', 'group']].apply(lambda x: " ".join(x), axis=1)
    print(f">>> {all_meetings.nunique():,} different workshops")
    print(">>> Presentations by meeting:\n",
          pd.crosstab(nber['group'], nber['year'], margins=True))
    stats = {"N_of_pres": presentations.shape[0],
             "N_of_pres_title_unknown": sum(nber["title"] == "-"),
             "N_of_pres_joint": mask_joint.sum(),
             "N_of_pres_discussed": len(pres_dis),
             "N_of_pres_discussants_unknown": dis.count("-"),
             "N_of_pres_discussants_scopus": len(dis_sco),
             "N_of_workshops": all_meetings.nunique()}
    write_stats(stats)


if __name__ == '__main__':
    main()
