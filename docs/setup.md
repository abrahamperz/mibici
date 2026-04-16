# Instrucciones de Setup

**Prerequisitos**: Docker (incluye Docker Compose). Node.js no es necesario, todo corre dentro de contenedores.

## 1. Clonar y levantar

```bash
git clone https://github.com/abrahamperz/mibici.git
cd mibici
docker compose up -d --build --wait
```

Eso es todo. Al iniciar, el contenedor `api` automaticamente:
1. Ejecuta las migraciones de base de datos (crea tablas `stations` y `reservations` con indice espacial GiST)
2. Descarga 383 estaciones reales de MIBICI desde mibici.net y genera 9,617 sinteticas para alcanzar 10,000 totales
3. Inicia el servidor FastAPI

No se necesita crear ningun `.env`. Docker Compose usa `backend/.env.example` directamente con los valores por defecto para desarrollo.

## 2. Correr tests (opcional)

```bash
# Requiere act: https://github.com/nektos/act
# Instalacion: brew install act (macOS) o https://nektosact.com/installation
act push
```

## URLs

| Servicio | URL |
|----------|-----|
| API REST | http://localhost:8000 |
| Documentacion Swagger (OpenAPI) | http://localhost:8000/docs |
| Mapa frontend (Leaflet.js) | http://localhost:3000 |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/stations/nearest?lon=&lat=&k=5&radius_m=` | KNN spatial search |
| `GET` | `/stations/{id}` | Station details + availability |
| `POST` | `/stations` | Create station |
| `DELETE` | `/stations/{id}` | Remove station |
| `POST` | `/stations/{id}/reserve` | Reserve a bike |
| `POST` | `/stations/{id}/return` | Return a bike |
| `GET` | `/health` | Health check |

### Ejemplos

```bash
# Encontrar las 5 estaciones mas cercanas al centro de Guadalajara
curl "http://localhost:8000/stations/nearest?lon=-103.35&lat=20.67&k=5"

# Reservar una bicicleta
curl -X POST "http://localhost:8000/stations/1/reserve"

# Devolver una bicicleta
curl -X POST "http://localhost:8000/stations/1/return"
```

## Apagar todo

```bash
docker compose down -v   # -v elimina el volumen de PostgreSQL
```

---

**Siguiente**: [Pruebas y Escalabilidad](tests.md)
