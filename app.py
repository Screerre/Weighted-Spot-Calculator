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
        "BERKSHIRE HATHAWAY": "BRK-A","JOHNSON & JOHNSON": "JNJ",
        "JPMORGAN CHASE": "JPM", "EXXON MOBIL": "XOM", "COCA-COLA": "KO",
        "WALMART": "WMT", "DISNEY": "DIS", "LVMH": "LVMH.PA", "LOREAL": "OR.PA",
        "TOTALENERGIES": "TTE", "SANTE": "SAN.PA", "BNP PARIBAS": "BNP.PA",
        "BNP": "BNP.PA", "SOCIETE GENERALE": "GLE.PA", "HERMES": "RMS.PA",
        "AIRBUS": "AIR.PA", "AXA": "CS.PA", "SAP": "SAP.DE", "SIEMENS": "SIE.DE",
        "BAYER": "BAYN.DE", "SAMSUNG": "005930.KS", "TSMC": "TSM",
        "TOYOTA": "TM","JPMORGAN CHASE": "JPM","BANK OF AMERICA": "BAC",
        "WELLS FARGO & CO": "WFC","GOLDMAN SACHS": "GS","MORGAN STANLEY": "MS",
        "CITIGROUP INC": "C","CITIGROUP": "C","CITI" : "C","BNP PARIBAS": "BNP.PA",
        "CREDIT AGRICOLE": "ACA.PA","DEUTSCHE BANK AG": "DBK.DE","COMMERZBANK AG": "CBK.DE",
        "UBS GROUP AG": "UBSG.SW","UBS GROUP" : "UBSG.SW","UBS": "UBSG.SW","CREDIT SUISSE": "CSGN.SW",
        "STANDARD CHARTERED": "STAN.L","BARCLAYS PLC": "BARC.L","LLOYDS BANKING GROUP": "LLOY.L",
        "NATWEST GROUP": "NWG.L","ROYAL BANK OF CANADA": "RY","TORONTO-DOMINION BANK": "TD",
        "SOCIETE GENERALE": "GLE.PA","HSBC": "HSBA.L",
  # --- BANQUES RÉGIONALES ET SPÉCIALISÉES (US & EU) ---
        "PNC FINANCIAL SERV": "PNC","US BANCORP": "USB","CAPITAL ONE FINANCIAL": "COF",
        "ZIONS BANCORP": "ZION","COMERICA INC": "CMA","HUNTINGTON BANCSHARES": "HBAN",
        "REGIONS FINANCIAL CORP": "RF","FIFTH THIRD BANCORP": "FITB","KEYCORP": "KEY",
        "EAST WEST BANCORP": "EWBC","ING GROEP NV": "INGA.AS","KBC GROUP NV": "KBC.BR",
        "BANCO SANTANDER": "SAN","UNICREDIT SPA": "UCG.MI",
        "INTESA SANPAOLO": "ISP.MI","BANCO DE SABADELL": "SAB.MC","CAIXABANK SA": "CABK.MC",
        "MEDIOBANCA SPA": "MB.MI","NORDEA BANK ABP": "NDA-DK.CO",
        "DANSKE BANK A/S": "DANSKE.CO","SWEDBANK AB": "SWED A.ST","SEB AB": "SEB A.ST",
 # --- ASSURANCES (VIE, NON-VIE, RÉASSURANCE) ---
        "CHUBB LTD": "CB","AIG": "AIG","METLIFE INC": "MET","PRUDENTIAL FINANCIAL": "PRU",
        "UNUM GROUP": "UNM","TRUIST FINANCIAL CORP": "TFC","ALLIANZ SE": "ALV.DE",
        "MUNICH RE": "MUV2.DE","HANNOVER RE": "HNR1.DE","ZURICH INSURANCE GR": "ZURN.SW",
        "GENERALI ASSICURAZIONI": "G.MI","AVIVA PLC": "AV.L","LEGAL & GENERAL GR": "LGEN.L",
        "PRUDENTIAL PLC (UK)": "PRU.L","MANULIFE FINANCIAL": "MFC","SUN LIFE FINANCIAL": "SLF",
        "AXA SA": "CS.PA",
 # --- GESTION D'ACTIFS ET MARCHÉS DE CAPITAUX ---
       "BLACKROCK INC": "BLK","VANGUARD": "VTI","STATE STREET CORP": "STT","CME GROUP": "CME",
       "BANK OF NEW YORK MELLON": "BK","NORTHERN TRUST CORP": "NTRS","CME GROUP": "CME",
       "INTERCONTINENTAL EXC": "ICE","CBOE GLOBAL MARKETS": "CBOE","NASDAQ INC": "NDAQ",
       "LSE GROUP PLC": "LSEG.L","DEUTSCHE BOERSE AG": "DB1.DE","EURONEXT NV": "ENX.PA",
       "HONG KONG EXCHANGES": "0388.HK","S&P GLOBAL INC": "SPGI","MOODY'S CORP": "MCO",
       "FACTSET RESEARCH": "FDS",
 # --- FINTECH ET PAIEMENTS ---
       "VISA INC": "V","MASTERCARD INC": "MA","AMERICAN EXPRESS": "AXP", "FIS GLOBAL": "FIS",
       "PAYPAL HOLDINGS": "PYPL","SQUARE (BLOCK INC)": "SQ","COINBASE GLOBAL": "COIN",
       "ADYEN NV": "ADYEN.AS","GLOBAL PAYMENTS INC": "GPN","FISERV INC": "FISV",
       "FIS GLOBAL": "FIS","DISCOVER FINANCIAL SERV": "DFS","SYNCHRONY FINANCIAL": "SYF",
       "AFFIRM HOLDINGS": "AFRM","SOFI TECHNOLOGIES": "SOFI","ROBINHOOD MARKETS": "HOOD",
       "WISE PLC": "WISE.L","PAGSEGURO DIGITAL": "PAGS","STONECO LTD": "STNE", 
