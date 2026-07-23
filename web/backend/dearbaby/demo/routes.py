# -*- coding: utf-8 -*-
"""
Sample data for the signed-in account.

The seed script populates the fixed demo logins. This lets ANY account —
including one you just registered — fill itself with a realistic pregnancy
and a baby so no screen is empty while you're exploring.

Everything created here belongs to the calling user and can be wiped again
with DELETE /api/demo.
"""
import random
from datetime import datetime, timedelta, timezone, date
from flask import Blueprint, jsonify
from dearbaby.extensions import db
from dearbaby.models import (Child, Milestone, MilestoneType, JournalEntry, Growth,
                        Appointment, Tooth, BirthRecord, KickSession, Album,
                        Contraction, Reminder, Subscription)
from dearbaby.decorators import login_required, _current_user

demo_bp = Blueprint("demo", __name__)

PREGNANCY_MILESTONES = [
    ("positive_test", 150, "Three tests, just to be sure."),
    ("first_scan", 120, "Tiny and impossibly fast."),
    ("heard_heartbeat", 118, "We played it back all evening."),
    ("first_kick", 60, "Halfway through dinner. Not wind this time."),
    ("anomaly_scan", 28, "Everything measuring beautifully."),
]

PREGNANCY_JOURNAL = [
    (140, "Telling our families", "We waited until the twelve-week scan. My mother "
     "cried before we even finished the sentence.", "overjoyed"),
    (118, "We saw the heartbeat", "Tiny and impossibly fast. I cried in the car park "
     "afterwards and didn't care who saw.", "overjoyed"),
    (95, "The tiredness is unreal", "Asleep by eight most nights. Everyone says the "
     "second trimester is kinder. Holding them to it.", "tired"),
    (60, "First proper kick", "I was halfway through dinner and felt a definite thump. "
     "Sat very still for ten minutes hoping for another.", "excited"),
    (42, "Nursery started", "Painted the small room this weekend. Two coats and a lot "
     "of arguing about the shade of white.", "calm"),
    (28, "The 20-week scan", "Everything measuring beautifully. We got a printout of "
     "the profile view and it's on the fridge.", "grateful"),
    (12, "Slowing down", "Back is aching and sleep is patchy, but the kicks at night "
     "make up for it. Not long now.", "tired"),
    (3, "Bag packed", "Probably too early, but it's by the door and I feel better "
     "for it.", "calm"),
]

BABY_MILESTONES = [
    ("birth", 245, "3.2kg, born just after midnight."),
    ("first_smile", 200, "Right after her morning feed. We both cried a little."),
    ("first_laugh", 170, "Her father sneezed and she found it hilarious."),
    ("rolled_over", 130, "Front to back, then straight back again, very pleased."),
    ("first_tooth", 90, "Bottom left. Days of grumpiness explained."),
    ("sat_up", 75, "Wobbly but unassisted for a whole minute."),
    ("first_food", 60, "Sweet potato puree. Mostly went on the wall."),
    ("first_crawl", 25, "Backwards at first, which frustrated her enormously."),
]

BABY_JOURNAL = [
    (240, "First week home", "Nobody warned us how loud a newborn's breathing is. "
     "I keep checking she's still going.", "overwhelmed"),
    (198, "That smile", "It wasn't wind. It was absolutely a smile and I will not be "
     "argued with on this.", "overjoyed"),
    (120, "Sleep, briefly", "Six hours in a row. I woke up in a panic instead of "
     "enjoying it.", "tired"),
    (58, "Starting solids", "More on her face than in it, but she's enthusiastic.", "excited"),
    (20, "On the move", "Nothing on a low shelf is safe anymore. Cupboard locks ordered.", "excited"),
]


def _mk_pregnancy(user, types):
    """A pregnancy at roughly 24 weeks."""
    child = Child(owner_id=user.id, name="Baby",
                  due_date=date.today() + timedelta(weeks=16))
    db.session.add(child)
    db.session.flush()

    for slug, days_ago, note in PREGNANCY_MILESTONES:
        t = types.get(slug)
        if t:
            db.session.add(Milestone(child_id=child.id, type_id=t.id, title=t.label,
                                     emoji=t.emoji, note=note,
                                     occurred_on=date.today() - timedelta(days=days_ago)))

    for days_ago, title, body, mood in PREGNANCY_JOURNAL:
        db.session.add(JournalEntry(child_id=child.id, author_id=user.id, title=title,
                                    body=body, mood=mood, week=child.current_week(),
                                    entry_date=date.today() - timedelta(days=days_ago)))

    for days, title, place in [
        (9, "Antenatal check-up", "Nairobi Women's Hospital"),
        (25, "Glucose screening", "Nairobi Women's Hospital"),
        (47, "Growth scan", "Nairobi Women's Hospital"),
    ]:
        db.session.add(Appointment(child_id=child.id, title=title, location=place,
                                   starts_at=datetime.now(timezone.utc) + timedelta(days=days)))

    # a few kick sessions over the last fortnight
    for d in (1, 3, 6, 9, 13):
        start = datetime.now(timezone.utc) - timedelta(days=d, hours=random.randint(1, 10))
        db.session.add(KickSession(child_id=child.id, started_at=start,
                                   ended_at=start + timedelta(minutes=random.randint(18, 55)),
                                   kick_count=random.randint(8, 14)))

    # one practice run of Braxton Hicks
    base = datetime.now(timezone.utc) - timedelta(days=2)
    for i in range(5):
        s = base + timedelta(minutes=i * 14)
        db.session.add(Contraction(child_id=child.id, started_at=s,
                                   ended_at=s + timedelta(seconds=random.randint(35, 60))))

    db.session.add(Album(child_id=child.id, title="Scans"))
    db.session.add(Album(child_id=child.id, title="Bump diary"))
    return child


