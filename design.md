# Book Manager — Technical Design

## 1. Tổng quan

**Book Manager** là webapp quản lý sách cá nhân kết hợp mạng xã hội đọc sách, cho phép người dùng:
- Quản lý tủ sách cá nhân (thêm, sửa, xóa, phân loại)
- Theo dõi trạng thái đọc (đang đọc, đã đọc, muốn đọc)
- **Viết review, chia sẻ cảm nhận chi tiết về từng cuốn sách**
- **Bình luận, thảo luận về sách với cộng đồng người đọc**
- **Vote (thích / không thích) trên review và bình luận**
- **Xem tổng hợp cảm nhận của nhiều người về cùng một cuốn sách**
- Chia sẻ tủ sách, danh sách sách qua link công khai
- Quản lý việc cho mượn sách

---

## 2. Tech Stack

| Layer | Công nghệ | Lý do chọn |
|-------|-----------|------------|
| Frontend | React + TypeScript + Vite | Fast dev, type-safe |
| UI | Tailwind CSS + shadcn/ui | Đẹp, flexible, không cần thiết kế từ đầu |
| State | Zustand | Đơn giản, nhẹ hơn Redux |
| Rich text editor | Tiptap | Editor viết review với format (bold, quote, spoiler block) |
| Backend | FastAPI (Python) | Nhanh, auto docs, dùng được thư viện Python |
| Database | PostgreSQL | Relational, phù hợp quan hệ phức tạp (votes, threads) |
| ORM | SQLAlchemy + Alembic | Migrations dễ quản lý |
| Auth | JWT (access + refresh token) | Stateless, đơn giản |
| Search | PostgreSQL full-text search | Đủ dùng, không cần Elasticsearch |
| Real-time | Server-Sent Events (SSE) | Thông báo mới, cập nhật vote count real-time |
| Book metadata | Google Books API | Tự động điền thông tin từ ISBN |
| File storage | Cloudinary | Lưu ảnh bìa |
| Cache | Redis | Cache vote counts, hot reviews, session |
| Deploy | Docker Compose | Local dev đồng nhất |

---

## 3. Kiến trúc Social Layer

### 3.1 Khái niệm cốt lõi

Hệ thống tách biệt **cuốn sách như một thực thể dùng chung** (canonical book) khỏi **quan hệ cá nhân của user với cuốn sách** (user's copy). Đây là nền tảng để social features hoạt động được.

```
book_catalog (thực thể chung, 1 bản / ISBN)
    ├── user_books (quan hệ cá nhân: trạng thái đọc, ghi chú riêng)
    ├── reviews (cảm nhận công khai, 1 user chỉ viết 1 review / sách)
    │       ├── review_reactions (emoji reaction: ❤️ 👍 😢 🤔 🔥)
    │       └── comments (bình luận vào review, có thread)
    │               └── comment_votes (upvote / downvote bình luận)
    └── reading_activity (feed hoạt động: ai đang đọc gì)
```

**Tại sao cần tách?**
- Cùng một cuốn "Nhà Giả Kim", 100 user sở hữu → 100 `user_books` record
- Nhưng chỉ có 1 entry trong `book_catalog` để tổng hợp: tổng reviews, điểm trung bình, feed thảo luận chung

### 3.2 Phân quyền trên social content

| Hành động | Chưa đăng nhập | Đã đăng nhập | Chính tác giả |
|-----------|---------------|-------------|--------------|
| Đọc review | ✅ | ✅ | ✅ |
| Đọc comment | ✅ | ✅ | ✅ |
| Vote review | ❌ | ✅ | ❌ (không tự vote) |
| Vote comment | ❌ | ✅ | ❌ (không tự vote) |
| Viết review | ❌ | ✅ (phải có sách trong tủ, status=read) | ✅ |
| Viết comment | ❌ | ✅ | ✅ |
| Sửa / xóa | ❌ | ❌ | ✅ |
| Report nội dung | ❌ | ✅ | ✅ |

---

## 4. Database Schema

### 4.1 users
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
email           VARCHAR(255) UNIQUE NOT NULL
password_hash   VARCHAR(255) NOT NULL
name            VARCHAR(100) NOT NULL
avatar_url      VARCHAR(500)
profile_slug    VARCHAR(50) UNIQUE         -- /u/phihong
bio             TEXT
website_url     VARCHAR(500)
reading_goal    SMALLINT                   -- mục tiêu số sách/năm
is_public       BOOLEAN DEFAULT TRUE
created_at      TIMESTAMP DEFAULT NOW()
updated_at      TIMESTAMP DEFAULT NOW()
```

### 4.2 book_catalog (thực thể sách dùng chung)
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
source          VARCHAR(50)               -- 'google_books' | 'manual'

-- Denormalized counters (cập nhật qua trigger hoặc service)
review_count    INTEGER DEFAULT 0
avg_rating      NUMERIC(3,2) DEFAULT 0    -- trung bình cộng rating từ reviews
reader_count    INTEGER DEFAULT 0         -- số user có sách này trong tủ

created_at      TIMESTAMP DEFAULT NOW()
updated_at      TIMESTAMP DEFAULT NOW()
```

### 4.3 user_books (quan hệ cá nhân user ↔ sách)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id         UUID REFERENCES users(id) ON DELETE CASCADE
catalog_id      UUID REFERENCES book_catalog(id)
tags            VARCHAR(50)[]              -- nhãn cá nhân
status          VARCHAR(20) NOT NULL       -- 'reading' | 'read' | 'want_to_read' | 'lent_out'
started_at      DATE
finished_at     DATE
is_public       BOOLEAN DEFAULT TRUE       -- hiện trên profile công khai
note            TEXT                       -- ghi chú riêng tư
source          VARCHAR(50)               -- 'google_books' | 'manual' | 'isbn_scan'
created_at      TIMESTAMP DEFAULT NOW()
updated_at      TIMESTAMP DEFAULT NOW()

UNIQUE(user_id, catalog_id)               -- 1 user chỉ có 1 bản của mỗi sách
```

### 4.4 reviews (cảm nhận công khai) ← TRỌNG TÂM

```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
catalog_id      UUID REFERENCES book_catalog(id) ON DELETE CASCADE
user_id         UUID REFERENCES users(id) ON DELETE CASCADE
user_book_id    UUID REFERENCES user_books(id)  -- liên kết với bản cá nhân

-- Nội dung
rating          SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5)
title           VARCHAR(300)               -- tiêu đề review (tùy chọn)
body            TEXT NOT NULL              -- nội dung review (Tiptap HTML, tối đa 10.000 ký tự)
body_plain      TEXT                       -- plain text để full-text search
has_spoiler     BOOLEAN DEFAULT FALSE      -- cảnh báo spoiler

