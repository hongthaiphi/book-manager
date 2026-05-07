# Book Manager — Tài liệu Yêu cầu Chi tiết (SRS)

**Phiên bản:** 1.0  
**Ngày:** 2026-05-07  
**Tác giả:** phihongthai.it@gmail.com

---

## Mục lục

1. [Giới thiệu](#1-giới-thiệu)
2. [Người dùng & Vai trò](#2-người-dùng--vai-trò)
3. [Yêu cầu chức năng](#3-yêu-cầu-chức-năng)
   - 3.1 [Xác thực & Tài khoản](#31-xác-thực--tài-khoản)
   - 3.2 [Quản lý sách](#32-quản-lý-sách)
   - 3.3 [Cho mượn sách](#33-cho-mượn-sách)
   - 3.4 [Chia sẻ & Profile công khai](#34-chia-sẻ--profile-công-khai)
   - 3.5 [Danh sách chia sẻ](#35-danh-sách-chia-sẻ)
   - 3.6 [Yêu cầu mượn](#36-yêu-cầu-mượn)
   - 3.7 [Thông báo](#37-thông-báo)
   - 3.8 [Thống kê](#38-thống-kê)
4. [Yêu cầu phi chức năng](#4-yêu-cầu-phi-chức-năng)
5. [Quy tắc nghiệp vụ](#5-quy-tắc-nghiệp-vụ)
6. [Yêu cầu giao diện](#6-yêu-cầu-giao-diện)
7. [Yêu cầu tích hợp ngoài](#7-yêu-cầu-tích-hợp-ngoài)
8. [Acceptance Criteria tổng hợp](#8-acceptance-criteria-tổng-hợp)

---

## 1. Giới thiệu

### 1.1 Mục đích

Tài liệu này mô tả đầy đủ yêu cầu chức năng và phi chức năng của **Book Manager** — ứng dụng web quản lý tủ sách cá nhân, theo dõi hoạt động đọc, quản lý cho mượn, và chia sẻ tủ sách với cộng đồng.

### 1.2 Phạm vi

Book Manager phục vụ người đọc sách cá nhân muốn:
- Số hóa danh mục sách vật lý đang sở hữu
- Theo dõi tiến độ và lịch sử đọc sách
- Quản lý việc cho bạn bè / gia đình mượn sách
- Chia sẻ tủ sách như một "thư viện nhỏ" cá nhân

### 1.3 Định nghĩa thuật ngữ

| Thuật ngữ | Định nghĩa |
|-----------|-----------|
| Owner | Người dùng đã đăng ký, sở hữu tủ sách |
| Visitor | Người xem profile công khai (không cần đăng nhập) |
| Borrower | Người mượn sách (có thể là user hoặc không) |
| Shelf | Tập hợp toàn bộ sách của một owner |
| Loan | Phiếu ghi nhận việc cho mượn một cuốn sách |
| Borrow Request | Yêu cầu mượn gửi qua profile công khai |
| Shared List | Danh sách sách được owner curate và chia sẻ qua link |

---

## 2. Người dùng & Vai trò

### 2.1 Owner (Chủ tủ sách)

Người dùng đã đăng ký và đăng nhập. Có toàn quyền với dữ liệu của mình.

**Có thể làm:**
- Quản lý toàn bộ tủ sách cá nhân
- Tạo và quản lý phiếu cho mượn
- Tạo và quản lý danh sách chia sẻ
- Cài đặt profile công khai
- Xem và phản hồi yêu cầu mượn
- Xem thống kê đọc sách cá nhân

### 2.2 Visitor (Khách)

Người chưa đăng nhập, chỉ truy cập được trang công khai.

**Có thể làm:**
- Xem profile công khai của owner
- Xem danh sách sách công khai
- Xem chi tiết sách công khai
- Gửi yêu cầu mượn (cần nhập tên + email/SĐT)
- Xem danh sách chia sẻ qua link

**Không thể làm:**
- Xem sách private của owner
- Quản lý bất kỳ dữ liệu nào

---

## 3. Yêu cầu chức năng

---

### 3.1 Xác thực & Tài khoản

#### FR-AUTH-01: Đăng ký tài khoản

**Mô tả:** Người dùng mới tạo tài khoản bằng email và mật khẩu.

**Input:**
- `name`: Tên hiển thị, bắt buộc, 2–100 ký tự
- `email`: Địa chỉ email hợp lệ, bắt buộc, duy nhất trong hệ thống
- `password`: Mật khẩu, bắt buộc, tối thiểu 8 ký tự, có ít nhất 1 chữ hoa + 1 số

**Xử lý:**
- Kiểm tra email chưa tồn tại trong DB
- Hash password bằng bcrypt (cost factor 12)
- Tự động sinh `profile_slug` từ tên (ví dụ: "Phi Hong Thai" → `phi-hong-thai`), nếu trùng thêm số đuôi (`phi-hong-thai-2`)
- Tạo access token (15 phút) và refresh token (30 ngày)

**Output:** `{ user, access_token, refresh_token }`

**Acceptance Criteria:**
- [ ] Đăng ký thành công → trả về token, tự động đăng nhập
- [ ] Email đã tồn tại → lỗi 409 với thông báo rõ ràng
- [ ] Mật khẩu yếu → lỗi 422 liệt kê điều kiện chưa đạt
- [ ] `profile_slug` được sinh tự động và duy nhất

---

#### FR-AUTH-02: Đăng nhập

**Input:** `email`, `password`

**Xử lý:**
- Xác minh email tồn tại
- So sánh password với hash
- Cấp access token mới + refresh token mới (rotation)

**Acceptance Criteria:**
- [ ] Đăng nhập đúng → nhận token, chuyển về Dashboard
- [ ] Sai email hoặc password → lỗi 401, không chỉ rõ trường nào sai (bảo mật)
- [ ] Sau 5 lần sai liên tiếp trong 15 phút → khóa tạm 15 phút

---

#### FR-AUTH-03: Làm mới token

**Mô tả:** Client dùng refresh token để lấy access token mới mà không cần đăng nhập lại.

**Xử lý:** Xác minh refresh token còn hạn → cấp access token mới (refresh token rotation: thu hồi token cũ, cấp token mới)

**Acceptance Criteria:**
- [ ] Refresh token hợp lệ → access token mới
- [ ] Refresh token hết hạn hoặc đã bị thu hồi → lỗi 401, client buộc đăng nhập lại

---

#### FR-AUTH-04: Đăng xuất

**Xử lý:** Thu hồi refresh token hiện tại trong DB (blacklist hoặc xóa)

**Acceptance Criteria:**
- [ ] Sau đăng xuất, refresh token cũ không dùng được nữa

---

#### FR-AUTH-05: Cập nhật profile

**Input (tất cả optional):** `name`, `bio`, `avatar` (file ảnh), `profile_slug`

**Ràng buộc:**
- `profile_slug`: 3–50 ký tự, chỉ gồm `a-z`, `0-9`, `-`, không bắt đầu/kết thúc bằng `-`
- Avatar: JPG/PNG/WEBP, tối đa 5MB → upload Cloudinary, resize về 200×200px

**Acceptance Criteria:**
- [ ] Cập nhật thành công → phản ánh ngay trên profile
- [ ] `profile_slug` đã tồn tại → lỗi 409
- [ ] File ảnh quá lớn hoặc sai định dạng → lỗi 422
- [ ] Slug thay đổi → URL cũ (`/u/old-slug`) tự redirect 301 đến URL mới

---

#### FR-AUTH-06: Đổi mật khẩu

**Input:** `current_password`, `new_password`, `confirm_password`

**Acceptance Criteria:**
- [ ] Sai `current_password` → lỗi 401
- [ ] `new_password` ≠ `confirm_password` → lỗi 422
- [ ] Đổi thành công → thu hồi tất cả refresh token hiện có (buộc đăng nhập lại mọi thiết bị)

---

### 3.2 Quản lý sách

#### FR-BOOK-01: Thêm sách qua ISBN

**Mô tả:** User nhập ISBN (10 hoặc 13 chữ số) để tự động tra cứu thông tin từ Google Books API.

**Luồng:**
1. User nhập ISBN → hệ thống gọi Google Books API
2. Nếu tìm thấy: hiện form điền sẵn toàn bộ thông tin (title, authors, publisher, published_at, cover_url, page_count, description, genre)
3. User kiểm tra, chỉnh sửa nếu cần → xác nhận lưu
4. Nếu không tìm thấy: thông báo và cho phép nhập tay

**Cache:** Kết quả Google Books API được cache Redis 24h theo key `isbn:{isbn}`

**Acceptance Criteria:**
- [ ] ISBN hợp lệ, có trong Google Books → form điền sẵn trong < 2 giây
- [ ] ISBN không tìm thấy → thông báo rõ, không crash
- [ ] ISBN đã thêm trước đó vào tủ sách → cảnh báo trùng, hỏi có muốn thêm bản thứ 2 không
- [ ] ISBN không đúng định dạng → validate ngay trên frontend (không gọi API)

---

#### FR-BOOK-02: Tìm kiếm sách để thêm

**Mô tả:** User tìm kiếm tên sách/tác giả qua Google Books, chọn kết quả để thêm vào tủ.

**Luồng:**
1. User nhập tên sách → gọi Google Books search API → hiện danh sách kết quả (tối đa 10)
2. User click chọn một kết quả → form điền sẵn → lưu

**Acceptance Criteria:**
- [ ] Hiện kết quả search trong < 1 giây
- [ ] Mỗi kết quả hiện: ảnh bìa, tên, tác giả, năm xuất bản
- [ ] Không có kết quả → thông báo và offer nhập tay

---

#### FR-BOOK-03: Thêm sách thủ công

**Mô tả:** Nhập thông tin sách hoàn toàn bằng tay khi không có ISBN hoặc Google Books không có dữ liệu.

**Input:**
| Trường | Bắt buộc | Kiểu | Ràng buộc |
|--------|----------|------|-----------|
| `title` | Có | text | 1–500 ký tự |
| `authors` | Không | text[] | Mỗi tên tối đa 100 ký tự |
| `isbn` | Không | text | ISBN-10 hoặc ISBN-13 hợp lệ |
| `publisher` | Không | text | tối đa 200 ký tự |
| `published_at` | Không | date | Không được là ngày tương lai |
| `page_count` | Không | integer | 1–9999 |
| `language` | Không | select | Mặc định "vi" |
| `genre` | Không | text[] | Tối đa 5 thể loại |
| `tags` | Không | text[] | Tối đa 10 tag, mỗi tag ≤ 30 ký tự |
| `status` | Có | select | Mặc định "want_to_read" |
| `description` | Không | textarea | tối đa 5000 ký tự |
| `cover` | Không | file | JPG/PNG/WEBP ≤ 5MB |

**Acceptance Criteria:**
- [ ] Chỉ `title` và `status` là bắt buộc
- [ ] Ảnh bìa upload được → resize về 400×600px, lưu Cloudinary
- [ ] Lưu thành công → chuyển đến trang chi tiết sách vừa thêm

---

#### FR-BOOK-04: Quét ISBN bằng camera

**Mô tả:** Trên mobile, user có thể quét barcode bìa sau sách thay vì gõ ISBN.

**Luồng:** User nhấn nút "Quét ISBN" → trình duyệt xin quyền camera → hiện viewfinder → nhận diện barcode → tự động điền ISBN → tiếp tục luồng FR-BOOK-01

**Thư viện:** `quagga2`

**Acceptance Criteria:**
- [ ] Hoạt động trên Chrome Mobile và Safari iOS
- [ ] Nhận diện được EAN-13 (ISBN-13) và Code128
- [ ] Nhận diện thành công trong điều kiện ánh sáng bình thường (không tối hoàn toàn)
- [ ] Nếu browser không hỗ trợ camera API → ẩn nút, không hiện lỗi

---

#### FR-BOOK-05: Xem danh sách sách

**Mô tả:** Trang tủ sách hiển thị toàn bộ sách của user với khả năng lọc và sắp xếp.

**Bộ lọc:**
- `status`: reading | read | want_to_read | lent_out | (all)
- `genre`: chọn một hoặc nhiều thể loại
- `language`: vi | en | (other)
- `rating`: 1–5 sao
- `tags`: chọn tag
- `lent_out`: checkbox "Chỉ hiện sách đang cho mượn"

**Tìm kiếm:** Full-text search trên `title` + `authors` + `tags` (PostgreSQL `tsvector`)

**Sắp xếp:** Ngày thêm (mặc định), Tên (A-Z), Đánh giá, Ngày hoàn thành

**Hiển thị:** Grid view (mặc định) hoặc List view — user chọn được, lưu preference

**Phân trang:** Infinite scroll, mỗi trang 24 cuốn

**Acceptance Criteria:**
- [ ] Load trang đầu < 300ms
- [ ] Bộ lọc phản ánh ngay (không cần bấm Search)
- [ ] Kết quả tìm kiếm highlight từ khóa trên tên sách
- [ ] Khi không có sách nào khớp → hiện empty state kèm gợi ý hành động

---

#### FR-BOOK-06: Xem chi tiết sách

**Mô tả:** Trang chi tiết một cuốn sách với đầy đủ thông tin và các hành động nhanh.

**Hiển thị:**
- Ảnh bìa (placeholder nếu không có)
- Thông tin: tên, tác giả, NXB, năm, ISBN, số trang, ngôn ngữ, mô tả, thể loại, tags
- Trạng thái đọc với ngày bắt đầu / kết thúc
- Đánh giá sao (1–5) + review của owner
- Lịch sử cho mượn (các lần đã mượn trước)
- Phiếu mượn hiện tại (nếu đang được mượn)

**Hành động nhanh:**
- Đổi trạng thái đọc
- Ghi nhận đánh giá / review
- Cho mượn (mở form tạo phiếu)
- Chỉnh sửa thông tin sách
- Xóa sách

**Acceptance Criteria:**
- [ ] Tất cả thông tin hiển thị đầy đủ, không bị cắt
- [ ] Đổi trạng thái không cần reload trang
- [ ] Nếu sách đang được mượn → nút "Cho mượn" bị disable, hiện tên người đang mượn

---

#### FR-BOOK-07: Chỉnh sửa sách

**Mô tả:** Sửa bất kỳ trường nào của cuốn sách.

**Acceptance Criteria:**
- [ ] Form điền sẵn giá trị hiện tại
- [ ] Có thể thay ảnh bìa mới
- [ ] Lưu thành công → cập nhật `updated_at`, hiện thông báo thành công
- [ ] Đổi `status` từ `reading` sang `read` → tự động đặt `finished_at = today` nếu chưa có

---

#### FR-BOOK-08: Xóa sách

**Mô tả:** Xóa sách khỏi tủ.

**Ràng buộc:** Sách đang được mượn (`status = lent_out`) không được xóa trực tiếp.

**Acceptance Criteria:**
- [ ] Hiện dialog xác nhận trước khi xóa
- [ ] Xóa thành công → xóa luôn toàn bộ lịch sử loan của sách đó
- [ ] Sách đang được mượn → disable nút xóa, hiện tooltip giải thích

---

### 3.3 Cho mượn sách

#### FR-LOAN-01: Tạo phiếu mượn

**Mô tả:** Owner ghi nhận việc cho ai đó mượn một cuốn sách.

**Input:**
| Trường | Bắt buộc | Kiểu | Ràng buộc |
|--------|----------|------|-----------|
| `borrower_name` | Có | text | 1–100 ký tự |
| `borrower_contact` | Không | text | SĐT hoặc email, tối đa 200 ký tự |
| `lent_at` | Có | date | Mặc định hôm nay, không được là ngày tương lai |
| `due_at` | Không | date | Phải sau `lent_at` |
| `note` | Không | textarea | tối đa 500 ký tự |

**Xử lý:**
- Tạo record loan
- Cập nhật `books.status = 'lent_out'`
- Nếu có `due_at`: lên lịch notification nhắc trước 3 ngày và đúng ngày hạn

**Acceptance Criteria:**
- [ ] Tạo phiếu thành công → sách hiện badge "Đang cho mượn" ngay lập tức
- [ ] Không thể tạo phiếu nếu sách đã có phiếu mượn đang active
- [ ] `due_at` trong quá khứ → cảnh báo nhưng vẫn cho lưu (mượn đã qua hạn)
- [ ] Notification nhắc được tạo nếu có `due_at`

---

#### FR-LOAN-02: Xem danh sách cho mượn

**Mô tả:** Trang quản lý tất cả phiếu mượn.

**Bộ lọc:**
- `status`: active | returned | overdue | (all)
- Tìm kiếm theo tên người mượn

**Hiển thị mỗi phiếu:** Ảnh bìa sách, tên sách, tên người mượn, ngày mượn, hạn trả, số ngày quá hạn (nếu có), nút hành động

**Trạng thái quá hạn:** Tự động hiện badge đỏ khi `due_at < today AND returned_at IS NULL`

**Acceptance Criteria:**
- [ ] Sắp xếp mặc định: sách quá hạn lên đầu, tiếp theo là sắp đến hạn
- [ ] Hiện rõ số ngày còn lại hoặc số ngày quá hạn
- [ ] Phiếu quá hạn được highlight màu cảnh báo

---

#### FR-LOAN-03: Ghi nhận trả sách

**Mô tả:** Owner đánh dấu sách đã được trả lại.

**Xử lý:**
- Cập nhật `loans.returned_at = today`, `loans.status = 'returned'`
- Cập nhật `books.status` về trạng thái trước khi cho mượn (mặc định về `'read'`)
- Hủy notification nhắc nếu còn pending

**Acceptance Criteria:**
- [ ] Hiện dialog xác nhận ngày trả (mặc định hôm nay, có thể chỉnh)
- [ ] Trả xong → phiếu mượn chuyển sang tab "Đã trả", sách trở về trạng thái bình thường
- [ ] Có thể thêm ghi chú khi trả (ví dụ: "trả thiếu trang 50–60")

---

#### FR-LOAN-04: Gia hạn mượn

**Mô tả:** Cập nhật ngày hạn trả mới cho phiếu mượn đang active.

**Input:** `due_at` mới (phải sau ngày hiện tại)

**Acceptance Criteria:**
- [ ] Cập nhật hạn → tự động cập nhật lịch notification nhắc
- [ ] Lưu lịch sử gia hạn trong trường `note` (append, không ghi đè)

---

#### FR-LOAN-05: Xem lịch sử cho mượn của một cuốn sách

**Mô tả:** Trong trang chi tiết sách, hiện toàn bộ lịch sử ai đã mượn, khi nào, có trả chưa.

**Acceptance Criteria:**
- [ ] Sắp xếp từ mới nhất đến cũ nhất
- [ ] Hiện rõ trạng thái từng phiếu

---

### 3.4 Chia sẻ & Profile công khai

#### FR-PUBLIC-01: Bật/tắt profile công khai

**Mô tả:** Owner quyết định tủ sách có hiện công khai hay không.

**Cài đặt:**
- `profile_is_public` (boolean): bật/tắt toàn bộ profile
- Mỗi sách có `is_public` riêng: ẩn sách cụ thể khỏi profile (kể cả khi profile public)

**Acceptance Criteria:**
- [ ] Khi profile private → truy cập `/u/{slug}` trả về 404 (không để lộ slug tồn tại)
- [ ] Khi profile public → visitor thấy được các sách có `is_public = true`
- [ ] Toggle public/private không ảnh hưởng đến dữ liệu sách

---

#### FR-PUBLIC-02: Xem profile công khai

**Mô tả:** Trang `/u/{slug}` dành cho visitor, không yêu cầu đăng nhập.

**Hiển thị:**
- Avatar, tên, bio của owner
- Tổng số sách, số đã đọc
- Danh sách sách công khai (grid, tương tự trang tủ sách cá nhân)
- Bộ lọc: status, genre, rating
- Tìm kiếm trong tủ sách của owner

**Không hiển thị:**
- Sách có `is_public = false`
- Thông tin liên lạc của borrower
- Thống kê cá nhân

**Acceptance Criteria:**
- [ ] Trang load < 500ms (cache Redis 5 phút)
- [ ] Meta tags đầy đủ cho social sharing (og:title, og:image, og:description)
- [ ] URL ổn định, có thể bookmark và chia sẻ

---

#### FR-PUBLIC-03: Xem chi tiết sách công khai

**Mô tả:** Visitor xem chi tiết một cuốn sách trên profile công khai.

**Hiển thị:** Ảnh bìa, tên, tác giả, NXB, mô tả, thể loại, đánh giá và review của owner

**Không hiển thị:** Thông tin cho mượn, lịch sử loan, tags cá nhân

**Hành động:** Nút "Yêu cầu mượn" (nếu sách có `status = 'read'` hoặc `'want_to_read'` và owner cho phép)

**Acceptance Criteria:**
- [ ] Sách `lent_out` hiện trạng thái "Đang được mượn", nút yêu cầu bị vô hiệu hóa
- [ ] Nút yêu cầu mượn mở form FR-REQUEST-01

---

### 3.5 Danh sách chia sẻ

#### FR-LIST-01: Tạo danh sách chia sẻ

**Mô tả:** Owner tạo một curate list gồm nhiều sách, chia sẻ qua link độc lập.

**Input:**
| Trường | Bắt buộc | Ràng buộc |
|--------|----------|-----------|
| `name` | Có | 1–200 ký tự |
| `description` | Không | tối đa 1000 ký tự |
| `slug` | Tự sinh | Tự sinh từ `name`, owner có thể tùy chỉnh |
| `book_ids` | Có | Ít nhất 1 sách, tối đa 100 sách |
| `is_public` | Có | Mặc định true |

**Acceptance Criteria:**
- [ ] Slug duy nhất toàn hệ thống
- [ ] Chỉ được chọn sách thuộc tủ của chính mình
- [ ] Tạo thành công → hiện link chia sẻ ngay (`/list/{slug}`)

---

#### FR-LIST-02: Xem danh sách chia sẻ công khai

**Mô tả:** Bất kỳ ai có link `/list/{slug}` đều xem được (không cần đăng nhập).

**Hiển thị:** Tên list, mô tả, tên owner, ngày tạo, danh sách sách (ảnh bìa + tên + tác giả)

**Acceptance Criteria:**
- [ ] List private → trả về 404
- [ ] Sách trong list nhưng owner ẩn (`is_public = false`) → vẫn hiện trong list (owner đã chủ ý thêm vào list chia sẻ)
- [ ] Có nút "Copy link" để chia sẻ

---

#### FR-LIST-03: Quản lý danh sách

**Acceptance Criteria:**
- [ ] Owner xem toàn bộ danh sách mình đã tạo
- [ ] Có thể thêm/bớt sách trong danh sách
- [ ] Có thể đổi tên, mô tả, slug, public/private
- [ ] Xóa danh sách (chỉ xóa list, không xóa sách)

---

### 3.6 Yêu cầu mượn

#### FR-REQUEST-01: Gửi yêu cầu mượn

**Mô tả:** Visitor gửi yêu cầu mượn sách qua profile công khai của owner.

**Input:**
| Trường | Bắt buộc | Ràng buộc |
|--------|----------|-----------|
| `requester_name` | Có | 1–100 ký tự |
| `requester_contact` | Có | SĐT hoặc email hợp lệ |
| `message` | Không | tối đa 500 ký tự |

**Xử lý:**
- Tạo record `book_requests`
- Tạo notification cho owner (type: `borrow_request`)

**Acceptance Criteria:**
- [ ] Không cần đăng nhập để gửi yêu cầu
- [ ] Rate limit: 3 yêu cầu/IP/giờ (chống spam)
- [ ] Gửi thành công → hiện thông báo "Yêu cầu đã được gửi, owner sẽ liên hệ bạn qua thông tin bạn cung cấp"
- [ ] Cùng 1 IP không gửi 2 yêu cầu cùng sách trong 24h

---

#### FR-REQUEST-02: Xử lý yêu cầu mượn

**Mô tả:** Owner xem danh sách yêu cầu và phê duyệt hoặc từ chối.

**Hiển thị yêu cầu:** Tên sách, tên người gửi, contact, tin nhắn, thời gian gửi

**Hành động:**
- **Approve**: Tự động tạo phiếu mượn (FR-LOAN-01) với thông tin từ request, thông báo đã duyệt
- **Reject**: Đánh dấu rejected, owner có thể ghi lý do (chỉ lưu nội bộ)

**Acceptance Criteria:**
- [ ] Yêu cầu mới hiện badge số lượng trên menu notification
- [ ] Approve → tự động mở form loan với thông tin từ request điền sẵn
- [ ] Chỉ owner mới xem được danh sách yêu cầu của mình

---

### 3.7 Thông báo

#### FR-NOTIF-01: Nhắc nhở hạn trả

**Mô tả:** Hệ thống tự động tạo notification khi phiếu mượn sắp đến hạn hoặc quá hạn.

**Lịch chạy:**
- Mỗi ngày 9:00 sáng (cron job)
- Notification **"Sắp đến hạn"**: tạo khi `due_at = today + 3 ngày`
- Notification **"Đến hạn hôm nay"**: tạo khi `due_at = today`
- Notification **"Quá hạn"**: tạo mỗi 7 ngày kể từ `due_at` cho đến khi trả

**Acceptance Criteria:**
- [ ] Không tạo trùng notification cùng loại cho cùng loan trong cùng ngày
- [ ] Khi sách được đánh dấu trả → các notification pending bị hủy (không gửi tiếp)

---

#### FR-NOTIF-02: Thông báo yêu cầu mượn

**Trigger:** Visitor gửi yêu cầu mượn → tạo notification cho owner ngay lập tức

**Acceptance Criteria:**
- [ ] Badge số lượng notification chưa đọc cập nhật real-time (polling mỗi 30 giây hoặc WebSocket)
- [ ] Click notification → chuyển đến trang xử lý yêu cầu

---

#### FR-NOTIF-03: Xem và quản lý thông báo

**Hiển thị:** Danh sách notification theo thứ tự mới nhất, phân biệt đã đọc / chưa đọc

**Hành động:**
- Click notification → đánh dấu đã đọc + điều hướng đến nội dung liên quan
- "Đánh dấu tất cả đã đọc"
- Xóa notification cụ thể

**Acceptance Criteria:**
- [ ] Tối đa hiển thị 100 notification gần nhất
- [ ] Notification cũ hơn 90 ngày tự động xóa (cleanup job)

---

### 3.8 Thống kê

#### FR-STATS-01: Dashboard tổng quan

**Mô tả:** Trang Home hiển thị các chỉ số nhanh.

**Hiển thị:**
- Tổng số sách trong tủ
- Số sách đã đọc / đang đọc / muốn đọc / đang cho mượn
- Số sách đọc xong trong năm nay
- Số sách đọc xong trong tháng này
- Sách đang đọc dở (danh sách, sắp xếp theo `started_at`)
- Sách mới thêm gần đây (5 cuốn)
- Phiếu mượn sắp đến hạn / quá hạn (nếu có)

**Acceptance Criteria:**
- [ ] Load dashboard < 500ms (aggregate query được tối ưu + cache)
- [ ] Số liệu chính xác tính đến thời điểm hiện tại

---

#### FR-STATS-02: Thống kê tốc độ đọc

**Mô tả:** Biểu đồ số sách đọc xong theo tháng trong 12 tháng gần nhất.

**Hiển thị:** Bar chart, trục X là tháng, trục Y là số sách

**Acceptance Criteria:**
- [ ] Chỉ tính sách có `status = 'read'` và `finished_at` không null
- [ ] Có thể chuyển đổi giữa "theo tháng" và "theo năm"
- [ ] Hover vào cột → xem danh sách sách đọc xong tháng đó

---

#### FR-STATS-03: Thống kê theo thể loại

**Hiển thị:** Pie chart hoặc bar chart phân bổ sách theo `genre`

**Acceptance Criteria:**
- [ ] Thể loại "Khác" gộp các genre có < 2% tổng số sách
- [ ] Click vào phần → filter tủ sách theo genre đó

---

#### FR-STATS-04: Thống kê đánh giá

**Hiển thị:** Phân bổ sách theo rating (1–5 sao), trung bình rating

**Acceptance Criteria:**
- [ ] Chỉ tính sách có rating (bỏ qua sách chưa đánh giá)
- [ ] Hiện tổng số sách đã được đánh giá / tổng sách đã đọc

---

## 4. Yêu cầu phi chức năng

### 4.1 Hiệu năng

| Metric | Mục tiêu | Ghi chú |
|--------|----------|---------|
| API response time (P95) | < 200ms | Không kể cold start |
| API response time (P99) | < 500ms | |
| Full-text search | < 500ms | Với tủ sách ≤ 10.000 cuốn |
| Trang công khai load | < 1 giây | Bao gồm render phía client |
| Google Books lookup | < 2 giây | Phụ thuộc API bên ngoài, có timeout 3s |
| Image upload & resize | < 5 giây | |
| Concurrent users | 100 users | Không giảm hiệu năng đáng kể |

### 4.2 Bảo mật

- Mật khẩu hash bằng bcrypt, cost factor ≥ 12
- JWT secret ≥ 256-bit entropy
- Tất cả API endpoint yêu cầu auth (trừ public routes) phải validate token
- SQL injection: dùng parameterized query qua SQLAlchemy ORM
- XSS: sanitize tất cả user input trước khi lưu; frontend escape khi render
- CORS: chỉ cho phép origin từ FRONTEND_URL
- HTTPS bắt buộc trên production
- Rate limiting:
  - Auth endpoints: 10 req/phút/IP
  - Public borrow request: 3 req/giờ/IP
  - API chung: 200 req/phút/user

### 4.3 Độ tin cậy

- Uptime mục tiêu: 99% (cho phép ~7.2 giờ downtime/tháng)
- Database backup: hàng ngày, lưu 30 ngày
- Graceful error: mọi API lỗi trả về JSON `{ "error": "...", "code": "..." }` nhất quán
- Google Books API timeout: 3 giây → fallback về "không tìm thấy"

### 4.4 Khả năng mở rộng

- Stateless backend: không lưu session trên server, dễ scale horizontal
- Database connection pool: tối đa 20 connections
- Cache Redis: TTL hợp lý, không cache dữ liệu có tính nhất quán cao (loan status)

### 4.5 Khả năng bảo trì

- API tự động sinh docs qua FastAPI (`/docs` và `/redoc`)
- Migration database quản lý bằng Alembic (không sửa trực tiếp DB)
- Log structured (JSON) với các level: DEBUG / INFO / WARNING / ERROR
- Mọi lỗi 5xx phải được log kèm traceback và request context

---

## 5. Quy tắc nghiệp vụ

| ID | Quy tắc |
|----|---------|
| BR-01 | Một cuốn sách chỉ có thể có tối đa 1 phiếu mượn `active` tại một thời điểm |
| BR-02 | Sách đang được mượn (`lent_out`) không thể bị xóa, phải trả trước |
| BR-03 | Khi đánh dấu trả sách, `status` về `read` (không về trạng thái trước đó vì logic phức tạp) |
| BR-04 | `profile_slug` một khi đã thay đổi, slug cũ vẫn redirect 301 đến slug mới (tránh link chết) |
| BR-05 | Sách trong shared list không bắt buộc có `is_public = true` — owner đã chủ ý thêm vào list |
| BR-06 | Owner không thể gửi borrow request cho chính mình |
| BR-07 | Rating chỉ được phép đặt khi `status = 'read'`; nếu đổi status về `reading` thì giữ nguyên rating |
| BR-08 | `finished_at` không thể trước `started_at` |
| BR-09 | Visitor không thể xem số liệu thống kê của owner (chỉ thấy tổng số sách trên profile) |
| BR-10 | Notification nhắc hạn chỉ gửi nếu owner chưa tắt tính năng nhắc nhở trong cài đặt |

---

## 6. Yêu cầu giao diện

### 6.1 Responsive

| Breakpoint | Chiều rộng | Ghi chú |
|------------|-----------|---------|
| Mobile S | 375px+ | Bố cục 1 cột |
| Mobile L | 425px+ | |
| Tablet | 768px+ | Bố cục 2 cột |
| Desktop | 1024px+ | Bố cục 3–4 cột grid sách |
| Wide | 1440px+ | Max-width container 1280px |

### 6.2 Theme

- Hỗ trợ **Light mode** (mặc định) và **Dark mode**
- Toggle dark mode thủ công; ghi nhớ preference vào `localStorage`
- Cũng detect `prefers-color-scheme` của hệ thống khi lần đầu truy cập

### 6.3 Trang & Navigation

| Trang | URL | Auth |
|-------|-----|------|
| Landing / Login | `/` | Không cần |
| Đăng ký | `/register` | Không cần |
| Dashboard (Home) | `/home` | Cần |
| Tủ sách | `/shelf` | Cần |
| Chi tiết sách | `/shelf/{id}` | Cần |
| Thêm sách | `/shelf/add` | Cần |
| Cho mượn | `/loans` | Cần |
| Danh sách chia sẻ | `/lists` | Cần |
| Thống kê | `/stats` | Cần |
| Cài đặt | `/settings` | Cần |
| Profile công khai | `/u/{slug}` | Không cần |
| Shared list | `/list/{slug}` | Không cần |

### 6.4 Trạng thái trống (Empty States)

Mọi trang danh sách phải có empty state rõ ràng khi chưa có dữ liệu:
- Tủ sách trống → "Bạn chưa có cuốn sách nào. Thêm sách đầu tiên!" + nút CTA
- Không có phiếu mượn → "Chưa có sách nào đang được mượn."
- Không có thông báo → "Bạn đã đọc hết thông báo."

### 6.5 Feedback & Loading

- Mọi action bất đồng bộ phải có loading indicator
- Thành công → toast notification màu xanh, tự đóng sau 3 giây
- Lỗi → toast notification màu đỏ, không tự đóng (user phải dismiss)
- Form validation: báo lỗi inline ngay bên dưới trường, không chỉ sau khi submit

---

## 7. Yêu cầu tích hợp ngoài

### 7.1 Google Books API

- Dùng để: lookup theo ISBN, search theo tên/tác giả
- Auth: API Key (không cần OAuth)
- Quota free tier: 1.000 req/ngày → đủ cho giai đoạn đầu
- Fallback: nếu API down hoặc timeout → thông báo "Không tìm được thông tin tự động, vui lòng nhập tay"
- Cache kết quả trong Redis, TTL 24 giờ

### 7.2 Cloudinary

- Dùng để: lưu trữ và serve ảnh bìa sách, avatar user
- Upload: từ backend (không expose API key ra frontend)
- Transform: resize ảnh bìa về 400×600px, avatar về 200×200px
- Fallback: ảnh bìa mặc định (placeholder SVG) nếu không có ảnh

### 7.3 Redis

- Dùng để: cache Google Books lookup, cache trang profile công khai (TTL 5 phút), rate limiting counters
- Không dùng để lưu dữ liệu persistent (chỉ là cache)

---

## 8. Acceptance Criteria tổng hợp

### Luồng Happy Path phải hoạt động hoàn chỉnh:

**Luồng 1: Thêm sách mới qua ISBN**
1. User đăng nhập thành công
2. Vào trang "Thêm sách", nhập ISBN
3. Form tự động điền thông tin từ Google Books
4. User chỉnh status → "Đang đọc", đặt ngày bắt đầu
5. Lưu → sách xuất hiện trong tủ với badge "Đang đọc"
6. User vào chi tiết → đổi status sang "Đã đọc" → `finished_at` tự điền
7. Đặt rating 4 sao + review
8. Sách xuất hiện trong thống kê tháng này

**Luồng 2: Cho mượn và nhắc trả**
1. Owner vào chi tiết sách → "Cho mượn"
2. Điền tên "Minh", SĐT, hạn trả 7 ngày sau
3. Sách hiện badge "Đang cho mượn"
4. Sau 4 ngày, owner nhận notification "Sắp đến hạn (còn 3 ngày)"
5. Owner vào Loans → tìm thấy phiếu → click "Đã trả"
6. Sách trở về trạng thái bình thường, phiếu chuyển sang lịch sử

**Luồng 3: Chia sẻ tủ sách và nhận yêu cầu mượn**
1. Owner bật profile công khai tại `/u/phihong`
2. Visitor truy cập link, xem tủ sách, tìm sách quan tâm
3. Visitor click "Yêu cầu mượn", điền tên + SĐT
4. Owner nhận notification, vào xem yêu cầu
5. Owner approve → phiếu mượn được tạo tự động
6. Owner liên hệ người mượn qua SĐT đã cung cấp

---

*Tài liệu này là nguồn duy nhất của sự thật (Single Source of Truth) cho yêu cầu sản phẩm. Mọi thay đổi cần được phản ánh đồng thời trong `design.md` và cập nhật phiên bản tài liệu này.*
