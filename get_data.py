import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
import time
from slugify import slugify  # Install this package with `pip install python-slugify`
import os

# Base URLs of the leagues
league_urls = [
    "https://www.profixio.com/fx/serieoppsett.php?t=SBTF_SERIE_AVD17203&k=LS17203&p=1",
    "https://www.profixio.com/fx/serieoppsett.php?t=SBTF_SERIE_AVD17205&k=LS17205&p=1"
]

def fetch_ranking(player, team):
    """Fetch ranking points for a player."""
    last_name, first_name = player.split(', ')
    url_template = "https://www.profixio.com/fx/ranking_sbtf/ranking_sbtf_list.php?searching=1&rid=&distr=47&club=&licencesubtype=&gender={gender}&age=&ln={last_name}&fn={first_name}"
    
    # Try fetching data with male gender first, then female if needed
    for gender in ['m', 'k']:
        url = url_template.format(gender=gender, last_name=last_name, first_name=first_name)
        response = requests.get(url)
        if response.status_code != 200:
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        player_row = None

        # Search for the player's row with matching team name
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 5 and cells[4].text.strip()[:5] in team:
                player_row = row
                break

        # Extract ranking points
        if player_row:
            hoyre_cells = player_row.find_all(class_="hoyre")
            if len(hoyre_cells) >= 2:
                return int(hoyre_cells[1].text.strip())

    return 0  # Return 0 if no data is found

def scrape_league(base_url):
    """Scrape data for a single league."""
    response = requests.get(base_url)
    if response.status_code != 200:
        return None, None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract the league name dynamically
    league_name_tag = soup.find('a', href=base_url.split('/')[-1])
    if not league_name_tag:
        return None, None
    league_name = league_name_tag.text.strip()

    # Collect match detail links
    details_links = soup.find_all('a', href=lambda x: x and 'serieoppsett_viskamper_rapport.php' in x)
    teams_data = defaultdict(lambda: defaultdict(lambda: {1: 0, 2: 0, 3: 0, 4: 0}))

    # Scrape match details
    for link in details_links:
        details_url = 'https://www.profixio.com/fx/' + link['href']
        scrape_match_details(details_url, teams_data)

    # Add Rankingpoäng and aggregate metrics
    data = []
    for team, players in teams_data.items():
        for player, positions in players.items():
            ranking_points = fetch_ranking(player, team)
            row = {
                'Lag': team,
                'Spelare': player,
                'Position 1': positions[1],
                'Position 2': positions[2],
                'Position 3': positions[3],
                'Position 4': positions[4],
                'Rankingpoäng': ranking_points
            }
            data.append(row)

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Calculate mean rankings
    df["Medelranking serie"] = round(df.loc[df["Rankingpoäng"] > 0, "Rankingpoäng"].mean(), 1)
    df["Medelranking lag"] = df.groupby("Lag")["Rankingpoäng"].transform(lambda x: round(x[x > 0].mean(), 1))

    return league_name, df

def scrape_match_details(details_url, teams_data):
    """Scrape individual match details page."""
    response = requests.get(details_url)
    if response.status_code != 200:
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    team_ths = soup.find_all('th', colspan="2")
    if len(team_ths) != 2:
        return

    team_a = team_ths[0].text.strip()
    team_b = team_ths[1].text.strip()

    player_divs = soup.find_all('div', id=lambda x: x and x.startswith('txtnavn_'))[:8]
    for div in player_divs:
        player_name = div.text.strip()
        div_id = div['id']
        team = div_id[-2]
        pos_num = int(div_id[-1])

        if team == 'A':
            teams_data[team_a][player_name][pos_num] += 1
        elif team == 'B':
            teams_data[team_b][player_name][pos_num] += 1


def save_to_csv(league_name, df):
    """Save the league data to a CSV file in the 'data' folder (relative to the script location)."""
    # Get the directory of the script being run
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define the 'data' folder path
    output_dir = os.path.join(script_dir, 'data')
    os.makedirs(output_dir, exist_ok=True)  # Create the folder if it doesn't exist

    # Generate the file path
    filename = slugify(league_name.lower()) + '.csv'
    filepath = os.path.join(output_dir, filename)

    # Save the DataFrame to CSV
    df.to_csv(filepath, index=False)
    print(f"Saved data for {league_name} to {filepath}")



if __name__ == "__main__":
    for base_url in league_urls:
        print(f"Scraping data for {base_url}...")
        league_name, league_df = scrape_league(base_url)
        print(league_name)
        print(league_df)
        if league_name and not league_df.empty:
            save_to_csv(league_name, league_df)
        time.sleep(5)  # Avoid overwhelming the server
