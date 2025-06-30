FROM nginxinc/nginx-unprivileged

# Use default Nginx config (listens on port 80)
# or update your nginx.conf to listen on 80 instead of 8080
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

COPY ./dist/stars /usr/share/nginx/html
COPY ./src/assets/configs/config.docker.json /usr/share/nginx/html/assets/configs/config.json

CMD ["nginx", "-g", "daemon off;"]