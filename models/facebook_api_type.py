# models/facebook_api_type.py
from database_init import db


class FacebookApiType(db.Model):
    __tablename__ = "facebook_api_type"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(
        db.String(100), unique=True, nullable=False
    )  # Ví dụ: campaigns, adsets, ads, pages, posts, insights
    description = db.Column(db.String(255), nullable=True)  # Mô tả ngắn gọn

    statuses = db.relationship(
        "FacebookApiStatus", back_populates="api_type", lazy=True
    )
