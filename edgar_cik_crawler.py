"""
Extract fund holdings from EDGAR given ticker or CIK, outputting 
content found from tabular data in crawled docs as TSV in within
/results subfolder.

Has basic CLI for running the crawling with optional filter text.

Examples Usage:
python edgar_crawler.py -i 0001166559 
python edgar_crawler.py -i 0001068833 -f 13F

If no -f parameter is provided, filter text defaults to '' so 
all doc links found will be downloaded.
"""

import os
import argparse
import requests
from bs4 import BeautifulSoup
from lxml import etree

parser = etree.XMLParser(recover=True)

def convert_to_tsv(filename, text):
    """
    Parses tabular data from XML content and converts it into valid TSV values.
    """
    # First split our text by newlines, since the data is stored in a table.
    # We can assume each new line is a new record, and that the first line contains
    # the table headers.
    lines = text.strip().split("\n")
    new_lines = []
    res_lines = []
    for line in lines:
         # The company name is found generally within the first six words (e.g. 
         # 'MELLON FINANCIAL CORP'). Since we have to normalize whitespace chars
         # because the data from Edgar is inconsistently formatted, we construct
         # the name first as it's separated by single spaces, and rebuild the lines
         # with remaining tokens of data that are not part of a company name
         # (which can be separated by one or more spaces). 
        new_line_tokens = line.split() # This splits everything out by whitespaces
        new_line_name_tokens = line.split(' ')[0:6] # This gives us just the name tokens
        new_line_name_tokens = list(filter(None, new_line_name_tokens))
        name = ' '.join([token for token in new_line_name_tokens])
        # Check to see if a name token is found in the first six items of the new line
        # tokens, and if so, remove the name elements for separate combining.
        for token in new_line_name_tokens:
            if token in new_line_tokens[0:6]:
                new_line_tokens.remove(token)
        # Combine name with rest of the line tokens
        res_line_tokens = []
        res_line_tokens.append(name)
        res_line_tokens = res_line_tokens + new_line_tokens
        res_lines.append(res_line_tokens)
    if not os.path.exists('results'):
        os.makedirs('results')
    with open('results/' + filename + '.tsv', "w") as tsv_file:
        # Write each record into a TSV file
        for each in res_lines:
            res_line = '\t'.join([val for val in each])
            try:
                print(res_line)
            except:
                pass
            try:
                tsv_file.write(str(res_line) + "\n")
            except:
                pass
    return

def extract_xml_content_from_text(text_data):
    """
    Extracts tabular data from the XML contents found within a text.
    """
    doc_tree = etree.fromstring(text_data, parser=parser)
    # List of strings to filter lines within the XML content by since we 
    # only want usable data that can be parsed into TSV easily. This list 
    # was generated based off of testing funds list for different tickers
    # and aggregating text that would likely invalidate the final TSV results.
    filter_vals = ['S REPORT SUMMARY',
                   'FORM 13F INFORMATION TABLE',
                   'SHARES/ SH/ PUT/ INVSTMT',
                   'Total   ( '
                  ]
    if doc_tree is not None:
        xml_results = []
        for node in doc_tree.iter():
            if str(node.tag).lower() == "table": # Get the table element
               vals = ''.join(node.itertext())
                # Filter out invalid lines found
               lines = vals.split('\n')
               for line in lines:
                   filter_found = False
                   for each in filter_vals:
                       if each in line:
                            filter_found = True
                            break
                   if not filter_found:
                       xml_results.append(line)
        return '\n'.join(xml_results)
    else:
        return None

def extract_data_from_text_files(ticker_link):
    """
    Picks the best text file to download from a ticker page in Edgar. 

    Although some document pages contain files already in XML format, there
    was a large majority of docs that only had a .txt file for the data. 
    This function grabs the best text file found and extracts the content.
    """
    inner_page_data = make_request(ticker_link)
    soup = BeautifulSoup(inner_page_data, 'html5lib')
    table = soup.find('table', {'class': 'tableFile'}) # Table name we want is tableFile

    # Some company pages have multiple text files (including a duplicate of the other
    # file but with cryptographic information prepended), so check to see if multiple 
    # downloadable docs are found. If so, as a naive check for now, check to see which
    # link contains the smallest file available, because that will be the copy of the
    # file with no cryptographic data, and download that.
    inner_a_divs = table.find_all('a', href=True) # Actual links to the docs
    inner_hrefs = []
    inner_links = []
    xml_found = False
    for each in inner_a_divs:
        inner_hrefs.append(each.get('href'))
    for each in inner_hrefs:
        # If we find a XML file then use that instead of a text file.
        if '.xml' in str(each):
            inner_links.append('https://www.sec.gov/' + each)
            xml_found = True
            break
        # Otherwise, grab all the text files and determine which one to extract.
        if '.txt' in str(each): # Only grab links that contain a .txt extension, since 
                                # XML data in Edgar is stored within text files.
            inner_links.append('https://www.sec.gov/' + each)
    if not xml_found:
        inner_links_info = []
        for link in inner_links:
            try:
                content_length = requests.get(link, stream=True).headers['Content-length']
            except:
                content_length = 0
            inner_links_info.append((link, int(content_length)))
        smallest = 1000000000000000000000000000 # Extremely large number to start 
        smallest_link = ''
        for link_info in inner_links_info:
            if link_info[1] < smallest:
               smallest = link_info[1]
               smallest_link = link_info[0]
        # Download the contents within the link with the smaller file size found (as 
        # it is the file that does not contain encryption info in a header)
        try:
            # print("Downloading text contents from: ", smallest_link)
            text_data = make_request(smallest_link)
            return text_data
        except:
            return None
    else:
        try:
            xml_data = make_request(inner_links[0])
            return xml_data
        except:
            return None

