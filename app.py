# app.py
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import requests
import matplotlib.pyplot as plt

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
        data = yf.download(ticker, start=start, end=end, progress=False)
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

# ---------- Interface ----------
st.title("📊 Calcul automatique du Spot d’un Produit Structuré")
st.markdown("Entrez les tickers Yahoo (ex: AAPL, BNP.PA) et les dates (JJ/MM/AAAA) une par ligne.")

nb_sj = st.number_input("Nombre de sous-jacents", min_value=1, max_value=10, value=2)

sous_jacents = {}
cols = st.columns(3)
for i in range(nb_sj):
    st.markdown(f"---\n**Sous-jacent {i+1}**")
    ticker = st.text_input(f"Ticker Yahoo (ex: BNP.PA)", key=f"ticker{i}")
    dates = st.text_area(f"Dates de constatation (JJ/MM/AAAA, une par ligne)", key=f"dates{i}", height=120)
    ponderation = st.number_input(
        f"Pondération (0 = équi-pondérée) pour {ticker or f'#{i+1}'}",
        min_value=0.0, max_value=10.0, value=0.0, step=0.01, key=f"pond{i}"
    )
    if ticker and dates:
        dates_list = [d.strip() for d in dates.split("\n") if d.strip()]
        sous_jacents[ticker.strip().upper()] = {"dates": dates_list, "pond": ponderation}

st.write("")  # espace

if st.button("Calculer le spot"):
    if not sous_jacents:
        st.warning("Aucun sous-jacent renseigné.")
    else:
        resultats = []
        spots, pond_total = 0.0, 0.0

        progress = st.progress(0)
        total = len(sous_jacents)
        idx = 0

        for ticker, info in sous_jacents.items():
            valeurs = [get_price_on_date(ticker, d) for d in info["dates"]]
            # Remplacer None par NaN pour moyenne ignorante
            valeurs_clean = [v for v in valeurs if v is not None]
            if not valeurs_clean:
                spot = None
            else:
                spot = sum(valeurs_clean) / len(valeurs_clean)

            pond = info["pond"] if info["pond"] > 0 else 1.0
            if spot is not None:
                spots += spot * pond
                pond_total += pond

            resultats.append({
                "Ticker": ticker,
                "Dates": ", ".join(info["dates"]),
                "Valeurs": ", ".join([str(v) if v is not None else "N/A" for v in valeurs]),
                "Spot": round(spot, 6) if spot is not None else "N/A",
                "Pondération": pond
            })

            idx += 1
            progress.progress(int(idx/total * 100))

        df = pd.DataFrame(resultats)
        st.subheader("🟦 Résultats individuels")
        st.dataframe(df)

        if pond_total == 0:
            st.error("Impossible de calculer spot global : pondération totale = 0 ou pas de prix valides.")
        else:
            spot_global = spots / pond_total
            st.subheader("⭐ Spot global pondéré")
            st.metric("Spot global", f"{spot_global:.6f}")

            # Graphique simple : barres des spots
            try:
                fig, ax = plt.subplots(figsize=(10,4))
                df_plot = df[df["Spot"] != "N/A"].set_index("Ticker")
                ax.bar(df_plot.index, df_plot["Spot"].astype(float))
                ax.set_ylabel("Spot")
                ax.set_title("Spot par sous-jacent")
                st.pyplot(fig)
            except Exception:
                pass

            # Export Excel (création en mémoire)
            to_export = df.copy()
            out = pd.ExcelWriter("spots_export.xlsx", engine="openpyxl")
            to_export.to_excel(out, index=False, sheet_name="Spots")
            out.save()
            with open("spots_export.xlsx", "rb") as f:
                st.download_button(
                    label="📥 Télécharger le résultat Excel",
                    data=f,
                    file_name="spots.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
