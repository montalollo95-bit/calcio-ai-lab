import streamlit as st
import sqlite3
import re
import time
from google import genai
from google.genai import types

DB_PATH = "calcio_lab.db"

# 🔒 CHIAVE NASCOSTA PER GEMINI
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

SISTEMA_PROMPT = """Sei un algoritmo quantitativo di scommesse di livello istituzionale. Il tuo compito è unire analisi statistica avanzata (xG), studio dei Tier e tattica per generare il pronostico più preciso possibile. Tutte le tue valutazioni nel dossier DEVONO convergere e giustificare la tua previsione assoluta.
REGOLA FONDAMENTALE: Devi copiare e incollare il blocco sottostante e compilarlo. NON usare il grassetto (**), NON usare formattazioni strane sulle chiavi in maiuscolo. Scrivi esattamente le chiavi così come le vedi.

PRONOSTICO_PRINCIPALE: [Esito]
RISULTATI_ESATTI_PROBABILI: [Esiti]
ASIAN_HANDICAP_CONSIGLIATO: [Handicap]

PROBABILITA_1: [Numero]
PROBABILITA_X: [Numero]
PROBABILITA_2: [Numero]
PROBABILITA_OVER_15: [Numero]
PROBABILITA_UNDER_15: [Numero]
PROBABILITA_OVER_25: [Numero]
PROBABILITA_UNDER_25: [Numero]
PROBABILITA_OVER_35: [Numero]
PROBABILITA_UNDER_35: [Numero]
PROBABILITA_OVER_45: [Numero]
PROBABILITA_UNDER_45: [Numero]
PROBABILITA_GOAL: [Numero]
PROBABILITA_NOGOAL: [Numero]
MULTIGOAL_1_3: [Numero]
MULTIGOAL_2_4: [Numero]
MULTIGOAL_CASA_1_2: [Numero]
MULTIGOAL_TRASFERTA_1_2: [Numero]

DOSSIER_TECNICO:
🎯 PREVISIONE ASSOLUTA E SINTESI
[Analisi riassuntiva cruda e diretta che FONDE i dati su xG, Tier e tattica per giustificare matematicamente e logicamente il pronostico principale che hai scelto]

📊 Metriche Avanzate e Produzione Offensiva
* xG e Expected Points: [Analisi profonda degli xG prodotti e subiti di entrambe le squadre, e lo scarto tra gol reali e attesi]
* Tiri e Pericolosità: [Volume di tiri in porta, grandi occasioni create e concesse]

🏟️ Comportamento per Fascia (Tier Analysis)
* Squadra Casa vs Fascia Avversario: [Come si comporta storicamente la squadra di casa quando affronta squadre del livello specifico della squadra in trasferta]
* Squadra Trasferta vs Fascia Avversario: [Come si comporta storicamente la squadra in trasferta quando affronta squadre del livello specifico della squadra di casa]

🚑 Analisi Formazioni, News & Calendario
* Squadra Casa: [Infortuni, mal di pancia, assenze pesanti e stato di forma REALE E AGGIORNATO A OGGI]
* Squadra Trasferta: [Infortuni, mal di pancia, assenze pesanti e stato di forma REALE E AGGIORNATO A OGGI]

♟️ Matchup Tattico
* Modulo e Impostazione: [Analisi dei moduli reali in campo e allenatori ATTUALI]
* Vulnerabilità: [Spiega esattamente dove e come una squadra colpirà i punti deboli dell'altra]

💡 IL FATTORE X (La chiave invisibile)
[Inserisci il dettaglio essenziale che sfugge ai bookmaker: motivazioni psicologiche, un singolo duello individuale chiave in campo, l'impatto dell'arbitro o l'effetto di un meteo estremo]

🛡️ CONSIGLIO DEL RISK MANAGER
[Valutazione finale indipendente sulla varianza del match e sul livello di rischio della giocata]
"""

