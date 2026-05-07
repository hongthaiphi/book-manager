# Book Manager — Technical Design

## 1. Tổng quan

**Book Manager** là webapp quản lý tủ sách cá nhân, tập trung vào hai việc:

1. **Số hoá tủ sách** — catalog sách đang có, ghi chú mua ở đâu, giá bao nhiêu, có xứng đáng không
2. **Cho mượn trong cộng đồng** — hiện tại trong phạm vi một toà nhà, người mượn phải đăng ký và chịu trách nhiệm

Social features (review công khai, follow, feed) là optional — xem xét ở Phase 5 sau khi core đã ổn định.

---

## 2. Tech Stack

| Layer | Công nghệ | Lý do chọn |
|-------|-----------|------------|
| Frontend | React + TypeScript + Vite | Fast dev, type-safe |
| UI | Tailwind CSS + shadcn/ui | Đẹp, flexible, không cần thiết kế từ đầu |
| State | Zustand | Đơn giản, nhẹ hơn Redux |
| Backend | FastAPI (Python) | Nhanh, auto docs, dùng được thư viện Python |
| Database | PostgreSQL | Relational, phù hợp |
| ORM | SQLAlchemy + Alembic | Migrations dễ quản lý |
| Auth | Google OAuth 2.0 | Gmail login, không cần quản lý password |
| Search | PostgreSQL full-text search | Đủ dùng cho scale nhỏ |
| Book metadata | Google Books API | Auto-fill từ ISBN |
| File storage | Cloudinary | Lưu ảnh bìa / ảnh thực tế của sách |
| Deploy | Docker Compose | Local dev đồng nhất |

**Không dùng ngay (thêm sau nếu cần):**
- Redis — thêm vào Phase 5+ nếu performance cần cải thiện
- SSE / WebSocket — notifications dùng polling trước (đơn giản hơn nhiều)
- Tiptap rich text editor — personal notes dùng textarea đơn giản

---

## 3. Kiến trúc cốt lõi

### 3.1 Tách book_catalog và user_books

Cùng một cuốn "Nhà Giả Kim" có thể được nhiều người sở hữu. Hệ thống tách:

```
book_catalog (thực thể sách chung — 1 bản/ISBN)
    └── user_books (quan hệ cá nhân: bản sách tôi đang có, ghi chú của tôi)
            ├── loan_requests (yêu cầu mượn từ người khác)
            └── loans (phiếu mượn đang active)
```

**Tại sao cần tách?**
- Cùng cuốn "Atomic Habits", 10 người trong toà có thể sở hữu → 10 `user_books` record
- Nhưng chỉ 1 entry trong `book_catalog` để tra cứu metadata chung
- Mỗi người có ghi chú riêng (giá mua, cảm nhận...) không ảnh hưởng nhau

### 3.2 Lending flow trong toà nhà

```
Lender đánh dấu sách "sẵn sàng cho mượn"
    ↓
Borrower (trong cùng toà nhà) gửi loan_request
    ↓
Lender approve (kèm thoả thuận cọc + địa điểm hẹn) hoặc reject
    ↓ (approved)
Gặp nhau ngoài đời, trao sách, chuyển khoản cọc
    ↓
Lender confirm → loan status = active
    ↓
[Thời gian mượn... notification nhắc khi gần hạn]
    ↓
Sách trả về → Lender mark returned
    ↓
Lender có thể rate borrower (tùy chọn)
```

> Deposit thực tế xảy ra ngoài hệ thống (bank transfer). App chỉ lưu `agreed_deposit` làm reference.

### 3.3 Trust model

- Người mượn cần xác thực **số điện thoại** khi đăng ký (ngoài Google login)
- Lender có thể **blacklist** borrower — người bị block không thể gửi request mượn sách của lender đó
- Rating borrower là **private** (chỉ lender thấy), không public

---

## 4. Database Schema

