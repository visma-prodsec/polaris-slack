import requests
import json

def GroupIssuesByPriority(issues):
    issue_per_priority = {'Critical': [], 'High': [], 'Medium': [], 'Low': [], 'Audit': []}

    for issue in issues:
        if not issue['severity'] in issue_per_priority:
            issue_per_priority[issue['severity']] = [issue]
        else:
            issue_per_priority[issue['severity']] += [issue]

    return issue_per_priority

def WidgetForIssue(issue_info):

    untriaged_issues_count = len(issue_info['untriaged-issues'])
    untriaged_info = f"({untriaged_issues_count} not triaged)" if untriaged_issues_count > 0 else ""
    return {
        "decoratedText": {
            "text": f"{len(issue_info['issues'])} {issue_info['severity']} issues {untriaged_info}"
        }
    }

def SeverityToColor(severity):
    if severity == 'Critical' or severity == 'High':
        return {
          "red": 0.86,
          "green": 0.21,
          "blue": 0.27,
          "alpha": 1
        }
    elif severity == 'Medium':
        return {
          "red": 0.99,
          "green": 0.49,
          "blue": 0.08,
          "alpha": 1
        }
    else:
        return {
          "red": 1,
          "green": 0.76,
          "blue": 0.03,
          "alpha": 1
        }

class Google:

    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def _SummaryForProject(self, project):

        issues_per_priority = GroupIssuesByPriority(project['issues'])
        untriaged_issues_per_priority = GroupIssuesByPriority(project['untriaged-issues'])

        issues_by_severity = [
            {
                'severity': severity,
                'issues': issues,
                'untriaged-issues': untriaged_issues_per_priority.get(severity, [])
            }
            for (severity, issues) in issues_per_priority.items() if len(issues) > 0]

        max_issue_level = issues_by_severity[0]['severity']
        untriaged_issues = sum([len(info['untriaged-issues']) for info in issues_by_severity])

        link_to_issues = {
            "buttonList": {
              "buttons": [
                {
                  "text": "Go to issues",
                  "color": SeverityToColor(max_issue_level),
                  "onClick": {
                    "openLink": {
                      "url": project['direct-link']
                    }
                  }
                }
              ]
            }
        }

        if untriaged_issues > 0:
            link_to_issues['buttonList']['buttons'] += [
                {
                  "text": "Untriaged issues",
                 #"color": SeverityToColor(max_issue_level),
                  "onClick": {
                    "openLink": {
                      "url": project['direct-link-untriaged']
                    }
                  }
                }
            ]

        return {
            "header": project['project_name'],
            "widgets": list(map(WidgetForIssue, issues_by_severity)) +
                       [link_to_issues],
        }

    def SendSummaryMessage(self, normalized_projects, normalized_projects_only_untriaged, filter):
        total_issues = 0
        total_untriaged_issues = 0
        for project in normalized_projects:
            total_issues += len(project['issues'])

            same_projects = [other_project for other_project in normalized_projects_only_untriaged if other_project['project_id'] == project['project_id']]
            project['untriaged-issues'] = same_projects[0]['issues'] if len(same_projects) > 0 else []
            total_untriaged_issues += len(project['untriaged-issues'])

        summary = {
            "cardsV2": [
                {
                    "cardId": "unique-card-id",
                    "card": {
                        "header": {
                            "title": "Summary of polaris tickets",
                            "subtitle": f"There are {total_issues} issues in {len(normalized_projects)} projects. {total_untriaged_issues} issues need to be triaged"
                        },
                        "sections": list(map(self._SummaryForProject, normalized_projects))
                    }
                }
            ],
        }

        headers = {
            'Content-Type': 'application/json'
        }
        client = requests.Session()
        client.post(self.webhook_url, headers=headers, data=json.dumps(summary))
