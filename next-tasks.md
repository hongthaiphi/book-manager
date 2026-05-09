# Next Tasks — Go-Live Checklist

Mục tiêu: chạy thử cho cộng đồng nhỏ (~20–50 người trong toà nhà).
Ưu tiên: đủ dùng, đủ an toàn, không over-engineer.

---

## 🔴 P0 — Bắt buộc trước khi share link

### 1. VPS + domain + HTTPS
- Thuê VPS (DigitalOcean $6/tháng, Hetzner €4, hoặc Fly.io free tier)
- Trỏ domain/subdomain về IP VPS (vd: `books.tentoanha.com`)
- Cài Nginx + Certbot (Let's Encrypt) để có HTTPS
- File `nginx.conf` proxy `/` → frontend:5173, `/api` → backend:8000

### 2. Production docker-compose
- Tách `docker-compose.prod.yml`: bỏ `--reload`, thêm `restart: unless-stopped`
- Frontend build static (`npm run build`) + serve qua Nginx thay vì Vite dev server
- Bỏ expose port 8000 ra ngoài (chỉ Nginx mới gọi vào backend)

### 3. Secrets thật
- Sinh `SECRET_KEY` và `REFRESH_SECRET_KEY` bằng `openssl rand -hex 32`
- Cập nhật Google OAuth Console: thêm production domain vào Authorized Origins + Redirect URIs
- Set `GOOGLE_REDIRECT_URI=https://books.tentoanha.com/api/auth/callback`
- Set `FRONTEND_URL=https://books.tentoanha.com`
- Đổi `secure=True` cho refresh cookie trong `auth.py` (hiện đang `False`)

### 4. CORS production
- `CORS_ORIGINS` trong `config.py` → chỉ cho phép production domain, bỏ `localhost`

### 5. Database backup tối thiểu
- Cron job hàng ngày: `pg_dump | gzip > backup_$(date).sql.gz`
- Upload lên Cloudinary hoặc S3/R2 (Cloudflare R2 có free tier)

---

## 🟡 P1 — Nên có để trải nghiệm tốt

### 6. SMS OTP thật (hiện đang chưa gửi SMS)
- Tích hợp Twilio hoặc **Esms.vn** (rẻ hơn cho VN, ~100đ/SMS)
- Cập nhật `auth.py` route `/phone/send-otp`: thay print/log bằng gọi SMS API
- Hoặc skip tạm: cho phép dùng app không cần xác minh SĐT, chỉ bắt buộc khi mượn sách

### 7. Trang lỗi và UX cơ bản
- Thêm route `*` trong React để render trang 404 thay vì blank screen
- Khi backend lỗi 500: hiển thị toast thân thiện thay vì crash
- Thêm favicon + meta title/description (cho khi share link qua Zalo)

### 8. Onboarding flow
- Sau login lần đầu: popup hỏi tên hiển thị + invite code toà nhà
- Hiện tại user phải tự vào Settings để điền — khó cho người không quen

### 9. Invite code flow rõ ràng
- Trang `/join?code=XXXXX` để share link vào group Zalo
- Ai click link → login Google → tự động join toà nhà đó
- Hiện tại phải tự nhập code trong Community page

---

## 🟢 P2 — Nice-to-have, sau khi chạy thử

### 10. Monitoring tối thiểu
- Thêm `GET /api/health` trả về `{"status": "ok", "db": "connected"}`
- Dùng UptimeRobot (free) để ping mỗi 5 phút, alert qua email nếu down

### 11. Rate limiting
- Thêm `slowapi` để giới hạn OTP request (5 req/phút/IP)
- Giới hạn search Google Books (tránh vượt quota API key)

### 12. Google Books API fallback
- Khi hết quota hoặc không tìm thấy: cho phép thêm sách thủ công (title + author only)
- Form "Thêm thủ công" đã có trong modal nhưng UX còn ẩn

### 13. Zalo notification (thay thế email)
- Dùng Zalo OA API để gửi thông báo mượn/trả sách
- Phù hợp hơn email cho cộng đồng VN

---

## Thứ tự thực hiện gợi ý

```
Tuần 1: Task 1 + 2 + 3 + 4  →  app chạy được trên server thật với HTTPS
Tuần 1: Task 5              →  có backup, yên tâm share
Tuần 2: Task 6 hoặc skip    →  OTP thật hoặc tạm bỏ qua
Tuần 2: Task 7 + 8 + 9      →  UX đủ tốt để người không quen tech dùng được
Sau khi có feedback: Task 10–13
```

---

## Files cần tạo/sửa

| File | Việc cần làm |
|------|-------------|
| `docker-compose.prod.yml` | Production compose (no reload, restart policy, build frontend) |
| `nginx/nginx.conf` | Reverse proxy + SSL termination |
| `frontend/Dockerfile.prod` | Multi-stage: build → serve static via Nginx |
| `backend/app/api/routes/auth.py` | `secure=True` cho cookie, SMS OTP thật |
| `backend/app/core/config.py` | `CORS_ORIGINS` từ env |
| `backend/app/api/routes/health.py` | `GET /api/health` |
| `.env.prod.example` | Template env cho production |
| `scripts/backup.sh` | pg_dump + upload |
