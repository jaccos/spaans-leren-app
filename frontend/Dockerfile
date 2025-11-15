# Frontend Dockerfile voor Spaans Leren App - Nginx variant
FROM nginx:alpine

# Verwijder default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy frontend HTML file
COPY index.html /usr/share/nginx/html/

# Expose port
EXPOSE 80

# Nginx runs in foreground by default
CMD ["nginx", "-g", "daemon off;"]
