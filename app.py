import streamlit as st
import pandas as pd
import random
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Évaluation de Pertinence RI", layout="wide")

# --- CONSIGNES D'ÉVALUATION PAR DATASET ---
DATASET_INSTRUCTIONS = {
    "MANTIS": " **MANTIS (Recherche Conversationnelle) :** La requête est un historique de discussion. Jugez si le document apporte une réponse pertinente au *dernier message* de l'utilisateur, en tenant compte du contexte de la conversation.",
    "QQP": " **QQP (Intentions Similaires) :** La requête est une question. Jugez si le document (qui est une autre question) a *exactement la même signification* et la même intention. Un score élevé signifie que les deux questions sont des doublons.",
    "TREC": " **TREC 2020 (Recherche Web) :** La requête est une recherche internet standard. Jugez si le document (passage de texte) contient l'information exacte et directe pour répondre au besoin de l'utilisateur."
}

# --- CONNEXION DIRECTE GSPREAD ---
@st.cache_resource
def get_worksheet():
    creds_dict = st.secrets["connections"]["gsheets"]
    credentials = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(credentials)
    return client.open_by_url(creds_dict["spreadsheet"]).worksheet("Sheet1")

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
    
    if order[0] == 0:
        score_baseline = score_a
        score_twsls = score_b
        modele_en_A = "baseline"
    else:
        score_baseline = score_b
        score_twsls = score_a
        modele_en_A = "twsls"
    
    row = questions_df.iloc[st.session_state.current_idx]
    
    new_row = [
        st.session_state.user,
        row['dataset'],
        str(row['query_id']),
        int(score_baseline),  
        int(score_twsls),     
        modele_en_A        
    ]
    
    worksheet.append_row(new_row)
    
    st.session_state.current_idx += 1
    st.session_state.random_order = random.sample([0, 1], 2)

# --- INTERFACE D'ÉVALUATION ---
st.title(f"Évaluation : {st.session_state.user}")
total_q = len(questions_df)
    
if st.session_state.current_idx < total_q:
    idx = st.session_state.current_idx
    st.progress(idx / total_q)
    st.write(f"Question **{idx + 1}** sur {total_q}")
    
    curr_q = questions_df.iloc[idx]
    dataset_name = str(curr_q['dataset']).upper().strip()
    
    if dataset_name == "MANTIS":
        st.info(" **MANTIS (Conversation) :** Jugez si le document répond à la *Dernière question*, en vous aidant de l'historique si besoin.")
        
        # Découpage du texte en liste de messages
        contexte_brut = str(curr_q['context'])
        messages = contexte_brut.split('|||SPLIT|||')
        
        historique = messages[:-1] # Tout sauf le dernier
        derniere_question = messages[-1] # Uniquement le dernier
        
        # On cache l'historique dans un expander fermé par défaut
        if len(historique) > 0:
            with st.expander(" Cliquez ici pour voir l'historique de la conversation", expanded=False):
                for i, msg in enumerate(historique):
                    st.caption(f"Message {i+1}")
                    st.markdown(msg.strip())
                    st.divider()
        
        st.warning(" **Dernière question de l'utilisateur :**")
        st.markdown(derniere_question.strip())

    else:
        if dataset_name in DATASET_INSTRUCTIONS:
            st.info(DATASET_INSTRUCTIONS[dataset_name])
        else:
            st.info(f"Dataset: {dataset_name} - Évaluez la pertinence du document.")
            
        with st.expander("Voir la requête à évaluer", expanded=True):
            st.markdown(str(curr_q['context']))

    st.markdown("---") # Ligne de séparation avant les documents

    # Affichage A/B anonymisé
    responses = [curr_q['response_baseline'], curr_q['response_twsls']]
    order = st.session_state.random_order
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Document A")
        st.markdown(responses[order[0]])
        s_a = st.select_slider("Note A :", options=[1,2,3,4,5], value=3, key=f"a{idx}")
        
    with col2:
        st.subheader("Document B")
        st.markdown(responses[order[1]])
        s_b = st.select_slider("Note B :", options=[1,2,3,4,5], value=3, key=f"b{idx}")

    st.markdown("---")
    if st.button("Valider mes notes", type="primary", use_container_width=True):
        save_score(s_a, s_b)
        st.rerun()
else:
    st.success("Vous avez complété toutes les évaluations.")