from typing import Mapping, Any, List, Tuple, Dict, Optional, Set

Row = Mapping[str, Any]
SeatIndex = Dict[int, Dict[int, Dict[str, int]]]  # seat_type_id -> row -> col -> seat_id


# ---------- Helpers (antes internos del service) ----------

def adjacent_pairs(airplane_id: int) -> Set[Tuple[str, str]]:
    """
    Pares (col1, col2) adyacentes en la MISMA banda (sin cruzar pasillo).
    Avión 1: A,B,C | E,F,G
    Avión 2: A,B,C | D,E,F | G,H,I
    """
    if airplane_id == 1:
        blocks = [["A", "B", "C"], ["E", "F", "G"]]
    else:
        blocks = [["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]]

    pairs: Set[Tuple[str, str]] = set()
    for block in blocks:
        for a, b in zip(block, block[1:]):
            pairs.add((a, b))
            pairs.add((b, a))
    return pairs


def index_seats(seats: List[Row]) -> SeatIndex:
    """Indexa por seat_type_id -> seat_row -> seat_column -> seat_id."""
    idx: SeatIndex = {}
    for s in seats:
        st, r, c = s["seat_type_id"], s["seat_row"], s["seat_column"]
        idx.setdefault(st, {}).setdefault(r, {})[c] = s["seat_id"]
    return idx


def column_blocks(airplane_id: int) -> List[List[str]]:
    """Bloques de columnas para no cruzar pasillo."""
    if airplane_id == 1:
        return [["A", "B", "C"], ["E", "F", "G"]]
    return [["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]]


def free_runs_in_block(
    cols_map: Dict[str, int],   # col -> seat_id en esa fila
    block: List[str],           # p.ej. ["A","B","C"]
    occupied: Set[int],         # seat_ids ocupados
) -> List[List[Tuple[str, int]]]:
    """Secuencias contiguas libres dentro de un bloque (sin cruzar pasillo)."""
    runs: List[List[Tuple[str, int]]] = []
    run: List[Tuple[str, int]] = []
    for col in block:
        sid = cols_map.get(col)
        if sid is not None and sid not in occupied:
            run.append((col, sid))
        else:
            if run:
                runs.append(run)
                run = []
    if run:
        runs.append(run)
    return runs


def assign_minors_next_to_adults(
    rows: List[Dict[str, Any]],
    seat_idx: SeatIndex,
    occupied: Set[int],
    airplane_id: int,
) -> None:
    """
    Asigna seat_id (solo a quienes tienen None) para que cada menor (<18) quede
    adyacente (misma fila) a un adulto de SU compra y MISMA clase (seat_type_id).
    No reubica asientos ya asignados.
    """
    adj = adjacent_pairs(airplane_id)

    # seat_id -> (row, col) (lookup inverso)
    seat_lookup: Dict[int, Tuple[int, str]] = {}
    for _st, rows_map in seat_idx.items():
        for rownum, cols_map in rows_map.items():
            for col, sid in cols_map.items():
                seat_lookup[sid] = (rownum, col)

    # Agrupar por compra
    by_purchase: Dict[int, List[Dict[str, Any]]] = {}
    for r in rows:
        by_purchase.setdefault(r["purchase_id"], []).append(r)

    for pax in by_purchase.values():
        # Respetar la clase
        by_class: Dict[int, List[Dict[str, Any]]] = {}
        for r in pax:
            by_class.setdefault(r["seat_type_id"], []).append(r)

        for seat_type, group in by_class.items():
            minors = [g for g in group if g.get("age") is not None and g["age"] < 18]
            adults = [g for g in group if g.get("age") is not None and g["age"] >= 18]
            if not minors or not adults:
                continue

            # Adultos ya sentados (clave: (fila, col))
            adults_assigned: Dict[Tuple[int, str], Dict[str, Any]] = {}
            for a in adults:
                sid = a.get("seat_id")
                if sid is None:
                    continue
                rc = seat_lookup.get(sid)
                if rc:
                    adults_assigned[rc] = a

            # 1) Menores sin asiento: pegarlos a un adulto ya sentado
            for m in (x for x in minors if x.get("seat_id") is None):
                placed = False
                for (rownum, acol), _adult in adults_assigned.items():
                    row_map = seat_idx.get(seat_type, {}).get(rownum, {})
                    for bcol, candidate_sid in row_map.items():
                        if (acol, bcol) not in adj:
                            continue
                        if candidate_sid not in occupied:
                            m["seat_id"] = candidate_sid
                            occupied.add(candidate_sid)
                            placed = True
                            break
                    if placed:
                        break
                if placed:
                    continue

                # 2) Si no hay adulto "pegable", formar pareja menor+adulto sin asiento
                free_adult = next((a for a in adults if a.get("seat_id") is None), None)
                if not free_adult:
                    continue

                class_rows = seat_idx.get(seat_type, {})
                for rownum, cols_map in class_rows.items():
                    # columnas libres en esa fila
                    free_cols = [(col, sid) for col, sid in cols_map.items() if sid not in occupied]
                    if len(free_cols) < 2:
                        continue

                    free_cols.sort(key=lambda x: x[0])
                    pair_sid: Optional[Tuple[int, int]] = None
                    for i in range(len(free_cols) - 1):
                        c1, sid1 = free_cols[i]
                        c2, sid2 = free_cols[i + 1]
                        if (c1, c2) in adj:
                            pair_sid = (sid1, sid2)
                            break

                    if pair_sid:
                        sid_a, sid_m = pair_sid
                        free_adult["seat_id"] = sid_a
                        m["seat_id"] = sid_m
                        occupied.update({sid_a, sid_m})

                        # Registrar adulto ahora sentado para próximos menores
                        acol = seat_lookup.get(sid_a, (rownum, None))[1]
                        if acol is None:
                            for col, sid in cols_map.items():
                                if sid == sid_a:
                                    acol = col
                                    break
                        if acol is not None:
                            adults_assigned[(rownum, acol)] = free_adult
                        break


def assign_group_nearby(
    rows: List[Dict[str, Any]],
    seat_idx: SeatIndex,
    occupied: Set[int],
    airplane_id: int,
) -> None:
    """
    Para cada compra y clase, intenta sentar a los pasajeros SIN asiento:
    1) En una sola fila (ideal), dentro de un tramo contiguo del mismo bloque.
    2) Si no cabe, en la misma fila aunque sea dividido por bloques.
    3) Si tampoco, en pocas filas (prioriza filas con tramos contiguos largos).
    """
    blocks = column_blocks(airplane_id)

    # Agrupar por compra
    by_purchase: Dict[int, List[Dict[str, Any]]] = {}
    for r in rows:
        by_purchase.setdefault(r["purchase_id"], []).append(r)

    for pax in by_purchase.values():
        # Por clase
        by_class: Dict[int, List[Dict[str, Any]]] = {}
        for r in pax:
            by_class.setdefault(r["seat_type_id"], []).append(r)

        for seat_type, group in by_class.items():
            # Solo los que no tienen asiento (no reubicamos)
            todo: List[Dict[str, Any]] = [g for g in group if g.get("seat_id") is None]
            if not todo:
                continue

            placed_all = False
            class_rows = seat_idx.get(seat_type, {})

            # Ordena filas por cantidad de libres desc (filas “espaciosas” primero)
            candidate_rows = sorted(
                class_rows.items(),
                key=lambda item: sum(1 for sid in item[1].values() if sid not in occupied),
                reverse=True,
            )

            # A) tramo contiguo en un bloque (misma fila)
            for rownum, cols_map in candidate_rows:
                best_run: List[Tuple[str, int]] = []
                for block in blocks:
                    runs = free_runs_in_block(cols_map, block, occupied)
                    for run in runs:
                        if len(run) > len(best_run):
                            best_run = run
                if len(best_run) >= len(todo):
                    for _, sid in best_run[: len(todo)]:
                        todo[0]["seat_id"] = sid
                        occupied.add(sid)
                        todo.pop(0)
                        if not todo:
                            placed_all = True
                            break
                if placed_all:
                    break
            if placed_all:
                continue

            # B) misma fila, sumando runs (puede cruzar bloque)
            if todo:
                for rownum, cols_map in candidate_rows:
                    free_in_row = [(col, sid) for col, sid in cols_map.items() if sid not in occupied]
                    if len(free_in_row) >= len(todo):
                        runs_all: List[List[Tuple[str, int]]] = []
                        for block in blocks:
                            runs_all.extend(free_runs_in_block(cols_map, block, occupied))
                        runs_all.sort(key=len, reverse=True)

                        for run in runs_all:
                            for _, sid in run:
                                if not todo:
                                    break
                                todo[0]["seat_id"] = sid
                                occupied.add(sid)
                                todo.pop(0)
                            if not todo:
                                break

                        if todo:
                            free_in_row.sort(key=lambda x: x[0])  # por columna
                            for _, sid in free_in_row:
                                if not todo:
                                    break
                                todo[0]["seat_id"] = sid
                                occupied.add(sid)
                                todo.pop(0)

                        if not todo:
                            placed_all = True
                            break
            if placed_all:
                continue

            # C) varias filas cercanas
            if todo:
                for rownum, cols_map in candidate_rows:
                    if not todo:
                        break
                    best_run: List[Tuple[str, int]] = []
                    for block in blocks:
                        for run in free_runs_in_block(cols_map, block, occupied):
                            if len(run) > len(best_run):
                                best_run = run
                    for _, sid in best_run:
                        if not todo:
                            break
                        todo[0]["seat_id"] = sid
                        occupied.add(sid)
                        todo.pop(0)

                # Último recurso: cualquier asiento libre
                if todo:
                    for rownum, cols_map in candidate_rows:
                        if not todo:
                            break
                        free_any = [(col, sid) for col, sid in cols_map.items() if sid not in occupied]
                        free_any.sort(key=lambda x: (rownum, x[0]))
                        for _, sid in free_any:
                            if not todo:
                                break
                            todo[0]["seat_id"] = sid
                            occupied.add(sid)
                            todo.pop(0)