-- Cảm xúc / mood tags (chọn nhiều)
-- Ví dụ: ['inspiring', 'emotional', 'thought_provoking', 'easy_read', 'dense', 'boring']
mood_tags       VARCHAR(50)[]

-- Trích dẫn yêu thích từ sách
favorite_quote  TEXT

-- Đối tượng đề xuất đọc
recommend_to    TEXT                       -- "Dành cho ai thích..."

-- Thống kê (denormalized, cập nhật realtime)
upvote_count    INTEGER DEFAULT 0
comment_count   INTEGER DEFAULT 0

-- Trạng thái
is_public       BOOLEAN DEFAULT TRUE
is_edited       BOOLEAN DEFAULT FALSE
created_at      TIMESTAMP DEFAULT NOW()
updated_at      TIMESTAMP DEFAULT NOW()

UNIQUE(user_id, catalog_id)               -- 1 user chỉ viết 1 review / sách
```

**Mood tags được định nghĩa sẵn:**

| Tag | Label | Emoji |
|-----|-------|-------|
| `inspiring` | Truyền cảm hứng | ✨ |
| `emotional` | Cảm động | 😢 |
| `thought_provoking` | Kích thích tư duy | 🧠 |
| `easy_read` | Dễ đọc | 😊 |
| `dense` | Nặng, đọc chậm | 📚 |
| `practical` | Thực tiễn, áp dụng được | 🔧 |
| `boring` | Nhàm chán | 😴 |
| `page_turner` | Không thể đặt xuống | 🔥 |
| `life_changing` | Thay đổi quan điểm sống | 🌟 |
| `overrated` | Bị đánh giá quá cao | 🤔 |
| `underrated` | Xứng đáng nổi tiếng hơn | 💎 |
| `reread_worthy` | Đọc lại nhiều lần vẫn hay | ♻️ |

### 4.5 review_reactions (emoji reaction trên review)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
review_id       UUID REFERENCES reviews(id) ON DELETE CASCADE
user_id         UUID REFERENCES users(id) ON DELETE CASCADE
emoji           VARCHAR(20) NOT NULL
-- Giá trị: 'heart' | 'thumbs_up' | 'wow' | 'sad' | 'fire' | 'thinking'
created_at      TIMESTAMP DEFAULT NOW()

UNIQUE(review_id, user_id, emoji)         -- 1 user chỉ react 1 loại emoji / review
-- Nhưng có thể react nhiều emoji khác nhau trên cùng 1 review
```

**Emoji palette:**

