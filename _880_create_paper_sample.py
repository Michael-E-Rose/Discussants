#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Creates master file for paper sample."""

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler

from _012_list_presentations import write_stats
from _780_create_discussant_sample import read_data_file

NBER_FILE = Path("./119_NBER_sample/manuscripts.csv")
TARGET_FILE = Path("./880_paper_samples/main.csv")
OUTPUT_FOLDER = Path("./990_output")

TOP_JOURNALS = {"finance": {"Journal of Finance",
                            "Journal of Financial Economics",
                            "Review of Financial Studies"},
                "E": {"Journal of Monetary Economics"},
                "F": {"Journal of International Economics"},
                "G": {"Journal of Finance", "Journal of Financial Economics"},
                "econ": {'Review of Economic Studies',
                         'American Economic Review',
                         'Journal of Political Economy',
                         'Quarterly Journal of Economics',
                         'Econometrica'}
                }

EXP_STEPS = [1, 6, 15]
_exp_classes = {}
for idx, step in enumerate(EXP_STEPS):
    if idx == 0:
        new = {n: f"<{step+1}" for n in range(0, step+1)}
    else:
        prev = EXP_STEPS[idx-1]
        new = {n: f"{prev+1}-{step}" for n in range(prev+1, step+1)}
    if idx == len(EXP_STEPS)-1:
        new.update({n: f">{step}" for n in range(step+1, 60)})
    _exp_classes.update(new)


def deduplicate(seq):
    """Deduplciate sequence while preservering order."""
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def read_sjr(field=2000):
    """Read file with SCImago Journal Rank."""
    SJR_URL = "https://raw.githubusercontent.com/Michael-E-Rose/"\
              "SCImagoJournalRankIndicators/master/Scimago_JIFs.csv"
    cols = ['field', 'year', 'SJR', 'h-index', 'avg_citations', 'Sourceid']
    sjr = pd.read_csv(SJR_URL, usecols=cols, index_col=["Sourceid", "year"])
    if field:
        sjr = sjr[sjr["field"] == field]
    sjr = sjr[sjr["SJR"] > 0].drop(columns="field")
    return sjr


def make_depvar_kde_plot(df, fname, figsize=(7, 4)):
    """Plot KDE of standardized SJR and h-index."""
    # Plot
    fig, ax = plt.subplots(figsize=figsize)
    sns.kdeplot(x="SJR", data=df, ax=ax, color="b")
    sns.kdeplot(x="h-index", data=df, ax=ax, color="r")
    sns.kdeplot(x="avg_citations", data=df, ax=ax, color="g")
    # Aesthetics
    sjr_patch = mpatches.Patch(color='b', label='SJR')
    hindex_patch = mpatches.Patch(color='r', label='h-index')
    avgcitations_patch = mpatches.Patch(color='g', label='Avg. citations')
    plt.legend(handles=[sjr_patch, hindex_patch, avgcitations_patch])
    ax.set(xlim=(0, 1), xlabel="")
    # Save
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


def make_group_table(df, fname):
    """Create table giving certain statistics on groups."""
    # Count manuscripts
    counts = df["distinct_group"].value_counts().sort_index()
    counts["\\midrule Total"] = df["short"].nunique()
    # Compute group-wise means
    agg_cols = ["published", "citcount_2", "SJR", "top"]
    grouped = df.groupby("distinct_group")[agg_cols].mean()
    # Add total means
    grouped = grouped.T
    total_means = df.drop_duplicates(subset=["short"])[agg_cols].mean()
    grouped["\\midrule Total"] = total_means
    grouped = grouped.T
    out = counts.to_frame("Manuscripts").join(grouped)
    # Write out
    out["published"] *= 100
    out["top"] *= 100
    out.columns = ["Manuscripts", "Share published", "Avg. Citations (2 yrs.)",
                   "Avg. Journal SJR", "Share top journals"]
    out.round(1).to_latex(fname, escape=False)


