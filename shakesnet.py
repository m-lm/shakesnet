import pandas as pd
import networkx as nx
from pyvis.network import Network
from collections import Counter
from tqdm import tqdm
import string
import os
import itertools
import json
import time


def preprocess():
    """
    Create CSV files for each Shakespeare play.
    """
    df = pd.read_csv("data/shakespeare/shakespeare_plays.csv")
    grouped = df.groupby("play_name")
    plays = {play: data for play, data in grouped}
    for play, data in plays.items():
        data.to_csv(f"data/plays/{play}.csv", index=False)

def find_mentions(text, characters, invalid_names):
    """
    Find explicit mentions of characters within sentences based off the play's character cast.
    """
    cleaned_text = text.translate(str.maketrans("", "", string.punctuation)).lower()
    return [char for char in characters if char.lower() in cleaned_text and char.lower() not in invalid_names]

def extract_relationships():
    """
    Read in each play and extract the relationships.
    """
    plays = sorted(os.listdir("data/plays"))
    invalid_names = ["all"]
    cumulative_elapsed_time = 0

    with tqdm(total=len(plays), desc="Processing plays", dynamic_ncols=True, position=0) as pbar:
        for play in plays:
            if play[0].isalpha():
                filename = os.path.join("data/plays", play)
            else:
                continue

            """
            Read in CSV file for the play.
            Get character names as well as their lowercased versions.
            """
            start_time = time.time()
            df = pd.read_csv(filename)
            characters = [name for name in df["character"].unique().tolist() if name.lower() not in invalid_names]
            original_character_map = {name.lower(): name for name in characters}
            df["entities"] = df["text"].apply(lambda t: find_mentions(t, characters, invalid_names)).to_list()

            """
            Go through each scene and get the character cast.
            First, check for explicit relations (mention of one character by another).
            Then, check for implicit relations (association of one character with another).
            Cumulatively store relation counts per (act, scene) in cumulative_relation_counts as temporal info.
            Make sure not to double-up if a speaker directly addresses a fellow scene participant.
            """
            scenes = df.groupby(["act", "scene"])
            explicit_relation_counts = Counter()
            implicit_relation_counts = Counter()
            cumulative_relation_counts = {}
            for (act, scene), lines in scenes:
                scene_chars = lines["character"].unique().tolist()
                associations = set() # Tracks relations in scene.

                """
                This loop is for explicit mentions by a speaker within the same scene.
                Organize the relationships in unordered pairs.
                Then, lower() is used for name normalization. At the end, names are mapped back to original.

                For each sentence text in the scene, check if mention is valid.
                If so, append the valid explicit
                """
                for _, row in lines.iterrows():
                    mentioned = row["entities"]
                    speaker = row["character"].lower()
                    for mention in list(map(str.lower, mentioned)):
                        if speaker != mention and mention.lower() not in invalid_names:
                            pair = tuple(sorted((speaker, mention)))
                            associations.add(pair)
                            explicit_relation_counts[pair] += 1

                """
                This loop is for implicit relations from scene associations. Characters within the same scene are likely related.
                Prioritize explicit mentions over implicit associations by checking whether the pair has already be explicitly related.
                """
                for combo in itertools.combinations(list(map(str.lower, scene_chars)), 2):
                    pair = tuple(sorted(combo))
                    if pair not in associations:
                        associations.add(pair)
                        implicit_relation_counts[pair] += 1

                """
                Update scene-by-scene temporal info for cumulative snapshots of relations and their counts.
                """
                shadow_exp_rel_counts = Counter({(original_character_map[a], original_character_map[b]): count for (a, b), count in explicit_relation_counts.items() if a in original_character_map and b in original_character_map})
                shadow_imp_rel_counts = Counter({(original_character_map[a], original_character_map[b]): count for (a, b), count in implicit_relation_counts.items() if a in original_character_map and b in original_character_map})
                cumulative_relation_counts[(act, scene)] = shadow_exp_rel_counts + shadow_imp_rel_counts

            """
            Convert lowercase normalized names to original proper case.
            Check if gathered names are in the list of participating characters.
            """
            explicit_relation_counts = Counter({(original_character_map[a], original_character_map[b]): count for (a, b), count in explicit_relation_counts.items() if a in original_character_map and b in original_character_map})
            implicit_relation_counts = Counter({(original_character_map[a], original_character_map[b]): count for (a, b), count in implicit_relation_counts.items() if a in original_character_map and b in original_character_map})
            final_relation_counts = explicit_relation_counts + implicit_relation_counts

            """
            Finish processing play by generating the export files for visualization.
            """
            play_title = play[:play.find(".")]
            generate_visualization(play_title, final_relation_counts, cumulative_relation_counts)
            end_time = time.time()
            elapsed_time = round(end_time - start_time, 1)
            cumulative_elapsed_time += elapsed_time
            tqdm.write(f"{play_title} done processing... ({elapsed_time}s)\n")
            pbar.update(1)

    tqdm.write(f"\nAll {len(plays)} plays are done processing. ({round(cumulative_elapsed_time, 1)}s)\n")

def generate_visualization(play_title, final_relation_counts, cumulative_relation_counts):
    """
    Construct a graph for visualization and file exporting.
    """
    G = nx.Graph()

    for relation, weight in final_relation_counts.items():
        G.add_edge(relation[0], relation[1], weight=weight)

    viz = Network(
        notebook=True, 
        cdn_resources="remote",
        neighborhood_highlight=True,
        select_menu=True,
        filter_menu=True,
        )
    for node in G.nodes():
        viz.add_node(node, label=node, size=G.degree(node)*2) # Scale by 2 for nodes.
    viz.from_nx(G)
    viz.set_options("""
        {
            "nodes": {
                "font": {
                    "size": 50
                }
            },
            "physics": {
                "stabilization": {
                    "enabled": true,
                    "iterations": 300
                },
                "barnesHut": {
                    "gravitationalConstant": -80000,
                    "centralGravity": 0.3,
                    "springLength": 95,
                    "springConstant": 0.04
                }
            }
        }
    """)

    """
    Generate Pyvis graph visualizations in HTML.
    Export graph to .graphml.
    """
    viz.show(f"viz/{play_title}.html")
    nx.write_graphml(G, f"exports/graphml/{play_title}.graphml")
    nx.write_gexf(G, f"exports/gexf/{play_title}.gexf")
    graph_snapshot = {str(tuple(int(t) for t in time_tuple)): {str(inner_k): inner_v for inner_k, inner_v in inner_relations.items()} for time_tuple, inner_relations in cumulative_relation_counts.items()}
    with open(f"exports/snapshots/{play_title} Temporal-Snapshot.json", "w") as f:
        json.dump(graph_snapshot, f, indent=4)


if __name__ == "__main__":
    preprocess()
    extract_relationships()