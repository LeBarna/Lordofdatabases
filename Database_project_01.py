import os
import base64
import tempfile

import streamlit as st
import streamlit.components.v1 as components
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable, ConfigurationError
from pyvis.network import Network

# 1) MUST be first Streamlit command
st.set_page_config(page_title="Tolkien Graph Explorer", layout="wide")  # 【1-c8fede】


def add_bg_from_local(image_file):
    # ne ölje meg az appot, ha Renderen nem találja a fájlt
    try:
        with open(image_file, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        st.markdown(
            f"""
<link href="https://fonts.googleapis.com/css2?family=IM+Fell+English&display=swap" rel="stylesheet">
<style>
html, body, div, span, input, textarea, button, label, p, li, ul, ol, h1, h2, h3, h4, h5, h6 {{
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
}}
</style>
""",
            unsafe_allow_html=True
        )
    except Exception as e:
        st.sidebar.warning(f"Háttérkép betöltése kihagyva: {e}")

add_bg_from_local("lotrbg.jpg")


def _get_env(name, fallback=None):
    v = os.getenv(name)
    if v is None and fallback:
        v = os.getenv(fallback)
    return v.strip() if isinstance(v, str) else v


@st.cache_resource
def get_driver():
    uri = _get_env("NEO4J_URI")
    user = _get_env("NEO4J_USERNAME", fallback="NEO4J_USER")
    password = _get_env("NEO4J_PASSWORD")

    if not uri or not user or not password:
        raise RuntimeError("Hiányzó Neo4j env var: NEO4J_URI, NEO4J_USERNAME/NEO4J_USER, NEO4J_PASSWORD")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    # gyors, explicit ellenőrzés (javasolt) 【4-04aabe】
    driver.verify_connectivity()
    return driver


def try_connect_banner():
    try:
        driver = get_driver()
        st.sidebar.success("Neo4j kapcsolat: OK")
        return driver, None
    except (AuthError, ServiceUnavailable, ConfigurationError, RuntimeError) as e:
        # UI tovább él, csak Neo4j funkciók lesznek tiltva
        st.sidebar.error("Neo4j kapcsolat: HIBA")
        st.sidebar.caption(f"{type(e).__name__}: {e}")
        return None, e


driver, conn_err = try_connect_banner()

# Ne csinálj session.run-t top-levelen! (ez ölte meg a futást Renderen)
with st.expander("Neo4j debug", expanded=False):
    st.write("NEO4J_URI set:", bool(os.getenv("NEO4J_URI")))
    st.write("NEO4J_USERNAME/NEO4J_USER set:", bool(os.getenv("NEO4J_USERNAME") or os.getenv("NEO4J_USER")))
    st.write("NEO4J_PASSWORD set:", bool(os.getenv("NEO4J_PASSWORD")))
    st.write("Tipp: Aura URI scheme gyakran neo4j+s://...")  # 【5-2029c6】

if conn_err is not None:
    st.warning("A Neo4j nem elérhető hitelesítési/kapcsolati hiba miatt. Az app UI működik, de a DB-funkciók le vannak tiltva.")
    # itt nem állítjuk le az appot; csak a DB részeket kell guard-olni

# Példa: DB-hívó függvényekben ellenőrzés:
@st.cache_data
def safe_run(query, **params):
    if driver is None:
        return []
    with driver.session() as session:
        return list(session.run(query, **params))


def draw_graph(edges):
    net = Network(height="650px", width="100%", bgcolor="#111111", font_color="white", directed=False)
    net.barnes_hut()

    for src, rel, dst, race, realm in edges:
        if not src or not dst:
            continue
        net.add_node(src, label=src)
        net.add_node(dst, label=dst)
        net.add_edge(src, dst, label=rel)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    tmp.close()
    net.save_graph(tmp.name)
    with open(tmp.name, "r", encoding="utf-8") as f:
        components.html(f.read(), height=680, scrolling=True)
# ------------------------------------------------------------
# UI cosmetics (after page config)
# ------------------------------------------------------------
add_bg_from_local("lotrbg.jpg")


# ------------------------------------------------------------
# Neo4j-safe functions (use driver inside)
# ------------------------------------------------------------
@st.cache_data
def get_character_basic(name: str):
    driver = get_driver()
    query = sanitize_cypher("""
    MATCH (c)
    WHERE toLower(c.primary_name) = toLower($name)
    RETURN c.primary_name AS name,
           c.race AS race,
           c.age AS age,
           c.realm AS realm
    LIMIT 1
    """)
    with driver.session() as session:
        rec = session.run(query, name=name).single()
        return dict(rec) if rec else None


@st.cache_data
def get_neighbors(name: str, race_filter=None, rel_types=None):
    driver = get_driver()
    query = sanitize_cypher("""
    MATCH (a)-[r]->(b)
    WHERE toLower(a.primary_name) = toLower($name)
      AND ($race_filter IS NULL OR b.race IN $race_filter)
      AND ($rel_types IS NULL OR type(r) IN $rel_types)
    RETURN a.primary_name AS from,
           type(r) AS rel,
           b.primary_name AS to,
           b.race AS race,
           b.realm AS realm
    """)
    with driver.session() as session:
        return list(session.run(query, name=name, race_filter=race_filter, rel_types=rel_types))


@st.cache_data
def check_elvish_ancestry(name: str):
    driver = get_driver()
    query = sanitize_cypher("""
    MATCH (c)-[:DESCENDANT_OF*1..15]->(ancestor)
    WHERE toLower(c.primary_name) = toLower($name)
      AND ancestor.race CONTAINS 'Elf'
    RETURN DISTINCT ancestor.primary_name AS elf_ancestor
    ORDER BY elf_ancestor
    """)
    with driver.session() as session:
        return list(session.run(query, name=name))


@st.cache_data
def get_lineage(name: str):
    driver = get_driver()
    query = sanitize_cypher("""
    MATCH path = (c)-[:DESCENDANT_OF*0..15]->(ancestor)
    WHERE toLower(c.primary_name) = toLower($name)
    WITH nodes(path) AS ns
    UNWIND ns AS n
    WITH DISTINCT n
    RETURN n.primary_name AS name,
           n.race AS race,
           n.realm AS realm
    ORDER BY name
    """)
    with driver.session() as session:
        return list(session.run(query, name=name))


def race_color(race: str):
    if race == "Elf":
        return "#7FFFD4"
    if race == "Man":
        return "#FFD700"
    if race == "Dwarf":
        return "#CD853F"
    if race == "Hobbit":
        return "#ADFF2F"
    if race == "Maiar":
        return "#FF69B4"
    return "#97c2fc"


def draw_graph(edges):
    net = Network(height="650px", width="100%", bgcolor="#111111", font_color="white", notebook=False, directed=False)
    net.barnes_hut()

    added_nodes = set()
    for src, rel, dst, race, realm in edges:
        if not src or not dst:
            continue

        if src not in added_nodes:
            net.add_node(src, label=src)
            added_nodes.add(src)

        if dst not in added_nodes:
            title = f"{dst}<br>Race: {race or 'Unknown'}<br>Realm: {realm or 'Unknown'}"
            net.add_node(dst, label=dst, color=race_color(race), title=title)
            added_nodes.add(dst)

        net.add_edge(src, dst, label=rel)

    # Write HTML to temp directory (safer on hosted env)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    tmp.close()
    net.save_graph(tmp.name)

    with open(tmp.name, "r", encoding="utf-8") as f:
        components.html(f.read(), height=680, scrolling=True)


# ------------------------------------------------------------
# Main App
# ------------------------------------------------------------
st.title("Middle Earth Wiki")
driver = neo4j_ok_banner()  # does not stop UI if DB is down

mode = st.sidebar.radio("Page", ["Explorer", "Character Editor"])

# ---------------- Explorer ----------------
if mode == "Explorer":
    with st.sidebar:
        st.title("Search")
        name = st.text_input("Character name", value="Aragorn")

        st.markdown("---")
        st.caption("Filters")

        race_filter = st.multiselect("Race filter", ["Elf", "Man", "Dwarf", "Hobbit", "Maiar", "Orc"])
        race_filter_val = race_filter if race_filter else None

        rel_filter = st.multiselect("Relationship types", ["ALLY_OF", "ENEMY_OF", "DESCENDANT_OF", "FRIEND_OF", "MEMBER_OF"])
        rel_filter_val = rel_filter if rel_filter else None

        st.markdown("---")
        st.caption("Sections")
        show_connections = st.checkbox("🔗 Connections", True)
        show_elf = st.checkbox("🧝 Elvish ancestry", True)
        show_lineage = st.checkbox("🧬 Lineage", True)
        show_graph = st.checkbox("🕸️ Graph", True)

    # Only run DB-backed queries if Neo4j is OK
    results, elf_results, lineage_results, char_info = [], [], [], None
    if name and driver is not None:
        char_info = get_character_basic(name)

        if show_connections or show_graph:
            raw = get_neighbors(name, race_filter_val, rel_filter_val)
            results = list({
                (r["from"], r["rel"], r["to"], r["race"], r["realm"])
                for r in raw
                if r.get("to") is not None
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
        elif driver is None:
            st.warning("Neo4j is not reachable; Explorer features are disabled.")
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
                        st.markdown(f"- {r['name']} ({r['race'] or 'Unknown'}, {r['realm'] or 'Unknown'})")
                else:
                    st.info("No lineage data found.")

            if show_connections:
                st.markdown("---")
                st.subheader("🔗 Connections")
                if results:
                    for src, rel, dst, race, realm in results:
                        st.markdown(f"**{src}** → *{rel}* → **{dst}** ({race or 'Unknown'}, {realm or 'Unknown'})")
                else:
                    st.info("No connections found.")

    with col2:
        st.subheader("🕸️ Graph")
        if driver is None:
            st.warning("Neo4j is not reachable; Graph view disabled.")
        elif show_graph and results:
            draw_graph(results)
        else:
            st.info("No graph to display.")

# ---------------- Character Editor ----------------
else:
    st.title("⚙ Character Editor")

    if driver is None:
        st.warning("Neo4j is not reachable; editor disabled.")
        st.stop()

    def normalize_text(value):
        if not value:
            return None
        return value.strip().title()

    def character_exists(name):
        query = sanitize_cypher("""
        MATCH (c:Character)
        WHERE toLower(c.primary_name) = toLower($name)
        RETURN count(c) AS cnt
        """)
        with get_driver().session() as session:
            result = session.run(query, name=name).single()
        return result["cnt"] > 0

    def create_character(name, race, realm):
        query = sanitize_cypher("""
        MERGE (c:Character {primary_name:$name})
        SET c.race=$race,
            c.realm=$realm
        """)
        with get_driver().session() as session:
            session.run(query, name=name, race=race, realm=realm)

    def get_all_characters():
        query = sanitize_cypher("""
        MATCH (c:Character)
        RETURN c.primary_name AS name
        ORDER BY name
        """)
        with get_driver().session() as session:
            return [r["name"] for r in session.run(query)]

    def create_relationship(a, rel, b):
        query = sanitize_cypher(f"""
        MATCH (x:Character {{primary_name:$a}})
        MATCH (y:Character {{primary_name:$b}})
        MERGE (x)-[:{rel}]->(y)
        """)
        with get_driver().session() as session:
            session.run(query, a=a, b=b)

    def update_character(name, race, realm):
        query = sanitize_cypher("""
        MATCH (c:Character {primary_name:$name})
        SET c.race=$race,
            c.realm=$realm
        """)
        with get_driver().session() as session:
            session.run(query, name=name, race=race, realm=realm)

    def delete_character(name):
        query = sanitize_cypher("""
        MATCH (c:Character {primary_name:$name})
        DETACH DELETE c
        """)
        with get_driver().session() as session:
            session.run(query, name=name)

    tab1, tab2, tab3 = st.tabs(["Add Character", "Add Relationship", "Edit / Delete"])

    with tab1:
        st.subheader("➕ Add Character")
        name = st.text_input("Name", key="add_name")
        race = st.text_input("Race", key="add_race")
        realm = st.text_input("Realm", key="add_realm")

        if st.button("Create Character"):
            name_n = normalize_text(name)
            race_n = normalize_text(race)
            realm_n = normalize_text(realm)

            if not name_n or not race_n:
                st.error("Name and race required")
            elif character_exists(name_n):
                st.warning("Character already exists")
            else:
                create_character(name_n, race_n, realm_n)
                st.success("Character added")

    with tab2:
        st.subheader("🔗 Add Relationship")
        characters = get_all_characters()

        if not characters:
            st.info("No characters yet.")
        else:
            char_a = st.selectbox("Character A", characters, key="rel_a")
            char_b = st.selectbox("Character B", characters, key="rel_b")

            relation = st.selectbox(
                "Relationship",
                ["ALLY_OF", "ENEMY_OF", "DESCENDANT_OF", "FRIEND_OF", "MEMBER_OF", "SPOUSE_OF"],
                key="rel_type"
            )

            if st.button("Create Relationship"):
                if char_a == char_b:
                    st.error("Cannot relate a character to itself")
                else:
                    create_relationship(char_a, relation, char_b)
                    st.success("Relationship created")

    with tab3:
        st.subheader("✏ Edit Character")
        characters = get_all_characters()

        if not characters:
            st.info("No characters yet.")
        else:
            selected = st.selectbox("Select Character", characters, key="edit_sel")
            new_race = st.text_input("Race", key="edit_race")
            new_realm = st.text_input("Realm", key="edit_realm")

            if st.button("Update Character"):
                update_character(selected, normalize_text(new_race), normalize_text(new_realm))
                st.success("Character updated")

            st.markdown("---")
            st.subheader("❌ Delete Character")
            if st.button("Delete Character"):
                delete_character(selected)
                st.warning("Character deleted")
