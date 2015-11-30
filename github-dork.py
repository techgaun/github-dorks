#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import github3 as github
import os
import argparse


gh_user = os.getenv('GH_USER', None)
gh_pass = os.getenv('GH_PWD', None)
gh_token = os.getenv('GH_TOKEN', None)

gh = github.GitHub(username=gh_user, password=gh_pass, token=gh_token)


def search(repo_to_search=None, user_to_search=None, gh_dorks_file=None):
    if gh_dorks_file is None:
        gh_dorks_file = 'github-dorks.txt'
    if not os.path.isfile(gh_dorks_file):
        raise Exception('Error, the dorks file path is not valid')

    found = False
    with open(gh_dorks_file, 'r') as dork_file:
        for dork in dork_file:
            dork = dork.strip()
            if not dork or dork[0] in '#;':
                continue
            addendum = ''
            if repo_to_search is not None:
                addendum = ' repo:' + repo_to_search
            elif user_to_search is not None:
                addendum = ' user:' + user_to_search

            dork = dork + addendum
            search_results = gh.search_code(dork)
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
                    result = '\n'.join([
                        'Found result for {dork}',
                        'Text matches: {text_matches}',
                        'File path: {path}',
                        'Score/Relevance: {score}',
                        'URL of File: {url}',
                        ''
                    ]).format(**fmt_args)
                    print(result)
            except github.exceptions.ForbiddenError as e:
                print(e)
                return
                # need to retry in case of API rate limit reached
                # not done yet
            except github.exceptions.GitHubError as e:
                print('GitHubError encountered on search of dork: ' + dork)
                print(e)
                return
            except Exception as e:
                print('Error encountered on search of dork: ' + dork)

    if not found:
        print('No results for your dork search' + addendum + '. Hurray!')


def main():
    parser = argparse.ArgumentParser(
        description='Search github for github dorks',
        epilog='Use responsibly, Enjoy pentesting'
    )

    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-u',
        '--user',
        dest='user_to_search',
        action='store',
        help='Github user/org to search within. Eg: techgaun'
    )

    group.add_argument(
        '-r',
        '--repo',
        dest='repo_to_search',
        action='store',
        help='Github repo to search within. Eg: techgaun/github-dorks'
    )

    parser.add_argument(
        '-d',
        '--dork',
        dest='gh_dorks_file',
        action='store',
        help='Github dorks file. Eg: github-dorks.txt'
    )

    args = parser.parse_args()
    search(
        repo_to_search=args.repo_to_search,
        user_to_search=args.user_to_search,
        gh_dorks_file=args.gh_dorks_file
    )

if __name__ == '__main__':
    main()
