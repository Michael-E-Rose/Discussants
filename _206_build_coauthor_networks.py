#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Generates co-author networks for t, using publications
in t-1, t and t+1.
"""

from collections import defaultdict
from itertools import combinations
from pathlib import Path

import networkx as nx
import pandas as pd
from pybliometrics.scopus import ScopusSearch

from _012_list_presentations import DATA_RANGE

SOURCE_FILE = Path("005_identifiers/journals.csv")
TARGET_FOLDER = Path("./206_coauthor_networks")

SPAN = 3  # Number of years for each network
LEAD = 2  # Number of years to look forward (i.e. the publication lag)
_doctypes = {'cp', 'ar', 're', 'no', 'sh', 'ip'}  # Document types we keep


def main():
    # Read in
    source_ids = pd.read_csv(SOURCE_FILE)['Scopus ID'].dropna().astype("uint64").unique()
    G = defaultdict(lambda: nx.Graph())
    pub_counts = defaultdict(lambda: 0)

    # Iterate over publication lists
    print(">>> Parsing publications for ...")
    for year in range(min(DATA_RANGE), max(DATA_RANGE)+SPAN):
        print("...", str(year))
        cur_count = 0
        nodes = []
        edges = []
        for source_id in source_ids:
            # Get publications
            q = f'SOURCE-ID({source_id}) AND PUBYEAR IS {year}'
            res = ScopusSearch(q, refresh=50).results or []
            pubs = [p for p in res if p.author_ids and p.subtype in _doctypes]
            cur_count += len(pubs)
            # Create edges
            auth_groups = [p.author_ids.split(";") for p in pubs]
            nodes.extend([a for sl in auth_groups for a in sl])
            new_edges = [list(combinations(group, 2)) for group in auth_groups]
            edges.extend([tuple(sorted(pair)) for sl in new_edges for pair in sl])
        # Build network and append to other years
        H = nx.Graph()
        H.add_nodes_from(nodes)
        H.add_edges_from(edges)
        for cur_year in range(year-LEAD, year-LEAD+SPAN):
            if cur_year < min(DATA_RANGE) or cur_year > max(DATA_RANGE):
                continue
            G[cur_year] = nx.compose(G[cur_year], H)
            pub_counts[cur_year] += cur_count

    # Write out
    for year, network in G.items():
        ouf = (TARGET_FOLDER/str(year)).with_suffix(".gexf")
        nx.write_gexf(network, ouf)


if __name__ == '__main__':
    main()
