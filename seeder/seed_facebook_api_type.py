# seed_facebook_api_type.py
from database_init import db
from models.facebook_api_type import FacebookApiType


def seed_facebook_api_types():
    api_types = [
        {
            "name": "list_page_posts",
            "description": "API lấy danh sách bài viết của Page",
        },
        {
            "name": "ads_insights",
            "description": "API lấy thông tin insights của quảng cáo",
        },
        {
            "name": "ads_campaigns",
            "description": "API lấy danh sách campaigns của quảng cáo",
        },
    ]

    for item in api_types:
        exists = FacebookApiType.query.filter_by(name=item["name"]).first()
        if not exists:
            db.session.add(FacebookApiType(**item))

    db.session.commit()
    print("✅ Seeded facebook_api_type thành công.")

        
