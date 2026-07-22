# Handoff técnico — Calculadora de Derivadas

> **Para el próximo chat:** este documento describe **qué es la app, cómo está construida y cómo se armó paso a paso**. Úsalo como fuente única de verdad para generar un **documento formal de construcción** (informe técnico / manual paso a paso) del proyecto. No tienes acceso a la conversación original; todo lo necesario está aquí. El proyecto es un trabajo escolar de **cálculo diferencial**, así que el documento formal debe explicar el **paso a paso** de forma clara y ordenada.

---

## 1. Resumen del proyecto

Aplicación de **escritorio** (Windows) que **deriva funciones matemáticas de una variable** y **explica qué reglas de derivación se aplicaron** (producto, cociente, cadena, potencia, derivadas de seno/coseno/exponencial, etc.). Pensada como herramienta de estudio: además del resultado, muestra el "paso a paso" en forma de lista de reglas.

- **Motor matemático:** SymPy (cálculo simbólico exacto).
- **Interfaz gráfica:** PySide6 (Qt para Python), con diseño propio "editorial".
- **Teclado matemático (numpad)** integrado tipo calculadora científica, para insertar funciones y símbolos sin errores de tipeo.
- **Empaquetable como `.exe`** con PyInstaller (no requiere que el usuario final tenga Python).

---

## 2. Tecnologías y dependencias

| Componente | Uso |
|---|---|
| Python 3.12 | Lenguaje base |
| PySide6 (>=6.6, <7) | Interfaz gráfica (Qt) |
| SymPy (==1.14.0) | Motor de derivación simbólica |
| PyInstaller (6.x) | Generar el ejecutable `.exe` |
| Pillow | Solo para generar el ícono `.ico` (paso auxiliar) |
| Fuentes: **Fraunces** e **IBM Plex Mono** | Tipografía embebida (licencia libre OFL, descargadas de fontsource) |

`requirements.txt`:
```
PySide6>=6.6,<7
sympy==1.14.0
```

---

## 3. Estructura de archivos

```
calc/
├── main.py            # Interfaz gráfica (ventana, numpad, estados)
├── derivador.py       # Motor: deriva y detecta las reglas aplicadas
├── style.qss          # Estilos (colores, tipografía) — "CSS" de Qt
├── main.spec          # Receta de PyInstaller para armar el .exe
├── requirements.txt   # Dependencias
├── start.bat          # Lanzador rápido para desarrollo
├── assets/
│   ├── app_icon.png   # Ícono de la ventana
│   ├── app_icon.ico   # Ícono del .exe
│   └── fonts/         # 7 archivos .ttf (Fraunces + IBM Plex Mono)
└── dist/
    └── CalculadoraDerivadas.exe   # Ejecutable final (generado por PyInstaller)
```

Separación de responsabilidades: **`derivador.py` no sabe nada de la interfaz** (es lógica pura y se puede probar sola), y **`main.py` no calcula derivadas** (solo llama a `derivar()` y muestra el resultado).

---

## 4. El motor — `derivador.py`

Expone una sola función pública: `derivar(funcion_str)` que recibe la función como texto y devuelve un diccionario:

```python
{
    'funcion_original': <expresión SymPy>,
    'derivada': <expresión SymPy>,
    'reglas': [<lista de textos explicando cada regla>],
    'variable': 'x',          # variable respecto a la que se derivó
    'exito': True/False,
    'error': None o <mensaje>
}
```

### 4.1 Cómo deriva (`derivar`)

1. Convierte el texto a una expresión con `sympify(funcion_str)`.
2. **Detecta la variable automáticamente** con `funcion.free_symbols` (así funciona con `x`, `t`, `y`, etc., no solo `x`).
   - **0 variables** → es una constante → derivada `0`.
   - **1 variable** → deriva respecto a ella.
   - **2 o más variables** → **avisa y NO calcula** (esta calculadora es de una sola variable). Ejemplo de mensaje: *"Detecté varias variables (x, y)…"*.
3. **Asume la variable REAL** antes de derivar (`sp.Symbol(nombre, real=True)`), para obtener resultados limpios en el dominio real (ej. `d/dx |x| = sign(x)` en vez de una expresión con `re(x)`/`im(x)`).
4. Calcula la derivada con `diff`.
5. Llama a `identificar_reglas` para el paso a paso.

Manejo de errores: si `sympify` no entiende la fórmula, devuelve un mensaje claro pidiendo revisar paréntesis/potencias, en vez de romperse.

