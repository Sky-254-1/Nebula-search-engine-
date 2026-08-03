FROM node:20-alpine AS build
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm ci --omit=dev
COPY frontend/ .
RUN npm run build

FROM nginx:1.25-alpine
# Create non-root user with same UID/GID as nginx
RUN addgroup -S nginx 2>/dev/null || true && \
    adduser -S nginx -G nginx 2>/dev/null || true && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && chown nginx:nginx /var/run/nginx.pid

# Copy built frontend
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY frontend/legacy /usr/share/nginx/html/legacy
COPY docker/nginx.prod.conf /etc/nginx/conf.d/default.conf

# Set proper permissions
RUN chown -R nginx:nginx /usr/share/nginx/html

# Switch to non-root user
USER nginx

# Expose port
EXPOSE 80/tcp

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/health/live || exit 1

# Use dumb-init for proper signal handling
RUN apk add --no-cache dumb-init
ENTRYPOINT ["dumb-init", "--"]
CMD ["nginx", "-g", "daemon off;"]
