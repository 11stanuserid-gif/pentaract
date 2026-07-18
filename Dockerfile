FROM rust:1.75 as builder

WORKDIR /app
COPY ./Pentaract/pentaract/ .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/pentaract /pentaract
COPY ./docker-entrypoint.sh /docker-entrypoint.sh
COPY ./config.dat /app/config.dat
RUN chmod +x /docker-entrypoint.sh

EXPOSE 7860
ENTRYPOINT ["/docker-entrypoint.sh"]
