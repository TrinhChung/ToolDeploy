# Danh sách route

Các route được nhóm theo từng blueprint. Phần lớn các trang (ngoại trừ một số API) yêu cầu người dùng đăng nhập.

## Auth
- `GET /register`, `POST /register`
- `GET /login`, `POST /login`
- `GET /logout`

## Home
- `GET /`
- `GET /terms`
- `GET /polices`

## Admin
- `GET /admin/users`
- `GET /admin/users/activate/<user_id>`
- `GET /admin/users/delete/<user_id>`

## Server
- `GET /server/servers`
- `GET|POST /server/server/add`
- `GET|POST /server/server/edit/<server_id>`
- `POST /server/server/delete/<server_id>`
- `GET /server/server/<server_id>`

## Domain
- `GET /domain/list`
- `GET|POST /domain/add`
- `GET|POST /domain/verify/<domain_id>`
- `POST /domain/delete/<domain_id>`

## DNS
- `GET /dns/<domain_id>`
- `GET /dns/sync/<domain_id>`
- `GET|POST /dns/add/<domain_id>`
- `POST /dns/delete/<record_id>`

## Deploy ứng dụng
- `GET|POST /deployed_app/deploy`
- `GET /deployed_app/list`
- `POST /deployed_app/add-dns-txt/<app_id>`
- `POST /deployed_app/stop-app/<app_id>`
- `POST /deployed_app/confirm-facebook/<app_id>`
- `POST /deployed_app/redeploy/<app_id>`
- `GET /deployed_app/detail/<app_id>`

## Cloudflare Account
- `GET /cloudflare/accounts`
- `GET|POST /cloudflare/add`
- `POST /cloudflare/delete/<account_id>`
- `POST /cloudflare/sync/<account_id>`

## Company
- `GET /company/`
- `GET /company/<company_id>`
- `GET|POST /company/add`
- `GET|POST /company/edit/<company_id>`
- `POST /company/delete/<company_id>`

## Website
- `GET /website/`
- `GET|POST /website/add`
- `POST /website/delete/<website_id>`

## API (prefix `/api`)
- `GET /api/products`
- `GET /api/products/<product_id>`
- `GET|POST /api/users`
- `GET|PUT /api/users/<user_id>`
- `GET|POST /api/orders`
- `GET /api/orders/<order_id>`
- `GET /api/company`
