# app.py
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import re 

st.set_page_config(page_title="Spot Calculator", layout="wide")

# ---------- Utilitaires ----------
# ... (Fonctions get_price_on_date, safe_float_list, is_valid_ticker, resolve_ticker_from_name restent inchangées)

def get_price_on_date(ticker, date_str):
    """Retourne le prix Close le plus proche de date_str (format JJ/MM/AAAA)"""
    try:
        date = datetime.strptime(date_str.strip(), "%d/%m/%Y")
    except Exception:
        return None
    start = date - timedelta(days=4)
    end = date + timedelta(days=4)
    try:
        data = yf.download(ticker.upper(), start=start, end=end, progress=False)
    except Exception:
        return None
    if data is None or data.empty:
        return None
    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)
    data["diff"] = abs(data.index - date)
    closest = data.sort_values("diff").iloc[0]
    return float(closest["Close"])

def safe_float_list(lst):
    return [None if v is None else float(v) for v in lst]

def is_valid_ticker(ticker):
    """Vérifie rapidement si un ticker est reconnu par yfinance."""
    if not ticker: return False
    try:
        info = yf.Ticker(ticker).info
        if 'longName' in info and len(info.get('longName', '')) > 2:
            return True
        return False
    except Exception:
        return False

def resolve_ticker_from_name(name_or_ticker):
    """
    Tente de trouver le ticker Yahoo Finance en utilisant d'abord un mappage 
    pour les noms courants, puis la vérification directe (pour les tickers inconnus).
    """
    clean_input = name_or_ticker.strip().upper()
    
    # --- 1. Mappage Direct des noms courants (Liste Blanche) ---
    COMMON_TICKERS = {
        "APPLE": "AAPL", "MICROSOFT": "MSFT", "GOOGLE": "GOOGL", "ALPHABET": "GOOGL",
        "AMAZON": "AMZN", "NVIDIA": "NVDA", "TESLA": "TSLA", "META": "META",
        "BERKSHIRE HATHAWAY": "BRK-A", "VISA": "V", "JOHNSON & JOHNSON": "JNJ",
        "JPMORGAN CHASE": "JPM", "EXXON MOBIL": "XOM", "COCA-COLA": "KO",
        "WALMART": "WMT", "DISNEY": "DIS", "LVMH": "LVMH.PA", "LOREAL": "OR.PA",
        "TOTALENERGIES": "TTE", "SANTE": "SAN.PA", "BNP PARIBAS": "BNP.PA",
        "BNP": "BNP.PA", "SOCIETE GENERALE": "GLE.PA", "HERMES": "RMS.PA",
        "AIRBUS": "AIR.PA", "AXA": "CS.PA", "SAP": "SAP.DE", "SIEMENS": "SIE.DE",
        "BAYER": "BAYN.DE", "SAMSUNG": "005930.KS", "TAIWAN SEMICONDUCTOR": "TSM",
        "TOYOTA": "TM"
    }

    if clean_input in COMMON_TICKERS:
        return COMMON_TICKERS[clean_input]

    # 2. Vérification si l'entrée est un Ticker non mappé
    if len(clean_input) <= 10 and (' ' not in clean_input):
        if is_valid_ticker(clean_input):
            return clean_input
            
    return None 

# ---------- Interface ----------
st.title("💰 Calcul automatique du Spot d’un Produit Structuré")
st.markdown("Entrez le **Nom de la compagnie** ou le Ticker (ex: Apple, BNP.PA).")

nb_sj = st.number_input("Nombre de sous-jacents", min_value=1, max_value=10, value=2)

