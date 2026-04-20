"""Clinic booking flow backed by the main Postgres database."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any

from db.pool import get_pool

DEFAULT_DOCTORS = [
    ("D1", "Dr. Anil Sharma", "General Physician", "10:00-14:00"),
    ("D2", "Dr. Neha Verma", "Dermatologist", "11:00-16:00"),
    ("D3", "Dr. Rohit Mehta", "Orthopedic", "09:00-13:00"),
    ("D4", "Dr. Kavita Rao", "Pediatrician", "10:00-15:00"),
    ("D5", "Dr. Sanjay Iyer", "ENT Specialist", "12:00-17:00"),
]

CLINIC_SESSIONS: dict[str, dict[str, Any]] = {}


def _assistant(content: str, options: list[str] | None = None) -> dict[str, Any]:
    message = {"role": "assistant", "content": content}
    if options:
        message["options"] = options
    return message


def _user(content: str) -> dict[str, str]:
    return {"role": "user", "content": content}


def _base_state() -> dict[str, Any]:
    return {
        "stage": "greeting",
        "messages": [],
        "available_options": [],
        "selected_speciality": None,
        "selected_doctor": None,
        "selected_date": None,
        "selected_slot": None,
        "customer_name": None,
        "customer_phone": None,
        "booking_id": None,
    }


def _add_prompt(state: dict[str, Any], content: str, options: list[str] | None = None) -> None:
    if state["messages"] and state["messages"][-1]["role"] == "assistant":
        last = state["messages"][-1]
        if last.get("content") == content and last.get("options", []) == (options or []):
            state["available_options"] = options or []
            return
    state["messages"].append(_assistant(content, options))
    state["available_options"] = options or []


def _today_and_tomorrow() -> tuple[str, str]:
    today_dt = datetime.now()
    tomorrow_dt = today_dt + timedelta(days=1)
    return today_dt.strftime("%Y-%m-%d"), tomorrow_dt.strftime("%Y-%m-%d")


def _parse_appointment_date(value: str) -> date:
    """Convert YYYY-MM-DD string to a Python date for asyncpg DATE columns."""
    return datetime.strptime(value, "%Y-%m-%d").date()


def _generate_time_slots(office_timing: str) -> list[str]:
    start_time, end_time = office_timing.split("-")
    start_hour = int(start_time.split(":")[0])
    end_hour = int(end_time.split(":")[0])

    slots: list[str] = []
    for hour in range(start_hour, end_hour):
        if hour < 12:
            suffix = "AM"
            display_hour = hour if hour > 0 else 12
        elif hour == 12:
            suffix = "PM"
            display_hour = 12
        else:
            suffix = "PM"
            display_hour = hour - 12
        slots.append(f"{display_hour}:00 {suffix}")
    return slots


def _parse_time_slot(slot_str: str) -> str:
    time_part, suffix = slot_str.split(" ")
    hour, minute = time_part.split(":")
    hour_int = int(hour)

    if suffix == "PM" and hour_int != 12:
        hour_int += 12
    elif suffix == "AM" and hour_int == 12:
        hour_int = 0

    return f"{hour_int:02d}:{minute}"


def _match_speciality(user_input: str, specialities: list[str]) -> str | None:
    normalized = user_input.strip().lower()
    aliases = {
        "skin": "Dermatologist",
        "ortho": "Orthopedic",
        "bone": "Orthopedic",
        "general": "General Physician",
        "physician": "General Physician",
        "child": "Pediatrician",
        "kids": "Pediatrician",
        "children": "Pediatrician",
        "ent": "ENT Specialist",
    }

    for speciality in specialities:
        if normalized == speciality.lower():
            return speciality
        if speciality.lower() in normalized or normalized in speciality.lower():
            return speciality

    for alias, speciality in aliases.items():
        if alias in normalized:
            return speciality
    return None


def _match_date(user_input: str) -> str | None:
    today, tomorrow = _today_and_tomorrow()
    normalized = user_input.strip().lower()
    if "today" in normalized or today in normalized:
        return today
    if "tomorrow" in normalized or tomorrow in normalized:
        return tomorrow
    return None


def _match_slot(user_input: str, available_slots: list[str]) -> str | None:
    normalized = user_input.strip().lower()
    for slot in available_slots:
        if normalized == slot.lower():
            return slot
        if slot.lower() in normalized:
            return slot
    return None


async def _get_specialities() -> list[str]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT speciality
            FROM clinic_doctors
            ORDER BY speciality
            """
        )
    return [row["speciality"] for row in rows]


