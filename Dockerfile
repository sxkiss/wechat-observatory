FROM node:20-alpine AS web-build

WORKDIR /src/web/admin
COPY web/admin/package*.json ./
RUN npm ci
COPY web/admin ./
RUN npm run build

FROM golang:1.24.2-alpine AS build

ARG GOPROXY=https://goproxy.cn,direct
ENV GOPROXY=${GOPROXY}

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
COPY --from=web-build /src/internal/bridge/admin_dist ./internal/bridge/admin_dist
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/wechat-observatory ./cmd/bridge
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /out/wechat-observatory-db ./cmd/bridge-db

FROM alpine:3.21

RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories \
	&& apk add --no-cache ca-certificates wget
RUN adduser -D -H -u 10001 appuser \
	&& mkdir -p /var/lib/wechat-observatory/media /usr/share/wechat-observatory/docs \
	&& chown -R appuser:appuser /var/lib/wechat-observatory
COPY --from=build /out/wechat-observatory /usr/local/bin/wechat-observatory
COPY --from=build /out/wechat-observatory-db /usr/local/bin/wechat-observatory-db
COPY --from=build /src/docs/api.md /usr/share/wechat-observatory/docs/api.md
COPY --from=build /src/docs/adapter-quickstart-v1.md /usr/share/wechat-observatory/docs/adapter-quickstart-v1.md
COPY --from=build /src/docs/capability-evidence-v1.md /usr/share/wechat-observatory/docs/capability-evidence-v1.md
COPY --from=build /src/docs/protocol-capability-review-2026-07-03.md /usr/share/wechat-observatory/docs/protocol-capability-review-2026-07-03.md
COPY --from=build /src/docs/protocol-stability-review-v1.md /usr/share/wechat-observatory/docs/protocol-stability-review-v1.md
COPY --from=build /src/docs/public-api-errors-v1.md /usr/share/wechat-observatory/docs/public-api-errors-v1.md
COPY --from=build /src/docs/public-api-message-samples-v1.md /usr/share/wechat-observatory/docs/public-api-message-samples-v1.md
COPY --from=build /src/docs/public-api-python-client-v1.md /usr/share/wechat-observatory/docs/public-api-python-client-v1.md

USER appuser
EXPOSE 8088
ENTRYPOINT ["/usr/local/bin/wechat-observatory"]
