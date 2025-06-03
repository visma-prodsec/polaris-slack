import requests
import urllib
import math
import aiohttp
import asyncio
import time

import json

ISSUE_SEVERITY_RANKS = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
    "Audit": 4
}

class Polaris:
    def __init__(self, url, token, retries, wait_seconds):
        self._baseurl = url
        self._client = requests.Session()
        self._retries = retries
        self._wait_seconds = wait_seconds
        self._jwt = self.getJwt(token)

    def __del__(self):
        self._client.close()

    def _getHeaders(self):
        headers = {'Content-Type': 'application/vnd.api+json', 'Accept': 'application/vnd.api+json',
                   'Authorization': f'Bearer {self._jwt}'}
        return headers

    def getFullUrl(self, path):
        return urllib.parse.urljoin(self._baseurl, path)

    def getJwt(self, token):
        auth_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        auth_params = {'accesstoken': token}

        for attempt in range(self._retries):
            try:
                response = self._client.post(
                    self.getFullUrl('/api/auth/authenticate'),
                    headers=auth_headers,
                    data=auth_params
                )
                if response.status_code == 200:
                    json_payload = response.json()
                    return json_payload['jwt']
                else:
                    raise Exception(f"HTTP {response.status_code}")
            except Exception as e:
                if attempt < self._retries - 1:
                    print(f"Warning: Failed to authenticate with Polaris ({e}). Retrying in {self._wait_seconds} seconds...", flush=True)
                    time.sleep(self._wait_seconds)
                else:
                    print(f"Failed to authenticate after {self._retries} attempts. Last error: {e}", flush=True)
                    raise RuntimeError(
                        f"Failed: Unexpected response from Polaris after {self._retries} attempts (HTTP {getattr(response, 'status_code', 'N/A')})"
                    )
        return None

    def GetApplication(self, application_id):
        url = self.getFullUrl(f'/api/common/v0/applications/{application_id}')
        return self._request_with_retries("GET", url, headers=self._getHeaders())

    def GetProjectsFromApplication(self, application_id):
        url = self.getFullUrl('/api/common/v0/projects') + f'?page[limit]=500&application-id={application_id}&include[project][]=branches&include[project][]=runs'
        return self._request_with_retries("GET", url, headers=self._getHeaders())

    def GetProjectsByCustomProperty(self, **kwargs):
        custom_properties = "&".join("filter[project][properties][{}][$eq]={}".format(*i) for i in kwargs.items())
        url = self.getFullUrl('/api/common/v0/projects') + f'?page[limit]=500&{custom_properties}&include[project][]=branches&include[project][]=runs'
        return self._request_with_retries("GET", url, headers=self._getHeaders())

    def _getProjects(self):
        url = self.getFullUrl('/api/common/v0/projects') + '?page[limit]=500&include[project][]=branches&include[project][]=runs'
        return self._request_with_retries("GET", url, headers=self._getHeaders())

    async def _getPaginatedIssuePage(self, session, project_id, branch_id, limit, offset, filter):
        query_args = [
            f"page[limit]={limit}",
            f"page[offset]={offset}",
            f"project-id={project_id}",
            f"branch-id={branch_id}",
            "filter[issue][status][$eq]=opened",
            "filter[issue][dismissed][$eq]=false",
            "include[issue][]=severity",
            "include[issue][]=issue-kind",
        ]

        if filter.get('only-security', False):
            query_args += ["filter[issue][taxonomy][taxonomy-type][issue-kind][taxon][$eq]=security"]

        if filter.get('only-untriaged', False):
            query_args += ["filter[issue][triage-status][$eq]=not-triaged"]

        request_url = self.getFullUrl('/api/query/v1/issues' + '?' + '&'.join(query_args))
        for attempt in range(self._retries):
            async with session.get(request_url, headers=self._getHeaders()) as response:
                try:
                    return await response.json()
                except Exception:
                    if attempt < self._retries - 1:
                        print(f"Warning: Unexpected response from Polaris (HTTP {response.status}). Retrying in {self._wait_seconds} seconds...", flush=True)
                        await asyncio.sleep(self._wait_seconds)
                    else:
                        raise RuntimeError(
                            f"Failed: Unexpected response from Polaris after {self._retries} attempts (HTTP {response.status})"
                        )

    async def _getPaginatedIssues(self, session, project_id, branch_id, filter):
        first_page = await self._getPaginatedIssuePage(session, project_id, branch_id, 500, 0, filter)
        yield first_page

        total = first_page['meta']['total']
        limit = first_page['meta']['limit']

        if total > len(first_page['data']):
            for page in range(1, math.ceil(total/limit)):
                yield self._getPaginatedIssuePage(session, project_id, branch_id, limit, page*limit, filter)


    async def _getProjectIssues(self, session, project_id, branch_id, filter):
        data = []
        included = []
        pages = self._getPaginatedIssues(session, project_id, branch_id, filter)
        try:
            async for page in pages:
                page_data = page['data']
                page_included = page['included']
                data.extend(page_data)
                included.extend(page_included)
        finally:
            pages.aclose()

        return {
            'data': data,
            'included': included
        }

    def FormatIssueUrl(self, project_id, branch_id, revision_id, issue_id):
        return self.getFullUrl(f'/projects/{project_id}/branches/{branch_id}/revisions/{revision_id}/issues/{issue_id}')

    def FormatProjectUrl(self, project_id, branch_id, filter):
        filters = [
            "issue[status][$eq]=opened",
        ]

        if filter['only-security']:
            filters += ["issue[taxonomy][taxonomy-type][issue-kind][taxon][$eq]=security"]

        if filter['only-untriaged']:
            filters += ["issue[triage-status][$eq]=not-triaged"]

        filter_as_query = urllib.parse.quote('&'.join(filters))
        return self.getFullUrl(f"/projects/{project_id}/branches/{branch_id}/issues?filter={filter_as_query}")

    async def _NormalizedProjectAndIssues(self, session, runs, project_id, branch_id, project_name, filter):
        issues = await self._getProjectIssues(session, project_id, branch_id, filter)

        data = issues['data']
        if len(data) > 0:
            print(project_name, flush=True)
            untriaged_filter = filter.copy()
            untriaged_filter['only-untriaged'] = True
            return {
                'project_name': project_name,
                'project_id': project_id,
                'branch_id': branch_id,
                'direct-link': self.FormatProjectUrl(project_id, branch_id, filter),
                'direct-link-untriaged': self.FormatProjectUrl(project_id, branch_id, untriaged_filter),
                'issues': self.NormalizeIssues(data, issues['included'], runs, project_id, branch_id)
            }

    def GetProjectsAndIssues(self, filter = None):
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(self._GetProjectsAndIssues(filter))
        return results

    async def _GetProjectsAndIssues(self, filter):
        projects = self._getProjects()

        project_include = []
        runs = []

        for include in projects['included']:
            if include['type'] == 'branch' and include['attributes']['main-for-project']:
                branch_id = include['id']
                project_id = include['relationships']['project']['data']['id']
                project_name = [x for x in projects['data'] if x['id'] == project_id][0]['attributes']['name']

                project_include.append({'project_id': project_id, 'branch_id': branch_id, 'project_name': project_name})
            elif include['type'] == 'run':
                runs.append(include)

        project_with_issues = []

        async with aiohttp.ClientSession() as session:
            project_with_issues = await asyncio.gather(*[self._NormalizedProjectAndIssues(session, runs, projectandinclude['project_id'], projectandinclude['branch_id'], projectandinclude['project_name'], filter) for projectandinclude in project_include])

        # Remove None from list, None represents projects that didn't have any issues
        project_with_issues = [x for x in project_with_issues if x is not None]

        return sorted(project_with_issues, key=lambda x: x['project_name'])

    def NormalizeIssue(self, issue, project_id, branch_id):
        normalize_data = {}

        normalize_data['severity'] = issue['severity']['name']
        normalize_data['issue-kind'] = issue['issue-kind']['name']
        normalize_data['issue-type'] = issue['issue-type']['issue-type']
        normalize_data['issue-type-name'] = issue['issue-type']['name']
        normalize_data['id'] = issue['id']
        normalize_data['path'] = issue['path']
        normalize_data['type'] = issue['type']
        normalize_data['finding-id'] = issue['attributes']['finding-key']
        normalize_data['issue-key'] = issue['attributes']['issue-key']
        normalize_data['sub-tool'] = issue['attributes']['sub-tool']
        normalize_data['revision-id'] = issue['attributes']['revision-id']
        normalize_data['latest-observed-on-run'] = issue['attributes']['latest-observed-on-run']
        normalize_data['direct-link'] = self.FormatIssueUrl(project_id, branch_id, normalize_data['revision-id'], normalize_data['id'])

        return normalize_data

    def NormalizeIssueRelationshipValues(self, normalized_data, relationship_key, value):
        unique_keys = ['issue-type', 'issue-kind', 'latest-observed-on-run', 'path', 'severity']

        normalized_data[relationship_key] = value
        if 'attributes' in value[0]:
            if relationship_key in unique_keys:
                if relationship_key == 'latest-observed-on-run':
                    normalized_data['attributes'][relationship_key] = value[0]['id']
                    normalized_data['attributes']['revision-id'] = \
                        value[0]['relationships']['revision']['data']['id']
                elif relationship_key == 'path' and value[0]['attributes']['path-type'] == 'unknown':
                    normalized_data[relationship_key] = '/'.join(value[0]['attributes'][relationship_key])
                else:
                    normalized_data[relationship_key] = value[0]['attributes']

        return normalized_data

    def NormalizeIssues(self, data, included, runs, project_id, branch_id):
        issues = []

        for issue in data:
            normalized_data = {}

            for key, value in issue.items():
                if key == 'relationships':
                    continue  # yeet
                normalized_data[key] = value

            for relationship_key, relationship_value in issue['relationships'].items():
                if relationship_key == 'transitions':
                    continue  # nope
                if 'data' not in relationship_value or not relationship_value['data']:
                    continue

                relationship_type = relationship_value['data']['type']
                relationship_id = relationship_value['data']['id']

                if relationship_key == 'latest-observed-on-run':
                    value = [x for x in runs if x['type'] == relationship_type and x['id'] == relationship_id]
                else:
                    value = [x for x in included if x['type'] == relationship_type and x['id'] == relationship_id]

                if len(value) > 0:
                    normalized_data = self.NormalizeIssueRelationshipValues(normalized_data, relationship_key, value)
                #else:
                #    print(f'{relationship_key} couldn\'t be found')

            issues.append(self.NormalizeIssue(normalized_data, project_id, branch_id))

        # Sort by severity rank, issue-type and path
        return sorted(issues, key=lambda x: (int(ISSUE_SEVERITY_RANKS[x['severity']]), x['issue-type'], x['path']))

    def _request_with_retries(self, method, url, **kwargs):
        for attempt in range(self._retries):
            response = self._client.request(method, url, **kwargs)
            try:
                return response.json()
            except Exception:
                if attempt < self._retries - 1:
                    print(f"Warning: Unexpected response from Polaris (HTTP {response.status_code}). Retrying in {wait_seconds} seconds...", flush=True)
                    time.sleep(self._wait_seconds)
                else:
                    raise RuntimeError(
                        f"Failed: Unexpected response from Polaris after {self._retries} attempts (HTTP {response.status_code})"
                    )