### 4.1 users
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
google_sub      VARCHAR(255) UNIQUE NOT NULL   -- Google OAuth subject ID
email           VARCHAR(255) UNIQUE NOT NULL
name            VARCHAR(100) NOT NULL
avatar_url      VARCHAR(500)
phone_number    VARCHAR(20)                    -- bắt buộc để mượn sách
phone_verified  BOOLEAN DEFAULT FALSE
profile_slug    VARCHAR(50) UNIQUE             -- /u/phihong
bio             TEXT
is_public       BOOLEAN DEFAULT TRUE           -- tủ sách có hiện công khai không
building_id     UUID REFERENCES buildings(id)  -- toà nhà đang ở
created_at      TIMESTAMP DEFAULT NOW()
updated_at      TIMESTAMP DEFAULT NOW()
```

### 4.2 buildings (toà nhà / cộng đồng)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
name            VARCHAR(200) NOT NULL           -- "Vinhomes Central Park T2"
address         TEXT
invite_code     VARCHAR(20) UNIQUE              -- code để join toà nhà
created_at      TIMESTAMP DEFAULT NOW()
```

### 4.3 book_catalog (thực thể sách chung)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
isbn            VARCHAR(20) UNIQUE
title           VARCHAR(500) NOT NULL
authors         TEXT[]
publisher       VARCHAR(200)
published_at    DATE
cover_url       VARCHAR(500)
language        VARCHAR(10) DEFAULT 'vi'
page_count      INTEGER
description     TEXT
genres          VARCHAR(100)[]
source          VARCHAR(50)                    -- 'google_books' | 'manual'
created_at      TIMESTAMP DEFAULT NOW()
updated_at      TIMESTAMP DEFAULT NOW()
```

### 4.4 user_books (tủ sách cá nhân) ← TRỌNG TÂM
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id         UUID REFERENCES users(id) ON DELETE CASCADE
catalog_id      UUID REFERENCES book_catalog(id)

-- Trạng thái đọc
status          VARCHAR(20) NOT NULL
-- 'want_to_read' | 'reading' | 'read' | 'did_not_finish'
started_at      DATE
finished_at     DATE

-- Thông tin mua / nhận sách
acquired_how    VARCHAR(20)                    -- 'bought' | 'gift' | 'other'
gift_from       VARCHAR(100)                   -- nếu được tặng: từ ai
purchase_price  NUMERIC(10,2)                  -- giá mua
purchase_where  VARCHAR(200)                   -- mua ở đâu (Fahasa, Shopee, hội sách...)
purchase_reason TEXT                           -- tại sao mua

-- Đánh giá sau khi đọc (private)
personal_rating  SMALLINT CHECK (personal_rating BETWEEN 1 AND 5)
met_expectations BOOLEAN                       -- có xứng đáng với kì vọng trước khi mua?
personal_note    TEXT                          -- ghi chú riêng tư

-- Ảnh thực tế cuốn sách (nếu khác cover online)
physical_cover_url VARCHAR(500)

-- Cho mượn
can_lend        BOOLEAN DEFAULT FALSE          -- có cho mượn không
deposit_amount  NUMERIC(10,2) DEFAULT 0        -- tiền cọc yêu cầu (0 = không cần cọc)
lend_note       TEXT                           -- ghi chú điều kiện mượn

-- Metadata
tags            VARCHAR(50)[]                  -- nhãn cá nhân
is_public       BOOLEAN DEFAULT TRUE
created_at      TIMESTAMP DEFAULT NOW()
updated_at      TIMESTAMP DEFAULT NOW()

UNIQUE(user_id, catalog_id)
```

### 4.5 loan_requests (yêu cầu mượn)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_book_id    UUID REFERENCES user_books(id) ON DELETE CASCADE
lender_id       UUID REFERENCES users(id)
borrower_id     UUID REFERENCES users(id)

message         TEXT                           -- tin nhắn từ người muốn mượn
status          VARCHAR(20) DEFAULT 'pending'
-- 'pending' | 'approved' | 'rejected' | 'cancelled'

-- Điền khi approve
agreed_deposit  NUMERIC(10,2)                  -- cọc đã thoả thuận
meet_location   TEXT                           -- "tầng trệt, chiều thứ 6"
agreed_at       TIMESTAMP

rejected_reason TEXT
created_at      TIMESTAMP DEFAULT NOW()
updated_at      TIMESTAMP DEFAULT NOW()
```

### 4.6 loans (phiếu mượn đang active)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
loan_request_id UUID REFERENCES loan_requests(id)
user_book_id    UUID REFERENCES user_books(id) ON DELETE CASCADE
lender_id       UUID REFERENCES users(id)
borrower_id     UUID REFERENCES users(id)

lent_at         DATE NOT NULL DEFAULT CURRENT_DATE
due_at          DATE
returned_at     DATE

status          VARCHAR(20) DEFAULT 'active'
-- 'active' | 'returned' | 'overdue' | 'lost'

lender_note     TEXT
created_at      TIMESTAMP DEFAULT NOW()
updated_at      TIMESTAMP DEFAULT NOW()
```