def get_soup_contents(page_data, filter_text):
    """
    Parse page content with BeautifulSoup4, and get 
    the rows of information located in the table,
    based on a filter_text provided.
    """
    soup = BeautifulSoup(page_data, 'html5lib')
    # Get links to documents with 13F in them
    # The table on this page with the important info is named tableFile2.
    table = soup.find('table', {'class': 'tableFile2'})
    rows = table.findAll('tr')
    table_content = []
    matrices_rows = []
    for row in rows:
        matrix_row = []
        for cell in row.find_all('td'):
            matrix_row.append(cell)
        matrices_rows.append(matrix_row)
    for row in matrices_rows:
        try:
            doc_title = row[0].get_text().strip() # Title of doc
            filing_date = row[3].get_text().strip() # Save filing date so we can
                                                    # uniquely identify each doc later.
            if filter_text in doc_title: # If 13F is in the document name..
                a_content = row[1].find('a') # Get link to document
                href = a_content['href'] 
                full_link = 'https://www.sec.gov/' + href # Need to combine base site 
                                                         # URL with path from href
                tup = (doc_title, full_link, filing_date)
                table_content.append(tup) # Append values as tuples to list
        except:
            pass
    return table_content

def make_request(URL):
    """
    Makes page request and returns content.
    """
    r = requests.get(URL)
    data = r.content
    return data

def build_url(ticker_id):
    """
    Builds URL to crawl from ticker or CIK.
    """
    edgar_url = 'https://www.sec.gov/cgi-bin/browse-edgar?CIK=' + \
                 ticker_id + '&Find=Search&owner=exclude&action=getcompany'
    return edgar_url

# Per the requirements, have the default filter_text be '13F' for document titles if not provided.
def main(ticker_id, filter_text=''):
    """
    Main function that calls crawling, parsing, and saving of fund holdings from Edgar.
    """
    # Build URL to make request to Edgar
    url = build_url(ticker_id)
    print("\nGetting request for Edgar URL: ", url, "with the filter of: ", filter_text, "\n")
    page_data = make_request(url)
    # Parse page data for documents
    print("Getting soup and parsing docs..\n")
    # Make a list of links that contains the documents we want to extract from
    docs_contents = get_soup_contents(page_data, filter_text)
    xml_results = {} # Results from parsing XML contents
    results_files = [] # List of filenames with TSV data saved from docs
    for each in docs_contents:
        doc_title = each[0]
        doc_link = each[1]
        doc_filing_date = each[2]
        text_data = extract_data_from_text_files(doc_link) # Get text data from ticker docs
        if (text_data is not None):
            xml_data = extract_xml_content_from_text(text_data) # Extracted XML content to be converted
                                                                # into TSV files.
            if xml_data is not None:
                print("Parsed XML contents for: " + doc_title, "from", doc_filing_date, "from", ticker_id)
                # print(xml_data)
                xml_results[doc_title + '_' + ticker_id] = xml_data
                filename = ticker_id + '_' + doc_title + '_' + doc_filing_date + '_results'
                filename = filename.replace('/', '-') # Sometimes there are slash names within the doc title,
                                                      # replace this as it makes an invalid filename.
                convert_to_tsv(filename, xml_results[doc_title + '_' + ticker_id])
                print("Converted XML results and saved as TSV in", filename+'.tsv')
                results_files.append(filename+'.tsv')
    print("\nResults of" , ticker_id, "for filter", filter_text, "saved to", results_files)


if __name__ == '__main__':
    # CLI
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--id", required=True,
                    help="Enter in ticker or CIK number")
    ap.add_argument("-f", "--filter", required=False,
                    help="""Filter document title by this string. 
                          Not required, by default, set to '' to 
                          capture all document links found.""")
    args = vars(ap.parse_args())
    # Get the text we want to filter document titles by. 
    # By default, set to '' to extract all found documents
    filter_text = args['filter']
    if filter_text is None:
        filter_text = ''
    # Get ticker or CIK from script argument
    ticker_id = args['id']
    # Run main function
    main(ticker_id, filter_text)