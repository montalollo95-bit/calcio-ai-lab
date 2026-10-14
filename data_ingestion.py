import streamlit as st
import sqlite3
import requests
from datetime import datetime, timedelta

DB_PATH = "calcio_lab.db"

def inizializza_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS daily_matches")
    
    cursor.execute('''
        CREATE TABLE daily_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament TEXT,
            home_team TEXT,
            away_team TEXT,
            match_time TEXT,
            status TEXT DEFAULT 'PENDING',
            
            raw_stats TEXT,
            
            pronostico_principale TEXT,
            risultati_esatti TEXT,
            asian_handicap TEXT,
            
            pure_prob_1 REAL, pure_prob_x REAL, pure_prob_2 REAL,
            pure_prob_o15 REAL, pure_prob_u15 REAL,
            pure_prob_o25 REAL, pure_prob_u25 REAL,
            pure_prob_o35 REAL, pure_prob_u35 REAL,
            pure_prob_o45 REAL, pure_prob_u45 REAL,
            pure_prob_goal REAL, pure_prob_nogoal REAL,
            
            mg_1_3 REAL, mg_2_4 REAL,
            mg_casa_1_2 REAL, mg_trasf_1_2 REAL,
            
            dossier TEXT
        )
    ''')
    conn.commit()
    conn.close()

def estrai_da_api():
    print("⚡ Mi collego ai server di Flashscore tramite API per estrarre palinsesto...")
    
    URL = "https://flashscore-api1.p.rapidapi.com/api/flashscore/v2/matches/list-by-date" 
    
    # 🔒 CHIAVE NASCOSTA PER FLASHSCORE
    API_KEY = st.secrets["FLASHSCORE_API_KEY"]
    API_HOST = "flashscore-api1.p.rapidapi.com"
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": API_HOST}

    # Calcoliamo oggi e domani
    oggi = datetime.now().strftime("%Y-%m-%d")
    domani = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Creiamo una lista con le date da interrogare
    date_da_scaricare = [oggi, domani]
    matches_estratti = []
    
    for data_match in date_da_scaricare:
        print(f"📅 Scaricamento partite del: {data_match}...")
        querystring = {"sport_id": "1", "date": data_match, "language": "it", "timezone": "Europe/Rome"}
        
        try:
            response = requests.get(URL, headers=headers, params=querystring)
            response.raise_for_status()
            data = response.json()
            
            for torneo in data:
                torneo_nome = torneo.get("country_name", "Torneo Sconosciuto")
                for match in torneo.get("matches", []):
                    home = match.get("home_team", {}).get("name", "Sconosciuto")
                    away = match.get("away_team", {}).get("name", "Sconosciuto")
                    
                    orario = data_match 
                    match_id_fs = match.get("event_id", "")
                    stats_grezze = f"ID Evento Flashscore: {match_id_fs}. Torneo: {torneo_nome}. Data: {data_match}."
                    
                    if home != "Sconosciuto" and away != "Sconosciuto":
                        matches_estratti.append((torneo_nome, home, away, orario, stats_grezze))
                        
        except Exception as e:
            print(f"⚠️ Errore API per la data {data_match}: {e}")

    print(f"🔍 MISSIONE COMPIUTA: Scaricate {len(matches_estratti)} partite in totale tra oggi e domani.")
    return matches_estratti

def salva(matches):
    if not matches: return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for t, h, a, m, s in matches:
        cursor.execute("INSERT INTO daily_matches (tournament, home_team, away_team, match_time, raw_stats, status) VALUES (?, ?, ?, ?, ?, 'PENDING')", (t, h, a, m, s))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    inizializza_database()
    lista = estrai_da_api()
    salva(lista)
    print("✅ Salvataggio completato! Database popolato con i dati strutturati.")