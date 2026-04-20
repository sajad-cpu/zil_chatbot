"""Database migrations to create tables on startup.

Idempotent: uses CREATE TABLE IF NOT EXISTS and CREATE INDEX IF NOT EXISTS.
"""

from __future__ import annotations

from db.pool import get_pool

DEFAULT_CLINIC_DOCTORS = [
    ("D1", "Dr. Anil Sharma", "General Physician", "10:00-14:00"),
    ("D2", "Dr. Neha Verma", "Dermatologist", "11:00-16:00"),
    ("D3", "Dr. Rohit Mehta", "Orthopedic", "09:00-13:00"),
    ("D4", "Dr. Kavita Rao", "Pediatrician", "10:00-15:00"),
    ("D5", "Dr. Sanjay Iyer", "ENT Specialist", "12:00-17:00"),
]


async def init_db() -> None:
    """Create all required tables if they don't exist."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Create users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)

        # Create conversations table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL DEFAULT 'New Chat',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)

        # Create messages table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)

        # Create indexes for common queries
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id
            ON conversations(user_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
            ON messages(conversation_id)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_user_id
            ON messages(user_id)
        """)

        # Create clinic_doctors table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS clinic_doctors (
                doctor_id TEXT PRIMARY KEY,
                doctor_name TEXT NOT NULL,
                speciality TEXT NOT NULL,
                office_timing TEXT NOT NULL
            )
        """)

        # Create clinic_customers table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS clinic_customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)

        # Create clinic_bookings table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS clinic_bookings (
                booking_id TEXT PRIMARY KEY,
                doctor_id TEXT NOT NULL REFERENCES clinic_doctors(doctor_id) ON DELETE RESTRICT,
                customer_id TEXT NOT NULL REFERENCES clinic_customers(customer_id) ON DELETE CASCADE,
                appointment_date DATE NOT NULL,
                appointment_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Confirmed',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_clinic_doctors_speciality
            ON clinic_doctors(speciality)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_clinic_customers_phone
            ON clinic_customers(phone)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_clinic_bookings_doctor_date
            ON clinic_bookings(doctor_id, appointment_date)
        """)

        await conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_clinic_bookings_unique_slot
            ON clinic_bookings(doctor_id, appointment_date, appointment_time)
            WHERE status = 'Confirmed'
        """)

        for doctor in DEFAULT_CLINIC_DOCTORS:
            await conn.execute(
                """
                INSERT INTO clinic_doctors
                (doctor_id, doctor_name, speciality, office_timing)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (doctor_id) DO NOTHING
                """,
                *doctor,
            )

        print("[migrations] Database initialized successfully")
