# derivador.py - Motor de derivación proyecto
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
_NOMBRES_PERMITIDOS = [
    'sin', 'cos', 'tan', 'cot', 'sec', 'csc',
    'asin', 'acos', 'atan', 'acot',
    'sinh', 'cosh', 'tanh',
    'exp', 'log', 'ln', 'sqrt', 'cbrt', 'root', 'Abs', 'factorial',
    'pi', 'E',
]
_PERMITIDAS = {n: getattr(sp, n) for n in _NOMBRES_PERMITIDOS if hasattr(sp, n)}
# Alias en español/latino: si el alumno ESCRIBE la notación de clase, también sirve.
_ALIAS = {
    'sen': sp.sin, 'senh': sp.sinh,
    'arcsen': sp.asin, 'arccos': sp.acos, 'arctan': sp.atan, 'arctg': sp.atan,
    'tg': sp.tan, 'ctg': sp.cot, 'cotg': sp.cot,
    'abs': sp.Abs,
    'e': sp.E,  # 'e' minúscula = número de Euler (no una variable)
}
_PERMITIDAS.update(_ALIAS)
# convert_xor: ^ -> potencia | implicit_multiplication: 45x -> 45*x, 2(x+1) -> 2*(x+1)
_TRANSF = standard_transformations + (convert_xor, implicit_multiplication)

# Namespace global mínimo: solo los constructores que necesitan las
# transformaciones + builtins vacío (bloquea __import__ y demás). NO incluye
# funciones peligrosas (integrate, solve...), que así se vuelven símbolos inertes.
_GLOBALS = {
    '__builtins__': {},
    'Symbol': sp.Symbol, 'Integer': sp.Integer,
    'Float': sp.Float, 'Rational': sp.Rational,
    # necesarios para el parseo sin evaluar (evaluate=False)
    'Add': sp.Add, 'Mul': sp.Mul, 'Pow': sp.Pow,
}

# Solo se permiten estos caracteres en la entrada (bloquea unicode, comillas,
# guion bajo, dos puntos, %, corchetes... es decir, casi todos los ataques).
_CHARS_OK = re.compile(r'^[A-Za-z0-9 \t.,+\-*/^()!]*$')
_MAX_LEN = 300

# Funciones aceptables en el RESULTADO (derivadas de funciones elementales).
# Si la derivada contiene otra cosa (gamma, polygamma, zeta...), se rechaza.
_SALIDA_OK = tuple(
    getattr(sp, n) for n in
    ['sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'asin', 'acos', 'atan', 'acot',
     'sinh', 'cosh', 'tanh', 'coth', 'exp', 'log', 'Abs', 'sign']
    if hasattr(sp, n)
)
# Funciones que aparecen cuando el resultado sale del dominio REAL (valores complejos)
_COMPLEJAS = tuple(
    getattr(sp, n) for n in ['re', 'im', 'arg', 'conjugate', 'atan2']
    if hasattr(sp, n)
)


def _parsear(texto, evaluate=True):
    return parse_expr(texto, local_dict=_PERMITIDAS,
                      global_dict=_GLOBALS,
                      transformations=_TRANSF, evaluate=evaluate)


def _fallo(mensaje, tipo='error'):
    # tipo: 'error' (algo mal escrito, se explica) | 'indeterminacion' (no definida)
    return {'funcion_original': None, 'derivada': None, 'reglas': [],
            'variable': None, 'exito': False, 'error': mensaje, 'tipo': tipo}


def _es_segura(expr):
    """Rechaza expresiones que materializarían números gigantes (DoS): torres de
    potencias (9**9**9), potencias/factoriales/enteros enormes. Solo revisa la
    ESTRUCTURA (forma cruda sin evaluar); nunca materializa el número."""
    for nodo in sp.preorder_traversal(expr):
        if isinstance(nodo, sp.Integer) and len(str(abs(int(nodo)))) > 7:
            return False
        if isinstance(nodo, sp.Pow):
            base, exponente = nodo.args
            if not base.free_symbols and not exponente.free_symbols:
                base_ok = bool(base.is_number) and bool(base.is_Atom)
                exp_ok = (
                    (isinstance(exponente, sp.Integer) and abs(int(exponente)) <= 64)
                    or (isinstance(exponente, sp.Rational)
                        and not isinstance(exponente, sp.Integer)
                        and abs(exponente.p) <= 64 and exponente.q <= 64)
                )
                if not (base_ok and exp_ok):
                    return False
        if isinstance(nodo, sp.factorial):
            arg = nodo.args[0]
            if not arg.free_symbols:
                if not (isinstance(arg, sp.Integer) and abs(int(arg)) <= 5000):
                    return False
    return True


