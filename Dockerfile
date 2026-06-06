# syntax=docker/dockerfile:1

FROM node:20-bookworm-slim

# Install Python and minimal dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create virtual environment and install requirements
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY binance_bot/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Node dependencies
COPY package*.json ./
RUN npm install

# Copy all source files
COPY . .

# Generate Prisma Client and build NestJS app
RUN npx prisma generate
RUN npm run build

# Make start script executable
RUN chmod +x start.sh

ENV NODE_ENV=production
EXPOSE 3000

CMD ["./start.sh"]