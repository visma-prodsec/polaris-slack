import json
import logging
from os import environ

from polaris import Polaris
from slack import Slack

logger = logging.getLogger('polaris-slack')

def main():
    polaris_url = environ.get('POLARIS_URL')
    token = environ.get('POLARIS_TOKEN')

    if not polaris_url:
        logger.critical("Environment variable POLARIS_URL is unset")
    if not token:
        logger.critical("Environment variable POLARIS_TOKEN is unset")
    if not polaris_url or not token:
        exit(1)

    dry_run = False
    slack_webhook_url = environ.get('SLACK_WEBHOOK_URL')
    if not slack_webhook_url:
        logger.warning("Environment SLACK_WEBHOOK is unset, just outputting issues to console.")
        dry_run = True

    polaris = Polaris(polaris_url, token)
    slack = Slack(slack_webhook_url)

    projects_with_issues = polaris.GetProjectsAndIssues()

    if dry_run:
        print(json.dumps(projects_with_issues, indent=2))
    else:
        slack.SendSummaryPerProjects(projects_with_issues)

if __name__ == '__main__':
    main()