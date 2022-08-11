#!/usr/bin/env python3
# Author:  Michael E. Rose <michael.ernst.rose@gmail.com>
"""Plots the distributions of citations of papers in our sample."""

from datetime import datetime
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from pybliometrics.scopus import AbstractRetrieval, ScopusSearch
from tqdm import tqdm

from _119_prepare_NBER_data import figure_font, figure_params

mpl.rc('font', **figure_font)
plt.rcParams.update(figure_params)

NBER_FILE = Path("./119_NBER_sample/manuscripts.csv")
OUTPUT_FOLDER = Path("./990_output")


def citer_cited_comparison(s, find_col="discussant"):
    """Whether any of `find_col` is authoring a citing paper."""
    try:
        return sum([s["citing_author"].count(d) for d in s[find_col]])
    except (AttributeError, TypeError):
        return 0


def join_lists(s):
    """Join multiple lists."""
    return [x for l in s for x in l]


def make_citations_kdeplot(df, fname, figsize=(12, 6)):
    """Plot log of citations and KDE of when authors cite a discussed
    paper, depending on their status (discussant or not).
    """
    from numpy import log

    def lag_counts(df, col):
        """Multiply lag in index with number of occurences in `col`."""
        lst = list(zip(df[col], df.index))
        lst = [(int(t[0]) * [t[1]]) for t in lst if t[0] != 0]
        return list([e for sl in lst for e in sl if sl])

    # Compute cites by group of authors
    df["dis_cits_dis"] = df.apply(citer_cited_comparison, axis=1)
    df["n_paper"] = df["citing_author"].str.count("-") + 1
    dis_cited = df[df["dis_cits_dis"] > 0]
    discussants = join_lists(dis_cited["discussant"])
    print("... Discussants' citation pattern inferred from "
          f"{dis_cited.shape[0]:,} citations by "
          f"{len(set(discussants)):,} discussants of "
          f"{dis_cited['eid'].nunique():,} papers")
    discussed = ~df["discussant"].isnull()
    df.loc[discussed, "dis_cits"] = df["n_paper"]
    df.loc[~discussed, "cits"] = df["n_paper"]
    grouped = df.groupby("year").sum()
    # Plot
    fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)
    # Log distribution of citations
    grouped_log = (grouped.drop(columns="n_paper")
                          .apply(lambda n: log(n+1), axis=0))
    grouped_log = (grouped_log.reset_index()
                              .melt(id_vars="year",
                                    value_name="log(# of citations)"))
    sns.lineplot(data=grouped_log, x="year", y="log(# of citations)",
                 ax=axes[0], hue="variable", style="variable",
                 dashes={"dis_cits_dis": (1, 2), "dis_cits": "", "cits": ""})
    # KDE plots
    dis_cits_dis = lag_counts(grouped, "dis_cits_dis")
    sns.kdeplot(dis_cits_dis, ax=axes[1], cut=0, linestyle=":")
    dis_cits = lag_counts(grouped, "dis_cits")
    sns.kdeplot(dis_cits, ax=axes[1], cut=0)
    cits = lag_counts(grouped, "cits")
    sns.kdeplot(cits, ax=axes[1], cut=0)
    # Aesthetics
    new_labels = {"dis_cits_dis": "Discussants citing the paper they discussed",
                  "dis_cits": "Non-discussants citing discussed papers",
                  "cits": "Anybody citing non-discussed papers"}
    axes[1].set(xlabel="Years until/since publication")
    handles, labels = axes[0].get_legend_handles_labels()
    axes[0].legend(handles=handles, labels=[new_labels.get(l) for l in labels])
    # Save
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


def make_citations_lineplot(df, fname, probablity=True):
    """Plot probability of annual citation by group for discussed papers."""
    # Statistics
    value_vars = ["Same authors", "Other workshop authors",
                  "Own discussant", "Other workshop discussants"]
    print(f"... Distribution of citer's identity for discussed papers:")
    print(df[value_vars].sum())
    if probablity:  # Use binary indicator by group-workshop-year
        for c in value_vars:
            df[c] = df[c].clip(0, 1)
    grouped = df.groupby(["eid"])["Own discussant"].max()
    not_cited = grouped.value_counts()[0]
    print(f"... {not_cited:,} discussed papers not cited by their discussant")
    df = df.melt(id_vars=["eid", "year"], value_name="Citation count",
                 value_vars=value_vars, var_name="Citation by")
    # Plot
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
    sns.lineplot(data=df, x="year", y="Citation count", ax=ax,
                 hue="Citation by", style="Citation by")
    # Aesthetics
    ax.set(xlabel="Years until/since publication", ylabel="Citation probability")
    # Save
    plt.savefig(fname, bbox_inches="tight")
    plt.clf()


