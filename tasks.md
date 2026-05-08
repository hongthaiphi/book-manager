# Book Manager — Implementation Tasks

**Dựa trên:** `design.md` v2 + `requirements.md` v2.0
**Mục tiêu:** Danh sách task chi tiết để giao cho AI agents thực hiện từng phần độc lập.

---

## Quy ước

Mỗi task có:
- **ID** dạng `Px.y` (Phase x, task y)
- **Depends on**: các task phải hoàn thành trước
- **Input files**: context agent cần đọc
- **Output**: files/folders sẽ được tạo/sửa
- **Acceptance**: tiêu chí done rõ ràng, kiểm tra được

Stack context cho mọi agent:
- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2
- Frontend: React 18, TypeScript 5, Vite, Tailwind CSS v3, shadcn/ui, Zustand
- DB: PostgreSQL 16
- Storage: Cloudinary
- Auth: Google OAuth 2.0 + JWT (access 15 phút, refresh 30 ngày, rotation)

---

## Phase 1 — Catalog MVP

### P1.1 — Project scaffold & Docker Compose

**Depends on:** —

**Mô tả:** Tạo cấu trúc thư mục đầy đủ và Docker Compose cho môi trường dev.

**Output:**
```
book-manager/
├── backend/
│   ├── app/
│   │   ├── api/routes/         (empty __init__.py)
│   │   ├── core/config.py      (Settings class dùng pydantic-settings)
│   │   ├── db/session.py       (async engine + get_db dependency)
│   │   └── main.py             (FastAPI app, CORS, include routers)
│   ├── migrations/             (Alembic init)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/               (axios instance với interceptor)
│   │   ├── components/ui/     (shadcn setup)
│   │   ├── stores/
│   │   └── App.tsx
│   ├── Dockerfile
│   ├── vite.config.ts
│   └── package.json
├── docker-compose.yml
├── docker-compose.dev.yml
└── .env.example
```

**`docker-compose.dev.yml` phải có:** postgres:16-alpine, backend (hot reload), frontend (hot reload). Không có Redis.

**`requirements.txt` phải có:** fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, python-jose[cryptography], httpx, cloudinary, python-multipart, apscheduler

**`package.json` phải có:** react, react-dom, react-router-dom, @tanstack/react-query, zustand, axios, tailwindcss, shadcn/ui

**Acceptance:**
- [ ] `docker-compose up` khởi động được cả 3 service không lỗi
- [ ] `GET /` backend trả `{ "status": "ok" }`
- [ ] Frontend load được tại `localhost:5173`
- [ ] Alembic init thành công, `alembic revision --autogenerate` chạy được

---

### P1.2 — Database models (SQLAlchemy)

**Depends on:** P1.1

**Input files:** `design.md` (Section 4 — Database Schema)

**Mô tả:** Tạo tất cả SQLAlchemy models cho Phase 1 + 2 cùng lúc (để tạo migration 1 lần).

**Output:** `backend/app/db/models.py`

**Models phải có (theo đúng schema trong design.md):**
- `User` — google_sub, email, name, avatar_url, phone_number, phone_verified, profile_slug, bio, is_public, building_id
- `Building` — name, address, invite_code (unique, 8 chars)
- `BookCatalog` — isbn (unique), title, authors (ARRAY), publisher, published_at, cover_url, language, page_count, description, genres (ARRAY), source
- `UserBook` — user_id, catalog_id, status, started_at, finished_at, acquired_how, gift_from, purchase_price, purchase_where, purchase_reason, personal_rating, met_expectations, personal_note, physical_cover_url, can_lend, deposit_amount, lend_note, tags (ARRAY), is_public + UNIQUE(user_id, catalog_id)
- `LoanRequest` — user_book_id, lender_id, borrower_id, message, status, agreed_deposit, meet_location, agreed_at, rejected_reason
- `Loan` — loan_request_id, user_book_id, lender_id, borrower_id, lent_at, due_at, returned_at, status
- `BorrowerRating` — loan_id (unique), lender_id, borrower_id, is_positive, note
- `BorrowerBlacklist` — lender_id, blocked_user_id, reason + UNIQUE(lender_id, blocked_user_id)
- `Notification` — user_id, type, title, body, actor_id, content_type, content_id, is_read

