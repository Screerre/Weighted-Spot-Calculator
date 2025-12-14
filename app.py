# app.py
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import requests
import matplotlib.pyplot as plt
import re # Nécessaire pour l'extraction de ticker

# Configuration de la page
st.set_page_config(page_title="Spot Calculator", layout="wide")

# ---------- Utilitaires ----------
def get_price_on_date(ticker, date_str):
    """Retourne le prix Close le plus proche de date_str (format JJ/MM/AAAA)"""
    try:
        date = datetime.strptime(date_str.strip(), "%d/%m/%Y")
    except Exception:
        return None
    start = date - timedelta(days=4)
    end = date + timedelta(days=4)
    try:
        # yfinance est sensible à la casse pour certains marchés, mais l'upper() est généralement sûr.
        data = yf.download(ticker.upper(), start=start, end=end, progress=False)
    except Exception:
        return None
    if data is None or data.empty:
        return None
    # normaliser index timezone si besoin
    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)
    data["diff"] = abs(data.index - date)
    closest = data.sort_values("diff").iloc[0]
    return float(closest["Close"])

def safe_float_list(lst):
    return [None if v is None else float(v) for v in lst]

# 🌟 NOUVELLE FONCTION : Résolution de Ticker via Recherche
def resolve_ticker_from_name(name_or_ticker):
    """
    Tente de trouver le ticker Yahoo Finance à partir du nom de la compagnie 
    ou vérifie si l'entrée est déjà un ticker.
    Retourne le ticker (str) ou None.
    """
    clean_input = name_or_ticker.strip().upper()
    
    # 1. Traitement rapide si l'entrée ressemble à un Ticker (court, sans espace)
    # L'heuristique ici est de considérer l'entrée comme Ticker si elle est courte.
    if len(clean_input) <= 6 and (' ' not in clean_input):
        return clean_input 
    
    # 2. Si c'est un nom long, on utilise Google Search pour trouver le ticker.
    query = f"{name_or_ticker} yahoo finance ticker"
    
    try:
        # Appel à l'outil de recherche Google
        response = google.search(queries=[query])
        search_result = response.result
        
        # Logique d'extraction : on cherche dans les titres/descriptions 
        # des résultats un terme qui ressemble fortement à un ticker.
        # Pattern: 1 à 5 lettres/chiffres, optionnellement suivis d'un point et 1-2 lettres (pour les marchés non US)
        # On ne regarde que le début de la réponse pour plus de pertinence.
        match = re.search(r"\b([A-Z0-9]{1,5}\.?[A-Z]{1,2}|[A-Z]{1,5})\b", search_result[:1000])
        
        if match:
            # On vérifie que le résultat n'est pas un mot commun (ex: 'THE')
            potential_ticker = match.group(1).upper()
            if len(potential_ticker) > 1 and potential_ticker not in ['THE', 'AND', 'FOR']:
                return potential_ticker
        
        return None
        
    except Exception:
        # En cas d'erreur lors de l'appel de l'outil de recherche
        return None

# ---------- Interface ----------
st.title("💰 Calcul automatique du Spot d’un Produit Structuré")
st.markdown("Entrez les noms des compagnies ou tickers, et les dates de constatation.")

nb_sj = st.number_input("Nombre de sous-jacents", min_value=1, max_value=10, value=2)

# Sélecteur Global (Unifié)
mode_calcul_global = st.selectbox(
    "Mode de calcul du prix de constatation (applicable à tous les sous-jacents)",
    options=[
        "Moyenne simple",
        "Cours le plus haut (max)",
        "Cours le plus bas (min)"
    ],
    key="mode_calc_global"
)

