
| Model                  | Trường đáng chú ý                                                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **User**               | `id`, `username`, `email`, `password`, `is_active`, `is_admin`                                                                             |
| **Domain**             | `id`, `name`, `zone_id`, `status`, `user_id`, `cloudflare_account_id`                                                                      |
| **DNSRecord**          | `id`, `domain_id`, `record_id`, `record_type`, `name`, `content`, `ttl`, `proxied`                                                         |
| **CloudflareAccount**  | `id`, `name`, `email`, `api_token`, `account_id`, `ns1`, `ns2`                                                                             |
| **Server**             | `id`, `name`, `ip`, `admin_username`, `admin_password`, `db_name`, `db_user`, `db_password`, `note`                                        |
| **DeployedApp**        | `id`, `server_id`, `domain_id`, `subdomain`, `env`, `status`, `note`, `created_at`, `updated_at`                                           |
| **Template**           | `id`, `name`, `description`, `sample_url`, `port`, `backend`                                                                               |
| **Company**            | `id`, `name`, `address`, `hotline`, `email`, `license_no`, `google_map_embed`, `logo_url`, `footer_text`, `description`, `note`, `user_id` |
| **Website**            | `id`, `company_id`, `dns_record_id`, `template_id`, `static_page_link`, `note`, `user_id`                                                  |
| **Product**            | `id`, `title`, `image`, `category`, `price`, `popularity`, `stock`, `description`, `detail`, `delivery_detail`                             |
| **UserFE**             | `id`, `name`, `lastname`, `email`, `password`, `phone`, `address`, `created_at`, `is_active`                                               |
| **Order**              | `id`, `user_fe_id`, `order_status`, `order_date`, `subtotal`, `shipping_address`, `phone`, `payment_type`, `note`                          |
| **OrderItem**          | `id`, `order_id`, `product_id`, `quantity`, `price`, `size`, `color`, `popularity`, `stock`                                                |
| **DomainVerification** | `id`, `deployed_app_id`, `txt_value`, `create_count`                                                                                       |