### 4.7 borrower_ratings (đánh giá người mượn — private)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
loan_id         UUID REFERENCES loans(id)
lender_id       UUID REFERENCES users(id)
borrower_id     UUID REFERENCES users(id)
is_positive     BOOLEAN NOT NULL               -- positive hoặc negative
note            TEXT                           -- lý do (không trả đúng hạn, sách hỏng...)
created_at      TIMESTAMP DEFAULT NOW()

UNIQUE(loan_id)                                -- 1 loan → 1 rating
```

### 4.8 borrower_blacklist
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
lender_id       UUID REFERENCES users(id)
blocked_user_id UUID REFERENCES users(id)
reason          TEXT
created_at      TIMESTAMP DEFAULT NOW()

UNIQUE(lender_id, blocked_user_id)
CHECK (lender_id != blocked_user_id)
```

### 4.9 notifications
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id         UUID REFERENCES users(id)
type            VARCHAR(50)
-- 'loan_request_received'   -- có người muốn mượn sách của mình
-- 'loan_request_approved'   -- yêu cầu mượn được chấp nhận
-- 'loan_request_rejected'   -- yêu cầu mượn bị từ chối
-- 'loan_due_soon'           -- sắp đến hạn trả (3 ngày trước)
-- 'loan_overdue'            -- quá hạn trả
title           VARCHAR(200)
body            TEXT
actor_id        UUID REFERENCES users(id)      -- người thực hiện hành động
content_type    VARCHAR(20)                    -- 'loan_request' | 'loan'
content_id      UUID
is_read         BOOLEAN DEFAULT FALSE
created_at      TIMESTAMP DEFAULT NOW()
```

---

## 5. API Endpoints

### Auth (Google OAuth)
```
GET  /api/auth/google                         -- redirect đến Google OAuth
GET  /api/auth/google/callback                -- Google callback, trả về JWT
POST /api/auth/refresh
POST /api/auth/logout
POST /api/auth/phone/send-otp                 -- gửi OTP xác thực số điện thoại
POST /api/auth/phone/verify                   -- confirm OTP
```

### Book Catalog
```
GET  /api/catalog/lookup/isbn/{isbn}          -- tra Google Books theo ISBN
GET  /api/catalog/search?q=                   -- tìm sách (Google Books + nội bộ)
GET  /api/catalog/{id}                        -- chi tiết sách
```

### User Books (tủ sách cá nhân)
```
GET    /api/books                             -- tủ sách của mình (filter, sort, search)
POST   /api/books                             -- thêm sách vào tủ
GET    /api/books/{id}                        -- chi tiết 1 cuốn
PUT    /api/books/{id}                        -- cập nhật mọi field
DELETE /api/books/{id}                        -- xóa khỏi tủ
```

### Lending
```
-- Loan requests
GET    /api/loan-requests                     -- requests gửi đến mình (lender view)
GET    /api/loan-requests/sent                -- requests mình đã gửi (borrower view)
POST   /api/books/{book_id}/request-loan      -- gửi yêu cầu mượn
PUT    /api/loan-requests/{id}/approve        -- chấp nhận (kèm agreed_deposit, meet_location)
PUT    /api/loan-requests/{id}/reject         -- từ chối (kèm lý do)
DELETE /api/loan-requests/{id}               -- borrower tự cancel

-- Active loans
GET    /api/loans                             -- loans của mình (cả 2 chiều)
PUT    /api/loans/{id}/confirm                -- lender confirm đã giao sách → active
PUT    /api/loans/{id}/return                 -- lender mark đã nhận lại sách
POST   /api/loans/{id}/rate                   -- rate borrower sau khi trả

