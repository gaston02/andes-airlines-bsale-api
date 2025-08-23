# app/services/flight_audit_service.py
from typing import Any, Dict, List, Mapping, Tuple, Set, DefaultDict
from collections import defaultdict

ABC = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

class FlightAuditService:
    """
    Servicio de auditoría: aplica reglas de verificación sobre un vuelo.
    - Depende de un 'flight_repo' que exponga:
        - fetch_flight_with_passengers(flight_id) -> List[Mapping]
        - fetch_seats_for_flight(flight_id) -> List[Mapping]
      (tanto el repo real como el fake tienen esas firmas)
    """

    def __init__(self, flight_repo: Any):
        self.flight_repo = flight_repo

    # ---------- API PÚBLICA ----------
    def run_checks(self, flight_id: int) -> Dict[str, Any]:
        rows = self.flight_repo.fetch_flight_with_passengers(int(flight_id))
        if not rows:
            return {"code": 404, "data": {}}

        seats = self.flight_repo.fetch_seats_for_flight(int(flight_id))
        seat_by_id, col_order = self._build_lookups(rows, seats)
        col_index = {c: i for i, c in enumerate(col_order)}

        rule1 = self._check_minors_next_to_adults(rows, seat_by_id, col_index)
        rule2 = self._check_groups_nearby(rows, seat_by_id, col_index)

        first = rows[0]
        out: Dict[str, Any] = {
            "code": 200,
            "data": {
                "flightId": first["flight_id"],
                "takeoffDateTime": first.get("takeoff_date_time"),
                "takeoffAirport": first.get("takeoff_airport"),
                "landingDateTime": first.get("landing_date_time"),
                "landingAirport": first.get("landing_airport"),
                "airplaneId": first["airplane_id"],
                "totals": {
                    "passengers": len(rows),
                    "minors": sum(1 for r in rows if r.get("age") is not None and r["age"] < 18),
                    "groups": len({r["purchase_id"] for r in rows}),
                },
                # Resultados de reglas
                "rule1_minors_next_to_adults": rule1,
                "rule2_groups_nearby": rule2,
            },
        }
        return out

    # ---------- LOOKUPS / HELPERS ----------
    def _build_lookups(
        self,
        rows: List[Mapping[str, Any]],
        seats: List[Mapping[str, Any]],
    ) -> Tuple[Dict[int, Tuple[int, str, int]], List[str]]:
        """
        seat_by_id: seat_id -> (row:int, col:str, seat_type_id:int)
        col_order: orden físico de columnas (sin letras que no existan, para no cruzar pasillos)
        """
        # seat_id -> (row, col, seat_type)
        seat_by_id: Dict[int, Tuple[int, str, int]] = {}
        for s in seats:
            seat_by_id[int(s["seat_id"])] = (
                int(s["seat_row"]),
                str(s["seat_column"]),
                int(s["seat_type_id"]),
            )

        # Derivar columnas presentes y ordenarlas según ABC (filtrando solo las existentes).
        present: List[str] = []
        seen: Set[str] = set()
        for s in seats:
            c = str(s["seat_column"])
            if c not in seen:
                seen.add(c)
                present.append(c)

        # Orden físico: respeta que si no existe 'D', la secuencia queda ABCEFG (evita cruzar pasillo).
        col_order = [c for c in ABC if c in seen]
        # Fallback: si por alguna razón no detectamos columnas, usa las que vengan en rows
        if not col_order and rows:
            seen2: Set[str] = set()
            for r in rows:
                c = str(r.get("assigned_seat_column") or "")
                if c and c not in seen2:
                    seen2.add(c)
            col_order = [c for c in ABC if c in seen2] or list("ABCDEF")
        return seat_by_id, col_order

    # ---------- REGLA 1 ----------
    def _check_minors_next_to_adults(
        self,
        rows: List[Mapping[str, Any]],
        seat_by_id: Dict[int, Tuple[int, str, int]],
        col_index: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Un menor (<18) debe tener al menos UN adulto (>=18) adyacente.
        Adyacencia = mismo tipo de asiento y:
            - misma fila y columna +/-1 (izq/der), o
            - misma columna y fila +/-1 (frente/atrás).
        """
        minors = [r for r in rows if r.get("age") is not None and r["age"] < 18]
        adults = [r for r in rows if r.get("age") is not None and r["age"] >= 18]

        def neighbors(p: Mapping[str, Any]) -> List[Mapping[str, Any]]:
            sid = int(p["seat_id"])
            if sid not in seat_by_id:
                return []
            r1, c1, t1 = seat_by_id[sid]
            ci1 = col_index.get(c1, -999)
            out: List[Mapping[str, Any]] = []
            for q in adults:
                if q is p:
                    continue
                sid2 = int(q["seat_id"])
                if sid2 not in seat_by_id:
                    continue
                r2, c2, t2 = seat_by_id[sid2]
                if t1 != t2:
                    continue  # no cruzamos cabinas / seat_type
                ci2 = col_index.get(c2, -999)
                # Adyacencia 4-neighbors (izq/der, frente/atrás)
                if r1 == r2 and abs(ci1 - ci2) == 1:
                    out.append(q)
                elif ci1 == ci2 and abs(r1 - r2) == 1:
                    out.append(q)
            return out

        failures: List[Dict[str, Any]] = []
        for m in minors:
            neigh = neighbors(m)
            if not neigh:
                failures.append(
                    {
                        "passengerId": int(m["passenger_id"]),
                        "seatId": int(m["seat_id"]),
                        "age": int(m["age"]),
                        "reason": "minor_without_adjacent_adult",
                    }
                )

        return {
            "ok": len(failures) == 0,
            "failures": failures,
            "checkedMinors": len(minors),
        }

    # ---------- REGLA 2 ----------
    def _check_groups_nearby(
        self,
        rows: List[Mapping[str, Any]],
        seat_by_id: Dict[int, Tuple[int, str, int]],
        col_index: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Grupos = mismo 'purchase_id'. Validamos que estén 'cerca'.
        Definición de 'cerca' (simple y consistente):
          - Misma cabina (seat_type_id)
          - Distancia Manhattan <= 2 entre cada par del grupo
            donde:
              d = |fila1 - fila2| + |colIdx1 - colIdx2|
        Si algún par excede, marcamos el grupo como 'spread'.
        """
        # Agrupar por purchase_id y seat_type_id (para no mezclar cabinas)
        groups: DefaultDict[Tuple[int, int], List[Mapping[str, Any]]] = defaultdict(list)
        for r in rows:
            groups[(int(r["purchase_id"]), int(r["seat_type_id"]))].append(r)

        spread_groups: List[Dict[str, Any]] = []

        for (purchase_id, seat_type_id), members in groups.items():
            if len(members) <= 1:
                continue
            bad_pairs: List[Tuple[int, int]] = []

            # Precalcular pos
            pos: Dict[int, Tuple[int, int]] = {}  # pid -> (row, colIdx)
            for m in members:
                sid = int(m["seat_id"])
                if sid not in seat_by_id:
                    continue
                r, c, t = seat_by_id[sid]
                ci = col_index.get(c, -999)
                pos[int(m["passenger_id"])] = (r, ci)

            pids = list(pos.keys())
            for i in range(len(pids)):
                for j in range(i + 1, len(pids)):
                    a, b = pids[i], pids[j]
                    r1, c1 = pos[a]
                    r2, c2 = pos[b]
                    d = abs(r1 - r2) + abs(c1 - c2)
                    if d > 2:
                        bad_pairs.append((a, b))

            if bad_pairs:
                spread_groups.append(
                    {
                        "purchaseId": purchase_id,
                        "seatTypeId": seat_type_id,
                        "members": [int(m["passenger_id"]) for m in members],
                        "tooFarPairs": [{"a": a, "b": b} for (a, b) in bad_pairs],
                    }
                )

        return {
            "ok": len(spread_groups) == 0,
            "spreadGroups": spread_groups,
            "groupsChecked": len(groups),
        }
