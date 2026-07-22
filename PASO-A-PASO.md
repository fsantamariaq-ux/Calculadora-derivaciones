# Construcción paso a paso de una Calculadora de Derivadas

### Documento de fundamentación matemática, lógica y técnica

---

## 1. Objetivo y alcance

Se construye una aplicación de escritorio que, dada una función real de una variable
$f(x)$, calcula su derivada $f'(x)$ **y explica el conjunto de reglas de derivación
que intervienen**. El énfasis no está solo en el resultado, sino en el *procedimiento*:
la aplicación es una herramienta didáctica de **cálculo diferencial**.

Alcance: funciones reales de **una variable**, construidas con las operaciones
elementales (suma, resta, producto, cociente, potencia y raíz) y las funciones
elementales (polinómicas, racionales, trigonométricas y sus inversas, exponenciales,
logarítmicas y valor absoluto).

---

## 2. Fundamentos matemáticos

### 2.1 Definición de derivada

La derivada de $f$ en un punto $x$ es el límite del cociente incremental

$$f'(x) \;=\; \lim_{h \to 0} \frac{f(x+h) - f(x)}{h},$$

siempre que dicho límite exista. Geométricamente, $f'(x)$ es la **pendiente de la recta
tangente** a la gráfica de $f$ en el punto $(x, f(x))$; físicamente, es la **razón de
cambio instantánea** de $f$ respecto a $x$.

Derivar directamente por la definición es impráctico para funciones compuestas. Por eso
el cálculo diferencial se apoya en un **álgebra de derivadas**: un conjunto de reglas que
permiten derivar cualquier función elemental descomponiéndola en sus partes.

### 2.2 Reglas de derivación (el álgebra de derivadas)

Sean $u = u(x)$ y $v = v(x)$ funciones derivables y $c$ una constante:

| Regla | Enunciado |
|---|---|
| Constante | $\dfrac{d}{dx}(c) = 0$ |
| Identidad | $\dfrac{d}{dx}(x) = 1$ |
| Múltiplo constante | $\dfrac{d}{dx}(c\,u) = c\,u'$ |
| Suma / resta | $\dfrac{d}{dx}(u \pm v) = u' \pm v'$ |
| Producto | $\dfrac{d}{dx}(u\,v) = u'v + u\,v'$ |
| Cociente | $\dfrac{d}{dx}\!\left(\dfrac{u}{v}\right) = \dfrac{u'v - u\,v'}{v^{2}}$ |
| Potencia | $\dfrac{d}{dx}(u^{n}) = n\,u^{\,n-1}\,u'$ |
| Cadena | $\dfrac{d}{dx}\,f\bigl(g(x)\bigr) = f'\bigl(g(x)\bigr)\cdot g'(x)$ |

La **regla de la potencia** es válida para todo exponente real $n$; en particular, una
**raíz** es una potencia de exponente fraccionario:

$$\sqrt[n]{u} = u^{1/n} \quad\Longrightarrow\quad \frac{d}{dx}\,u^{1/n} = \frac{1}{n}\,u^{\,\frac{1}{n}-1}\,u'.$$

La **regla exponencial** para base constante $a>0$ es

$$\frac{d}{dx}\,a^{\,u} = a^{\,u}\,\ln(a)\,u',$$

que en el caso $a=e$ se reduce a $\dfrac{d}{dx}e^{\,u} = e^{\,u}\,u'$.

### 2.3 Derivadas de las funciones elementales

| $f(x)$ | $f'(x)$ | | $f(x)$ | $f'(x)$ |
|---|---|---|---|---|
| $\sin x$ | $\cos x$ | | $\arcsin x$ | $\dfrac{1}{\sqrt{1-x^{2}}}$ |
| $\cos x$ | $-\sin x$ | | $\arccos x$ | $-\dfrac{1}{\sqrt{1-x^{2}}}$ |
| $\tan x$ | $\sec^{2} x$ | | $\arctan x$ | $\dfrac{1}{1+x^{2}}$ |
| $\cot x$ | $-\csc^{2} x$ | | $e^{x}$ | $e^{x}$ |
| $\sec x$ | $\sec x\,\tan x$ | | $a^{x}$ | $a^{x}\ln a$ |
| $\csc x$ | $-\csc x\,\cot x$ | | $\ln x$ | $\dfrac{1}{x}$ |
| $\lvert x\rvert$ | $\dfrac{x}{\lvert x\rvert}=\operatorname{sgn}(x)$ | | $\log_a x$ | $\dfrac{1}{x\ln a}$ |

Toda función elemental compuesta se deriva combinando estas derivadas con la regla de la
cadena y el álgebra de derivadas de la sección 2.2. Este hecho es la base teórica que
garantiza que el procedimiento es **completo** para el alcance definido.

### 2.4 Dominio real

La calculadora trabaja en $\mathbb{R}$. Una expresión como $\arcsin(2)$ **no está
definida** en los reales (pues $\arcsin$ requiere argumento en $[-1,1]$), y una división
por cero produce una **indeterminación**. Ambos casos se detectan y se comunican, en
lugar de devolver un resultado carente de sentido en el dominio real.

