# skills/weather_info.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def handle(command):
    try:
        # Extract city name from command
        city = "Hyderabad"  # default
        if "in" in command:
            city = command.split("in")[-1].strip()
        
        # Try free weather API first (wttr.in)
        try:
            weather_url = f"http://wttr.in/{city}?format=%C+%t+%h+%w"
            response = requests.get(weather_url, timeout=10)
            
            if response.status_code == 200:
                weather_data = response.text.strip()
                # Clean up any problematic characters
                weather_data = weather_data.encode('ascii', 'ignore').decode('ascii')
                parts = weather_data.split()
                
                if len(parts) >= 3:
                    condition = parts[0]
                    temperature = parts[1]
                    humidity = parts[2]
                    wind = parts[3] if len(parts) > 3 else "N/A"
                    
                    return (
                        f"Weather in {city}:\n"
                        f"- Condition: {condition}\n"
                        f"- Temperature: {temperature}\n"
                        f"- Humidity: {humidity}\n"
                        f"- Wind: {wind}\n"
                        f"(Data from wttr.in - free weather service)"
                    )
        except Exception as e:
            print(f"Free weather API failed: {e}")
        
        # Fallback to OpenWeatherMap if API key is available
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if api_key and api_key != "your_openweather_api_key_here":
            try:
                # Convert city name to coordinates
                geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={api_key}"
                geo_res = requests.get(geo_url).json()

                if not geo_res:
                    return f"Couldn't find location: {city}"

                lat = geo_res[0]["lat"]
                lon = geo_res[0]["lon"]

                # Fetch weather using One Call API 3.0
                weather_url = (
                    f"https://api.openweathermap.org/data/3.0/onecall?"
                    f"lat={lat}&lon={lon}&exclude=minutely,alerts&units=metric&appid={api_key}"
                )

                weather_res = requests.get(weather_url).json()
                current = weather_res.get("current", {})
                daily = weather_res.get("daily", [{}])[0]

                temp = current.get("temp", "N/A")
                desc = current.get("weather", [{}])[0].get("description", "N/A")
                feels_like = current.get("feels_like", "N/A")
                humidity = current.get("humidity", "N/A")

                return (
                    f"Weather in {city}:\n"
                    f"- Description: {desc}\n"
                    f"- Temperature: {temp}°C (feels like {feels_like}°C)\n"
                    f"- Humidity: {humidity}%\n"
                    f"- High: {daily.get('temp', {}).get('max', 'N/A')}°C | "
                    f"Low: {daily.get('temp', {}).get('min', 'N/A')}°C"
                )
            except Exception as e:
                return f"Weather API error: {str(e)}"
        
        # Fallback 2: Open-Meteo (no key) via geocoding + current weather
        try:
            import urllib.parse
            q = urllib.parse.quote(city)
            geo_res = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=1", timeout=10).json()
            if geo_res and geo_res.get('results'):
                lat = geo_res['results'][0]['latitude']
                lon = geo_res['results'][0]['longitude']
                meteo = requests.get(
                    f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m&hourly=temperature_2m&timezone=auto",
                    timeout=10
                ).json()
                cur = meteo.get('current', {})
                temp = cur.get('temperature_2m')
                rh = cur.get('relative_humidity_2m')
                wind = cur.get('wind_speed_10m')
                return (
                    f"Weather in {city}:\n"
                    f"- Temperature: {temp}°C\n"
                    f"- Humidity: {rh}%\n"
                    f"- Wind: {wind} m/s\n"
                    f"(Data from Open-Meteo)"
                )
        except Exception:
            pass

        # If all sources fail, provide helpful message
        return (
            f"Weather information for {city} is not available right now.\n"
            f"You can:\n"
            f"1. Set OPENWEATHER_API_KEY in your .env file\n"
            f"2. Visit https://wttr.in/{city} in your browser\n"
            f"3. Try again later"
        )

    except Exception as e:
        return f"Error fetching weather: {str(e)}"