# -- BANQUES ASIATIQUES ET ÉMERGENTES --
       "MITSUBISHI UFJ FIN": "8306.T","SUMITOMO MITSUI FIN": "8316.T","MIZUHO FINANCIAL GR": "8411.T",
       "NOMURA HOLDINGS": "8604.T","HDFC BANK": "HDFCBANK.NS","ICICI BANK": "ICICIBANK.NS",
       "AXIS BANK": "AXISBANK.NS","STATE BANK OF INDIA": "SBIN.NS","BANK OF CHINA": "3988.HK",
       "CHINA CONSTRUCTION BK": "0939.HK","ICBC": "1398.HK","WESTPAC BANKING CORP": "WBC.AX",
       "ANZ GROUP HOLDINGS": "ANZ.AX","COMMONWEALTH BANK AUS": "CBA.AX","MACQUARIE GROUP": "MQG.AX",
       "DBS GROUP HOLDINGS": "DBSM.SI","OVERSEAS CHINESE BK": "OCBC.SI"
# -- BOITES IA ET TECH --
       "ARISTANETWORKS": "ANET","ACLARARES": "ACLA","ALPHA&OMEGASEMI": "AOSL","MONOLITHICPOWERSYS": "MPWR",
       "QORVOINC": "QRVO","LUMINARTECH": "LAZR","AMD": "AMD","GLOBO": "GLBE","AXCELISTECHNOLOGIES": "ACLS",
       "NOVARTUS": "NVTS","SILICONLABS": "SLAB","HIMAXTECHNOLOGIES": "HIMX","INPHICORPORATION": "IPHI",
       "ONSEMICONDUCTOR": "ON","MACOMTECHNOLOGY": "MTSI","MKSINSTRUMENTS": "MKSI","ULVAC": "6728.T",
       "OKTAINC": "OKTA","DATADOG": "DDOG","COUPASOFTWARE": "COUP","C3AI": "AI","UPSTARTHOLDINGS": "UPST",
       "VEEVASYSTEMS": "VEEV","ZENDESK": "ZEN","NEWRELIC": "NEWR","MULESOFT": "MULE","ASANA": "ASAN",
       "PALANTIRTECHNOLOGIES": "PLTR","DRAFTKINGS": "DKNG","CROWDSTRIKEHOLDINGS": "CRWD","ZSCALER": "ZS",
       "FORTINET": "FTNT","CHECKPOINTSOFTWARE": "CHKP","CYBERARKSOFTWARE": "CYBR","PROOFPOINT": "PFPT",
       "OKTA": "OKTA","ACTEURSASIATIQUES&EUROPÉENS": "","NORDICSEMICONDUCTOR": "NOD.OL","IMEC": "IMEC.BR",
       "ACCELERATED": "ACEL","INFINEONTECHNOLOGIES": "IFX.DE","STMICROELECTRONICS": "STM","JD.COM": "JD",
       "ASMLHOLDING": "ASML","MEITUAN": "3690.HK","JD.COM": "JD","BAIDUINC": "BIDU","NETEASEINC": "NTES",
       "SKHYNIX": "000660.KS","KINGSOFTCLOUD": "KC","SONYGROUPCORP": "SONY","CANONINC": "CAJ","REDHAT": "IBM",
       "ARCELIKAS": "ARCLK.IS","INVITAECORP": "NVTA","TAIYOYUDENCO": "6976.T","TOKYOELECTRONLTD": "8035.T",
       "SCREENHOLDINGSCO": "7735.T","BESEMICONDUCTOR": "BESI.AS","EVOTECSE": "EVT.DE","BIONTECHSE": "BNTX",
       "TELADOCHEALTH": "TDOC","MAXLINEARINC": "MXL","WIX.COMLTD": "WIX","RINGCENTRAL": "RNG",
       "PAYCOMSOFTWARE": "PAYC","DOCUSIGNINC": "DOCU","TERADATACORP": "TDC","DATTOHOLDINGCORP": "DATTO",
       "CHECKPOINTSOFT": "CHKP","PALOALTONETWORKS": "PANW","ASANAINC": "ASAN","FASTLYINC": "FSLY",
       "LATTICESEMICON": "LSCC","DURATIONMEDIA": "DUR","ROHMCOLTD": "6963.T","DISCOCORP": "6146.T",
       "PHOTRONLTD": "6899.T","AMS-OSRAMAG": "AMS.SW","SARTORIUSSTEDIM": "DIM.PA","CUREVACNV": "CVAC",
       "ACCELERATEDIAGNOSTICS": "AXDX","SAGEGROUPPLC": "SGE.L","HUBSPOTINC": "HUBS","CLOUDERA": "CLDR",
       "FIVERRINTERNATIONAL": "FVRR","AUTOMATICDATAPROC": "ADP","HEWLETTPACKARDENT": "HPE",
       "COUPASOFTWARE": "COUP","DXCTECHNOLOGY": "DXC","CYBERARKSOFTWARE": "CYBR","ZSCALERINC": "ZS",
       "C3.AIINC": "AI","CORTICELLIB": "CORB","CREEINC": "CREE","AMBARELLAINC": "AMBA","SUMCOCORP": "3436.T",
       "LASERTECCORP": "6920.T","ASMINTERNATIONAL": "ASM.AS","AIXTRONSE": "AIXA.DE","GENMABAS": "GMAB.CO",
       "VAXARTINC": "VXRT","INSIGHTENTERPRISES": "NSIT","AVEVAGROUPPLC": "AVV.L","ZILLOWGROUP": "Z",
       "OKTAINC": "OKTA","UPWORKINC": "UPWK","SALESFORCEINC": "CRM","DELLTECHNOLOGIES": "DELL",
       "PAGERDUTYINC": "PD","MICROFOCUSINTL": "MCRO.L","FORTINETINC": "FTNT","VEEVASYSTEMS": "VEEV",
       "ATOSSE": "ATOS.PA","UPSTARTHOLDINGS": "UPST","SUMOLOGIC": "SUMO","SPLUNKINC": "SPLK",
}

    if clean_input in COMMON_TICKERS:
        return COMMON_TICKERS[clean_input]

    # 2. Vérification si l'entrée est un Ticker non mappé
    if len(clean_input) <= 10 and (' ' not in clean_input):
        if is_valid_ticker(clean_input):
            return clean_input
            
    return None 

