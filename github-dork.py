#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import os
import argparse
import time
import feedparser
import requests
import logging
from copy import copy
from sys import prefix

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# GitHub authentication and API setup
gh_token = os.getenv('GH_TOKEN')
gh_user = os.getenv('GH_USER')
gh_url = os.getenv('GH_URL', 'https://api.github.com')
headers = {'Authorization': f'token {gh_token}'}

def get_rate_limit():
    response = requests.get(f'{gh_url}/rate_limit', headers=headers)
    response.raise_for_status()
    return response.json()['resources']['search']

def search_wrapper(gen):
    while True:
        gen_back = copy(gen)
        try:
            yield next(gen)
        except StopIteration:
            return
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:  # Rate limit hit
                search_rate_limit = get_rate_limit()
                reset_time = search_rate_limit['reset']
                current_time = int(time.time())
                sleep_time = max(reset_time - current_time + 1, 1)
                logging.warning(f'GitHub API rate limit reached. Sleeping for {sleep_time} seconds.')
                time.sleep(sleep_time)
                yield next(gen_back)
            else:
                logging.error(f'HTTP Error: {e}')
                raise

def perform_search(query):
    url = f'{gh_url}/search/code?q={query}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get('items', [])

def search(repo_to_search=None, user_to_search=None, gh_dorks_file=None, output_filename=None):
    if gh_dorks_file is None:
        for path_prefix in ['.', os.path.join(prefix, 'github-dorks/')]:
            filename = os.path.join(path_prefix, 'github-dorks.txt')
            if os.path.isfile(filename):
                gh_dorks_file = filename
                break
    if not os.path.isfile(gh_dorks_file):
        raise Exception('Error: Invalid path for dorks file')

    with open(gh_dorks_file, 'r') as dork_file:
        if output_filename:
            with open(output_filename, 'w') as outputFile:
                outputFile.write('Issue Type (Dork), Text Matches, File Path, Score/Relevance, URL of File\n')

        for dork in dork_file:
            dork = dork.strip()
            if not dork or dork.startswith(('#', ';')):
                continue
            addendum = f' repo:{repo_to_search}' if repo_to_search else f' user:{user_to_search}' if user_to_search else ''
            dork_query = dork + addendum

            try:
                results = perform_search(dork_query)
                for result in results:
                    result_data = {
                        'dork': dork,
                        'text_matches': result.get('text_matches'),
                        'path': result['path'],
                        'score': result.get('score', 'N/A'),
                        'url': result['html_url']
                    }
                    output = f'{result_data["dork"]}, {result_data["text_matches"]}, {result_data["path"]}, {result_data["score"]}, {result_data["url"]}\n'
                    if output_filename:
                        outputFile.write(output)
                    else:
                        logging.info(output.strip())
            except Exception as e:
                logging.error(f'Error searching for dork "{dork}": {e}')

def monit(gh_dorks_file=None, active_monit=None, refresh_time=60):
    if gh_user is None:
        raise Exception('Error: GitHub user environment variable is required.')
    logging.info('Monitoring user private feed for new code to be dorked.')
    items_history = set()
    gh_private_feed = f"https://github.com/{gh_user}.private.atom?token={active_monit}"
    while True:
        feed = feedparser.parse(gh_private_feed)
        for item in feed['items']:
            if 'merged pull' in item['title'] and item['title'] not in items_history:
                search(user_to_search=item['author_detail']['name'], gh_dorks_file=gh_dorks_file)
                items_history.add(item['title'])
        logging.info('Waiting for new items...')
        time.sleep(refresh_time)

def metasearch(repo_to_search=None, user_to_search=None, gh_dorks_file=None, active_monit=None, output_filename=None, refresh_time=60):
    if active_monit is None:
        search(repo_to_search, user_to_search, gh_dorks_file, output_filename)
    else:
        monit(gh_dorks_file, active_monit, refresh_time)

def main():
    parser = argparse.ArgumentParser(description='Search GitHub for dorks', epilog='Use responsibly, Enjoy pentesting')

    parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.1.1')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-u', '--user', dest='user_to_search', help='GitHub user/org to search within. Eg: techgaun')
    group.add_argument('-r', '--repo', dest='repo_to_search', help='GitHub repo to search within. Eg: techgaun/github-dorks')
    parser.add_argument('-d', '--dork', dest='gh_dorks_file', help='GitHub dorks file. Eg: github-dorks.txt')
    group.add_argument('-m', '--monit', dest='active_monit', help='Monitors GitHub user private feed with feed token')
    parser.add_argument('-o', '--outputFile', dest='output_filename', help='CSV File to write results to. Eg: out.csv')

    args = parser.parse_args()
    metasearch(
        repo_to_search=args.repo_to_search,
        user_to_search=args.user_to_search,
        gh_dorks_file=args.gh_dorks_file,
        active_monit=args.active_monit,
        output_filename=args.output_filename
    )

if __name__ == '__main__':
    main()
