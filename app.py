import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import random

st.set_page_config(page_title="Évaluation de Pertinence RI", layout="wide")

# --- CONNEXION GOOGLE SHEETS ---
# Pour que cela marche, il faudra configurer les "Secrets" sur Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CHARGEMENT DES QUESTIONS (Fichier local dans ton GitHub) ---
@st.cache_data
def load_questions():
    return pd.read_csv("questions.csv")

questions_df = load_questions()

# --- GESTION DE LA SESSION ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0
if 'random_order' not in st.session_state:
    st.session_state.random_order = random.sample([0, 1], 2)

# --- ÉCRAN DE CONNEXION ---
if st.session_state.user is None:
    st.title("Plateforme d'Évaluation")
    user_input = st.text_input("Entrez votre nom ou identifiant pour commencer :")
    if st.button("Démarrer l'évaluation"):
        if user_input:
            st.session_state.user = user_input
            # Récupérer les données existantes pour voir si cet utilisateur a déjà commencé
            existing_data = conn.read(worksheet="Sheet1")
            user_results = existing_data[existing_data['username'] == user_input]
            st.session_state.current_idx = len(user_results)
            st.rerun()
        else:
            st.error("Veuillez entrer un identifiant.")
    st.stop()

# --- LOGIQUE D'ENREGISTREMENT ---
def save_to_gsheets(score_a, score_b):
    order = st.session_state.random_order
    score_baseline = score_a if order[0] == 0 else score_b
    score_twsls = score_a if order[1] == 0 else score_b
    
    row = questions_df.iloc[st.session_state.current_idx]
    
    # Préparation de la nouvelle ligne
    new_row = pd.DataFrame([{
        "username": st.session_state.user,
        "dataset": row['dataset'],
        "query_id": row['query_id'],
        "score_baseline": score_baseline,
        "score_twsls": score_twsls,
        "order_A": "baseline" if order[0] == 0 else "twsls"
    }])
    
    # Lecture, ajout et mise à jour sur Google Sheets
    current_results = conn.read(worksheet="Sheet1")
    updated_results = pd.concat([current_results, new_row], ignore_index=True)
    conn.update(worksheet="Sheet1", data=updated_results)
    
    # Suite
    st.session_state.current_idx += 1
    st.session_state.random_order = random.sample([0, 1], 2)

# --- INTERFACE D'ÉVALUATION ---
st.title(f"📊 Évaluation : {st.session_state.user}")
total_q = len(questions_df)

if st.session_state.current_idx < total_q:
    idx = st.session_state.current_idx
    st.progress(idx / total_q)
    st.write(f"Question **{idx + 1}** sur {total_q}")
    
    curr_q = questions_df.iloc[idx]
    with st.expander("🔍 Contexte de la requête", expanded=True):
        st.info(f"Dataset: {curr_q['dataset']}")
        st.code(curr_q['context'], language="text")

    # Affichage A/B
    responses = [curr_q['response_baseline'], curr_q['response_twsls']]
    order = st.session_state.random_order
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Réponse A")
        st.write(responses[order[0]])
        s_a = st.select_slider("Note A :", options=[1,2,3,4,5], value=3, key=f"a{idx}")
    with col2:
        st.subheader("Réponse B")
        st.write(responses[order[1]])
        s_b = st.select_slider("Note B :", options=[1,2,3,4,5], value=3, key=f"b{idx}")

    if st.button("Valider", type="primary", use_container_width=True):
        save_to_gsheets(s_a, s_b)
        st.rerun()
else:
    st.balloons()
    st.success("Merci ! Vous avez complété toutes les évaluations.")