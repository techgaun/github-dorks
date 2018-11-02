#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import github3 as github
import os
import argparse
import time
import feedparser
from copy import copy
from sys import stderr
from common import post_to_slack, get_logger

slack_channel = "#infra-scrum"
gh_user = os.getenv('GH_USER', None)
gh_pass = os.getenv('GH_PWD', None)
gh_token = os.getenv('GH_TOKEN', None)
gh_url = os.getenv('GH_URL', None)

if gh_url is None:
    gh = github.GitHub(username=gh_user, password=gh_pass, token=gh_token)
else:
    gh = github.GitHubEnterprise(
        url=gh_url, username=gh_user, password=gh_pass, token=gh_token)


def search_wrapper(gen):
    while True:
        gen_back = copy(gen)
        try:
            yield next(gen)
        except StopIteration:
            raise
        except github.exceptions.ForbiddenError as e:
            search_rate_limit = gh.rate_limit()['resources']['search']
            # limit_remaining = search_rate_limit['remaining']
            reset_time = search_rate_limit['reset']
            current_time = int(time.time())
            sleep_time = reset_time - current_time + 1
            stderr.write(
                'GitHub Search API rate limit reached. Sleeping for %d seconds.\n\n'
                % (sleep_time))
            time.sleep(sleep_time)
            yield next(gen_back)
        except Exception as e:
            raise e


def metasearch(repo_to_search=None,
               user_to_search=None,
               gh_dorks_file=None,
               active_monit=None,
               output_filename=None,
               refresh_time=60):
    if active_monit is None:
        search(repo_to_search, user_to_search, gh_dorks_file, active_monit, output_filename)
    else:
        monit(gh_dorks_file, active_monit, refresh_time)


def monit(gh_dorks_file=None, active_monit=None, refresh_time=60):
    if gh_user is None:
        raise Exception('Error, env Github user variable needed')
    else:
        print(
            'Monitoring user private feed searching new code to be dorked.' +
            'Every new merged pull request trigger user scan.'
        )
        print('-----')
        items_history = list()
        gh_private_feed = "https://github.com/{}.private.atom?token={}".format(
            gh_user, active_monit)
        while True:
            feed = feedparser.parse(gh_private_feed)
            for i in feed['items']:
                if 'merged pull' in i['title']:
                    if i['title'] not in items_history:
                        search(
                            user_to_search=i['author_detail']['name'],
                            gh_dorks_file=gh_dorks_file)
                        items_history.append(i['title'])
            print('Waiting for new items...')
            time.sleep(refresh_time)


def search(repo_to_search=None,
           user_to_search=None,
           gh_dorks_file=None,
           active_monit=None,
           output_filename=None):

    if gh_dorks_file is None:
        gh_dorks_file = 'github-dorks.txt'
    if not os.path.isfile(gh_dorks_file):
        raise Exception('Error, the dorks file path is not valid')
    if user_to_search:
        print("Scanning User: ", user_to_search)
    if repo_to_search:
        print("Scanning Repo: ", repo_to_search)
    found = False

    outputFile = None
    if output_filename:
        outputFile = open(output_filename, 'w')

    with open(gh_dorks_file, 'r') as dork_file:
        # Write CSV Header
        if outputFile:
            outputFile.write('Issue Type (Dork), Text Matches, File Path, Score/Relevance, URL of File\n')
        for dork in dork_file:
            dork = dork.strip()
            if not dork or dork[0] in '#;':
                continue
            addendum = ''
            if repo_to_search:
                addendum = ' repo:' + repo_to_search
            elif user_to_search:
                addendum = ' user:' + user_to_search

            dork = dork + addendum
            search_results = search_wrapper(gh.search_code(dork))
            try:
                for search_result in search_results:
                    found = True
                    fmt_args = {
                        'dork': dork,
                        'text_matches': search_result.text_matches,
                        'path': search_result.path,
                        'score': search_result.score,
                        'url': search_result.html_url
                    }

                    # Either write to file or print output
                    if outputFile:
                        outputFile.write('{dork}, {text_matches}, {path}, {score}, {url}\n'.format(**fmt_args))
                    else:
                        result = '\n'.join([
                            'Found result for {dork}',
                            'Text matches: {text_matches}', 'File path: {path}',
                            'Score/Relevance: {score}', 'URL of File: {url}', ''
                        ]).format(**fmt_args)
                        print(result)
                        post_to_slack(result, slack_channel)

            except github.exceptions.GitHubError as e:
                print('GitHubError encountered on search of dork: ' + dork)
                print(e)
                return
            except Exception as e:
                print(e)
                print('Error encountered on search of dork: ' + dork)

    if not found:
        print('No results for your dork search' + addendum + '. Hurray!')


def main():
    parser = argparse.ArgumentParser(
        description='Search github for github dorks',
        epilog='Use responsibly, Enjoy pentesting')

    parser.add_argument(
        '-v', '--version', action='version', version='%(prog)s 0.1.1')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-u',
        '--user',
        dest='user_to_search',
        action='store',
        help='Github user/org to search within. Eg: techgaun')

    group.add_argument(
        '-r',
        '--repo',
        dest='repo_to_search',
        action='store',
        help='Github repo to search within. Eg: techgaun/github-dorks')

    parser.add_argument(
        '-d',
        '--dork',
        dest='gh_dorks_file',
        action='store',
        help='Github dorks file. Eg: github-dorks.txt')

    group.add_argument(
        '-m',
        '--monit',
        dest='active_monit',
        action='store',
        help='Monitors Github user private feed with feed token'
    )

    parser.add_argument(
        '-o',
        '--outputFile',
        dest='output_filename',
        action='store',
        help='CSV File to write results to. This overwrites the file provided! Eg: out.csv'
    )

    args = parser.parse_args()
    metasearch(
        repo_to_search=args.repo_to_search,
        user_to_search=args.user_to_search,
        gh_dorks_file=args.gh_dorks_file,
        active_monit=args.active_monit,
        output_filename=args.output_filename)


if __name__ == '__main__':
    main()
