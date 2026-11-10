#!/bin/sh
set -e

echo "=========================================================="
echo "  KHO TỔNG SPX MEGA SOC PHÙ CHẨN - SHOPEE TMĐT & LOGISTICS"
echo "=========================================================="

# Đảm bảo thư mục lưu trữ dữ liệu tồn tại
mkdir -p /app/data

# Tự động khởi tạo CSDL và nạp dữ liệu mẫu ban đầu (idempotent)
echo "-> Kiểm tra và đồng bộ dữ liệu mẫu (seed_data)..."
python seed_data.py || echo "Warning: seed_data finished with note, continuing..."

# Khởi động Web Server Uvicorn
PORT=${SERVER_PORT:-8090}
echo "-> Server sẵn sàng tại cổng $PORT! Đang lắng nghe kết nối..."
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
