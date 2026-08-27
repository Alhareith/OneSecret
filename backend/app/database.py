"""أدوات SQLAlchemy الخاصة بالاتصال والنماذج فقط."""

import json
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """الأصل الذي ترث منه جداول OneSecret."""


def normalize_database_url(database_url: str) -> str:
    """يوائم عنوان MySQL العام مع PyMySQL المثبت في متطلبات Python.

    بعض المنصات تقدم `mysql://` من دون تسمية driver. SQLAlchemy يفسره
    افتراضيًا عبر MySQLdb غير المثبت هنا، لذلك نحدد PyMySQL صراحةً من دون
    لمس اسم الخادم أو اسم القاعدة أو بيانات الاعتماد.
    """

    if database_url.startswith("mysql://"):
        return f"mysql+pymysql://{database_url.removeprefix('mysql://')}"

    return database_url


def prepare_database_connection(database_url: str) -> tuple[str | URL, dict[str, Any]]:
    """يفصل إعداد SSL JSON الذي تقدمه المنصة عن عنوان PyMySQL.

    تقدم بعض عناوين MySQL قيمة مثل `ssl={...}` داخل query string. SQLAlchemy
    يمررها نصًا إلى PyMySQL، بينما تتوقع المكتبة قاموس SSL. نفك JSON ونمرره
    ضمن `connect_args` من دون كشف أو تعديل أي بيانات اعتماد داخل العنوان.
    """

    normalized_database_url = normalize_database_url(database_url)
    if not normalized_database_url.startswith("mysql+pymysql://"):
        return normalized_database_url, {}

    parsed_url = make_url(normalized_database_url)
    ssl_value = parsed_url.query.get("ssl")
    if ssl_value is None:
        return parsed_url, {}

    try:
        ssl_options = json.loads(ssl_value)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("The database SSL configuration is invalid") from error

    if not isinstance(ssl_options, dict):
        raise ValueError("The database SSL configuration is invalid")

    return parsed_url.difference_update_query(["ssl"]), {"ssl": ssl_options}


def build_engine(database_url: str) -> Engine:
    """ينشئ محرك قاعدة بيانات من عنوان اتصال واضح.

    يدعم SQLite للاختبارات المحلية وMySQL/TiDB للاستخدام الفعلي لاحقًا.
    """

    if not database_url:
        raise ValueError("A database URL is required")

    prepared_database_url, connect_args = prepare_database_connection(database_url)

    if str(prepared_database_url).startswith("sqlite"):
        return create_engine(
            prepared_database_url,
            future=True,
            connect_args={"check_same_thread": False},
        )

    return create_engine(prepared_database_url, future=True, pool_pre_ping=True, connect_args=connect_args)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """ينشئ مصنع جلسات لاستخدامه عند إضافة الاستعلامات في مرحلة API."""

    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
