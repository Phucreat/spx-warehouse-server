FROM python:3.11-slim

# Thiết lập biến môi trường Python chuẩn
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8090

# Cài đặt curl cho healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Thư mục làm việc trong container
WORKDIR /app

# Cài đặt các gói thư viện Python trước để tận dụng Docker cache layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy mã nguồn dự án
COPY . .

# Chuyển đổi CRLF sang LF và cấp quyền thực thi cho script khởi động
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

# Tạo thư mục dữ liệu cho persistent storage
RUN mkdir -p /app/data

# Mở cổng server
EXPOSE 8090

# Cấu hình Healthcheck kiểm tra tính sẵn sàng của ứng dụng
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${SERVER_PORT}/ || exit 1

# Khởi động ứng dụng
ENTRYPOINT ["/app/docker-entrypoint.sh"]