### 4.2 Cómo detecta las reglas (`identificar_reglas`) — el corazón del proyecto

**Idea clave:** recorre el **árbol de la expresión** de SymPy (`preorder_traversal`), NO el texto. Analizar el texto (como en una primera versión) produce falsos positivos (creer que hay "producto" porque `**` contiene un `*`, etc.). El árbol permite reconocer la estructura real:

- `Add` → regla de la **suma/resta**.
- `Mul` → separa factores; distingue **producto** (dos o más factores con la variable), **cociente** (hay un factor con exponente negativo que depende de la variable) y **múltiplo constante** (un número ≠ ±1 multiplicando).
- `Pow` → distingue **raíz** (exponente ½), **potencia** (`u^n`, exponente numérico), **exponencial** (`a^u`, base constante) y el caso general `u^v` (derivación logarítmica).
- Funciones (`sin`, `cos`, `asin`, `log`, `exp`, …) → agrega la **derivada específica** de cada una (diccionario `REGLAS_FUNCION`).
- **Regla de la cadena** → se agrega si alguna función o potencia tiene un argumento interno que no es solo la variable (composición).

Se deduplican por tipo para que la lista tenga sentido (no repetir "derivada del seno" 5 veces).

**Detalle importante — no simplificar:** las reglas se identifican sobre la fórmula **SIN simplificar**, usando `sympify(funcion_str, evaluate=False)`. ¿Por qué? Porque SymPy, al evaluar, cancela igualdades matemáticas: `sen(arcsen(u))` se convierte en `u`, y eso **borraría** funciones que el estudiante SÍ escribió. Derivando la versión evaluada pero identificando reglas sobre la versión cruda, se logra que **una función compleja muestre todas sus reglas** aunque matemáticamente se simplifique.

Ejemplo real (la prueba de fuego): para
`sin(asin(ln(cos(atan(exp(x))))))/sqrt(25*x)`
se listan **11 reglas**: cociente, derivada del seno, del arcoseno, del logaritmo, del coseno, del arcotangente, de la exponencial, potencia, raíz, múltiplo constante y cadena.

---

### 4.3 Seguridad y robustez
La entrada del usuario se trata como NO confiable (se sometió a un red-team de tres frentes: seguridad, matemático y aporreo):
- **Sin ejecución de código:** en vez de `sympify` (que evalúa con todo el intérprete y permitía ejecutar comandos del sistema, p. ej. `__import__("os").system(...)`), se usa `parse_expr` con una **lista blanca** de funciones y un namespace sin `__builtins__`. Los nombres desconocidos se vuelven símbolos inertes; funciones peligrosas (`integrate`, `solve`, `__import__`…) no existen para el parser.
- **Sin congelamientos (DoS):** un guard rechaza números/potencias gigantes (`9**9**9`, `factorial(10**6)`, torres de exponentes) revisando solo la ESTRUCTURA, antes de materializarlos. Se limita el largo de la entrada.
- **Solo caracteres válidos:** se aceptan únicamente letras, dígitos y operadores matemáticos; emojis, unicode raro y símbolos peligrosos se rechazan.
- **Nunca revienta:** `derivar()` siempre devuelve su diccionario (jamás lanza una excepción), con un mensaje claro si algo falla.
- **Solo funciones elementales y dominio real:** derivadas que darían funciones avanzadas (Gamma, `floor`, `zeta`…) o valores no definidos en los reales (`arcsen(2)`, `log(−1)`, división por cero) se rechazan con un aviso, en vez de mostrar jerga de SymPy o un `0` engañoso.

## 5. La interfaz — `main.py` + `style.qss`

### 5.1 Dirección de diseño: "Editorial"
Estilo de **revista/libro de matemáticas** (elegido por el usuario tras descartar un diseño de tarjetas por verse "genérico/IA"):
- Fondo **papel** cálido, tipografía **serif Fraunces** con carácter, acento **rojo óxido**, **secciones numeradas** (01 · FUNCIÓN, 02 · DERIVADA, 03 · REGLAS), líneas finas, mucho espacio en blanco. Sin tarjetas ni sombras (plano a propósito).

**Tokens de color** (definidos en `style.qss`):
```
#F2EEE3  papel (fondo)
#1B1A17  tinta (texto)
#9E3B2E  acento rojo óxido
#C7BEAB / #D6CDBB  líneas finas
#B8AF9C  número tenue de regla
#8A8577  texto tenue
```

