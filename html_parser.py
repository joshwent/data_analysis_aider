from bs4 import BeautifulSoup
import pandas as pd
import datetime
import pytz

def parse_html_file(html_content):
    """Parse the HTML content and extract game data from the specific table."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the heading text that precedes our target table
    target_text = "Copy of Your Data\nCall of Duty: Black Ops 6\nMultiplayer Match Data (reverse chronological)"
    
    # Find all text nodes and locate our target
    for text in soup.stripped_strings:
        if target_text in text:
            # Find the next table after this text
            table = soup.find('table')
            if table:
                # Get headers from first row
                headers = []
                for th in table.find_all('th'):
                    headers.append(th.text.strip())
                
                # Get data rows
                data = []
                for row in table.find_all('tr')[1:]:  # Skip header row
                    cols = row.find_all('td')
                    if len(cols) > 0:
                        row_data = {}
                        for i, col in enumerate(cols):
                            row_data[headers[i]] = col.text.strip()
                        data.append(row_data)
                
                # Convert to DataFrame
                df = pd.DataFrame(data)
                
                # Convert numeric columns
                numeric_columns = ['Score', 'Kills', 'Deaths', 'Shots', 'Hits', 
                                 'Headshots', 'Damage Done', 'Damage Taken',
                                 'Longest Streak', 'Lifetime Kills', 'Lifetime Deaths',
                                 'Lifetime Time Played']
                
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Convert UTC timestamps
                if 'UTC Timestamp' in df.columns:
                    df['UTC Timestamp'] = pd.to_datetime(df['UTC Timestamp'])
                
                # Convert Skill to float
                if 'Skill' in df.columns:
                    df['Skill'] = df['Skill'].astype(float)
                
                return df
            
    raise ValueError("Could not find the target table in the HTML content")
