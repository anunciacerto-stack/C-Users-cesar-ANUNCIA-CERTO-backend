# syntax=docker/dockerfile:1

FROM node:20-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npx prisma generate

RUN npm run build

ENV NODE_ENV=production

EXPOSE 3000

CMD ["node","dist/main.js"]