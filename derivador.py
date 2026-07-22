# derivador.py - Motor de derivación proyecto
# Este programa recibe una función matemática escrita como texto (por ejemplo "x^2 + sin(x)")
# y calcula su derivada, además de explicar qué reglas de derivación se usaron.
# Está pensado para que lo use un estudiante, así que el texto puede venir de cualquier
# persona (input no confiable), por eso hay tantas validaciones de seguridad.

import re
import sympy as sp
from sympy import symbols, diff
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, convert_xor, implicit_multiplication
)

# ---------------------------------------------------------------------------
# PARSER SEGURO
# `sympify` evalúa la entrada con el namespace completo de Python/SymPy, lo que
# permite ejecución de código (`__import__(...)`) y colgar la app con números
# gigantes. Usamos parse_expr con una LISTA BLANCA de funciones, sin builtins,
# y los nombres desconocidos se vuelven símbolos (no funciones peligrosas).
# ---------------------------------------------------------------------------

# Lista de nombres de funciones matemáticas que SÍ se permiten usar en la entrada.
# Cualquier cosa que no esté en esta lista (o en los alias de más abajo) no se
# reconoce como función, sino que sympy la trata como un símbolo cualquiera
# (una letra), así que no hay riesgo de que se ejecute código arbitrario.
_NOMBRES_PERMITIDOS = [
    'sin', 'cos', 'tan', 'cot', 'sec', 'csc',
    'asin', 'acos', 'atan', 'acot',
    'sinh', 'cosh', 'tanh',
    'exp', 'log', 'ln', 'sqrt', 'cbrt', 'root', 'Abs', 'factorial',
    'pi', 'E',
]
# Se arma un diccionario {nombre: función real de sympy} solo con los nombres
# de la lista de arriba que realmente existen en sympy (por si algún nombre
# no está disponible en la versión instalada, no revienta el programa).
_PERMITIDAS = {n: getattr(sp, n) for n in _NOMBRES_PERMITIDOS if hasattr(sp, n)}

# Alias en español/latino: si el alumno ESCRIBE la notación de clase, también sirve.
# Por ejemplo "sen(x)" en vez de "sin(x)", o "tg(x)" en vez de "tan(x)".
_ALIAS = {
    'sen': sp.sin, 'senh': sp.sinh,
    'arcsen': sp.asin, 'arccos': sp.acos, 'arctan': sp.atan, 'arctg': sp.atan,
    'tg': sp.tan, 'ctg': sp.cot, 'cotg': sp.cot,
    'abs': sp.Abs,
    'e': sp.E,  # 'e' minúscula = número de Euler (no una variable)
}
# Se juntan los alias con las funciones permitidas, en el mismo diccionario.
_PERMITIDAS.update(_ALIAS)

# convert_xor: convierte el símbolo ^ en potencia (para que x^2 se entienda como x**2).
# implicit_multiplication: permite escribir 45x como 45*x, o 2(x+1) como 2*(x+1),
# es decir, multiplicación "implícita" sin poner el asterisco.
_TRANSF = standard_transformations + (convert_xor, implicit_multiplication)

# Namespace global mínimo que se le pasa al parser. Solo incluye los constructores
# que sympy necesita internamente para armar la expresión (Symbol, Integer, etc.)
# más los builtins VACÍOS. Poner __builtins__ vacío es lo que bloquea que alguien
# meta cosas como __import__('os') y ejecute código del sistema. Como no incluye
# funciones peligrosas de sympy (integrate, solve, etc.), esos nombres quedan
# como símbolos inofensivos si alguien los escribe.
_GLOBALS = {
    '__builtins__': {},
    'Symbol': sp.Symbol, 'Integer': sp.Integer,
    'Float': sp.Float, 'Rational': sp.Rational,
    # necesarios para el parseo sin evaluar (evaluate=False)
    'Add': sp.Add, 'Mul': sp.Mul, 'Pow': sp.Pow,
}

# Expresión regular que define qué caracteres se aceptan en el texto de entrada.
# Solo letras, números, espacios, tabs, y los símbolos matemáticos básicos.
# Esto bloquea unicode raro, comillas, guion bajo, dos puntos, %, corchetes, etc,
# que es justo lo que se necesitaría para intentar un ataque de código.
_CHARS_OK = re.compile(r'^[A-Za-z0-9 \t.,+\-*/^()!]*$')
# Límite de longitud del texto, para que nadie mande una expresión gigantesca.
_MAX_LEN = 300