def estrai_dati_da_risposta(testo):
    testo_pulito = testo.replace("**", "").replace("*", "")
    
    dati = {
        "pronostico_principale": "N/A", "risultati_esatti": "N/A", "asian_handicap": "N/A",
        "prob_1": 0.0, "prob_x": 0.0, "prob_2": 0.0,
        "prob_o15": 0.0, "prob_u15": 0.0, "prob_o25": 0.0, "prob_u25": 0.0,
        "prob_o35": 0.0, "prob_u35": 0.0, "prob_o45": 0.0, "prob_u45": 0.0,
        "prob_goal": 0.0, "prob_nogoal": 0.0,
        "mg_1_3": 0.0, "mg_2_4": 0.0, "mg_casa_1_2": 0.0, "mg_trasf_1_2": 0.0,
        "dossier": ""
    }

    try:
        match_pronostico = re.search(r"PRONOSTICO_PRINCIPALE:\s*(.+)", testo_pulito, re.IGNORECASE)
        dati["pronostico_principale"] = match_pronostico.group(1).strip() if match_pronostico else "N/A"
        
        match_esatti = re.search(r"RISULTATI_ESATTI_PROBABILI:\s*(.+)", testo_pulito, re.IGNORECASE)
        dati["risultati_esatti"] = match_esatti.group(1).strip() if match_esatti else "N/A"
        
        match_asian = re.search(r"ASIAN_HANDICAP_CONSIGLIATO:\s*(.+)", testo_pulito, re.IGNORECASE)
        dati["asian_handicap"] = match_asian.group(1).strip() if match_asian else "N/A"
        
        for key, pattern in [
            ("prob_1", r"PROBABILITA_1:\s*([\d\.]+)"), ("prob_x", r"PROBABILITA_X:\s*([\d\.]+)"), ("prob_2", r"PROBABILITA_2:\s*([\d\.]+)"),
            ("prob_o15", r"PROBABILITA_OVER_15:\s*([\d\.]+)"), ("prob_u15", r"PROBABILITA_UNDER_15:\s*([\d\.]+)"),
            ("prob_o25", r"PROBABILITA_OVER_25:\s*([\d\.]+)"), ("prob_u25", r"PROBABILITA_UNDER_25:\s*([\d\.]+)"),
            ("prob_o35", r"PROBABILITA_OVER_35:\s*([\d\.]+)"), ("prob_u35", r"PROBABILITA_UNDER_35:\s*([\d\.]+)"),
            ("prob_o45", r"PROBABILITA_OVER_45:\s*([\d\.]+)"), ("prob_u45", r"PROBABILITA_UNDER_45:\s*([\d\.]+)"),
            ("prob_goal", r"PROBABILITA_GOAL:\s*([\d\.]+)"), ("prob_nogoal", r"PROBABILITA_NOGOAL:\s*([\d\.]+)"),
            ("mg_1_3", r"MULTIGOAL_1_3:\s*([\d\.]+)"), ("mg_2_4", r"MULTIGOAL_2_4:\s*([\d\.]+)"),
            ("mg_casa_1_2", r"MULTIGOAL_CASA_1_2:\s*([\d\.]+)"), ("mg_trasf_1_2", r"MULTIGOAL_TRASFERTA_1_2:\s*([\d\.]+)"),
        ]:
            match = re.search(pattern, testo_pulito, re.IGNORECASE)
            if match: dati[key] = float(match.group(1).strip())

        dossier_match = re.search(r"DOSSIER_TECNICO:\s*(.*)", testo, re.DOTALL | re.IGNORECASE)
        dati["dossier"] = dossier_match.group(1).strip() if dossier_match else testo_pulito
    except Exception as e:
        print(f"Errore parsing: {e}")
        dati["dossier"] = testo

    return dati

def analizza_partite():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, home_team, away_team, tournament, raw_stats FROM daily_matches WHERE status = 'QUEUED'")
    matches = cursor.fetchall()
    
    if not matches:
        print("Nessuna partita in coda (QUEUED).")
        conn.close()
        return

    for match in matches:
        match_id, home, away, tournament, raw_stats = match
        print(f"🧠 Analisi in corso per: {home} vs {away} (connessione web ATTIVA)...")
        
        prompt_utente = f"CERCA SUL WEB le ultime notizie di OGGI, formazioni, infortuni e dichiarazioni degli allenatori ATTUALI per {home} vs {away} ({tournament}). Poi, basandoti sui dati reali trovati online, compila rigorosamente il modulo."
        
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt_utente,
                config=types.GenerateContentConfig(
                    system_instruction=SISTEMA_PROMPT,
                    tools=[{"google_search": {}}], 
                    temperature=0.4 
                )
            )
            d = estrai_dati_da_risposta(response.text)
            
            cursor.execute('''
                UPDATE daily_matches SET 
                    status = 'COMPLETED',
                    pronostico_principale = ?, risultati_esatti = ?, asian_handicap = ?,
                    pure_prob_1 = ?, pure_prob_x = ?, pure_prob_2 = ?,
                    pure_prob_o15 = ?, pure_prob_u15 = ?, pure_prob_o25 = ?, pure_prob_u25 = ?,
                    pure_prob_o35 = ?, pure_prob_u35 = ?, pure_prob_o45 = ?, pure_prob_u45 = ?,
                    pure_prob_goal = ?, pure_prob_nogoal = ?,
                    mg_1_3 = ?, mg_2_4 = ?, mg_casa_1_2 = ?, mg_trasf_1_2 = ?,
                    dossier = ?
                WHERE id = ?
            ''', (
                d['pronostico_principale'], d['risultati_esatti'], d['asian_handicap'],
                d['prob_1'], d['prob_x'], d['prob_2'],
                d['prob_o15'], d['prob_u15'], d['prob_o25'], d['prob_u25'],
                d['prob_o35'], d['prob_u35'], d['prob_o45'], d['prob_u45'],
                d['prob_goal'], d['prob_nogoal'],
                d['mg_1_3'], d['mg_2_4'], d['mg_casa_1_2'], d['mg_trasf_1_2'],
                d['dossier'], match_id
            ))
            conn.commit()
            print(f"✅ Completata con successo: {home} vs {away}")
            time.sleep(4) 
            
        except Exception as e:
            print(f"❌ Errore su {home} vs {away}: {e}")
            cursor.execute("UPDATE daily_matches SET status = 'ERROR' WHERE id = ?", (match_id,))
            conn.commit()
            
    conn.close()

if __name__ == "__main__":
    analizza_partite()