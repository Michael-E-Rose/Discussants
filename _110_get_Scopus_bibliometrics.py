#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Compiles bibliometric information for NBER article set using Scopus."""

import re
from pathlib import Path

import pandas as pd
from numpy import cumsum
from pybliometrics.scopus import AbstractRetrieval, CitationOverview
from tqdm import tqdm

SOURCE_FILE = Path("020_title_mapping/mapping.csv")
TARGET_FILE = Path("110_bibliometrics/metrics.csv")

PAGE_RANGES = {
    "2-s2.0-77649165513": 60,
    "2-s2.0-21244446232": 35,
    "2-s2.0-84920752219": 25,
}

tqdm.pandas()

_copyright = {'copyright', '©', ' (c) ', ' 5555 ', 'published by ',
              'this is an abstract of a paper presented'}
_remove = {"Original is an abstract.", "Summary form only given.",
           "(Review article)"}
_suffixes = {"-Author.", "-from Authors.", "-Authors.", "from Author."}


def clean_abstract(ab):
    """Clean abstract: Replace some characters and remove meta stuff."""
    # Remove whitespaces
    try:
        ab = ab.replace("  ", " ").strip()
    except AttributeError:
        return None
    # Remove authors suffix
    for suffix in _suffixes:
        ab = ab.removesuffix(suffix)
    # Remove entire meta sentences
    for test in _remove:
        ab = ab.replace(test, "")
    # Remove trailing or leading sentence(s) if it includes Copyright information
    if not ab:
        return ""
    sentences = ab.strip(".").split(".")
    sentences = [s for s in sentences if "all rights reserved" not in s.lower()]
    if not sentences:
        return None
    if any(m in sentences[0].lower() for m in _copyright):
        del sentences[0]
    if not sentences:
        return None
    for idx in range(-8, 0):
        try:
            if any(m in sentences[idx].lower() for m in _copyright):
                sentences = sentences[:idx]
                break
        except IndexError:
            pass
    return ".".join(sentences + [""]).strip()


def compute_readability(ab):
    """Compute various readability scores."""
    from textatistic import Textatistic
    try:
        s = Textatistic(ab)
        d = {'flesch': s.flesch_score, 'fleschkincaid': s.fleschkincaid_score,
             'gunningfog': s.gunningfog_score, 'smog': s.smog_score}
    except (AttributeError, ValueError, ZeroDivisionError):
        d = None
    return pd.Series(d, dtype="float32")


def count_pages(s):
    """Attempt to count the number of pages."""
    try:
        pages = re.sub(r"[A-Za-z]+", '', s.pages)
        r = abs(eval(pages))+1
    except (NameError, SyntaxError, TypeError):
        r = PAGE_RANGES.get(s.name)
    if not r:
        print(f">>> Article {s.name} w/o page range")
    return r


def get_bibliometrics(eid, refresh=350, current_year=2022):
    """Retrieve Scopus abstracts and extract bibliometric information."""
    ab = AbstractRetrieval(eid, view='FULL', refresh=refresh)
    pubyear = int(ab.coverDate.split("-")[0])
    # Basic bibliometric information
    s = pd.Series(dtype=object)
    s['journal'] = ab.publicationName
    s['source'] = ab.source_id
    s['issue'] = ab.issueIdentifier
    s['pub_year'] = pubyear
    s['pages'] = ab.pageRange
    s['type'] = ab.aggregationType
    s['author'] = ";".join(str(au.auid) for au in ab.authors)
    s['abstract'] = ab.abstract or ab.description
    # Yearly cumulated citations
    sid = eid.split("-")[-1]
    co = CitationOverview([sid], start=pubyear, end=current_year, refresh=refresh)
    cc = [(t[0], t[1]) for t in co.cc[0] if t[0] < current_year]
    years, cites = list(zip(*cc))
    s['total_citations'] = sum(cites)
    labels = [f"citcount_{y-pubyear}" for y in years]
    citations = cumsum(cites)
    s = pd.concat([s, pd.Series(citations, index=labels)])
    return s


def main():
    # Read in
    df = pd.read_csv(SOURCE_FILE, usecols=["eid"])
    df = (df.dropna().drop_duplicates()
            .set_index('eid', drop=False))

    # Get bibliometrics
    print(f">>> Retrieving bibliometric information from Scopus...")
    bibl = df["eid"].progress_apply(get_bibliometrics)
    bibl['num_pages'] = bibl.apply(count_pages, axis=1)
    bibl = bibl.drop(columns="pages")
    bibl.loc[bibl["source"] == 17357, "type"] = "Journal"  # IMF Staff Papers

    # Compute readability
    bibl["abstract"] = bibl["abstract"].apply(clean_abstract)
    read = bibl["abstract"].apply(compute_readability)
    read = read.add_prefix("pub_")

    # Write out
    out = pd.concat([bibl.drop(columns="abstract"), read], axis=1)
    out.to_csv(TARGET_FILE, encoding="utf8")


if __name__ == '__main__':
    main()