**Yêu cầu kỹ thuật:**
- Dùng `mapped_column` và `Mapped` (SQLAlchemy 2.0 style)
- UUID primary keys (`default=uuid4`)
- `created_at`, `updated_at` với `server_default=func.now()` và `onupdate`
- Relationships với `back_populates`
- Tạo migration: `alembic revision --autogenerate -m "initial_schema"` và `alembic upgrade head`

**Acceptance:**
- [ ] `alembic upgrade head` tạo đủ tất cả tables không lỗi
- [ ] `alembic downgrade -1` roll back được sạch

---

### P1.3 — Google OAuth + JWT auth

**Depends on:** P1.2

**Input files:** `requirements.md` (Section 3.1), `design.md` (Section 5 — Auth endpoints)

**Mô tả:** Implement Google OAuth flow và JWT management.

**Output:**
- `backend/app/core/security.py` — JWT encode/decode, refresh token rotation
- `backend/app/api/routes/auth.py` — 4 endpoints
- `backend/app/api/deps.py` — `get_current_user` dependency

**Endpoints:**
```
GET  /api/auth/google           → redirect to Google OAuth URL
GET  /api/auth/google/callback  → exchange code, upsert user, return tokens
POST /api/auth/refresh          → body: { refresh_token } → new access + refresh token
POST /api/auth/logout           → revoke refresh token (lưu vào DB blacklist hoặc xoá)
```

**Logic Google callback:**
1. Exchange `code` → Google token endpoint → nhận `id_token`
2. Verify `id_token` với Google public keys (dùng `google-auth` hoặc verify manually với `python-jose`)
3. Extract `sub`, `email`, `name`, `picture`
4. Upsert User (create nếu chưa có, update name/avatar nếu đã có)
5. Auto-generate `profile_slug` từ name nếu user mới (slugify, thêm suffix nếu trùng)
6. Return `{ access_token, refresh_token, token_type: "bearer" }`

**Refresh token:** Lưu hashed refresh token vào bảng `refresh_tokens` (thêm model này: user_id, token_hash, expires_at, revoked). Rotation: revoke token cũ, tạo mới.

**`get_current_user` dependency:** Decode JWT → lấy `user_id` → query User → raise 401 nếu không hợp lệ.

**Acceptance:**
- [ ] Flow đầy đủ: GET /google → redirect → callback → trả token
- [ ] Refresh token hết hạn → 401
- [ ] Dùng token giả → 401
- [ ] Logout → refresh token cũ không dùng được

---

### P1.4 — Google Books API service

**Depends on:** P1.1

**Input files:** `requirements.md` (FR-BOOK-01, FR-BOOK-02)

**Mô tả:** Service gọi Google Books API, parse kết quả, map sang BookCatalog schema.

**Output:** `backend/app/services/google_books.py`

**Functions:**
```python
async def lookup_isbn(isbn: str) -> BookCatalogCreate | None
async def search_books(query: str, max_results: int = 10) -> list[BookCatalogCreate]
```

**Mapping từ Google Books response:**
- `volumeInfo.title` → title
- `volumeInfo.authors` → authors (list)
- `volumeInfo.publisher` → publisher
- `volumeInfo.publishedDate` → published_at (parse "2018", "2018-10", "2018-10-16")
- `volumeInfo.imageLinks.thumbnail` → cover_url (thay `zoom=1` → `zoom=2` cho ảnh lớn hơn)
- `volumeInfo.pageCount` → page_count
- `volumeInfo.description` → description
- `volumeInfo.categories` → genres
- `volumeInfo.language` → language
- `industryIdentifiers` → isbn (ưu tiên ISBN_13)

**Timeout:** 3 giây. Nếu timeout / lỗi → return None (caller hiển thị "nhập tay").

**Acceptance:**
- [ ] ISBN "9780735224292" (Atomic Habits) → trả về đúng thông tin
- [ ] ISBN không tồn tại → trả None, không raise exception
- [ ] Search "atomic habits" → trả list ≥ 1 kết quả

---

### P1.5 — Book catalog & user_books API

**Depends on:** P1.2, P1.3, P1.4

**Input files:** `requirements.md` (Section 3.2), `design.md` (Section 5 — API endpoints)

**Mô tả:** CRUD endpoints cho tủ sách cá nhân.

**Output:** `backend/app/api/routes/catalog.py`, `backend/app/api/routes/books.py`, `backend/app/services/book_service.py`

