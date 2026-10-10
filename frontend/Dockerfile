# Development image for the Vite dev server (docker compose `frontend` service).
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

RUN chown -R node:node /app
USER node

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
