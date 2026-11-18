# Asistente del Sueño

Aplicación web en español con FastAPI, autenticación, PostgreSQL y un asistente RAG que consulta `app/data/documento_sueno.pdf`. La interfaz y la API se sirven desde el mismo contenedor, por lo que `docker compose up --build` despliega ambas.

## Puesta en marcha

1. Define `GEMINI_API_KEY` en el entorno o en un archivo `.env` local (no lo subas al repositorio).
2. Desde la raíz del proyecto:

   ```sh
   docker compose up --build
   ```

3. Abre <http://localhost:8000>. La API está en `/api/v1` y su estado en `/api/v1/health`.

El frontend es parte de la imagen `web`; no requiere un servidor de desarrollo ni dependencias JavaScript externas. PostgreSQL conserva usuarios y sus datos. Los eventos de métricas descritos abajo se mantienen en memoria y se reinician al recrear el proceso.

## Perfil, seguimiento y recompensas

Al iniciar sesión, cada usuario puede guardar un nombre para mostrar, un rango de edad, un objetivo de horas y su zona horaria. El registro diario recoge fecha, duración, calidad percibida y despertares. Los datos se guardan por usuario en tablas separadas y las rutas de perfil, progreso y PDF requieren el token Bearer que devuelve el login (dura 12 horas).

La gamificación premia el hábito de registrar: 10 puntos por noche única, una insignia por el primer registro, otra por una racha de siete noches y otra al llegar a 30 noches. No se dan puntos por dormir más ni por una puntuación de calidad concreta. El panel dibuja duración y calidad de las últimas 14 noches; el PDF descargable contiene el perfil, el historial, un gráfico de las últimas 14 noches y las recompensas.

| Ruta | Uso |
| --- | --- |
| `PUT /api/v1/profile` / `GET /api/v1/profile` | Crear o consultar el perfil del usuario autenticado. |
| `POST /api/v1/sleep-logs` | Añadir un registro diario (una noche por fecha y cuenta). |
| `GET /api/v1/progress` | Consultar historial, gráfico y estado de gamificación. |
| `GET /api/v1/reports/progress.pdf` | Descargar el informe PDF del usuario autenticado. |

`JWT_SECRET_KEY` firma sesiones; en Docker Compose tiene una clave local de desarrollo predeterminada. En producción, Render genera una clave propia mediante el Blueprint. No compartas ni reutilices esa clave entre entornos.

## Recuperación y umbral de confianza

El PDF se separa en fragmentos y se puntúa con similitud coseno TF-IDF local. Para cada pregunta se envían a Gemini como máximo los dos fragmentos más relevantes, no el documento completo. Si la mejor similitud no alcanza el umbral, la API devuelve una respuesta de rechazo y no llama al modelo. Las peticiones de contar hasta un millón también se rechazan directamente.

Configura estos parámetros antes de iniciar el servicio:

| Variable | Predeterminado | Significado |
| --- | ---: | --- |
| `RAG_CONFIDENCE_THRESHOLD` | `0.10` | Similitud coseno mínima, expresada como decimal entre 0 y 1 (10 % por defecto). |
| `RAG_TOP_K` | `2` | Máximo de fragmentos que se pasan al modelo. |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Identificador del modelo de Gemini. |
| `SLEEP_GUIDE_PDF` | `app/data/documento_sueno.pdf` | Ruta al documento de referencia. |

El porcentaje que devuelve la API es similitud léxica de recuperación, **no** una probabilidad de que la respuesta sea cierta. Un umbral bajo amplía cobertura, pero puede recuperar contexto débil; uno alto reduce respuestas con contexto dudoso, pero aumenta los rechazos correctos. Valida cualquier cambio en el golden dataset antes de desplegarlo.

## Golden dataset y evaluación

`data/golden_dataset.csv` contiene preguntas con comportamiento y respuesta esperados: tanto consultas cubiertas por el documento como consultas ajenas al dominio. Ejecuta:

```sh
python scripts/evaluate_golden_dataset.py
```

También se puede probar otro umbral sin modificar el entorno:

```sh
python scripts/evaluate_golden_dataset.py --threshold 0.12
```

El evaluador informa matriz de confusión, precisión/recall de aceptación, tasa de preguntas fuera de dominio aceptadas por error y exactitud de la decisión de recuperar o rechazar. El comando falla si una pregunta se acepta/rechaza de forma distinta a la esperada. `respuesta_esperada` sirve para revisión humana de la generación; no se compara como texto literal porque las respuestas de Gemini pueden variar. Añade casos al CSV cuando cambie el documento o el alcance del producto y revisa respuestas con una persona antes de ajustar el umbral.

## Trazas y métricas

Cada consulta lleva un `trace_id`. Los logs estructurados de `rag_retrieval` y `rag_generation` registran identificador de conversación, similitud, umbral, fragmentos seleccionados y latencias de recuperación/generación; no registran las preguntas, respuestas, correos ni contraseñas. La respuesta del chat también muestra similitud, páginas de origen, fragmentos, latencia y referencia de traza.