**Endpoints catalog:**
```
GET  /api/catalog/lookup/isbn/{isbn}   → gọi google_books, upsert BookCatalog nếu chưa có, return
GET  /api/catalog/search?q=            → gọi google_books search, return list
GET  /api/catalog/{id}                 → chi tiết BookCatalog
```

**Endpoints user_books:**
```
GET    /api/books                      → list user_books của current_user (filter: status, can_lend, tags; search: full-text; sort)
POST   /api/books                      → tạo UserBook (catalog_id required; nếu catalog chưa có → nhận full catalog data từ body)
GET    /api/books/{id}
PUT    /api/books/{id}                 → update bất kỳ field nào
DELETE /api/books/{id}                 → chặn nếu có active loan
```

**Business rules trong service:**
- POST /api/books: nếu `catalog_id` chưa tồn tại trong DB → tạo BookCatalog trước (manual input case)
- DELETE: query Loan có `user_book_id = id AND status = 'active'` → nếu có → raise 409
- PUT: nếu `status` đổi sang `read` và `finished_at` is null → tự set `finished_at = today`
- `personal_rating` chỉ chấp nhận khi `status = 'read'`

**Full-text search:** Dùng PostgreSQL `to_tsvector('simple', title || ' ' || array_to_string(authors, ' '))` với GIN index.

**Acceptance:**
- [ ] POST → GET list hiện sách vừa thêm
- [ ] Filter `status=read` chỉ trả sách đã đọc
- [ ] DELETE sách có active loan → 409
- [ ] Search "atomic" tìm được "Atomic Habits"

---

### P1.6 — Cloudinary image upload

**Depends on:** P1.1

**Output:** `backend/app/services/cloudinary_service.py`, endpoint `POST /api/books/{id}/cover`

**Logic:**
1. Nhận file (multipart/form-data), validate: JPG/PNG/WEBP, ≤ 5MB
2. Upload lên Cloudinary với transform: `width=400, height=600, crop=fill`
3. Trả về `secure_url`
4. Caller update `user_books.physical_cover_url` hoặc `book_catalog.cover_url`

**Acceptance:**
- [ ] Upload ảnh hợp lệ → nhận URL Cloudinary
- [ ] File > 5MB → 422
- [ ] File không phải ảnh → 422

---

### P1.7 — Frontend: Auth & routing

**Depends on:** P1.3

**Output:**
- `frontend/src/stores/authStore.ts` — Zustand store: user, tokens, login/logout actions
- `frontend/src/api/index.ts` — axios instance, request interceptor (attach token), response interceptor (auto refresh khi 401)
- `frontend/src/pages/LoginPage.tsx` — nút "Đăng nhập bằng Google" → redirect `/api/auth/google`
- `frontend/src/components/ProtectedRoute.tsx` — redirect về login nếu chưa auth
- `frontend/src/App.tsx` — react-router setup với protected routes

**Auth flow frontend:**
1. User vào `/` → nếu chưa có token → LoginPage
2. Click Google → redirect `/api/auth/google`
3. Backend redirect về frontend kèm token trong query params hoặc cookie
4. Frontend lưu token → authStore → redirect `/home`

**Axios interceptor:**
- Request: `Authorization: Bearer {access_token}`
- Response 401: gọi `POST /api/auth/refresh` → nếu thành công → retry request gốc; nếu fail → logout + redirect login

**Acceptance:**
- [ ] Chưa login → mọi route protected đều redirect về `/`
- [ ] Login xong → redirect `/home`, token lưu được
- [ ] Token hết hạn → tự refresh không cần user làm gì

---

### P1.8 — Frontend: Tủ sách cá nhân

**Depends on:** P1.5, P1.7

**Output:**
- `frontend/src/pages/BookshelfPage.tsx`
- `frontend/src/pages/BookDetailPage.tsx`
- `frontend/src/pages/AddBookPage.tsx`
- `frontend/src/components/book/BookCard.tsx`
- `frontend/src/components/book/BookForm.tsx`
- `frontend/src/components/book/ISBNLookup.tsx`

**BookshelfPage:**
- Grid 3-4 cột (desktop), 2 cột (tablet), 1 cột (mobile)
- Filter bar: status tabs, can_lend toggle
- Search input với debounce 300ms
- Infinite scroll (react-query `useInfiniteQuery`)
- Empty state khi không có sách

