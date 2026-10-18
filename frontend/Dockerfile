FROM node:24-alpine AS build
WORKDIR /workspace/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
COPY scripts/ /workspace/scripts/
COPY distribution/windows/ /workspace/distribution/windows/
COPY backend/ /workspace/backend/
COPY helper.env.example compose.helper.yaml /workspace/
ARG QUERYLAB_FRONTEND_MODE=production
RUN npm run build -- --mode ${QUERYLAB_FRONTEND_MODE}
FROM nginx:1.28-alpine
ARG NGINX_CONFIG=nginx.conf
COPY frontend/${NGINX_CONFIG} /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/frontend/dist /usr/share/nginx/html
EXPOSE 80
