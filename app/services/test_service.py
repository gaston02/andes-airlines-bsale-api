# app/services/test_service.py
from typing import Any, Dict, List, Mapping, Tuple, Set
from collections import deque
from sqlalchemy.orm import Session

from app.repositories.interfaces import IFlightRepository, ISeatRepository

Row = Mapping[str, Any]


class FlightSeatingCheckService:
    """
    Servicio de VERIFICACIÓN (no asigna asientos, solo audita).
    - Regla 1: menor (<18) adyacente a un adulto de su compra y misma clase (SIN cruzar pasillo).
    - Regla 2: grupos por compra/clase "juntos o muy cercanos"
               (conectividad usando adyacencias por fila/columna).
    """

    def __init__(self, flight_repo: IFlightRepository, seat_repo: ISeatRepository) -> None:
        self.flight_repo = flight_repo
        self.seat_repo = seat_repo

    # ---------------------- API pública ----------------------

    def run_checks(self, db: Session, flight_id: int) -> Dict[str, Any]:
        rows = self.flight_repo.fetch_flight_with_passengers(db, flight_id)
        if not rows:
            return {"code": 404, "data": {}}

        seats = self.seat_repo.fetch_seats_for_flight(db, flight_id)
        seat_by_id, col_order = self._build_lookups(rows, seats)

        rule1 = self._check_minors_next_to_adults(rows, seat_by_id)
        rule2 = self._check_groups_nearby(rows, seat_by_id, col_order)

        first = rows[0]
        return {
            "code": 200,
            "data": {
                "flightId": first["flight_id"],
                "airplaneId": first["airplane_id"],
                "totals": {
                    "passengers": len(rows),
                    "minors": sum(1 for r in rows if (r.get("age") is not None and r["age"] < 18)),
                    "groups": len({(r["purchase_id"], r["seat_type_id"]) for r in rows}),
                },
                "rule1_minors_next_to_adults": rule1,
                "rule2_groups_nearby": rule2,
            },
        }

    # ---------------------- helpers: disposición ----------------------

    def _column_blocks(self, airplane_id: int) -> List[List[str]]:
        # Misma convención que en FlightService
        if airplane_id == 1:
            return [["A", "B", "C"], ["E", "F", "G"]]
        return [["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]]

    def _column_order(self, airplane_id: int) -> List[str]:
        # Secuencia lineal para medir cercanía horizontal (Regla 2)
        if airplane_id == 1:
            return ["A", "B", "C", "E", "F", "G"]
        return ["A", "B", "C", "D", "E", "F", "G", "H", "I"]

    def _adjacent_pairs_same_block(self, airplane_id: int) -> Set[Tuple[str, str]]:
        # Adyacentes horizontales SIN cruzar pasillo (Regla 1)
        pairs: Set[Tuple[str, str]] = set()
        for block in self._column_blocks(airplane_id):
            for a, b in zip(block, block[1:]):
                pairs.add((a, b))
                pairs.add((b, a))
        return pairs

    def _build_lookups(
        self,
        rows: List[Row],
        seats: List[Row],
    ) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, int]]:
        """
        seat_by_id: seat_id -> {"row": int, "col": str, "seat_type_id": int, "airplane_id": int}
        col_order:  mapa col -> índice lineal para distancia horizontal (Regla 2)
        """
        airplane_id = rows[0]["airplane_id"]
        order = self._column_order(airplane_id)
        col_order = {c: i for i, c in enumerate(order)}

        seat_by_id: Dict[int, Dict[str, Any]] = {}
        for s in seats:
            seat_by_id[s["seat_id"]] = {
                "row": s["seat_row"],
                "col": s["seat_column"],
                "seat_type_id": s["seat_type_id"],
                "airplane_id": s["airplane_id"],
            }
        return seat_by_id, col_order

    # ---------------------- Regla 1 ----------------------

    def _check_minors_next_to_adults(
        self,
        rows: List[Row],
        seat_by_id: Dict[int, Dict[str, Any]],
    ) -> Dict[str, Any]:
        airplane_id = rows[0]["airplane_id"]
        adjacent = self._adjacent_pairs_same_block(airplane_id)

        # Agrupar por compra y clase
        groups: Dict[Tuple[int, int], List[Row]] = {}
        for r in rows:
            groups.setdefault((r["purchase_id"], r["seat_type_id"]), []).append(r)

        violations: List[Dict[str, Any]] = []
        checked = 0

        for (purchase_id, seat_type_id), pax in groups.items():
            minors = [p for p in pax if (p.get("age") is not None and p["age"] < 18)]
            adults = [p for p in pax if (p.get("age") is not None and p["age"] >= 18)]
            if not minors:
                continue

            for m in minors:
                checked += 1
                sid_m = m.get("seat_id")
                if not sid_m or sid_m not in seat_by_id:
                    violations.append({
                        "purchaseId": purchase_id,
                        "seatTypeId": seat_type_id,
                        "minorPassengerId": m["passenger_id"],
                        "issue": "minor_without_seat",
                    })
                    continue

                mr = seat_by_id[sid_m]["row"]
                mc = seat_by_id[sid_m]["col"]

                ok = False
                for a in adults:
                    sid_a = a.get("seat_id")
                    if not sid_a or sid_a not in seat_by_id:
                        continue
                    ar = seat_by_id[sid_a]["row"]
                    ac = seat_by_id[sid_a]["col"]
                    if ar == mr and (ac, mc) in adjacent:
                        ok = True
                        break

                if not ok:
                    violations.append({
                        "purchaseId": purchase_id,
                        "seatTypeId": seat_type_id,
                        "minorPassengerId": m["passenger_id"],
                        "issue": "no_adjacent_adult_same_block",
                        "minorSeat": {"row": mr, "col": mc},
                    })

        return {
            "checkedMinors": checked,
            "passed": len(violations) == 0,
            "violations": violations,
        }

    # ---------------------- Regla 2 ----------------------

    def _check_groups_nearby(
        self,
        rows: List[Row],
        seat_by_id: Dict[int, Dict[str, Any]],
        col_order: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Para cada (purchase_id, seat_type_id) construimos un grafo donde hay arista si:
          - MISMA FILA y |Δcol_index| == 1 (horizontales adyacentes; aquí sí puede cruzar pasillo)
          - MISMA COLUMNA y |Δfila| == 1 (verticales adyacentes).
        Si todo el grupo asignado está en un solo componente, consideramos "nearby".
        """
        groups: Dict[Tuple[int, int], List[Row]] = {}
        for r in rows:
            groups.setdefault((r["purchase_id"], r["seat_type_id"]), []).append(r)

        results: List[Dict[str, Any]] = []

        for (purchase_id, seat_type_id), pax in groups.items():
            assigned = [p for p in pax if (p.get("seat_id") in seat_by_id)]
            missing = [p for p in pax if (p.get("seat_id") not in seat_by_id)]

            # Sin asignados => no hay nada que “conectar”
            if not assigned:
                results.append({
                    "purchaseId": purchase_id,
                    "seatTypeId": seat_type_id,
                    "groupSize": len(pax),
                    "assigned": 0,
                    "unassigned": [p["passenger_id"] for p in missing],
                    "components": [],
                    "componentCount": 0,
                    "nearbyConnected": False,
                    "rowsSpan": 0,
                    "colsSpan": 0,
                    "rowsUsed": [],
                    "colsUsed": [],
                })
                continue

            # passenger -> (row, colIdx, colLetter)
            nodes: Dict[int, Tuple[int, int, str]] = {}
            for p in assigned:
                info = seat_by_id[p["seat_id"]]
                r = info["row"]
                c = info["col"]
                nodes[p["passenger_id"]] = (r, col_order[c], c)

            # Grafo sin aristas a sí mismo
            edges: Dict[int, Set[int]] = {pid: set() for pid in nodes}
            ids = list(nodes.keys())
            for i in range(len(ids)):
                pid1 = ids[i]
                r1, ci1, c1 = nodes[pid1]
                for j in range(i + 1, len(ids)):
                    pid2 = ids[j]
                    r2, ci2, c2 = nodes[pid2]
                    # Horizontal adyacente
                    if r1 == r2 and abs(ci1 - ci2) == 1:
                        edges[pid1].add(pid2)
                        edges[pid2].add(pid1)
                    # Vertical adyacente
                    if c1 == c2 and abs(r1 - r2) == 1:
                        edges[pid1].add(pid2)
                        edges[pid2].add(pid1)

            # Componentes conectados (BFS)
            visited: Set[int] = set()
            components: List[Set[int]] = []
            for start in edges:
                if start in visited:
                    continue
                comp: Set[int] = set()
                q: deque[int] = deque([start])
                while q:
                    u = q.popleft()
                    if u in visited:
                        continue
                    visited.add(u)
                    comp.add(u)
                    # Solo encolamos los que no estén visitados aún
                    for v in edges[u]:
                        if v not in visited:
                            q.append(v)
                components.append(comp)

            # Métricas
            rows_used = sorted({nodes[pid][0] for pid in nodes})
            cols_used_letters = sorted({nodes[pid][2] for pid in nodes}, key=lambda x: col_order[x])
            row_span = (rows_used[-1] - rows_used[0] + 1) if rows_used else 0
            col_span = (col_order[cols_used_letters[-1]] - col_order[cols_used_letters[0]] + 1) if cols_used_letters else 0

            results.append({
                "purchaseId": purchase_id,
                "seatTypeId": seat_type_id,
                "groupSize": len(pax),
                "assigned": len(assigned),
                "unassigned": [p["passenger_id"] for p in missing],
                "components": [sorted(list(c)) for c in components],
                "componentCount": len(components),
                "nearbyConnected": (len(components) == 1),
                "rowsSpan": row_span,
                "colsSpan": col_span,
                "rowsUsed": rows_used,
                "colsUsed": cols_used_letters,
            })

        return {
            "groups": results,
            "passed": all(g["nearbyConnected"] for g in results if g["assigned"] > 1),
        }