def main():
    # Read in
    df = pd.read_csv(NBER_FILE, index_col="short")

    # Prepare individual data: editorial ranks, employer status
    data = read_data_file()
    editor_cols = ["managing_editor", "editor", "associate_editor"]
    data["editorial_pos"] = (data[editor_cols].sum(axis=1) > 0)*1
    data = data.drop(columns=editor_cols + ["editor_journal"])

    # Merge discussant data
    df = df.join(data, on=["discussant", "year"])
    df["practitioner_dis"] = df["aff_type"].isin(("govt", "ngov"))*1
    data = data.drop(columns=["aff_type"])

    # Set missing discussant values to 0
    mask_dis = (~df["discussant"].isna()) & (df["num_dis"] < 2)
    df.loc[mask_dis, data.columns] = df.loc[mask_dis, data.columns].fillna(0)
    df["diseuclid_top"] = (df["euclid"] >= df["euclid"].quantile(0.75))*1
    df["status_dis"] = df["experience"].replace(_exp_classes)
    df = df.rename(columns={"editorial_pos": "editor_dis"})

    # Add author data in year before publication
    idx_cols = ["short", "pub_year"]
    df["pub_year"] -= 1
    auth = (df.reset_index().set_index(idx_cols)
              ['author_scopus'].str.split(";", expand=True)
              .stack().to_frame("author")
              .droplevel(len(idx_cols)).reset_index())
    df["pub_year"] += 1
    auth = (auth.join(data, on=['author', 'pub_year'])
                .drop(columns=['editorial_pos']))
    exp = (auth.groupby(["short", "pub_year"])["experience"].agg(["min", "max"])
               .add_prefix("exp").add_suffix("_auth")
               .reset_index(level="pub_year", drop=True))
    auth_data = (auth.groupby(["short", "pub_year"]).sum()
                     .reset_index(level="pub_year", drop=True))
    auth_data = auth_data.join(exp)
    df = df.join(auth_data, lsuffix="_dis", rsuffix="_auth")

    # Set missing author values to 0
    mask_pub = df["published"] == 1
    fill_columns = [c for c in df.columns if c.endswith("_auth")]
    df.loc[mask_pub, fill_columns] = df.loc[mask_pub, fill_columns].fillna(0)

    # Compute author experience classes
    df["statusmin_auth"] = df["expmin_auth"].replace(_exp_classes)
    df["statusmax_auth"] = df["expmax_auth"].replace(_exp_classes)
    order = deduplicate(_exp_classes.values()) + ["All"]
    tab = pd.crosstab(df["statusmin_auth"], df["statusmax_auth"], margins=True)
    tab = tab.T[order].T[order].rename(columns={"All": "Total"})
    tab.index.name = "Youngest author"
    tab.columns.name = "Oldest author"
    fname = OUTPUT_FOLDER/"Tables"/"type_tabulation_status.tex"
    tab.style.to_latex(fname)

    # Add group's mean author data in year of discussion (acc. for joint workshops)
    group_map = (df['group'].str.split("-", expand=True)
                   .stack().to_frame("distinct_group")
                   .reset_index(level=1, drop=True))
    idx_cols = ["distinct_group", "year"]
    group_long = (group_map.join(df)
                           .reset_index().set_index(idx_cols)
                           ['author_scopus'].str.split(";", expand=True)
                           .stack().to_frame("author")
                          .droplevel(len(idx_cols)).reset_index())
    group_data = group_long.join(data, on=['author', 'year']).fillna(0)
    group_data = group_data[["distinct_group", "euclid"]]
    group_means = (group_data.groupby(["distinct_group"]).agg(["mean", "max"])
                             .droplevel(0, axis=1)
                             .add_prefix("euclid-").add_suffix("_group"))
    groups = (group_map.reset_index()
                       .join(group_means, on=["distinct_group"])
                       .groupby("short").mean())
    df = df.join(groups)

    # SCImago Journal Rank indicator
    df = df.merge(read_sjr(), 'left', left_on=['source', 'pub_year'],
                  right_index=True, indicator=True)
    if 'left_only' in df['_merge'].tolist():
        without = df[df['_merge'] == 'left_only']['journal'].dropna().unique()
        print(f">>> {len(without)} journals without SJR in at least one year:")
        print("; ".join(without))
    df = df.drop(columns="_merge")

    # Journal status
    top_columns = []
    for label, journals in TOP_JOURNALS.items():
        df["top_" + label] = df["journal"].apply(lambda x: int(x in journals))
        top_columns.append("top_" + label)
    mask_journals = df['type'] == 'Journal'
    df.loc[~mask_journals, top_columns] = np.nan

    # Statistics
    published = df[(df['published'] == 1) & mask_journals]
    authors = [d.strip() for l in published['author_scopus'].str.split(";")
               for d in l]
    pub_discussed = published[~published["euclid_dis"].isna()]
    discussants = [d.strip() for l in
                   pub_discussed['discussant'].dropna().str.split(";")
                   for d in l]
    stats = {"N_of_obsj": published.shape[0],
             "N_of_obsj_discussed": pub_discussed.shape[0],
             "N_of_obsj_discussants_scopus": len(set(discussants)),
             "N_of_obsj_authors": len(set(authors))}
    write_stats(stats)
    print(">>> Distribution of journal occurences:")
    print(df['journal'].value_counts())

    # Write out
    df = df.drop(columns=['author_scopus', 'discussant', 'eid'])
    df.to_csv(TARGET_FILE, index_label="short")

    # Create category-based group-level description tables
    df["top"] = df["top_econ"] + df["top_finance"]
    group_map = (df['group'].str.split("-", expand=True)
                            .stack().to_frame("distinct_group")
                            .reset_index(level=1, drop=True))
    temp = group_map.join(df)
    mask_discussed = temp["has_discussion"] == 1
    with_dis = temp[mask_discussed].reset_index()
    fname = OUTPUT_FOLDER/"Tables"/"category-dis_summary.tex"
    make_group_table(with_dis, fname)
    without_dis = temp[~mask_discussed].reset_index()
    fname = OUTPUT_FOLDER/"Tables"/"category-nodis_summary.tex"
    make_group_table(without_dis, fname)

    # Plot dependent variables on journal quality
    scaler = MinMaxScaler()
    dep_vars = ["SJR", "h-index", "avg_citations"]
    df[dep_vars] = scaler.fit_transform(df[dep_vars])
    fname = OUTPUT_FOLDER/"Figures"/"kdeplot_journal.pdf"
    make_depvar_kde_plot(df, fname)


if __name__ == '__main__':
    main()
