import streamlit as st
from db import try_connect_banner, get_character_basic, get_neighbors, check_elvish_ancestry, get_lineage
from graph import draw_graph
from editor import editor_ui
import base64

def add_bg_from_local(image_file):
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=IM+Fell+English&display=swap" rel="stylesheet">

<style>
html, body, div, span, input, textarea, button, label, p, li, ul, ol, h1, h2, h3, h4, h5, h6 {{
    font-family: 'IM Fell English', serif !important;
}}

[data-testid="stAppViewContainer"],
[data-testid="stSidebar"],
[data-testid="stMarkdownContainer"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stText"],
[data-testid="stWidgetLabel"] {{
    font-family: 'IM Fell English', serif !important;
}}

[data-testid="stAppViewContainer"] {{
    background-image:
        linear-gradient(rgba(0,0,0,0.45), rgba(0,0,0,0.45)),
        url("data:image/png;base64,{encoded}");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
}}

[data-testid="stAppViewContainer"] > .main {{
    background: transparent;
    position: relative;
    z-index: 1;
}}
</style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="Middle Earth Wiki", layout="wide")

add_bg_from_local("assets/lotrbg.jpg")

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

    # --- KÉT OSZLOP ---
    col_left, col_right = st.columns([1, 2])

    # --- BAL OSZLOP: karakter adatok ---
    with col_left:

        char = get_character_basic(name)

        if char:
            st.subheader(char["name"])
            st.write("Race:", char["race"])
            st.write("Age:", char["age"])
            st.write("Realm:", char["realm"])

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

    # --- JOBB OSZLOP: graph ---
    with col_right:
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
