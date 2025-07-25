from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from database_init import db
from models.cloudflare_acc import CloudflareAccount
from util.cloud_flare import sync_domains_from_cf_with_account

class CloudflareAccountForm(FlaskForm):
    name = StringField("Tên tài khoản", validators=[DataRequired()])
    email = StringField("Email")
    api_token = StringField("API Token", validators=[DataRequired()])
    account_id = StringField("Account ID", validators=[DataRequired()])
    ns1 = StringField("Nameserver 1")
    ns2 = StringField("Nameserver 2")
    submit = SubmitField("Lưu")

class DummyDeleteForm(FlaskForm):
    pass

cloudflare_bp = Blueprint("cloudflare", __name__, url_prefix="/cloudflare")

# Danh sách Cloudflare Account (chỉ admin)
@cloudflare_bp.route("/accounts")
@login_required
def list_accounts():
    if not current_user.is_admin:
        abort(403)
    accounts = CloudflareAccount.query.all()
    form = DummyDeleteForm()
    return render_template("cloudflare/list.html", accounts=accounts, form=form)

# Thêm mới Cloudflare Account (chỉ admin)
@cloudflare_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_account():
    if not current_user.is_admin:
        abort(403)
    form = CloudflareAccountForm()
    if form.validate_on_submit():
        # Check trùng account_id
        if CloudflareAccount.query.filter_by(account_id=form.account_id.data.strip()).first():
            flash("Account ID này đã tồn tại!", "danger")
            return render_template("cloudflare/add.html", form=form)
        acc = CloudflareAccount(
            name=form.name.data.strip(),
            email=form.email.data.strip(),
            api_token=form.api_token.data.strip(),
            account_id=form.account_id.data.strip(),
            ns1=form.ns1.data.strip(),
            ns2=form.ns2.data.strip()
        )
        db.session.add(acc)
        db.session.commit()
        flash("Đã thêm tài khoản Cloudflare!", "success")
        return redirect(url_for("cloudflare.list_accounts"))
    return render_template("cloudflare/add.html", form=form)

# Xóa Cloudflare Account (chỉ admin)
@cloudflare_bp.route("/delete/<int:account_id>", methods=["POST"])
@login_required
def delete_account(account_id):
    if not current_user.is_admin:
        abort(403)
    acc = CloudflareAccount.query.get_or_404(account_id)
    db.session.delete(acc)
    db.session.commit()
    flash(f"Đã xóa Cloudflare Account {acc.name}", "success")
    return redirect(url_for("cloudflare.list_accounts"))

@cloudflare_bp.route("/sync/<int:account_id>", methods=["POST"])
@login_required
def sync_domains(account_id):
    if not current_user.is_admin:
        abort(403)
    acc = CloudflareAccount.query.get_or_404(account_id)
    try:
        sync_domains_from_cf_with_account(acc)
        flash(f"Đã đồng bộ domain từ Cloudflare Account: {acc.name}", "success")
    except Exception as e:
        flash(f"Lỗi khi đồng bộ: {e}", "danger")
    return redirect(url_for("cloudflare.list_accounts"))