# Derivada conocida de cada función elemental (clave = nombre de clase SymPy)
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
    x = sp.Symbol(variable)

    # Si no depende de la variable, es una constante
    if x not in expresion.free_symbols:
        return ["Regla de la constante: la derivada de una constante es 0"]

    # Caso base: la propia variable
    if expresion == x:
        return ["Derivada de la variable: d/dx(x) = 1"]

    reglas = []
    vistas = set()

    def agregar(clave, texto):
        if clave not in vistas:
            vistas.add(clave)
            reglas.append(texto)

    for nodo in sp.preorder_traversal(expresion):
        if isinstance(nodo, sp.Add):
            agregar('suma', "Regla de la suma/resta: se deriva término a término")

        elif isinstance(nodo, sp.Mul):
            num_var, den_var = [], []
            const_no_trivial = False
            for factor in nodo.args:
                if x not in factor.free_symbols:
                    if factor.is_number and abs(factor) != 1:
                        const_no_trivial = True
                elif isinstance(factor, sp.Pow) and factor.exp.is_number and factor.exp.is_negative:
                    den_var.append(factor)
                else:
                    num_var.append(factor)
            if den_var and num_var:
                agregar('cociente', "Regla del cociente: (u/v)′ = (u′·v − u·v′)/v²")
            if len(num_var) >= 2:
                agregar('producto', "Regla del producto: (u·v)′ = u′·v + u·v′")
            if const_no_trivial and (num_var or den_var):
                agregar('const', "Regla del múltiplo constante: (c·u)′ = c·u′")

        elif isinstance(nodo, sp.Pow):
            base, exponente = nodo.args
            base_dep = x in base.free_symbols
            exp_dep = x in exponente.free_symbols
            # Exponente fraccionario => raíz (Y también regla de la potencia).
            es_frac = (base_dep and not exp_dep
                       and exponente.is_rational is True
                       and exponente.is_integer is False)
            if es_frac:
                agregar('raiz', "Regla de la raíz: un exponente fraccionario es una raíz "
                                "(u^(1/n) es la raíz n-ésima de u); se combina con la regla de la potencia")
                agregar('potencia', "Regla de la potencia: d/dx[u^r] = r·u^(r−1)·u′ "
                                    "(vale también para exponentes fraccionarios y negativos)")
            elif exponente.is_number and base_dep and not exp_dep:
                agregar('potencia', "Regla de la potencia: d/dx[u^n] = n·u^(n−1)·u′")
            elif exp_dep and not base_dep:
                agregar('exponencial', "Regla exponencial: d/dx[a^u] = a^u·ln(a)·u′")
            elif base_dep and exp_dep:
                agregar('pot_general', "Derivación logarítmica: d/dx[u^v] combina potencia y exponencial")

        elif isinstance(nodo, sp.Function) and x in nodo.free_symbols:
            nombre = type(nodo).__name__
            if nombre in REGLAS_FUNCION:
                agregar('fn_' + nombre, REGLAS_FUNCION[nombre])
            else:
                agregar('fn_' + nombre, f"Derivada de la función {nombre}: se aplica su "
                                        "derivada específica junto con la regla de la cadena")

    # Regla de la cadena: alguna composición cuyo argumento interno no es solo la variable
    for nodo in sp.preorder_traversal(expresion):
        if isinstance(nodo, sp.Function):
            if any((x in a.free_symbols and a != x) for a in nodo.args):
                agregar('cadena', "Regla de la cadena: d/dx[f(g(x))] = f′(g(x))·g′(x) (se aplica en cada composición)")
                break
        elif isinstance(nodo, sp.Pow):
            base, exponente = nodo.args
            if (x in base.free_symbols and base != x) or (x in exponente.free_symbols and exponente != x):
                agregar('cadena', "Regla de la cadena: d/dx[f(g(x))] = f′(g(x))·g′(x) (se aplica en cada composición)")
                break

    if not reglas:
        reglas.append("Derivada directa: la expresión es lineal; su derivada es una constante")
    return reglas


