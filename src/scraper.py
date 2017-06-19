"""King county health data scraped."""
import requests
from bs4 import BeautifulSoup
import sys
import re


INSPECTION_DOMAIN = 'http://info.kingcounty.gov'
INSPECTION_PATH = '/health/ehs/foodsafety/inspections/Results.aspx'
INSPECTION_PARAMS = {
    'Output': 'W',
    'Business_Name': '',
    'Business_Address': '',
    'Longitude': '',
    'Latitude': '',
    'City': '',
    'Zip_Code': '',
    'Inspection_Type': 'All',
    'Inspection_Start': '',
    'Inspection_End': '',
    'Inspection_Closed_Business': 'A',
    'Violation_Points': '',
    'Violation_Red_Points': '',
    'Violation_Descr': '',
    'Fuzzy_Search': 'N',
    'Sort': 'H'
}


def get_inspection_page(**queries):
    """Query king county health inspection data and return html content."""
    url = INSPECTION_DOMAIN + INSPECTION_PATH
    params = INSPECTION_PARAMS.copy()
    for key, val in queries.items():
        if key in INSPECTION_PARAMS:
            params[key] = val
    response = requests.get(url, params=params)
    response.raise_for_status()
    with open('./inspection_page.html', 'w') as page:
        page.write(response.text)
    return response.content, response.encoding


def load_inspection_page(**queries):
    """Return stored inspection data."""
    with open('./inspection_page.html') as page:
        f = page.read()
    return f.encode(), 'utf-8'


def parse_source(html_body):
    """Set up html and dom nodes for scraping."""
    return BeautifulSoup(html_body[0], 'html5lib', from_encoding=html_body[1])


def extract_data_listings(html):
    """Extract info from api."""
    id_finder = re.compile(r'PR[\d]+~')
    return html.find_all('div', id=id_finder)


def has_two_tds(element):
    """Return True if the element is both a <tr> and contains exactly two <td> elements immediately within it."""
    return element.name == 'tr' and len(element.find_all('td')) == 2


def clean_data(td):
    """Clean the values from the cells."""
    data = td.string
    try:
        return data.strip(" \n:-")
    except AttributeError:
        return u""


def extract_restaurant_metadata(listing):
    """Get the data and give a label and value as dictionary."""
    metadata = {}
    trs = listing.find('tbody').find_all(has_two_tds, recursive=False)
    for tr in trs:
        tds = tr.find_all('td', recursive=False)
        key = clean_data(tds[0])
        if key:
            metadata[key] = clean_data(tds[1])
        else:
            metadata['Address'] += ', ' + clean_data(tds[1])
    return metadata


def is_inspection_row(element):
    """Return True if the element matches the criteria of the filter, False otherwise."""
    tds = element.find_all('td')
    if element.name == 'tr' and len(tds) == 4:
        content = tds[0].string
        return 'Inspection' in content and content.split()[0] != 'Inspection'


def extract_score_data(element):
    """Return a dictionary containing the average score, high score, and total inspection values."""
    inspection_rows = element.find_all(is_inspection_row)
    samples = len(inspection_rows)
    total = high_score = average = 0
    for row in inspection_rows:
        strval = clean_data(row.find_all('td')[2])
        try:
            intval = int(strval)
        except (ValueError, TypeError):
            samples -= 1
        else:
            total += intval
            high_score = intval if intval > high_score else high_score
    if samples:
        average = total / float(samples)
    data = {
        u'Average Score': average,
        u'High Score': high_score,
        u'Total Inspections': samples
    }
    return data


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        response = load_inspection_page()
    else:
        response = get_inspection_page(Zip_Code='98121')
    soup = parse_source(response)
    listings = extract_data_listings(soup)
    for listing in listings:
        metadata = extract_restaurant_metadata(listing)
        score_data = extract_score_data(listing)
        metadata.update(score_data)
        print(metadata)
