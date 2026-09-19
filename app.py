import streamlit as st
import sqlite3
import pandas as pd
import requests

# 1. Base de données
conn = sqlite3.connect("videotheque.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS dvd (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titre TEXT NOT NULL,
    realisateur TEXT,
    annee INTEGER,
    genre TEXT,
    statut TEXT,
    affiche TEXT
)
""")
conn.commit()

# --- CONFIGURATION DE VOTRE CLÉ TMDB ---
TMDB_API_KEY = "d5aef1a69ce6a5594a69e045df6d6dd7"
# ----------------------------------------

# Moteur de recherche officiel utilisant votre nouvelle clé
def chercher_film_tmdb(titre_recherche):
    if not titre_recherche:
        return None
        
    url = "https://themoviedb.org"
    params = {
        "api_key": TMDB_API_KEY,
        "query": titre_recherche,
        "language": "fr-FR"
    }
    
    try:
        response = requests.get(url, params=params, timeout=5).json()
        results = response.get("results")
        
        if results:
            film = results[0]  # Premier résultat
            id_film = film.get("id")
            
            # Recherche du réalisateur via les crédits du film
            realisateur = "Inconnu"
            if id_film:
                credits_url = f"https://themoviedb.org{id_film}/credits"
                credits_resp = requests.get(credits_url, params={"api_key": TMDB_API_KEY}, timeout=5).json()
                for member in credits_resp.get("crew", []):
                    if member.get("job") == "Director":
                        realisateur = member.get("name")
                        break
            
            # Lien de l'affiche
            affiche_path = film.get("poster_path")
            url_affiche = f"https://tmdb.org{affiche_path}" if affiche_path else ""
            
            # Année de sortie
            date_reg = film.get("release_date", "")
            annee = int(date_reg[:4]) if date_reg else 2026

            return {
                "titre": film.get("title"),
                "annee": annee,
                "realisateur": realisateur,
                "affiche": url_affiche
            }
    except:
        pass
    return None

# 2. Interface Graphique Streamlit
st.set_page_config(page_title="Ma Vidéothèque Pro", page_icon="🎬", layout="wide")
st.title("🎬 Ma Vidéothèque Personnelle (Propulsé par TMDB)")

st.sidebar.header("🔍 Recherche Automatique")
recherche_titre = st.sidebar.text_input("Nom du film à chercher...")

film_trouve = None
if recherche_titre:
    film_trouve = chercher_film_tmdb(recherche_titre)
    if film_trouve:
        st.sidebar.success(f"🍿 Trouvé : {film_trouve['titre']}")
        if film_trouve['affiche']:
            st.sidebar.image(film_trouve['affiche'], width=120)
    else:
        st.sidebar.warning("Aucun résultat trouvé.")

st.sidebar.markdown("---")
st.sidebar.header("➕ Enregistrer le DVD")

with st.sidebar.form(key="add_form", clear_on_submit=True):
    titre = st.text_input("Titre officiel *", value=film_trouve["titre"] if film_trouve else "")
    realisateur = st.text_input("Réalisateur", value=film_trouve["realisateur"] if film_trouve else "")
    annee = st.number_input("Année", min_value=1890, max_value=2030, value=film_trouve["annee"] if film_trouve else 2026)
    genre = st.selectbox("Genre", ["Action", "Comédie", "Drame", "Science-Fiction", "Horreur", "Animation", "Thriller", "Autre"])
    statut = st.radio("Statut", ["À voir", "Déjà vu"])
    affiche_url = film_trouve["affiche"] if film_trouve else ""
    submit_button = st.form_submit_button(label="Ajouter à ma collection")

if submit_button and titre:
    cursor.execute(
        "INSERT INTO dvd (titre, realisateur, annee, genre, statut, affiche) VALUES (?, ?, ?, ?, ?, ?)",
        (titre, realisateur, annee, genre, statut, affiche_url)
    )
    conn.commit()
    st.sidebar.success(f"🎉 '{titre}' ajouté !")

# 3. Affichage de la collection de DVD
st.subheader("🍿 Mon Stock de DVD")
try:
    df = pd.read_sql_query("SELECT id, titre AS 'Titre', realisateur AS 'Réalisateur', annee AS 'Année', genre AS 'Genre', statut AS 'Statut', affiche FROM dvd", conn)
except:
    df = pd.DataFrame()

if not df.empty:
    search_query = st.text_input("🔍 Filtrer mes DVD...")
    df_filtered = df
    if search_query:
        df_filtered = df[df['Titre'].str.contains(search_query, case=False, na=False) | df['Réalisateur'].str.contains(search_query, case=False, na=False)]

    cols = st.columns(4)
    for idx, row in df_filtered.iterrows():
        id_film = row['id']
        with cols[idx % 4]:
            if row.get('affiche'):
                st.image(row['affiche'], use_container_width=True)
            else:
                st.write("🎬 *(Pas d'image)*")
            st.markdown(f"**{row['Titre']}**")
            st.caption(f"De {row['Réalisateur']} ({row['Année']})")
            st.caption(f"🔹 {row['Genre']} | *{row['Statut']}*")
            
            if st.button(f"🗑️ Supprimer", key=f"del_{id_film}"):
                cursor.execute("DELETE FROM dvd WHERE id = ?", (id_film,))
                conn.commit()
                st.rerun()
                
            st.markdown("---")
else:
    st.write("Votre cinémathèque est vide.")