# Funciones que se consideran aceptables dentro del RESULTADO de la derivada
# (son derivadas típicas de funciones elementales de nivel escolar).
# Si al derivar aparece algo que no está en esta lista (por ejemplo gamma,
# polygamma, zeta...), se rechaza el resultado porque se sale del alcance
# de la calculadora.
_SALIDA_OK = tuple(
    getattr(sp, n) for n in
    ['sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'asin', 'acos', 'atan', 'acot',
     'sinh', 'cosh', 'tanh', 'coth', 'exp', 'log', 'Abs', 'sign']
    if hasattr(sp, n)
)
# Funciones que aparecen cuando el resultado se sale del dominio de los números
# reales (o sea, quedó en números complejos). Si aparecen, se rechaza el resultado
# porque esta calculadora trabaja solo con números reales.
_COMPLEJAS = tuple(
    getattr(sp, n) for n in ['re', 'im', 'arg', 'conjugate', 'atan2']
    if hasattr(sp, n)
)


def _parsear(texto, evaluate=True):
    # Función auxiliar que arma la expresión de sympy a partir del texto,
    # usando siempre la lista blanca de nombres, el namespace restringido,
    # y las transformaciones definidas arriba (^ como potencia, etc).
    # evaluate=False sirve para obtener la expresión "cruda", tal como se
    # escribió, sin que sympy la simplifique todavía.
    return parse_expr(texto, local_dict=_PERMITIDAS,
                      global_dict=_GLOBALS,
                      transformations=_TRANSF, evaluate=evaluate)


def _fallo(mensaje, tipo='error'):
    # Atajo para armar el diccionario de respuesta cuando algo salió mal.
    # tipo: 'error' (algo mal escrito, se explica al usuario) |
    #       'indeterminacion' (la función no está definida matemáticamente,
    #       por ejemplo una división por cero).
    return {'funcion_original': None, 'derivada': None, 'reglas': [],
            'variable': None, 'exito': False, 'error': mensaje, 'tipo': tipo}


def _es_segura(expr):
    """Rechaza expresiones que materializarían números gigantes (DoS): torres de
    potencias (9**9**9), potencias/factoriales/enteros enormes. Solo revisa la
    ESTRUCTURA (forma cruda sin evaluar); nunca materializa el número."""
    # Se recorre la expresión como un árbol, nodo por nodo (preorder_traversal
    # va bajando por cada rama de la expresión matemática).
    for nodo in sp.preorder_traversal(expr):
        # Si aparece un número entero directamente escrito con más de 7 dígitos,
        # se rechaza (por ejemplo si alguien escribe un número gigantesco a mano).
        if isinstance(nodo, sp.Integer) and len(str(abs(int(nodo)))) > 7:
            return False
        # Si el nodo es una potencia (base ** exponente)...
        if isinstance(nodo, sp.Pow):
            base, exponente = nodo.args
            # Solo interesa revisar cuando NI la base NI el exponente dependen
            # de ninguna variable (o sea, es un número puro elevado a otro número,
            # como 9**9**9), porque eso es lo que puede generar un número gigantesco.
            if not base.free_symbols and not exponente.free_symbols:
                base_ok = bool(base.is_number) and bool(base.is_Atom)
                # El exponente se permite si es un entero pequeño (hasta 64 en
                # valor absoluto) o una fracción razonable (numerador y
                # denominador hasta 64), para permitir cosas como raíces.
                exp_ok = (
                    (isinstance(exponente, sp.Integer) and abs(int(exponente)) <= 64)
                    or (isinstance(exponente, sp.Rational)
                        and not isinstance(exponente, sp.Integer)
                        and abs(exponente.p) <= 64 and exponente.q <= 64)
                )
                # Si la base o el exponente no cumplen esas condiciones, se
                # rechaza la expresión completa por ser potencialmente peligrosa.
                if not (base_ok and exp_ok):
                    return False
        # Si el nodo es un factorial de un número puro (sin variables), se
        # limita a que el número sea como máximo 5000, porque factoriales de
        # números grandes también generan resultados enormes.
        if isinstance(nodo, sp.factorial):
            arg = nodo.args[0]
            if not arg.free_symbols:
                if not (isinstance(arg, sp.Integer) and abs(int(arg)) <= 5000):
                    return False
    # Si no se encontró nada peligroso en todo el recorrido, la expresión es segura.
    return True