async def _get_doctor_by_speciality(speciality: str) -> dict[str, str] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT doctor_id, doctor_name, speciality, office_timing
            FROM clinic_doctors
            WHERE LOWER(speciality) = LOWER($1)
            LIMIT 1
            """,
            speciality,
        )
    if not row:
        return None
    return {
        "doctor_id": row["doctor_id"],
        "doctor_name": row["doctor_name"],
        "speciality": row["speciality"],
        "office_timing": row["office_timing"],
    }


async def _get_booked_times(doctor_id: str, appointment_date: str) -> set[str]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT appointment_time
            FROM clinic_bookings
            WHERE doctor_id = $1
              AND appointment_date = $2
              AND status = 'Confirmed'
            """,
            doctor_id,
            _parse_appointment_date(appointment_date),
        )
    return {row["appointment_time"] for row in rows}


async def _available_slots_for(doctor_id: str, office_timing: str, appointment_date: str) -> list[str]:
    booked_times = await _get_booked_times(doctor_id, appointment_date)
    slots: list[str] = []
    for slot in _generate_time_slots(office_timing):
        if _parse_time_slot(slot) not in booked_times:
            slots.append(slot)
    return slots


async def _get_or_create_customer(name: str, phone: str) -> str:
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            """
            SELECT customer_id
            FROM clinic_customers
            WHERE phone = $1
            LIMIT 1
            """,
            phone,
        )
        if existing:
            return existing["customer_id"]

        customer_id = f"CUST-{uuid.uuid4().hex[:6].upper()}"
        await conn.execute(
            """
            INSERT INTO clinic_customers (customer_id, name, phone)
            VALUES ($1, $2, $3)
            """,
            customer_id,
            name,
            phone,
        )
        return customer_id


