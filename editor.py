import streamlit as st
from db import run_query


def get_all_characters():

    q = """
    MATCH (c:Character)
    RETURN c.primary_name AS name
    ORDER BY name
    """

    return [r["name"] for r in run_query(q)]


def create_character(name, race, realm):

    q = """
    MERGE (c:Character {primary_name:$name})
    SET c.race=$race,
        c.realm=$realm
    """

    run_query(q, name=name, race=race, realm=realm)


def create_relationship(a, rel, b):

    q = f"""
    MATCH (x:Character {{primary_name:$a}})
    MATCH (y:Character {{primary_name:$b}})
    MERGE (x)-[:{rel}]->(y)
    """

    run_query(q, a=a, b=b)


def editor_ui():

    st.title("Character Editor")

    tab1, tab2 = st.tabs(["Add Character", "Add Relationship"])

    with tab1:

        name = st.text_input("Name")
        race = st.text_input("Race")
        realm = st.text_input("Realm")

        if st.button("Create"):

            create_character(name.title(), race.title(), realm.title())
            st.success("Character created")

    with tab2:

        chars = get_all_characters()

        if not chars:
            st.info("No characters yet")
            return

        a = st.selectbox("Character A", chars)
        b = st.selectbox("Character B", chars)

        rel = st.selectbox(
            "Relationship",
            ["ALLY_OF", "ENEMY_OF", "DESCENDANT_OF", "FRIEND_OF"]
        )

        if st.button("Create Relationship"):

            create_relationship(a, rel, b)
            st.success("Relationship created")