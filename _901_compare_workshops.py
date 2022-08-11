#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Plots comparisons of workshops w/ and w/o discussants."""

from pathlib import Path

import matplotlib as mpl
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy.stats import ttest_ind

from _119_prepare_NBER_data import figure_font, figure_params

SAMPLE_FILE = Path("./119_NBER_sample/manuscripts.csv")
OUTPUT_FOLDER = Path("./990_output")

mpl.rc('font', **figure_font)
plt.rcParams.update(figure_params)


def add_annotation(ax, p, x=0.43, y=0.95, fontsize=12):
    """Annotate `ax` with p value and significance stars."""
    text = f"p = {p:.2f}{p_to_stars(p)}"
    ax.annotate(text, (x, y*ax.get_ylim()[1]), fontsize=fontsize)


def add_vertical_bar(ax, data, y, ylabel, title):
    """Plot vertical bar onto `ax`."""
    sns.barplot(x="has_discussion", y=y, data=data, ax=ax)
    ax.set(ylabel=ylabel, xlabel="", title=title)


def make_single_barplotpair(df, fname, col, ylabel, group_cols=["group", "year"]):
    """Plots bars with mean error indicators and p-values of t-tests for
    comparison of the variable `col`.
    """
    # Subset data
    df = df[df[col] > 0]
    mask = df["has_discussion"] == "With"
    papers_with = df.loc[mask]
    papers_without = df.loc[~mask]
    sis_with = papers_with.groupby(group_cols)[col].mean()
    sis_without = papers_without.groupby(group_cols)[col].mean()
    # Plot
    fig, axes = plt.subplots(1, 2, sharex=True, sharey=True, figsize=(12, 6))
    # Left plot (paper-level)
    add_vertical_bar(axes[0], df, col, ylabel, "Paper level")
    t = ttest_ind(papers_with[col].dropna(), papers_without[col].dropna())
    add_annotation(axes[0], t[1])
    # Right plot (SI-level)
    grouped = (df.groupby(group_cols + ["has_discussion"])[col].mean()
                 .reset_index())
    add_vertical_bar(axes[1], grouped, col, ylabel, "Workshop averages")
    t = ttest_ind(sis_with, sis_without)
    add_annotation(axes[1], t[1])
    # Save
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


def p_to_stars(p, thres=(0.1, 0.05, 0.01)):
    """Return stars for significance values."""
    n_stars = len([t for t in thres if p < t])
    return "".join("*"*n_stars)


def main():
    # Read presentations
    df_cols = ["short", "has_discussion", "duration", "group", "year",
               "Tilburg_Rank_weighted_auth", 'pres_flesch',
               'pres_fleschkincaid', 'pres_gunningfog', 'pres_smog']
    df = pd.read_csv(SAMPLE_FILE, usecols=df_cols)
    df["has_discussion"] = df["has_discussion"].replace({0: "Without", 1: "With"})

    # Plot duration comparison
    fname = OUTPUT_FOLDER/"Figures"/"barplot_duration.pdf"
    make_single_barplotpair(df, fname=fname, col="duration",
                            ylabel="Duration (in min)")

    # Plot affiliation rank comparison
    fname = OUTPUT_FOLDER/"Figures"/"barplot_tilburg.pdf"
    make_single_barplotpair(df, fname=fname, col="Tilburg_Rank_weighted_auth",
                            ylabel="Avg. affiliation rank")

    # Plot readability comparison
    measures = {'flesch': "Flesch reading ease",
                'fleschkincaid': "Flesch-Kincaid score",
                'gunningfog': "Gunning fog index",
                'smog': 'Simple Measure of Gobbledygook'}
    n_read = df.shape[0] - df["pres_flesch"].isna().sum()
    print(f">>> Using readability information for {n_read:,} "
          f"(out of {df.shape[0]}) papers")
    for col, ylabel in measures.items():
        fname = OUTPUT_FOLDER/"Figures"/f"barplot_{col}.pdf"
        make_single_barplotpair(df.copy(), fname=fname, col="pres_" + col,
                                ylabel=ylabel)

    # Combine four plots
    variables = ("duration", "Tilburg_Rank_weighted_auth", "pres_gunningfog",
                 "pres_smog")
    ylabels = ("Duration (in min)", "Avg. affiliation rank",
               "Gunning fog index", "Simple Measure of Gobbledygook")
    group_cols = ["group", "year"]
    fig = plt.figure(figsize=(15, 10))
    outer = gridspec.GridSpec(2, 2, wspace=0.25, hspace=0.1)
    for i in range(4):
        # Set variables
        var = variables[i]
        temp = df[df[var] > 0]
        mask = temp["has_discussion"] == "With"
        papers_with = temp.loc[mask]
        papers_without = temp.loc[~mask]
        sis_with = papers_with.groupby(group_cols)[var].mean()
        sis_without = papers_without.groupby(group_cols)[var].mean()

        # Initiate inner spec
        inner = gridspec.GridSpecFromSubplotSpec(1, 2, wspace=0.15,
            hspace=0.15, subplot_spec=outer[i])
        upper_row = i < 2

        # Left pair
        ax = plt.Subplot(fig, inner[0])
        if upper_row:
            title = "Paper-level"
        else:
            title = ""
        add_vertical_bar(ax, temp, var, ylabels[i], title)
        t = ttest_ind(papers_with[var].dropna(), papers_without[var].dropna())
        add_annotation(ax, t[1])
        if upper_row:
            plt.setp(ax.get_xticklabels(), visible=False)
        fig.add_subplot(ax)

        # Right pair
        ax = plt.Subplot(fig, inner[1])
        grouped = (df.groupby(group_cols + ["has_discussion"])[var].mean()
                     .reset_index())
        if upper_row:
            title = "Workshop averages"
        else:
            title = ""
        add_vertical_bar(ax, grouped, var, "", title)
        t = ttest_ind(sis_with, sis_without)
        add_annotation(ax, t[1])
        plt.setp(ax.get_yticklabels(), visible=False)
        if upper_row:
            plt.setp(ax.get_xticklabels(), visible=False)
        fig.add_subplot(ax)

    # Save
    fname = OUTPUT_FOLDER/"Figures"/"barplot_combined.pdf"
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


if __name__ == '__main__':
    main()