# Diccionario con la derivada conocida de cada función elemental, en texto,
# para poder mostrarle al usuario qué regla se aplicó. La clave es el nombre
# de la clase de sympy (por ejemplo 'sin' para seno).
REGLAS_FUNCION = {
    'sin': "Derivada del seno: d/dx[sen(u)] = cos(u)·u′",
    'cos': "Derivada del coseno: d/dx[cos(u)] = −sen(u)·u′",
    'tan': "Derivada de la tangente: d/dx[tan(u)] = sec²(u)·u′",
    'cot': "Derivada de la cotangente: d/dx[cot(u)] = −csc²(u)·u′",
    'sec': "Derivada de la secante: d/dx[sec(u)] = sec(u)·tan(u)·u′",
    'csc': "Derivada de la cosecante: d/dx[csc(u)] = −csc(u)·cot(u)·u′",
    'asin': "Derivada del arcoseno: d/dx[arcsen(u)] = u′/raíz(1−u²)",
    'acos': "Derivada del arcocoseno: d/dx[arccos(u)] = −u′/raíz(1−u²)",
    'atan': "Derivada del arcotangente: d/dx[arctan(u)] = u′/(1+u²)",
    'acot': "Derivada del arcocotangente: d/dx[arccot(u)] = −u′/(1+u²)",
    'sinh': "Derivada del seno hiperbólico: d/dx[senh(u)] = cosh(u)·u′",
    'cosh': "Derivada del coseno hiperbólico: d/dx[cosh(u)] = senh(u)·u′",
    'tanh': "Derivada de la tangente hiperbólica: d/dx[tanh(u)] = sech²(u)·u′",
    'exp': "Derivada de la exponencial natural: d/dx[e^u] = e^u·u′",
    'log': "Derivada del logaritmo: d/dx[ln(u)] = u′/u (en base a, dividir además entre ln a)",
    'Abs': "Derivada del valor absoluto: d/dx[|u|] = (u/|u|)·u′",
    'factorial': "Derivada del factorial: usa la función Gamma (tema avanzado)",
}


