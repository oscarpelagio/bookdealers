"""seed admin user, roles, catalogs and favorite establishments

Revision ID: fd0a1b2c3d4e
Revises: f9a0b1c2d3e4
Create Date: 2026-08-16 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fd0a1b2c3d4e'
down_revision: Union[str, Sequence[str], None] = 'f9a0b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Admin dev: admin@example.com / admin (hash Argon2id).
ADMIN_EMAIL = "admin@example.com"
ADMIN_USERNAME = "admin"
ADMIN_FULL_NAME = "Admin"
ADMIN_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=1$4xV5EWp3q46+cAMSUIWglw$"
    "S+b4woyKb/WDNTS2LG22n23efuhNmFrGCPgbGFdByUA"
)

# (catálogo name, service) que usará el admin.
ADMIN_CATALOGS = [
    ("aladi", "z3950"),
    ("catalunya", "ebiblio"),
]

# Bibliotecas físicas favoritas (catálogo aladi) en L'Hospitalet de Llobregat.
FAVORITE_LIBRARIES = [
    ("HOSPITALET DE LLOB.Bellvitge", "Plaça de la Cultura, 1", "08907", "L'Hospitalet de Llobregat", "Barcelona"),
    ("HOSPITALET DE LLOB.Can Sumarro", "Carrer Riera de l'Escorxador, s/n", "08901", "L'Hospitalet de Llobregat", "Barcelona"),
    ("HOSPITALET DE LLOB.J. Janés", "Carrer Doctor Martí i Julià, 33", "08903", "L'Hospitalet de Llobregat", "Barcelona"),
    ("HOSPITALET DE LLOB.La Bòbila", "Plaça de la Bòbila, 1", "08906", "L'Hospitalet de Llobregat", "Barcelona"),
    ("HOSPITALET DE LLOB.La Florida", "Avinguda Masnou, 40", "08905", "L'Hospitalet de Llobregat", "Barcelona"),
    ("HOSPITALET DE LLOB.Plaça d'Europa", "Amadeu Torner, 57", "08902", "L'Hospitalet de Llobregat", "Barcelona"),
    ("HOSPITALET DE LLOB.Tecla Sala", "Avinguda Josep Tarradellas, 44", "08901", "L'Hospitalet de Llobregat", "Barcelona"),
]

# Librerías favoritas (catálogo todostuslibros).
FAVORITE_BOOKSHOPS = [
    ("La Central calle Mallorca", "c/ Mallorca, 237", "08008", "Barcelona", "Barcelona"),
    ("Llibreria Finestres", "c/ Diputació, 249", "08007", "Barcelona", "Barcelona"),
]


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # 1) Crea l'usuari admin si no existeix (idempotent).
    bind.execute(
        sa.text("""
            INSERT INTO users (
                id, email, username, full_name, hashed_password,
                is_email_verified, is_active, failed_login_attempts,
                created_at, updated_at
            )
            VALUES (
                gen_random_uuid(), :email, :username, :full_name, :pw,
                TRUE, TRUE, 0, now(), now()
            )
            ON CONFLICT DO NOTHING
        """),
        {
            "email": ADMIN_EMAIL,
            "username": ADMIN_USERNAME,
            "full_name": ADMIN_FULL_NAME,
            "pw": ADMIN_HASH,
        },
    )

    # 2) Assigna rols ADMIN i USER si no els té.
    bind.execute(
        sa.text("""
            INSERT INTO user_roles (user_id, role_id, created_at)
            SELECT u.id, r.id, now()
            FROM users u, roles r
            WHERE u.email = :email
              AND r.name IN ('USER', 'ADMIN')
            ON CONFLICT DO NOTHING
        """),
        {"email": ADMIN_EMAIL},
    )

    # 3) Catàlegs de l'admin (aladi per biblios, catalunya per eBiblio).
    bind.execute(
        sa.text("""
            INSERT INTO user_catalogs (id, user_id, catalog_id, created_at)
            SELECT gen_random_uuid(), u.id, c.id, now()
            FROM users u, catalogs c
            WHERE u.email = :email
              AND c.name = :catalog_name
              AND c.service = :catalog_service
            ON CONFLICT (user_id, catalog_id) DO NOTHING
        """),
        [
            {"email": ADMIN_EMAIL, "catalog_name": name, "catalog_service": service}
            for name, service in ADMIN_CATALOGS
        ],
    )

    # 4) Establiments favorits: biblioteques (type=library, cat àladi) i
    #    llibreries (type=book_shop, cat todostuslibros). Idempotent per nom.
    for name, street, postal_code, city, province in FAVORITE_LIBRARIES:
        bind.execute(
            sa.text("""
                INSERT INTO establishments (
                    type, name, street, postal_code, city, province,
                    catalog_id, created_at, updated_at
                )
                SELECT 'library', :name, :street, :postal, :city, :province,
                       c.id, now(), now()
                FROM catalogs c
                WHERE c.service = 'z3950' AND c.name = 'aladi'
                ON CONFLICT DO NOTHING
            """),
            {
                "name": name,
                "street": street,
                "postal": postal_code,
                "city": city,
                "province": province,
            },
        )

    for name, street, postal_code, city, province in FAVORITE_BOOKSHOPS:
        bind.execute(
            sa.text("""
                INSERT INTO establishments (
                    type, name, street, postal_code, city, province,
                    catalog_id, created_at, updated_at
                )
                SELECT 'book_shop', :name, :street, :postal, :city, :province,
                       c.id, now(), now()
                FROM catalogs c
                WHERE c.service = 'todostuslibros' AND c.name = 'todostuslibros'
                ON CONFLICT DO NOTHING
            """),
            {
                "name": name,
                "street": street,
                "postal": postal_code,
                "city": city,
                "province": province,
            },
        )

    # 5) Marca tots aquests establiments com a favorits de l'admin.
    bind.execute(
        sa.text("""
            INSERT INTO user_favorite_establishments (id, user_id, establishment_id, created_at)
            SELECT gen_random_uuid(), u.id, e.id, now()
            FROM users u
            JOIN establishments e ON TRUE
            WHERE u.email = :email
              AND e.name = ANY(:favorite_names)
            ON CONFLICT (user_id, establishment_id) DO NOTHING
        """),
        {
            "email": ADMIN_EMAIL,
            "favorite_names": [
                name for name, *_ in FAVORITE_LIBRARIES + FAVORITE_BOOKSHOPS
            ],
        },
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    bind.execute(
        sa.text("""
            DELETE FROM user_favorite_establishments
            WHERE user_id = (SELECT id FROM users WHERE email = :email)
        """),
        {"email": ADMIN_EMAIL},
    )
    bind.execute(
        sa.text("""
            DELETE FROM user_catalogs
            WHERE user_id = (SELECT id FROM users WHERE email = :email)
        """),
        {"email": ADMIN_EMAIL},
    )
    bind.execute(
        sa.text("""
            DELETE FROM establishments
            WHERE name = ANY(:favorite_names)
        """),
        {
            "favorite_names": [
                name for name, *_ in FAVORITE_LIBRARIES + FAVORITE_BOOKSHOPS
            ],
        },
    )
    bind.execute(
        sa.text("""
            DELETE FROM user_roles
            WHERE user_id = (SELECT id FROM users WHERE email = :email)
        """),
        {"email": ADMIN_EMAIL},
    )
    bind.execute(
        sa.text("""
            DELETE FROM users WHERE email = :email
        """),
        {"email": ADMIN_EMAIL},
    )