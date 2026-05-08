# Book Manager — Tài liệu Yêu cầu Chi tiết (SRS)

**Phiên bản:** 2.0
**Ngày cập nhật:** 2026-05-08
**Tác giả:** phihongthai.it@gmail.com

> v2.0 — Cập nhật để đồng nhất với `design.md` v2:
> - Chuyển auth sang Google OAuth (bỏ email/password)
> - Thêm phone verification cho borrower
> - Thêm Buildings/Community (tủ sách toà nhà)
> - Redesign loan flow: request → approve → confirm → return → rate
> - Thêm borrower rating + blacklist
> - Bỏ Redis khỏi yêu cầu core (thêm Phase 5+ nếu cần)
> - Shared lists chuyển sang Phase 4 (optional)

---

## Mục lục

1. [Giới thiệu](#1-giới-thiệu)
2. [Người dùng & Vai trò](#2-người-dùng--vai-trò)
3. [Yêu cầu chức năng](#3-yêu-cầu-chức-năng)
   - 3.1 [Xác thực & Tài khoản](#31-xác-thực--tài-khoản)
   - 3.2 [Quản lý sách (Catalog)](#32-quản-lý-sách-catalog)
   - 3.3 [Cộng đồng toà nhà](#33-cộng-đồng-toà-nhà)
   - 3.4 [Cho mượn sách](#34-cho-mượn-sách)
   - 3.5 [Trust — Đánh giá & Blacklist](#35-trust--đánh-giá--blacklist)
   - 3.6 [Profile công khai](#36-profile-công-khai)
   - 3.7 [Thông báo](#37-thông-báo)
   - 3.8 [Thống kê](#38-thống-kê)
4. [Yêu cầu phi chức năng](#4-yêu-cầu-phi-chức-năng)
5. [Quy tắc nghiệp vụ](#5-quy-tắc-nghiệp-vụ)
6. [Yêu cầu giao diện](#6-yêu-cầu-giao-diện)
7. [Yêu cầu tích hợp ngoài](#7-yêu-cầu-tích-hợp-ngoài)
8. [Acceptance Criteria — Happy Paths](#8-acceptance-criteria--happy-paths)

---

## 1. Giới thiệu

### 1.1 Mục đích

Tài liệu này mô tả đầy đủ yêu cầu chức năng và phi chức năng của **Book Manager** — webapp quản lý tủ sách cá nhân và cho mượn sách trong cộng đồng toà nhà.

### 1.2 Phạm vi

Book Manager phục vụ hai nhu cầu:

1. **Số hoá tủ sách cá nhân** — catalog sách đang có, ghi chú mua ở đâu, giá bao nhiêu, có xứng đáng không, cho mượn được không
2. **Cho mượn trong cộng đồng** — người trong cùng toà nhà có thể xem sách available và gửi yêu cầu mượn, có cơ chế trust (phone verify + rating + blacklist)

Social features (review công khai, follow, feed) nằm ngoài phạm vi v2.0 — sẽ xem xét Phase 5.

### 1.3 Định nghĩa thuật ngữ

| Thuật ngữ | Định nghĩa |
|-----------|-----------|
| Lender | Người sở hữu sách, quyết định cho mượn hay không |
| Borrower | Người muốn mượn sách; phải đăng nhập + verify phone |
| Building | Toà nhà / cộng đồng chung cư; thành viên join bằng invite_code |
| Loan request | Yêu cầu mượn do borrower gửi; chờ lender approve/reject |
| Loan | Phiếu mượn active sau khi lender confirm đã trao sách |
| Blacklist | Danh sách người bị lender block; không thể gửi request đến lender đó |

---

## 2. Người dùng & Vai trò

### 2.1 Thành viên (Member)

Người dùng đã đăng nhập bằng Google. Mỗi member vừa có thể là Lender vừa là Borrower tuỳ tình huống.

**Làm được:**
- Quản lý toàn bộ tủ sách cá nhân
- Đánh dấu sách có thể cho mượn + đặt mức cọc
- Xem tủ sách toà nhà (sách available từ các thành viên khác)
- Gửi / nhận / xử lý loan requests
- Manage blacklist cá nhân

**Làm được thêm khi phone_verified = true:**
- Gửi loan request để mượn sách người khác

### 2.2 Guest (Khách chưa đăng nhập)

**Làm được:**
- Xem profile công khai của member (nếu member bật public)

**Không làm được:**
- Mượn sách, gửi loan request, xem tủ sách toà nhà

---

## 3. Yêu cầu chức năng

---

### 3.1 Xác thực & Tài khoản

#### FR-AUTH-01: Đăng nhập bằng Google OAuth

**Mô tả:** Toàn bộ auth thông qua Google OAuth 2.0. Không có email/password riêng.

**Luồng:**
1. User click "Đăng nhập bằng Google"
2. Redirect đến Google OAuth consent screen
3. Google redirect về `/api/auth/google/callback` kèm `code`
4. Backend exchange code → nhận `id_token` → extract `sub`, `email`, `name`, `picture`
5. Nếu `google_sub` chưa tồn tại → tạo user mới tự động
6. Nếu đã tồn tại → login, cập nhật `name` và `avatar_url` từ Google nếu thay đổi
7. Trả về JWT access token (15 phút) + refresh token (30 ngày)

**Acceptance Criteria:**
- [ ] Lần đầu login → tạo account, tự sinh `profile_slug` từ tên Google (unique)
- [ ] Đăng nhập thành công → redirect về trang trước hoặc `/home`
- [ ] Nếu Google callback trả lỗi → hiện thông báo lỗi, không crash

---

#### FR-AUTH-02: Làm mới token

**Xử lý:** Client gửi refresh token → nhận access token mới (refresh token rotation: thu hồi token cũ, cấp mới)

**Acceptance Criteria:**
- [ ] Refresh token hợp lệ → access token mới
- [ ] Refresh token hết hạn / bị thu hồi → lỗi 401, client redirect đến trang login

---

#### FR-AUTH-03: Đăng xuất

**Xử lý:** Thu hồi refresh token hiện tại

**Acceptance Criteria:**
- [ ] Sau đăng xuất, refresh token cũ không dùng được

---

#### FR-AUTH-04: Xác thực số điện thoại

**Mô tả:** Bắt buộc để có thể gửi loan request mượn sách. Dùng OTP qua SMS.

**Luồng:**
1. User vào Settings → nhập số điện thoại VN (10 số, bắt đầu 0)
2. Hệ thống gửi OTP 6 chữ số, hiệu lực 5 phút
3. User nhập OTP → nếu đúng → `phone_verified = true`

**Acceptance Criteria:**
- [ ] OTP sai quá 3 lần trong 5 phút → khóa 10 phút, phải gửi lại
- [ ] Chỉ cần verify 1 lần; số điện thoại có thể thay đổi (cần verify lại)
- [ ] Gửi lại OTP: phải chờ ít nhất 60 giây sau lần gửi trước

---

#### FR-AUTH-05: Cập nhật profile

**Input (optional):** `name`, `bio`, `profile_slug`

**Ràng buộc:**
- `profile_slug`: 3–50 ký tự, chỉ `a-z`, `0-9`, `-`; không bắt đầu/kết thúc bằng `-`

**Acceptance Criteria:**
- [ ] `profile_slug` đã tồn tại → lỗi 409
- [ ] Slug cũ sau khi đổi → redirect 301 đến slug mới

---

### 3.2 Quản lý sách (Catalog)

#### FR-BOOK-01: Thêm sách qua ISBN

**Mô tả:** Nhập ISBN → tự động tra Google Books → form điền sẵn.

**Luồng:**
1. User nhập ISBN (10 hoặc 13 số) → gọi Google Books API
2. Nếu tìm thấy: form điền sẵn title, authors, publisher, published_at, cover_url, page_count, description, genres
3. User bổ sung personal fields → lưu
4. Nếu không tìm thấy: thông báo, chuyển sang nhập tay

**Acceptance Criteria:**
- [ ] ISBN hợp lệ, có trên Google Books → form điền sẵn < 2 giây
- [ ] ISBN không tìm thấy → thông báo rõ, không crash
- [ ] ISBN định dạng sai → validate ngay frontend, không gọi API

---

#### FR-BOOK-02: Tìm kiếm sách để thêm

**Luồng:** Nhập tên sách / tác giả → Google Books search → danh sách kết quả → chọn → form điền sẵn

**Acceptance Criteria:**
- [ ] Kết quả hiện < 1 giây
- [ ] Mỗi kết quả: ảnh bìa, tên, tác giả, năm

---

#### FR-BOOK-03: Nhập sách thủ công

**Input:**

| Trường | Bắt buộc | Ràng buộc |
|--------|----------|-----------|
| `title` | Có | 1–500 ký tự |
| `authors` | Không | tối đa 5 tác giả |
| `isbn` | Không | ISBN-10 hoặc ISBN-13 hợp lệ |
| `publisher` | Không | ≤ 200 ký tự |
| `published_at` | Không | Không là ngày tương lai |
| `page_count` | Không | 1–9999 |
| `language` | Không | Mặc định "vi" |
| `genres` | Không | Tối đa 5 thể loại |
| `cover` | Không | JPG/PNG/WEBP ≤ 5MB |

**Acceptance Criteria:**
- [ ] Chỉ `title` là bắt buộc
- [ ] Ảnh bìa upload → resize 400×600px, lưu Cloudinary

---

#### FR-BOOK-04: Personal fields — thông tin cá nhân về cuốn sách

**Mô tả:** Các field này gắn với `user_books`, không phải `book_catalog`. Private theo mặc định.

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `status` | select | want_to_read / reading / read / did_not_finish |
| `started_at` | date | Ngày bắt đầu đọc |
| `finished_at` | date | Ngày đọc xong |
| `acquired_how` | select | bought / gift / other |
| `gift_from` | text | Được tặng từ ai (nếu `acquired_how = gift`) |
| `purchase_price` | number | Giá mua (VND) |
| `purchase_where` | text | Mua ở đâu (Fahasa, Shopee, hội sách...) |
| `purchase_reason` | textarea | Tại sao mua |
| `personal_rating` | 1–5 sao | Đánh giá cá nhân |
| `met_expectations` | boolean | Có xứng đáng với kỳ vọng trước khi mua? |
| `personal_note` | textarea | Ghi chú riêng tư |
| `physical_cover_url` | image | Ảnh chụp bìa thực tế (nếu khác ảnh online) |
| `tags` | text[] | Nhãn cá nhân, tối đa 10 |
| `is_public` | boolean | Hiện trên profile công khai, mặc định true |

**Ràng buộc:**
- `finished_at` không được trước `started_at`
- `personal_rating` chỉ cho phép khi `status = 'read'`
- `met_expectations` chỉ cho phép khi `status = 'read'`

**Acceptance Criteria:**
- [ ] Đổi status sang `read` → tự động đặt `finished_at = today` nếu chưa có
- [ ] Form cập nhật bất kỳ field nào không cần reload trang
- [ ] `physical_cover_url` → resize 400×600px, lưu Cloudinary

---

#### FR-BOOK-05: Đặt sách sẵn sàng cho mượn

**Mô tả:** Owner quyết định cuốn sách nào có thể được mượn và điều kiện.

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `can_lend` | boolean | Có cho mượn không |
| `deposit_amount` | number | Tiền cọc yêu cầu (0 = không cần cọc) |
| `lend_note` | textarea | Ghi chú điều kiện (ví dụ: "trả trong 2 tuần") |

**Acceptance Criteria:**
- [ ] Toggle `can_lend` → sách hiện/ẩn ngay trên tủ sách toà nhà
- [ ] Sách đang có active loan → không thể tắt `can_lend` cho đến khi trả xong
- [ ] `deposit_amount = 0` → hiển thị "Không cần cọc"

---

#### FR-BOOK-06: Scan ISBN bằng camera (Phase 3)

**Thư viện:** `html5-qrcode` hoặc `quagga2`

**Acceptance Criteria:**
- [ ] Hoạt động trên Chrome Mobile và Safari iOS
- [ ] Nhận diện EAN-13 (ISBN-13) trong điều kiện ánh sáng bình thường
- [ ] Browser không hỗ trợ camera API → ẩn nút, không hiện lỗi

---

#### FR-BOOK-07: Xem danh sách tủ sách

**Bộ lọc:**
- `status`: reading / read / want_to_read / did_not_finish / (all)
- `can_lend`: checkbox "Chỉ hiện sách đang cho mượn"
- `genres`, `tags`, `acquired_how`, `personal_rating`

**Tìm kiếm:** Full-text trên title + authors + tags (PostgreSQL `tsvector`)

**Sắp xếp:** Ngày thêm (mặc định), Tên A-Z, Rating, Ngày đọc xong

**Acceptance Criteria:**
- [ ] Load trang đầu < 300ms
- [ ] Filter phản ánh ngay, không cần bấm Search
- [ ] Empty state rõ ràng kèm CTA

---

#### FR-BOOK-08: Xem / Sửa / Xóa chi tiết sách

**Acceptance Criteria:**
- [ ] Tất cả fields hiển thị và chỉnh sửa được
- [ ] Sách đang có active loan → nút "Xóa" disabled + tooltip giải thích
- [ ] Xóa thành công → loan history của sách đó bị xóa theo

---

### 3.3 Cộng đồng toà nhà

#### FR-BUILDING-01: Tạo toà nhà

**Mô tả:** Member đầu tiên tạo toà nhà, nhận invite_code để chia sẻ cho hàng xóm.

**Input:** `name` (tên toà nhà), `address` (địa chỉ, optional)

**Xử lý:** Sinh `invite_code` 8 ký tự (A-Z + 0-9), unique

**Acceptance Criteria:**
- [ ] Mỗi user chỉ thuộc 1 toà nhà tại một thời điểm
- [ ] Người tạo tự động trở thành thành viên

---

#### FR-BUILDING-02: Tham gia toà nhà

**Input:** `invite_code`

**Acceptance Criteria:**
- [ ] Code đúng → join thành công, tủ sách toà nhà hiện ngay
- [ ] Code sai → lỗi rõ ràng
- [ ] Đã thuộc toà nhà khác → hỏi xác nhận trước khi chuyển

---

#### FR-BUILDING-03: Tủ sách toà nhà

**Mô tả:** Xem tất cả sách `can_lend = true` và không có active loan, từ mọi thành viên cùng toà nhà (trừ sách của chính mình).

**Hiển thị mỗi sách:**
- Ảnh bìa, tên, tác giả
- Tên chủ sách + tầng/căn (nếu có)
- Tiền cọc yêu cầu (hoặc "Không cần cọc")
- Nút "Yêu cầu mượn"

**Bộ lọc:** Theo tên sách / tác giả / tên chủ

**Acceptance Criteria:**
- [ ] Chỉ thành viên cùng toà nhà mới xem được
- [ ] Sách của chính mình không hiện trong danh sách
- [ ] Người chưa verify phone → click "Yêu cầu mượn" → redirect verify phone

---

### 3.4 Cho mượn sách

#### FR-LOAN-01: Gửi yêu cầu mượn

**Mô tả:** Borrower gửi loan request cho một cuốn sách trong tủ sách toà nhà.

**Điều kiện:**
- Borrower phải `phone_verified = true`
- Borrower không nằm trong blacklist của lender

**Input:** `message` (tin nhắn tuỳ chọn, ≤ 300 ký tự)

**Xử lý:**
- Tạo `loan_request` với `status = 'pending'`
- Gửi notification cho lender

**Acceptance Criteria:**
- [ ] Phone chưa verify → chặn, hiện modal "Xác thực số điện thoại trước"
- [ ] Đang trong blacklist của lender → ẩn nút, không thông báo lý do
- [ ] Đã có pending request cho sách đó → không gửi thêm được
- [ ] Rate limit: 10 requests/ngày/user (tránh spam)

---

#### FR-LOAN-02: Xem và xử lý yêu cầu (Lender)

**Mô tả:** Lender xem danh sách loan requests gửi đến, approve hoặc reject.

**Hiển thị mỗi request:** Avatar + tên borrower, tên sách, tin nhắn, thời gian gửi

**Hành động approve:**
- Lender điền `agreed_deposit` (tiền cọc đã thoả thuận) và `meet_location` (địa điểm hẹn)
- Request chuyển sang `status = 'approved'`
- Borrower nhận notification kèm thông tin cọc + địa điểm

**Hành động reject:**
- Lender điền lý do (optional, private)
- Request chuyển sang `status = 'rejected'`
- Borrower nhận notification "Yêu cầu mượn không được chấp nhận"

**Acceptance Criteria:**
- [ ] Badge số request chưa xử lý hiện trên menu
- [ ] Approve mà không điền agreed_deposit → deposit = 0 (không cần cọc)
- [ ] Reject xong → sách vẫn available cho người khác request

---

#### FR-LOAN-03: Confirm giao sách (Lender)

**Mô tả:** Sau khi gặp nhau và trao sách ngoài đời thực, lender confirm trong app.

**Xử lý:**
- Tạo `loan` record với `status = 'active'`
- Sách không còn hiện trong tủ sách toà nhà

**Acceptance Criteria:**
- [ ] Chỉ lender mới confirm được (không phải borrower)
- [ ] Confirm → loan chuyển sang active, loan request đóng lại

---

#### FR-LOAN-04: Theo dõi loan đang active

**Hiển thị (Lender view):**
- Tên + avatar borrower, tên sách
- Ngày mượn, ngày hẹn trả, số ngày còn lại / quá hạn
- Sách quá hạn → highlight đỏ

**Hiển thị (Borrower view):**
- Tên + avatar lender, tên sách
- Ngày mượn, ngày hẹn trả

**Acceptance Criteria:**
- [ ] Sắp xếp mặc định: quá hạn lên đầu, tiếp theo là sắp đến hạn
- [ ] Tự động mark `status = 'overdue'` khi quá `due_at` (scheduler hàng ngày)

---

#### FR-LOAN-05: Ghi nhận trả sách (Lender)

**Xử lý:**
- Cập nhật `loans.returned_at = today`, `loans.status = 'returned'`
- Sách hiện trở lại tủ sách toà nhà (nếu `can_lend` vẫn = true)

**Acceptance Criteria:**
- [ ] Dialog xác nhận ngày trả, mặc định hôm nay, có thể chỉnh
- [ ] Trả xong → loan chuyển lịch sử, sách available lại
- [ ] Hủy notifications nhắc hạn còn pending

---

### 3.5 Trust — Đánh giá & Blacklist

#### FR-TRUST-01: Rate borrower sau khi trả

**Mô tả:** Sau khi loan completed, lender có thể rate borrower. Optional, không bắt buộc.

**Input:**
- `is_positive` (boolean): 👍 Tốt / 👎 Không tốt
- `note` (text, ≤ 300 ký tự): lý do (ví dụ: "trả trễ 5 ngày", "sách bị nhàu góc")
- `block_user` (boolean): block borrower này luôn

**Acceptance Criteria:**
- [ ] Chỉ rate được khi loan ở trạng thái `returned` hoặc `lost`
- [ ] Mỗi loan chỉ rate được 1 lần
- [ ] Rating là private — borrower không nhận notification, không thấy nội dung

---

#### FR-TRUST-02: Blacklist

**Mô tả:** Lender block một borrower khỏi việc gửi request mượn sách của mình.

**Trigger tự động:** Tick "Block người này" khi rate (FR-TRUST-01)

**Trigger thủ công:** Vào Settings → Blacklist → Block thủ công bằng tên/email

**Hiệu lực:**
- Người bị block: nút "Yêu cầu mượn" ẩn trên sách của lender đó (silent, không có thông báo)
- Pending requests từ người bị block → tự động cancelled

**Acceptance Criteria:**
- [ ] Lender xem danh sách blacklist: tên, lý do, ngày block
- [ ] Lender có thể unblock bất kỳ lúc nào
- [ ] Blacklist là private, không hiển thị cho bên thứ 3

---

### 3.6 Profile công khai

#### FR-PUBLIC-01: Bật/tắt profile công khai

**Cài đặt:**
- `is_public` (user level): bật/tắt toàn bộ profile
- `is_public` (user_book level): ẩn sách cụ thể dù profile public

**Acceptance Criteria:**
- [ ] Profile private → `/u/{slug}` trả về 404
- [ ] Toggle không ảnh hưởng dữ liệu sách

---

#### FR-PUBLIC-02: Xem profile công khai

**URL:** `/u/{slug}` — không cần đăng nhập

**Hiển thị:** Avatar, tên, bio, tổng số sách, số đã đọc, danh sách sách public

**Không hiển thị:** Thông tin cá nhân (giá mua, ghi chú riêng, tủ sách toà nhà), blacklist, rating

**Acceptance Criteria:**
- [ ] Load < 500ms
- [ ] Meta tags đầy đủ (og:title, og:image, og:description) cho social sharing
- [ ] Sách `is_public = false` không hiện dù profile public

---

### 3.7 Thông báo

Notifications dùng **polling 30 giây** (không dùng SSE/WebSocket ở phase đầu).

#### FR-NOTIF-01: Các loại notification

| Type | Trigger | Nhận bởi |
|------|---------|---------|
| `loan_request_received` | Borrower gửi request | Lender |
| `loan_request_approved` | Lender approve | Borrower |
| `loan_request_rejected` | Lender reject | Borrower |
| `loan_due_soon` | Scheduler: `due_at = today + 3` | Lender (nhắc follow-up) |
| `loan_overdue` | Scheduler: `due_at < today`, mỗi 7 ngày | Lender |

**Acceptance Criteria:**
- [ ] Badge số notification chưa đọc cập nhật mỗi 30 giây
- [ ] Click notification → mark read + điều hướng đến nội dung liên quan
- [ ] Notification cũ hơn 90 ngày tự xóa (cleanup job)

---

#### FR-NOTIF-02: Nhắc hạn trả (Scheduler)

**Lịch chạy:** Mỗi ngày 9:00 sáng

**Logic:**
- `due_at = today + 3 ngày` → tạo `loan_due_soon` cho lender
- `due_at = today` → tạo thêm 1 notification
- `due_at < today AND returned_at IS NULL` → tạo `loan_overdue` mỗi 7 ngày

**Acceptance Criteria:**
- [ ] Không tạo trùng notification cùng loại cho cùng loan trong cùng ngày
- [ ] Loan được trả → hủy các notifications pending

---

### 3.8 Thống kê

#### FR-STATS-01: Dashboard tổng quan

**Hiển thị:**
- Tổng số sách / đã đọc / đang đọc / muốn đọc / chưa hoàn thành
- Số sách đọc xong năm nay / tháng này
- Sách đang đọc dở (sort theo `started_at`)
- Sách mới thêm (5 cuốn gần nhất)
- Loans sắp hết hạn / quá hạn

**Acceptance Criteria:**
- [ ] Load < 500ms
- [ ] Số liệu chính xác tính đến thời điểm hiện tại

---

#### FR-STATS-02: Tốc độ đọc

**Hiển thị:** Bar chart — số sách đọc xong theo tháng (12 tháng gần nhất)

**Acceptance Criteria:**
- [ ] Chỉ tính sách `status = 'read'` có `finished_at` không null
- [ ] Hover cột → xem danh sách sách đọc tháng đó

---

#### FR-STATS-03: Thống kê lending

**Hiển thị:**
- Tổng số lần cho mượn / tổng số lần đi mượn
- Tỷ lệ hoàn trả đúng hạn
- Sách được mượn nhiều nhất

**Acceptance Criteria:**
- [ ] Chỉ tính loans với `status = 'returned'` hoặc `'lost'`

---

## 4. Yêu cầu phi chức năng

### 4.1 Hiệu năng

| Metric | Mục tiêu |
|--------|----------|
| API response time (P95) | < 300ms |
| Full-text search | < 500ms |
| Trang public profile | < 1 giây |
| Google Books lookup | < 2 giây (timeout 3 giây) |
| Image upload & resize | < 5 giây |
| Notification polling | Mỗi 30 giây |

### 4.2 Bảo mật

- Google OAuth: không lưu password, verify `id_token` với Google public keys
- JWT secret ≥ 256-bit entropy; access token 15 phút, refresh token 30 ngày (rotation)
- SQL injection: chỉ dùng parameterized query qua SQLAlchemy
- XSS: sanitize user input trước khi lưu; frontend escape khi render
- CORS: chỉ cho phép origin từ `FRONTEND_URL`
- HTTPS bắt buộc trên production
- Rate limiting:
  - Auth endpoints: 20 req/phút/IP
  - Loan request: 10 requests/ngày/user
  - API chung: 200 req/phút/user
- Blacklist là private — không expose qua bất kỳ API public nào

### 4.3 Độ tin cậy

- Uptime mục tiêu: 99%
- Database backup: hàng ngày, lưu 30 ngày
- Mọi API lỗi trả về JSON `{ "error": "...", "code": "..." }` nhất quán
- Google Books API timeout 3 giây → fallback "không tìm thấy, nhập tay"

### 4.4 Khả năng bảo trì

- API auto docs qua FastAPI (`/docs`, `/redoc`)
- Database migration quản lý bằng Alembic
- Log structured (JSON): DEBUG / INFO / WARNING / ERROR
- Lỗi 5xx phải log kèm traceback và request context

---

## 5. Quy tắc nghiệp vụ

| ID | Quy tắc |
|----|---------|
| BR-01 | Một cuốn sách chỉ có tối đa 1 active loan tại một thời điểm |
| BR-02 | Sách đang có active loan không thể tắt `can_lend` hoặc xóa — phải trả xong trước |
| BR-03 | Borrower phải có `phone_verified = true` để gửi loan request |
| BR-04 | Người bị blacklist bởi lender X không gửi được loan request cho sách của lender X |
| BR-05 | Lender không thể tự gửi request mượn sách của chính mình |
| BR-06 | Rating borrower là private — không hiển thị cho borrower hoặc bất kỳ third party nào |
| BR-07 | `personal_rating` chỉ cho phép khi `status = 'read'` |
| BR-08 | `finished_at` không thể trước `started_at` |
| BR-09 | `profile_slug` một khi đổi → slug cũ redirect 301 đến slug mới |
| BR-10 | Deposit xảy ra ngoài hệ thống (bank transfer); app chỉ lưu `agreed_deposit` làm reference |
| BR-11 | Pending loan requests của một borrower → tự cancelled nếu borrower bị blacklist sau đó |
| BR-12 | Loan request chỉ có thể cancelled bởi borrower khi còn ở trạng thái `pending` |

---

## 6. Yêu cầu giao diện

### 6.1 Responsive

| Breakpoint | Chiều rộng | Layout |
|------------|-----------|--------|
| Mobile | 375px+ | 1 cột |
| Tablet | 768px+ | 2 cột |
| Desktop | 1024px+ | 3–4 cột (grid sách) |
| Wide | 1440px+ | Max-width container 1280px |

### 6.2 Theme

- Light mode (mặc định) + Dark mode
- Toggle thủ công; lưu preference vào `localStorage`
- Detect `prefers-color-scheme` lần đầu truy cập

### 6.3 Trang & Navigation

| Trang | URL | Auth |
|-------|-----|------|
| Landing / Login | `/` | Không cần |
| Home / Dashboard | `/home` | Cần |
| Tủ sách cá nhân | `/shelf` | Cần |
| Chi tiết sách | `/shelf/{id}` | Cần |
| Thêm sách | `/shelf/add` | Cần |
| Tủ sách toà nhà | `/community` | Cần + same building |
| Quản lý cho mượn | `/lending` | Cần |
| Thống kê | `/stats` | Cần |
| Cài đặt (profile, phone, blacklist) | `/settings` | Cần |
| Profile công khai | `/u/{slug}` | Không cần |

### 6.4 Empty States

Mọi trang danh sách phải có empty state rõ khi chưa có dữ liệu:
- Tủ sách trống → "Bạn chưa có sách nào. Thêm sách đầu tiên!" + CTA
- Tủ sách toà nhà trống → "Chưa có ai chia sẻ sách. Hãy là người đầu tiên!"
- Không có loan nào → "Chưa có sách nào đang được mượn."
- Không có notification → "Bạn đã đọc hết thông báo."

### 6.5 Feedback & Loading

- Mọi action bất đồng bộ phải có loading indicator
- Thành công → toast xanh, tự đóng sau 3 giây
- Lỗi → toast đỏ, không tự đóng
- Form validation: báo lỗi inline ngay dưới trường, không chỉ sau submit

---

## 7. Yêu cầu tích hợp ngoài

### 7.1 Google OAuth 2.0

- Scopes cần: `openid`, `email`, `profile`
- Verify `id_token` trên backend bằng Google public keys (không tin client)

### 7.2 Google Books API

- Dùng để: lookup ISBN, search tên/tác giả
- Auth: API Key (không cần OAuth)
- Quota free tier: 1.000 req/ngày — đủ giai đoạn đầu
- Fallback: API down / timeout → "Không tìm được tự động, vui lòng nhập tay"

### 7.3 Cloudinary

- Upload từ backend (không expose API key ra frontend)
- Transform: ảnh bìa → 400×600px; avatar → 200×200px
- Fallback: placeholder SVG nếu không có ảnh

### 7.4 SMS / OTP Provider (Phase 2)

- Dùng để verify số điện thoại
- Gợi ý: Twilio hoặc Vonage (có số VN)
- Fallback: nếu OTP provider down → retry sau, không block toàn bộ app

---

## 8. Acceptance Criteria — Happy Paths

### Luồng 1: Onboarding user mới

1. Vào app → click "Đăng nhập bằng Google" → Google consent → redirect về
2. Account tạo tự động, `profile_slug` sinh từ tên Google
3. Prompt join / tạo toà nhà
4. Nhập invite_code → join thành công → tủ sách toà nhà hiện ra

### Luồng 2: Số hoá tủ sách

1. Click "Thêm sách" → nhập ISBN
2. Form tự điền từ Google Books → user bổ sung: mua ở đâu, giá, tại sao mua, trạng thái
3. Tick "Cho mượn" + đặt cọc 50.000đ → lưu
4. Sách hiện trong tủ sách cá nhân + tủ sách toà nhà

### Luồng 3: Mượn sách từ hàng xóm

1. Borrower vào tủ sách toà nhà → tìm thấy "Atomic Habits" của PhiHong
2. Click "Yêu cầu mượn" → nhập tin nhắn → gửi
3. PhiHong nhận notification → vào xem request → Approve, điền "cọc 50k, gặp tầng trệt chiều thứ 6"
4. Borrower nhận notification "Được chấp nhận — cọc 50.000đ, gặp ở tầng trệt chiều thứ 6"
5. Gặp nhau, trao sách, chuyển khoản ngoài app
6. PhiHong confirm trong app → loan active, sách biến khỏi tủ toà nhà

### Luồng 4: Trả sách + Rate

1. Borrower trả sách cho PhiHong
2. PhiHong vào Lending → click "Đã nhận lại"
3. Loan chuyển sang returned, sách hiện lại tủ toà nhà
4. PhiHong rate: 👍 Tốt + note "trả đúng hạn, sách giữ tốt"

### Luồng 5: Hạn trả sắp đến

1. Loan có `due_at` = 3 ngày sau
2. Scheduler 9:00 sáng → tạo notification "Sách Atomic Habits sắp đến hạn trả (còn 3 ngày)"
3. PhiHong nhận notification → nhắn tin hàng xóm qua Zalo

---

*Tài liệu này là Single Source of Truth cho yêu cầu sản phẩm. Mọi thay đổi cần được phản ánh đồng thời trong `design.md`.*