| Key | Emoji | Ý nghĩa |
|-----|-------|---------|
| `heart` | ❤️ | Yêu thích |
| `thumbs_up` | 👍 | Đồng ý, hữu ích |
| `wow` | 😮 | Bất ngờ |
| `sad` | 😢 | Cảm động |
| `fire` | 🔥 | Xuất sắc |
| `thinking` | 🤔 | Thú vị, đáng suy nghĩ |

### 4.6 comments (bình luận, có thread) ← TRỌNG TÂM
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
review_id       UUID REFERENCES reviews(id) ON DELETE CASCADE
user_id         UUID REFERENCES users(id) ON DELETE CASCADE
parent_id       UUID REFERENCES comments(id) ON DELETE CASCADE
-- NULL = comment gốc; non-NULL = reply vào comment cha

body            TEXT NOT NULL              -- tối đa 2000 ký tự
mentioned_user_ids UUID[]                 -- @mention: danh sách user được nhắc

-- Thống kê
upvote_count    INTEGER DEFAULT 0
downvote_count  INTEGER DEFAULT 0

-- Trạng thái
is_edited       BOOLEAN DEFAULT FALSE
is_deleted      BOOLEAN DEFAULT FALSE      -- soft delete, giữ thread
created_at      TIMESTAMP DEFAULT NOW()
updated_at      TIMESTAMP DEFAULT NOW()

-- Giới hạn thread: chỉ 1 cấp reply (comment → reply, reply không có reply)
-- Thực thi ở application layer, không phải DB constraint
```

### 4.7 comment_votes (vote trên bình luận)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
comment_id      UUID REFERENCES comments(id) ON DELETE CASCADE
user_id         UUID REFERENCES users(id) ON DELETE CASCADE
value           SMALLINT NOT NULL CHECK (value IN (1, -1))
-- 1 = upvote, -1 = downvote
created_at      TIMESTAMP DEFAULT NOW()

UNIQUE(comment_id, user_id)               -- 1 user chỉ vote 1 lần / comment
```

### 4.8 review_votes (vote tổng thể cho review — "review này có hữu ích không?")
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
review_id       UUID REFERENCES reviews(id) ON DELETE CASCADE
user_id         UUID REFERENCES users(id) ON DELETE CASCADE
value           SMALLINT NOT NULL CHECK (value IN (1, -1))
created_at      TIMESTAMP DEFAULT NOW()

UNIQUE(review_id, user_id)
```

### 4.9 follows (theo dõi user khác)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
follower_id     UUID REFERENCES users(id) ON DELETE CASCADE
following_id    UUID REFERENCES users(id) ON DELETE CASCADE
created_at      TIMESTAMP DEFAULT NOW()

UNIQUE(follower_id, following_id)
CHECK (follower_id != following_id)
```

### 4.10 content_reports (báo cáo nội dung vi phạm)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
reporter_id     UUID REFERENCES users(id)
content_type    VARCHAR(20) NOT NULL       -- 'review' | 'comment'
content_id      UUID NOT NULL
reason          VARCHAR(50) NOT NULL
-- 'spam' | 'spoiler_unmarked' | 'offensive' | 'misinformation' | 'other'
detail          TEXT
status          VARCHAR(20) DEFAULT 'pending' -- 'pending' | 'resolved' | 'dismissed'
created_at      TIMESTAMP DEFAULT NOW()
```

### 4.11 loans (cho mượn — giữ nguyên)
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_book_id    UUID REFERENCES user_books(id) ON DELETE CASCADE
lender_id       UUID REFERENCES users(id)
borrower_name   VARCHAR(100) NOT NULL
borrower_user_id UUID REFERENCES users(id)
borrower_contact VARCHAR(200)
lent_at         DATE NOT NULL DEFAULT NOW()
due_at          DATE
returned_at     DATE
note            TEXT
status          VARCHAR(20) DEFAULT 'active'
created_at      TIMESTAMP DEFAULT NOW()
```

### 4.12 shared_lists
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id         UUID REFERENCES users(id)
name            VARCHAR(200) NOT NULL
description     TEXT
slug            VARCHAR(100) UNIQUE NOT NULL
catalog_ids     UUID[]
is_public       BOOLEAN DEFAULT TRUE
created_at      TIMESTAMP DEFAULT NOW()
```

### 4.13 notifications
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id         UUID REFERENCES users(id)
type            VARCHAR(50)
-- 'loan_due_soon' | 'loan_overdue'
-- 'new_comment_on_review'  -- ai đó comment vào review của mình
-- 'new_reply_on_comment'   -- ai đó reply comment của mình
-- 'review_voted'           -- review của mình được vote
-- 'mention'                -- bị @mention trong comment
-- 'new_follower'           -- có người follow mình
-- 'borrow_request' | 'borrow_approved'
title           VARCHAR(200)
body            TEXT
actor_id        UUID REFERENCES users(id)  -- người thực hiện hành động
content_type    VARCHAR(20)               -- 'review' | 'comment' | 'loan'
content_id      UUID
is_read         BOOLEAN DEFAULT FALSE
created_at      TIMESTAMP DEFAULT NOW()
```

