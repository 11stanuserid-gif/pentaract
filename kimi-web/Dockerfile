FROM python:3.11-alpine

RUN pip install --no-cache-dir kimi-code==1.49.0

EXPOSE 10000

CMD ["kimi", "web", "--host", "0.0.0.0", "--port", "10000", "--dangerously-omit-auth"]