def identificar_reglas(expresion, variable='x'):
    """Recorre el árbol de la expresión (SymPy) e identifica, sin falsos
    positivos, todas las reglas de derivación involucradas."""
    # Se crea el símbolo de la variable (por defecto 'x') para poder comparar
    # si cada parte de la expresión depende de ella o no.
    x = sp.Symbol(variable)

    # Si la expresión completa no depende de la variable, entonces es una
    # constante y la única regla que aplica es la de la derivada de una constante.
    if x not in expresion.free_symbols:
        return ["Regla de la constante: la derivada de una constante es 0"]

    # Caso base: si la expresión ES directamente la variable (por ejemplo "x"),
    # la regla es la derivada de la variable, que da 1.
    if expresion == x:
        return ["Derivada de la variable: d/dx(x) = 1"]

    reglas = []
    vistas = set()  # guarda claves ya agregadas, para no repetir la misma regla

    def agregar(clave, texto):
        # Solo agrega la regla si todavía no se había agregado antes (evita duplicados)
        if clave not in vistas:
            vistas.add(clave)
            reglas.append(texto)

    # Se recorre todo el árbol de la expresión, nodo por nodo, buscando patrones
    # que indiquen qué reglas de derivación hacen falta.
    for nodo in sp.preorder_traversal(expresion):

        # Si el nodo es una suma (o resta), se necesita la regla de la suma.
        if isinstance(nodo, sp.Add):
            agregar('suma', "Regla de la suma/resta: se deriva término a término")

        # Si el nodo es una multiplicación...
        elif isinstance(nodo, sp.Mul):
            num_var, den_var = [], []
            const_no_trivial = False
            # Se recorren los factores de la multiplicación uno por uno
            for factor in nodo.args:
                if x not in factor.free_symbols:
                    # Si el factor es un número (no depende de x) y no es 1 o -1,
                    # se marca que hay una constante "de verdad" multiplicando.
                    if factor.is_number and abs(factor) != 1:
                        const_no_trivial = True
                elif isinstance(factor, sp.Pow) and factor.exp.is_number and factor.exp.is_negative:
                    # Si el factor es algo elevado a un exponente negativo (o sea,
                    # está "dividiendo"), se cuenta como parte del denominador.
                    den_var.append(factor)
                else:
                    # Si depende de x y no es un exponente negativo, es parte del numerador.
                    num_var.append(factor)
            # Si hay algo en el numerador Y algo en el denominador, es una división,
            # entonces se necesita la regla del cociente.
            if den_var and num_var:
                agregar('cociente', "Regla del cociente: (u/v)′ = (u′·v − u·v′)/v²")
            # Si hay dos o más factores que dependen de x multiplicándose entre sí,
            # se necesita la regla del producto.
            if len(num_var) >= 2:
                agregar('producto', "Regla del producto: (u·v)′ = u′·v + u·v′")
            # Si además de eso hay una constante no trivial multiplicando, se
            # necesita también la regla del múltiplo constante.
            if const_no_trivial and (num_var or den_var):
                agregar('const', "Regla del múltiplo constante: (c·u)′ = c·u′")

        # Si el nodo es una potencia (base ** exponente)...
        elif isinstance(nodo, sp.Pow):
            base, exponente = nodo.args
            base_dep = x in base.free_symbols       # ¿la base depende de x?
            exp_dep = x in exponente.free_symbols    # ¿el exponente depende de x?

            # Caso especial: exponente fraccionario (por ejemplo x^(1/2)), que en
            # realidad es una raíz. Se marca tanto la regla de la raíz como la de
            # la potencia, porque van de la mano.
            es_frac = (base_dep and not exp_dep
                       and exponente.is_rational is True
                       and exponente.is_integer is False)
            if es_frac:
                agregar('raiz', "Regla de la raíz: un exponente fraccionario es una raíz "
                                "(u^(1/n) es la raíz n-ésima de u); se combina con la regla de la potencia")
                agregar('potencia', "Regla de la potencia: d/dx[u^r] = r·u^(r−1)·u′ "
                                    "(vale también para exponentes fraccionarios y negativos)")
            # Caso normal: la base depende de x y el exponente es un número fijo
            # (por ejemplo x^2, x^3). Se aplica la regla de la potencia normal.
            elif exponente.is_number and base_dep and not exp_dep:
                agregar('potencia', "Regla de la potencia: d/dx[u^n] = n·u^(n−1)·u′")
            # Caso donde el exponente depende de x pero la base es un número fijo
            # (por ejemplo 2^x). Es la regla exponencial.
            elif exp_dep and not base_dep:
                agregar('exponencial', "Regla exponencial: d/dx[a^u] = a^u·ln(a)·u′")
            # Caso donde TANTO la base como el exponente dependen de x (por
            # ejemplo x^x). Hace falta derivación logarítmica.
            elif base_dep and exp_dep:
                agregar('pot_general', "Derivación logarítmica: d/dx[u^v] combina potencia y exponencial")

        # Si el nodo es una función matemática (seno, coseno, etc) que depende de x...
        elif isinstance(nodo, sp.Function) and x in nodo.free_symbols:
            nombre = type(nodo).__name__
            if nombre in REGLAS_FUNCION:
                # Si está en el diccionario de reglas conocidas, se agrega esa explicación.
                agregar('fn_' + nombre, REGLAS_FUNCION[nombre])
            else:
                # Si es una función que no está en el diccionario (caso raro),
                # se agrega un mensaje genérico.
                agregar('fn_' + nombre, f"Derivada de la función {nombre}: se aplica su "
                                        "derivada específica junto con la regla de la cadena")

    # Segunda pasada por el árbol: detectar si hace falta la regla de la cadena.
    # Esto pasa cuando hay una función compuesta, es decir, una función cuyo
    # argumento no es simplemente "x" solo, sino otra expresión que también
    # depende de x (por ejemplo sin(x^2), donde adentro del seno no está x solo).
    for nodo in sp.preorder_traversal(expresion):
        if isinstance(nodo, sp.Function):
            # Si algún argumento de la función depende de x pero no es x mismo,
            # es una composición de funciones, así que aplica la regla de la cadena.
            if any((x in a.free_symbols and a != x) for a in nodo.args):
                agregar('cadena', "Regla de la cadena: d/dx[f(g(x))] = f′(g(x))·g′(x) (se aplica en cada composición)")
                break
        elif isinstance(nodo, sp.Pow):
            # Lo mismo pero para potencias: si la base o el exponente son algo
            # más complejo que "x" solo, también hace falta la regla de la cadena.
            base, exponente = nodo.args
            if (x in base.free_symbols and base != x) or (x in exponente.free_symbols and exponente != x):
                agregar('cadena', "Regla de la cadena: d/dx[f(g(x))] = f′(g(x))·g′(x) (se aplica en cada composición)")
                break

    # Si después de todo el recorrido no se encontró ninguna regla (por ejemplo
    # la expresión es algo simple como "3*x"), se pone un mensaje genérico.
    if not reglas:
        reglas.append("Derivada directa: la expresión es lineal; su derivada es una constante")
    return reglas


