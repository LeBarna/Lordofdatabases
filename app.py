import streamlit as st
from db import try_connect_banner, get_character_basic, get_neighbors, check_elvish_ancestry, get_lineage
from graph import draw_graph
from editor import editor_ui

st.set_page_config(page_title="Middle Earth Wiki", layout="wide")

st.title("Middle Earth Wiki")

driver = try_connect_banner()

mode = st.sidebar.radio(
    "Page",
    ["Explorer", "Character Editor"]
)

if mode == "Character Editor":

    editor_ui()

else:

    name = st.sidebar.text_input(
        "Character name",
        "Aragorn"
    )

    if driver is None:

        st.warning("Neo4j connection not available")
        st.stop()

    char = get_character_basic(name)

    if char:

        st.subheader(char["name"])
        st.write("Race:", char["race"])
        st.write("Age:", char["age"])
        st.write("Realm:", char["realm"])

    edges = get_neighbors(name)

    if edges:

        draw_graph(edges)

    elves = check_elvish_ancestry(name)

    if elves:

        st.subheader("Elvish ancestry")

        for e in elves:
            st.write(e["elf_ancestor"])

    lineage = get_lineage(name)

    if lineage:

        st.subheader("Lineage")

        for l in lineage:
            st.write(l["name"], "-", l["race"])