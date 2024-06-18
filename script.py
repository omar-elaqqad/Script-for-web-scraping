from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import re

def scrape_euro_fixtures():
    # Setup Selenium
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    
    # Navigate to the Euro fixtures page
    driver.get("https://www.flashscore.com/football/europe/euro/fixtures/")
    
    # Wait for the page to fully load
    try:
        element_present = EC.presence_of_element_located((By.CSS_SELECTOR, '.sportName.soccer'))
        WebDriverWait(driver, timeout=100).until(element_present)
    except Exception as e:
        print("Timed out waiting for page to load",e)
        driver.quit()
        return None
    
    # Get the page source
    html_content = driver.page_source
    
    # Close the browser
    driver.quit()
    
    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    
# Extract fixture details
    fixtures_data = []
    rows = soup.find_all('div', {'class': 'event__match'})
    for row in rows:
        # Extract the href attribute for the match detail link
        match_link = row.find('a', class_='eventRowLink')['href']
        
        # Extract the names of the participating countries
        home_country = row.find('div', class_='_participant_x6lwl_4 event__homeParticipant').find('span', class_='_simpleText_zfz11_4 _webTypeSimpleText01_zfz11_8 _name_x6lwl_17').text.strip()
        away_country = row.find('div', class_='_participant_x6lwl_4 event__awayParticipant').find('span', class_='_simpleText_zfz11_4 _webTypeSimpleText01_zfz11_8 _name_x6lwl_17').text.strip()
        
        fixtures_data.append({
            'Match Link': match_link.replace("match-summary","odds-comparison/correct-score/full-time"),
            'Home Country': home_country,
            'Away Country': away_country
        })
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(fixtures_data)
    
    return df

def scrape_odds_data(match_links):
    # Setup Selenium
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    
    odds_data = []
    
    for k, match_link in list(match_links.iterrows())[:8]:
        # Navigate to the odds comparison page for each match
        driver.get(match_link['Match Link'])
        homeCountry = match_link['Home Country']
        awayCountry = match_link['Away Country']
        
        # Wait for the page to fully load
        try:
            element_present = EC.presence_of_element_located((By.CSS_SELECTOR, '.oddsTab__tableWrapper'))
            WebDriverWait(driver, timeout=30).until(element_present)
        except Exception as e:
            print(f"Timed out waiting for page to load for {match_link['Match Link']}",e)
            continue
        
        # Get the page source
        html_content = driver.page_source
        
        # Parse the HTML content
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Ensure all rows are selected
        table_rows = soup.select('.ui-table__row')
        
        # Debugging: Print number of rows found
        print(f"Found {len(table_rows)} rows.")
        
        for index, row in enumerate(table_rows, start=1):
            # Extracting score, bookmaker, and odd value
            score_span = row.find('span', class_='oddsCell__noOddsCell')
            bookmaker_a = row.find('a', class_='prematchLink')
            odd_a = row.find('a', class_='oddsCell__odd')
            
            # Handling cases where elements might not be found
            score = "N/A" if not score_span else score_span.text.strip()
            bookmaker = "N/A" if not bookmaker_a else bookmaker_a['title']
            odd_value = "N/A" if not odd_a else odd_a.text.strip()
            
            # Adding additional debugging information
            # print(f"Processing row {index}: Score={score}, Bookmaker={bookmaker}, Odd Value={odd_value}")
            

            odds_data.append({'Home Country': homeCountry,'Away Country': awayCountry, 'Row Number': index, 'Score': score, 'Bookmaker': bookmaker, 'Odd Value': odd_value})

    # Close the browser
    driver.quit()
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(odds_data)
    
    return df
# Function to clean the 'Odd Value' column
def clean_odd_value(value):
    # This regex pattern attempts to extract a number from the string,
    # assuming the format might be something like "X.Y"
    match = re.match(r"(\d+\.\d+)", value)
    return float(match.group(1)) if match else None
def calculate_points(first, second):
    """
    Calculate the expected points based on the scoring rules.
    """
    a, b = map(int, first.split(':'))
    x, y = map(int, second.split(':'))
    ab = a - b
    xy = x - y
    if a == x and ab == xy:
        return 3
    elif ab == xy:
        return 2
    elif ab*xy > 0 or (ab ==0 and xy == 0):
        return 1
    else:
        return 0
def calculate_expected_points(score, all_scores):
    ab = sum([calculate_points(score, record["Score"])*record["Odds(%)"]/100 for record in all_scores])
    xy = sum([record["Odds(%)"]/100 for record in all_scores])
    return ab/xy
def take_average(df):
    df['Odd Value'] = df['Odd Value'].apply(clean_odd_value)
    #print(df)
    # Group by Home Country, Away Country, and Score, then calculate the mean of Odd Value
    grouped_averages = df.groupby(['Home Country', 'Away Country', 'Score'], as_index=False).mean()
    # Calculate Oddsand convert to percentage directly on the grouped object
    grouped_averages['Odds(%)'] = 1/grouped_averages['Odd Value'] * 100
    #print(grouped_averages)
    # Group by home country and away country
    grouped_by_match = grouped_averages.groupby(['Home Country', 'Away Country'])
    
    # Iterate through each group to filter out scores with Odds< 1%
    for name, group in grouped_by_match:
        # Ensure we check for the existence of the 0th element
        if len(group) > 0:
            # Filter out scores with Odds< 1%
            filtered_scores = group[group['Odds(%)'] >= 1]
            # Sort scores in descending order
            sorted_scores = filtered_scores.sort_values(by='Odds(%)', ascending=False)
            
            # Safely access the first elements for printing
            home_country = group.iloc[0]['Home Country']
            away_country = group.iloc[0]['Away Country']
            print(f"Match: {home_country} vs {away_country}")
            score_odds = sorted_scores[['Score', 'Odds(%)']]
            probability_by_score = score_odds[score_odds['Odds(%)']>=5].to_dict('records')
            score_odds['Expected Points'] = score_odds.apply(lambda row: calculate_expected_points(row['Score'], probability_by_score), axis=1)

            print(score_odds[score_odds['Odds(%)']>=5])
            print("\n")  # Add a newline for better readability between matches

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
fixtures_df = scrape_euro_fixtures()
if fixtures_df is not None:
    print(fixtures_df)
    odds_df = scrape_odds_data(fixtures_df)

    if odds_df is not None:
        take_average(odds_df)
