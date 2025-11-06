FROM python:3.14-slim

RUN apt update && apt install -y ca-certificates && apt clean && rm -rf /var/lib/{apt,dpkg,cache,log}/

ENV POLARIS_URL ""
ENV POLARIS_TOKEN ""
ENV SLACK_WEBHOOK_URL ""

WORKDIR /polaris-slack/

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

COPY . .

CMD ["python3", "/polaris-slack/main.py"]