---

## 3. Fundamentos lógicos y computacionales

### 3.1 Cálculo simbólico frente a numérico

Existen dos estrategias para derivar por computadora:

- **Numérica** (diferencias finitas): aproxima $f'(x)\approx \dfrac{f(x+h)-f(x)}{h}$ para
  un $h$ pequeño. Da un *número*, con error de truncamiento, y **no** produce ni la
  fórmula de la derivada ni las reglas aplicadas.
- **Simbólica**: manipula la expresión como objeto algebraico y aplica las reglas exactas
  de la sección 2. Produce la **fórmula exacta** y permite **rastrear qué reglas se usan**.

Como el objetivo es didáctico (explicar el procedimiento), la única estrategia adecuada es
la **simbólica**.

### 3.2 Una función es un árbol de expresión

Toda expresión matemática admite una representación única como **árbol sintáctico**
(*Abstract Syntax Tree*, AST), donde las hojas son variables y constantes, y los nodos
internos son operaciones o funciones. Por ejemplo, $x^{2}\cdot\sin(x)$ se representa como:

```
        · (producto)
       / \
      ^   sin
     / \   |
    x   2  x
```

Es decir, $\text{Mul}\bigl(\text{Pow}(x,2),\ \sin(x)\bigr)$. Esta representación es la que
usa internamente el motor simbólico y es la clave lógica de todo el diseño.

### 3.3 Correspondencia árbol $\leftrightarrow$ regla (principio central)

La observación fundamental que hace posible el "paso a paso" es la siguiente:

> **Cada tipo de nodo del árbol corresponde exactamente a una regla de derivación.**

| Nodo del árbol | Regla que aplica |
|---|---|
| Suma `Add` | Regla de la suma/resta |
| Producto `Mul` con $\ge 2$ factores en $x$ | Regla del producto |
| Producto `Mul` con un factor de exponente negativo | Regla del cociente |
| Producto `Mul` con un factor constante $\neq \pm 1$ | Regla del múltiplo constante |
| Potencia `Pow` con exponente entero | Regla de la potencia |
| Potencia `Pow` con exponente fraccionario | Regla de la raíz (+ potencia) |
| Potencia `Pow` con base constante | Regla exponencial |
| Función $\sin, \cos, \ln, \dots$ | Derivada de esa función elemental |
| Función/potencia cuyo argumento **no** es solo $x$ | Regla de la cadena |

Por lo tanto, **recorrer el árbol y clasificar cada nodo equivale a enumerar las reglas
que intervienen en la derivación**. Éste es el núcleo lógico de la aplicación.

### 3.4 Por qué NO se analiza el texto