**Tipografías embebidas** (en `assets/fonts/`, cargadas con `QFontDatabase.addApplicationFont`):
- `Fraunces` / `Fraunces SemiBold` / `Fraunces Black` (serif; cada peso se registra como familia propia).
- `IBM Plex Mono` (monoespaciada, para etiquetas, entrada y numpad).

Nota Qt: QSS **no** soporta `letter-spacing` ni `text-transform`, por eso el "tracking" de las etiquetas se aplica por código con `QFont.setLetterSpacing`, y el texto se escribe ya en mayúsculas.

### 5.2 El teclado matemático (numpad)
Rejilla (`QGridLayout`) de 6 columnas tipo calculadora científica. Cada botón **inserta sintaxis válida para SymPy** para evitar errores de tipeo. Incluye:
- **Multiplicación implícita:** `45x` se entiende como `45*x`, `2(x+1)` como `2·(x+1)`, `2sen(x)` como `2·sen(x)`. También se aceptan alias en español escritos a mano (`sen`, `arcsen`, `tg`, `abs`…).
- **Auto-limpiado:** al editar la función (teclado o numpad) el resultado anterior se borra solo, para que sea evidente que hay que volver a derivar (no hay que pulsar "C").
- **Notación de clase** en los botones (aunque por dentro inserten la sintaxis de SymPy): `sen cos tan`, inversas `arcsen arccos arctan` (→ `asin/acos/atan`), hiperbólicas `senh cosh tanh`.
- Logaritmos y exponencial: `ln` (→ `log()`), `log10` (→ `log(,10)`), `exp`.
- **Raíces** (no solo la cuadrada): `√` (→ `sqrt()`), `³√` cúbica (→ `cbrt()`), `n√` enésima (abre un pequeño diálogo que pregunta el índice, para no confundir el orden, y arma `root(radicando, índice)`), potencia `^` (→ `**`).
- Constantes `π`, `e` (→ `E`, número de Euler), factorial `n!` (→ `factorial()`), valor absoluto `|x|` (→ `Abs()`).
- Variable `x`, paréntesis, coma, números, operadores `+ − × ÷` (insertan `+ - * /`), `.`
- `DEL` (borrar), `C` (limpiar), y **Derivar** (botón de acento a lo ancho).

Detalles de usabilidad:
- Las funciones insertan `nombre()` y dejan el cursor **dentro** del paréntesis.
- **Paréntesis inteligente:** si el usuario pulsa `)` y ya hay uno a la derecha, el cursor solo salta sobre él (no duplica).
- Cada botón tiene **tooltip** explicativo (ej. `e` → "Número de Euler ≈ 2.718").
- Se usa la versión **completa** de IBM Plex Mono (incluye `√ π ³ ½`). La raíz cúbica se muestra `³√`; la enésima `n√` (la fuente no trae el superíndice `ⁿ`); el botón de borrar se rotula `DEL`.

### 5.3 Estados de la pantalla
- **Entrada** (01): campo de texto + línea gris `= …` que **repite la función tal como se escribió** (solo cambia `**`→`^` y `*`→`·`), sin simplificar.
- **Derivada** (02): resultado grande en serif, con la nota "derivada respecto a x".
- **Reglas** (03): lista numerada, una fila por regla, con líneas finas.
- **Errores en dos categorías:** si la función lleva a una **indeterminación** (p. ej. división por cero) se muestra una imagen; si hay un **error de escritura** (paréntesis, función mal escrita, varias variables…) se explica el error en texto (rojo óxido). El motor distingue ambos con el campo `tipo` del resultado (`indeterminacion` / `error`).
- Todo va dentro de un `QScrollArea` para que quepa en pantallas pequeñas.

### 5.4 Carga de recursos compatible con `.exe`
Para que el estilo, las fuentes y el ícono funcionen tanto en desarrollo como dentro del ejecutable, la ruta base se resuelve así:
```python
def _base_dir():
    if getattr(sys, "frozen", False):   # corriendo como .exe (PyInstaller)
        return sys._MEIPASS             # carpeta temporal donde se extraen los datos
    return os.path.dirname(os.path.abspath(__file__))  # desarrollo
```

---

## 6. Cómo ejecutar (desarrollo)

```bat
pip install -r requirements.txt
python main.py
```
(o hacer doble clic en `start.bat`, que instala las dependencias solo si faltan y abre la app).

---

## 7. Cómo construir el `.exe` (PyInstaller)