async def _confirm_booking(
    doctor_id: str,
    customer_name: str,
    customer_phone: str,
    time_slot: str,
    appointment_date: str,
) -> str:
    customer_id = await _get_or_create_customer(customer_name, customer_phone)
    booking_id = f"BKG-{uuid.uuid4().hex[:6].upper()}"

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO clinic_bookings
            (booking_id, doctor_id, customer_id, appointment_date, appointment_time, status)
            VALUES ($1, $2, $3, $4, $5, 'Confirmed')
            """,
            booking_id,
            doctor_id,
            customer_id,
            _parse_appointment_date(appointment_date),
            _parse_time_slot(time_slot),
        )
    return booking_id


def _create_session_state() -> dict[str, Any]:
    state = _base_state()
    _add_prompt(
        state,
        "Welcome to CarePlus Clinic. Would you like to book an appointment?",
        ["Book Appointment"],
    )
    return state


async def create_session(user_id: str) -> tuple[str, dict[str, Any]]:
    session_id = f"{user_id}:{uuid.uuid4().hex}"
    state = _create_session_state()
    CLINIC_SESSIONS[session_id] = state
    return session_id, state


async def get_session(user_id: str, session_id: str | None) -> tuple[str, dict[str, Any]]:
    if session_id:
        state = CLINIC_SESSIONS.get(session_id)
        if state is not None and session_id.startswith(f"{user_id}:"):
            return session_id, state
    return await create_session(user_id)


async def process_message(user_id: str, session_id: str | None, message: str) -> tuple[str, dict[str, Any]]:
    session_id, state = await get_session(user_id, session_id)
    text = message.strip()
    if not text:
        return session_id, state

    state["messages"].append(_user(text))
    lowered = text.lower()

    if state["stage"] == "greeting":
        if "book" in lowered or "appointment" in lowered or lowered == "hi":
            state["stage"] = "select_speciality"
            _add_prompt(state, "Please choose a speciality:", await _get_specialities())
        else:
            _add_prompt(
                state,
                "I can help you book a clinic appointment. Tap Book Appointment to get started.",
                ["Book Appointment"],
            )
        return session_id, state

    if state["stage"] == "select_speciality":
        specialities = await _get_specialities()
        speciality = _match_speciality(text, specialities)
        if not speciality:
            _add_prompt(
                state,
                "I didn't recognize that speciality. Please choose one from the list.",
                specialities,
            )
            return session_id, state

        doctor = await _get_doctor_by_speciality(speciality)
        if not doctor:
            _add_prompt(state, "No doctor is available for that speciality right now.", specialities)
            return session_id, state

        state["selected_speciality"] = speciality
        state["selected_doctor"] = doctor
        state["stage"] = "select_date"
        today, tomorrow = _today_and_tomorrow()
        _add_prompt(
            state,
            (
                f"You selected {doctor['doctor_name']} ({doctor['speciality']}). "
                f"Choose a date: Today ({today}) or Tomorrow ({tomorrow})."
            ),
            ["Today", "Tomorrow"],
        )
        return session_id, state

    if state["stage"] == "select_date":
        selected_date = _match_date(text)
        if not selected_date:
            _add_prompt(state, "Please choose Today or Tomorrow.", ["Today", "Tomorrow"])
            return session_id, state

        doctor = state["selected_doctor"]
        available_slots = await _available_slots_for(
            doctor["doctor_id"],
            doctor["office_timing"],
            selected_date,
        )
        state["selected_date"] = selected_date
        state["stage"] = "select_slot"
        if not available_slots:
            _add_prompt(
                state,
                "No slots are available for that date. Please choose another date.",
                ["Today", "Tomorrow"],
            )
            state["stage"] = "select_date"
            return session_id, state

        _add_prompt(state, "Please choose an available time slot:", available_slots)
        return session_id, state

    if state["stage"] == "select_slot":
        doctor = state["selected_doctor"]
        selected_date = state["selected_date"]
        available_slots = await _available_slots_for(
            doctor["doctor_id"],
            doctor["office_timing"],
            selected_date,
        )
        slot = _match_slot(text, available_slots)
        if not slot:
            _add_prompt(state, "Please pick one of the available slots.", available_slots)
            return session_id, state

        state["selected_slot"] = slot
        state["stage"] = "confirm"
        _add_prompt(
            state,
            (
                "Review your appointment:\n\n"
                f"Doctor: {doctor['doctor_name']}\n"
                f"Speciality: {doctor['speciality']}\n"
                f"Date: {selected_date}\n"
                f"Time: {slot}\n\n"
                "Would you like to confirm?"
            ),
            ["Confirm", "Change Slot", "Cancel"],
        )
        return session_id, state

    if state["stage"] == "confirm":
        if "change" in lowered:
            state["stage"] = "select_slot"
            doctor = state["selected_doctor"]
            available_slots = await _available_slots_for(
                doctor["doctor_id"],
                doctor["office_timing"],
                state["selected_date"],
            )
            _add_prompt(state, "Choose another slot:", available_slots)
            return session_id, state

        if "cancel" in lowered or lowered in {"no", "stop"}:
            state["stage"] = "cancelled"
            _add_prompt(state, "Booking cancelled. Start again anytime.", ["Book Appointment"])
            return session_id, state

        if "confirm" in lowered or lowered in {"yes", "okay", "ok"}:
            state["stage"] = "collect_name"
            _add_prompt(state, "Please enter your full name:")
            return session_id, state

        _add_prompt(state, "Please choose Confirm, Change Slot, or Cancel.", ["Confirm", "Change Slot", "Cancel"])
        return session_id, state

    if state["stage"] == "collect_name":
        state["customer_name"] = text
        state["stage"] = "collect_phone"
        _add_prompt(state, "Please enter your phone number:")
        return session_id, state

    if state["stage"] == "collect_phone":
        state["customer_phone"] = text
        try:
            booking_id = await _confirm_booking(
                doctor_id=state["selected_doctor"]["doctor_id"],
                customer_name=state["customer_name"],
                customer_phone=state["customer_phone"],
                time_slot=state["selected_slot"],
                appointment_date=state["selected_date"],
            )
        except Exception:
            doctor = state["selected_doctor"]
            state["stage"] = "select_slot"
            available_slots = await _available_slots_for(
                doctor["doctor_id"],
                doctor["office_timing"],
                state["selected_date"],
            )
            _add_prompt(
                state,
                "That slot is no longer available. Please choose another one.",
                available_slots,
            )
            return session_id, state

        state["booking_id"] = booking_id
        state["stage"] = "completed"
        _add_prompt(
            state,
            (
                "Appointment confirmed.\n\n"
                f"Booking ID: {booking_id}\n"
                f"Doctor: {state['selected_doctor']['doctor_name']}\n"
                f"Date: {state['selected_date']}\n"
                f"Time: {state['selected_slot']}"
            ),
            ["Book Another Appointment"],
        )
        return session_id, state

    if state["stage"] in {"completed", "cancelled"}:
        state.clear()
        state.update(_create_session_state())
        return await process_message(user_id, session_id, text)

    return session_id, state
