#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Creates master file for discussant sample: All presentations presented
exactly once.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from numpy import nan
from scipy.stats import kstest, linregress

NBER_FILE = Path("./119_NBER_sample/manuscripts.csv")
TARGET_FILE = Path("./780_discussant_sample/master.csv")
OUTPUT_FOLDER = Path("./990_output")


def make_ecdf_plot(auth, dis, fname, figsize=(11, 10)):
    """Make empirical CDF plot comparing distributions of four variables
    of authors with discussants.
    """
    # Prepare data
    comp_vars = ["euclid", "experience", "coauth_neighborhood_45",
                 "informal_neighborhood_45"]
    auth = auth.set_index("short")[comp_vars]
    combined = auth.join(dis[comp_vars], how="inner", lsuffix="_auth",
                         rsuffix="_dis")
    # KS tests
    print(">>> Kolmogorov-Smirnov test on distinct distribution:")
    for c in comp_vars:
        test = kstest(combined[c + "_auth"], combined[c + "_dis"])
        print(f"... {c}: p-value = {test.pvalue:.2}")
    # Reshape
    combined = combined.reset_index(drop=True).reset_index()
    temp = pd.wide_to_long(combined, comp_vars, i="index", j="Type", sep="_",
                           suffix='\\w+')
    temp = temp.reset_index(level=1).reset_index(drop=True)
    rename = {"dis": "Discussants", "auth": "Authors"}
    temp["Type"] = temp["Type"].replace(rename)
    # Plot
    fig, axes = plt.subplots(2, 2, sharey=True, figsize=figsize)
    sns.ecdfplot(data=temp, x="euclid", hue="Type", ax=axes[0][0])
    axes[0][0].set(xlabel="Euclid")
    sns.ecdfplot(data=temp, x="experience", hue="Type", ax=axes[0][1],
                 legend=False)
    axes[0][1].set(xlabel="Experience")
    sns.ecdfplot(data=temp, x="coauth_neighborhood_45", hue="Type",
                 ax=axes[1][0], legend=False)
    axes[1][0].set(xlabel="Co-author neighborhood")
    sns.ecdfplot(data=temp, x="informal_neighborhood_45", hue="Type",
                 ax=axes[1][1], legend=False)
    axes[1][1].set(xlabel="Informal neighborhood")
    # Aesthetics
    axes[0][0].get_legend().set_title(None)
    # Save
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


def make_histogram(data, x, fname, figsize=5, ratio=1.5):
    """Create histogram of a Series `x` with empirical CDF as overlay."""
    from math import ceil

    # Plot empirical CDF
    ax = sns.displot(data=data, x=x, color="green", kind="ecdf",
                     height=figsize, aspect=ratio)
    max_lim = (data[x].max()/5) * 5
    ax.set(xlim=(0, max_lim), ylabel="Empirical cumulative density",
           xlabel="Discussant experience (in years)")
    # Add nomralized histogram
    ax2 = plt.twinx()
    n_bins = data[x].nunique() + 1
    sns.histplot(data=data, x=x, bins=n_bins, stat="percent", ax=ax2)
    ax2.set(ylabel="Frequency of observation (in %)")
    # Write out
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


def make_regplot(df, fname):
    """Create annotated side-by-side regplots with dots colored by group."""
    from matplotlib.colors import to_hex, Normalize

    # Color by group
    cmap = plt.cm.rainbow
    norm = Normalize(vmin=0, vmax=df["group"].nunique()-1)
    int_map = (df["group"].value_counts()
                 .reset_index().reset_index()
                 .set_index("index")
                 ["level_0"].to_dict())
    colors = [to_hex(cmap(norm(int_map[v]))) for v in df["group"].values]
    # Iniate plot
    fig, axes = plt.subplots(1, 2, figsize=(18, 6), sharey=True)
    # Plot scatter with regression line
    df["experience-mean_auth"] = df["experience-sum_auth"]/df["num_auth"]
    p1 = sns.regplot(x="experience-mean_auth", y="experience_dis", data=df,
                     ax=axes[0], ci=90, scatter_kws={'color': colors})
    p2 = sns.regplot(x="experience-max_auth", y="experience_dis", data=df,
                     ax=axes[1], ci=90, scatter_kws={'color': colors})
    axes[0].axis('scaled')
    axes[1].axis('scaled')
    # Annotate with correlation and slope
    for ax, p, agg in zip(axes, (p1, p2), ("mean", "max")):
        col = f"experience-{agg}_auth"
        # Compute correlation and slope
        corr = df[["experience_dis", col]].corr().iloc[0, 1]
        xs = p.get_lines()[0].get_xdata()
        ys = p.get_lines()[0].get_ydata()
        reg = linregress(xs, ys)
        # Annotate
        coords = (0.85*ax.get_xlim()[1], 0.1*ax.get_ylim()[1])
        text = f"b = {reg.slope:.2}\n\u03C1 = {corr:.2}"
        ax.annotate(text, xy=coords, fontsize=12, fontweight="bold")
    # Aethestics
    axes[0].set(xlabel="Authors' mean experience", ylabel="Discussant experience")
    axes[1].set(xlabel="Authors' max. experience", ylabel="")
    plt.subplots_adjust(wspace=0, hspace=0)
    for ax, agg in zip(axes, ("mean", "max")):
        ax.set(xlim=(-1, df[f"experience-{agg}_auth"].max()+1))
    # Add legend to right plot
    cols = ["experience_dis", "experience-max_auth", "group"]
    grouped = df.groupby("group").head(1)[cols].sort_values("group")
    dots = []
    for i, row in grouped.iterrows():
        idx = df.index.get_loc(i)
        dot_color = to_hex(cmap(norm(int_map[row["group"]])))
        new = axes[1].scatter(row['experience-max_auth'], row['experience_dis'],
                              facecolor=dot_color)
        dots.append(new)
    axes[1].legend(dots, grouped["group"].to_list(), loc="upper right",
                   prop={'size': 20})
    # Save figure
    plt.tight_layout(pad=-4)
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


