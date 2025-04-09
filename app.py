import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import io
import base64

# --- Konfiguration ---
APP_PASSWORD = st.secrets["app_password"] if "app_password" in st.secrets else "1234"  # Default

# --- Authentifizierung ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Login")
    pw = st.text_input("Passwort", type="password")
    if pw == APP_PASSWORD:
        st.session_state.logged_in = True
        st.experimental_rerun()
    else:
        st.stop()

# --- App ---
st.set_page_config(page_title="Liquiditätsplanung", layout="wide")
st.title("💧 Liquiditätsplanung")

st.markdown("""
Diese App kombiniert Ausgaben (HTML) und Einnahmen (Excel) und zeigt eine Liquiditätsvorschau inkl. Kontostandverlauf. 
Alle Beträge werden auf **CHF 0.05** gerundet und mit zwei Nachkommastellen dargestellt.
""")

# --- Inputfelder ---
html_input = st.text_area("📤 HTML-Ausgaben (copy-paste)", height=300)
uploaded_excels = st.file_uploader("📥 Excel-Einnahmen hochladen (.xlsx)", type=["xlsx"], accept_multiple_files=True)
start_balance = st.number_input("💰 Aktueller Kontostand", value=0.0, step=100.0)

# --- Funktionen ---
def parse_html_output(html_string):
    soup = BeautifulSoup(html_string, 'html.parser')
    rows = soup.find_all('tr')
    data = []

    for row in rows:
        cells = row.find_all('td')
        if not cells:
            continue

        date = cells[0].find('span', class_='print').text
        details = cells[2].find('span', class_='text').text
        amount = cells[3].text.replace("'", "").replace(",", ".")

        try:
            amount = abs(float(amount))
            amount = round(amount * 20) / 20 * -1
        except:
            continue

        data.append([date, details, amount, 'Outgoing'])

    df = pd.DataFrame(data, columns=['Date', 'Details', 'Amount', 'Direction'])
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df

def parse_excel_input(file):
    df = pd.read_excel(file)
    tomorrow = datetime.now() + timedelta(days=1)
    df['Zahlbar bis'] = pd.to_datetime(df['Zahlbar bis'], errors='coerce')
    df.loc[df['Zahlbar bis'] < pd.to_datetime('today'), 'Zahlbar bis'] = tomorrow
    df['Details'] = df['Kunde'] + ' ' + df['Kundennummer'].astype(str)
    df.rename(columns={'Zahlbar bis': 'Date', 'Brutto': 'Amount'}, inplace=True)
    df = df[['Date', 'Details', 'Amount']]
    df['Direction'] = 'Incoming'
    df['Amount'] = df['Amount'].apply(lambda x: round(abs(x) * 20) / 20)
    return df

# --- Datenverarbeitung ---
if html_input or uploaded_excels:
    dfs = []

    if html_input:
        dfs.append(parse_html_output(html_input))

    if uploaded_excels:
        for file in uploaded_excels:
            dfs.append(parse_excel_input(file))

    if dfs:
        df = pd.concat(dfs)
        df = df.sort_values('Date')
        df['Kontostand'] = df['Amount'].cumsum() + start_balance
        df['Amount'] = df['Amount'].apply(lambda x: f"{x:.2f}")
        df['Kontostand'] = df['Kontostand'].apply(lambda x: f"{x:.2f}")
        df['Date'] = df['Date'].dt.strftime('%d.%m.%Y')

        st.subheader("📊 Ergebnis")
        st.dataframe(df, use_container_width=True)

        # --- Plot ---
        st.subheader("📈 Kontostand Verlauf")
        df_plot = df.copy()
        df_plot['Kontostand'] = df_plot['Kontostand'].astype(float)
        st.line_chart(data=df_plot, x='Date', y='Kontostand')

        # --- Download ---
        def convert_df(df):
            return df.to_csv(index=False).encode('utf-8')

        csv = convert_df(df)
        st.download_button(
            label="⬇️ Als CSV herunterladen",
            data=csv,
            file_name='liquiditaetsplanung.csv',
            mime='text/csv',
        )
    else:
        st.info("Bitte Daten eingeben.")
else:
    st.info("Bitte Daten eingeben.")
