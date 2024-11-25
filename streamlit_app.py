import pandas as pd
import streamlit as st
from pathlib import Path
import os

# Set the data directory relative to the script location
data_dir = Path(os.path.dirname(os.path.abspath(__file__))) / 'data'

# Ensure the data directory exists
if not data_dir.exists():
    st.error(f"Data directory '{data_dir}' does not exist. Please make sure the data folder is in the same directory as this script.")
    st.stop()

# Load all CSV files from the data folder
csv_files = list(data_dir.glob('*.csv'))
if not csv_files:
    st.error(f"No CSV files found in the data directory '{data_dir}'.")
    st.stop()

# Map league names to filenames
league_files = {file.stem.replace('-', ' ').title(): file for file in csv_files}

st.title('TT Stockholm')

# Sidebar for league selection
league_selected = st.sidebar.selectbox('Välj liga:', league_files.keys())

# Load data for selected league
df = pd.read_csv(league_files[league_selected])

# Sidebar for team selection
teams = df['Lag'].unique()
team_selected = st.sidebar.selectbox('Välj lag:', teams)

# Filter data for the selected team
team_data = df[df['Lag'] == team_selected]

# Display league and team data
st.header(f'Statistik för {team_selected} i {league_selected}')
st.write(team_data)

# Option to download the data as CSV
st.download_button("Ladda ner lagets statistik som CSV", team_data.to_csv(index=False), "team_stats.csv")