-- Blacklist
GET    /api/blacklist                         -- danh sách blacklist của mình
POST   /api/blacklist                         -- block { blocked_user_id, reason }
DELETE /api/blacklist/{blocked_user_id}       -- unblock
```

### Community (toà nhà)
```
POST   /api/buildings                         -- tạo toà nhà mới
POST   /api/buildings/join                    -- join bằng invite_code
GET    /api/buildings/me                      -- info toà nhà đang ở
GET    /api/buildings/books                   -- sách available từ mọi người trong toà
GET    /api/buildings/members                 -- danh sách thành viên
```

### Public Profile + Notifications + Stats
```
GET /api/public/users/{slug}                  -- profile công khai
GET /api/public/users/{slug}/books            -- tủ sách công khai (is_public = true)

GET /api/notifications                        -- danh sách thông báo (polling)
PUT /api/notifications/{id}/read
PUT /api/notifications/read-all

GET /api/stats/summary                        -- tổng sách, đã đọc, đang cho mượn...
GET /api/stats/reading-pace                   -- tốc độ đọc theo tháng
GET /api/stats/lending                        -- thống kê cho mượn / mượn
```

---

## 6. Thiết kế chi tiết: Lending

### 6.1 Trạng thái cho mượn của một cuốn sách

Không dùng `status = 'lent_out'` trong `user_books` (status đó mô tả trạng thái đọc, không phải vật lý). Trạng thái cho mượn được suy ra từ `loans` table:

```
user_book.can_lend = true
    → Check: có loan nào với status='active' không?
        → Không có → [Có thể mượn]
        → Có → [Đang được mượn bởi X]
```

### 6.2 Màn hình "Tủ sách toà nhà"

Hiển thị tất cả sách `can_lend = true` và không có active loan, từ mọi thành viên cùng building:

```
┌─────────────────────────────────────────────────────┐
│  📚 Tủ sách toà nhà                   15 cuốn sẵn  │
├─────────────────────────────────────────────────────┤
│  [Cover] Atomic Habits                              │
│          James Clear                                │
│          Chủ: PhiHong · Tầng 5  •  Cọc: 50.000đ  │
│          [Yêu cầu mượn]                            │
│                                                     │
│  [Cover] Nhà Giả Kim                               │
│          Paulo Coelho                               │
│          Chủ: MinhDev · Tầng 2  •  Không cần cọc  │
│          [Yêu cầu mượn]                            │
└─────────────────────────────────────────────────────┘
```

### 6.3 Flow yêu cầu mượn chi tiết

```
Borrower click [Yêu cầu mượn]
    ↓
Kiểm tra:
  - phone_verified = true? (nếu không → redirect verify phone)
  - Không nằm trong blacklist của lender?
    ↓
Điền form: tin nhắn ngắn (optional) → Submit
    ↓
Lender nhận notification "Có người muốn mượn [Tên sách]"
    ↓
Lender vào xem → Approve hoặc Reject
    ↓ Approve
Lender điền: tiền cọc thoả thuận + địa điểm hẹn
Borrower nhận notification "Được chấp nhận — hẹn gặp ở X, cọc Y đồng"
    ↓
[Gặp nhau ngoài đời, trao sách, chuyển khoản cọc]
    ↓
Lender confirm trong app → Loan status = 'active'
    ↓
[Thời gian mượn]
Notification tự động nhắc borrower 3 ngày trước due_at
    ↓
Trả sách → Lender click [Đã nhận lại] → status = 'returned'
    ↓
