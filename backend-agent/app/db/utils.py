from .models import (
    Attack as AttackDB,
    db,
    AttackModel as AttackModelDB,
    AttackResult as AttackResultDB,
    ModelAttackScore as ModelAttackScoreDB,
)


def save_to_db(attack_results):
    """
    Persist the SuiteResult into the database.
    Returns a list of AttackResults that were added.
    """
    inserted_records = []

    attack_name = attack_results.attack.lower()
    success = attack_results.success
    vulnerability_type = attack_results.vulnerability_type.lower()
    details = attack_results.details  # JSON column
    model_name = details.get('target_model').lower() if 'target_model' in details else 'unknown'

    model = AttackModelDB.query.filter_by(name=model_name).first()
    if not model:
        model = AttackModelDB(name=model_name)
        db.session.add(model)
        db.session.flush()

    attack = AttackDB.query.filter_by(name=attack_name).first()
    if not attack:
        attack = AttackDB(name=attack_name, weight=1)  # Default weight
        db.session.add(attack)
        db.session.flush()

    db_record = AttackResultDB(
        attack_model_id=model.id,
        attack_id=attack.id,
        success=success,
        vulnerability_type=vulnerability_type,
        details=details,
    )
    db.session.add(db_record)
    inserted_records.append(db_record)

    model_attack_score = ModelAttackScoreDB.query.filter_by(
        attack_model_id=model.id,
        attack_id=attack.id
    ).first()

    if not model_attack_score:
        model_attack_score = ModelAttackScoreDB(
            attack_model_id=model.id,
            attack_id=attack.id,
            total_number_of_attack=details.get('total_attacks', 0),
            total_success=details.get('number_successful_attacks', 0)
        )
    else:
        model_attack_score.total_number_of_attack += details.get('total_attacks', 0)
        model_attack_score.total_success += details.get('number_successful_attacks', 0)

    db.session.add(model_attack_score)
    inserted_records.append(model_attack_score)

    try:
        db.session.commit()
        print("Results successfully saved to the database.")
        return inserted_records
    except Exception as e:
        db.session.rollback()
        print(f"Error while saving to DB: {e}")
        return []
