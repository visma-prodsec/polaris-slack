FROM python:3.12-slim

ENV POLARIS_URL ""
ENV POLARIS_TOKEN ""
ENV SLACK_WEBHOOK_URL ""

WORKDIR /polaris-slack/

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

COPY . .

CMD ["python3", "/polaris-slack/main.py"]