def derivar(funcion_str):
    """Calcula la derivada de forma SEGURA: valida la entrada, bloquea código y
    números gigantes, detecta la variable y devuelve un diccionario. NUNCA lanza."""

    # Se limpian espacios sobrantes al principio y al final del texto.
    texto = funcion_str.strip()

    # --- Validaciones básicas de la entrada, antes de intentar interpretar nada ---

    if not texto:
        return _fallo("Escribe una función para derivar.")
    if len(texto) > _MAX_LEN:
        return _fallo("La función es demasiado larga. Escribe una expresión más corta.")
    if not _CHARS_OK.match(texto):
        # Si el texto tiene algún carácter fuera de la lista permitida, se rechaza
        # de una, sin ni siquiera intentar parsearlo.
        return _fallo("Usa solo letras, números y operadores matemáticos "
                      "( + − × ÷ ^ ( ) , ! ). Evita otros símbolos.")

    # 1) Parseo crudo (sin evaluar) para revisar seguridad sin materializar nada.
    # Se usa evaluate=False para que sympy NO simplifique ni calcule nada todavía,
    # así se puede revisar la estructura antes de que se generen números gigantes.
    try:
        cruda = _parsear(texto, evaluate=False)
    except Exception:
        # Si el texto no se puede interpretar como expresión matemática (paréntesis
        # mal puestos, etc), se devuelve un mensaje de error amigable.
        return _fallo("No pude interpretar la función. Revisa los paréntesis y usa "
                      "el botón ^ (o **) para las potencias, por ejemplo x^2.")
    # Se revisa con la función de seguridad si la expresión cruda es peligrosa
    # (torres de potencias, factoriales enormes, etc).
    if not _es_segura(cruda):
        return _fallo("Esa expresión es demasiado grande para calcular "
                      "(números o potencias enormes). Usa valores más pequeños.")

    # 2) Ahora sí, parseo evaluado: se deja que sympy simplifique la expresión
    # normalmente, ya con la garantía de que es segura.
    try:
        funcion = _parsear(texto, evaluate=True)
    except Exception:
        return _fallo("No pude interpretar la función. Revisa que esté completa "
                      "y bien escrita (cada función con su argumento).")

    # 3) Se revisa si la función en sí misma ya da algo indefinido, como infinito
    # o "zoo" (que en sympy representa una división por cero / infinito complejo).
    if funcion.has(sp.zoo, sp.nan, sp.oo, sp.S.NegativeInfinity):
        return _fallo("La función lleva a una indeterminación (por ejemplo una división por cero).",
                      tipo='indeterminacion')

    # 4) Se detectan las variables presentes en la expresión (letras que no son
    # funciones ni constantes conocidas).
    variables = sorted(funcion.free_symbols, key=lambda s: s.name)
    if len(variables) > 1:
        # Esta calculadora solo deriva funciones de UNA variable, así que si
        # aparece más de una (por ejemplo x e y), se avisa al usuario.
        nombres = ', '.join(s.name for s in variables)
        return _fallo(f"Detecté varias variables ({nombres}). Esta calculadora deriva "
                      "funciones de UNA sola variable; escribe la función usando solo "
                      "una (por ejemplo, x).")

    # Si no hay ninguna variable (es una constante pura, como "log(-1)") y esa
    # constante da un número complejo, se rechaza porque no es un valor real.
    if not variables and funcion.is_real is False:
        return _fallo("Esa función no está definida en los números reales "
                      "(da un valor complejo).")

    # Si hay una variable, se usa esa; si no hay ninguna (función constante),
    # se usa 'x' por defecto solo para no romper el resto del código.
    variable = variables[0] if variables else symbols('x')
    # Se vuelve a crear el símbolo pero marcado explícitamente como "real",
    # para que sympy simplifique asumiendo que la variable toma valores reales
    # (esto evita que aparezcan resultados con valores absolutos o partes
    # imaginarias innecesarias).
    var_real = sp.Symbol(variable.name, real=True)

    # 5) Se calcula la derivada de verdad, usando diff de sympy.
    try:
        derivada = diff(funcion.subs(variable, var_real), var_real)
    except Exception:
        return _fallo("No pude calcular la derivada de esa función.")

    # 6) Revisiones sobre el RESULTADO de la derivada, antes de devolverlo:

    # Si sympy no pudo resolver del todo la derivada, deja una "Derivative" sin
    # calcular dentro del resultado; en ese caso se avisa que no se pudo derivar.
    if derivada.has(sp.Derivative):
        return _fallo("No puedo derivar esa función de forma exacta "
                      "(no es una función elemental soportada).")

    # Se revisan todas las funciones que aparecen en el resultado de la derivada.
    funcs_salida = derivada.atoms(sp.Function)

    # Si aparece alguna función relacionada a números complejos (re, im, arg...),
    # significa que el resultado se salió del dominio real.
    if any(isinstance(f, _COMPLEJAS) for f in funcs_salida):
        return _fallo("Esta función toma valores complejos: sale del dominio de los "
                      "números reales (por ejemplo, el arcoseno de un valor mayor que 1). "
                      "Esta calculadora trabaja solo con funciones reales.")

    # Si aparece alguna función que no está en la lista de funciones "aceptables"
    # como resultado (por ejemplo gamma, derivada de factorial, etc), se rechaza.
    if any(not isinstance(f, _SALIDA_OK) for f in funcs_salida):
        return _fallo("Esa función involucra funciones avanzadas fuera del alcance de "
                      "esta calculadora (por ejemplo, el factorial de una variable).")

    # Si el resultado de la derivada da una indeterminación (división por cero, etc).
    if derivada.has(sp.zoo, sp.nan, sp.oo, sp.S.NegativeInfinity):
        return _fallo("La derivada lleva a una indeterminación (por ejemplo una división por cero).",
                      tipo='indeterminacion')

    # 7) Se arma la lista de reglas usadas para explicarle al usuario cómo se
    # llegó al resultado. Si la derivada dio 0, significa que la función
    # original era básicamente una constante.
    if derivada == 0:
        reglas = ["Regla de la constante: la derivada de una constante es 0"]
    else:
        # Se identifican las reglas sobre la expresión "cruda" (tal cual la
        # escribió el usuario, sin simplificar), para que las reglas mostradas
        # coincidan con lo que el usuario realmente escribió.
        reglas = identificar_reglas(cruda, variable.name)

    # Se devuelve el diccionario final con todo el resultado, marcando éxito.
    return {
        'funcion_original': funcion,
        'derivada': derivada,
        'reglas': reglas,
        'variable': variable.name,
        'exito': True,
        'error': None,
        'tipo': 'ok',
    }


# Este bloque solo se ejecuta si el archivo se corre directamente desde la
# terminal (no si se importa desde otro archivo). Sirve como una pequeña
# interfaz de consola para probar la calculadora manualmente.
if __name__ == "__main__":
    print("=" * 50)
    print("   CALCULADORA DE DERIVADAS")
    print("=" * 50)
    print("Escribe la función que quieras derivar.")
    print("Ejemplos: x**2 , sin(x) , x**2 * sin(x) , exp(x)")
    print("Escribe 'salir' para terminar.")
    print("-" * 50)

    # Bucle infinito que sigue pidiendo funciones hasta que el usuario escriba "salir"
    while True:
        funcion_str = input("\nIngresa tu función: ")
        if funcion_str.lower() == "salir":
            print("¡Hasta luego!")
            break
        # Se llama a la función principal, que nunca lanza excepciones (siempre
        # devuelve un diccionario, ya sea de éxito o de error).
        resultado = derivar(funcion_str)
        if resultado['exito']:
            print(f"Función original: {resultado['funcion_original']}")
            print(f"Derivada:         {resultado['derivada']}")
            print(f"Reglas usadas:    {', '.join(resultado['reglas'])}")
        else:
            print(f"Error: {resultado['error']}")
