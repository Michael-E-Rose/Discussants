#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Generates networks of informal collaboration for t, using publications
in t-1, t and t+1.
"""

from collections import Counter, defaultdict
from itertools import combinations, product
from json import loads
from pathlib import Path
from urllib.request import urlopen

import networkx as nx
import pandas as pd

from _012_list_presentations import write_stats, DATA_RANGE
from _206_build_coauthor_networks import LEAD, SPAN

ACK_FILE = "https://raw.githubusercontent.com/Michael-E-Rose/CoFE/"\
           "master/acks_min.json"
EDITOR_FILE = Path("./035_person_auxiliary/editor_tenures.csv")
TARGET_FOLDER = Path("./209_informal_networks/")


def add_attribute(network, edges, val, attr='weight'):
    """Creates, appends or increases attribute of edges"""
    for entry in edges:
        d = network.edges[entry[0], entry[1]]
        try:
            if isinstance(d[attr], str):
                d[attr] += ";" + val  # append
            else:
                d[attr] += val  # increase
        except KeyError:
            d[attr] = val  # create


def main():
    # READ IN
    eds = pd.read_csv(EDITOR_FILE).dropna(subset=['scopus_id'])
    eds = eds[eds['managing_editor'] == 1]
    eds['scopus_id'] = eds['scopus_id'].astype("uint64").astype(str)
    acks = loads(urlopen(ACK_FILE).read().decode("utf-8"))['data']
    papers_with = 0

    # GENERATE NETWORKS
    G = defaultdict(lambda: nx.DiGraph(name="both"))
    for item in acks:
        pub_year = item['year']
        journal = item['journal']
        # Authors
        auths = [a.get('scopus_id', a['label']) for a in item['authors']]
        # Commenters
        coms = [c.get('scopus_id', c['label']) for c in item.get('com', [])]
        coms.extend([c.get('scopus_id', c['label']) for c in item.get('dis', [])])
        coms.extend([p.get('scopus_id', p['label']) for x in item['authors']
                     for p in x.get('phd', [])])
        # Remove editors of this and previous year
        eds_range = range(pub_year-1, pub_year+1)
        mask = (eds['year'].isin(eds_range)) & (eds['journal'] == item['journal'])
        cur_editors = set(eds[mask]['scopus_id'])
        coms = set(coms) - cur_editors
        papers_with += (len(coms) > 0)*1
        # Add weighted links to this and the next SPAN networks
        for cur_year in range(pub_year-LEAD, pub_year-LEAD+SPAN):
            if cur_year < min(DATA_RANGE) or cur_year > max(DATA_RANGE):
                continue
            com_links = list(product(coms, auths))
            # Both network
            G[cur_year].add_nodes_from(coms)
            G[cur_year].add_edges_from(com_links)
            add_attribute(G[cur_year], com_links, 1.0/len(auths))

    # WRITE OUT
    for year, G in G.items():
        ouf = (TARGET_FOLDER/str(year)).with_suffix(".gexf")
        nx.write_gexf(G, ouf)

    # SAVE STATISTICS
    stats = {"N_of_papers_informal": papers_with}
    write_stats(stats)


if __name__ == '__main__':
    main()