---

## 5. API Endpoints

### Auth
```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
PUT  /api/auth/password
```

### Book Catalog (thực thể sách chung)
```
GET  /api/catalog/lookup/isbn/{isbn}       -- tra Google Books theo ISBN
GET  /api/catalog/search?q=               -- tìm kiếm sách (Google Books + catalog nội bộ)
GET  /api/catalog/{id}                    -- chi tiết sách: info + aggregate reviews
GET  /api/catalog/{id}/reviews            -- tất cả reviews của cuốn sách (sorted)
GET  /api/catalog/{id}/stats              -- avg_rating, phân bổ rating, mood tags phổ biến
```

### User Books (tủ sách cá nhân)
```
GET    /api/books                         -- tủ sách của mình (filter, sort, search)
POST   /api/books                         -- thêm sách vào tủ
GET    /api/books/{id}                    -- chi tiết 1 bản sách trong tủ
PUT    /api/books/{id}                    -- cập nhật (status, tags, note, dates)
DELETE /api/books/{id}                    -- xóa khỏi tủ
```

### Reviews ← TRỌNG TÂM
```
-- Tạo / sửa / xóa
POST   /api/reviews                       -- viết review mới
GET    /api/reviews/{id}                  -- chi tiết review
PUT    /api/reviews/{id}                  -- sửa review
DELETE /api/reviews/{id}                  -- xóa review

-- Vote
POST   /api/reviews/{id}/vote             -- vote { value: 1 | -1 }
DELETE /api/reviews/{id}/vote             -- bỏ vote

-- Reactions (emoji)
POST   /api/reviews/{id}/reactions        -- react { emoji: 'heart' | ... }
DELETE /api/reviews/{id}/reactions/{emoji} -- bỏ reaction

-- Feed review của user khác
GET    /api/users/{user_id}/reviews       -- tất cả reviews công khai của 1 user
GET    /api/reviews/feed                  -- review mới từ những người mình follow
```

### Comments ← TRỌNG TÂM
```
-- CRUD
GET    /api/reviews/{review_id}/comments         -- danh sách comment (kèm replies)
POST   /api/reviews/{review_id}/comments         -- tạo comment gốc
POST   /api/reviews/{review_id}/comments/{id}/replies  -- reply vào comment
PUT    /api/comments/{id}                        -- sửa comment
DELETE /api/comments/{id}                        -- xóa (soft delete)

-- Vote
POST   /api/comments/{id}/vote                   -- vote { value: 1 | -1 }
DELETE /api/comments/{id}/vote                   -- bỏ vote
```

### Social
```
-- Follow
POST   /api/users/{id}/follow             -- follow user
DELETE /api/users/{id}/follow             -- unfollow
GET    /api/users/{id}/followers          -- danh sách follower
GET    /api/users/{id}/following          -- danh sách đang follow

-- Activity feed
GET    /api/feed                          -- hoạt động của người mình follow
                                          -- (mới thêm sách, viết review, đọc xong)

-- Report
POST   /api/reports                       -- báo cáo review / comment
```

### Public Profile
```
GET /api/public/users/{slug}              -- profile công khai
GET /api/public/users/{slug}/books        -- tủ sách công khai
GET /api/public/users/{slug}/reviews      -- reviews công khai của user
GET /api/public/lists/{slug}              -- danh sách chia sẻ
POST /api/public/books/{id}/request       -- gửi yêu cầu mượn
```

### Loans, Lists, Notifications, Stats
```
-- Loans (giữ nguyên)
GET/POST       /api/loans
GET/PUT/DELETE /api/loans/{id}
PUT            /api/loans/{id}/return

-- Lists
GET/POST       /api/lists
GET/PUT/DELETE /api/lists/{id}

-- Notifications
GET  /api/notifications
PUT  /api/notifications/{id}/read
PUT  /api/notifications/read-all
GET  /api/notifications/stream            -- SSE endpoint cho real-time

-- Stats
GET /api/stats/summary
GET /api/stats/reading-pace
GET /api/stats/genres
GET /api/stats/reviews                    -- thống kê reviews của mình
```

---

## 6. Thiết kế chi tiết tính năng Social