# 🌟 RÉINTÉGRÉ : Sélecteur Global
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
    
    input_name = st.text_input(
        f"Nom de la compagnie ou Ticker (ex: Apple, BNP.PA)", 
        key=f"name_or_ticker{i}"
    )
    
    dates = st.text_area(f"Dates de constatation (JJ/MM/AAAA, une par ligne)", key=f"dates{i}", height=120)
    
    ponderation = st.number_input(
        f"Pondération (0 = équi-pondérée) pour {input_name or f'#{i+1}'}",
        min_value=0.0, max_value=10.0, value=0.0, step=0.01, key=f"pond{i}"
    )
    
    if input_name:
        resolved_ticker = resolve_ticker_from_name(input_name)
        ticker_to_use = resolved_ticker if resolved_ticker else input_name.strip().upper()
        
        dates_list = [d.strip() for d in dates.split("\n") if d.strip()]

        if not resolved_ticker:
             st.error(f"❌ Ticker introuvable pour **'{input_name}'**. Utilisation de l'entrée brute : **{ticker_to_use}** (risque d'échec de récupération des prix).")

        if dates_list:
            sous_jacents[ticker_to_use] = { 
                "dates": dates_list, 
                "pond": ponderation,
                "input_name": input_name.strip(), 
                "resolved_ticker": ticker_to_use   
            }
        elif resolved_ticker:
             st.warning(f"❗ **Attention** : Les dates de constatation pour **{ticker_to_use}** sont manquantes. Ce sous-jacent ne sera pas inclus dans le calcul.")


st.write("") 

if st.button("🚀 Calculer le spot"):
    if not sous_jacents:
        st.error("❌ Impossible de lancer le calcul. Aucun sous-jacent n'a pu être configuré (vérifiez le Ticker ET les dates).")
    else:
        resultats = []
        spots, pond_total = 0.0, 0.0

        progress = st.progress(0, text="Récupération des données...")
        total = len(sous_jacents)
        idx = 0
        
        # Le mode global est maintenant récupéré depuis le sélecteur
        mode_global = mode_calcul_global 
        prix_manquants_compteur = 0

        for ticker, info in sous_jacents.items():
            
            valeurs = [get_price_on_date(ticker, d) for d in info["dates"]]
            
            valeurs_clean = [v for v in valeurs if v is not None]

            if not valeurs_clean:
                spot = None
                prix_manquants_compteur += 1
            else:
                # 🌟 RÉINTÉGRÉ : Logique de calcul basée sur le mode global
                if mode_global == "Moyenne simple":
                    spot = sum(valeurs_clean) / len(valeurs_clean)
                elif mode_global == "Cours le plus haut (max)":
                    spot = max(valeurs_clean)
                elif mode_global == "Cours le plus bas (min)":
                    spot = min(valeurs_clean)
                else: 
                    spot = sum(valeurs_clean) / len(valeurs_clean) # Fallback sécurité

            pond = info["pond"] if info["pond"] > 0 else 1.0
            if spot is not None:
                spots += spot * pond
                pond_total += pond

            resultats.append({
                "Nom Entré": info["input_name"],          
                "Ticker Utilisé": info["resolved_ticker"], 
                "Dates": ", ".join(info["dates"]),
                "Valeurs": ", ".join([str(v) if v is not None else "N/A" for v in valeurs]),
                "Spot": round(spot, 6) if spot is not None else "N/A",
                "Pondération": pond
            })

            idx += 1
            progress.progress(int(idx/total * 100))
        
        progress.empty() 

        df = pd.DataFrame(resultats)
        st.subheader("📊 Résultats individuels par Sous-Jacent")
        st.dataframe(df)
        
        if prix_manquants_compteur > 0:
            st.warning(f"⚠️ Attention : {prix_manquants_compteur} sous-jacent(s) n'a/ont pas pu avoir son/leur spot calculé (Ticker non reconnu ou données manquantes).")


        if pond_total == 0:
            st.error("❌ Impossible de calculer le spot global : pondération totale = 0 ou pas de prix valides. Vérifiez vos dates.")
        else:
            spot_global = spots / pond_total
            st.subheader("✨ Spot global pondéré")
            st.metric("Spot global", f"{spot_global:.6f}")
            st.info(f"Mode de calcul des spots individuels : **{mode_global}**") # Affichage du mode

            # Graphique simple : barres des spots
            try:
                fig, ax = plt.subplots(figsize=(10,4))
                df_plot = df[df["Spot"] != "N/A"].set_index("Ticker Utilisé")
                ax.bar(df_plot.index, df_plot["Spot"].astype(float))
                ax.set_ylabel("Spot")
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