def read_data_file():
    """Read file with all individual data."""
    data = pd.read_csv(Path("./440_person_data/all.csv"), low_memory=False,
                       dtype={"node": str})
    return data.set_index(["node", "year"])


def main():
    # Merge NBER with discussant data (in year of discussion)
    cols = ['short', 'year', 'group_AMRE', 'group_AP', 'group_CF',
            'group_EFCE', 'group_EFEL', 'group_EFFE', 'group_IFM', 'group_ME',
            'group_PERE', 'group_RISK', 'group', 'discussant', 'author_scopus',
            'num_dis', 'num_auth', 'has_discussion',
            'Tilburg_Rank_unweighted_dis', 'Tilburg_Rank_weighted_dis']
    df = pd.read_csv(NBER_FILE, index_col="short", usecols=cols)
    df = df.dropna(subset=["author_scopus"])
    data = read_data_file()
    data = data.drop(columns=['editor_journal', 'aff_type'])
    df = df.join(data, on=["discussant", "year"])
    rename = {"experience": "experience_dis", "euclid": "euclid_dis"}
    df = df.rename(columns=rename)

    # Fill empty discussant values with 0
    mask_dis = (~df["discussant"].isna()) & (df["num_dis"] == 1)
    df[mask_dis] = df[mask_dis].fillna(0)
    rank_cols = [c for c in df.columns if c.startswith("Tilburg")]
    for c in rank_cols:
        df.loc[df[c] == 0, c] = nan

    # Compute rank
    df["top_dis"] = (df["Tilburg_Rank_weighted_dis"].between(1, 30))*1
    df.loc[df["Tilburg_Rank_weighted_dis"].isna(), "top_dis"] = nan

    # Histogram with CDF overlay
    fname = OUTPUT_FOLDER/"Figures"/"histogram_disexperience.pdf"
    make_histogram(df, "experience_dis", fname)

    # Merge with author data (in year of discussion)
    idx_cols = ["short", "year"]
    auth_pub = (df.reset_index().set_index(idx_cols)
                  ['author_scopus'].str.split(";", expand=True)
                  .stack().to_frame("author")
                  .droplevel(len(idx_cols)).reset_index())
    auth_data = auth_pub.join(data, on=['author', 'year']).fillna(0)
    auth_agg = (auth_data[["short", "year", "euclid", "experience"]]
                         .groupby(["short", "year"]).agg([sum, max])
                         .fillna(0)
                         .reset_index().set_index("short")
                         .drop(columns="year"))
    auth_agg.columns = ["-".join(c) + "_auth" for c in auth_agg.columns]
    df = df.join(auth_agg)

    # Fill empty author values with 0
    auth_cols = [c for c in df.columns if c.endswith("_auth")]
    df[auth_cols] = df[auth_cols].fillna(0)

    # Write out
    df = df.drop(columns=['author_scopus', 'discussant', 'num_dis'])
    df.to_csv(TARGET_FILE, index_label="short", encoding="utf8")

    # Correlations
    print(">>> Pearson correlations of discussant and author values")
    for m in ("experience", "euclid"):
        cols = [c for c in df.columns if m in c]
        print(f"... {m}:")
        print(df[cols].corr().iloc[0].round(3))

    # Scatterplot of experience
    df = df.dropna(subset=["experience_dis"])
    fname = OUTPUT_FOLDER/"Figures"/"scatter_disauthexperience.pdf"
    make_regplot(df, fname)

    # Comparison of distributions
    rename = {"euclid_dis": "euclid", "experience_dis": "experience"}
    df = df.rename(columns=rename)
    df = df[df["has_discussion"] == 1]
    fname = OUTPUT_FOLDER/"Figures"/"ecdf_auth-dis.pdf"
    make_ecdf_plot(auth_data, df, fname)


if __name__ == '__main__':
    main()
