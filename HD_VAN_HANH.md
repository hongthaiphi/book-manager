# Hướng dẫn Vận hành Book Manager

Dự án **Book Manager** là hệ thống quản lý tủ sách cá nhân và hỗ trợ cho mượn sách trong cộng đồng (tòa nhà). Hệ thống sử dụng FastAPI (Backend), React (Frontend) và PostgreSQL (Database), được đóng gói bằng Docker.

---

## 1. Yêu cầu Hệ thống

Để chạy dự án này, bạn cần cài đặt:
- **Docker Desktop** (hoặc Docker Engine + Docker Compose).
- **Make** (tùy chọn, giúp chạy các lệnh nhanh hơn).

---

## 2. Thiết lập Môi trường

1.  **Tạo file `.env`**:
    Chạy lệnh sau để copy từ file ví dụ:
    ```bash
    make setup
    # Hoặc: cp .env.example .env
    ```

2.  **Cấu hình các API Key**:
    Mở file `.env` và điền đầy đủ các thông tin sau:
    - **Google OAuth**: Tạo tại [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
        - `GOOGLE_CLIENT_ID`
        - `GOOGLE_CLIENT_SECRET`
        - `GOOGLE_REDIRECT_URI`: Mặc định là `http://localhost:8000/api/auth/callback`
    - **Cloudinary**: Tạo tại [Cloudinary](https://cloudinary.com) để lưu trữ ảnh bìa sách.
        - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
    - **Google Books API**: Tạo tại [Google Library](https://console.cloud.google.com/apis/library/books.googleapis.com) để tự động điền thông tin sách qua ISBN.
        - `GOOGLE_BOOKS_API_KEY`

---

## 3. Khởi chạy Ứng dụng

Sử dụng Docker Compose để khởi chạy toàn bộ stack (Database + Backend + Frontend):

```bash
make up
# Hoặc: docker compose up --build
```

Hệ thống sẽ:
1.  Khởi động database PostgreSQL.
2.  Tự động chạy các bản cập nhật database (Alembic migrations).
3.  Chạy Backend tại cổng `8000`.
4.  Chạy Frontend tại cổng `5173`.

---

## 4. Địa chỉ truy cập

- **Frontend**: [http://localhost:5173](http://localhost:5173)
- **API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Redoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 5. Quy trình sử dụng (Workflows)

### 5.1 Đăng nhập & Xác thực
- Hệ thống sử dụng **Google OAuth 2.0**. Người dùng chỉ cần click "Login with Google".
- Để mượn sách, người dùng cần xác thực số điện thoại trong mục **Settings**. OTP sẽ được in ra tại console của Backend (Logs) nếu đang ở chế độ dev.

### 5.2 Quản lý tủ sách cá nhân
- **Thêm sách**: Nhập mã ISBN (10 hoặc 13 số), hệ thống sẽ tự động lấy thông tin (tên, tác giả, ảnh bìa) từ Google Books.
- **Ghi chú cá nhân**: Bạn có thể note lại giá mua, lý do mua, trạng thái đã đọc hay chưa, và đánh giá xem sách có xứng đáng với kỳ vọng không.
- **Thiết lập cho mượn**: Bật chế độ "Cho mượn" và đặt số tiền cọc (deposit) mong muốn.

### 5.3 Cho mượn sách trong cộng đồng
1.  **Gia nhập tòa nhà**: Người dùng cần tạo hoặc gia nhập một tòa nhà bằng `invite_code` để thấy sách của hàng xóm.
2.  **Gửi yêu cầu**: Người mượn chọn sách -> Gửi yêu cầu (Request).
3.  **Duyệt yêu cầu**: Chủ sách nhận thông báo -> Approve (hẹn địa điểm, thống nhất tiền cọc).
4.  **Trao sách**: Gặp mặt trực tiếp -> Chủ sách bấm "Confirm" để chuyển trạng thái sang "Đang mượn".
5.  **Trả sách**: Sau khi nhận lại sách, chủ sách bấm "Mark as Returned" và có thể đánh giá (Rate) người mượn.

---

## 6. Các lệnh quản lý hữu ích

| Lệnh | Mô tả |
| :--- | :--- |
| `make logs` | Xem nhật ký (logs) của hệ thống |
| `make migrate` | Chạy thủ công các bản cập nhật database |
| `make shell-backend` | Truy cập vào terminal của Backend |
| `make test` | Chạy bộ test kiểm thử (Pytest) |
| `make down` | Dừng và xóa các container |

---

## 7. Xử lý lỗi thường gặp

- **Lỗi Database chưa sẵn sàng**: Khi chạy lần đầu, Backend có thể khởi động trước DB. Docker Compose đã cấu hình `healthcheck` để xử lý việc này, nhưng nếu gặp lỗi, hãy thử `make down` rồi `make up` lại.
- **Lỗi Google OAuth**: Đảm bảo `GOOGLE_REDIRECT_URI` trong file `.env` khớp chính xác với cấu hình trên Google Cloud Console.
- **Ảnh không hiện**: Kiểm tra lại thông số Cloudinary trong file `.env`.