def robust_query(q, integrity, refresh=100):
    """Return query results, attempt to refresh once."""
    try:
        res = ScopusSearch(q, integrity_fields=integrity, refresh=refresh).results
    except AttributeError:
        try:
            res = ScopusSearch(q, integrity_fields=integrity, refresh=True).results
        except AttributeError:
            res = ScopusSearch(q).results
            print(f"...missing fields {', '.join(integrity)} persist")
    return res or []


def main():
    # Read all relevant documents
    cols = ["eid", "discussant", "author_scopus", "group", "year", "type"]
    nber = pd.read_csv(NBER_FILE, usecols=cols)
    nber = nber[nber["type"] == "Journal"].drop(columns="type")
    nber = nber.rename(columns={"author_scopus": "authors"})
    for c in ("discussant", "authors"):
        nber[c] = nber[c].str.replace("-", ";").str.split(";")

    # Get authors and discussants by workshop
    discussants = (nber.dropna(subset=["discussant"])
                       .groupby(["group", "year"])["discussant"].apply(join_lists))
    discussants.name = "workshop_discussants"
    authors = nber.groupby(["group", "year"])["authors"].apply(join_lists)
    authors.name = "workshop_authors"

    # Retrieve citations for each paper
    eids = nber["eid"].unique()
    total = len(eids)
    print(f">>> Downloading referencing information for {total:,} articles")
    out = {}
    for eid in tqdm(eids):
        ab = AbstractRetrieval(eid, view="FULL")
        pub_year = int(ab.coverDate[:4])
        q = f"REF({eid})"
        res = robust_query(q, integrity=["eid", "coverDate"])
        cites = {}
        for p in res:
            year = int(p.coverDate[:4])
            if year >= datetime.now().year or not p.author_ids:
                continue
            delta = year - pub_year
            try:
                cites[delta] += "-" + p.author_ids
            except KeyError:
                cites[delta] = p.author_ids
        out[eid] = cites
    refs = pd.DataFrame(out).T
    refs = refs[sorted(refs.columns)]
    df = nber.join(refs, on="eid")

    # Plot citation probability by workshop participants to discussed papers
    df = (df.dropna(subset=["discussant"])
            .join(discussants, on=["group", "year"])
            .join(authors, on=["group", "year"]))
    df = df[df["discussant"].str.len() == 1]
    id_vars = ["eid", "discussant", "authors", "workshop_discussants",
               "workshop_authors"]
    temp = (df.drop(columns=["year", "group"])
              .melt(id_vars=id_vars, value_name="citing_author", var_name="year"))
    n_cites = sum(temp["citing_author"].dropna().str.count("-") + 1)
    print(f">>> Plotting citation probability for {df.shape[0]:,} papers and "
          f"{n_cites:,} total citations")
    temp["year"] = temp["year"].astype("int16")
    temp["Own discussant"] = temp.apply(citer_cited_comparison, axis=1)
    temp["Other workshop discussants"] = temp.apply(
        lambda s: citer_cited_comparison(s, find_col="workshop_discussants"), axis=1)
    temp["Other workshop discussants"] -= temp["Own discussant"]
    temp["Same authors"] = temp.apply(
        lambda s: citer_cited_comparison(s, find_col="authors"), axis=1)
    temp["Other workshop authors"] = temp.apply(
        lambda s: citer_cited_comparison(s, find_col="workshop_authors"), axis=1)
    temp["Other workshop authors"] -= temp["Same authors"]
    fname = OUTPUT_FOLDER/"Figures"/"lineplot_citationprob.pdf"
    make_citations_lineplot(temp, fname)


if __name__ == '__main__':
    main()
