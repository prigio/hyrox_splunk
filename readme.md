

# Download Hyrox data from mikatiming

Update the `events` data structure within `download_data.py` with the updated event IDs, dates and names.

```bash
virtualenv venv
source venv/bin/activate
pip3 install -r pip_requirements.py

python3 download_data.py
```

## Ingest the data within splunk

`splunk add oneshot <filename> -sourcetype hyrox`

## In case of duplicates within the Hyrox data
The website might duplicate data. When stored, the links must be modified to remove the page number, then `|sort|uniq` the data.


    cat Hyrox\ -\ 2019\ Hannover.json \
    | sed 's/page=.&//g' \
    | sort | uniq \
    > data_files/Hyrox\ -\ 2019\ Hannover.json


## Sample data

```json
	{
    "category": "women",
    "division": "regular",
    "event": "Hyrox",
    "event_occurrence": "2018 Stuttgart",
    "judges_bonus": null,
    "judges_penalty": null,
    "name": "Stunning, Athlete (GER)",
    "place": "8",
    "place_ak": 1,
    "splits": {
        "01_Running 1": 253.0,
        "02_Running 2": 324.0,
        "03_Running 3": 362.0,
        "04_Running 4": 347.0,
        "05_Running 5": 350.0,
        "06_Running 6": 326.0,
        "07_Running 7": 332.0,
        "08_Running 8": 391.0,
        "09_1000m Ski Erg": 284.0,
        "10_2x25m Sled Push": 120.0,
        "11_2x25m Sled Pull": 321.0,
        "12_80m Burpee Broad Jump": 332.0,
        "13_1000m Ruder Erg": 2335.0,
        "14_200m Farmers Carry": 99.0,
        "15_100m Sandbag Lunges": 269.0,
        "16_Wall Balls": 252.0
    },
    "start_number": "100009",
    "start_time": "2018-12-08 10:00:00",
    "total_time": 5036.0
	}
```