def derivar(funcion_str):
    """Calcula la derivada de forma SEGURA: valida la entrada, bloquea código y
    números gigantes, detecta la variable y devuelve un diccionario. NUNCA lanza."""
    texto = funcion_str.strip()

    if not texto:
        return _fallo("Escribe una función para derivar.")
    if len(texto) > _MAX_LEN:
        return _fallo("La función es demasiado larga. Escribe una expresión más corta.")
    if not _CHARS_OK.match(texto):
        return _fallo("Usa solo letras, números y operadores matemáticos "
                      "( + − × ÷ ^ ( ) , ! ). Evita otros símbolos.")

    # 1) Parseo crudo (sin evaluar) para revisar seguridad sin materializar nada
    try:
        cruda = _parsear(texto, evaluate=False)
    except Exception:
        return _fallo("No pude interpretar la función. Revisa los paréntesis y usa "
                      "el botón ^ (o **) para las potencias, por ejemplo x^2.")
    if not _es_segura(cruda):
        return _fallo("Esa expresión es demasiado grande para calcular "
                      "(números o potencias enormes). Usa valores más pequeños.")

    # 2) Parseo evaluado
    try:
        funcion = _parsear(texto, evaluate=True)
    except Exception:
        return _fallo("No pude interpretar la función. Revisa que esté completa "
                      "y bien escrita (cada función con su argumento).")

    # 3) Valores no definidos (división por cero, etc.) => INDETERMINACIÓN
    if funcion.has(sp.zoo, sp.nan, sp.oo, sp.S.NegativeInfinity):
        return _fallo("La función lleva a una indeterminación (por ejemplo una división por cero).",
                      tipo='indeterminacion')

    # 4) Variable(s)
    variables = sorted(funcion.free_symbols, key=lambda s: s.name)
    if len(variables) > 1:
        nombres = ', '.join(s.name for s in variables)
        return _fallo(f"Detecté varias variables ({nombres}). Esta calculadora deriva "
                      "funciones de UNA sola variable; escribe la función usando solo "
                      "una (por ejemplo, x).")

    # Constante compleja (fuera del dominio real): p. ej. arcsen(2), log(-1)
    if not variables and funcion.is_real is False:
        return _fallo("Esa función no está definida en los números reales "
                      "(da un valor complejo).")

    variable = variables[0] if variables else symbols('x')
    var_real = sp.Symbol(variable.name, real=True)

    # 5) Derivar
    try:
        derivada = diff(funcion.subs(variable, var_real), var_real)
    except Exception:
        return _fallo("No pude calcular la derivada de esa función.")

    # 6) Resultado no elemental / fuera del dominio real
    if derivada.has(sp.Derivative):
        return _fallo("No puedo derivar esa función de forma exacta "
                      "(no es una función elemental soportada).")
    funcs_salida = derivada.atoms(sp.Function)
    if any(isinstance(f, _COMPLEJAS) for f in funcs_salida):
        return _fallo("Esta función toma valores complejos: sale del dominio de los "
                      "números reales (por ejemplo, el arcoseno de un valor mayor que 1). "
                      "Esta calculadora trabaja solo con funciones reales.")
    if any(not isinstance(f, _SALIDA_OK) for f in funcs_salida):
        return _fallo("Esa función involucra funciones avanzadas fuera del alcance de "
                      "esta calculadora (por ejemplo, el factorial de una variable).")
    if derivada.has(sp.zoo, sp.nan, sp.oo, sp.S.NegativeInfinity):
        return _fallo("La derivada lleva a una indeterminación (por ejemplo una división por cero).",
                      tipo='indeterminacion')

    # 7) Reglas: si la derivada es 0, la función equivale a una constante;
    #    si no, se identifican sobre la forma cruda (tal como se escribió).
    if derivada == 0:
        reglas = ["Regla de la constante: la derivada de una constante es 0"]
    else:
        reglas = identificar_reglas(cruda, variable.name)

    return {
        'funcion_original': funcion,
        'derivada': derivada,
        'reglas': reglas,
        'variable': variable.name,
        'exito': True,
        'error': None,
        'tipo': 'ok',
    }


if __name__ == "__main__":
    print("=" * 50)
    print("   CALCULADORA DE DERIVADAS")
    print("=" * 50)
    print("Escribe la función que quieras derivar.")
    print("Ejemplos: x**2 , sin(x) , x**2 * sin(x) , exp(x)")
    print("Escribe 'salir' para terminar.")
    print("-" * 50)

    while True:
        funcion_str = input("\nIngresa tu función: ")
        if funcion_str.lower() == "salir":
            print("¡Hasta luego!")
            break
        resultado = derivar(funcion_str)
        if resultado['exito']:
            print(f"Función original: {resultado['funcion_original']}")
            print(f"Derivada:         {resultado['derivada']}")
            print(f"Reglas usadas:    {', '.join(resultado['reglas'])}")
        else:
            print(f"Error: {resultado['error']}")