**AddBookPage — luồng thêm sách:**
1. Bước 1: Nhập ISBN → call `GET /api/catalog/lookup/isbn/{isbn}` → nếu có → điền sẵn form; nếu không có → form trắng
2. Bước 2: Form đầy đủ gồm 2 tab:
   - Tab "Thông tin sách": title, authors, publisher, year, cover upload
   - Tab "Thông tin cá nhân": acquired_how, gift_from, purchase_price, purchase_where, purchase_reason, status, started_at, finished_at, personal_rating, met_expectations, personal_note, can_lend, deposit_amount, lend_note, tags

**BookDetailPage:** Hiển thị đầy đủ + edit inline (click vào field để sửa) + nút xoá.

**Acceptance:**
- [ ] Add sách ISBN → form điền sẵn, lưu → hiện trong grid
- [ ] Filter status hoạt động không cần reload
- [ ] Empty state đúng khi tủ trống

---

## Phase 2 — Lending Core

### P2.1 — Phone OTP verification

**Depends on:** P1.3

**Input files:** `requirements.md` (FR-AUTH-04)

**Output:**
- `backend/app/api/routes/auth.py` (thêm 2 endpoints)
- Cần chọn SMS provider: dùng **Vonage** (có số VN) hoặc mock bằng log nếu chưa có account

**Endpoints:**
```
POST /api/auth/phone/send-otp    body: { phone_number: "0912345678" }
POST /api/auth/phone/verify      body: { phone_number, otp }
```

**Logic:**
- Sinh OTP 6 chữ số, lưu vào bảng `phone_otps` (phone, otp_hash, expires_at, attempt_count)
- `expires_at = now + 5 phút`
- Gửi qua SMS (hoặc log ra console nếu dev mode)
- Verify: check OTP khớp, chưa hết hạn, attempt < 3 → update `users.phone_number`, `phone_verified = true`
- Resend: chỉ cho phép nếu OTP cũ đã hơn 60 giây

**Rate limiting:** 3 OTP sai liên tiếp → lock 10 phút (lưu trong `phone_otps.locked_until`)

**Dev mode:** Nếu `SMS_PROVIDER=mock` trong env → chỉ log OTP ra console, không gửi SMS thật.

**Acceptance:**
- [ ] Send OTP → OTP lưu DB
- [ ] Verify đúng → phone_verified = true
- [ ] Verify sai 3 lần → 429 locked
- [ ] Resend trước 60s → 429

---

### P2.2 — Buildings API

**Depends on:** P1.2, P1.3

**Input files:** `requirements.md` (Section 3.3), `design.md` (FR-BUILDING-*)

**Output:** `backend/app/api/routes/community.py`

**Endpoints:**
```
POST /api/buildings              → tạo building, join luôn, trả { building, invite_code }
POST /api/buildings/join         → body: { invite_code } → join building
GET  /api/buildings/me           → info building đang ở
GET  /api/buildings/books        → sách available trong toà nhà (can_lend=true, no active loan, not owned by current user)
GET  /api/buildings/members      → danh sách thành viên
```

**Logic `/api/buildings/books`:**
```sql
SELECT ub.*, u.name as owner_name, bc.*
FROM user_books ub
JOIN users u ON u.id = ub.user_id
JOIN book_catalog bc ON bc.id = ub.catalog_id
WHERE ub.can_lend = true
  AND ub.user_id != {current_user_id}
  AND u.building_id = {current_user.building_id}
  AND NOT EXISTS (
    SELECT 1 FROM loans l WHERE l.user_book_id = ub.id AND l.status = 'active'
  )
ORDER BY ub.updated_at DESC
```

**Blacklist check cho `/api/buildings/books`:** Với mỗi sách, annotate `is_blocked = true/false` để frontend ẩn nút request nếu current_user bị lender block. (Không filter ra khỏi list, chỉ annotate.)

**Acceptance:**
- [ ] Tạo building → invite_code 8 chars unique
- [ ] Join bằng code đúng → thành công
- [ ] Join code sai → 404
- [ ] `/buildings/books` không hiện sách của chính mình
- [ ] Sách có active loan không hiện trong danh sách

---

### P2.3 — Loan requests API

**Depends on:** P1.2, P1.3, P2.2

**Input files:** `requirements.md` (Section 3.4), `design.md` (Section 5 — Lending endpoints)

