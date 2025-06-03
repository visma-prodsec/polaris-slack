import json
import logging
import sys
from os import environ

from polaris import Polaris
from slack import Slack
from google import Google

logger = logging.getLogger('polaris-slack')

def main():
    try:
        polaris_url = environ.get('POLARIS_URL')
        token = environ.get('POLARIS_TOKEN')
        retries = int(environ.get('POLARIS_RETRIES', 1))  # Default to 1 if not set
        wait_seconds = int(environ.get('POLARIS_WAIT_SECONDS', 60))  # Default to 60 if not set

        if not polaris_url:
            logger.critical("Environment variable POLARIS_URL is unset")
        if not token:
            logger.critical("Environment variable POLARIS_TOKEN is unset")
        if not polaris_url or not token:
            exit(1)

        slack_webhook_url = environ.get('SLACK_WEBHOOK_URL')
        google_spaces_url = environ.get('GOOGLE_SPACES_URL')
        if (not slack_webhook_url) and (not google_spaces_url):
            logger.warning("Environment SLACK_WEBHOOK and GOOGLE_SPACES_URL is unset, just outputting issues to console.")

        polaris = Polaris(polaris_url, token, retries=retries, wait_seconds=wait_seconds)

        filter = {
            'only-security': environ.get('POLARIS_FILTER_ONLY_SECURITY'),
            'only-untriaged': environ.get('POLARIS_FILTER_ONLY_UNTRIAGED'),
        }
        filter_untriaged = filter.copy()
        filter_untriaged['only-untriaged'] = True

        projects_with_issues = polaris.GetProjectsAndIssues(filter)

        if slack_webhook_url:
            slack = Slack(slack_webhook_url)
            slack.SendSummaryPerProjects(projects_with_issues, filter)
        elif google_spaces_url:
            projects_with_untriaged_issues = polaris.GetProjectsAndIssues(filter_untriaged)
            google = Google(google_spaces_url)
            google.SendSummaryMessage(projects_with_issues, projects_with_untriaged_issues, filter)
        else:
            print(json.dumps(projects_with_issues, indent=2))
    except Exception as e:
        print(f"Fatal error: {e}", flush=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
