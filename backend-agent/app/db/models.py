from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# Represents a target model that can be attacked by various attacks.
class TargetModel(db.Model):
    __tablename__ = 'target_models'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    description = db.Column(db.String)


# Represents an attack that can be performed on a target model.
class Attack(db.Model):
    __tablename__ = 'attacks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    weight = db.Column(db.Integer, nullable=False, default=1, server_default="1")  # noqa: E501


# Represents a sub-attack that is part of a larger attack.
class SubAttack(db.Model):
    __tablename__ = 'sub_attacks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    attack_id = db.Column(db.Integer, db.ForeignKey('attacks.id'), nullable=False)  # noqa: E501


# Represents the results of each sigle attack on a target model.
class AttackResult(db.Model):
    __tablename__ = 'attack_results'
    id = db.Column(db.Integer, primary_key=True)
    target_model_id = db.Column(db.Integer, db.ForeignKey('target_models.id'), nullable=False)  # noqa: E501
    attack_id = db.Column(db.Integer, db.ForeignKey('attacks.id'), nullable=False)  # noqa: E501
    success = db.Column(db.Boolean, nullable=False)
    vulnerability_type = db.Column(db.String, nullable=True)
    details = db.Column(db.JSON, nullable=True)  # JSON field


# Represents the global attack success rate of an attack on a target model,
# including the total number of attacks and successful attacks.
class ModelAttackScore(db.Model):
    __tablename__ = 'model_attack_scores'
    id = db.Column(db.Integer, primary_key=True)
    target_model_id = db.Column(db.Integer, db.ForeignKey('target_models.id'), nullable=False)  # noqa: E501
    attack_id = db.Column(db.Integer, db.ForeignKey('attacks.id'), nullable=False)  # noqa: E501
    total_number_of_attack = db.Column(db.Integer, nullable=False)
    total_success = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('target_model_id', 'attack_id', name='uix_model_attack'),  # noqa: E501
    )


db.configure_mappers()