**Output:** `backend/app/api/routes/loans.py`, `backend/app/services/loan_service.py`

**Endpoints:**
```
POST   /api/books/{book_id}/request-loan      → borrower gửi request
GET    /api/loan-requests                     → lender xem requests gửi đến (filter: status)
GET    /api/loan-requests/sent                → borrower xem requests đã gửi
PUT    /api/loan-requests/{id}/approve        → body: { agreed_deposit, meet_location }
PUT    /api/loan-requests/{id}/reject         → body: { reason? }
DELETE /api/loan-requests/{id}               → borrower cancel (chỉ khi status=pending)
```

**Validation khi gửi request:**
- `borrower.phone_verified = true` → nếu không → 403 "Cần verify số điện thoại"
- Kiểm tra `BorrowerBlacklist` (lender_id = book.user_id, blocked_user_id = current_user) → nếu bị block → 403 "Không thể gửi yêu cầu"
- Không có pending request nào cho sách này từ user này → nếu có → 409
- Rate limit: 10 requests/ngày/user → 429

**Sau approve:** Tạo notification cho borrower type `loan_request_approved` kèm `agreed_deposit` và `meet_location` trong body.

**Sau reject:** Tạo notification cho borrower type `loan_request_rejected`.

**Acceptance:**
- [ ] Borrower chưa verify phone → 403
- [ ] Borrower bị blacklist → 403
- [ ] Approve → notification gửi đến borrower
- [ ] Borrower cancel pending request → thành công; cancel approved request → 409

---

### P2.4 — Active loans API

**Depends on:** P2.3

**Output:** Thêm vào `backend/app/api/routes/loans.py`

**Endpoints:**
```
GET    /api/loans                    → list loans của current_user (cả lender lẫn borrower role; filter: status)
PUT    /api/loans/{id}/confirm       → lender confirm đã trao sách → status = 'active'
PUT    /api/loans/{id}/return        → lender mark đã nhận lại → status = 'returned'
```

**Logic `confirm`:**
- Chỉ lender mới gọi được
- Tạo Loan record từ LoanRequest đã approved
- Cập nhật LoanRequest.status = 'confirmed'

**Logic `return`:**
- Chỉ lender mới gọi được
- Cập nhật `returned_at = today`, `status = 'returned'`
- Tạo notification cho borrower "Lender đã xác nhận nhận lại sách [X]"

**Acceptance:**
- [ ] Borrower gọi confirm → 403
- [ ] Confirm → loan active, sách biến khỏi community shelf
- [ ] Return → loan returned, sách hiện lại community shelf

---

### P2.5 — Notifications API + Scheduler

**Depends on:** P1.2, P1.3

**Output:**
- `backend/app/api/routes/notifications.py`
- `backend/app/core/scheduler.py`

**Endpoints:**
```
GET /api/notifications              → list 50 notifications mới nhất của current_user
PUT /api/notifications/{id}/read    → mark read
PUT /api/notifications/read-all
```

**Scheduler (APScheduler):**
```python
# Chạy mỗi ngày 9:00 sáng
def daily_loan_reminders():
    # Lấy tất cả active loans có due_at
    # due_at == today + 3 → tạo notification 'loan_due_soon'
    # due_at == today → tạo notification 'loan_due_today'
    # due_at < today → mỗi 7 ngày tạo 'loan_overdue'
    # Không tạo trùng: check notification đã tồn tại cùng type + loan + ngày hôm nay
```

**`notification_service.py`:** Hàm `create_notification(user_id, type, title, body, actor_id, content_type, content_id)` — dùng ở nhiều nơi.

**Acceptance:**
- [ ] GET notifications trả đúng của current_user
- [ ] Mark read → is_read = true
- [ ] Scheduler job không tạo trùng notification trong ngày

---

### P2.6 — Frontend: Community & Lending

**Depends on:** P2.2, P2.3, P2.4, P2.5, P1.7

**Output:**
- `frontend/src/pages/CommunityPage.tsx` — tủ sách toà nhà
- `frontend/src/pages/LendingPage.tsx` — quản lý cho mượn (tabs: Chờ xử lý / Đang mượn / Lịch sử)
- `frontend/src/components/lending/LoanRequestForm.tsx`
- `frontend/src/components/lending/LoanRequestCard.tsx` — approve / reject với form
- `frontend/src/components/lending/ActiveLoanCard.tsx`
- `frontend/src/components/shared/PhoneVerifyModal.tsx`

