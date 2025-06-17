from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class AttackModel(db.Model):
    __tablename__ = 'attack_models'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    description = db.Column(db.String)

    # attack_results = db.relationship('AttackResult', backref='attack_model')
    # model_scores = db.relationship('ModelAttackScore', back_populates='attack_model')


class Attack(db.Model):
    __tablename__ = 'attacks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    weight = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    # subattacks = db.relationship('SubAttack', backref='attack', cascade='all, delete-orphan')
    # model_scores = db.relationship('ModelAttackScore', back_populates='attack')


class SubAttack(db.Model):
    __tablename__ = 'sub_attacks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    attack_id = db.Column(db.Integer, db.ForeignKey('attacks.id'), nullable=False)


class AttackResult(db.Model):
    __tablename__ = 'attack_results'
    id = db.Column(db.Integer, primary_key=True)
    attack_model_id = db.Column(db.Integer, db.ForeignKey('attack_models.id'), nullable=False)
    attack_id = db.Column(db.Integer, db.ForeignKey('attacks.id'), nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    vulnerability_type = db.Column(db.String, nullable=True)
    details = db.Column(db.JSON, nullable=True)  # JSON field


class ModelAttackScore(db.Model):
    __tablename__ = 'model_attack_scores'
    id = db.Column(db.Integer, primary_key=True)
    attack_model_id = db.Column(db.Integer, db.ForeignKey('attack_models.id'), nullable=False)
    attack_id = db.Column(db.Integer, db.ForeignKey('attacks.id'), nullable=False)
    total_number_of_attack = db.Column(db.Integer, nullable=False)
    total_success = db.Column(db.Integer, nullable=False)

    # attack_model = db.relationship('AttackModel', back_populates='model_scores')
    # attack = db.relationship('Attack', back_populates='model_scores')

    __table_args__ = (
        db.UniqueConstraint('attack_model_id', 'attack_id', name='uix_model_attack'),
    )


db.configure_mappers()
