#!/usr/bin/env python3
# Author:   Michael E. Rose <michael.ernst.rose@gmail.com>
"""Computes centralities for all nodes of a all networks."""

import time
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

COAUTHOR_FOLDER = Path("./206_coauthor_networks")
INFORMAL_FOLDER = Path("./209_informal_networks")
TARGET_FOLDER = Path("./220_centralities")

ATTENUATIONS = list(map(lambda x: x/100.0, list(range(5, 96, 10))))


def compute_centralities(G, H, degree=True, eigvec=True, weight=None):
    """Return DataFrame with node-wise network measures."""
    start = time.time()
    # Neighborhood centrality
    df = discounted_neighborhood(G)
    print("... computing other centralities")
    label = ""
    if weight:
        label = "_w"
    # Other centralities
    if degree:
        df["degree" + label] = pd.Series(dict(nx.degree(H, weight=weight)))
    if eigvec:
        df["eigenvector" + label] = pd.Series(
            nx.eigenvector_centrality_numpy(G, weight=weight))
    diff = time.strftime("%H:%M:%S", time.gmtime(time.time() - start))
    print("... Time for computation:", diff)
    return df


def discounted_neighborhood(net):
    """Compute discounted neighborhood centrality."""
    print("... computing neighborhood centrality")
    nodes = sorted(net.nodes())
    M_sum = G = M = nx.adjacency_matrix(net, nodelist=nodes, weight=None).todense()
    I = np.identity(len(G))
    # First iteration
    idx = 1
    vec = np.array(M.sum(axis=0))[0]
    centr = {alpha: (alpha**idx)*vec for alpha in ATTENUATIONS}
    # All other iterations
    while np.any(M):
        idx += 1
        W = np.matmul(M, G)
        Z = W.clip(max=1) - (I + M_sum)
        M = Z.clip(min=0)
        vec = np.array(M.sum(axis=0))[0]
        centr = {alpha: np.add(old, (alpha**idx) * vec) for
                 alpha, old in centr.items()}
        M_sum = np.add(M_sum, M)
    # Create DataFrame from dictionary
    df = pd.DataFrame.from_dict(centr)
    df.index = nodes
    df.columns = [f"neighborhood_{int(alpha*100)}" for alpha in df.columns]
    return df


def giant(H):
    """Return giant component of a network."""
    try:
        components = sorted(nx.connected_components(H), key=len, reverse=True)
    except nx.NetworkXNotImplemented:  # Directed network
        components = sorted(nx.weakly_connected_components(H),
                            key=len, reverse=True)
    return H.subgraph(components[0])


def main():
    files = INFORMAL_FOLDER.glob("*.gexf")
    files.extend(COAUTHOR_FOLDER.glob("*.gexf"))

    print(">>> Now working on:")
    for file in sorted(files):
        # Read in
        year = file.name[:-5]
        if file.parts[-2] == "206_coauthor_networks":
            net_type = 'coauth'
        else:
            net_type = 'informal'
        ident = "_".join([net_type, year])
        print(f"... {ident} ...")
        H = nx.read_gexf(file)
        G = giant(H)

        # Centralities (with predefined attenuation factors)
        centr = compute_centralities(G, H, weight=None).sort_index()
        centr.to_csv((TARGET_FOLDER/ident).with_suffix(".csv"), index_label="node")


if __name__ == '__main__':
    main()
