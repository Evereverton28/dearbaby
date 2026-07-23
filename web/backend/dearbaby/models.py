"""Full DearBaby domain model. Soft-delete + updated_at everywhere so the
mobile client can sync later with ?since= and tombstones."""
from datetime import datetime, timezone, date
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from dearbaby.extensions import db
from dearbaby.roles import PARENT


def _uuid(): return str(uuid.uuid4())
def _now(): return datetime.now(timezone.utc)


class Base(db.Model):
    __abstract__ = True
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)
    deleted_at = db.Column(db.DateTime, nullable=True)

    @classmethod
    def alive(cls):
        return cls.query.filter(cls.deleted_at.is_(None))


# ---------------------------------------------------------------- users
class User(Base):
    __tablename__ = "users"
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255))
    display_name = db.Column(db.String(120), nullable=False)
    avatar_url = db.Column(db.String(512))
    bio = db.Column(db.Text)
    role = db.Column(db.String(32), nullable=False, default=PARENT)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    email_verified = db.Column(db.Boolean, default=False)

    def set_password(self, raw): self.password_hash = generate_password_hash(raw)
    def check_password(self, raw):
        return bool(self.password_hash) and check_password_hash(self.password_hash, raw)

    def to_dict(self, full=False):
        d = {"id": self.id, "email": self.email, "display_name": self.display_name,
             "avatar_url": self.avatar_url, "role": self.role, "is_active": self.is_active,
             "created_at": self.created_at.isoformat() if self.created_at else None}
        if full:
            d["bio"] = self.bio
        return d

    def public(self):
        return {"id": self.id, "display_name": self.display_name, "avatar_url": self.avatar_url}


class UserSettings(db.Model):
    __tablename__ = "user_settings"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), primary_key=True)
    theme = db.Column(db.String(16), default="system")
    notif_milestones = db.Column(db.Boolean, default=True)
    notif_pregnancy = db.Column(db.Boolean, default=True)
    notif_vaccination = db.Column(db.Boolean, default=True)
    notif_birthday = db.Column(db.Boolean, default=True)
    notif_growth = db.Column(db.Boolean, default=True)
    auto_backup = db.Column(db.Boolean, default=True)
    units = db.Column(db.String(16), default="metric")
    profile_public = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# ------------------------------------------------------------- children
class Child(Base):
    __tablename__ = "children"
    owner_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True, nullable=False)
    name = db.Column(db.String(120))
    due_date = db.Column(db.Date)
    birth_date = db.Column(db.Date)
    sex = db.Column(db.String(16))
    cover_url = db.Column(db.String(512))

    def current_week(self):
        if self.birth_date or not self.due_date:
            return None
        days_left = (self.due_date - date.today()).days
        wk = 40 - (days_left // 7)
        return max(1, min(42, wk))

    def age_days(self):
        return (date.today() - self.birth_date).days if self.birth_date else None

    def to_dict(self):
        return {"id": self.id, "owner_id": self.owner_id, "name": self.name,
                "due_date": self.due_date.isoformat() if self.due_date else None,
                "birth_date": self.birth_date.isoformat() if self.birth_date else None,
                "sex": self.sex, "cover_url": self.cover_url,
                "stage": "baby" if self.birth_date else "pregnancy",
                "current_week": self.current_week(), "age_days": self.age_days()}


class ChildMember(db.Model):
    __tablename__ = "child_members"
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), primary_key=True)
    can_edit = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=_now)


# ---------------------------------------------------------------- media
class Media(Base):
    __tablename__ = "media"
    owner_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), index=True)
    kind = db.Column(db.String(16), default="photo")     # photo|video|scan|document
    url = db.Column(db.String(512))
    thumb_url = db.Column(db.String(512))
    filename = db.Column(db.String(255))
    mime_type = db.Column(db.String(120))
    bytes = db.Column(db.Integer)
    caption = db.Column(db.Text)
    captured_at = db.Column(db.DateTime, default=_now)

    def to_dict(self):
        return {"id": self.id, "child_id": self.child_id, "kind": self.kind,
                "url": self.url, "thumb_url": self.thumb_url, "caption": self.caption,
                "filename": self.filename, "bytes": self.bytes,
                "captured_at": self.captured_at.isoformat() if self.captured_at else None}


class MediaLink(db.Model):
    __tablename__ = "media_links"
    media_id = db.Column(db.String(36), db.ForeignKey("media.id"), primary_key=True)
    entity_type = db.Column(db.String(32), primary_key=True)
    entity_id = db.Column(db.String(36), primary_key=True)
    position = db.Column(db.Integer, default=0)


