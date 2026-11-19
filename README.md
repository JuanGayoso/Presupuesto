# Evaluación de Proyectos Inmobiliarios

Herramienta para evaluar la factibilidad económica de un proyecto inmobiliario con un **modelo paramétrico**: cada partida (Terreno, Alcabala, Costo directo, Fees, Contingencia, Ingresos…) tiene su propia fórmula escrita en lenguaje natural, que referencia otras partidas o variables **por nombre y no por posición de celda**.

Está pensada como reemplazo de la hoja de Excel de "cabida/evaluación", resolviendo sus problemas típicos: fórmulas que se rompen al insertar o mover filas, referencias que apuntan a la celda equivocada sin avisar, e inconsistencias entre celdas que nadie detecta.

## Índice
1. [Qué hace](#qué-hace)
2. [Cómo ejecutarlo](#cómo-ejecutarlo)
3. [Conceptos del modelo](#conceptos-del-modelo)
4. [Lenguaje de fórmulas](#lenguaje-de-fórmulas)
5. [Cómo se calcula](#cómo-se-calcula)
6. [Impuestos y reglas del negocio](#impuestos-y-reglas-del-negocio)
7. [Plantillas y proyectos](#plantillas-y-proyectos)
8. [API REST](#api-rest)
9. [Arquitectura y estructura del código](#arquitectura-y-estructura-del-código)
10. [Seguridad](#seguridad)
11. [Limitaciones conocidas](#limitaciones-conocidas)

## Qué hace
- **Fórmulas por nombre**: `Alcabala = max(0, Terreno - 10*UIT) * 0.03`. Reordenar, renombrar o insertar partidas no rompe nada.
- **Grafo de dependencias**: las dependencias se infieren leyendo cada fórmula (no se declaran a mano). El orden de cálculo se resuelve solo (orden topológico).
- **Detección de ciclos** antes de calcular, indicando qué partidas están involucradas (`A → B → C → A`).
- **Errores localizados**: una fórmula rota marca solo esa partida (y las que dependen de ella); el resto se sigue calculando.
- **Variables generales del proyecto** (UIT, tipo de cambio, área vendible, área construida, etc.) como inputs base.
- **Partidas agregadoras**: una partida puede ser la suma de sub-partidas; las partidas que la referencian no necesitan cambiar su fórmula.
- **Plantillas reutilizables**: un proyecto nuevo se crea duplicando una plantilla y queda totalmente independiente de ella.
- **Historial** de cambios de fórmula por partida (fórmula anterior, nueva y fecha).
- **API REST completa** y interfaz web.

## Cómo ejecutarlo
Requisito: [Docker](https://www.docker.com/) con Docker Compose (Windows, Mac o Linux). No necesitas instalar Python ni PostgreSQL.

```bash
git clone https://github.com/JuanGayoso/Presupuesto.git
cd Presupuesto
```

**1. Configuración inicial (una sola vez).** El asistente te pregunta los datos y crea el archivo `.env`; al final ofrece levantar la aplicación.

| Sistema | Comando |
|---|---|
| macOS / Linux | `./setup.sh` |
| Windows (PowerShell) | `.\setup.ps1` (si bloquea scripts: `powershell -ExecutionPolicy Bypass -File .\setup.ps1`) |

Te pide: nombre de la base de datos, usuario, **contraseña** (con Enter se genera una segura), puerto de la aplicación y si quieres la plantilla demo.

*¿Prefieres hacerlo a mano?* Copia `.env.example` a `.env` y completa `POSTGRES_PASSWORD`. Sin ese archivo, `docker compose` se detiene con un mensaje que lo indica.

**2. Levantar la aplicación** (si el asistente no lo hizo ya):
```bash
docker compose up --build -d
```

- Interfaz web: http://localhost:8000 (o el puerto que elegiste)
- Documentación interactiva de la API (Swagger): http://localhost:8000/docs

Para detener: `docker compose down` (con `-v` también borra los datos).

### Dónde se configura todo
Toda la información sensible o dependiente de tu entorno vive en el archivo **`.env`** (no se sube a git):

| Variable | Para qué sirve | Por defecto |
|---|---|---|
| `POSTGRES_PASSWORD` | Contraseña de la base de datos. **Obligatoria.** Solo letras, números, `_`, `.` o `-`. | — |
| `POSTGRES_USER` | Usuario de la base de datos | `evaluacion` |
| `POSTGRES_DB` | Nombre de la base de datos | `evaluacion_inmobiliaria` |
| `APP_PORT` | Puerto web en tu máquina | `8000` |
| `SEED_ON_STARTUP` | `true` crea la plantilla demo si la base está vacía | `true` |

### Base de datos
La aplicación usa **PostgreSQL 16**, que corre en un contenedor Docker propio: **no tienes que instalarla ni crearla**.
- La base y el usuario se crean solos la primera vez, con los valores de tu `.env`.
- Las **tablas** las crea la propia aplicación al arrancar (no hay scripts SQL que ejecutar).
- Los **datos** se guardan en el volumen de Docker `db_data`, así que sobreviven a reinicios y a `docker compose down`.
- Si cambias `POSTGRES_USER`, `POSTGRES_PASSWORD` o `POSTGRES_DB` **después** del primer arranque, Postgres seguirá usando los valores antiguos guardados en el volumen. Para empezar de cero con credenciales nuevas: `docker compose down -v` (borra los datos) y vuelve a levantar.
- Para conectarte a una base de datos propia, sin el contenedor de Postgres, define la variable `DATABASE_URL` (ej. `postgresql+psycopg2://usuario:clave@host:5432/base`) y ejecuta la app con `uvicorn app.main:app`.

## Conceptos del modelo
| Concepto | Qué es |
|---|---|
| **Variable** | Input base con una `key` (ej. `UIT`, `AreaVendible`). No tiene fórmula, solo un valor. |
| **Partida** (line item) | Un concepto del modelo (ej. `Terreno`, `GastosGenerales`). Tiene `key`, nombre, categoría y una fórmula, o bien es agregadora. |
| **Partida agregadora** | Su valor es la suma de sus sub-partidas (las que la tienen como padre). No lleva fórmula. |
| **Plantilla** | Conjunto de variables y partidas con sus fórmulas, sin datos de un proyecto específico. Tiene un número de versión que sube con cada cambio estructural. |
| **Proyecto** | Copia independiente de una plantilla, con sus propios valores de variables y sus propias fórmulas editables. |
| **`key`** | Identificador estable (letras, números y `_`, sin espacios, no puede empezar con número). Es lo que usan las fórmulas para referenciar. Es único dentro de la plantilla/proyecto entre variables y partidas. |

La jerarquía padre/hijo (agregadoras) es **estructural** y es independiente del grafo de referencias entre fórmulas: una partida puede ser hija de otra y a la vez ser referenciada desde cualquier fórmula.

## Lenguaje de fórmulas
Una fórmula es una expresión matemática. Puede usar:

- **Números**: `10`, `0.03`, `1500000.50`
- **Operadores**: `+  -  *  /  %  ^` (potencia) y paréntesis. Menos unario: `-x`.
- **Comparaciones**: `<  <=  >  >=  ==  !=` (útiles dentro de `if`).
- **Referencias**: la `key` de una variable u otra partida, ej. `CostoDirecto * 0.08`.
- **Funciones permitidas**: `max(a,b,…)`, `min(a,b,…)`, `round(x, n)`, `sqrt(x)`, `abs(x)`, `ceil(x)`, `floor(x)`, `if(condición, si_verdadero, si_falso)`.

Ejemplos:

| Partida | Fórmula |
|---|---|
| Alcabala (tramo de 10 UIT exonerado, luego 3%) | `max(0, Terreno - 10*UIT) * 0.03` |
| Gastos generales (% de otra partida) | `CostoDirectoConstruccion * 0.10` |
| Marketing (% de los ingresos) | `IngresosTotales * 0.03` |
| Ingresos netos (IGV de ventas incluido en el precio) | `IngresosTotales / 1.09` |
| Fee escalonado | `if(AreaVendible > 1000, IngresosTotales * 0.02, IngresosTotales * 0.03)` |

Una referencia a algo que no existe (por ejemplo por un error de tipeo) no se detecta al guardar sino al calcular, y marca esa partida con el error `'X' no está definido o no se pudo calcular`, resaltando la referencia faltante.

## Cómo se calcula
El motor (`app/formula/engine.py`) sigue estos pasos cada vez que se pide un cálculo:

1. **Parsea** cada fórmula y extrae sus dependencias leyendo las referencias del árbol sintáctico.
2. **Construye el grafo** (variables → partidas) usando solo las referencias que existen.
3. **Ordena topológicamente** (algoritmo de Kahn): nunca calcula una partida antes que aquellas de las que depende.
4. **Detecta ciclos**: los nodos que no se pueden ordenar forman parte de un ciclo (o dependen de uno); se reporta el camino exacto.
5. **Evalúa en orden**, capturando el error de cada partida por separado. Una partida con error no entra al contexto, así que todo lo que depende de ella falla con el mensaje `depende de 'X', que tiene un error`.

El cálculo se hace en cada consulta a `/calculate`; no se almacenan resultados, por lo que nunca hay valores desactualizados.

## Impuestos y reglas del negocio
Ninguna regla está "quemada" en el motor salvo el IGV de compras; el resto son simplemente fórmulas:

- **IGV de compras (18%)**: cada partida tiene una casilla *"Aplica IGV de compras"*. El motor crea automáticamente el valor `IGV_COMPRAS` = (suma de las partidas marcadas) × tasa, que puedes referenciar en cualquier fórmula (ej. en la inversión total). Terreno y Alcabala se dejan sin marcar porque son operaciones no gravadas. La tasa es 0.18 por defecto y se puede cambiar creando una variable llamada `IGV_COMPRAS_TASA`. `IGV_COMPRAS` es una key reservada.
- **IGV de ventas (9%)**: ya incluido en el precio de venta; se resuelve "hacia atrás" con la fórmula `Ingresos / 1.09`.
- **Alcabala con tramo UIT**: ver ejemplo de arriba.
- **Fees**: como % de otras partidas o como % de los ingresos totales, ambos con fórmulas normales.

## Plantillas y proyectos
- **Crear un proyecto** (`POST /api/projects`) copia las variables y partidas de la plantilla elegida. A partir de ahí el proyecto es independiente: editar la plantilla no cambia proyectos existentes y viceversa.
- Cada proyecto guarda un *snapshot* del nombre y versión de la plantilla de origen, solo informativo.
- La plantilla puede evolucionar (agregar partidas, subdividir una partida en sub-partidas agregadoras) sin romper proyectos ya creados. Subdividir una partida en sub-partidas no obliga a cambiar las fórmulas que la referencian, porque se referencia por `key`.
- **Duplicar plantilla** (`POST /api/templates/{id}/duplicate`) crea una copia con sufijo "(copia)".
- Cada cambio de fórmula en una partida (de plantilla o de proyecto) queda en su **historial**.

### Plantilla demo incluida
"Modelo Inmobiliario Estándar", con valores de ejemplo genéricos (todos editables; no corresponden a ningún proyecto real):

| Variables | Partidas principales |
|---|---|
| `UIT`, `TipoCambio`, `AreaVendible`, `AreaConstruidaTotal`, `PrecioVentaM2`, `IGV_COMPRAS_TASA` | Terreno, Alcabala, Costo directo de construcción (agregadora de 5 sub-partidas), Gastos generales, Utilidad del constructor, Costo de construcción total, Ingresos totales / netos, Gestión inmobiliaria, Marketing, Contingencia, Inversión total, Utilidad del proyecto, Margen (%) |

Las partidas de la categoría `Resumen` se muestran como indicadores (KPI) en la cabecera de un proyecto.

## API REST
Documentación interactiva en `/docs`. Resumen:

**Plantillas** (`/api/templates`)
| Método | Ruta | Descripción |
|---|---|---|
| GET / POST | `/api/templates` | Listar / crear |
| GET / PUT / DELETE | `/api/templates/{id}` | Detalle (con variables y partidas) / editar / borrar |
| POST | `/api/templates/{id}/duplicate` | Duplicar |
| POST | `/api/templates/{id}/variables` | Agregar variable |
| PUT / DELETE | `/api/templates/{id}/variables/{var_id}` | Editar / borrar variable |
| POST | `/api/templates/{id}/items` | Agregar partida |
| PUT / DELETE | `/api/templates/{id}/items/{item_id}` | Editar / borrar partida |
| GET | `/api/templates/{id}/items/{item_id}/history` | Historial de fórmula |
| GET | `/api/templates/{id}/calculate` | Calcular con los valores por defecto |

**Proyectos** (`/api/projects`)
| Método | Ruta | Descripción |
|---|---|---|
| GET / POST | `/api/projects` | Listar / crear a partir de una plantilla (`{"name": "...", "template_id": 1}`) |
| GET / PUT / DELETE | `/api/projects/{id}` | Detalle / renombrar / borrar |
| PUT | `/api/projects/{id}/variables/{var_id}` | Cambiar el valor de una variable (`{"value": 2500}`) |
| POST | `/api/projects/{id}/items` | Agregar partida al proyecto |
| PUT / DELETE | `/api/projects/{id}/items/{item_id}` | Editar / borrar partida |
| GET | `/api/projects/{id}/items/{item_id}/history` | Historial de fórmula |
| GET | `/api/projects/{id}/calculate` | Calcular el proyecto |

**Fórmulas**: `POST /api/formulas/validate` con `{"formula": "..."}` devuelve si es válida, el error de sintaxis y las dependencias detectadas.

Ejemplo — crear un proyecto desde la plantilla demo y recalcular tras cambiar una variable:
```bash
curl -X POST localhost:8000/api/projects -H "Content-Type: application/json" \
  -d '{"name":"Mi proyecto","template_id":1}'
curl -X PUT localhost:8000/api/projects/1/variables/3 -H "Content-Type: application/json" \
  -d '{"value":2500}'
curl localhost:8000/api/projects/1/calculate
```
La respuesta de `/calculate` incluye, por cada nodo: `value`, `error`, `depends_on`, y la lista `order` con el orden de cálculo resuelto.

## Arquitectura y estructura del código
Tres capas, desplegadas con Docker Compose (dos contenedores: base de datos y aplicación que sirve API + interfaz):

```
Navegador (JS vanilla)  ──►  FastAPI + motor de cálculo (Python)  ──►  PostgreSQL
```

```
app/
  main.py            App FastAPI, crea las tablas y sirve la interfaz estática
  database.py        Conexión SQLAlchemy (DATABASE_URL)
  models.py          Plantilla/Proyecto, variables, partidas e historial
  schemas.py         Esquemas Pydantic de entrada/salida
  services.py        Une modelos con el motor (resolución de padres, cálculo)
  seed.py            Plantilla demo del primer arranque
  routers/           templates.py, projects.py, formulas.py
  formula/
    lexer.py         Tokenizador
    parser.py        Parser descendente recursivo → AST
    ast_nodes.py     Nodos del árbol sintáctico
    evaluator.py     Evaluación restringida + extracción de dependencias
    engine.py        Grafo, orden topológico, ciclos, IGV, agregadoras
public/              Interfaz web (index.html, css, js/views/…)
Dockerfile, docker-compose.yml, requirements.txt
```
El motor (`app/formula/`) no depende de la base de datos: trabaja con estructuras simples, por lo que puede probarse o reutilizarse por separado.

Las tablas se crean al arrancar (`create_all`); aún no hay migraciones.

## Seguridad
Las fórmulas **no se ejecutan con `eval`**: un parser propio solo admite números, referencias, operadores y las funciones de la lista blanca. No hay cadenas de texto, acceso a atributos, imports, archivos, red ni ejecución de comandos, algo relevante si varias personas editan fórmulas.

## Limitaciones conocidas
- Sin autenticación ni usuarios: pensado para uso interno o local; no lo expongas a internet tal cual (el puerto de la base de datos no se publica, solo el de la aplicación).
- El historial registra la fórmula, pero no quién la cambió.
- Las referencias inexistentes se detectan al calcular, no al guardar la fórmula.
- Sin migraciones de base de datos ni pruebas automatizadas aún.
- La interfaz está validada con la plantilla demo; conviene probar más a fondo la edición de partidas con fórmulas.
