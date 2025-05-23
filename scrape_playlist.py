import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import pytz
import argparse

def scrape_kink_playlist(cache_dir=None, max_age=0):
    # Set up timezone for Amsterdam/CET
    cet_timezone = pytz.timezone('Europe/Amsterdam')
    current_time_utc = datetime.utcnow()
    current_time_cet = current_time_utc.replace(tzinfo=pytz.UTC).astimezone(cet_timezone)
    
    # Debug timezone information
    print(f"Current time in CET: {current_time_cet.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
    
    # Format the date for the URL to ensure we get the correct day's playlist
    date_str = current_time_cet.strftime("%Y-%m-%d")
    
    # Use the date in the URL to get the specific day's playlist
    url = f"https://onlineradiobox.com/nl/kink/playlist/{date_str}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://onlineradiobox.com/nl/kink/",
    }
    
    try:
        print(f"Fetching data from {url}...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        print(f"Response status code: {response.status_code}")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: Save HTML to file for inspection
        with open("debug_response.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("Saved response HTML to debug_response.html")
        
        # Updated selector to match the actual HTML structure
        playlist_rows = soup.select('table.tablelist-schedule tr')
        print(f"Found {len(playlist_rows)} playlist rows")
        
        playlist_data = []
        
        for row in playlist_rows:
            # Skip rows without proper structure
            time_element = row.select_one('.tablelist-schedule__time .time--schedule')
            track_element = row.select_one('.track_history_item a')
            
            # If no link is found, try to get the text directly from the track_history_item
            if time_element and not track_element:
                track_element_div = row.select_one('.track_history_item')
                if track_element_div:
                    track_text = track_element_div.text.strip()
                    time_text = time_element.text.strip()
                    
                    # Split artist and title (assuming format "Artist - Title")
                    if " - " in track_text:
                        artist, title = track_text.split(" - ", 1)
                    else:
                        artist = "Unknown"
                        title = track_text
                    
                    print(f"Found song (no link): {artist} - {title} at {time_text}")
                    
                    # Parse the time_text (e.g., "14:30") and create a datetime object with the correct date and timezone
                    try:
                        hour, minute = map(int, time_text.split(':'))
                        song_datetime = current_time_cet.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        
                        # If the song time is in the future (more than 1 hour ahead), it's probably from yesterday
                        if (song_datetime - current_time_cet).total_seconds() > 3600:
                            song_datetime = song_datetime.replace(day=song_datetime.day-1)
                            
                        timestamp = song_datetime.isoformat()
                    except ValueError:
                        # Fallback to current time if time parsing fails
                        timestamp = current_time_cet.isoformat()
                    
                    playlist_data.append({
                        "time": time_text,
                        "artist": artist,
                        "title": title,
                        "timestamp": timestamp
                    })
            elif time_element and track_element:
                time_text = time_element.text.strip()
                track_text = track_element.text.strip()
                
                # Split artist and title (assuming format "Artist - Title")
                if " - " in track_text:
                    artist, title = track_text.split(" - ", 1)
                else:
                    artist = "Unknown"
                    title = track_text
                
                print(f"Found song: {artist} - {title} at {time_text}")
                
                # Parse the time_text (e.g., "14:30") and create a datetime object with the correct date and timezone
                try:
                    hour, minute = map(int, time_text.split(':'))
                    song_datetime = current_time_cet.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # If the song time is in the future (more than 1 hour ahead), it's probably from yesterday
                    if (song_datetime - current_time_cet).total_seconds() > 3600:
                        song_datetime = song_datetime.replace(day=song_datetime.day-1)
                        
                    timestamp = song_datetime.isoformat()
                except ValueError:
                    # Fallback to current time if time parsing fails
                    timestamp = current_time_cet.isoformat()
                
                playlist_data.append({
                    "time": time_text,
                    "artist": artist,
                    "title": title,
                    "timestamp": timestamp
                })
            else:
                if row.find('td'):  # Only report missing elements for actual data rows
                    print("Missing elements in playlist row:", 
                          "time_element" if not time_element else "",
                          "track_element" if not track_element else "")
        
        return playlist_data
    
    except Exception as e:
        print(f"Error scraping playlist: {e}")
        import traceback
        traceback.print_exc()
        return []

def save_playlist(playlist_data):
    # Create docs directory if it doesn't exist
    os.makedirs("docs", exist_ok=True)
    
    # Path to the playlist JSON file
    playlist_file = "docs/playlist.json"
    
    # Instead of loading existing data, just use the new data
    print(f"Saving {len(playlist_data)} songs to {playlist_file}")
    
    # Save the updated playlist (completely replacing the old one)
    with open(playlist_file, 'w', encoding='utf-8') as f:
        json.dump(playlist_data, f, ensure_ascii=False, indent=2)
    
    print(f"Playlist replaced with {len(playlist_data)} new songs")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape Kink Radio playlist')
    parser.add_argument('--cache-dir', help='Directory to store cache files')
    parser.add_argument('--max-age', type=int, default=0, help='Maximum age of cache in seconds')
    args = parser.parse_args()
    
    print("Starting Kink Radio playlist scraper...")
    playlist_data = scrape_kink_playlist(args.cache_dir, args.max_age)
    if playlist_data:
        print(f"Successfully scraped {len(playlist_data)} songs")
        save_playlist(playlist_data)
    else:
        print("No playlist data was scraped")