# ---------- Interface ----------
st.title("<Calcul automatique du Spot d’un Produit Structuré>")
st.markdown("Entrez le **Nom de la compagnie** ou le Ticker (ex: Apple, BNP.PA).")

nb_sj = st.number_input("Nombre de sous-jacents", min_value=1, max_value=10, value=2)

# RÉINTÉGRÉ : Sélecteur Global
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
             st.error(f"Ticker introuvable pour **'{input_name}'**. Utilisation de l'entrée brute : **{ticker_to_use}** (risque d'échec de récupération des prix).")

        if dates_list:
            sous_jacents[ticker_to_use] = { 
                "dates": dates_list, 
                "pond": ponderation,
                "input_name": input_name.strip(), 
                "resolved_ticker": ticker_to_use   
            }
        elif resolved_ticker:
             st.warning(f" **Attention** : Les dates de constatation pour **{ticker_to_use}** sont manquantes. Ce sous-jacent ne sera pas inclus dans le calcul.")


st.write("") 

if st.button("Calculer le spot"):
    if not sous_jacents:
        st.error("Impossible de lancer le calcul. Vérifiez le Ticker et les dates.")
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
                # RÉINTÉGRÉ : Logique de calcul basée sur le mode global
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
        st.subheader("- Résultats individuels par Sous-Jacent -")
        st.dataframe(df)
        
        if prix_manquants_compteur > 0:
            st.warning(f"Attention : {prix_manquants_compteur} sous-jacent(s) n'a/ont pas pu avoir son/leur spot calculé (Ticker non reconnu ou données manquantes).")


        if pond_total == 0:
            st.error("Impossible de calculer le spot global : pondération totale = 0 ou pas de prix valides. Vérifiez vos dates.")
        else:
            spot_global = spots / pond_total
            st.subheader("- Spot global pondéré -")
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
                    label="Télécharger le résultat Excel",
                    data=f,
                    file_name="spots.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
