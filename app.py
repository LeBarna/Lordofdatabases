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
    with st.sidebar:

        st.title("Search")
    
        name = st.text_input("Character name", value="Aragorn")
    
        st.markdown("---")
        st.caption("Filters")
    
        race_filter = st.multiselect(
            "Race filter",
            ["Elf", "Man", "Dwarf", "Hobbit", "Maiar", "Orc"]
        )
    
        race_filter_val = race_filter if race_filter else None
    
        rel_filter = st.multiselect(
            "Relationship types",
            ["ALLY_OF", "ENEMY_OF", "DESCENDANT_OF", "FRIEND_OF", "MEMBER_OF"]
        )
    
        rel_filter_val = rel_filter if rel_filter else None
    
        st.markdown("---")
        st.caption("Sections")
    
        show_connections = st.checkbox("🔗 Connections", True)
        show_elf = st.checkbox("🧝 Elvish ancestry", True)
        show_lineage = st.checkbox("🧬 Lineage", True)
        show_graph = st.checkbox("🕸️ Graph", True)




st.title("Middle Earth Wiki")

results = []
elf_results = []
lineage_results = []
char_info = None

if name:

    char_info = get_character_basic(name)

    if show_connections or show_graph:

        raw = get_neighbors(name, race_filter_val, rel_filter_val)

        results = list({
            (r["from"], r["rel"], r["to"], r["race"], r["realm"])
            for r in raw
            if r["to"] is not None
        })

    if show_elf:
        elf_results = check_elvish_ancestry(name)

    if show_lineage:
        lineage_results = get_lineage(name)




col1, col2 = st.columns([1, 2])




with col1:

    st.subheader("🔍 Character info")

    if not name:
        st.info("Search for a character.")
    else:

        if char_info:

            st.markdown(f"### {char_info['name']}")
            st.markdown(f"**Race:** {char_info['race'] or 'Unknown'}")
            st.markdown(f"**Age:** {char_info['age'] or 'Unknown'}")

        else:
            st.warning("Character not found.")

        if show_elf:

            st.markdown("---")
            st.subheader("🧝 Elvish ancestry")

            if elf_results:
                for r in elf_results:
                    st.markdown(f"🧝 {r['elf_ancestor']}")
            else:
                st.info("No elvish ancestry found.")

        if show_lineage:

            st.markdown("---")
            st.subheader("🧬 Lineage")

            if lineage_results:

                for r in lineage_results:
                    st.markdown(
                        f"- {r['name']} ({r['race'] or 'Unknown'}, {r['realm'] or 'Unknown'})"
                    )

            else:
                st.info("No lineage data found.")

        if show_connections:

            st.markdown("---")
            st.subheader("🔗 Connections")

            if results:

                for src, rel, dst, race, realm in results:

                    st.markdown(
                        f"**{src}** → *{rel}* → **{dst}** "
                        f"({race or 'Unknown'}, {realm or 'Unknown'})"
                    )

            else:
                st.info("No connections found.")




with col2:

    if show_graph:

        st.subheader("🕸️ Graph")

        if results:
            draw_graph(results)
        else:
            st.info("No graph to display.")

