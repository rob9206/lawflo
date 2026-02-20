"""Seed the law subject and topic taxonomy.

Run: python -m scripts.seed_subjects
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.database import init_database, get_db
from api.models.student import SubjectMastery, TopicMastery

TAXONOMY = {
    "con_law": {
        "display_name": "Constitutional Law",
        "topics": {
            "judicial_review": "Judicial Review",
            "standing": "Standing",
            "political_question": "Political Question Doctrine",
            "commerce_clause": "Commerce Clause",
            "spending_power": "Spending Power",
            "necessary_proper": "Necessary & Proper Clause",
            "preemption": "Preemption",
            "dormant_commerce": "Dormant Commerce Clause",
            "due_process_substantive": "Substantive Due Process",
            "due_process_procedural": "Procedural Due Process",
            "equal_protection": "Equal Protection",
            "first_amendment_speech": "First Amendment - Speech",
            "first_amendment_religion": "First Amendment - Religion",
            "state_action": "State Action Doctrine",
            "takings": "Takings Clause",
            "privileges_immunities": "Privileges & Immunities",
        },
    },
    "contracts": {
        "display_name": "Contracts",
        "topics": {
            "offer": "Offer",
            "acceptance": "Acceptance",
            "consideration": "Consideration",
            "promissory_estoppel": "Promissory Estoppel",
            "statute_of_frauds": "Statute of Frauds",
            "parol_evidence": "Parol Evidence Rule",
            "ucc_vs_common_law": "UCC vs Common Law",
            "conditions": "Conditions",
            "breach": "Breach",
            "anticipatory_repudiation": "Anticipatory Repudiation",
            "remedies_damages": "Remedies & Damages",
            "specific_performance": "Specific Performance",
            "third_party_beneficiaries": "Third-Party Beneficiaries",
            "assignment_delegation": "Assignment & Delegation",
            "impossibility_impracticability": "Impossibility & Impracticability",
            "unconscionability": "Unconscionability",
        },
    },
    "torts": {
        "display_name": "Torts",
        "topics": {
            "intentional_torts": "Intentional Torts",
            "battery": "Battery",
            "assault": "Assault",
            "false_imprisonment": "False Imprisonment",
            "iied": "IIED",
            "trespass": "Trespass",
            "conversion": "Conversion",
            "negligence_duty": "Negligence - Duty",
            "negligence_breach": "Negligence - Breach",
            "negligence_causation": "Negligence - Causation",
            "negligence_damages": "Negligence - Damages",
            "res_ipsa": "Res Ipsa Loquitur",
            "negligence_per_se": "Negligence Per Se",
            "comparative_fault": "Comparative Fault",
            "strict_liability": "Strict Liability",
            "products_liability": "Products Liability",
            "defamation": "Defamation",
            "privacy_torts": "Privacy Torts",
            "vicarious_liability": "Vicarious Liability",
        },
    },
    "crim_law": {
        "display_name": "Criminal Law",
        "topics": {
            "actus_reus": "Actus Reus",
            "mens_rea": "Mens Rea",
            "homicide": "Homicide",
            "murder": "Murder",
            "manslaughter": "Manslaughter",
            "felony_murder": "Felony Murder",
            "theft_crimes": "Theft Crimes",
            "robbery_burglary": "Robbery & Burglary",
            "inchoate_crimes": "Inchoate Crimes (Attempt, Conspiracy, Solicitation)",
            "accomplice_liability": "Accomplice Liability",
            "self_defense": "Self-Defense",
            "insanity": "Insanity Defense",
            "intoxication": "Intoxication",
            "entrapment": "Entrapment",
        },
    },
    "civ_pro": {
        "display_name": "Civil Procedure",
        "topics": {
            "personal_jurisdiction": "Personal Jurisdiction",
            "subject_matter_jurisdiction": "Subject Matter Jurisdiction",
            "diversity_jurisdiction": "Diversity Jurisdiction",
            "federal_question": "Federal Question Jurisdiction",
            "removal": "Removal",
            "venue": "Venue",
            "erie_doctrine": "Erie Doctrine",
            "pleading_standards": "Pleading Standards",
            "rule_12_motions": "Rule 12 Motions",
            "discovery": "Discovery",
            "summary_judgment": "Summary Judgment",
            "class_actions": "Class Actions",
            "joinder": "Joinder",
            "claim_issue_preclusion": "Claim & Issue Preclusion",
        },
    },
    "property": {
        "display_name": "Property",
        "topics": {
            "estates_in_land": "Estates in Land",
            "future_interests": "Future Interests",
            "concurrent_ownership": "Concurrent Ownership",
            "landlord_tenant": "Landlord-Tenant",
            "easements": "Easements",
            "covenants": "Covenants",
            "adverse_possession": "Adverse Possession",
            "recording_acts": "Recording Acts",
            "takings_zoning": "Takings & Zoning",
        },
    },
    "evidence": {
        "display_name": "Evidence",
        "topics": {
            "relevance": "Relevance (FRE 401-403)",
            "character_evidence": "Character Evidence",
            "hearsay": "Hearsay",
            "hearsay_exceptions": "Hearsay Exceptions",
            "impeachment": "Impeachment",
            "privileges": "Privileges",
            "expert_testimony": "Expert Testimony",
            "authentication": "Authentication",
            "best_evidence": "Best Evidence Rule",
        },
    },
    "prof_responsibility": {
        "display_name": "Professional Responsibility",
        "topics": {
            "competence_diligence": "Competence & Diligence",
            "confidentiality": "Confidentiality",
            "conflicts_of_interest": "Conflicts of Interest",
            "client_communications": "Client Communications",
            "fees": "Fees",
            "advertising_solicitation": "Advertising & Solicitation",
            "duties_to_court": "Duties to the Court",
        },
    },
}


def seed():
    """Seed all subjects and topics into the database."""
    init_database()

    with get_db() as db:
        for subject_key, subject_data in TAXONOMY.items():
            # Create or update subject
            existing = db.query(SubjectMastery).filter_by(subject=subject_key).first()
            if not existing:
                subj = SubjectMastery(
                    subject=subject_key,
                    display_name=subject_data["display_name"],
                )
                db.add(subj)

            # Create topics
            for topic_key, topic_display in subject_data["topics"].items():
                existing_topic = db.query(TopicMastery).filter_by(
                    subject=subject_key, topic=topic_key
                ).first()
                if not existing_topic:
                    topic = TopicMastery(
                        subject=subject_key,
                        topic=topic_key,
                        display_name=topic_display,
                    )
                    db.add(topic)

    print(f"Seeded {len(TAXONOMY)} subjects with {sum(len(s['topics']) for s in TAXONOMY.values())} topics.")


if __name__ == "__main__":
    seed()
