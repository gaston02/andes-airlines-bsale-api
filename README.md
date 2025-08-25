Andes Airlines API

API de lectura para listar los pasajeros de un vuelo y reconstruir en memoria la asignación de asientos cumpliendo reglas de negocio.
Pensada para una prueba técnica: se expone un único endpoint funcional y documentación automática vía Swagger.

Arquitectura

FastAPI para el HTTP layer y la documentación automática OpenAPI.

SQLAlchemy para acceso a datos (solo lectura).

Capa de servicios con reglas de asignación de asientos en memoria (no se hacen UPDATE sobre la BD).

Repositorios que abstraen el origen de datos: FlightRepository y SeatRepository.

Esquemas Pydantic para serializar la respuesta final.