### 6.1 Review — Cảm nhận sách

**Cấu trúc một review đầy đủ:**
```
┌─────────────────────────────────────────────────────┐
│  Avatar  Tên user  •  Đã đọc xong 12/03/2026       │
│                                                     │
│  ★★★★☆  4/5 sao                                    │
│                                                     │
│  [Tiêu đề review]                                   │
│  "Cuốn sách thay đổi cách tôi nhìn về thói quen"   │
│                                                     │
│  [Mood tags]                                        │
│  ✨ Truyền cảm hứng  🔧 Thực tiễn  🔥 Không thể đặt │
│                                                     │
│  [Nội dung review — rich text]                      │
│  Atomic Habits là cuốn sách hiếm hoi mà tôi        │
│  cảm thấy phải đọc chậm để thấm...                 │
│                                                     │
│  [Trích dẫn yêu thích]                              │
│  ❝ You do not rise to the level of your goals,     │
│    you fall to the level of your systems. ❞         │
│                                                     │
│  [Đề xuất]                                          │
│  Dành cho ai muốn thay đổi thói quen nhưng hay... │
│                                                     │
│  ❤️ 12  👍 8  🔥 5  😮 2               [Hữu ích? 👍24]│
│  [Bình luận 7]                                      │
└─────────────────────────────────────────────────────┘
```

**Quy tắc viết review:**
- Phải có cuốn sách trong tủ với `status = 'read'`
- Mỗi user chỉ có 1 review / cuốn sách (có thể sửa sau)
- `body` bắt buộc, tối thiểu 50 ký tự
- Nếu có spoiler → phải tick `has_spoiler`, nội dung sẽ bị blur cho người đọc

**Spoiler block trong rich text:**
Tiptap custom extension `SpoilerBlock` cho phép writer đánh dấu từng đoạn là spoiler, render ra:
```html
<div class="spoiler-block" data-revealed="false">
  <span class="spoiler-warning">⚠️ Nhấn để xem spoiler</span>
  <div class="spoiler-content hidden">...</div>
</div>
```

### 6.2 Hệ thống Vote

**Vote trên review (helpful/not helpful):**
- Toggle: vote lần 2 → bỏ vote
- Không thể vote review của chính mình
- `upvote_count` được lưu denormalized trong `reviews`, cập nhật qua DB trigger
- Redis cache `review_vote:{review_id}:{user_id}` = 1 | -1 | null để kiểm tra vote state nhanh

**Vote trên comment (upvote / downvote):**
- Score = upvote_count - downvote_count
- Comment bị ẩn tự động nếu score < -5 (hiện link "Xem bình luận bị ẩn")
- Không thể vote comment của chính mình

**Thứ tự sort comments:**
```
Mặc định: "Nổi bật" = hot score theo Wilson score confidence interval
Alt: "Mới nhất" = created_at DESC
Alt: "Cũ nhất" = created_at ASC
```

**Hot score (Wilson score):**
```python
def wilson_score(upvotes: int, total: int) -> float:
    if total == 0:
        return 0
    z = 1.96  # 95% confidence
    phat = upvotes / total
    return (phat + z*z/(2*total) - z * sqrt((phat*(1-phat)+z*z/(4*total))/total)) \
           / (1 + z*z/total)
```

### 6.3 Emoji Reactions trên Review

Khác với vote (đánh giá chất lượng review), reaction là biểu đạt cảm xúc với nội dung review. User có thể react nhiều emoji trên cùng 1 review.

**Hiển thị:**
```
❤️ 12  👍 8  🔥 5  😢 3  😮 2  🤔 1
```
Click vào emoji đã react → bỏ; click emoji chưa react → thêm.

**API:**
```
POST /api/reviews/{id}/reactions   body: { emoji: "heart" }
DELETE /api/reviews/{id}/reactions/heart
```

**Cache Redis:**
- `review_reactions:{review_id}` → Hash `{ heart: 12, thumbs_up: 8, ... }`
- `user_review_reaction:{user_id}:{review_id}` → Set các emoji user đã react
- TTL: 10 phút, invalidate khi có thay đổi

### 6.4 Bình luận (Comments & Threads)

**Cấu trúc hiển thị:**
```
📝 MinhDev  •  2 giờ trước                              [+3] [−1]
   Review hay lắm! Tôi cũng đọc xong rồi và đồng ý
   với bạn về phần "habit stacking"

   └─ 📝 PhiHong  •  1 giờ trước (phản hồi @MinhDev)   [+1]
      Đúng rồi! Bạn đã áp dụng technique đó chưa?

   └─ 📝 AnhTu  •  30 phút trước                        [+2]
      Mình áp dụng được 3 tuần rồi, hiệu quả lắm 💪

📝 LinhNguyen  •  5 giờ trước                           [+7] [−0]
   Phần trích dẫn bạn chọn rất hay, câu đó mình
   highlight trong sách rồi 😄
```