**CommunityPage:**
- Hiển thị grid sách available từ toà nhà
- Mỗi card: ảnh bìa, tên sách, tên chủ, tiền cọc, nút "Yêu cầu mượn"
- Nút bị disabled (tooltip giải thích) nếu: đang có pending request, bị blacklist (`is_blocked = true`)
- Click nút → nếu `phone_verified = false` → mở `PhoneVerifyModal`; nếu đã verify → mở `LoanRequestForm`

**LendingPage — 3 tabs:**
1. **Chờ xử lý** (lender view): danh sách `loan_requests` đang pending → approve (form: cọc + địa điểm) / reject
2. **Đang mượn**: active loans — cả chiều cho mượn lẫn đi mượn; hiện badge đỏ nếu quá hạn; nút "Đã nhận lại" (lender only)
3. **Lịch sử**: returned + cancelled loans

**Notification polling:** `useEffect` gọi `GET /api/notifications` mỗi 30 giây, hiển thị badge số ở navbar.

**Acceptance:**
- [ ] Community shelf ẩn sách của chính mình
- [ ] Send request → sách hiện "Đang chờ xử lý" với borrower
- [ ] Approve → confirm flow → loan active
- [ ] Badge notification cập nhật sau max 30s

---

## Phase 3 — Trust & Polish

### P3.1 — Borrower rating & blacklist API

**Depends on:** P2.4

**Input files:** `requirements.md` (Section 3.5)

**Output:** Thêm vào `backend/app/api/routes/loans.py` + `backend/app/api/routes/community.py`

**Endpoints:**
```
POST   /api/loans/{id}/rate          → body: { is_positive, note, block_user? }
GET    /api/blacklist                 → danh sách blacklist của current_user
POST   /api/blacklist                 → body: { blocked_user_id, reason }
DELETE /api/blacklist/{user_id}      → unblock
```

**Logic rate:**
- Chỉ lender được rate
- Loan phải ở trạng thái `returned` hoặc `lost`
- `UNIQUE(loan_id)` → không rate 2 lần
- Nếu `block_user = true` → tạo thêm `BorrowerBlacklist` record
- Cancel pending requests từ user bị block nếu có

**Acceptance:**
- [ ] Rate thành công → BorrowerRating tạo
- [ ] Rate 2 lần → 409
- [ ] Block user → pending requests của họ bị cancelled

---

### P3.2 — Public profile API

**Depends on:** P1.3, P1.5

**Input files:** `requirements.md` (Section 3.6)

**Output:** `backend/app/api/routes/public.py`

**Endpoints:**
```
GET /api/public/users/{slug}          → profile info (name, bio, avatar, stats)
GET /api/public/users/{slug}/books    → sách public của user (is_public=true)
```

**Logic:**
- User.is_public = false → 404 (không để lộ slug tồn tại)
- Không trả về: purchase_price, personal_note, phone_number, blacklist

**Acceptance:**
- [ ] Profile private → 404
- [ ] Sách `is_public=false` không hiện dù profile public

---

### P3.3 — Frontend: Trust + Public profile

**Depends on:** P3.1, P3.2

**Output:**
- `frontend/src/components/lending/BorrowerRating.tsx` — modal sau khi mark returned
- `frontend/src/pages/SettingsPage.tsx` — tab Blacklist (list + unblock)
- `frontend/src/pages/PublicProfilePage.tsx` — `/u/{slug}`

**BorrowerRating:** Sau khi lender click "Đã nhận lại" → dialog hỏi "Muốn đánh giá người mượn không?" → form: 👍/👎 + textarea note + checkbox "Block người này"

**SettingsPage blacklist tab:** Danh sách người bị block: avatar, tên, lý do, ngày block, nút Unblock.

**Acceptance:**
- [ ] Rate dialog hiện sau return
- [ ] Unblock → người đó có thể request lại
- [ ] Public profile không hiện personal fields

---

### P3.4 — Stats API + Frontend

**Depends on:** P1.5, P2.4

**Input files:** `requirements.md` (Section 3.8)

**Output:**
- `backend/app/api/routes/stats.py`
- `frontend/src/pages/StatsPage.tsx`

