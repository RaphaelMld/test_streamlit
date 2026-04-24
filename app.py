import streamlit as st
import pandas as pd
import random
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Évaluation de Pertinence RI", layout="wide")

# --- CONNEXION DIRECTE GSPREAD ---
@st.cache_resource
def get_worksheet():
    # On récupère les identifiants depuis les Secrets Streamlit
    creds_dict = st.secrets["connections"]["gsheets"]
    
    # On s'authentifie officiellement auprès de Google
    credentials = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(credentials)
    
    # On ouvre le fichier cible
    return client.open_by_url(creds_dict["spreadsheet"]).worksheet("Sheet1")

# Initialisation de la connexion Google Sheets
worksheet = get_worksheet()

# --- CHARGEMENT DES QUESTIONS ---
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
            
            with st.spinner("Vérification de votre progression..."):
                # On lit les données directement pour ne rien écraser
                all_records = worksheet.get_all_records()
                count = sum(1 for row in all_records if str(row.get('username', '')) == user_input)
                st.session_state.current_idx = count
                
            st.rerun()
        else:
            st.error("Veuillez entrer un identifiant.")
    st.stop()

# --- LOGIQUE D'ENREGISTREMENT ---
def save_score(score_a, score_b):
    order = st.session_state.random_order
    score_baseline = score_a if order[0] == 0 else score_b
    score_twsls = score_a if order[1] == 0 else score_b
    
    row = questions_df.iloc[st.session_state.current_idx]
    
    new_row = [
        st.session_state.user,
        row['dataset'],
        str(row['query_id']),
        int(score_baseline),
        int(score_twsls),
        "baseline" if order[0] == 0 else "twsls"
    ]
    
    # Ajout instantané à la fin du fichier
    worksheet.append_row(new_row)
    
    # On passe à la suite
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
    with st.expander("Contexte de la requête", expanded=True):
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
        save_score(s_a, s_b)
        st.rerun()
else:
    st.success("Merci ! Vous avez complété toutes les évaluations.")