class Album(Base):
    __tablename__ = "albums"
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), index=True)
    title = db.Column(db.String(200), nullable=False)
    cover_url = db.Column(db.String(512))

    def to_dict(self, count=0):
        return {"id": self.id, "child_id": self.child_id, "title": self.title,
                "cover_url": self.cover_url, "item_count": count,
                "created_at": self.created_at.isoformat()}


class AlbumMedia(db.Model):
    __tablename__ = "album_media"
    album_id = db.Column(db.String(36), db.ForeignKey("albums.id"), primary_key=True)
    media_id = db.Column(db.String(36), db.ForeignKey("media.id"), primary_key=True)
    position = db.Column(db.Integer, default=0)


class Share(Base):
    __tablename__ = "shares"
    owner_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    entity_type = db.Column(db.String(32))
    entity_id = db.Column(db.String(36))
    token = db.Column(db.String(64), unique=True, index=True)
    expires_at = db.Column(db.DateTime)


# ----------------------------------------------------------- pregnancy
class PregnancyWeek(db.Model):
    __tablename__ = "pregnancy_weeks"
    week = db.Column(db.Integer, primary_key=True)
    size_label = db.Column(db.String(120))
    emoji = db.Column(db.String(8))
    length_cm = db.Column(db.Float)
    weight_g = db.Column(db.Float)
    summary = db.Column(db.Text)
    tip = db.Column(db.Text)

    def to_dict(self):
        return {"week": self.week, "size_label": self.size_label, "emoji": self.emoji,
                "length_cm": self.length_cm, "weight_g": self.weight_g,
                "summary": self.summary, "tip": self.tip,
                "trimester": 1 if self.week <= 13 else (2 if self.week <= 27 else 3)}


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), index=True)
    author_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    mood = db.Column(db.String(32))
    week = db.Column(db.Integer)
    entry_date = db.Column(db.Date, default=date.today)

    def to_dict(self, media=None):
        return {"id": self.id, "child_id": self.child_id, "title": self.title,
                "body": self.body, "mood": self.mood, "week": self.week,
                "entry_date": self.entry_date.isoformat() if self.entry_date else None,
                "media": media or []}


class Appointment(Base):
    __tablename__ = "appointments"
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), index=True)
    title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200))
    notes = db.Column(db.Text)
    starts_at = db.Column(db.DateTime, nullable=False)

    def to_dict(self):
        return {"id": self.id, "child_id": self.child_id, "title": self.title,
                "location": self.location, "notes": self.notes,
                "starts_at": self.starts_at.isoformat() if self.starts_at else None}


class KickSession(Base):
    __tablename__ = "kick_sessions"
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), index=True)
    started_at = db.Column(db.DateTime, default=_now)
    ended_at = db.Column(db.DateTime)
    kick_count = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {"id": self.id, "child_id": self.child_id, "kick_count": self.kick_count,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "ended_at": self.ended_at.isoformat() if self.ended_at else None}


class Contraction(Base):
    __tablename__ = "contractions"
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), index=True)
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime)

    def duration_s(self):
        return int((self.ended_at - self.started_at).total_seconds()) if self.ended_at else None

    def to_dict(self):
        return {"id": self.id, "child_id": self.child_id,
                "started_at": self.started_at.isoformat(),
                "ended_at": self.ended_at.isoformat() if self.ended_at else None,
                "duration_s": self.duration_s()}


# -------------------------------------------------------- memory book
class MilestoneType(db.Model):
    __tablename__ = "milestone_types"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    slug = db.Column(db.String(64), unique=True)
    label = db.Column(db.String(120))
    emoji = db.Column(db.String(8))
    stage = db.Column(db.String(16), default="baby")   # pregnancy|baby
    sort_order = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {"id": self.id, "slug": self.slug, "label": self.label,
                "emoji": self.emoji, "stage": self.stage}


class Milestone(Base):
    __tablename__ = "milestones"
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), index=True)
    type_id = db.Column(db.String(36), db.ForeignKey("milestone_types.id"))
    title = db.Column(db.String(200), nullable=False)
    note = db.Column(db.Text)
    emoji = db.Column(db.String(8))
    occurred_on = db.Column(db.Date)

    def to_dict(self, media=None):
        return {"id": self.id, "child_id": self.child_id, "type_id": self.type_id,
                "title": self.title, "note": self.note, "emoji": self.emoji,
                "occurred_on": self.occurred_on.isoformat() if self.occurred_on else None,
                "media": media or []}


class BirthRecord(db.Model):
    __tablename__ = "birth_records"
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), primary_key=True)
    born_at = db.Column(db.DateTime)
    place = db.Column(db.String(200))
    weight_g = db.Column(db.Float)
    length_cm = db.Column(db.Float)
    head_circ_cm = db.Column(db.Float)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {"child_id": self.child_id,
                "born_at": self.born_at.isoformat() if self.born_at else None,
                "place": self.place, "weight_g": self.weight_g,
                "length_cm": self.length_cm, "head_circ_cm": self.head_circ_cm,
                "notes": self.notes}