Una implementación ingenua buscaría símbolos en la *cadena de texto* (por ejemplo, "si hay
un `*`, hay un producto"). Esto es **lógicamente incorrecto** y produce falsos positivos:
la cadena `x**2` contiene el carácter `*`, pero no hay ningún producto; es una potencia.
Solo el **árbol** distingue la estructura real. Trabajar sobre el árbol —y no sobre el
texto— es una decisión de corrección, no de estilo.

---

## 4. Construcción paso a paso

### Paso 1 — Elección de tecnologías

| Herramienta | Función | Justificación |
|---|---|---|
| **Python** | Lenguaje base | Legible, amplio soporte científico. |
| **SymPy** | Motor de cálculo simbólico | Implementa con rigor el álgebra de derivadas y la representación en árbol (sección 3.2). |
| **PySide6 (Qt)** | Interfaz gráfica | Aplicación de escritorio nativa multiplataforma. |
| **PyInstaller** | Empaquetado | Genera un ejecutable `.exe` autónomo (sin requerir Python instalado). |

### Paso 2 — El motor: de texto a derivada

El motor implementa la siguiente *tubería* (pipeline):

$$\text{texto} \;\xrightarrow{\text{análisis léxico/sintáctico}}\; \text{árbol (AST)} \;\xrightarrow{\text{diff}}\; f'(x) \;\xrightarrow{\text{clasificación de nodos}}\; \text{reglas}.$$

1. **Análisis (parseo):** la cadena escrita por el usuario se convierte en el árbol de
   expresión. Se usa un analizador con **lista blanca** de funciones permitidas (ver Paso 6).
2. **Detección de la variable:** se examina el conjunto de símbolos libres del árbol
   (*free symbols*). Si hay exactamente uno, se deriva respecto a él; si hay varios, se
   informa que la calculadora es de una variable; si no hay ninguno, la función es
   constante y su derivada es $0$.
3. **Derivación:** se aplica el operador de derivación de SymPy, que ejecuta el álgebra de
   la sección 2 sobre el árbol, asumiendo la variable **real** para permanecer en $\mathbb{R}$.

### Paso 3 — Identificación de las reglas (el corazón didáctico)

Se recorre el árbol en **preorden** (de la operación más externa hacia las internas) y se
clasifica cada nodo según la tabla de la sección 3.3. En pseudocódigo:

```
para cada nodo en recorrido_preorden(árbol):
    si nodo es Suma:            registrar "regla de la suma/resta"
    si nodo es Producto:        analizar factores → producto / cociente / múltiplo constante
    si nodo es Potencia:        analizar exponente → potencia / raíz / exponencial
    si nodo es Función f:       registrar "derivada de f"
    si el argumento de una función/potencia no es solo x:
                                registrar "regla de la cadena"
devolver la lista de reglas (sin repetir)
```

**Corrección.** Como todo nodo del árbol corresponde a exactamente una regla (sección 3.3)
y el recorrido en preorden visita **todos** los nodos, la lista resultante contiene
**todas** las reglas involucradas y **solo** ésas (se evitan duplicados por tipo). Esto es
lo que garantiza que el "paso a paso" es correcto y completo.

**Matiz importante (identificar sin simplificar).** El motor calcula la derivada sobre la
forma *evaluada* (simplificada) —porque la derivada correcta es la misma para dos
expresiones matemáticamente iguales— pero **identifica las reglas sobre la forma tal como
la escribió el estudiante** (sin simplificar). La razón es didáctica: si el estudiante
escribe $\operatorname{sen}(\arcsin(u))$, esa expresión es igual a $u$, y una
simplificación borraría las funciones seno y arcoseno; pero pedagógicamente el estudiante
**sí** aplicó ambas. Se preservan, por tanto, todas las reglas del enunciado original.

### Paso 4 — Detección automática de la variable

En lugar de exigir que la variable sea siempre $x$, se lee el conjunto de símbolos libres
del árbol. Así, $y^{3}$ se deriva respecto a $y$ dando $3y^{2}$, y no un $0$ incorrecto.
Este es un requisito de **corrección**: derivar respecto a una variable que no aparece
daría $0$, un resultado falso.

### Paso 5 — La interfaz y el teclado matemático

La interfaz presenta la función, la derivada y la lista numerada de reglas (el paso a
paso). Un **teclado matemático** con botones inserta automáticamente la sintaxis correcta
(por ejemplo, el botón de raíz cúbica inserta la potencia $u^{1/3}$), de modo que el
estudiante no comete errores de escritura. Cuando el resultado es una **indeterminación**
se muestra una señal visual; cuando hay un **error de escritura** se explica qué corregir.

### Paso 6 — Robustez, dominio y seguridad

Puesto que la entrada es texto arbitrario del usuario, se aplican tres controles lógicos:

1. **Dominio real:** si la función o su derivada contienen partes complejas
   (p. ej. $\arcsin(2)$) o indeterminaciones (división por cero), se detecta y se informa,
   en vez de mostrar un resultado sin sentido real.
2. **Análisis seguro:** la entrada se interpreta con una **lista blanca** de funciones y
   sin acceso al intérprete del sistema, de modo que no puede ejecutarse código arbitrario.
3. **Acotación de recursos:** se rechazan expresiones que producirían números
   desmesurados (por ejemplo, torres de potencias), evitando que el cálculo se bloquee.

### Paso 7 — Empaquetado

Con PyInstaller se genera un único ejecutable que incorpora el intérprete, las
bibliotecas, las fuentes tipográficas y los recursos, de modo que la aplicación funciona en
cualquier equipo Windows sin instalación previa.

---

## 5. Validación

La corrección se comprobó con una batería de casos. Algunos representativos:

| Entrada | Derivada | Reglas identificadas |
|---|---|---|
| $x^{2}\sin x$ | $x^{2}\cos x + 2x\sin x$ | producto, potencia, seno |
| $y^{3}$ | $3y^{2}$ | potencia (variable $y$) |
| $\dfrac{\sin x}{x}$ | $\dfrac{\cos x}{x} - \dfrac{\sin x}{x^{2}}$ | cociente, seno, potencia |
| $\sqrt[3]{x}$ | $\dfrac{1}{3}x^{-2/3}$ | raíz, potencia |
| $\dfrac{\operatorname{sen}\!\bigl(\arcsin(\ln(\cos(\arctan(e^{x}))))\bigr)}{\sqrt{25x}}$ | (expresión extensa) | cociente, seno, arcoseno, logaritmo, coseno, arcotangente, exponencial, potencia, raíz, múltiplo constante y cadena — **11 reglas** |

El último caso confirma que la enumeración de reglas escala correctamente a funciones
profundamente anidadas.

---

## 6. Conclusión

La aplicación se sustenta en tres pilares:

1. **Matemático:** el álgebra de derivadas y las derivadas de las funciones elementales
   (sección 2), que garantizan que el método es exacto y completo para el alcance definido.
2. **Lógico:** la representación de toda función como árbol de expresión y la
   correspondencia biunívoca entre tipos de nodo y reglas de derivación (sección 3), que
   convierte el "explicar el procedimiento" en un simple recorrido del árbol, demostrablemente
   correcto.
3. **Técnico:** una implementación segura y robusta, empaquetada como aplicación de
   escritorio autónoma.

De este modo, la calculadora no solo *entrega* la derivada, sino que *justifica* cada paso
con el mismo rigor con que se enseña el cálculo diferencial.