sous_jacents = {}
for i in range(nb_sj):
    st.markdown(f"---\n**Sous-jacent {i+1}**")
    
    # ⚠️ MODIFIÉ : Accepte Nom ou Ticker
    input_name = st.text_input(
        f"Nom de la compagnie ou Ticker (ex: Apple, BNP.PA)", 
        key=f"name_or_ticker{i}"
    )
    
    dates = st.text_area(f"Dates de constatation (JJ/MM/AAAA, une par ligne)", key=f"dates{i}", height=120)
    
    ponderation = st.number_input(
        f"Pondération (0 = équi-pondérée) pour {input_name or f'#{i+1}'}",
        min_value=0.0, max_value=10.0, value=0.0, step=0.01, key=f"pond{i}"
    )
    
    if input_name and dates:
        
        # 🌟 UTILISATION DE LA FONCTION DE RÉSOLUTION
        resolved_ticker = resolve_ticker_from_name(input_name)
        ticker_to_use = resolved_ticker if resolved_ticker else input_name.strip().upper()

        if resolved_ticker is None and len(input_name.strip()) > 6 and ' ' in input_name.strip():
            st.warning(f"⚠️ **Avertissement** : Ticker introuvable pour **'{input_name}'**. Le script tentera d'utiliser '{ticker_to_use}' (l'entrée brute) pour le calcul. Veuillez vérifier le résultat.")
            
        dates_list = [d.strip() for d in dates.split("\n") if d.strip()]
        
        # Le dictionnaire utilise le Ticker pour la clé (unique)
        sous_jacents[ticker_to_use] = { 
            "dates": dates_list, 
            "pond": ponderation,
            "input_name": input_name.strip(), 
            "resolved_ticker": ticker_to_use   
        }

st.write("")  # espace

if st.button("🚀 Calculer le spot"):
    if not sous_jacents:
        st.error("❌ Aucun sous-jacent renseigné ou impossible d'en déterminer un ticker valide.")
    else:
        resultats = []
        spots, pond_total = 0.0, 0.0

        progress = st.progress(0, text="Récupération des données...")
        total = len(sous_jacents)
        idx = 0
        
        mode_global = mode_calcul_global 

        for ticker, info in sous_jacents.items():
            
            # Récupération des prix
            valeurs = [get_price_on_date(ticker, d) for d in info["dates"]]
            
            # Traitement des valeurs
            valeurs_clean = [v for v in valeurs if v is not None]

            if not valeurs_clean:
                spot = None
            else:
                # Logique de calcul du spot basée sur le mode global
                if mode_global == "Moyenne simple":
                    spot = sum(valeurs_clean) / len(valeurs_clean)
                elif mode_global == "Cours le plus haut (max)":
                    spot = max(valeurs_clean)
                elif mode_global == "Cours le plus bas (min)":
                    spot = min(valeurs_clean)
                else: 
                    spot = sum(valeurs_clean) / len(valeurs_clean) # Fallback

            pond = info["pond"] if info["pond"] > 0 else 1.0
            if spot is not None:
                spots += spot * pond
                pond_total += pond

            resultats.append({
                "Nom Entré": info["input_name"],          
                "Ticker Utilisé": info["resolved_ticker"], 
                "Dates de constatation": ", ".join(info["dates"]),
                "Valeurs (Jours de fix.)": ", ".join([str(v) if v is not None else "N/A" for v in valeurs]),
                "Spot Calculé": round(spot, 6) if spot is not None else "N/A",
                "Pondération": pond
            })

            idx += 1
            progress.progress(int(idx/total * 100))
        
        progress.empty() # Enlever la barre de progression

        df = pd.DataFrame(resultats)
        st.subheader("📊 Résultats individuels par Sous-Jacent")
        st.dataframe(df)

        if pond_total == 0:
            st.error("❌ Impossible de calculer le spot global : pondération totale = 0 ou aucun prix valide trouvé.")
        else:
            spot_global = spots / pond_total
            st.subheader("✨ Spot Global Pondéré du Produit Structuré")
            st.metric("Spot global", f"{spot_global:.6f}")
            st.info(f"Mode de calcul des spots individuels : **{mode_global}**")

            # Graphique simple : barres des spots
            try:
                fig, ax = plt.subplots(figsize=(10,4))
                df_plot = df[df["Spot Calculé"] != "N/A"].set_index("Ticker Utilisé")
                ax.bar(df_plot.index, df_plot["Spot Calculé"].astype(float), color='skyblue')
                ax.set_ylabel("Spot Calculé")
                ax.set_title("Spot par sous-jacent")
                st.pyplot(fig)
            except Exception:
                st.warning("Impossible de générer le graphique.")

            # Export Excel
            to_export = df.copy()
            with pd.ExcelWriter("spots_export.xlsx", engine="openpyxl") as out:
                to_export.to_excel(out, index=False, sheet_name="Spots")
            with open("spots_export.xlsx", "rb") as f:
                st.download_button(
                    label="⬇️ Télécharger le résultat Excel",
                    data=f,
                    file_name="spots.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