class Tooth(db.Model):
    __tablename__ = "teeth"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), index=True)
    tooth_code = db.Column(db.String(40))
    erupted_on = db.Column(db.Date)

    def to_dict(self):
        return {"id": self.id, "child_id": self.child_id, "tooth_code": self.tooth_code,
                "erupted_on": self.erupted_on.isoformat() if self.erupted_on else None}


class Growth(Base):
    __tablename__ = "growth"
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), index=True)
    kind = db.Column(db.String(24))          # height|weight|head
    value = db.Column(db.Float, nullable=False)
    measured_on = db.Column(db.Date, default=date.today)

    def to_dict(self):
        return {"id": self.id, "child_id": self.child_id, "kind": self.kind,
                "value": self.value, "measured_on": self.measured_on.isoformat()}


# --------------------------------------------------------- scrapbook
class ScrapbookPage(Base):
    __tablename__ = "scrapbook_pages"
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), index=True)
    title = db.Column(db.String(200))
    layout = db.Column(db.JSON, default=dict)
    theme = db.Column(db.String(40), default="oat")
    position = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {"id": self.id, "child_id": self.child_id, "title": self.title,
                "layout": self.layout or {}, "theme": self.theme, "position": self.position}


class PrintBook(Base):
    __tablename__ = "print_books"
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"), index=True)
    title = db.Column(db.String(200))
    page_ids = db.Column(db.JSON, default=list)
    status = db.Column(db.String(24), default="draft")
    pdf_url = db.Column(db.String(512))

    def to_dict(self):
        return {"id": self.id, "child_id": self.child_id, "title": self.title,
                "page_ids": self.page_ids or [], "status": self.status,
                "pdf_url": self.pdf_url, "created_at": self.created_at.isoformat()}


# --------------------------------------------------------- community
class Group(Base):
    __tablename__ = "groups"
    slug = db.Column(db.String(80), unique=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    emoji = db.Column(db.String(8))

    def to_dict(self, members=0, posts=0):
        return {"id": self.id, "slug": self.slug, "name": self.name, "emoji": self.emoji,
                "description": self.description, "member_count": members, "post_count": posts}


class GroupMember(db.Model):
    __tablename__ = "group_members"
    group_id = db.Column(db.String(36), db.ForeignKey("groups.id"), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), primary_key=True)
    created_at = db.Column(db.DateTime, default=_now)


class Post(Base):
    __tablename__ = "posts"
    author_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    group_id = db.Column(db.String(36), db.ForeignKey("groups.id"), index=True)
    kind = db.Column(db.String(24), default="discussion")   # discussion|question
    title = db.Column(db.String(240))
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(24), default="visible")    # visible|hidden|removed
    like_count = db.Column(db.Integer, default=0)
    reply_count = db.Column(db.Integer, default=0)

    def to_dict(self, author=None, group=None, liked=False):
        return {"id": self.id, "kind": self.kind, "title": self.title, "body": self.body,
                "status": self.status, "like_count": self.like_count,
                "reply_count": self.reply_count, "liked": liked,
                "author": author.public() if author else None,
                "group": {"id": group.id, "name": group.name, "slug": group.slug} if group else None,
                "created_at": self.created_at.isoformat()}


class Comment(Base):
    __tablename__ = "comments"
    post_id = db.Column(db.String(36), db.ForeignKey("posts.id"), index=True)
    author_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(24), default="visible")
    like_count = db.Column(db.Integer, default=0)

    def to_dict(self, author=None):
        return {"id": self.id, "post_id": self.post_id, "body": self.body,
                "status": self.status, "like_count": self.like_count,
                "author": author.public() if author else None,
                "created_at": self.created_at.isoformat()}


class Like(db.Model):
    __tablename__ = "likes"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), primary_key=True)
    entity_type = db.Column(db.String(24), primary_key=True)
    entity_id = db.Column(db.String(36), primary_key=True)
    created_at = db.Column(db.DateTime, default=_now)


class Follow(db.Model):
    __tablename__ = "follows"
    follower_id = db.Column(db.String(36), db.ForeignKey("users.id"), primary_key=True)
    followee_id = db.Column(db.String(36), db.ForeignKey("users.id"), primary_key=True)
    created_at = db.Column(db.DateTime, default=_now)


class Report(Base):
    __tablename__ = "reports"
    reporter_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    entity_type = db.Column(db.String(24))
    entity_id = db.Column(db.String(36))
    reason = db.Column(db.Text)
    status = db.Column(db.String(24), default="open")   # open|actioned|dismissed
    handled_by = db.Column(db.String(36), db.ForeignKey("users.id"))

    def to_dict(self, snippet=None, reporter=None):
        return {"id": self.id, "entity_type": self.entity_type, "entity_id": self.entity_id,
                "reason": self.reason, "status": self.status, "snippet": snippet,
                "reporter": reporter.public() if reporter else None,
                "created_at": self.created_at.isoformat()}


