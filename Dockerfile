# Stage 1: Build the VueJS frontend
FROM node:22-alpine AS frontend-builder

# Set working directory
WORKDIR /app/frontend

# Copy frontend source code
COPY frontend/package*.json ./
COPY frontend/ ./

# Install dependencies and build the VueJS app
RUN npm install && npm run build

# Stage 2: Set up Flask backend with Nginx to serve the front-end and API
FROM python:3.11-slim

# Install required dependencies
RUN apt-get update && apt-get install -y nginx curl gzip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy backend source code
COPY backend/ /app/backend

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy VueJS built files from the first stage
COPY --from=frontend-builder /app/frontend/dist /var/www/html

# Configure Nginx
RUN rm /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/sites-available/vuejs-flask
RUN ln -s /etc/nginx/sites-available/vuejs-flask /etc/nginx/sites-enabled/

# Expose ports for Flask API and Nginx
EXPOSE 80

# Command to start Nginx and Flask
CMD service nginx start && python /app/backend/app.py
