# models/facebook_api_status.py
from database_init import db
from datetime import datetime, timedelta
import random


class FacebookApiStatus(db.Model):
    __tablename__ = "facebook_api_status"

    # Gợi ý index (cần migration để áp dụng nếu bảng đã tồn tại)
    __table_args__ = (
        db.Index("ix_fb_status_next", "next_eligible_at"),
        db.Index("ix_fb_status_mode_next", "mode", "next_eligible_at"),
    )

    deployed_app_id = db.Column(
        db.Integer, db.ForeignKey("deployed_app.id"), primary_key=True
    )
    api_type_id = db.Column(
        db.Integer, db.ForeignKey("facebook_api_type.id"), primary_key=True
    )

    last_checked_at = db.Column(db.DateTime, nullable=True)

    total_calls = db.Column(db.Integer, default=0)
    total_success_calls = db.Column(db.Integer, default=0)
    total_errors = db.Column(db.Integer, default=0)

    daily_calls = db.Column(db.Integer, default=0)
    daily_success_calls = db.Column(db.Integer, default=0)
    daily_reset_at = db.Column(db.DateTime, nullable=True)

    mode = db.Column(db.String(20), default="normal")  # normal|reduced|stopped
    reduced_mode_start = db.Column(db.DateTime, nullable=True)
    reduced_days_count = db.Column(db.Integer, default=0)

    cooldown_until = db.Column(db.DateTime, nullable=True)
    next_eligible_at = db.Column(db.DateTime, index=True, nullable=True)

    last_rate_limit_at = db.Column(db.DateTime, nullable=True)
    last_error_code = db.Column(db.Integer, nullable=True)
    last_error_subcode = db.Column(db.Integer, nullable=True)

    deployed_app = db.relationship(
        "DeployedApp", backref=db.backref("api_statuses", lazy=True)
    )
    api_type = db.relationship("FacebookApiType", back_populates="statuses")

    # -------- Core quyết định khi nào được gọi --------
    def can_call(self, now=None) -> bool:
        now = now or datetime.utcnow()

        # Reset theo ngày
        if not self.daily_reset_at or now.date() != self.daily_reset_at.date():
            self.daily_calls = 0
            self.daily_success_calls = 0
            self.daily_reset_at = now
            if self.mode == "reduced":
                self.reduced_days_count += 1
                if self.reduced_days_count >= 30:
                    self.mode = "stopped"

        if self.mode == "stopped":
            return False

        if self.cooldown_until and now < self.cooldown_until:
            return False

        if self.mode == "reduced" and (self.daily_calls or 0) >= 5:
            return False

        # next_eligible_at (nếu đặt) cũng chặn
        if self.next_eligible_at and now < self.next_eligible_at:
            return False

        return True

    def _bump_next_eligible(self, now=None):
        """Tự tính lần gọi tiếp theo (giảm DB polling)."""
        now = now or datetime.utcnow()

        if self.cooldown_until and now < self.cooldown_until:
            self.next_eligible_at = self.cooldown_until
            return

        if self.mode == "stopped":
            # dời xa để không bao giờ được chọn
            self.next_eligible_at = now + timedelta(days=365 * 10)
            return

        if self.mode == "reduced":
            # Nếu đã đủ 5 lượt hôm nay → đợi tới nửa đêm + jitter
            if (self.daily_calls or 0) >= 5:
                tomorrow = (now + timedelta(days=1)).replace(
                    hour=0, minute=0, second=10, microsecond=0
                )
                self.next_eligible_at = tomorrow + timedelta(
                    seconds=random.randint(0, 30)
                )
            else:
                # giãn nhịp rộng hơn chút trong reduced
                self.next_eligible_at = now + timedelta(seconds=random.randint(8, 15))
            return

        # normal: gọi nhịp ngắn (2-5s) — có jitter
        self.next_eligible_at = now + timedelta(seconds=random.randint(2, 5))

    def record_call(self, success=True, now=None):
        now = now or datetime.utcnow()
        self.last_checked_at = now
        self.total_calls = (self.total_calls or 0) + 1
        self.daily_calls = (self.daily_calls or 0) + 1

        if success:
            self.total_success_calls = (self.total_success_calls or 0) + 1
            self.daily_success_calls = (self.daily_success_calls or 0) + 1

            # Với schema 1 dòng / (app, type), chỉ cần check trực tiếp
            if self.mode == "normal" and (self.daily_success_calls or 0) >= 1500:
                # Chuyển loại của app sang reduced (chính là dòng này)
                self.mode = "reduced"
                self.reduced_mode_start = now
                self.reduced_days_count = 0
        else:
            self.total_errors = (self.total_errors or 0) + 1

        self._bump_next_eligible(now)

    def set_cooldown(self, seconds, error_code=None, error_subcode=None, now=None):
        now = now or datetime.utcnow()
        self.cooldown_until = now + timedelta(seconds=seconds)
        self.last_rate_limit_at = now
        self.last_error_code = error_code
        self.last_error_subcode = error_subcode
        # Lập lịch ngay theo cooldown
        self.next_eligible_at = self.cooldown_until
