[根目录](../../CLAUDE.md) > **nginx**

# Nginx 部署配置模块

## 变更记录 (Changelog)

### 2025-10-23 10:45:44 - 模块架构初始化
- ✨ 新增：模块导航面包屑
- ✨ 新增：Nginx配置文档
- 📊 分析：反向代理、静态资源、负载均衡配置
- 🔧 优化：生产环境部署和安全配置

---

## 模块职责

Nginx模块负责地产资产管理系统的生产环境部署配置，提供反向代理、静态资源服务、负载均衡、SSL终端和安全防护功能。确保系统在生产环境中的高性能、高可用和高安全性。

### 核心职责
- **反向代理**: 前端到后端的请求转发和负载均衡
- **静态资源**: 前端构建文件的高效服务和缓存
- **SSL终端**: HTTPS配置和证书管理
- **安全防护**: 访问控制、请求限制、安全头设置
- **性能优化**: Gzip压缩、缓存策略、连接优化

## 配置文件结构

### Nginx配置目录
```
nginx/
├── nginx.conf                 # 主配置文件
├── conf.d/                    # 配置片段目录
│   ├── gzip.conf             # Gzip压缩配置
│   ├── performance.conf      # 性能优化配置
│   └── security.conf         # 安全配置
└── ssl/                       # SSL证书目录
    ├── cert.pem              # SSL证书
    └── key.pem               # SSL私钥
```

## 主配置文件

### nginx.conf - 主配置
```nginx
# 用户和进程配置
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

# 事件处理配置
events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

# HTTP配置块
http {
    # 基础配置
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    # 性能优化配置
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    # 包含子配置
    include /etc/nginx/conf.d/*.conf;

    # 主服务器配置
    server {
        listen 80;
        server_name localhost;

        # 重定向到HTTPS (生产环境)
        # return 301 https://$server_name$request_uri;

        # 开发环境配置
        location / {
            root /usr/share/nginx/html;
            index index.html index.htm;
            try_files $uri $uri/ /index.html;
        }

        # API代理配置
        location /api/ {
            proxy_pass http://backend:8002;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 健康检查端点
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }

    # HTTPS服务器配置 (生产环境)
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL证书配置
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # SSL安全配置
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # 安全头配置
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

        # 静态文件服务
        location / {
            root /usr/share/nginx/html;
            index index.html index.htm;
            try_files $uri $uri/ /index.html;

            # 缓存配置
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }

        # API代理
        location /api/ {
            proxy_pass http://backend:8002;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # 文件上传配置
        location /api/v1/pdf_import/upload {
            proxy_pass http://backend:8002;
            client_max_body_size 100M;
            proxy_request_buffering off;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## 性能优化配置

### gzip.conf - Gzip压缩配置
```nginx
# Gzip压缩配置
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_proxied any;
gzip_comp_level 6;
gzip_types
    application/atom+xml
    application/geo+json
    application/javascript
    application/x-javascript
    application/json
    application/ld+json
    application/manifest+json
    application/rdf+xml
    application/rss+xml
    application/xhtml+xml
    application/xml
    font/eot
    font/otf
    font/ttf
    image/svg+xml
    text/css
    text/javascript
    text/plain
    text/xml;

# 禁用压缩条件 (针对已压缩文件)
gzip_disable "msie6";
```

### performance.conf - 性能优化配置
```nginx
# 工作进程优化
worker_processes auto;
worker_rlimit_nofile 100000;

# 事件处理优化
events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

# HTTP性能优化
http {
    # 连接优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 100;

    # 缓冲区优化
    client_body_buffer_size 128k;
    client_max_body_size 100m;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 4k;
    client_body_timeout 12;
    client_header_timeout 12;
    send_timeout 10;

    # 文件描述符缓存
    open_file_cache max=200000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;

    # DNS解析缓存
    resolver_timeout 5s;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
}
```

## 安全配置

### security.conf - 安全配置
```nginx
# 隐藏Nginx版本信息
server_tokens off;

# 安全头配置
add_header X-Frame-Options DENY always;
add_header X-Content-Type-Options nosniff always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' ws: wss:;" always;

# 请求限制
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

# 限制请求大小
client_max_body_size 100M;

# 禁用不安全的HTTP方法
if ($request_method !~ ^(GET|HEAD|POST|PUT|DELETE|OPTIONS)$ ) {
    return 405;
}

# 防止隐藏文件访问
location ~ /\. {
    deny all;
    access_log off;
    log_not_found off;
}

# 防止备份文件访问
location ~ ~$ {
    deny all;
    access_log off;
    log_not_found off;
}

# IP白名单 (可选)
# allow 192.168.1.0/24;
# deny all;

# 防止robots.txt攻击
location = /robots.txt {
    access_log off;
    log_not_found off;
}

# 防止 favicon.ico 404错误
location = /favicon.ico {
    access_log off;
    log_not_found off;
}
```

## 负载均衡配置

### 负载均衡配置块
```nginx
# 后端服务器组
upstream backend {
    least_conn;
    server backend1:8002 weight=3 max_fails=3 fail_timeout=30s;
    server backend2:8002 weight=2 max_fails=3 fail_timeout=30s;
    server backend3:8002 weight=1 max_fails=3 fail_timeout=30s backup;

    # 健康检查
    keepalive 32;
}

# 前端服务器组 (如果有多实例)
upstream frontend {
    ip_hash;  # 基于IP的会话保持
    server frontend1:80;
    server frontend2:80;
}