**Endpoints:**
```
GET /api/stats/summary    → { total_books, by_status: {...}, read_this_year, read_this_month }
GET /api/stats/reading    → { monthly: [{ month: "2026-01", count: 3 }, ...] }  (12 tháng)
GET /api/stats/lending    → { total_lent, total_borrowed, on_time_rate, most_lent_books }
```

**Frontend StatsPage:** 3 sections với số liệu + bar chart tốc độ đọc (dùng `recharts` hoặc thuần CSS bars).

**Acceptance:**
- [ ] Summary đúng với dữ liệu thực
- [ ] Lending stats chỉ tính loans `returned` hoặc `lost`

---

### P3.5 — Dark mode + Mobile responsive

**Depends on:** P1.8, P2.6

**Mô tả:** Polish UI cho toàn bộ frontend.

**Checklist:**
- [ ] Dark mode toggle trong navbar, lưu `localStorage`
- [ ] Detect `prefers-color-scheme` lần đầu
- [ ] Tất cả pages responsive từ 375px: grid sách 1 cột mobile, 2 cột tablet, 3-4 cột desktop
- [ ] Form inputs touch-friendly (min-height 44px)
- [ ] Toast notifications (shadcn `Toaster`) cho success/error actions
- [ ] Loading skeletons cho lists

---

### P3.6 — ISBN camera scanner (Phase 3, optional)

**Depends on:** P1.8

**Output:** `frontend/src/components/book/ISBNScanner.tsx`

**Thư viện:** `html5-qrcode`

**Acceptance:**
- [ ] Scan thành công → ISBN điền vào form
- [ ] Browser không hỗ trợ camera → nút ẩn, không crash

---

## Phase 4 — Polish & Import

### P4.1 — Goodreads CSV import

**Depends on:** P1.5

**Output:** `backend/app/api/routes/books.py` (thêm endpoint), `backend/app/services/import_service.py`

**Endpoint:** `POST /api/books/import/goodreads` — multipart file upload (CSV)

**Logic:**
1. Parse CSV (Goodreads export format: Title, Author, ISBN, My Rating, Date Read, Bookshelves...)
2. Với mỗi row: lookup BookCatalog bằng ISBN hoặc title → tạo UserBook
3. Map Goodreads shelf → status: `read` / `to-read` / `currently-reading`
4. Map `My Rating` → `personal_rating`
5. Return: `{ imported: N, skipped: M, errors: [...] }`

**Acceptance:**
- [ ] File CSV hợp lệ → import được
- [ ] Sách đã tồn tại trong tủ → skip, không duplicate
- [ ] File sai format → lỗi rõ

---

### P4.2 — End-to-end tests (happy paths)

**Depends on:** P3.x (hoàn thành Phase 3)

**Output:** `backend/tests/test_happy_paths.py` dùng `pytest` + `httpx.AsyncClient`

**Test cases theo `requirements.md` Section 8:**
1. Onboarding user mới (mock Google OAuth)
2. Thêm sách qua ISBN
3. Mượn sách từ hàng xóm (full flow: request → approve → confirm → return)
4. Rate borrower + blacklist
5. Nhắc hạn trả (trigger scheduler manually)

**Acceptance:**
- [ ] Tất cả 5 happy paths pass
- [ ] Không có flaky test (chạy 3 lần liên tiếp đều pass)

---

## Tóm tắt thứ tự thực hiện

```
P1.1 (scaffold)
    ├── P1.2 (models)
    │   ├── P1.3 (auth)
    │   │   ├── P1.7 (fe: auth)
    │   │   │   └── P1.8 (fe: shelf)
    │   │   ├── P2.1 (phone OTP)
    │   │   ├── P2.2 (buildings)
    │   │   │   ├── P2.3 (loan requests)
    │   │   │   │   └── P2.4 (active loans)
    │   │   │   │       ├── P3.1 (trust)
    │   │   │   │       └── P3.4 (stats)
    │   │   │   └── P2.6 (fe: community)
    │   │   └── P3.2 (public profile)
    │   └── P2.5 (notifications)
    ├── P1.4 (google books)
    │   └── P1.5 (books API)
    └── P1.6 (cloudinary)
```

**Có thể chạy song song:**
- P1.4 + P1.6 (không phụ thuộc nhau)
- P1.7 + P1.5 (sau khi có P1.3 và P1.2)
- P2.1 + P2.2 + P2.5 (sau P1.3)
- P3.3 + P3.4 + P3.5 (sau P3.1 + P3.2)
