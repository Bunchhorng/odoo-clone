FROM node:22-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5175
CMD ["sh", "-c", "npm ci --no-audit --no-fund && exec npm run dev"]
