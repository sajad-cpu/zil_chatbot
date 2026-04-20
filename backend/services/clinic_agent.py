"""Native clinic-agent flow for the main FastAPI backend."""

from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import datetime, timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

CLINIC_PROJECT_ROOT = (
    Path(__file__).resolve().parents[2] / "agentic-ai-usecases" / "medium" / "clinic-agent"
)
if str(CLINIC_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(CLINIC_PROJECT_ROOT))


def _load_module(module_name: str, file_path: Path):
    spec = spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module: {file_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


clinic_db = _load_module("clinic_data_db", CLINIC_PROJECT_ROOT / "data" / "db.py")
clinic_doctor_service = _load_module(
    "clinic_doctor_service",
    CLINIC_PROJECT_ROOT / "services" / "doctor_service.py",
)

create_booking = clinic_db.create_booking
create_customer = clinic_db.create_customer
get_bookings_by_doctor_and_date = clinic_db.get_bookings_by_doctor_and_date
get_customer_by_phone = clinic_db.get_customer_by_phone
init_db = clinic_db.init_db
generate_time_slots = clinic_doctor_service.generate_time_slots
get_doctor_info = clinic_doctor_service.get_doctor_info
get_specialities_list = clinic_doctor_service.get_specialities_list
parse_time_slot = clinic_doctor_service.parse_time_slot

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


def _today_and_tomorrow() -> tuple[str, str]:
    today_dt = datetime.now()
    tomorrow_dt = today_dt + timedelta(days=1)
    return today_dt.strftime("%Y-%m-%d"), tomorrow_dt.strftime("%Y-%m-%d")


def _add_prompt(state: dict[str, Any], content: str, options: list[str] | None = None) -> None:
    if state["messages"] and state["messages"][-1]["role"] == "assistant":
        last = state["messages"][-1]
        if last.get("content") == content and last.get("options", []) == (options or []):
            state["available_options"] = options or []
            return
    state["messages"].append(_assistant(content, options))
    state["available_options"] = options or []


def _match_speciality(user_input: str) -> str | None:
    specialities = get_specialities_list()
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


def _available_slots_for(doctor_id: str, office_timing: str, appointment_date: str) -> list[str]:
    booked_times = set(get_bookings_by_doctor_and_date(doctor_id, appointment_date))
    slots = []
    for slot in generate_time_slots(office_timing):
        if parse_time_slot(slot) not in booked_times:
            slots.append(slot)
    return slots


def _get_or_create_customer(name: str, phone: str) -> str:
    customer = get_customer_by_phone(phone)
    if customer:
        return customer[0]

    customer_id = f"CUST-{uuid.uuid4().hex[:6].upper()}"
    create_customer(customer_id, name, phone)
    return customer_id


def _confirm_booking(
    doctor_id: str,
    customer_name: str,
    customer_phone: str,
    time_slot: str,
    appointment_date: str,
) -> str:
    customer_id = _get_or_create_customer(customer_name, customer_phone)
    booking_id = f"BKG-{uuid.uuid4().hex[:6].upper()}"
    create_booking(
        booking_id,
        doctor_id,
        customer_id,
        appointment_date,
        parse_time_slot(time_slot),
        "Confirmed",
    )
    return booking_id


def _match_slot(user_input: str, available_slots: list[str]) -> str | None:
    normalized = user_input.strip().lower()
    for slot in available_slots:
        if normalized == slot.lower():
            return slot
        if slot.lower() in normalized:
            return slot
    return None


def _create_session_state() -> dict[str, Any]:
    init_db()
    state = _base_state()
    _add_prompt(
        state,
        "Welcome to CarePlus Clinic. Would you like to book an appointment?",
        ["Book Appointment"],
    )
    return state


def create_session(user_id: str) -> tuple[str, dict[str, Any]]:
    session_id = f"{user_id}:{uuid.uuid4().hex}"
    state = _create_session_state()
    CLINIC_SESSIONS[session_id] = state
    return session_id, state


def get_session(user_id: str, session_id: str | None) -> tuple[str, dict[str, Any]]:
    if session_id:
        state = CLINIC_SESSIONS.get(session_id)
        if state is not None and session_id.startswith(f"{user_id}:"):
            return session_id, state
    return create_session(user_id)


def process_message(user_id: str, session_id: str | None, message: str) -> tuple[str, dict[str, Any]]:
    session_id, state = get_session(user_id, session_id)
    text = message.strip()
    if not text:
        return session_id, state

    state["messages"].append(_user(text))
    lowered = text.lower()

    if state["stage"] == "greeting":
        if "book" in lowered or "appointment" in lowered or lowered == "hi":
            state["stage"] = "select_speciality"
            _add_prompt(state, "Please choose a speciality:", get_specialities_list())
        else:
            _add_prompt(
                state,
                "I can help you book a clinic appointment. Tap Book Appointment to get started.",
                ["Book Appointment"],
            )
        return session_id, state

    if state["stage"] == "select_speciality":
        speciality = _match_speciality(text)
        if not speciality:
            _add_prompt(
                state,
                "I didn't recognize that speciality. Please choose one from the list.",
                get_specialities_list(),
            )
            return session_id, state

        doctor = get_doctor_info(speciality)
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
        available_slots = _available_slots_for(
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
        available_slots = _available_slots_for(
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
            available_slots = _available_slots_for(
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
            booking_id = _confirm_booking(
                doctor_id=state["selected_doctor"]["doctor_id"],
                customer_name=state["customer_name"],
                customer_phone=state["customer_phone"],
                time_slot=state["selected_slot"],
                appointment_date=state["selected_date"],
            )
        except sqlite3.IntegrityError:
            state["stage"] = "select_slot"
            doctor = state["selected_doctor"]
            available_slots = _available_slots_for(
                doctor["doctor_id"],
                doctor["office_timing"],
                state["selected_date"],
            )
            _add_prompt(
                state,
                "That slot was just booked by someone else. Please choose another slot.",
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
        return process_message(user_id, session_id, text)

    return session_id, state