class ModerationAction(db.Model):
    __tablename__ = "moderation_actions"
    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    moderator_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    entity_type = db.Column(db.String(24))
    entity_id = db.Column(db.String(36))
    action = db.Column(db.String(24))
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_now)


# ----------------------------------------------------------- recipes
class Recipe(Base):
    __tablename__ = "recipes"
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(40))       # weaning|puree|finger_food|toddler
    min_age_months = db.Column(db.Integer)
    prep_minutes = db.Column(db.Integer)
    description = db.Column(db.Text)
    ingredients = db.Column(db.JSON, default=list)
    steps = db.Column(db.JSON, default=list)
    emoji = db.Column(db.String(8))
    allergens = db.Column(db.JSON, default=list)

    def to_dict(self, favorited=False):
        return {"id": self.id, "title": self.title, "category": self.category,
                "min_age_months": self.min_age_months, "prep_minutes": self.prep_minutes,
                "description": self.description, "ingredients": self.ingredients or [],
                "steps": self.steps or [], "emoji": self.emoji,
                "allergens": self.allergens or [], "favorited": favorited}


class RecipeFavorite(db.Model):
    __tablename__ = "recipe_favorites"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), primary_key=True)
    recipe_id = db.Column(db.String(36), db.ForeignKey("recipes.id"), primary_key=True)
    created_at = db.Column(db.DateTime, default=_now)


# ----------------------------------------------- notifications/reminders
class Reminder(Base):
    __tablename__ = "reminders"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    child_id = db.Column(db.String(36), db.ForeignKey("children.id"))
    kind = db.Column(db.String(32))
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)
    fire_at = db.Column(db.DateTime, nullable=False)
    sent_at = db.Column(db.DateTime)

    def to_dict(self):
        return {"id": self.id, "kind": self.kind, "title": self.title, "body": self.body,
                "child_id": self.child_id, "fire_at": self.fire_at.isoformat(),
                "sent": self.sent_at is not None}


class Notification(Base):
    __tablename__ = "notifications"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    link = db.Column(db.String(255))
    read_at = db.Column(db.DateTime)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "body": self.body, "link": self.link,
                "read": self.read_at is not None, "created_at": self.created_at.isoformat()}


# --------------------------------------------------- subscriptions
class Subscription(Base):
    __tablename__ = "subscriptions"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    plan = db.Column(db.String(24))            # monthly|annual
    status = db.Column(db.String(24), default="trialing")
    provider = db.Column(db.String(24))        # stripe (covers card, Apple Pay, Google Pay)
    provider_ref = db.Column(db.String(120))
    trial_ends_at = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    cancel_at_period_end = db.Column(db.Boolean, default=False)

    def is_premium(self):
        if self.status not in ("trialing", "active"):
            return False
        end = self.current_period_end or self.trial_ends_at
        return end is None or end.replace(tzinfo=timezone.utc) > _now()

    def to_dict(self):
        return {"id": self.id, "plan": self.plan, "status": self.status,
                "provider": self.provider, "premium": self.is_premium(),
                "cancel_at_period_end": self.cancel_at_period_end,
                "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
                "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None}


class Payment(Base):
    __tablename__ = "payments"
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), index=True)
    subscription_id = db.Column(db.String(36), db.ForeignKey("subscriptions.id"))
    provider = db.Column(db.String(24))
    provider_ref = db.Column(db.String(120))
    amount_cents = db.Column(db.Integer)
    currency = db.Column(db.String(8), default="KES")
    status = db.Column(db.String(24), default="pending")
    raw = db.Column(db.JSON)

    def to_dict(self):
        return {"id": self.id, "provider": self.provider, "amount_cents": self.amount_cents,
                "currency": self.currency, "status": self.status,
                "provider_ref": self.provider_ref, "created_at": self.created_at.isoformat()}


class Announcement(Base):
    __tablename__ = "announcements"
    author_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    audience = db.Column(db.String(24), default="all")
    published_at = db.Column(db.DateTime)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "body": self.body,
                "audience": self.audience,
                "published_at": self.published_at.isoformat() if self.published_at else None,
                "created_at": self.created_at.isoformat()}


class AnalyticsEvent(db.Model):
    __tablename__ = "analytics_events"
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(64), index=True)
    session_id = db.Column(db.String(64), index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    name = db.Column(db.String(64), nullable=False, index=True)
    path = db.Column(db.String(512))
    referrer = db.Column(db.String(512))
    device_type = db.Column(db.String(32))
    browser = db.Column(db.String(64))
    os = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=_now, index=True)
