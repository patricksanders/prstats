#!/usr/bin/env python

from collections import defaultdict
from json import dumps
from os import getenv
from os import makedirs

from github3 import GitHub
from github3 import GitHubEnterprise
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

from config import GH_TOKEN
from config import GH_URL
from config import REPOS

mpl.use('TkAgg')
GH_TOKEN = GH_TOKEN or getenv('GH_TOKEN')


def main():
    if GH_URL:
        gh = GitHubEnterprise(GH_URL, token=GH_TOKEN)
    else:
        gh = GitHub(token=GH_TOKEN)

    for org_name, repo_name in REPOS:
        analyze_repo(gh, org_name, repo_name)


def analyze_repo(gh, org_name, repo_name):
    output_dir = make_output_dir(org_name, repo_name)
    repo_slug = '{}/{}'.format(org_name, repo_name)
    print('fetching PRs for {}/{}'.format(org_name, repo_name))
    pulls = get_pulls(gh, org_name, repo_name)
    coll = build_collection(pulls)
    print('plot time!')
    get_plots(coll, output_dir, repo_slug)
    plot_users(coll['user'], output_dir, repo_slug)
    stats = get_stats(coll)
    with open(output_dir + '/stats.txt', 'w') as file:
        file.write(dumps(stats, indent=4))
    print('completed analysis for {}/{}'.format(org_name, repo_name))


def build_collection(pulls):
    coll = defaultdict(list)
    coll['user'] = defaultdict(int)
    for p in pulls:
        coll['additions_count'].append(p.additions_count)
        coll['deletions_count'].append(p.deletions_count)
        coll['comments_count'].append(p.comments_count + p.review_comments_count)
        coll['commits_count'].append(p.commits_count)
        coll['user'][p.user.login] += 1
    return coll


def get_stats(coll):
    stats = {}
    percentiles = (25, 50, 75, 90, 95)
    for key, value in coll.items():
        if isinstance(value, list):
            stats[key] = {str(p): int(np.percentile(value, p)) for p in percentiles}
        else:
            stats[key] = value
    return stats


def get_plots(coll, output_path, repo_slug):
    for key, value in coll.items():
        if isinstance(value, list):
            print('making plot for', key)
            plt.figure()
            plt.title('{} {}'.format(repo_slug, key))
            plt.plot(value)
            plt.ylabel(key)
            plt.xlabel('PR Number')
            plt.savefig('{}/plots/{}.png'.format(output_path, key))


def make_output_dir(org_name, repo_name):
    base_path = 'output/{}/{}'.format(org_name, repo_name)
    try:
        makedirs(base_path + '/plots')
    except FileExistsError:
        pass
    return base_path


def plot_users(users, output_path, repo_slug):
    print('making plot for pr_count')
    names = users.keys()
    pr_counts = users.values()
    y_pos = np.arange(len(names))
    plt.figure()
    plt.title('{} pr_count'.format(repo_slug))
    plt.bar(y_pos, pr_counts)
    plt.ylabel('PR Count')
    plt.xticks(y_pos, names)
    plt.savefig('{}/plots/pr_count.png'.format(output_path))


def get_pulls(gh, owner, repo, fault_tolerance=1):
    count = 1
    while True:
        pull = gh.pull_request(owner, repo, count)
        if pull:
            count += 1
            yield pull
        elif fault_tolerance > 0:
            count += 1
            fault_tolerance -= 1
        else:
            break


if __name__ == '__main__':
    main()