1. Instalar PyInstaller: `pip install pyinstaller`
2. Construir con la receta: `python -m PyInstaller --noconfirm --clean main.spec`
3. Resultado: `dist/CalculadoraDerivadas.exe` (ejecutable único, ~78 MB, con el ícono embebido).

`main.spec` (puntos clave):
- `datas=[('style.qss', '.'), ('assets', 'assets')]` → empaqueta el estilo y la carpeta `assets` (fuentes + ícono) dentro del `.exe`.
- `icon=['assets\\app_icon.ico']` → ícono del ejecutable.
- `console=False` → app de ventana, sin consola negra.
- `name='CalculadoraDerivadas'` → nombre del ejecutable.

El ícono se generó con un script auxiliar (Qt dibuja una "d" serif de Fraunces sobre un cuadrado redondeado color óxido → PNG; Pillow lo convierte a `.ico` multi-tamaño).

---

## 8. Historial de construcción (etapas)

El proyecto partió de una versión básica con fallos y se mejoró por etapas:

- **Análisis inicial:** se auditó el código y se listaron errores de lógica, interfaz, diseño y empaquetado.
- **Etapa 1 — Interfaz/diseño:** rediseño completo al estilo editorial, con fuentes embebidas (antes eran de relleno y no combinaban).
- **Etapa 2 — Variable automática:** antes la app solo entendía `x` y devolvía `0` en secreto con otras variables; ahora detecta la variable y avisa si hay varias.
- **Numpad:** se agregó el teclado matemático para evitar errores de tipeo.
- **Etapa 3 — Reglas correctas:** se reescribió la detección de reglas (de leer texto a recorrer el árbol de SymPy), eliminando falsos positivos y mostrando todas las reglas de funciones anidadas.
- **Etapa 4 — Empaquetado:** rutas compatibles con `.exe` (`sys._MEIPASS`), ícono propio, versiones fijadas, y build final del ejecutable.
- **Pulido final:** variable asumida real (para `Abs`), auditoría de casos raros (0 crashes en 28 entradas límite).

---

## 9. Verificación / casos de prueba (todos comprobados)

| Entrada | Resultado esperado |
|---|---|
| `x**2 * sin(x)` | derivada `x²·cos(x) + 2·x·sin(x)`; reglas: producto, potencia, seno |
| `y**2` | derivada `2·y` (detecta variable `y`) |
| `x*y` | aviso: varias variables, no calcula |
| `x/2` | múltiplo constante |
| `sin(x**2)` | seno, potencia, cadena |
| `Abs(x)` | `sign(x)` |
| `2**x` | exponencial |
| `sin(asin(ln(cos(atan(exp(x))))))/sqrt(25*x)` | 11 reglas completas |
| entradas basura (`@@`, `sin(`, `x***2`) | mensaje de error claro, sin crash |

---

## 10. Limitaciones conocidas

- Es una calculadora de **una sola variable** (si hay varias, avisa y no calcula — decisión de diseño).
- La **derivada** que se muestra es la forma matemática (SymPy puede simplificarla); las **reglas** sí respetan la fórmula tal como se escribió.
- Escribir `e` en minúscula lo interpreta como una **variable** llamada e; para el número de Euler se usa el botón `e` (inserta `E`) o se escribe `E`.
- Solo deriva funciones **elementales**. Las avanzadas (factorial de una variable, `floor`, `ceiling`, Gamma, `zeta`…) se rechazan con un aviso, en vez de mostrar un resultado ilegible.

---

## 11. Instrucción para el documento formal

Con base en TODO lo anterior, genera un **documento formal de construcción de la aplicación**, paso a paso, apto para entregar como trabajo escolar de cálculo diferencial. Debe incluir, como mínimo:
1. Portada / título, objetivo y alcance del proyecto.
2. Marco teórico breve (reglas de derivación que implementa la app).
3. Tecnologías utilizadas y por qué.
4. Arquitectura (separación motor / interfaz) con la estructura de archivos.
5. Explicación **paso a paso** de cómo funciona el motor (detección de variable, derivación, identificación de reglas por el árbol de SymPy, el detalle de no simplificar).
6. Explicación de la interfaz y del teclado matemático.
7. Guía de instalación, ejecución y **construcción del `.exe`**.
8. Pruebas realizadas y resultados.
9. Conclusiones y posibles mejoras futuras.

Redáctalo en español, con lenguaje claro, encabezados, y donde ayude, incluye fragmentos de código y tablas. Mantén un tono formal y didáctico.
```
