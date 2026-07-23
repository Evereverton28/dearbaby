# -*- coding: utf-8 -*-
"""Seed data that demonstrates the system: one account per role, reference
content, and a demo family with real memories so no screen is empty.

The super_admin is created HERE and only here.

    python seed.py
"""
import random
from datetime import datetime, timedelta, timezone, date
from dearbaby import create_app
from dearbaby.extensions import db
from dearbaby.models import (User, UserSettings, Child, PregnancyWeek, MilestoneType,
                        Milestone, JournalEntry, Growth, Group, GroupMember, Post,
                        Comment, Recipe, Subscription, AnalyticsEvent, Appointment,
                        Report, ChildMember)
from dearbaby.roles import PARENT, MODERATOR, ADMIN, SUPER_ADMIN
from dearbaby.content import PREGNANCY_WEEKS, MILESTONE_TYPES, GROUPS, RECIPES

PW = "ChangeMe!2026"
ACCOUNTS = [
    ("owner@dearbaby.app", "Nia Owner", SUPER_ADMIN),
    ("admin@dearbaby.app", "Ade Admin", ADMIN),
    ("mod@dearbaby.app", "Moses Mod", MODERATOR),
    ("amara@example.com", "Amara", PARENT),
    ("joy@example.com", "Joy", PARENT),
    ("wanjiku@example.com", "Wanjiku", PARENT),
]


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        # ---- accounts -------------------------------------------------
        users = {}
        for email, name, role in ACCOUNTS:
            u = User.query.filter_by(email=email).first()
            if u is None:
                u = User(email=email, display_name=name, role=role, email_verified=True)
                u.set_password(PW)
                db.session.add(u)
                db.session.flush()
                db.session.add(UserSettings(user_id=u.id))
            users[email] = u
        db.session.commit()

        # ---- reference content ----------------------------------------
        if PregnancyWeek.query.count() == 0:
            for wk, size, emoji, ln, wt, summary, tip in PREGNANCY_WEEKS:
                db.session.add(PregnancyWeek(week=wk, size_label=size, emoji=emoji,
                                             length_cm=ln, weight_g=wt,
                                             summary=summary, tip=tip))
        if MilestoneType.query.count() == 0:
            for slug, label, emoji, stage, order in MILESTONE_TYPES:
                db.session.add(MilestoneType(slug=slug, label=label, emoji=emoji,
                                             stage=stage, sort_order=order))
        if Group.query.count() == 0:
            for slug, name, emoji, desc in GROUPS:
                db.session.add(Group(slug=slug, name=name, emoji=emoji, description=desc))
        if Recipe.query.count() == 0:
            for title, cat, age, mins, emoji, desc, ing, steps, allerg in RECIPES:
                db.session.add(Recipe(title=title, category=cat, min_age_months=age,
                                      prep_minutes=mins, emoji=emoji, description=desc,
                                      ingredients=ing, steps=steps, allergens=allerg))
        db.session.commit()

        amara, joy, wanjiku = users["amara@example.com"], users["joy@example.com"], users["wanjiku@example.com"]

        # ---- demo family: Amara is 24 weeks pregnant ------------------
        if Child.query.filter_by(owner_id=amara.id).count() == 0:
            bump = Child(owner_id=amara.id, name="Baby",
                         due_date=date.today() + timedelta(weeks=16))
            db.session.add(bump)
            db.session.flush()
            db.session.add(ChildMember(child_id=bump.id, user_id=joy.id, can_edit=True))

            types = {t.slug: t for t in MilestoneType.query.all()}
            for slug, days_ago in [("positive_test", 150), ("first_scan", 120),
                                   ("heard_heartbeat", 118), ("first_kick", 60),
                                   ("anomaly_scan", 28)]:
                t = types[slug]
                db.session.add(Milestone(child_id=bump.id, type_id=t.id, title=t.label,
                                         emoji=t.emoji,
                                         occurred_on=date.today() - timedelta(days=days_ago)))

            for days_ago, title, body, mood in [
                (120, "We saw the heartbeat",
                 "Tiny and impossibly fast. I cried in the car park afterwards.", "overjoyed"),
                (60, "First proper kick",
                 "I was halfway through dinner and felt a definite thump. Not wind this time.", "excited"),
                (28, "The 20-week scan",
                 "Everything measuring beautifully. We got a printout of the profile view.", "grateful"),
                (7, "Slowing down",
                 "Back is aching and sleep is patchy, but the kicks at night make up for it.", "tired"),
            ]:
                db.session.add(JournalEntry(child_id=bump.id, author_id=amara.id, title=title,
                                            body=body, mood=mood, week=bump.current_week(),
                                            entry_date=date.today() - timedelta(days=days_ago)))

            db.session.add(Appointment(child_id=bump.id, title="Antenatal check-up",
                                       location="Nairobi Women's Hospital",
                                       starts_at=datetime.now(timezone.utc) + timedelta(days=9)))
            db.session.add(Appointment(child_id=bump.id, title="Glucose screening",
                                       location="Nairobi Women's Hospital",
                                       starts_at=datetime.now(timezone.utc) + timedelta(days=25)))

        # ---- demo family: Wanjiku's baby Maya, 8 months ---------------
        if Child.query.filter_by(owner_id=wanjiku.id).count() == 0:
            maya = Child(owner_id=wanjiku.id, name="Maya", sex="female",
                         birth_date=date.today() - timedelta(days=245))
            db.session.add(maya)
            db.session.flush()
            types = {t.slug: t for t in MilestoneType.query.all()}
            for slug, days_ago, note in [
                ("birth", 245, "3.2kg, born just after midnight."),
                ("first_smile", 200, "Right after her morning feed. We both cried a little."),
                ("first_laugh", 170, "Her father sneezed and she found it hilarious."),
                ("rolled_over", 130, "Front to back, then straight back again."),
                ("first_tooth", 90, "Bottom left. Days of grumpiness explained."),
                ("sat_up", 75, "Wobbly but unassisted for a whole minute."),
                ("first_food", 60, "Sweet potato puree. Mostly went on the wall."),
            ]:
                t = types[slug]
                db.session.add(Milestone(child_id=maya.id, type_id=t.id, title=t.label,
                                         emoji=t.emoji, note=note,
                                         occurred_on=date.today() - timedelta(days=days_ago)))
            # growth curve
            for months in range(0, 9):
                d = maya.birth_date + timedelta(days=months * 30)
                db.session.add(Growth(child_id=maya.id, kind="weight",
                                      value=round(3.2 + months * 0.62, 2), measured_on=d))
                db.session.add(Growth(child_id=maya.id, kind="height",
                                      value=round(49 + months * 2.1, 1), measured_on=d))

        # ---- community ------------------------------------------------
        if Post.query.count() == 0:
            groups = {g.slug: g for g in Group.query.all()}
            seeds = [
                (amara, "first-time-parents", "question", "How much water is too much?",
                 "I'm 24 weeks and constantly thirsty. Is there such a thing as overdoing it?"),
                (wanjiku, "weaning", "discussion", "Baby-led weaning, one month in",
                 "We started at six months and the mess is unreal, but she's genuinely enjoying food. Anyone else find purees stressful by comparison?"),
                (joy, "sleep", "question", "Four-month sleep regression \u2014 does it end?",
                 "Three weeks of hourly wake-ups. Tell me it passes."),
                (wanjiku, "nairobi-parents", "question", "Recommendations for a paediatrician?",
                 "Moving to Westlands next month and looking for someone good with babies."),
                (amara, "due-this-year", "discussion", "November due dates, say hello",
                 "Due the 5th. Second trimester has been so much kinder than the first."),
            ]
            for author, gslug, kind, title, body in seeds:
                p = Post(author_id=author.id, group_id=groups[gslug].id, kind=kind,
                         title=title, body=body, like_count=random.randint(2, 24),
                         created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 20)))
                db.session.add(p)
                db.session.flush()
                for replier, text in [(joy, "You're not alone \u2014 same here."),
                                      (wanjiku, "This got easier for us around week three.")]:
                    if replier.id != author.id:
                        db.session.add(Comment(post_id=p.id, author_id=replier.id, body=text))
                        p.reply_count = (p.reply_count or 0) + 1
                db.session.add(GroupMember(group_id=groups[gslug].id, user_id=author.id))

            # one open report so the moderation queue isn't empty
            spam = Post(author_id=joy.id, group_id=groups["weaning"].id,
                        title="BUY CHEAP FORMULA NOW",
                        body="Best prices guaranteed, message me for a link!!!")
            db.session.add(spam)
            db.session.flush()
            db.session.add(Report(reporter_id=wanjiku.id, entity_type="post",
                                  entity_id=spam.id, reason="Spam / advertising"))

        # ---- subscriptions --------------------------------------------
        if Subscription.query.count() == 0:
            db.session.add(Subscription(user_id=amara.id, plan="monthly", status="trialing",
                                        provider="none",
                                        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=18)))
            db.session.add(Subscription(user_id=wanjiku.id, plan="annual", status="active",
                                        provider="stripe",
                                        current_period_end=datetime.now(timezone.utc) + timedelta(days=280)))

        # ---- synthetic traffic ----------------------------------------
        if AnalyticsEvent.query.count() == 0:
            paths = ["/", "/pricing", "/app", "/app/journal", "/app/gallery",
                     "/app/milestones", "/community", "/recipes"]
            devices = ["mobile"] * 6 + ["desktop"] * 3 + ["tablet"]
            now = datetime.now(timezone.utc)
            for d in range(30):
                for _ in range(random.randint(25, 70)):
                    db.session.add(AnalyticsEvent(
                        visitor_id=f"v{random.randint(1, 500)}",
                        session_id=f"s{random.randint(1, 1200)}", name="pageview",
                        path=random.choice(paths), device_type=random.choice(devices),
                        browser=random.choice(["Chrome", "Safari", "Firefox"]),
                        os=random.choice(["Android", "iOS", "Windows"]),
                        created_at=now - timedelta(days=d, minutes=random.randint(0, 1439))))
                for step, cap in [("signup_started", 14), ("account_created", 9),
                                  ("first_memory_added", 6), ("subscribed", 3)]:
                    for _ in range(random.randint(0, cap)):
                        db.session.add(AnalyticsEvent(
                            visitor_id=f"v{random.randint(1, 500)}",
                            session_id=f"s{random.randint(1, 1200)}", name=step,
                            path="/signup", device_type=random.choice(devices),
                            browser="Chrome", os="Android",
                            created_at=now - timedelta(days=d)))

        db.session.commit()

        print("Seeded. Password for every account: " + PW)
        for email, _, role in ACCOUNTS:
            print("  %-12s %s" % (role, email))
        print("\nReference content:")
        print("  pregnancy weeks : %d" % PregnancyWeek.query.count())
        print("  milestone types : %d" % MilestoneType.query.count())
        print("  recipes         : %d" % Recipe.query.count())
        print("  groups          : %d" % Group.query.count())
        print("Demo data:")
        print("  children        : %d" % Child.query.count())
        print("  milestones      : %d" % Milestone.query.count())
        print("  posts           : %d" % Post.query.count())
        print("  analytics events: %d" % AnalyticsEvent.query.count())


if __name__ == "__main__":
    seed()
