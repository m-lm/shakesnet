# shakesnet

Shakesnet is a network analysis program written in Python which creates character networks for all 39 of Shakespeare plays. It extracts character relationships by identifying both implicit and explicit interactions and generates the social network accordingly for each play. In addition, it tracks temporal information (cumulative co-relation counts by scene), enabling dynamic graph analysis on scene-by-scene snapshots.

Shakesnet also exports Pyvis-generated HTML files for interactive graph visualizations as well as .graphml and .gexf files for use in programs like Gephi.

> Note: temporal information may not yet be incorporated into the exported file formats, and is currently on my to-do list. However, JSON snapshots containing this information are available.

### Run

To run the program, enter `./run.sh` in your terminal of choice after running `pip install -r requirements.txt` to install the dependencies.