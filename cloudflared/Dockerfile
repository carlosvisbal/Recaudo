FROM alpine:3.21
RUN apk add --no-cache ca-certificates \
    && adduser -D -u 65532 nonroot
COPY --from=cloudflare/cloudflared:latest /usr/local/bin/cloudflared /usr/local/bin/cloudflared
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh /usr/local/bin/cloudflared
USER 65532:65532
ENTRYPOINT ["/entrypoint.sh"]
