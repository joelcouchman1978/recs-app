FROM node:20-alpine
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.6.0 --activate
COPY package.json pnpm-lock.yaml* .npmrc* /app/
RUN pnpm install --frozen-lockfile || true
COPY . /app
EXPOSE 3000
CMD ["pnpm", "dev"]