**Luồng render comments:**
1. Fetch comments gốc (parent_id IS NULL), sorted by hot score
2. Mỗi comment gốc fetch tối đa 3 reply đầu
3. "Xem thêm N phản hồi" → lazy load phần còn lại
4. Thread chỉ sâu 1 cấp — reply của reply không tạo thêm indent, chỉ hiện @mention

**@mention trong comment:**
- User gõ `@` → dropdown gợi ý user đang trong thread
- Frontend parse và convert thành `<span data-mention-id="uuid">@Tên</span>`
- Backend extract mention IDs → lưu vào `comments.mentioned_user_ids`
- Notification được gửi đến user được mention

**Soft delete:**
Khi xóa comment có replies, không xóa vật lý mà đặt `is_deleted = true`. Hiển thị:
```
[Bình luận đã bị xóa]
   └─ 📝 MinhDev  •  phản hồi ...  (reply vẫn còn)
```

### 6.5 Trang sách tổng hợp (Book Detail — Social View)

Trang `/books/{catalog_id}` là trang công khai cho mọi người:

```
┌─────────────────────────────────────────────────────┐
│  [Ảnh bìa]  Atomic Habits                          │
│             James Clear  •  2018  •  320 trang      │
│                                                     │
│  ⭐ 4.3 / 5  (từ 24 reviews)                        │
│  ████████░░ 5 sao: 14                              │
│  ██████░░░░ 4 sao: 8                               │
│  ██░░░░░░░░ 3 sao: 2                               │
│  ░░░░░░░░░░ 2 sao: 0                               │
│  ░░░░░░░░░░ 1 sao: 0                               │
│                                                     │
│  Mood tags phổ biến:                                │
│  ✨×18  🔧×15  🔥×12  🧠×9  😊×7                    │
│                                                     │
│  [Nút: Thêm vào tủ / Viết review / Yêu cầu mượn]  │
├─────────────────────────────────────────────────────┤
│  REVIEWS (24)                       [Sắp xếp ▾]   │
│  ○ Nổi bật  ○ Mới nhất  ○ Tin cậy nhất            │
│                                                     │
│  [Review card 1 — nổi bật nhất]                    │
│  [Review card 2]                                    │
│  [Review card 3]                                    │
│  ...                        [Xem thêm 21 reviews]  │
└─────────────────────────────────────────────────────┘
```

**Sort options cho reviews:**
- **Nổi bật** (default): `upvote_count DESC, comment_count DESC`
- **Mới nhất**: `created_at DESC`
- **Tin cậy nhất**: Wilson score trên upvote/(upvote+downvote)
- **Đánh giá cao nhất**: `rating DESC`
- **Đánh giá thấp nhất**: `rating ASC`

**Filter reviews:**
- Theo số sao (1–5)
- Chỉ hiện review có spoiler warning
- Chỉ hiện review từ người mình follow

### 6.6 Activity Feed (Bảng tin)

Trang `/feed` hiển thị hoạt động của những người mình follow:

```
📚 PhiHong vừa đọc xong "Sapiens" — 2 giờ trước
   ★★★★★  "Cuốn sách làm thay đổi cách nhìn lịch sử..."
   [Xem review đầy đủ]

📖 MinhDev đang đọc "Deep Work" — 5 giờ trước

❤️ AnhTu react ❤️ vào review của LinhNguyen về "Atomic Habits" — 1 ngày trước

➕ TuanAnh vừa thêm "The Psychology of Money" vào tủ — 2 ngày trước
```

**Các loại activity event:**
| Event type | Trigger | Hiển thị |
|-----------|---------|---------|
| `book_finished` | `status` → `read` | "X vừa đọc xong [sách]" + snippet review nếu có |
| `book_started` | `status` → `reading` | "X đang đọc [sách]" |
| `book_added` | Thêm sách mới vào tủ | "X vừa thêm [sách] vào tủ" |
| `review_posted` | Tạo review mới | "X vừa review [sách]" + title + rating |
| `review_reacted` | React vào review | "X react [emoji] vào review của Y" |

**Hiệu năng feed:**
- Không dùng pull-based fanout (query n người đang follow mỗi lần load)
- Dùng pre-generated feed: khi user A có activity → push event vào Redis list của mỗi follower
- Key: `feed:{user_id}` → Redis sorted set (score = timestamp)
- TTL: 30 ngày, tối đa 200 events/user