Lender có thể rate: 👍 Tốt / 👎 Không tốt + ghi chú
```

### 6.4 Blacklist

Trigger để block:
- Lender mark loan là `lost`
- Lender rate negative và chọn "Block người này"
- Hoặc thủ công trong Settings

Khi bị block:
- Button [Yêu cầu mượn] ẩn đối với lender đó
- Không có thông báo gì cho borrower (silent block)

Lender quản lý blacklist trong `/settings/blacklist`:
- Xem danh sách, lý do, ngày block
- Có thể unblock bất kỳ lúc nào

---

## 7. Cấu trúc thư mục

```
book-manager/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py              -- Google OAuth + phone verify
│   │   │   │   ├── books.py             -- user_books CRUD
│   │   │   │   ├── catalog.py           -- book_catalog + Google Books API
│   │   │   │   ├── loans.py             -- loan_requests + loans + ratings + blacklist
│   │   │   │   ├── community.py         -- buildings, tủ sách toà nhà
│   │   │   │   ├── public.py            -- public profiles
│   │   │   │   ├── notifications.py
│   │   │   │   └── stats.py
│   │   │   └── deps.py                  -- auth dependency, get_current_user
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py              -- JWT + Google OAuth
│   │   │   └── scheduler.py             -- cron: nhắc hạn trả, mark overdue
│   │   ├── db/
│   │   │   ├── models.py                -- tất cả SQLAlchemy models
│   │   │   ├── schemas/                 -- Pydantic request/response schemas
│   │   │   │   ├── book.py
│   │   │   │   ├── loan.py
│   │   │   │   └── user.py
│   │   │   └── session.py
│   │   ├── services/
│   │   │   ├── google_books.py          -- Google Books API client
│   │   │   ├── loan_service.py          -- business logic cho lending flow
│   │   │   ├── notification_service.py
│   │   │   └── cloudinary_service.py
│   │   └── main.py
│   ├── migrations/                      -- Alembic migrations
│   ├── tests/
│   │   ├── test_books.py
│   │   └── test_loans.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/                      -- shadcn components
│   │   │   ├── book/
│   │   │   │   ├── BookCard.tsx          -- hiển thị 1 cuốn trong tủ
│   │   │   │   ├── BookForm.tsx          -- thêm / sửa sách (có đầy đủ personal fields)
│   │   │   │   ├── ISBNScanner.tsx       -- scan ISBN bằng camera (Phase 3)
│   │   │   │   └── CoverUpload.tsx       -- upload ảnh bìa thực tế
│   │   │   ├── lending/
│   │   │   │   ├── CommunityShelf.tsx    -- tủ sách toà nhà
│   │   │   │   ├── LoanRequestForm.tsx   -- form gửi yêu cầu mượn
│   │   │   │   ├── LoanRequestCard.tsx   -- card approve/reject (lender view)
│   │   │   │   ├── ActiveLoanCard.tsx    -- card theo dõi loan đang active
│   │   │   │   ├── BorrowerRating.tsx    -- form rate sau khi trả
│   │   │   │   └── BlacklistManager.tsx  -- quản lý blacklist
│   │   │   └── shared/
│   │   │       ├── StarRating.tsx
│   │   │       └── PhoneVerifyModal.tsx
│   │   ├── pages/
│   │   │   ├── BookshelfPage.tsx         -- tủ sách cá nhân
│   │   │   ├── BookDetailPage.tsx        -- chi tiết + edit một cuốn
│   │   │   ├── CommunityPage.tsx         -- tủ sách toà nhà
│   │   │   ├── LendingPage.tsx           -- quản lý cho mượn (lender + borrower view)
│   │   │   ├── NotificationsPage.tsx
│   │   │   ├── StatsPage.tsx
│   │   │   ├── SettingsPage.tsx          -- profile, phone verify, blacklist
│   │   │   └── PublicProfilePage.tsx
│   │   ├── stores/
│   │   │   ├── authStore.ts
│   │   │   ├── bookStore.ts
│   │   │   └── loanStore.ts
│   │   ├── hooks/
│   │   │   ├── useBooks.ts
│   │   │   ├── useLoans.ts
│   │   │   └── useNotifications.ts      -- polling mỗi 30s
│   │   └── api/                         -- axios wrappers cho từng endpoint
│   ├── Dockerfile
│   ├── vite.config.ts
│   └── package.json
│
├── docker-compose.yml
├── docker-compose.dev.yml
└── design.md
```

---

## 8. Luồng chính (User Flows)

### 8.1 Đăng ký và setup
```
Vào app → [Đăng nhập bằng Google]
    → Google OAuth → Tạo account tự động
    → Nhập số điện thoại → Nhận OTP → Verify
    → Nhập invite_code của toà nhà (hoặc tạo toà nhà mới)
    → Sẵn sàng dùng
```

### 8.2 Thêm sách vào tủ
```
Click [Thêm sách]
    ↓
Nhập ISBN → Google Books API tự fill title, author, cover
(hoặc tìm theo tên, hoặc nhập tay)
    ↓
Điền thông tin cá nhân:
    • Mua hay được tặng? Từ ai / mua ở đâu? Giá bao nhiêu?
    • Tại sao mua?
    • Trạng thái đọc hiện tại?
    • Cảm nhận cá nhân + có xứng đáng không? (nếu đã đọc)
    • Có cho mượn không? Cọc bao nhiêu?
    ↓
