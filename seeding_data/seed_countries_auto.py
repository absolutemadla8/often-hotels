#!/usr/bin/env python3

import asyncio
import json
import os
import sys
import pycountry
import requests
from datetime import datetime
from typing import Dict, List, Optional

try:
    from babel.core import Locale
    from babel.numbers import get_currency_name
    BABEL_AVAILABLE = True
except ImportError:
    BABEL_AVAILABLE = False
    print("⚠️ Babel library not available - currency names may be incomplete")

try:
    import pycountry_convert as pc
    PYCOUNTRY_CONVERT_AVAILABLE = True
except ImportError:
    PYCOUNTRY_CONVERT_AVAILABLE = False
    print("⚠️ pycountry-convert not available - continent data may be incomplete")

try:
    from countryinfo import CountryInfo
    COUNTRYINFO_AVAILABLE = True
except ImportError:
    COUNTRYINFO_AVAILABLE = False
    print("⚠️ countryinfo not available - additional data may be incomplete")

try:
    from countries_data import countries
    COUNTRIES_DATA_AVAILABLE = True
except ImportError:
    COUNTRIES_DATA_AVAILABLE = False
    print("⚠️ countries-data not available - additional data may be incomplete")

# Comprehensive sub-region mapping based on UN M49 standard
SUBREGION_MAPPING = {
    # Europe
    'AD': 'Southern Europe', 'AL': 'Southern Europe', 'AT': 'Western Europe', 'BA': 'Southern Europe',
    'BE': 'Western Europe', 'BG': 'Eastern Europe', 'BY': 'Eastern Europe', 'CH': 'Western Europe',
    'CZ': 'Eastern Europe', 'DE': 'Western Europe', 'DK': 'Northern Europe', 'EE': 'Northern Europe',
    'ES': 'Southern Europe', 'FI': 'Northern Europe', 'FO': 'Northern Europe', 'FR': 'Western Europe',
    'GB': 'Northern Europe', 'GG': 'Northern Europe', 'GI': 'Southern Europe', 'GR': 'Southern Europe',
    'HR': 'Southern Europe', 'HU': 'Eastern Europe', 'IE': 'Northern Europe', 'IM': 'Northern Europe',
    'IS': 'Northern Europe', 'IT': 'Southern Europe', 'JE': 'Northern Europe', 'LI': 'Western Europe',
    'LT': 'Northern Europe', 'LU': 'Western Europe', 'LV': 'Northern Europe', 'MC': 'Western Europe',
    'MD': 'Eastern Europe', 'ME': 'Southern Europe', 'MK': 'Southern Europe', 'MT': 'Southern Europe',
    'NL': 'Western Europe', 'NO': 'Northern Europe', 'PL': 'Eastern Europe', 'PT': 'Southern Europe',
    'RO': 'Eastern Europe', 'RS': 'Southern Europe', 'RU': 'Eastern Europe', 'SE': 'Northern Europe',
    'SI': 'Southern Europe', 'SJ': 'Northern Europe', 'SK': 'Eastern Europe', 'SM': 'Southern Europe',
    'UA': 'Eastern Europe', 'VA': 'Southern Europe', 'XK': 'Southern Europe',
    
    # Asia
    'AE': 'Western Asia', 'AF': 'Southern Asia', 'AM': 'Western Asia', 'AZ': 'Western Asia',
    'BD': 'Southern Asia', 'BH': 'Western Asia', 'BN': 'South-Eastern Asia', 'BT': 'Southern Asia',
    'CN': 'Eastern Asia', 'CY': 'Western Asia', 'GE': 'Western Asia', 'HK': 'Eastern Asia',
    'ID': 'South-Eastern Asia', 'IL': 'Western Asia', 'IN': 'Southern Asia', 'IQ': 'Western Asia',
    'IR': 'Southern Asia', 'JO': 'Western Asia', 'JP': 'Eastern Asia', 'KG': 'Central Asia',
    'KH': 'South-Eastern Asia', 'KP': 'Eastern Asia', 'KR': 'Eastern Asia', 'KW': 'Western Asia',
    'KZ': 'Central Asia', 'LA': 'South-Eastern Asia', 'LB': 'Western Asia', 'LK': 'Southern Asia',
    'MN': 'Eastern Asia', 'MO': 'Eastern Asia', 'MV': 'Southern Asia', 'MY': 'South-Eastern Asia',
    'NP': 'Southern Asia', 'OM': 'Western Asia', 'PH': 'South-Eastern Asia', 'PK': 'Southern Asia',
    'PS': 'Western Asia', 'QA': 'Western Asia', 'SA': 'Western Asia', 'SG': 'South-Eastern Asia',
    'SY': 'Western Asia', 'TH': 'South-Eastern Asia', 'TJ': 'Central Asia', 'TL': 'South-Eastern Asia',
    'TM': 'Central Asia', 'TR': 'Western Asia', 'TW': 'Eastern Asia', 'UZ': 'Central Asia',
    'VN': 'South-Eastern Asia', 'YE': 'Western Asia',
    
    # Africa
    'AO': 'Middle Africa', 'BF': 'Western Africa', 'BI': 'Eastern Africa', 'BJ': 'Western Africa',
    'BW': 'Southern Africa', 'CD': 'Middle Africa', 'CF': 'Middle Africa', 'CG': 'Middle Africa',
    'CI': 'Western Africa', 'CM': 'Middle Africa', 'CV': 'Western Africa', 'DJ': 'Eastern Africa',
    'DZ': 'Northern Africa', 'EG': 'Northern Africa', 'EH': 'Northern Africa', 'ER': 'Eastern Africa',
    'ET': 'Eastern Africa', 'GA': 'Middle Africa', 'GH': 'Western Africa', 'GM': 'Western Africa',
    'GN': 'Western Africa', 'GQ': 'Middle Africa', 'GW': 'Western Africa', 'KE': 'Eastern Africa',
    'KM': 'Eastern Africa', 'LR': 'Western Africa', 'LS': 'Southern Africa', 'LY': 'Northern Africa',
    'MA': 'Northern Africa', 'MG': 'Eastern Africa', 'ML': 'Western Africa', 'MR': 'Western Africa',
    'MU': 'Eastern Africa', 'MW': 'Eastern Africa', 'MZ': 'Eastern Africa', 'NA': 'Southern Africa',
    'NE': 'Western Africa', 'NG': 'Western Africa', 'RE': 'Eastern Africa', 'RW': 'Eastern Africa',
    'SC': 'Eastern Africa', 'SD': 'Northern Africa', 'SL': 'Western Africa', 'SN': 'Western Africa',
    'SO': 'Eastern Africa', 'SS': 'Eastern Africa', 'ST': 'Middle Africa', 'SZ': 'Southern Africa',
    'TD': 'Middle Africa', 'TG': 'Western Africa', 'TN': 'Northern Africa', 'TZ': 'Eastern Africa',
    'UG': 'Eastern Africa', 'YT': 'Eastern Africa', 'ZA': 'Southern Africa', 'ZM': 'Eastern Africa',
    'ZW': 'Eastern Africa',
    
    # Americas
    'AG': 'Caribbean', 'AI': 'Caribbean', 'AR': 'South America', 'AW': 'Caribbean',
    'BB': 'Caribbean', 'BL': 'Caribbean', 'BM': 'Northern America', 'BO': 'South America',
    'BQ': 'Caribbean', 'BR': 'South America', 'BS': 'Caribbean', 'BZ': 'Central America',
    'CA': 'Northern America', 'CL': 'South America', 'CO': 'South America', 'CR': 'Central America',
    'CU': 'Caribbean', 'CW': 'Caribbean', 'DM': 'Caribbean', 'DO': 'Caribbean',
    'EC': 'South America', 'FK': 'South America', 'GD': 'Caribbean', 'GF': 'South America',
    'GL': 'Northern America', 'GP': 'Caribbean', 'GT': 'Central America', 'GY': 'South America',
    'HN': 'Central America', 'HT': 'Caribbean', 'JM': 'Caribbean', 'KN': 'Caribbean',
    'KY': 'Caribbean', 'LC': 'Caribbean', 'MF': 'Caribbean', 'MQ': 'Caribbean',
    'MS': 'Caribbean', 'MX': 'Central America', 'NI': 'Central America', 'PA': 'Central America',
    'PE': 'South America', 'PM': 'Northern America', 'PR': 'Caribbean', 'PY': 'South America',
    'SR': 'South America', 'SV': 'Central America', 'SX': 'Caribbean', 'TC': 'Caribbean',
    'TT': 'Caribbean', 'US': 'Northern America', 'UY': 'South America', 'VC': 'Caribbean',
    'VE': 'South America', 'VG': 'Caribbean', 'VI': 'Caribbean',
    
    # Oceania
    'AS': 'Polynesia', 'AU': 'Australia and New Zealand', 'CC': 'Australia and New Zealand',
    'CK': 'Polynesia', 'CX': 'Australia and New Zealand', 'FJ': 'Melanesia', 'FM': 'Micronesia',
    'GU': 'Micronesia', 'HM': 'Australia and New Zealand', 'KI': 'Micronesia', 'MH': 'Micronesia',
    'MP': 'Micronesia', 'NC': 'Melanesia', 'NF': 'Australia and New Zealand', 'NR': 'Micronesia',
    'NU': 'Polynesia', 'NZ': 'Australia and New Zealand', 'PF': 'Polynesia', 'PG': 'Melanesia',
    'PN': 'Polynesia', 'PW': 'Micronesia', 'SB': 'Melanesia', 'TK': 'Polynesia', 'TO': 'Polynesia',
    'TV': 'Polynesia', 'UM': 'Micronesia', 'VU': 'Melanesia', 'WF': 'Polynesia', 'WS': 'Polynesia'
}

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from tortoise import Tortoise
from core.config import settings
from models.models import Country

