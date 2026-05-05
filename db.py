import os
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable, ConfigurationError
import streamlit as st


def _get_env(name, fallback=None):
    v = os.getenv(name)
    if v is None and fallback:
        v = os.getenv(fallback)
    return v.strip() if isinstance(v, str) else v


@st.cache_resource
def get_driver():
    print("NEO4J_URI =", repr(os.getenv("NEO4J_URI")))
    print("NEO4J_USER =", repr(os.getenv("NEO4J_USER")))
    print("NEO4J_PASSWORD length =", len(os.getenv("NEO4J_PASSWORD") or ""))
    uri = _get_env("NEO4J_URI")
    user = _get_env("NEO4J_USER")
    password = _get_env("NEO4J_PASSWORD")

    if not uri or not user or not password:
        raise RuntimeError("Missing Neo4j env vars")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    return driver


def try_connect_banner():
    try:
        driver = get_driver()
        st.sidebar.success("Neo4j connection OK")
        return driver
    except (AuthError, ServiceUnavailable, ConfigurationError, RuntimeError) as e:
        st.sidebar.error("Neo4j connection FAILED")
        st.sidebar.caption(f"{type(e).__name__}: {e}")
        return None


def run_query(query, **params):
    driver = get_driver()
    with driver.session() as session:
        return list(session.run(query, **params))


def get_character_basic(name):
    query = """
    MATCH (c)
    WHERE toLower(c.primary_name)=toLower($name)
    RETURN c.primary_name AS name,
           c.race AS race,
           c.age AS age,
           c.realm AS realm
    LIMIT 1
    """
    res = run_query(query, name=name)
    return dict(res[0]) if res else None


def get_neighbors(name, race_filter=None, rel_types=None):
    query = """
    MATCH (a)-[r]->(b)
    WHERE toLower(a.primary_name)=toLower($name)
      AND ($race_filter IS NULL OR b.race IN $race_filter)
      AND ($rel_types IS NULL OR type(r) IN $rel_types)
    RETURN a.primary_name AS from,
           type(r) AS rel,
           b.primary_name AS to,
           b.race AS race,
           b.realm AS realm
    """
    return run_query(query, name=name, race_filter=race_filter, rel_types=rel_types)


def check_elvish_ancestry(name):
    query = """
    MATCH (c)-[:DESCENDANT_OF*1..15]->(ancestor)
    WHERE toLower(c.primary_name)=toLower($name)
      AND ancestor.race CONTAINS 'Elf'
    RETURN DISTINCT ancestor.primary_name AS elf_ancestor
    """
    return run_query(query, name=name)


def get_lineage(name):
    query = """
    MATCH path = (c)-[:DESCENDANT_OF*0..15]->(ancestor)
    WHERE toLower(c.primary_name)=toLower($name)
    WITH nodes(path) AS ns
    UNWIND ns AS n
    WITH DISTINCT n
    RETURN n.primary_name AS name,
           n.race AS race,
           n.realm AS realm
    """
    return run_query(query, name=name)