---

## 7. Cấu trúc thư mục

```
book-manager/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py
│   │   │   │   ├── books.py           -- user_books CRUD
│   │   │   │   ├── catalog.py         -- book_catalog + aggregate
│   │   │   │   ├── reviews.py         -- review CRUD + vote + reactions
│   │   │   │   ├── comments.py        -- comment CRUD + vote
│   │   │   │   ├── social.py          -- follow, feed, activity
│   │   │   │   ├── loans.py
│   │   │   │   ├── lists.py
│   │   │   │   ├── public.py
│   │   │   │   ├── notifications.py
│   │   │   │   └── stats.py
│   │   │   └── deps.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── scheduler.py           -- cron: loan reminders, feed cleanup
│   │   │   └── sse.py                 -- Server-Sent Events manager
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   ├── schemas/
│   │   │   │   ├── review.py
│   │   │   │   ├── comment.py
│   │   │   │   └── social.py
│   │   │   └── session.py
│   │   ├── services/
│   │   │   ├── book_service.py
│   │   │   ├── google_books.py
│   │   │   ├── review_service.py
│   │   │   ├── comment_service.py
│   │   │   ├── vote_service.py        -- xử lý vote + cập nhật counter
│   │   │   ├── reaction_service.py
│   │   │   ├── feed_service.py        -- fanout activity vào Redis
│   │   │   ├── loan_service.py
│   │   │   └── notification_service.py
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   │   ├── test_reviews.py
│   │   ├── test_comments.py
│   │   └── test_votes.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/                    -- shadcn components
│   │   │   ├── book/
│   │   │   │   ├── BookCard.tsx
│   │   │   │   ├── BookForm.tsx
│   │   │   │   └── ISBNScanner.tsx
│   │   │   ├── review/
│   │   │   │   ├── ReviewCard.tsx     -- hiển thị 1 review
│   │   │   │   ├── ReviewEditor.tsx   -- Tiptap editor viết review
│   │   │   │   ├── ReviewList.tsx     -- danh sách reviews có sort/filter
│   │   │   │   ├── RatingDistribution.tsx
│   │   │   │   ├── MoodTagSelector.tsx
│   │   │   │   ├── MoodTagCloud.tsx   -- hiển thị tags phổ biến
│   │   │   │   └── SpoilerBlock.tsx   -- Tiptap extension
│   │   │   ├── comment/
│   │   │   │   ├── CommentThread.tsx  -- thread 1 comment gốc + replies
│   │   │   │   ├── CommentList.tsx    -- danh sách comment threads
│   │   │   │   ├── CommentForm.tsx    -- form viết / sửa
│   │   │   │   └── MentionDropdown.tsx
│   │   │   ├── social/
│   │   │   │   ├── VoteButton.tsx     -- nút vote generic (dùng cho review + comment)
│   │   │   │   ├── ReactionBar.tsx    -- emoji reaction bar
│   │   │   │   ├── ActivityFeedItem.tsx
│   │   │   │   └── FollowButton.tsx
│   │   │   └── loan/
│   │   │       └── LoanForm.tsx
│   │   ├── pages/
│   │   │   ├── HomePage.tsx           -- feed + dashboard
│   │   │   ├── BookshelfPage.tsx
│   │   │   ├── BookDetailPage.tsx     -- trang sách cá nhân
│   │   │   ├── CatalogBookPage.tsx    -- trang sách công khai + all reviews
│   │   │   ├── ReviewDetailPage.tsx   -- 1 review đầy đủ + comments
│   │   │   ├── FeedPage.tsx           -- activity feed từ following
│   │   │   ├── LoansPage.tsx
│   │   │   ├── PublicProfilePage.tsx
│   │   │   ├── SharedListPage.tsx
│   │   │   └── StatsPage.tsx
│   │   ├── stores/
│   │   │   ├── authStore.ts
│   │   │   ├── bookStore.ts
│   │   │   ├── reviewStore.ts
│   │   │   ├── commentStore.ts
│   │   │   └── notificationStore.ts
│   │   ├── hooks/
│   │   │   ├── useVote.ts
│   │   │   ├── useReaction.ts
│   │   │   ├── useSSE.ts              -- nhận notification real-time
│   │   │   └── useInfiniteScroll.ts
│   │   ├── api/
│   │   └── types/
│   ├── public/
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

### 8.1 Viết review sau khi đọc xong
```
Đổi status → 'read'
  → Popup: "Bạn vừa đọc xong! Chia sẻ cảm nhận?"  [Viết review] [Để sau]
  → ReviewEditor mở ra
  → Chọn rating (bắt buộc) + mood tags + tiêu đề + nội dung
  → Preview → Publish
  → Review xuất hiện trên trang sách public + feed của followers
