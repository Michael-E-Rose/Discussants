#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Combines all NBER-related information for manuscripts presented exactly
once at Finance-related NBER Summer Institutes.
"""

from itertools import product
from pathlib import Path
from string import punctuation, whitespace

import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from _012_list_presentations import write_stats, MEETINGS_WITH, TITLE_CORRECTION
from _110_get_Scopus_bibliometrics import compute_readability

AUTHOR_FILE = Path("./005_identifiers/unpublished.csv")
NBER_FILE = Path("./012_presentations/entries.csv")
MAPPING_FILE = Path("020_title_mapping/mapping.csv")
AUX_FOLDER = Path("./025_paper_auxiliary")
SCOPUS_FILE = Path("110_bibliometrics/metrics.csv")
TARGET_FILE = Path("./119_NBER_sample/manuscripts.csv")
OUTPUT_FOLDER = Path("./990_output")
MAINTENANCE_FOLDER = Path("./999_maintenance/")

_string_mapper = {k: "" for k in punctuation + whitespace}
_joint_sessions = {('IFM', 2001, (4, 4)), ('RISK', 2007, False),
                   ('RISK', 2008, False)}
_missing_auth_ids = []

figure_font = {'family': 'serif', 'serif': 'Utopia', 'size': 15}
mpl.rc('font', **figure_font)
figure_params = {'legend.fontsize': 15,
                 'axes.labelsize': 15,
                 'axes.titlesize': 20,
                 'xtick.labelsize': 15,
                 'ytick.labelsize': 15}
plt.rcParams.update(figure_params)


def compute_timedelta_months(s):
    """Compute the timedelta between two dates in months."""
    first = s.submitted
    last = s.accepted
    if not (first and last):
        return None
    return 12*(last.year-first.year) + (last.month-first.month)


def find_author(p, sample):
    """Mark paper `p` if one of its authors is in `sample`."""
    return len(set(p["author_scopus"]).intersection(sample)) > 1


def find_author_ids(s, id_mapping):
    """Find IDs of authors of unpublished manuscripts."""
    out = []
    for author in s:
        author = author.split(",", 1)[0].upper()
        try:
            auth_id = id_mapping[author]
        except KeyError:
            auth_id = "-"
            _missing_auth_ids.append(author)
        out.append(auth_id)
    return ";".join(out)


def make_age_boxplot(df, fname):
    """Visualize distribution of age variable as boxplot."""
    # Plot
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.boxplot(x="age", data=df, ax=ax)
    ax.set(xlabel="Years until publication")
    # Save
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


def make_overview_table(df, fname):
    """Construct overview table showing number of published presentations
    with number of presentations per year and NBER group.
    """
    def tuple_to_share(t):
        """Divide first number of tuple by second."""
        return f"{int(round(t[0]/float(t[1]), 2)*100)}\%"

    def tuple_to_string(t):
        """Stringfy a 2-tuple with second element in parenthesis."""
        return f"{int(t[0])} ({t[1]})"

    def get_totals(s):
        """Sum numbers of papers published as well as presented."""
        values = [e.strip(")").split(" (") for e in s.values]
        values = [(int(n[0]), int(n[1])) for n in values]
        published = sum(n[0] for n in values)
        total = sum(n[1] for n in values)
        return published, total

    years = sorted(df['year'].astype(int).unique())
    groups = sorted(df['group'].unique())
    overview = pd.DataFrame(columns=years, index=groups)
    combs = product(years, groups)
    for year, group in combs:
        mask = (df['year'] == year) & (df['group'] == group)
        published = int(df[mask]['published'].sum())
        total = int(mask.sum())
        if total > 0:
            overview[year][group] = f"{published} ({total})"
        else:
            overview[year][group] = "0 (0)"
    # Correct for joint workshops using a temporary copy
    temp = overview[years].copy()
    for group, year, correction in _joint_sessions:
        if not correction:  # Complete session was held jointly
            temp.loc[group, year] = "0 (0)"
        else:  # Only part of the sessions were joint
            temp.loc[group, year] = tuple_to_string(correction)
    # Two rows with totals and shares, corrected for joint presentations
    coltotal = temp.apply(get_totals)
    n_published = coltotal.iloc[0].sum()
    n_presented = coltotal.iloc[1].sum()
    colshare = coltotal.apply(tuple_to_share)
    colshare['total'] = tuple_to_share((n_published, n_presented))
    colshare.name = 'share'
    coltotal = coltotal.apply(tuple_to_string)
    coltotal['total'] = tuple_to_string((n_published, n_presented))
    coltotal.name = f'\cmidrule{{1-{len(years)+1}}} total'
    # Two columns with totals and shares
    overview['total'] = overview[years].apply(get_totals, axis=1)
    overview['share'] = overview['total'].apply(tuple_to_share)
    overview['total'] = overview['total'].apply(tuple_to_string)
    # Mark joint sessions
    for group, year, correction in _joint_sessions:
        val = overview.loc[group, year]
        if not correction:
            overview.loc[group, year] = f"\\textit{{{val}}}"
        else:
            overview.loc[group, year] = val + "*"
    # Mark groups w/ discussants
    overview.index = [f"\\textbf{{{c}}}" if c in MEETINGS_WITH else c
                      for c in overview.index]
    # Combine
    overview = pd.concat([overview, coltotal.to_frame().T, colshare.to_frame().T])
    overview = overview.fillna("").replace("0 (0)", "")
    # Save
    column_format = "l"*(len(years)+1) + "|" + "l"*3
    overview.style.to_latex(fname, column_format=column_format)


def read_mapping():
    """Read mapping of title to EID."""
    mapping = pd.read_csv(MAPPING_FILE, index_col=0).drop(columns="comment")
    mapping.index = mapping.index.map(standardize)
    mapping["published"] = (~mapping["published_version"].isnull())*1
    return mapping


def read_jel():
    """Read two JEL-Codes files turned into dummies."""
    df = pd.concat([pd.read_csv(f, index_col="short") for
                    f in AUX_FOLDER.glob("JEL*.csv")])
    temp = (df["JEL"].str.split(", ").apply(pd.Series)
              .unstack()
              .reset_index(level=0, drop=True)
              .reset_index().set_index("short")
              .dropna())
    temp[0] = temp[0].str[:1]
    dummies = pd.get_dummies(temp[0]).add_prefix("JEL_").reset_index()
    return dummies.groupby("short").max()


def standardize(s):
    """Remove interpunctuation and whitespaces from a string."""
    return s.translate(str.maketrans(_string_mapper))


def main():
    # Read presentations and drop duplicated entries which are reporting errors
    nber = pd.read_csv(NBER_FILE)
    nber["index"] = nber["title"].apply(standardize)
    nber = nber.drop_duplicates(subset=["index", "group", "start"])
    print(f">>> Starting with {nber.shape[0]} entries..")

    # Merge abstracts of presented version
    abs_cols = ['title', 'year', 'abstract']
    abstracts = pd.read_csv(AUX_FOLDER/"abstracts_programs.csv", na_values="-",
                            index_col=[0, 1], usecols=abs_cols,)
    read = abstracts["abstract"].apply(compute_readability).dropna()
    read = (read.add_prefix("pres_")
                .reset_index().rename(columns={"title": "index"}))
    read["index"] = read["index"].str.upper().replace(TITLE_CORRECTION).apply(standardize)
    nber = (nber.merge(read, "left", on=["index", "year"])
                .drop_duplicates(subset=["title", "group", "start"]))

    # Merge mapping of titles to EIDs
    nber = (nber.join(read_mapping(), on="index")
                .drop_duplicates(subset=["index", "group", "start"])
                .set_index("index"))

    # Merge Scopus metrics
    nber = nber.join(pd.read_csv(SCOPUS_FILE, index_col="eid"), how='left',
                     on="eid", rsuffix="_scopus")
    nber["published"] = nber["published"].fillna(0)

    # Construct overview table
    fname = OUTPUT_FOLDER/"Tables"/"workshop_counts.tex"
    make_overview_table(nber, fname)
    stats = {"N_of_workshops_joint": len(_joint_sessions)}

    # Drop presentations w/o indicated title
    nber = nber[nber.index != ""]
    print(f"... continuing with {nber.shape[0]} entries with known title")

    # Add group dummies accounting for joint sessions
    cols = ["title", "start", "year"]
    dfs = [nber[cols + ["group"]],
           pd.get_dummies(nber["group"], prefix="group")]
    grouped = pd.concat(dfs, axis=1).groupby(cols)
    strings = grouped["group"].apply(lambda x: "-".join(sorted(x)))
    dummies = grouped.sum()
    temp = pd.concat([dummies, strings], axis=1)
    nber = nber.drop_duplicates(subset=["title", "start"]).reset_index()
    assert(nber.shape[0] == temp.shape[0])
    nber = nber.drop(columns="group").join(temp, on=cols)
    print(f"... left with {nber.shape[0]} manuscripts after accounting "
          f"for joint sessions")

    # Separate published and unpublished presentations
    mask_published = nber["published"] == 1
    unpublished = nber[~mask_published].copy()
    published = nber[mask_published].copy()
    stats["N_of_pres_published"] = published.shape[0]
    stats["N_of_pubs"] = published["published_version"].nunique()
    stats["N_of_pubs_joint"] = sum([1 for x in published["group"] if "-" in x])
    stats["N_of_pubs_scopus"] = published['eid'].nunique()

    # Add IDs of authors of unpublished papers
    unpub_authors = pd.read_csv(AUTHOR_FILE, index_col="Name").dropna()
    unpub_authors = unpub_authors["Scopus_ID"].astype("uint64").astype(str).to_dict()
    unpublished["author_scopus"] = unpublished["author"].str.split("; ").apply(
        lambda s: find_author_ids(s, unpub_authors))
    if _missing_auth_ids:
        print(f">>> {len(_missing_auth_ids)} authors w/o Scopus ID:")
        print(_missing_auth_ids)

    # Join published and unpublished papers
    out = pd.concat([published, unpublished], sort=False)
    out["short"] = out["published_version"].fillna(out["index"]).apply(standardize)
    out = out.drop(columns=["title", "index", "published_version", "organizer"])

    # Save list of unpublished presentations
    unpublished = unpublished.set_index("title")[["author", "year", "group"]]
    unpublished.to_csv(TARGET_FOLDER/"unpublished.csv")

    # Mark presentations with multiple discussants
    out["num_dis"] = out["discussant"].fillna("").str.count(";") + 1
    out.loc[out["discussant"].isnull(), "num_dis"] = 0
    stats["N_of_pres_discussants_multiple"] = sum(out["num_dis"] > 1)

    # Drop manuscripts that were presented multiple times
    mask_mult = out.duplicated("short", keep=False)
    stats["N_of_manus_multiple"] = out[mask_mult]["short"].nunique()
    out = out[~mask_mult]
    print(f"... keeping {out.shape[0]} which were presented once only")

    # Compute variables
    out['num_auth'] = out['author'].apply(lambda s: s.count(";")+1)
    out['age'] = out['pub_year'] - out['year']
    out["has_discussion"] = 1 - out["discussant"].isnull()*1
    out.loc[out["discussant"] == "-", "discussant"] = None

    # Merge JEL codes
    out = out.join(read_jel(), on="short")
    no_jel = out[(out["JEL_G"].isna()) & (out["type"] == "Journal")]
    if not no_jel.empty:
        print(f">>> {no_jel.shape[0]} papers w/o JEL codes:")
        print(no_jel[["eid", "journal", "short"]])
    del no_jel

    # Mark papers whose authors presented & published in both categories
    temp = out[out["published"] == 1].copy().dropna(subset=["author_scopus"])
    temp["author_scopus"] = temp["author_scopus"].str.split(";")
    no_discussion = temp["discussant"].isna()
    left = [a for l in temp.loc[no_discussion, "author_scopus"] for a in l]
    right = [a for l in temp.loc[~no_discussion, "author_scopus"] for a in l]
    both = set(left).intersection(right)
    temp["author_both"] = temp.apply(lambda s: find_author(s, both), axis=1)
    print(f">>> Found {temp['author_both'].sum()} manuscripts by {len(both)} "
          "authors who published papers presented in both categories of groups")
    out["author_both"] = out["short"].isin(temp.loc[temp["author_both"], "short"])*1

    # Write out
    out = out.drop(columns="author").sort_values("short").set_index('short')
    out.to_csv(TARGET_FILE)

    # Plot age distribution
    make_age_boxplot(out, fname=OUTPUT_FOLDER/"Figures"/"boxplot_age.pdf")

    # Statistics
    mask_dis = out["has_discussion"] == 1
    print(">>> Share of manuscripts that got published: "
          f"{out[mask_dis]['published'].mean():.1%} (discussed) vs. "
          f"{out[~mask_dis]['published'].mean():.1%} (non-discussed)")
    published = out[out['published'] == 1]
    pub_discussed = published[published["has_discussion"] == 1]
    scopus = {col: {a for l in published[col].dropna() for a in l.split(";")}
              for col in ["author_scopus", "discussant"]}
    stats["N_of_pubs_books"] = sum(published[~published["eid"].isna()]['type'] != "Journal")
    stats.update({"N_of_pubs_discussed": pub_discussed.shape[0],
                  "N_of_pubs_authors": len(scopus["author_scopus"]),
                  "N_of_pubs_discussants_scopus": len(scopus["discussant"]),
                  "N_of_pubs_discussants_unknown": sum(pub_discussed["discussant"].isna())})
    write_stats(stats)


if __name__ == '__main__':
    main()