# API服务器配置
server {
    listen 80;
    server_name api.your-domain.com;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 负载均衡配置
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;

        # 健康检查
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
        proxy_next_upstream_tries 2;
        proxy_next_upstream_timeout 30s;
    }
}
```

## SSL/TLS配置

### SSL配置示例
```nginx
# SSL协议和密码套件
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;

# SSL会话缓存
ssl_session_cache shared:SSL:50m;
ssl_session_timeout 1d;
ssl_session_tickets off;

# OCSP装订
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;

# HSTS (HTTP严格传输安全)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

### Let's Encrypt证书配置
```bash
# 安装Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# 获取SSL证书
sudo certbot --nginx -d your-domain.com -d api.your-domain.com

# 自动续期
sudo crontab -e
# 添加以下行：
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## 缓存策略

### 静态资源缓存配置
```nginx
# 静态文件缓存配置
location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff|woff2|ttf|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header Vary Accept-Encoding;

    # 启用ETag
    etag on;

    # 压缩
    gzip_static on;
}

# HTML文件缓存 (短期)
location ~* \.html$ {
    expires 1h;
    add_header Cache-Control "public, must-revalidate";
}

# API响应缓存 (谨慎使用)
location /api/v1/assets/ {
    proxy_pass http://backend;
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$request_uri$is_args$args";
    proxy_cache_bypass $http_pragma $http_authorization;
}

# 缓存配置
proxy_cache_path /var/cache/nginx/api_cache levels=1:2 keys_zone=api_cache:10m inactive=60m use_temp_path=off;
```

## 监控和日志

### 访问日志配置
```nginx
# 详细访问日志格式
log_format detailed '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    '$request_time $upstream_response_time '
                    '$upstream_addr $upstream_status';

# 错误日志配置
error_log /var/log/nginx/error.log warn;

# 访问日志配置
access_log /var/log/nginx/access.log detailed;

# API请求日志
location /api/ {
    access_log /var/log/nginx/api_access.log detailed;
    proxy_pass http://backend;
}
```

### 监控端点配置
```nginx
# Nginx状态页面
location /nginx_status {
    stub_status on;
    access_log off;
    allow 127.0.0.1;
    allow 10.0.0.0/8;
    deny all;
}

# 健康检查端点
location /health {
    access_log off;
    return 200 "healthy\n";
    add_header Content-Type text/plain;
}
```

## Docker部署配置

### Docker Compose配置
```yaml
# docker-compose.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: zcgl-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
      - ./frontend/dist:/usr/share/nginx/html
      - ./nginx/logs:/var/log/nginx
    depends_on:
      - backend
    networks:
      - zcgl-network
    restart: unless-stopped

  backend:
    build: ./backend
    container_name: zcgl-backend
    expose:
      - "8002"
    environment:
      - DATABASE_URL=sqlite:///./data/land_property.db
    volumes:
      - ./backend/data:/app/data
      - ./backend/logs:/app/logs
    networks:
      - zcgl-network
    restart: unless-stopped

networks:
  zcgl-network:
    driver: bridge
```

### Nginx Dockerfile
```dockerfile
# nginx/Dockerfile
FROM nginx:alpine

# 复制配置文件
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# 创建日志目录
RUN mkdir -p /var/log/nginx

# 设置权限
RUN chown -R nginx:nginx /var/log/nginx

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost/health || exit 1

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
```

## 常见问题 (FAQ)

### Q: 如何配置HTTPS？
A: 获取SSL证书后，修改nginx.conf中的SSL配置，包括证书路径、协议版本和密码套件。

### Q: 如何处理大文件上传？
A: 设置`client_max_body_size`为合适的值，同时调整后端FastAPI的上传限制。

### Q: 如何配置缓存？
A: 使用`expires`和`add_header Cache-Control`指令配置静态文件缓存，API缓存需要谨慎使用。

### Q: 如何实现负载均衡？
A: 配置upstream块定义后端服务器组，在location中使用proxy_pass引用。

### Q: 如何监控Nginx性能？
A: 启用stub_status模块，配置访问日志，使用外部监控工具如Prometheus + Grafana。

### Q: 如何处理WebSocket连接？
A: 添加WebSocket特定的代理配置，包括Upgrade头和Connection头设置。

## 相关文件清单

### 主配置文件
- `nginx.conf` - 主配置文件
- `conf.d/gzip.conf` - Gzip压缩配置
- `conf.d/performance.conf` - 性能优化配置
- `conf.d/security.conf` - 安全配置

### SSL证书
- `ssl/cert.pem` - SSL证书文件
- `ssl/key.pem` - SSL私钥文件

### 日志文件
- `logs/access.log` - 访问日志
- `logs/error.log` - 错误日志
- `logs/api_access.log` - API访问日志

### Docker文件
- `../docker-compose.yml` - Docker Compose配置
- `Dockerfile` - Nginx Docker镜像构建文件

### 脚本文件
- `scripts/reload-nginx.sh` - Nginx重载脚本
- `scripts/backup-config.sh` - 配置备份脚本
- `scripts/ssl-renew.sh` - SSL证书续期脚本

---

**模块状态**: 🟢 生产就绪，配置完整，支持HTTPS、负载均衡、缓存策略和Docker部署。

**最后更新**: 2025-10-23 20:35:00 (部署配置优化)