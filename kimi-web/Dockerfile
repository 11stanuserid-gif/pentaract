FROM alpine:3.19

RUN apk add --no-cache curl

# Install kimi v1.49.0 binary for aarch64
RUN curl -sL "https://github.com/MoonshotAI/kimi-cli/releases/download/1.49.0/kimi-1.49.0-aarch64-unknown-linux-gnu-onedir.tar.gz" \
    -o /tmp/kimi.tar.gz && \
    mkdir -p /opt/kimi && \
    tar xzf /tmp/kimi.tar.gz -C /opt/kimi && \
    rm /tmp/kimi.tar.gz && \
    find /opt/kimi -name kimi -type f | head -1 | xargs -I{} ln -sf {} /usr/local/bin/kimi && \
    kimi --version

EXPOSE 10000

CMD ["kimi", "web", "--host", "0.0.0.0", "--port", "10000", "--dangerously-omit-auth"]
