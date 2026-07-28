FROM node:22-alpine AS frontend-deps
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .

FROM frontend-deps AS test
RUN npm test

FROM frontend-deps AS build
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
