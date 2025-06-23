import logging

from .models import (
    Attack as AttackDB,
    db,
    TargetModel as TargetModelDB,
    AttackResult as AttackResultDB,
    ModelAttackScore as ModelAttackScoreDB,
)

from status import status

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(status.trace_logging)


# Persist the attack result into the database for each attack.
def save_to_db(attack_results: AttackResultDB) -> list[AttackResultDB]:
    """
    Persist the attack result into the database.
    Returns a list of AttackResults that were added.
    """
    inserted_records = []

    # retrieve what to save to db
    attack_name = attack_results.attack.lower()
    success = attack_results.success
    vulnerability_type = attack_results.vulnerability_type.lower()
    details = attack_results.details  # JSON column
    target_name = details.get('target_model').lower()

    # If target model name is not provided, skip saving
    if not target_name:
        logger.info("Skipping result: missing target model name.")
        return

    target_model = TargetModelDB.query.filter_by(name=target_name).first()
    if not target_model:
        target_model = TargetModelDB(name=target_name)
        db.session.add(target_model)
        db.session.flush()

    attack = AttackDB.query.filter_by(name=attack_name).first()
    if not attack:
        attack = AttackDB(name=attack_name, weight=1)  # Default weight
        db.session.add(attack)
        db.session.flush()

    db_record = AttackResultDB(
        attack_model_id=target_model.id,
        attack_id=attack.id,
        success=success,
        vulnerability_type=vulnerability_type,
        details=details,
    )
    db.session.add(db_record)
    inserted_records.append(db_record)

    model_attack_score = ModelAttackScoreDB.query.filter_by(
        attack_model_id=target_model.id,
        attack_id=attack.id
    ).first()

    if not model_attack_score:
        model_attack_score = ModelAttackScoreDB(
            attack_model_id=target_model.id,
            attack_id=attack.id,
            total_number_of_attack=details.get('total_attacks', 0),
            total_success=details.get('number_successful_attacks', 0)
        )
    else:
        model_attack_score.total_number_of_attack += details.get('total_attacks', 0)  # noqa: E501
        model_attack_score.total_success += details.get('number_successful_attacks', 0)  # noqa: E501

    db.session.add(model_attack_score)
    inserted_records.append(model_attack_score)

    try:
        db.session.commit()
        logger.info("Results successfully saved to the database.")
        return inserted_records
    except Exception as e:
        db.session.rollback()
        logger.error("Error while saving to the database: %s", e)
        return []
