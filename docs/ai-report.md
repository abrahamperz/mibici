# Reporte de Uso de IA

**Herramientas utilizadas**:
- **Claude Code** (Claude Opus) via CLI — implementacion, tests, CI/CD
- **[GStack](https://github.com/garrytan/gstack)** — para la fase de diseño use GStack con su skill `/office-hours`. GStack fue creado por Garry Tan, principal partner y CEO de Y Combinator. Debati con el diferentes soluciones de arquitectura hasta que encontre algo que me gusto. La evidencia completa de esa sesion de diseño esta en [Evidencia-IA.md](Evidencia-IA.md).

## Que sugerencia de la IA rechace y por que?

**Contexto: Analisis de concurrencia.**

Claude sugirio usar `SELECT FOR UPDATE` para controlar la concurrencia en las reservaciones. Es el enfoque estandar en SQL, pero lo rechace por tres razones:

1. **Riesgo de deadlocks**: Con `SELECT FOR UPDATE`, si dos transacciones intentan bloquear las mismas filas en diferente orden, se produce un deadlock. Con `pg_advisory_xact_lock(station_id)`, cada transaccion pide un solo lock por estacion, eliminando deadlocks por definicion.
2. **Sin logica de retry**: Con optimistic locking (otro approach que sugirio), el cliente necesita reintentar cuando falla la version. Advisory locks bloquean hasta obtener el lock, no necesitan retries.
3. **Demostrabilidad en tests**: Advisory locks son deterministicos. El test `test_last_bike_race` dispara 50 requests concurrentes y el resultado es siempre exactamente 1 exito y 49 conflictos. Con `SELECT FOR UPDATE` el resultado podria variar dependiendo del timing.

El trade-off es que advisory locks son especificos de PostgreSQL, pero para este proyecto eso es aceptable.

## Como detecte y corregi una alucinacion o error de seguridad de la IA?

**Contexto: SQL injection en el script de seed.**

Claude genero un script de seed que construia queries SQL con f-strings directos usando nombres de estaciones del CSV:

```python
# CODIGO PELIGROSO que Claude genero (rechazado)
query = f"INSERT INTO stations (name) VALUES ('{station_name}')"
```

Un nombre de estacion malicioso en el CSV (ej: `'); DROP TABLE stations; --`) ejecutaria SQL arbitrario. Lo detecte durante code review y corregi de dos formas:
1. El seed script usa `text()` de SQLAlchemy con parametros bind (`:name`) en vez de f-strings
2. Todos los endpoints de la API pasan por validacion de Pydantic y queries parametrizados de SQLAlchemy

## Cual fue el prompt mas interesante que use?

**Contexto: Diseño del test de concurrencia `search_under_mutation`.**

Durante la fase de diseño use `/office-hours` de GStack, que tiene una etapa de "Cross-Model Second Opinion": el skill lanza un sub-agente independiente (otra instancia de Claude sin contexto previo de nuestra conversacion) para obtener una perspectiva externa sobre el diseño. Esto evita el sesgo de confirmacion que tendria Claude defendiendo decisiones que el mismo me ayudo a tomar.

Ese sub-agente, leyendo el diseño en frio, propuso la idea de un "live replay engine" que reproduce viajes reales de MIBICI a 60x velocidad a partir de los datos publicos de viajes.

No lo implemente (fuera de scope), pero influyo directamente en el diseño del test `test_search_under_mutation`: 15 writes (reservaciones) y 20 reads (busquedas espaciales) ejecutandose simultaneamente. Este patron simula exactamente lo que un replay engine produciria, mezclando lecturas y escrituras concurrentes para verificar que el sistema no produce errores 500 ni conteos negativos de bicicletas.

---

**Inicio**: [README](../README.md)
