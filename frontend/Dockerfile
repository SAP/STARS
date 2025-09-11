FROM nginxinc/nginx-unprivileged

# Use default Nginx config (listens on port 8080)
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built Angular application
COPY ./dist/stars /usr/share/nginx/html

# Copy the config generation script
COPY ./generate-config.sh /usr/local/bin/generate-config.sh

# Make the script executable and create config directory with proper permissions
USER root
RUN chmod +x /usr/local/bin/generate-config.sh && \
    mkdir -p /usr/share/nginx/html/assets/configs && \
    chown -R nginx:nginx /usr/share/nginx/html/assets/configs
USER nginx

# Set environment variables with default values
ENV BACKEND_URL=http://localhost:8080
ENV BACKEND_WS_URL=ws://localhost:8080/agent
ENV API_URL=http://localhost:8080

EXPOSE 8080

# Use the script as entrypoint to generate config before starting nginx
ENTRYPOINT ["/usr/local/bin/generate-config.sh"]
CMD ["nginx", "-g", "daemon off;"]
