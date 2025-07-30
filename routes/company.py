# routes/company.py

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from models.company import Company
from database_init import db

company_bp = Blueprint("company", __name__, url_prefix="/company")

# 1. Danh sách company - chỉ lấy của user hiện tại
@company_bp.route("/")
@login_required
def list_companies():
    companies = Company.query.filter_by(user_id=current_user.id).all()
    return render_template("company/list.html", companies=companies)

# 2. Xem chi tiết company - chỉ được xem của mình
@company_bp.route("/<int:company_id>")
@login_required
def company_detail(company_id):
    company = Company.query.filter_by(id=company_id, user_id=current_user.id).first_or_404()
    return render_template("company/detail.html", company=company)

# 3. Thêm company (GET/POST), gán user_id là current_user
@company_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_company():
    if request.method == "POST":
        form_data = {
            "name": request.form.get("name", ""),
            "address": request.form.get("address", ""),
            "hotline": request.form.get("hotline", ""),
            "email": request.form.get("email", ""),
            "license_no": request.form.get("license_no", ""),
            "google_map_embed": request.form.get("google_map_embed", ""),
            "logo_url": request.form.get("logo_url", ""),
            "footer_text": request.form.get("footer_text", ""),
            "description": request.form.get("description", ""),
            "note": request.form.get("note", ""),
        }
        if not form_data["name"]:
            flash("Tên công ty không được để trống!", "danger")
            return render_template("company/add.html", company=form_data)

        # Gán user_id cho company
        form_data["user_id"] = current_user.id

        company = Company(**form_data)
        db.session.add(company)
        db.session.commit()
        flash("Đã thêm công ty thành công.", "success")
        return redirect(url_for("company.list_companies"))
    return render_template("company/add.html", company=None)

# 4. Sửa company (GET/POST) - chỉ được sửa của mình
@company_bp.route("/edit/<int:company_id>", methods=["GET", "POST"])
@login_required
def edit_company(company_id):
    company = Company.query.filter_by(id=company_id, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        company.name = request.form.get("name")
        company.address = request.form.get("address")
        company.hotline = request.form.get("hotline")
        company.email = request.form.get("email")
        company.license_no = request.form.get("license_no")
        company.google_map_embed = request.form.get("google_map_embed")
        company.logo_url = request.form.get("logo_url")
        company.footer_text = request.form.get("footer_text")
        company.description = request.form.get("description")
        company.note = request.form.get("note")
        db.session.commit()
        flash("Đã cập nhật thông tin công ty.", "success")
        return redirect(url_for("company.company_detail", company_id=company.id))
    return render_template("company/edit.html", company=company)

# 5. Xóa company - chỉ xóa được của mình
@company_bp.route("/delete/<int:company_id>", methods=["POST"])
@login_required
def delete_company(company_id):
    company = Company.query.filter_by(id=company_id, user_id=current_user.id).first_or_404()
    db.session.delete(company)
    db.session.commit()
    flash("Đã xóa công ty.", "success")
    return redirect(url_for("company.list_companies"))
