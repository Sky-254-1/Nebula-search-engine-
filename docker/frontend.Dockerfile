FROM node:20-alpine AS build
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM nginx:1.25-alpine
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY frontend/legacy /usr/share/nginx/html/legacy
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
RUN addgroup -S nginx || true && adduser -S nginx -G nginx || true && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && chown nginx:nginx /var/run/nginx.pid
USER nginx
EXPOSE 80/tcp
