# polaris-slack
Slack integration for Synopsys Coverity on Polaris

The functionality of this script is to alert on new issues in any Polaris project that a service account has access to.

But you are in charge of running this script after your normal Polaris snapshot process.

## Required Environment Variables

|VariableName|Type|Example|
|---|---|---|
|POLARIS_URI|Uri|`http://example.polaris.synopsys.com/`|
|POLARIS_TOKEN|string|`examplepolaritoken`|
|SLACK_WEBHOOK_URI|Uri|`https://hooks.slack.com/services/XXXX/YYYY/zzzzz`|

## Usage with docker

```bash
docker build -t polaris-slack:example
docker run -e POLARIS_URL -e POLARIS_TOKEN -e SLACK_WEBHOOK_URL polaris-slack:example
```

## Usage from cli 

### Bash
```bash
python3 -m venv venv
source venv/Scripts/activate
python3 -m pip install -r requirements.txt
python3 main.py
```

### Powershell
```powershell
python3 -m venv venv
./venv/Scripts/Activate.ps1
python3 -m pip install -r requirements.txt
python3 main.py
``` 

## Example Output

![Example Output](/example.png?raw=true "Example Output")