def _mk_baby(user, types):
    """A baby at roughly 8 months, with a full growth curve."""
    born = date.today() - timedelta(days=245)
    child = Child(owner_id=user.id, name="Maya", sex="female", birth_date=born)
    db.session.add(child)
    db.session.flush()

    db.session.add(BirthRecord(child_id=child.id,
                               born_at=datetime.combine(born, datetime.min.time()).replace(
                                   hour=0, minute=17, tzinfo=timezone.utc),
                               place="Nairobi Women's Hospital", weight_g=3200,
                               length_cm=49, head_circ_cm=34.5,
                               notes="Arrived nine days early, in a hurry."))

    for slug, days_ago, note in BABY_MILESTONES:
        t = types.get(slug)
        if t:
            db.session.add(Milestone(child_id=child.id, type_id=t.id, title=t.label,
                                     emoji=t.emoji, note=note,
                                     occurred_on=date.today() - timedelta(days=days_ago)))

    for days_ago, title, body, mood in BABY_JOURNAL:
        db.session.add(JournalEntry(child_id=child.id, author_id=user.id, title=title,
                                    body=body, mood=mood,
                                    entry_date=date.today() - timedelta(days=days_ago)))

    # monthly growth measurements
    for m in range(0, 9):
        when = born + timedelta(days=m * 30)
        db.session.add(Growth(child_id=child.id, kind="weight",
                              value=round(3.2 + m * 0.62 + random.uniform(-.08, .08), 2),
                              measured_on=when))
        db.session.add(Growth(child_id=child.id, kind="height",
                              value=round(49 + m * 2.1 + random.uniform(-.4, .4), 1),
                              measured_on=when))
        db.session.add(Growth(child_id=child.id, kind="head",
                              value=round(34.5 + m * 0.9, 1), measured_on=when))

    # two teeth through
    for code, days_ago in [("lower_left_central", 90), ("lower_right_central", 74)]:
        db.session.add(Tooth(child_id=child.id, tooth_code=code,
                             erupted_on=date.today() - timedelta(days=days_ago)))

    for days, title in [(11, "8-month clinic visit"), (38, "Immunisation catch-up")]:
        db.session.add(Appointment(child_id=child.id, title=title,
                                   location="Westlands Clinic",
                                   starts_at=datetime.now(timezone.utc) + timedelta(days=days)))

    db.session.add(Album(child_id=child.id, title="First year"))
    db.session.add(Album(child_id=child.id, title="Firsts"))
    return child


@demo_bp.post("")
@login_required
def populate():
    """Fill this account with a sample pregnancy and a sample baby."""
    user = _current_user()
    if Child.alive().filter_by(owner_id=user.id).count() > 0:
        return jsonify(error="You already have a child on this account. "
                             "Clear it first if you want fresh sample data.",
                       code="already_populated"), 409

    types = {t.slug: t for t in MilestoneType.query.all()}
    if not types:
        return jsonify(error="Reference content is missing. Run `python seed.py` "
                             "in the backend folder first."), 503

    bump = _mk_pregnancy(user, types)
    maya = _mk_baby(user, types)

    # a trial so premium screens are explorable
    if not Subscription.query.filter_by(user_id=user.id).first():
        db.session.add(Subscription(user_id=user.id, plan="monthly", status="trialing",
                                    provider="none",
                                    trial_ends_at=datetime.now(timezone.utc) + timedelta(days=30)))

    for title, days, kind in [("Week 25 begins", 4, "pregnancy_week"),
                              ("Maya's 9-month check", 25, "growth"),
                              ("Maya turns 1", 120, "birthday")]:
        db.session.add(Reminder(user_id=user.id, kind=kind, title=title,
                                fire_at=datetime.now(timezone.utc) + timedelta(days=days)))

    db.session.commit()
    return jsonify(ok=True, created={"children": 2},
                   children=[bump.to_dict(), maya.to_dict()],
                   message="Sample data added. Explore away."), 201


@demo_bp.delete("")
@login_required
def clear():
    """Remove everything on this account so you can start clean."""
    user = _current_user()
    child_ids = [c.id for c in Child.query.filter_by(owner_id=user.id).all()]
    if child_ids:
        for model in (JournalEntry, Milestone, Growth, Appointment, Tooth,
                      KickSession, Contraction, Album):
            model.query.filter(model.child_id.in_(child_ids)).delete(synchronize_session=False)
        BirthRecord.query.filter(BirthRecord.child_id.in_(child_ids)).delete(
            synchronize_session=False)
        Child.query.filter(Child.id.in_(child_ids)).delete(synchronize_session=False)
    Reminder.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.commit()
    return jsonify(ok=True, message="Cleared."), 200