`GET /api/v1/metrics` presenta agregados de una ventana circular de hasta 5.000 consultas:

| Tipo | Métrica | Definición y uso |
| --- | --- | --- |
| Funcional | Consultas con contexto / rechazos | Conteo de recuperaciones que superan el umbral y rechazos por falta de evidencia. Vigila cambios al actualizar la guía o el umbral. |
| Funcional | Turnos medios por conversación | Total de consultas dividido entre conversaciones identificadas por `conversation_id`. Sirve para detectar conversaciones que no llegan a una respuesta útil. |
| Técnica | Latencia media por etapa | Milisegundos de recuperación, generación y petición completa. Aísla si el cuello de botella está en el RAG o en Gemini. |
| Técnica | Latencia total p95 | Percentil 95 de latencia de las últimas consultas; úsalo como objetivo de servicio acordado, no como una garantía actual. |
| Técnica | Errores | Fallos de generación registrados. Contrástalos con logs por `trace_id`. |
| Calidad RAG | Similitud media y umbral | Diagnóstico de recuperación, no una medida de veracidad. Para precisión, recall y falsos rechazos usa la evaluación del golden dataset. |

Los agregados de `/metrics` son por proceso: se pierden al reiniciar y no se comparten entre varias réplicas. Para un entorno de producción, expórtalos a una base/servicio de observabilidad con retención y agregación centralizadas; no uses la memoria del proceso como histórico.

### Métricas para dimensionamiento y cliente

Estas medidas completan las métricas de aplicación y se deben recoger durante una prueba de carga representativa (misma guía, modelo, número de usuarios y región que producción):

| Métrica | Cómo medirla | Qué comunicar |
| --- | --- | --- |
| CPU y memoria | `docker stats --no-stream` durante la prueba, registrando valores cada intervalo acordado. | Consumo por instancia y margen antes de escalar. |
| Almacenamiento | `docker system df` para imágenes/volúmenes y tamaño del volumen PostgreSQL; medir crecimiento por semana con datos representativos. | Huella inicial, crecimiento y política de retención/backup. |
| Latencia y escala | Registrar p50/p95 y errores con `/api/v1/metrics` y el generador de carga; aumentar usuarios concurrentes por etapas. | Usuarios concurrentes probados, saturación observada y latencia objetivo. |
| Coste de inferencia | Multiplicar llamadas y tokens de entrada/salida observados por las tarifas vigentes del proveedor. | Coste estimado por consulta y por volumen mensual; el coste de Gemini no se infiere de la similitud. |
| Disponibilidad | Comprobar el healthcheck de `web` y la base de datos en Docker; agregar periodos disponibles y errores en una ventana acordada. | Disponibilidad medida y procedimiento de recuperación. |

La aplicación aún no mide por sí sola el consumo de CPU, el almacenamiento histórico ni los tokens/coste de Gemini. Mídelos en la prueba de carga y en la infraestructura del despliegue antes de presentar cifras como compromisos comerciales. Evita atribuir un valor de escala o coste no medido.

## Pruebas

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/evaluate_golden_dataset.py
```

`tests/test_api.py` y `tests/test_progress_api.py` cubren health, frontend estático, chat/RAG, métricas, login, aislamiento por usuario, registros, logros y PDF. Los tests usan una base SQLite temporal y no necesitan credenciales de Gemini ni PostgreSQL. GitHub Actions repite los tests y la evaluación, y construye la imagen Docker en cada PR o push a `main`.

## GitHub Actions y despliegue a Render

El workflow de `.github/workflows/ci-cd.yml` despliega solo los pushes a `main`, y únicamente después de que pasen los tests, el golden dataset y el build de Docker. Los PR ejecutan esas verificaciones, pero no despliegan.

1. Sube el código a GitHub y crea un **Blueprint** en Render conectado a este repositorio; Render leerá `render.yaml` y creará el servicio web y la base de datos. El plan `free` de Render puede tener límites o condiciones de disponibilidad propios del proveedor.
2. En la configuración del servicio web de Render, añade `GEMINI_API_KEY` como variable secreta.
3. En Render, crea un **Deploy Hook** para el servicio web y copia la URL.
4. En GitHub, abre **Settings → Secrets and variables → Actions → New repository secret** y crea `RENDER_DEPLOY_HOOK_URL` con esa URL. No la guardes en el repositorio ni en `render.yaml`.
5. Desactiva los despliegues automáticos por commit en Render (el Blueprint ya establece `autoDeployTrigger: off`). Así, producción solo se actualiza cuando termina correctamente el workflow.
6. Abre **Actions** en GitHub para ver el resultado. Un push a `main` inicia el pipeline y, al pasar todos los checks, solicita el despliegue a Render.

El deploy hook inicia el despliegue; el estado final y los logs de compilación/arranque se consultan en el panel de Render. Añade reglas de protección a `main` para exigir que el workflow pase antes de aceptar cambios.
