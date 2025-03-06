from docutils import nodes
from sphinx.util.docutils import SphinxDirective
import requests
from datetime import datetime
import pytz
import logging
from dotenv import load_dotenv
import os

load_dotenv()

GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
TARGET_TIMEZONE = pytz.timezone('America/Sao_Paulo')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChangelogNode(nodes.General, nodes.Element):
    pass

def visit_changelog_node(self, node):
    self.body.append(self.starttag(node, 'div', CLASS='changelog'))

def depart_changelog_node(self, node):
    self.body.append('</div>')

class ChangelogDirective(SphinxDirective):
    required_arguments = 0
    optional_arguments = 0
    option_spec = {
        'repo': str,
        'kind': str,
        'title': lambda x: x.lower() in ['true', '1', 'yes', 'on'],
        'desc': lambda x: x.lower() in ['true', '1', 'yes', 'on'],
        'commits': lambda x: x.lower() in ['true', '1', 'yes', 'on'],
        'date': lambda x: x.lower() in ['true', '1', 'yes', 'on'],
    }
    has_content = False

    def run(self):
        repo_url = self.options.get('repo')
        kind = self.options.get('kind', 'tag')
        show_title = self.options.get('title', True)
        show_desc = self.options.get('desc', True)
        show_commits = self.options.get('commits', True)
        show_date = self.options.get('date', True)

        if repo_url:
            changelog_html = fetch_changelog(repo_url, kind, show_title, show_desc, show_commits, show_date)
            raw_node = nodes.raw('', changelog_html, format='html')
            return [raw_node]
        else:
            return [nodes.paragraph(text='No repository URL provided.')]

def fetch_changelog(repo_url, kind, show_title, show_desc, show_commits, show_date):
    try:
        owner_repo = repo_url.split("github.com/")[1]
        if kind == 'release':
            api_url = f'https://api.github.com/repos/{owner_repo}/releases'
            response = requests.get(api_url, auth=(GITHUB_USERNAME, GITHUB_TOKEN))
            logger.debug(f"Release API URL: {api_url} - Status: {response.status_code}") 
        else:
            api_url = f'https://api.github.com/repos/{owner_repo}/tags'
        logger.debug(f"API URL: {api_url}")
        response = requests.get(api_url, auth=(GITHUB_USERNAME, GITHUB_TOKEN))
        logger.debug(f"API response status: {response.status_code}")
        response.raise_for_status()

        items = response.json()
        logger.debug(f"Fetched {len(items)} items")

        changelog_list = []
        for item in items:
            version = item.get('tag_name') if kind == 'release' else item.get('name')
            url = item.get('html_url') if kind == 'release' else f"https://github.com/{owner_repo}/tree/{version}"

            logger.debug(f"Processing {kind}: {version}")

            commits_text = "Not Displayed"
            date = "Unknown"
            if show_commits or (kind == 'tag' and show_date):
                commits_api_url = f'https://api.github.com/repos/{owner_repo}/commits?sha={version}'
                commits_response = requests.get(commits_api_url, auth=(GITHUB_USERNAME, GITHUB_TOKEN))
                logger.debug(f"Commits API response status for {version}: {commits_response.status_code}")
                commits_response.raise_for_status()
                commits = commits_response.json()
                logger.debug(f"Fetched {len(commits)} commits for {kind} {version}")

                if commits and show_date:
                    commit_date_str = commits[0]['commit']['author']['date']
                    date = format_date(commit_date_str, TARGET_TIMEZONE)

                if show_commits:
                    commits_details = [
                        f'<a href="https://github.com/{owner_repo}/commit/{commit["sha"]}">{commit["sha"][:7]}</a>'
                        for commit in commits
                    ]
                    commits_text = ', '.join(commits_details)

            entry = [
                f'<h3 class="changelog_title"><a href="{url}">{version}</a></h3>'
            ]
            if show_date and kind == 'release':
                release_date = item.get('published_at') or item.get('created_at', 'Unknown')
                entry.append(f'<p class="changelog_entries"><strong>date:</strong> {format_date(release_date, TARGET_TIMEZONE)}</p>')
            if show_date and kind == 'tag':
                entry.append(f'<p class="changelog_entries"><strong>date:</strong> {date}</p>')
            if show_title and 'name' in item:
                entry.append(f'<p class="changelog_entries"><strong>title:</strong> {item["name"]}</p>')
            if show_desc and kind == 'release':
                logger.debug(f"Release item: {item}")
                description = item.get('body', '').strip() or 'No description available'
                entry.append(f'<p class="changelog_entries"><strong>desc:</strong> {description}</p>')
            if show_desc and kind == 'tag':
                tags_api_url = f'https://api.github.com/repos/{owner_repo}/commits/{item["commit"]["sha"]}'
                tags_response = requests.get(tags_api_url, auth=(GITHUB_USERNAME, GITHUB_TOKEN))
                tags_response.raise_for_status()
                commit_details = tags_response.json()
                description = commit_details['commit']['message'].strip() or 'No description available' 
                entry.append(f'<p class="changelog_entries"><strong>desc:</strong> {description}</p>')
            if show_commits:
                entry.append(f'<p class="changelog_entries"><strong>commits:</strong> {commits_text}</p>')

            changelog_list.extend(entry)

        return '\n'.join(changelog_list)

    except requests.RequestException as e:
        logger.error(f"Network-related error fetching changelog: {e}")
        return f'Error fetching changelog: {str(e)}'
    except Exception as e:
        logger.error(f"Unexpected error fetching changelog: {e}")
        return f'Error fetching changelog: {str(e)}'

def format_date(date_str, timezone):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
        utc_date = pytz.utc.localize(date_obj)
        local_date = utc_date.astimezone(timezone)
        return local_date.strftime('%Y-%m-%d at %H:%M %z')
    except ValueError as ve:
        logging.error(f"Error formatting date: {ve}")
        return "Invalid date"


def setup(app):
    app.add_node(ChangelogNode,
                html=(visit_changelog_node, depart_changelog_node),
                latex=(visit_changelog_node, depart_changelog_node),
                text=(visit_changelog_node, depart_changelog_node))

    app.add_directive('changelog', ChangelogDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
