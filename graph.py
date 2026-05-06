import tempfile
import streamlit.components.v1 as components
from pyvis.network import Network


def race_color(race):
    colors = {
        "Elf": "#7FFFD4",
        "Man": "#FFD700",
        "Dwarf": "#CD853F",
        "Hobbit": "#ADFF2F",
        "Maiar": "#FF69B4",
    }
    return colors.get(race, "#97c2fc")


def draw_graph(edges):

    net = Network(
        height="650px",
        width="100%",
        bgcolor="#111111",
        font_color="white",
        directed=False
    )

    net.barnes_hut()

    added_nodes = set()

    for row in edges:

   
        if len(row) == 3:
            src, rel, dst = row
            race = "Unknown"
            realm = "Unknown"

      
        elif len(row) == 5:
            src, rel, dst, race, realm = row

        else:
            
            continue

        
        if not isinstance(src, str) or not isinstance(dst, str):
            continue

       
        if src not in added_nodes:
            net.add_node(src, label=src)
            added_nodes.add(src)

        if dst not in added_nodes:
            title = f"{dst}<br>Race:{race}<br>Realm:{realm}"
            net.add_node(dst, label=dst, color=race_color(race), title=title)
            added_nodes.add(dst)

       
        net.add_edge(src, dst, label=rel)

   
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    tmp.close()

    net.save_graph(tmp.name)

    with open(tmp.name, "r", encoding="utf-8") as f:
        components.html(f.read(), height=680, scrolling=True)
