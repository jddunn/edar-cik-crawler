# Edgar Crawler

Script to extract fund holdings from EDGAR given ticker or CIK, outputting content found from tabular data in crawled docs as TSV in within /results subfolder. Has basic CLI for running the crawling with optional filter text. 

The crawled URL essentially comes from https://www.sec.gov/edgar/searchedgar/companysearch.html. Data normalization is done for consistency, but the only property the table extraction looks for is for a table class "tableFile". In the future this should be looked into so that all possible tables can be extracted and checked for meaningful data, by adding extra steps in checking the parsed text for more tables.

Run the script with arguments --id TICKER_CIK and --filter (optional) FILTER_STRING to have Edgar Crawler only extract documents with titles that contain the text passed.

## Pre-requisites

- Beautiful Soup 4
- LXML
- html5lib

```
pip3 install -r requirements.txt
```

## Examples

```
python edgar_cik_crawler.py -i 0001068833 
```

```
python edgar_crawler_cik.py -i 0001166559 -f 13F
```

## Sample output screenshot

![Alt text](output_screenshot_sample.png?raw=true "Edgar Crawler Sample Output Screenshot")