def fetch_countries_from_api() -> List[Dict]:
    """Fetch comprehensive country data from REST Countries API"""
    print("📡 Fetching country data from REST Countries API...")
    
    try:
        # Try without fields parameter first (get all data)
        response = requests.get(
            "https://restcountries.com/v3.1/all",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        print(f"✅ Successfully fetched {len(data)} countries with full data")
        return data
        
    except requests.RequestException as e:
        print(f"❌ API request failed: {e}")
        
        # Try alternative API
        try:
            print("🔄 Trying alternative REST Countries API...")
            response = requests.get(
                "https://restcountries.com/v2/all",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            print(f"✅ Successfully fetched {len(data)} countries from v2 API")
            return data
            
        except requests.RequestException as e2:
            print(f"❌ Alternative API also failed: {e2}")
            print("📚 Falling back to pycountry library...")
            return []

def get_popular_destinations_for_country(country_code: str, country_name: str) -> List[str]:
    """Get popular destinations for a country"""
    
    # Popular destinations mapping (you can expand this)
    popular_destinations = {
        "US": ["New York", "Los Angeles", "Chicago", "Miami", "Las Vegas", "San Francisco", "Orlando", "Washington DC"],
        "IN": ["Mumbai", "Delhi", "Bangalore", "Goa", "Jaipur", "Kerala", "Agra", "Chennai"],
        "GB": ["London", "Edinburgh", "Manchester", "Liverpool", "Bath", "Oxford", "Cambridge", "Brighton"],
        "FR": ["Paris", "Nice", "Marseille", "Lyon", "Cannes", "Bordeaux", "Toulouse", "Strasbourg"],
        "DE": ["Berlin", "Munich", "Hamburg", "Frankfurt", "Cologne", "Dresden", "Heidelberg", "Nuremberg"],
        "JP": ["Tokyo", "Osaka", "Kyoto", "Hiroshima", "Fukuoka", "Sapporo", "Yokohama", "Nara"],
        "CN": ["Beijing", "Shanghai", "Guangzhou", "Shenzhen", "Xi'an", "Chengdu", "Hangzhou", "Suzhou"],
        "AU": ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast", "Cairns", "Darwin"],
        "CA": ["Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa", "Quebec City", "Winnipeg", "Halifax"],
        "IT": ["Rome", "Milan", "Venice", "Florence", "Naples", "Turin", "Bologna", "Palermo"],
        "ES": ["Madrid", "Barcelona", "Seville", "Valencia", "Bilbao", "Granada", "Palma", "San Sebastian"],
        "BR": ["Rio de Janeiro", "São Paulo", "Salvador", "Brasília", "Recife", "Fortaleza", "Manaus", "Porto Alegre"],
        "RU": ["Moscow", "St. Petersburg", "Novosibirsk", "Yekaterinburg", "Kazan", "Nizhny Novgorod", "Chelyabinsk", "Samara"],
        "MX": ["Mexico City", "Cancún", "Guadalajara", "Playa del Carmen", "Puerto Vallarta", "Monterrey", "Mérida", "Oaxaca"],
        "KR": ["Seoul", "Busan", "Jeju", "Incheon", "Daegu", "Daejeon", "Gwangju", "Suwon"],
        "TH": ["Bangkok", "Phuket", "Pattaya", "Chiang Mai", "Krabi", "Koh Samui", "Hua Hin", "Ayutthaya"],
        "SG": ["Singapore"],
        "AE": ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah"],
        "NL": ["Amsterdam", "Rotterdam", "The Hague", "Utrecht", "Eindhoven", "Groningen", "Maastricht", "Haarlem"],
        "CH": ["Zurich", "Geneva", "Basel", "Bern", "Lausanne", "Lucerne", "St. Moritz", "Interlaken"],
        "TR": ["Istanbul", "Ankara", "Izmir", "Antalya", "Bursa", "Adana", "Gaziantep", "Konya"],
        "EG": ["Cairo", "Alexandria", "Giza", "Luxor", "Aswan", "Hurghada", "Sharm El Sheikh", "Port Said"],
        "ZA": ["Cape Town", "Johannesburg", "Durban", "Pretoria", "Port Elizabeth", "Bloemfontein", "East London", "Pietermaritzburg"],
        "AR": ["Buenos Aires", "Córdoba", "Rosario", "Mendoza", "Tucumán", "La Plata", "Mar del Plata", "Salta"],
        "ID": ["Jakarta", "Bali", "Surabaya", "Medan", "Bandung", "Makassar", "Palembang", "Yogyakarta"],
        "MY": ["Kuala Lumpur", "Penang", "Johor Bahru", "Malacca", "Kota Kinabalu", "Kuching", "Ipoh", "Shah Alam"],
        "PH": ["Manila", "Cebu", "Davao", "Quezon City", "Zamboanga", "Antipolo", "Pasig", "Taguig"],
        "VN": ["Ho Chi Minh City", "Hanoi", "Da Nang", "Hai Phong", "Can Tho", "Bien Hoa", "Hue", "Nha Trang"],
        "GR": ["Athens", "Thessaloniki", "Patras", "Heraklion", "Larissa", "Volos", "Rhodes", "Ioannina"],
        "PT": ["Lisbon", "Porto", "Vila Nova de Gaia", "Amadora", "Braga", "Funchal", "Coimbra", "Setúbal"],
        "NO": ["Oslo", "Bergen", "Stavanger", "Trondheim", "Fredrikstad", "Kristiansand", "Sandnes", "Tromsø"],
        "SE": ["Stockholm", "Gothenburg", "Malmö", "Uppsala", "Västerås", "Örebro", "Linköping", "Helsingborg"],
        "DK": ["Copenhagen", "Aarhus", "Odense", "Aalborg", "Esbjerg", "Randers", "Kolding", "Horsens"],
        "FI": ["Helsinki", "Espoo", "Tampere", "Vantaa", "Oulu", "Turku", "Jyväskylä", "Lahti"],
        "AT": ["Vienna", "Graz", "Linz", "Salzburg", "Innsbruck", "Klagenfurt", "Villach", "Wels"],
        "BE": ["Brussels", "Antwerp", "Ghent", "Charleroi", "Liège", "Bruges", "Namur", "Leuven"],
        "CZ": ["Prague", "Brno", "Ostrava", "Plzen", "Liberec", "Olomouc", "Budweis", "Hradec Králové"],
        "PL": ["Warsaw", "Krakow", "Łódź", "Wrocław", "Poznań", "Gdansk", "Szczecin", "Bydgoszcz"],
        "HU": ["Budapest", "Debrecen", "Szeged", "Miskolc", "Pécs", "Győr", "Nyíregyháza", "Kecskemét"],
        "RO": ["Bucharest", "Cluj-Napoca", "Timișoara", "Iași", "Constanța", "Craiova", "Brașov", "Galați"],
        "BG": ["Sofia", "Plovdiv", "Varna", "Burgas", "Ruse", "Stara Zagora", "Pleven", "Dobrich"],
        "HR": ["Zagreb", "Split", "Rijeka", "Osijek", "Zadar", "Pula", "Slavonski Brod", "Karlovac"],
        "IL": ["Tel Aviv", "Jerusalem", "Haifa", "Rishon LeZion", "Petah Tikva", "Ashdod", "Netanya", "Beer Sheva"],
        "SA": ["Riyadh", "Jeddah", "Mecca", "Medina", "Dammam", "Khobar", "Tabuk", "Buraidah"],
        "QA": ["Doha", "Al Rayyan", "Umm Salal", "Al Wakrah", "Al Khor", "Dukhan", "Mesaieed", "Al Shamal"],
        "KW": ["Kuwait City", "Al Ahmadi", "Hawalli", "As Salimiyah", "Sabah as Salim", "Al Farwaniyah", "Al Fahahil", "Ar Riqqah"],
        "OM": ["Muscat", "Seeb", "Salalah", "Bawshar", "Sohar", "As Suwayq", "Saham", "Bahla"],
        "BH": ["Manama", "Riffa", "Muharraq", "Hamad Town", "A'ali", "Isa Town", "Sitra", "Budaiya"],
        "JO": ["Amman", "Zarqa", "Irbid", "Russeifa", "Wadi as Sir", "Aqaba", "Madaba", "As Salt"],
        "LB": ["Beirut", "Tripoli", "Sidon", "Tyre", "Nabatieh", "Jounieh", "Zahle", "Baalbek"],
        "CY": ["Nicosia", "Limassol", "Larnaca", "Famagusta", "Paphos", "Kyrenia", "Morphou", "Paralimni"],
        "MT": ["Valletta", "Birkirkara", "Mosta", "Qormi", "Zabbar", "San Pawl il-Baħar", "San Ġwann", "Tarxien"],
        "IS": ["Reykjavík", "Kópavogur", "Hafnarfjörður", "Akureyri", "Garðabær", "Mosfellsbær", "Árborg", "Akranes"],
        "LU": ["Luxembourg City", "Esch-sur-Alzette", "Differdange", "Dudelange", "Ettelbruck", "Diekirch", "Strassen", "Bertrange"],
        "MC": ["Monaco", "Monte Carlo", "La Condamine", "Fontvieille"]
    }
    
    return popular_destinations.get(country_code, [country_name])

def enhance_currency_data(currency_code: str, currency_name: str) -> tuple:
    """Enhance currency data using multiple sources"""
    if not currency_code:
        return None, None
    
    # If we have currency name from API, use it
    if currency_name:
        enhanced_name = currency_name
    else:
        enhanced_name = None
    
    # Try to get currency name from babel if available and name is missing
    if BABEL_AVAILABLE and not enhanced_name:
        try:
            enhanced_name = get_currency_name(currency_code, locale='en')
        except:
            pass
    
    # Try to get from pycountry currencies
    if not enhanced_name:
        try:
            pycountry_currency = pycountry.currencies.get(alpha_3=currency_code)
            if pycountry_currency:
                enhanced_name = pycountry_currency.name
        except:
            pass
    
    return currency_code, enhanced_name

def enhance_country_with_multiple_libs(country_data: Dict) -> Dict:
    """Enhance country data using multiple libraries"""
    iso_code_2 = country_data.get('iso_code_2')
    if not iso_code_2:
        return country_data
    
    # Enhance with pycountry
    try:
        pycountry_country = pycountry.countries.get(alpha_2=iso_code_2)
        if pycountry_country:
            # Enhance numeric code if missing
            if not country_data.get('numeric_code'):
                country_data['numeric_code'] = pycountry_country.numeric
            
            # Enhance ISO-3 code if missing
            if not country_data.get('iso_code_3'):
                country_data['iso_code_3'] = pycountry_country.alpha_3
            
            # Enhance official name if missing
            if not country_data.get('official_name'):
                country_data['official_name'] = pycountry_country.name
    except:
        pass
    
    # Enhance with pycountry-convert for continent/region data
    if PYCOUNTRY_CONVERT_AVAILABLE:
        try:
            # Get continent
            if not country_data.get('continent'):
                continent_code = pc.country_alpha2_to_continent_code(iso_code_2)
                continent_name = pc.convert_continent_code_to_continent_name(continent_code)
                country_data['continent'] = continent_name
            
            # Get region (continent in our case, since pycountry-convert doesn't have detailed regions)
            if not country_data.get('region'):
                country_data['region'] = country_data.get('continent')
                
        except:
            pass
    
    # Add sub-region data from our comprehensive mapping
    if not country_data.get('sub_region'):
        country_data['sub_region'] = SUBREGION_MAPPING.get(iso_code_2)
    
    # Enhance with countries-data library if available
    if COUNTRIES_DATA_AVAILABLE:
        try:
            country_details = countries.get(iso_code_2)
            if country_details:
                # Additional enhancements from countries-data
                if not country_data.get('languages') or len(country_data['languages']) == 0:
                    if hasattr(country_details, 'languages') and country_details.languages:
                        country_data['languages'] = country_details.languages
                        
                # Additional continent/region verification
                if hasattr(country_details, 'continent') and not country_data.get('continent'):
                    country_data['continent'] = country_details.continent
                    
        except:
            pass
    
    # Enhance with countryinfo for additional data
    if COUNTRYINFO_AVAILABLE:
        try:
            country_info = CountryInfo(iso_code_2)
            
            # Get capital if missing
            if not country_data.get('capital_city'):
                capital = country_info.capital()
                if capital:
                    country_data['capital_city'] = capital
            
            # Get currencies if missing
            if not country_data.get('currency_code'):
                currencies = country_info.currencies()
                if currencies and len(currencies) > 0:
                    country_data['currency_code'] = currencies[0]
                    
                    # Try to get currency name from babel
                    if BABEL_AVAILABLE:
                        try:
                            currency_name = get_currency_name(currencies[0], locale='en')
                            country_data['currency_name'] = currency_name
                        except:
                            pass
            
            # Get calling codes if missing
            if not country_data.get('calling_code'):
                calling_codes = country_info.calling_codes()
                if calling_codes and len(calling_codes) > 0:
                    country_data['calling_code'] = f"+{calling_codes[0]}"
            
            # Get coordinates if missing
            if not country_data.get('latitude') or not country_data.get('longitude'):
                try:
                    latlng = country_info.latlng()
                    if latlng and len(latlng) >= 2:
                        country_data['latitude'] = latlng[0]
                        country_data['longitude'] = latlng[1]
                except:
                    pass
            
            # Get timezones if missing
            if not country_data.get('timezone_info') or country_data['timezone_info']['main'] == 'UTC':
                try:
                    timezones = country_info.timezones()
                    if timezones:
                        country_data['timezone_info'] = {
                            "main": timezones[0],
                            "zones": timezones
                        }
                except:
                    pass
                    
        except:
            pass
    
    return country_data

def process_country_data(api_data: List[Dict]) -> List[Dict]:
    """Process country data from API, pycountry, and babel"""
    
    processed_countries = []
    
    # Detect API version from data structure
    is_v3_api = any('cca2' in country for country in api_data[:5])
    api_version = "v3" if is_v3_api else "v2"
    print(f"📊 Processing {len(api_data)} countries from REST Countries API {api_version}")
    print(f"🔧 Multi-library enhancement:")
    print(f"   - pycountry: ✅")
    print(f"   - babel: {'✅' if BABEL_AVAILABLE else '❌'}")
    print(f"   - pycountry-convert: {'✅' if PYCOUNTRY_CONVERT_AVAILABLE else '❌'}")
    print(f"   - countryinfo: {'✅' if COUNTRYINFO_AVAILABLE else '❌'}")
    
    for country in api_data:
        try:
            if api_version == "v3":
                # REST Countries API v3 format
                cca2 = country.get('cca2')
                cca3 = country.get('cca3')
                name = country.get('name', {}).get('common', '')
                official_name = country.get('name', {}).get('official', '')
                
                # Extract currencies (v3 format)
                currencies = country.get('currencies', {})
                currency_code = None
                currency_name = None
                if currencies:
                    first_currency = list(currencies.values())[0]
                    currency_code = list(currencies.keys())[0]
                    currency_name = first_currency.get('name', '')
                
                # Extract languages (v3 format)
                languages = country.get('languages', {})
                language_codes = list(languages.keys()) if languages else []
                
                # Get capital (v3 format)
                capital = None
                if country.get('capital'):
                    capital = country['capital'][0] if isinstance(country['capital'], list) else str(country['capital'])
                
                # Get calling codes (v3 format)
                calling_codes = country.get('idd', {})
                calling_code = None
                if calling_codes.get('root') and calling_codes.get('suffixes'):
                    calling_code = calling_codes['root'] + (calling_codes['suffixes'][0] if calling_codes['suffixes'] else '')
                
                # Geographic data (v3 format)
                continent = country.get('continents', [None])[0]
                region = country.get('region')
                sub_region = country.get('subregion')
                
            else:
                # REST Countries API v2 format
                cca2 = country.get('alpha2Code')
                cca3 = country.get('alpha3Code') 
                name = country.get('name', '')
                official_name = name  # v2 doesn't have separate official name
                
                # Extract currencies (v2 format)
                currencies = country.get('currencies', [])
                currency_code = None
                currency_name = None
                if currencies and len(currencies) > 0:
                    first_currency = currencies[0]
                    currency_code = first_currency.get('code')
                    currency_name = first_currency.get('name')
                
                # Extract languages (v2 format)
                languages = country.get('languages', [])
                language_codes = [lang.get('iso639_1') for lang in languages if lang.get('iso639_1')]
                
                # Get capital (v2 format)
                capital = country.get('capital')
                
                # Get calling codes (v2 format)
                calling_codes = country.get('callingCodes', [])
                calling_code = f"+{calling_codes[0]}" if calling_codes and calling_codes[0] else None
                
                # Geographic data (v2 format)
                continent = country.get('region')  # v2 uses 'region' for continent
                region = country.get('region')
                sub_region = country.get('subregion')
            
            # Skip if missing essential data
            if not cca2 or not name:
                continue
            
            # Extract coordinates (same for both versions)
            latlng = country.get('latlng', [])
            latitude = latlng[0] if len(latlng) > 0 else None
            longitude = latlng[1] if len(latlng) > 1 else None
            
            # Get timezone info
            timezones = country.get('timezones', [])
            timezone_info = {
                "main": timezones[0] if timezones else "UTC",
                "zones": timezones
            }
            
            # Enhance currency data using multiple sources
            enhanced_currency_code, enhanced_currency_name = enhance_currency_data(currency_code, currency_name)
            
            # Determine popularity (major countries by population/tourism)
            popular_country_codes = {
                'US', 'CN', 'IN', 'BR', 'RU', 'JP', 'DE', 'GB', 'FR', 'IT', 'KR', 'ES', 'CA', 'AU', 'MX', 'TH', 'TR', 'SA', 'AE', 'SG', 'MY', 'ID', 'PH', 'VN', 'EG', 'ZA', 'AR', 'NL', 'CH', 'AT', 'BE', 'SE', 'NO', 'DK', 'FI', 'IE', 'PT', 'GR', 'PL', 'CZ', 'HU', 'RO', 'BG', 'HR', 'IL', 'QA', 'KW', 'OM', 'BH', 'JO', 'LB', 'CY', 'MT', 'IS', 'LU', 'MC'
            }
            
            country_data = {
                "iso_code_2": cca2,
                "iso_code_3": cca3,
                "numeric_code": country.get('ccn3') if api_version == "v3" else country.get('numericCode'),
                "name": name,
                "official_name": official_name,
                "common_name": name,
                "continent": continent,
                "region": region,
                "sub_region": sub_region,
                "currency_code": enhanced_currency_code,
                "currency_name": enhanced_currency_name,
                "languages": language_codes,
                "capital_city": capital,
                "latitude": latitude,
                "longitude": longitude,
                "calling_code": calling_code,
                "timezone_info": timezone_info,
                "popular_destinations": get_popular_destinations_for_country(cca2, name),
                "is_active": True,
                "is_popular": cca2 in popular_country_codes
            }
            
            # Enhance with multiple libraries
            country_data = enhance_country_with_multiple_libs(country_data)
            
            processed_countries.append(country_data)
            
        except Exception as e:
            country_name = country.get('name', {}).get('common') if isinstance(country.get('name'), dict) else country.get('name', 'Unknown')
            print(f"❌ Error processing country {country_name}: {e}")
            continue
    
    # Sort by popularity and name
    processed_countries.sort(key=lambda x: (not x['is_popular'], x['name']))
    
    return processed_countries

def get_fallback_data() -> List[Dict]:
    """Fallback data using multiple libraries with comprehensive enhancement"""
    print("📚 Using pycountry with multi-library enhancement...")
    print(f"🔧 Available libraries:")
    print(f"   - pycountry: ✅")
    print(f"   - babel: {'✅' if BABEL_AVAILABLE else '❌'}")
    print(f"   - pycountry-convert: {'✅' if PYCOUNTRY_CONVERT_AVAILABLE else '❌'}")
    print(f"   - countryinfo: {'✅' if COUNTRYINFO_AVAILABLE else '❌'}")
    print(f"   - countries-data: {'✅' if COUNTRIES_DATA_AVAILABLE else '❌'}")
    print(f"   - UN M49 sub-regions: ✅")
    
    countries = []
    
    for country in pycountry.countries:
        # Get popular destinations
        popular_destinations = get_popular_destinations_for_country(country.alpha_2, country.name)
        
        # Determine if popular
        popular_codes = {'US', 'CN', 'IN', 'BR', 'RU', 'JP', 'DE', 'GB', 'FR', 'IT', 'KR', 'ES', 'CA', 'AU'}
        
        country_data = {
            "iso_code_2": country.alpha_2,
            "iso_code_3": country.alpha_3,
            "numeric_code": country.numeric,
            "name": country.name,
            "official_name": country.name,
            "common_name": country.name,
            "continent": None,
            "region": None,
            "sub_region": None,
            "currency_code": None,
            "currency_name": None,
            "languages": [],
            "capital_city": None,
            "latitude": None,
            "longitude": None,
            "calling_code": None,
            "timezone_info": {"main": "UTC", "zones": ["UTC"]},
            "popular_destinations": popular_destinations,
            "is_active": True,
            "is_popular": country.alpha_2 in popular_codes
        }
        
        # Enhance with multiple libraries
        country_data = enhance_country_with_multiple_libs(country_data)
        
        countries.append(country_data)
    
    return countries

async def seed_countries_auto():
    """Automatically seed countries using API and library data"""
    
    # Initialize Tortoise ORM
    db_url = settings.DATABASE_URL
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://', 1)

    TORTOISE_ORM = {
        "connections": {"default": db_url},
        "apps": {
            "models": {
                "models": ["models.models"],
                "default_connection": "default",
            },
        },
    }

    print(f"🌍 Auto-seeding countries from multiple sources...")
    print(f"Connecting to database: {db_url}")
    await Tortoise.init(config=TORTOISE_ORM)

    # Check existing data
    existing_count = await Country.all().count()
    if existing_count > 0:
        print(f"Found {existing_count} existing countries")
        print("Auto-clearing existing data to reseed with comprehensive data...")
        await Country.all().delete()
        print("Cleared existing country data")

    # Get country data
    api_data = fetch_countries_from_api()
    
    if api_data:
        print(f"✅ Found {len(api_data)} countries from REST Countries API")
        countries_data = process_country_data(api_data)
    else:
        print("⚠️ API failed, using pycountry fallback")
        countries_data = get_fallback_data()

    # Insert countries
    countries_created = 0
    
    for country_data in countries_data:
        try:
            country = await Country.create(**country_data)
            countries_created += 1
            
            status = "🌟" if country.is_popular else "🌍"
            dest_count = len(country.popular_destinations) if country.popular_destinations else 0
            print(f"{status} Created: {country.name} ({country.iso_code_2}) - {dest_count} destinations")
            
        except Exception as e:
            print(f"❌ Failed to create {country_data['name']}: {e}")

    print(f"\n🎉 Successfully created {countries_created} countries")
    
    # Statistics
    total = await Country.all().count()
    popular = await Country.filter(is_popular=True).count()
    
    print(f"📊 Final statistics:")
    print(f"   - Total countries: {total}")
    print(f"   - Popular countries: {popular}")
    print(f"   - Regular countries: {total - popular}")
    
    # Show popular countries
    print(f"\n🌟 Popular countries with destinations:")
    popular_countries = await Country.filter(is_popular=True).order_by('name').limit(10).all()
    for country in popular_countries:
        dest_count = len(country.popular_destinations) if country.popular_destinations else 0
        print(f"   {country.name} ({country.iso_code_2}) - {dest_count} destinations - {country.currency_code}")

    await Tortoise.close_connections()
    print("\n✅ Automated country seeding completed!")

if __name__ == "__main__":
    asyncio.run(seed_countries_auto())