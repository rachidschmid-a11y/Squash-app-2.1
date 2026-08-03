import streamlit as st
import pandas as pd
from datetime import date
import config as cfg
import database as db
import calculations as calc
import visualizations as vis
import export_utils

@st.dialog("Karte wirklich löschen?")
def confirm_delete_karte_dialog(karte_id):
    st.warning(
        "⚠️ Diese Aktion kann nicht rückgängig gemacht werden. "
        "Das aktuelle Kartenguthaben geht dabei verloren."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, endgültig löschen", type="primary", width="stretch"):
            if db.delete_karte(karte_id):
                st.success("Die aktive Karte wurde erfolgreich gelöscht!")
            st.rerun()
    with col2:
        if st.button("Abbrechen", width="stretch"):
            st.rerun()

@st.dialog("Eintrag wirklich löschen?")
def confirm_delete_spiel_dialog(eintrag, karte):
    st.warning(
        f"Eintrag ID {eintrag['id']} ({eintrag.get('kosten', 0):.2f} €) wird gelöscht "
        f"und dem Kartenguthaben gutgeschrieben."
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ja, löschen", type="primary", width="stretch"):
            if karte:
                alter_guthaben = karte["guthaben"]
                neues_guthaben = alter_guthaben + eintrag.get("kosten", 0)
                db.update_karte_guthaben(karte["id"], alter_guthaben, neues_guthaben)
            if db.delete_spiel_by_id(eintrag["id"]):
                st.success(f"Eintrag {eintrag['id']} erfolgreich gelöscht!")
            st.rerun()
    with col2:
        if st.button("Abbrechen", width="stretch"):
            st.rerun()

def render_abrechnung_page():
    st.title("🏸 Squash Abrechnung & Guthaben")

    with st.expander("➕ Neue Karte starten"):
        st.markdown("#### 📋 Letzte Abrechnung (Historie)")
        letzte_schulden, alter_zahler = db.get_letzte_abrechnung()

        if letzte_schulden:
            st.caption(f"Zur Erinnerung: Das waren die Ausgleichszahlungen für die letzte Karte von **{alter_zahler}**:")
            for eintrag in letzte_schulden:
                if eintrag['spieler'] != alter_zahler:
                    st.write(f"• **{eintrag['spieler']}** → **{eintrag['betrag']:.2f} €** an {alter_zahler}")
                else:
                    st.write(f"• *{eintrag['spieler']} (Zahler der Karte)*")
        else:
            st.info("Keine historischen Abrechnungsdaten gefunden.")

        st.divider()

        st.markdown("#### Neue Karte aktivieren")
        bezahlt_von = st.selectbox("Wer hat die Karte bezahlt?", cfg.SPIELER, key="card_payer")

        if st.button("Karte aktivieren"):
            letzte_karte = db.get_letzte_inaktive_karte()
            last_guthaben = letzte_karte["guthaben"] if (letzte_karte and letzte_karte.get("guthaben") is not None) else 0

            start_guthaben = 250.0 + (last_guthaben if last_guthaben < 0 else 0)

            if db.insert_karte({
                "guthaben": start_guthaben,
                "aktiv": True,
                "bezahlt_von": bezahlt_von
            }):
                st.success(f"Neue Karte gestartet! Bezahlt von: {bezahlt_von}")
                st.rerun()

    st.divider()
    st.subheader("Neues Spiel (Session) eintragen")
    col1, col2 = st.columns(2)
    with col1:
        eingetragen_von = st.selectbox("Eingetragen von", cfg.SPIELER, key="fin_input_by")
    with col2:
        gespielt_am = st.date_input("Gespielt am", date.today(), key="fin_date")

    st.write("**Mitspieler auswählen:**")
    cols = st.columns(len(cfg.SPIELER))
    auswahl = [p for i, p in enumerate(cfg.SPIELER) if cols[i].checkbox(p, key=f"check_{p}")]

    einheiten = st.number_input("Einheiten (45 Minuten)", min_value=1, max_value=20, value=1, key="fin_units")

    if st.button("Spiel-Session speichern"):
        if len(auswahl) == 0:
            st.warning("Bitte Spieler auswählen")
        else:
            status, msg = calc.speichern_logik(auswahl, einheiten, eingetragen_von, gespielt_am)
            if status == "success":
                st.success(msg)
            elif status == "warning":
                st.info(msg)
            else:
                st.error(msg)
            if status != "error":
                st.rerun()

    st.divider()
    st.subheader("Aktueller Stand")
    karte = db.get_karte()
    if karte:
        st.metric("Kartenguthaben", f"{karte['guthaben']:.2f} €")
        st.caption(f"Diese Karte wurde bezahlt von: **{karte.get('bezahlt_von', 'Unbekannt')}**")

        # Funktion zur nachträglichen Korrektur des Karten-Zahlers bei Tippfehlern
        with st.expander("✏️ Falschen Zahler eingetragen? Name korrigieren"):
            aktueller_zahler = karte.get("bezahlt_von")
            default_index = cfg.SPIELER.index(aktueller_zahler) if aktueller_zahler in cfg.SPIELER else 0

            neuer_zahler = st.selectbox(
                "Wer hat die Karte wirklich bezahlt?",
                cfg.SPIELER,
                index=default_index,
                key="correct_card_payer"
            )

            if st.button("Zahler aktualisieren", key="btn_correct_payer"):
                if neuer_zahler == aktueller_zahler:
                    st.info("Dieser Spieler ist bereits als Zahler eingetragen.")
                else:
                    if db.update_karte_zahler(karte["id"], neuer_zahler):
                        st.success(f"Zahler erfolgreich auf **{neuer_zahler}** geändert!")
                        st.rerun()
    else:
        st.warning("Keine aktive Karte vorhanden. Bitte neue Karte starten.")

    spiele = db.get_spiele()
    if spiele:
        df_display = calc.format_dataframe(pd.DataFrame(spiele))
        st.dataframe(df_display, width="stretch")
        st.download_button(
            "📥 Spiele-Übersicht als CSV exportieren",
            data=export_utils.to_csv_bytes(df_display),
            file_name=f"spiele_kosten_{date.today().isoformat()}.csv",
            mime="text/csv",
            key="dl_spiele_kosten",
        )
    else:
        st.info("Noch keine Spiele auf der aktuellen Karte vorhanden")

    st.divider()
    with st.expander("🗑️ Fehlerhaften Eintrag oder Karte löschen"):
        st.markdown("#### 🏸 Spiel-Session löschen")
        if spiele:
            df_raw = pd.DataFrame(spiele)
            optionen = {row["id"]: f"ID {row['id']} | {pd.to_datetime(row['gespielt_am']).strftime('%d.%m.%Y')} | {row['spieler']} | {row['kosten']:.2f} €" for _, row in df_raw.iterrows()}
            auswahl_id = st.selectbox("Welcher Eintrag soll gelöscht werden?", list(optionen.keys()), format_func=lambda x: optionen[x], key="del_fin_id")

            if st.button("Eintrag löschen & Guthaben erstatten"):
                eintrag = next((s for s in spiele if s["id"] == auswahl_id), None)
                if eintrag:
                    confirm_delete_spiel_dialog(eintrag, karte)
        else:
            st.info("Keine aktuellen Spiele vorhanden, die gelöscht werden könnten.")

        st.divider()
        st.markdown("#### ⚠️ Aktive Karte stornieren")
        if karte:
            st.warning("Achtung: Das Löschen der aktiven Karte setzt das aktuelle Kartenguthaben zurück. Offene Sessions bleiben als 'nicht abgerechnet' bestehen und zählen für die nächste aktivierte Karte.")
            if st.button("🔴 Aktive Karte unwiderruflich löschen", key="btn_delete_active_card"):
                confirm_delete_karte_dialog(karte["id"])
        else:
            st.info("Keine aktive Karte vorhanden, die gelöscht werden könnte.")

    st.divider()
    st.subheader("Kostenstatistik")
    if spiele:
        df_stats = pd.DataFrame(spiele).groupby("spieler")["kosten"].sum().reset_index()
        c1, c2 = st.columns(2)
        with c1:
            vis.plot_costs_bar(df_stats)
        with c2:
            vis.plot_costs_pie(df_stats)
        st.download_button(
            "📥 Kostenstatistik als CSV exportieren",
            data=export_utils.to_csv_bytes(df_stats),
            file_name=f"kostenstatistik_{date.today().isoformat()}.csv",
            mime="text/csv",
            key="dl_kostenstatistik",
        )
    else:
        st.info("Noch keine Daten für eine Visualisierung vorhanden.")

def render_statistics_page():
    st.title("📊 Sportliche Statistiken")

    df = calc.build_dataframe()
    if df.empty:
        st.info("Noch keine Daten vorhanden")
        return

    spieler = st.selectbox("Spieler auswählen", cfg.SPIELER, key="stats_player_select")

    stats = calc.player_stats(df, spieler)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Siege", stats["siege"])
    col2.metric("Niederlagen", stats["niederlagen"])
    col3.metric("Spiele", stats["gesamt"])
    col4.metric("Quote %", stats["quote"])

    st.divider()
    vis.plot_match_scatter(df, spieler)

    st.subheader("🧮 Gesamt-Matrix")
    matrix = calc.head_to_head_matrix(df)
    st.dataframe(matrix, width="stretch")
    st.download_button(
        "📥 Matrix als CSV exportieren",
        data=export_utils.to_csv_bytes(matrix, index=True),
        file_name=f"head_to_head_matrix_{date.today().isoformat()}.csv",
        mime="text/csv",
        key="dl_matrix",
    )
