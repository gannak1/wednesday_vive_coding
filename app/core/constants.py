CATEGORIES = ("war", "economy", "disaster", "politics")
CONTINENTS = (
    "Asia",
    "Europe",
    "Africa",
    "NorthAmerica",
    "SouthAmerica",
    "Oceania",
)

CATEGORY_LABELS = {
    "war": "전쟁",
    "economy": "경제",
    "disaster": "자연재해",
    "politics": "정치",
}

CATEGORY_ROUTES = {
    "war": "/war",
    "economy": "/economy",
    "disaster": "/disaster",
    "politics": "/politics",
}

PIN_COLORS = {
    "war": "#EF4444",
    "economy": "#16A34A",
    "politics": "#EAB308",
    "disaster": "#F97316",
}

HIGH_INTENSITY_KEYWORDS = {
    "war": ["invasion", "missile", "strike", "nuclear", "siege"],
    "economy": ["recession", "crash", "rate hike", "sanctions", "default"],
    "disaster": ["earthquake", "tsunami", "wildfire", "flood", "eruption"],
    "politics": ["coup", "impeachment", "election crisis", "martial law", "sanctions"],
}

CATEGORY_QUERIES = {
    "war": "war OR military OR missile OR conflict OR invasion OR ceasefire",
    "economy": "economy OR inflation OR interest rate OR trade OR market OR tariff",
    "disaster": "earthquake OR flood OR wildfire OR hurricane OR typhoon OR drought",
    "politics": "election OR government OR parliament OR diplomacy OR summit OR sanctions",
}

CATEGORY_PRIORITY = ("disaster", "war", "politics", "economy")