Lưu → Xuất hiện trong tủ sách
```

### 8.3 Mượn sách từ hàng xóm
```
Vào [Tủ sách toà nhà]
    → Xem danh sách sách available
    → Click [Yêu cầu mượn] trên cuốn thích
    → Nhập tin nhắn (optional) → Submit
    → Chờ lender reply (nhận notification khi approve/reject)
    → Nếu approve: gặp nhau, nhận sách, chuyển khoản cọc
    → Đọc sách
    → Trả sách → lender mark returned trong app
```

### 8.4 Quản lý cho mượn (lender view)
```
Vào [Quản lý cho mượn]
    → Tab "Chờ xử lý": approve / reject các requests
    → Tab "Đang cho mượn": ai đang mượn gì, hạn bao giờ
    → Tab "Lịch sử": các lần cho mượn trước
    → Khi trả: [Đã nhận lại] → Rate borrower nếu muốn
```

---

## 9. Tính năng theo phase

### Phase 1 — Catalog MVP (tuần 1-2)
- [ ] Google OAuth login
- [ ] Thêm sách bằng ISBN → auto-fill từ Google Books API
- [ ] Nhập tay nếu không có ISBN
- [ ] Đầy đủ personal fields: giá, mua ở đâu, tại sao, được tặng, cảm nhận, có xứng đáng
- [ ] Trạng thái đọc (want_to_read, reading, read, did_not_finish)
- [ ] Filter và search tủ sách cá nhân
- [ ] Upload ảnh bìa thực tế

### Phase 2 — Lending Core (tuần 3-4)
- [ ] Xác thực số điện thoại (OTP)
- [ ] Tạo / join toà nhà bằng invite_code
- [ ] Mark sách "sẵn sàng cho mượn" + đặt tiền cọc
- [ ] Tủ sách toà nhà: xem sách available từ hàng xóm
- [ ] Loan request flow: gửi → approve/reject → confirm giao sách
- [ ] Active loans: theo dõi ai đang mượn gì, hạn trả
- [ ] Mark đã trả
- [ ] Notifications (polling 30s)

### Phase 3 — Trust & Polish (tuần 5-6)
- [ ] Rate borrower sau khi trả (positive / negative + ghi chú)
- [ ] Blacklist borrower
- [ ] Scheduler nhắc hạn trả (3 ngày trước, ngày hết hạn)
- [ ] Auto-mark overdue khi quá hạn
- [ ] ISBN scan bằng camera (quagga2 hoặc html5-qrcode)
- [ ] Public profile `/u/{slug}`
- [ ] Dark mode + mobile responsive

### Phase 4 — Stats & Import (tuần 7)
- [ ] Dashboard thống kê (tổng sách, tốc độ đọc theo tháng, lending stats)
- [ ] Import sách từ Goodreads CSV
- [ ] Export danh sách tủ sách

### Phase 5 — Social (Optional, nếu muốn thách thức thêm)
- [ ] Review công khai + star rating
- [ ] Bình luận trên review
- [ ] Follow user
- [ ] Activity feed từ following
- [ ] Real-time notifications (Server-Sent Events)
- [ ] Redis cache cho vote counts và feed

---

## 10. Non-functional Requirements

| Yêu cầu | Mục tiêu |
|---------|----------|
| API response time (P95) | < 300ms |
| Auth | Google OAuth; JWT access 15 phút, refresh 30 ngày |
| Rate limit — loan request | 5 requests/ngày/user (tránh spam) |
| Image upload | Max 5MB, resize về 400×600px |
| Notifications polling | Mỗi 30 giây |
| Responsive | Mobile-first, hoạt động tốt từ 375px |

---

## 11. Environment Variables

```env
# Backend
DATABASE_URL=postgresql://user:pass@localhost:5432/bookmanager
SECRET_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_BOOKS_API_KEY=...
CLOUDINARY_URL=...
FRONTEND_URL=http://localhost:5173

# Frontend
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=...
```

---

## 12. Docker Compose (dev)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: bookmanager
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres]
    volumes: [./backend:/app]

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    env_file: .env
    volumes: [./frontend:/app]

volumes:
  pgdata:
```
