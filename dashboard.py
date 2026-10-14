import streamlit as st
import sqlite3
import pandas as pd
import time
import os
import data_ingestion
import brain_agent

DB_PATH = "calcio_lab.db"

# Rimosso layout="wide" per farlo adattare in automatico allo schermo del cellulare
st.set_page_config(page_title="Calcio AI Lab", page_icon="📱")
st.title("⚽ Calcio AI Lab")

st.markdown("### 🎛️ Pannello di Controllo")
# Su cellulare questi due pulsanti si metteranno automaticamente uno sopra l'altro
col1, col2 = st.columns(2)

with col1:
    if st.button("📥 1. Scarica Palinsesto", use_container_width=True):
        with st.spinner("Scaricamento di oggi e domani..."):
            data_ingestion.inizializza_database()
            lista = data_ingestion.estrai_da_api()
            data_ingestion.salva(lista)
        st.success("✅ Partite scaricate!")
        time.sleep(2)
        st.rerun()

with col2:
    if st.button("🧠 3. Avvia Analisi AI", use_container_width=True, type="primary"):
        with st.spinner("Gemini AI sta analizzando il web..."):
            brain_agent.analizza_partite()
        st.success("✅ Analisi completata!")
        time.sleep(2)
        st.rerun()

st.markdown("---")

def load_data(status_filter):
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        query = f"SELECT id, match_time, tournament, home_team, away_team, status FROM daily_matches WHERE status IN ({status_filter}) ORDER BY match_time, tournament"
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        df = pd.DataFrame()
    conn.close()
    return df

st.markdown("### 📋 2. Coda Analisi")

df_pending = load_data("'PENDING', 'ERROR'")
partite_da_mettere_in_coda = []

if not df_pending.empty:
    grouped_df = df_pending.groupby("tournament")
    for torneo, group in grouped_df:
        with st.expander(f"🏆 {torneo} ({len(group)})"):
            for index, row in group.iterrows():
                # Formattazione più compatta per il cellulare
                label_partita = f"{row['match_time'][5:]} | {row['home_team']} - {row['away_team']}"
                selezionata = st.checkbox(label_partita, key=f"check_{row['id']}")
                if selezionata:
                    partite_da_mettere_in_coda.append(row['id'])
    
    if st.button("➕ Metti in coda", use_container_width=True):
        if not partite_da_mettere_in_coda:
            st.warning("Seleziona almeno una partita!")
        else:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for match_id in partite_da_mettere_in_coda:
                cursor.execute("UPDATE daily_matches SET status = 'QUEUED' WHERE id = ?", (match_id,))
            conn.commit()
            conn.close()
            st.success(f"✅ {len(partite_da_mettere_in_coda)} in coda!")
            time.sleep(2)
            st.rerun()
else:
    st.info("Nessuna partita. Scarica il palinsesto in alto.")

st.markdown("---")
st.markdown("### 💎 4. Dossier e Risultati")

df_completed = load_data("'COMPLETED'")

if not df_completed.empty:
    grouped_completed = df_completed.groupby("tournament")
    for torneo, group in grouped_completed:
        st.markdown(f"**🏆 {torneo}**")
        for index, row in group.iterrows():
            conn = sqlite3.connect(DB_PATH)
            dettagli = pd.read_sql_query(f"SELECT * FROM daily_matches WHERE id = {row['id']}", conn).iloc[0]
            conn.close()

            # Titolo espansore compatto
            with st.expander(f"📊 {dettagli['home_team']} vs {dettagli['away_team']}"):
                st.success(f"🎯 **PRONOSTICO: {dettagli['pronostico_principale']}**")
                st.info(f"💡 **Esatti:** {dettagli['risultati_esatti']}\n\n🛡️ **Asian:** {dettagli['asian_handicap']}")
                
                st.markdown("#### 📈 Probabilità Matematiche")
                # Accorpato in 2 colonne per leggibilità su smartphone
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Esito 1X2**")
                    st.write(f"1: {dettagli['pure_prob_1']}%")
                    st.write(f"X: {dettagli['pure_prob_x']}%")
                    st.write(f"2: {dettagli['pure_prob_2']}%")
                    st.markdown("**Goal / NoGoal**")
                    st.write(f"Goal: {dettagli['pure_prob_goal']}%")
                    st.write(f"NoG: {dettagli['pure_prob_nogoal']}%")
                    
                with col2:
                    st.markdown("**Over/Under**")
                    st.write(f"O 1.5: {dettagli['pure_prob_o15']}%")
                    st.write(f"O 2.5: {dettagli['pure_prob_o25']}%")
                    st.write(f"O 3.5: {dettagli['pure_prob_o35']}%")
                    st.markdown("**Multigoal**")
                    st.write(f"1-3: {dettagli['mg_1_3']}%")
                    st.write(f"2-4: {dettagli['mg_2_4']}%")
                    
                st.markdown("---")
                st.markdown("#### 📝 Dossier AI")
                st.markdown(dettagli['dossier'])
else:
    st.write("Nessuna analisi completata.")