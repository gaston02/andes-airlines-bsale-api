# app/repositories/fake_flight_repo.py
from typing import Any, Dict, List, Mapping, Tuple

# Intentamos soportar ambos nombres, por si tu fixture quedó como EXCEPTED o EXPECTED
try:
    from app.fixtures.excepted_payload import EXPECTED as _PAYLOADS
except Exception:
    from app.fixtures.excepted_payload import EXCEPTED as _PAYLOADS  # type: ignore

# --- Layouts por avión (con pasillos implícitos) ---
# Avión 1: [A,B,C] | [E,F,G]  -> "ABCEFG"  (la D es pasillo)
# Avión 2: [A,B,C] | [D,E,F] | [G,H,I] -> "ABCDEFGHI"
LAYOUTS: Dict[int, str] = {
    1: "ABCEFG",
    2: "ABCDEFGHI",
}

DEFAULT_COLUMNS = "ABCDEF"  # fallback seguro


def _columns_for_airplane(airplane_id: int) -> str:
    return LAYOUTS.get(int(airplane_id), DEFAULT_COLUMNS)


def _seat_pos(seat_id: int, airplane_id: int) -> Tuple[int, str]:
    """
    Mapeo determinista SOLO para modo fake:
    fila = (seat_id-1) // num_cols + 1
    col  = columnas[(seat_id-1) % num_cols]

    Nota: si el layout omite letras de pasillo (p.ej. sin 'D'), no genera vecinos
    falsos a través del pasillo (C no es vecino de E).
    """
    cols = _columns_for_airplane(airplane_id)
    ncols = len(cols)
    row = ((int(seat_id) - 1) // ncols) + 1
    col = cols[(int(seat_id) - 1) % ncols]
    return row, col


class FakeFlightRepo:
    """
    Repo 'fake' que construye filas equivalentes a la query SQL a partir de los JSON
    de EXPECTED/EXCEPTED. No usa DB.

    Métodos:
      - fetch_flight_with_passengers(flight_id) -> rows con campos como tu SELECT
      - fetch_seats_for_flight(flight_id)      -> inventario mínimo de asientos
    """

    def fetch_flight_with_passengers(self, flight_id: int) -> List[Mapping[str, Any]]:
        if int(flight_id) not in _PAYLOADS:
            return []

        payload = _PAYLOADS[int(flight_id)]["data"]
        rows: List[Dict[str, Any]] = []

        airplane_id = int(payload["airplaneId"])
        for p in payload["passengers"]:
            seat_id = int(p["seatId"])
            r, c = _seat_pos(seat_id, airplane_id)

            rows.append(
                {
                    # Campos del vuelo
                    "flight_id": int(payload["flightId"]),
                    "takeoff_date_time": payload["takeoffDateTime"],
                    "landing_date_time": payload["landingDateTime"],
                    "takeoff_airport": payload["takeoffAirport"],
                    "landing_airport": payload["landingAirport"],
                    "airplane_id": airplane_id,
                    # Pasajero
                    "passenger_id": int(p["passengerId"]),
                    "dni": p["dni"],
                    "name": p["name"],
                    "age": p["age"],
                    "country": p["country"],
                    # Boarding pass
                    "boarding_pass_id": int(p["boardingPassId"]),
                    "purchase_id": int(p["purchaseId"]),
                    "seat_type_id": int(p["seatTypeId"]),
                    "seat_id": seat_id,
                    # Posición “fake” para reglas de proximidad
                    "assigned_seat_row": r,
                    "assigned_seat_column": c,
                }
            )

        # Orden similar a tu ORDER BY (aprox)
        rows.sort(key=lambda x: (x["purchase_id"], x["passenger_id"]))
        return rows

    def fetch_seats_for_flight(self, flight_id: int) -> List[Mapping[str, Any]]:
        if int(flight_id) not in _PAYLOADS:
            return []

        payload = _PAYLOADS[int(flight_id)]["data"]
        airplane_id = int(payload["airplaneId"])

        # Inventario mínimo a partir de los seats usados en el payload
        seen: Dict[int, int] = {}  # seat_id -> seat_type_id
        for p in payload["passengers"]:
            seen[int(p["seatId"])] = int(p["seatTypeId"])

        seats: List[Dict[str, Any]] = []
        for seat_id, seat_type_id in sorted(seen.items()):
            r, c = _seat_pos(seat_id, airplane_id)
            seats.append(
                {
                    "seat_id": seat_id,
                    "seat_column": c,
                    "seat_row": r,
                    "seat_type_id": seat_type_id,
                    "airplane_id": airplane_id,
                }
            )
        return seats
