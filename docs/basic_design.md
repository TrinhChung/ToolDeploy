# Basic Design cho hệ thống ToolDeploy

## 1. Mục tiêu ứng dụng

Cung cấp công cụ tự động triển khai (deploy) ứng dụng và website phục vụ mục đích xác minh doanh nghiệp cho khách hàng.

## 2. Đối tượng người dùng

* **Quản trị viên:** Quản lý server, thêm tài khoản Cloudflare, quản lý domain và template.
* **Khách hàng:** Quản lý và triển khai ứng dụng, website dựa trên thông tin công ty, chọn domain và template frontend có sẵn.

## 3. Luồng xử lý Deploy ứng dụng

### Khách hàng nhập thông tin

* Nhập thông tin công ty.
* Chọn domain và subdomain thông qua DNS record A.
* Chọn server (đã được quản trị viên thiết lập).

### Quy trình deploy ứng dụng

1. Hệ thống tự động tạo bản ghi DNS A cho subdomain được chọn.
2. Hệ thống kết nối đến server khách hàng đã chọn.
3. Hệ thống tiến hành tạo SSL (HTTPS) cho subdomain.
4. Hệ thống triển khai ứng dụng khách hàng lên server.
5. Hệ thống cập nhật trạng thái deploy:

   * Thành công: Active
   * Thất bại: Failed

### Xác minh quyền sở hữu ứng dụng

* Khách hàng cập nhật bản ghi TXT xác minh từ Facebook.

### Các chức năng quản lý ứng dụng

* Redeploy ứng dụng trong trường hợp lỗi.
* Stop ứng dụng sau khi đã được xác minh.

## 4. Luồng xử lý Deploy website

### Khách hàng nhập thông tin

* Chọn template frontend.
* Cung cấp thông tin công ty (hiển thị tại footer, trang liên hệ, bản đồ).

### Quy trình deploy website

1. Kiểm tra template frontend trên server:

   * Nếu chưa có, hệ thống tự động lấy và triển khai template.
2. Hệ thống tạo bản ghi DNS A cho subdomain được chọn.
3. Hệ thống tạo SSL (HTTPS) cho subdomain thông qua các bước tự động.

### Hiển thị thông tin công ty

* Template frontend tự động lấy thông tin từ hệ thống dựa trên domain khách hàng cung cấp.

## 5. Yêu cầu nghiệp vụ đặc biệt

* Khách hàng chỉ được phép tạo subdomain thông qua DNS record A nhằm tránh lãng phí domain.
* Tối ưu hóa tài nguyên, chỉ cung cấp dịch vụ vừa đủ để phục vụ xác minh doanh nghiệp, hạn chế lãng phí.
* Mỗi server chỉ triển khai duy nhất một loại template frontend để giảm thiểu tiêu hao tài nguyên.

## 6. Xử lý lỗi

* Khi gặp lỗi trong quá trình triển khai:

  * Thông báo trạng thái lỗi rõ ràng, chi tiết cho khách hàng.
  * Cho phép khách hàng thực hiện lại việc triển khai (redeploy).
* Ghi nhận lỗi rõ ràng để hỗ trợ debug nhanh chóng và hiệu quả.
