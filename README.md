# MIBICI - Bike-Sharing REST API

REST API para el sistema de bicicletas compartidas de Guadalajara con busqueda espacial, disponibilidad en tiempo real, y seguridad de concurrencia. Construido para 10,000 estaciones y 1,000,000 MAU.

## Indice

1. **[Documentacion de Arquitectura](docs/arquitectura.md)** — Diagrama, decisiones tecnicas (PostGIS, advisory locks, monolito, FastAPI async), alternativas consideradas, tech stack
2. **[Instrucciones de Setup](docs/setup.md)** — Como ejecutar con Docker, endpoints de la API, ejemplos de uso
3. **[Pruebas y Escalabilidad](docs/tests.md)** — 11 tests automatizados (race conditions, estres espacial, integracion), resultados, como escala el sistema
4. **[Evidencia de IA](docs/Evidencia-IA.md)** — Sesion de diseno con [GStack](https://github.com/garrytan/gstack) (Garry Tan, CEO de Y Combinator), debate de alternativas, documento de diseno aprobado
5. **[Reporte de Uso de IA](docs/ai-report.md)** — Sugerencia rechazada, alucinacion corregida, prompt mas interesante

## Quick Start

```bash
git clone https://github.com/array101/mibici.git
cd mibici
docker compose up -d --build --wait
```

Eso es todo. Las migraciones y el seed de datos (10,000 estaciones) corren automaticamente al iniciar el contenedor.

| Servicio | URL |
|----------|-----|
| API REST | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| Mapa frontend | http://localhost:3000 |