```

### 8.2 Vote và tương tác với review
```
Visitor / User đọc review
  → Click ❤️ / 👍 / 🔥 → Reaction tăng ngay (optimistic update)
  → Click [Hữu ích?] → Upvote review → upvote_count tăng
  → Click [Bình luận] → CommentForm mở
  → Gõ comment + @mention → Submit
  → Tác giả review nhận notification → vào xem → reply
  → User gốc nhận notification về reply
```

### 8.3 Khám phá sách qua reviews
```
Search sách  →  Vào CatalogBookPage
  → Xem rating tổng hợp + mood tags phổ biến
  → Đọc review nổi bật (không cần đăng nhập)
  → Click "Xem bình luận" → đọc thảo luận
  → Thấy hay → "Thêm vào tủ muốn đọc" (cần đăng nhập)
  → Follow tác giả review có gu đọc tương tự
```

### 8.4 Thêm sách và cho mượn
```
User nhập ISBN  →  Tra Google Books API  →  Hiện form điền sẵn
             ↓ (không có ISBN)
        Nhập tay  →  Lưu vào DB

Chọn sách  →  Tạo phiếu mượn (tên, SĐT, hạn trả)
           →  Scheduler nhắc 3 ngày trước hạn
           →  User đánh dấu trả  →  status về 'read'
```

---

## 9. Tính năng theo phase

### Phase 1 — MVP (tuần 1-2)
- [ ] Auth (đăng ký, đăng nhập)
- [ ] Book catalog + user_books CRUD
- [ ] Lookup sách từ Google Books API bằng ISBN / tên
- [ ] Filter/search tủ sách cá nhân
- [ ] Quản lý cho mượn cơ bản

### Phase 2 — Social Core (tuần 3-4) ← TRỌNG TÂM
- [ ] Viết / sửa / xóa review (Tiptap editor, spoiler block)
- [ ] Rating + mood tags
- [ ] Vote review (upvote/downvote helpful)
- [ ] Emoji reactions trên review
- [ ] Trang sách tổng hợp reviews (`/books/{catalog_id}`)
- [ ] Bình luận trên review (comment gốc)

### Phase 3 — Community (tuần 5-6)
- [ ] Thread replies + @mention trong comment
- [ ] Vote comment (upvote/downvote)
- [ ] Follow / unfollow user
- [ ] Activity feed từ following
- [ ] Notification real-time (SSE)
- [ ] Report nội dung vi phạm

### Phase 4 — Public & Polish (tuần 7)
- [ ] Profile công khai `/u/{slug}`
- [ ] Danh sách chia sẻ `/list/{slug}`
- [ ] Yêu cầu mượn qua profile
- [ ] Dashboard thống kê
- [ ] Dark mode + mobile responsive

### Phase 5 — Optional
- [ ] Quét ISBN bằng camera (`quagga2`)
- [ ] Import từ Goodreads CSV
- [ ] Gợi ý sách dựa trên mood tags yêu thích
- [ ] Export PDF danh sách tủ sách
- [ ] PWA (offline access)

---

## 10. Non-functional Requirements

| Yêu cầu | Mục tiêu |
|---------|----------|
| API response time (P95) | < 200ms |
| Trang review / comment load | < 300ms |
| Vote / reaction response | < 100ms (optimistic update trên client) |
| Real-time notification delay | < 5 giây (SSE polling fallback 30s) |
| Search | < 500ms full-text search |
| Auth token expiry | Access: 15 phút, Refresh: 30 ngày |
| Rate limit — viết review | 10 reviews/ngày/user |
| Rate limit — viết comment | 60 comments/giờ/user |
| Rate limit — vote | 300 votes/giờ/user |
| Image upload | Max 5MB, resize về 400×600px |
| Responsive | Mobile-first, hoạt động tốt từ 375px |

---

## 11. Environment Variables

```env
# Backend
DATABASE_URL=postgresql://user:pass@localhost:5432/bookmanager
REDIS_URL=redis://localhost:6379
SECRET_KEY=...
GOOGLE_BOOKS_API_KEY=...
CLOUDINARY_URL=...
FRONTEND_URL=http://localhost:5173

# Review content moderation (optional, Phase 3+)
OPENAI_API_KEY=...    -- dùng để tự động detect nội dung spam / offensive

# Frontend
VITE_API_BASE_URL=http://localhost:8000
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

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres, redis]
    volumes: [./backend:/app]

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    env_file: .env
    volumes: [./frontend:/app]

volumes:
  pgdata:
```
