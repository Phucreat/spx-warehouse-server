-- =============================================================================
-- ĐỒNG BỘ SUPABASE POSTGRESQL GIỮA SOFTWARE-PC-CONTROL & WEB SERVER FASTAPI
-- Áp dụng cho: SortingStation + MachineVision <-> Supabase <-> SPX Server
-- Lưu ý: Giữ tương thích 100% với Software-PC Control (không sửa mã máy trạm)
-- =============================================================================

BEGIN;

-- 1. Chuẩn hóa mặc định khổ tem A7 (khớp server và MachineVision config/default.yaml)
ALTER TABLE public.orders
    ALTER COLUMN label_size SET DEFAULT 'A7';

ALTER TABLE public.orders
    DROP CONSTRAINT IF EXISTS orders_label_size_check;

ALTER TABLE public.orders
    ADD CONSTRAINT orders_label_size_check
    CHECK (label_size IN ('A6', 'A7', 'A7_QR28', 'A8'));

-- Đảm bảo mọi đơn hiện có đều có qr_payload khớp tracking_code
UPDATE public.orders
SET qr_payload = tracking_code
WHERE qr_payload IS NULL OR btrim(qr_payload) = '';

-- 2. Index tối ưu truy vấn tra cứu log mới nhất theo tracking_code & watcher id
CREATE INDEX IF NOT EXISTS ix_sorting_logs_tracking_latest
    ON public.sorting_logs (tracking_code, created_at DESC, id DESC);

-- 3. Nâng cấp trigger function sorting_logs_apply()
--    - Tự nối order_id theo tracking_code (không phân biệt hoa/thường)
--    - Tự điền decision nếu công cụ cũ chỉ gửi status
--    - Tự chép reason sang notes nếu notes trống (PC-Control ghi vào reason)
--    - Khi decision = 'PASS': chuyển đơn sang SORTED, điền sorted_at và hub_received_at (nếu thiếu)
--    - Khi decision IN ('REJECT', 'MANUAL_REVIEW'): giữ nguyên trạng thái đơn để cho phép quét lại trên băng tải
CREATE OR REPLACE FUNCTION public.sorting_logs_apply()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF new.tracking_code IS NOT NULL THEN
        new.tracking_code := btrim(new.tracking_code);
    END IF;

    IF new.decision IS NULL AND new.status IS NOT NULL THEN
        IF upper(new.status) IN ('SORTED', 'SUCCESS', 'PASS') THEN
            new.decision := 'PASS';
        ELSIF upper(new.status) = 'MANUAL_REVIEW' THEN
            new.decision := 'MANUAL_REVIEW';
        ELSE
            new.decision := 'REJECT';
        END IF;
    END IF;

    IF (new.notes IS NULL OR btrim(new.notes) = '') AND new.reason IS NOT NULL THEN
        new.notes := left(new.reason, 255);
    END IF;

    IF new.order_id IS NULL AND new.tracking_code IS NOT NULL AND upper(new.tracking_code) <> 'UNKNOWN' THEN
        SELECT o.id INTO new.order_id
        FROM public.orders o
        WHERE upper(o.tracking_code) = upper(new.tracking_code)
        LIMIT 1;
    END IF;

    IF new.order_id IS NOT NULL AND new.decision = 'PASS' THEN
        UPDATE public.orders o
        SET status = 'SORTED',
            sorted_at = (now() AT TIME ZONE 'utc'),
            hub_received_at = COALESCE(o.hub_received_at, (now() AT TIME ZONE 'utc'))
        WHERE o.id = new.order_id;
    END IF;

    RETURN new;
END;
$$;

REVOKE ALL ON FUNCTION public.sorting_logs_apply() FROM public, anon, authenticated;

DROP TRIGGER IF EXISTS trg_sorting_logs_apply ON public.sorting_logs;
CREATE TRIGGER trg_sorting_logs_apply
BEFORE INSERT ON public.sorting_logs
FOR EACH ROW EXECUTE FUNCTION public.sorting_logs_apply();

-- 4. Bật Row Level Security (RLS) an toàn:
--    - Khóa hoàn toàn bảng nhạy cảm (users.password_hash, order_items, sort_receipts) khỏi anon
--    - Cho phép máy trạm PC-Control hoạt động mượt mà với CẢ service_role key LẪN anon key:
--      + Đọc danh mục/sản phẩm
--      + Đọc cột định tuyến của orders (ẩn tên, SĐT, địa chỉ chi tiết người nhận khỏi anon)
--      + Ghi/Upsert và đọc sorting_logs (không cho phép DELETE/TRUNCATE)
ALTER TABLE public.users         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.categories    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_items   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sorting_logs  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sort_receipts ENABLE ROW LEVEL SECURITY;

-- Xóa các policy cũ nếu chạy lại nhiều lần (idempotent)
DROP POLICY IF EXISTS "catalog_read_categories" ON public.categories;
DROP POLICY IF EXISTS "catalog_read_products"   ON public.products;
DROP POLICY IF EXISTS "station_read_orders"     ON public.orders;
DROP POLICY IF EXISTS "station_read_logs"       ON public.sorting_logs;
DROP POLICY IF EXISTS "station_insert_logs"     ON public.sorting_logs;
DROP POLICY IF EXISTS "station_update_logs"     ON public.sorting_logs;

CREATE POLICY "catalog_read_categories" ON public.categories
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "catalog_read_products" ON public.products
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "station_read_orders" ON public.orders
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "station_read_logs" ON public.sorting_logs
    FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "station_insert_logs" ON public.sorting_logs
    FOR INSERT TO anon, authenticated WITH CHECK (true);

CREATE POLICY "station_update_logs" ON public.sorting_logs
    FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);

-- Phân quyền cột chặt chẽ cho anon / authenticated (bảo vệ PII khách hàng & mật khẩu)
REVOKE ALL ON public.users, public.order_items, public.sort_receipts FROM anon, authenticated;

REVOKE ALL ON public.categories, public.products FROM anon, authenticated;
GRANT SELECT ON public.categories, public.products TO anon, authenticated;

REVOKE ALL ON public.orders FROM anon, authenticated;
GRANT SELECT (
    id, order_code, tracking_code, recipient_province, routing_code,
    destination_hub, destination_chute_id, status, label_size, qr_payload,
    created_at, confirmed_at, hub_received_at, sorted_at
) ON public.orders TO anon, authenticated;

REVOKE ALL ON public.sorting_logs FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.sorting_logs TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.sorting_logs_id_seq TO anon, authenticated;

GRANT SELECT ON public.v_order_tracking, public.v_chute_summary, public.v_sorting_exceptions
    TO anon, authenticated, service_role;

-- Báo PostgREST (Supabase REST API) tải lại schema & quyền ngay lập tức
NOTIFY pgrst, 'reload schema';

COMMIT;
