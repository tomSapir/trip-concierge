"""Source text for the destination guides.

Hand-authored prose, one entry per destination. `make_guides.py` renders each
entry to data/destinations/<name>.pdf. This module is the reviewable, diffable
source of truth — the PDFs are build artifacts. Keys MUST match the destination
names in the registry (app/modules/destination_registry.py).
"""

GUIDES = {
    "Lisbon": {
        "country": "Portugal",
        "sections": [
            ("Climate",
             "Mediterranean and one of Europe's sunniest capitals. Warm, dry "
             "summers with highs around 28 C; mild, wetter winters that rarely "
             "drop below 8 C."),
            ("Best time to visit",
             "Spring (March-May) and early autumn (September-October) are ideal "
             "- warm weather with thinner crowds. July and August are the "
             "hottest and busiest."),
            ("Top attractions",
             "Belem Tower and Jeronimos Monastery, the maze-like Alfama district "
             "below Sao Jorge Castle, a ride on historic Tram 28, the hilltop "
             "miradouros over the Tagus, and a day trip to the palaces of Sintra."),
            ("Food",
             "Pasteis de nata custard tarts, bacalhau (salt cod) in countless "
             "forms, grilled sardines, fresh seafood, and a glass of ginjinha "
             "cherry liqueur or vinho verde."),
            ("Visa & safety",
             "A very safe city; take normal big-city care with pickpockets on "
             "crowded trams and in tourist areas. Portugal is in the Schengen "
             "Area - check the current entry requirements for your nationality "
             "before you travel."),
        ],
    },
    "Kyoto": {
        "country": "Japan",
        "sections": [
            ("Climate",
             "Humid subtropical with four distinct seasons. Hot, humid summers "
             "near 33 C with a rainy spell in June; cold, crisp winters with the "
             "occasional snowfall."),
            ("Best time to visit",
             "Late March to early April for cherry blossoms and November for "
             "autumn foliage - both spectacular and crowded. Summer is hot and "
             "humid; winter is quiet and atmospheric."),
            ("Top attractions",
             "The thousands of vermilion torii gates at Fushimi Inari, the "
             "Golden Pavilion (Kinkaku-ji), the Arashiyama bamboo grove, the "
             "historic Gion geisha district, and the hillside Kiyomizu-dera temple."),
            ("Food",
             "Multi-course kaiseki dining, yudofu (tofu hot pot), delicate "
             "matcha sweets, refined Buddhist vegetarian cuisine, and street "
             "snacks at Nishiki Market."),
            ("Visa & safety",
             "Extremely safe with very low crime; the main etiquette is respect "
             "at temples and shrines. Many nationalities receive visa-free short "
             "stays - confirm the current rules for your passport before travel."),
        ],
    },
    "Reykjavik": {
        "country": "Iceland",
        "sections": [
            ("Climate",
             "Subpolar oceanic and famously changeable. Cool summers around "
             "13 C and, for the latitude, mild but windy winters near 0 C. "
             "Near-endless daylight in midsummer, very short days in winter."),
            ("Best time to visit",
             "June to August for the midnight sun, hiking and road trips; "
             "September to March for a chance at the Northern Lights. Pack for "
             "wind and rain in any season."),
            ("Top attractions",
             "The Blue Lagoon geothermal spa, the Golden Circle (Thingvellir, "
             "Geysir and Gullfoss waterfall), the landmark Hallgrimskirkja "
             "church, whale watching, and glacier or volcano tours."),
            ("Food",
             "Free-range lamb, fresh cod and langoustine, creamy skyr, dense rye "
             "bread, and the local hot dogs (pylsur). The adventurous can try "
             "fermented shark."),
            ("Visa & safety",
             "One of the safest countries in the world; the real risks are "
             "weather and terrain, so follow your guides on tours. Iceland is in "
             "the Schengen Area - check the current entry requirements for your "
             "nationality before travel."),
        ],
    },
    "Barcelona": {
        "country": "Spain",
        "sections": [
            ("Climate",
             "Mediterranean and sunny most of the year. Warm summers around "
             "29 C cooled by a sea breeze, and mild winters near 14 C."),
            ("Best time to visit",
             "May-June and September bring warm weather and beach days without "
             "peak crowds. July and August are hottest and busiest; the "
             "nightlife runs year-round."),
            ("Top attractions",
             "Gaudi's Sagrada Familia, Park Guell, Casa Batllo and La Pedrera, "
             "the medieval Gothic Quarter, the La Rambla promenade, Barceloneta "
             "beach, and Camp Nou."),
            ("Food",
             "Tapas, paella, jamon iberico, pa amb tomaquet, fresh seafood, and "
             "cava sparkling wine - best grazed through the stalls of La Boqueria "
             "market, with dinner served late."),
            ("Visa & safety",
             "Generally safe but well known for pickpockets on La Rambla, the "
             "metro and the beach, so keep valuables secure. Spain is in the "
             "Schengen Area - check the current entry requirements for your "
             "nationality before travel."),
        ],
    },
    "Bali": {
        "country": "Indonesia",
        "sections": [
            ("Climate",
             "Tropical and warm all year near 30 C. A dry season from April to "
             "October and a humid wet season from November to March with short "
             "afternoon downpours."),
            ("Best time to visit",
             "The dry season (April-October), especially May-June and September, "
             "offers sun and lower humidity - ideal for beaches and surfing."),
            ("Top attractions",
             "Ubud's rice terraces, yoga studios and monkey forest; the clifftop "
             "Uluwatu and sea-set Tanah Lot temples; the beaches of Seminyak and "
             "Nusa Dua; a sunrise hike up Mount Batur; and the Nusa islands."),
            ("Food",
             "Nasi goreng and mie goreng, satay skewers, babi guling (suckling "
             "pig), abundant tropical fruit, and fresh seafood at beachfront "
             "warungs."),
            ("Visa & safety",
             "Generally safe; take care with scooter traffic and strong ocean "
             "currents. Many nationalities use a visa on arrival or e-visa - "
             "check the current Indonesian entry rules and passport-validity "
             "requirements before travel."),
        ],
    },
    "Rome": {
        "country": "Italy",
        "sections": [
            ("Climate",
             "Mediterranean with hot, dry summers around 31 C and mild, wetter "
             "winters near 12 C. Spring and autumn are pleasantly warm."),
            ("Best time to visit",
             "April-June and September-October bring warm weather with more "
             "manageable crowds. July and August are very hot and crowded, and "
             "many locals leave the city in August."),
            ("Top attractions",
             "The Colosseum and Roman Forum, Vatican City with St Peter's "
             "Basilica and the Sistine Chapel, the Pantheon, the Trevi Fountain, "
             "the Spanish Steps, and the lively Trastevere district."),
            ("Food",
             "Roman pasta classics - carbonara, cacio e pepe and amatriciana - "
             "plus thin Roman pizza, suppli, espresso, and gelato. Save room for "
             "Roman-Jewish fried artichokes."),
            ("Visa & safety",
             "Generally safe, with pickpockets working the major sites and the "
             "buses and metro toward Termini and the Vatican. Italy is in the "
             "Schengen Area - check the current entry requirements for your "
             "nationality before travel."),
        ],
    },
}
