from database_init import db


class Server(db.Model):
    __tablename__ = "server"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    ip = db.Column(db.String(45), unique=True, nullable=False)
    admin_username = db.Column(db.String(128))
    admin_password = db.Column(db.String(256))
    db_name = db.Column(db.String(128))
    db_user = db.Column(db.String(128))
    db_password = db.Column(db.String(256))
    note = db.Column(db.String(256))
    deployed_apps = db.relationship("DeployedApp", back_populates="server", lazy=True)

    def __repr__(self):
        return f"<Server {self.name} ({self.ip})>"
