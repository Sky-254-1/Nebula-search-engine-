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
