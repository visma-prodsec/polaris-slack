from slack_sdk.webhook import WebhookClient
from slack_sdk.models.blocks import SectionBlock, MarkdownTextObject, HeaderBlock, DividerBlock, TextObject


class Slack:
    slack_message = []
    severity_colors = {
        "Audit": ":large_white_square:",
        "Low": ":large_yellow_square:",
        "Medium": ":large_orange_square:",
        "High": ":large_red_square:"
    }

    def __init__(self, webhook_url):
        self.webhook = WebhookClient(webhook_url)

    def appendOrSend(self, block):
        if len(self.slack_message) >= 50:
            response = self.webhook.send(
                text="fallback",
                blocks=self.slack_message
            )
            self.slack_message = []
        self.slack_message.append(block)

    def flush(self):
        response = self.webhook.send(
            text="fallback",
            blocks=self.slack_message
        )

    def GetIssueCount(self, issues):
        issue_counts = {}

        for issue in issues:
            if not issue['severity'] in issue_counts:
                issue_counts[issue['severity']] = 1
            else:
                issue_counts[issue['severity']] += 1

        return issue_counts

    def SendSummaryPerProjects(self, normalized_projects, filter):
        total_issues = 0

        for project in normalized_projects:
            total_issues += len(project['issues'])

        issue_descriptions = []

        if filter.get('only-security'):
            issue_descriptions += ["security"]

        if filter.get('only-untriaged'):
            issue_descriptions += ["untriaged"]

        issue_description = ' '.join(issue_descriptions)

        self.appendOrSend(SectionBlock(
            text=MarkdownTextObject(text=f"{total_issues} {issue_description} issues in {len(normalized_projects)} polaris projects")))

        for project in normalized_projects:
            issues = project['issues']
            issue_counts = self.GetIssueCount(issues)

            fields = []
            for issue_severity, issue_count in issue_counts.items():
                fields.append(MarkdownTextObject(text=f"{self.severity_colors[issue_severity]}{issue_severity}: {issue_count}"))

            block = SectionBlock(text=MarkdownTextObject(text=f"*<{project['direct-link']}|{project['project_name']}>*",verbatim=False), fields=fields)

            self.appendOrSend(block)

        self.flush()

    def SendAllIssuesInProjects(self, normalized_projects):
        total_issues = 0

        for project in normalized_projects:
            total_issues += len(project['issues'])

        self.appendOrSend(SectionBlock(text=MarkdownTextObject(text=f"{total_issues} issues in {len(normalized_projects)} polaris projects")))

        for project in normalized_projects:
            issues = project['issues']
            self.appendOrSend(HeaderBlock(text=TextObject(subtype='plain_text',text=project['project_name'])))
            self.appendOrSend(SectionBlock(text=MarkdownTextObject(text=f"{len(issues)} issues")))
            last_severity = None
            last_issue_type = None
            for issue in issues:
                severity = issue['severity']

                issue_type = issue['sub-tool']
                if last_severity != severity:
                    self.appendOrSend(SectionBlock(text=TextObject(subtype='plain_text', text=f'Severity: {severity}')))
                    self.appendOrSend(DividerBlock())
                    last_severity = severity
                if last_issue_type != issue_type:
                    self.appendOrSend(SectionBlock(text=MarkdownTextObject(text=f'_{issue_type}_')))
                    self.appendOrSend(DividerBlock())
                    last_issue_type = issue_type
                self.appendOrSend(SectionBlock(text=MarkdownTextObject(text=f"<{issue['direct-link']}|{issue['path']}>", verbatim=False)))

        self.flush()
