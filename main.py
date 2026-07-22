"""
main.py - Interfaz de escritorio para la Calculadora de Derivadas
Motor de cálculo: derivador.py
UI: PySide6, dirección de diseño EDITORIAL (revista de matemáticas),
    estilizada con style.qss + fuentes embebidas (Fraunces, IBM Plex Mono).
    Incluye un teclado matemático (numpad) que inserta sintaxis válida
    para evitar errores de tipeo.
"""
# Este archivo arma toda la ventana de la aplicación (la parte visual) usando
# PySide6, que es la librería para hacer interfaces gráficas con Python.
# El cálculo de la derivada en sí NO está acá, se hace en derivador.py;
# este archivo solo se encarga de mostrar los botones, cuadros de texto,
# y de tomar el resultado que devuelve derivador.py para pintarlo en pantalla.

import sys
import os
# Se importan los distintos widgets (elementos visuales) que se van a usar:
# ventanas, botones, cuadros de texto, layouts para acomodar cosas, etc.
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QPushButton, QLabel, QFrame, QScrollArea, QSizePolicy, QInputDialog
)
# Cosas relacionadas a fuentes, íconos e imágenes.
from PySide6.QtGui import QFontDatabase, QIcon, QFont, QPixmap
# Constantes generales de Qt (alineaciones, cursores, etc).
from PySide6.QtCore import Qt

# Se importa la función principal del motor de derivadas (el otro archivo).
from derivador import derivar


def _base_dir():
    # Como .exe (PyInstaller) los datos viven en sys._MEIPASS; en desarrollo,
    # junto a este archivo.
    # Esto sirve para que la app encuentre sus archivos (imágenes, fuentes, etc)
    # tanto si se está corriendo directamente con Python, como si ya se convirtió
    # en un .exe con PyInstaller (que guarda los archivos en una carpeta temporal
    # distinta).
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


# Carpeta base del proyecto y carpeta donde están los "assets" (imágenes, fuentes, etc)
BASE_DIR = _base_dir()
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# --- Teclado matemático: etiqueta visible -> (texto a insertar, cursor atrás) ---
# Este diccionario define qué botón corresponde a qué texto insertado en el
# cuadro de la función. El segundo valor de la tupla dice cuántos caracteres
# hay que mover el cursor hacia atrás después de insertar, para que quede
# el cursor DENTRO de los paréntesis (por ejemplo al tocar "sen" se inserta
# "sin()" y el cursor queda justo entre los paréntesis, listo para escribir).
INSERT_MAP = {
    "sen": ("sin()", 1), "cos": ("cos()", 1), "tan": ("tan()", 1),
    "arcsen": ("asin()", 1), "arccos": ("acos()", 1), "arctan": ("atan()", 1),
    "senh": ("sinh()", 1), "cosh": ("cosh()", 1), "tanh": ("tanh()", 1),
    "ln": ("log()", 1), "log10": ("log(,10)", 4), "exp": ("exp()", 1),
    "√": ("sqrt()", 1), "³√": ("cbrt()", 1), "n√": ("root(,)", 2),
    "^": ("**", 0), "π": ("pi", 0), "e": ("E", 0),
    "n!": ("factorial()", 1), "|x|": ("Abs()", 1),
    "x": ("x", 0), "(": ("(", 0), ")": (")", 0), ",": (",", 0),
    "+": ("+", 0), "−": ("-", 0), "×": ("*", 0), "÷": ("/", 0), ".": (".", 0),
}
# Se agregan también los dígitos del 0 al 9 al mismo diccionario, cada uno
# se inserta tal cual (sin mover el cursor).
for _d in "0123456789":
    INSERT_MAP[_d] = (_d, 0)

# Diccionario de textos de ayuda (tooltips) que aparecen al pasar el mouse
# sobre cada botón del teclado matemático, explicando qué hace cada uno.
TOOLTIPS = {
    "sen": "Seno", "cos": "Coseno", "tan": "Tangente",
    "arcsen": "Arcoseno (inversa del seno, sen⁻¹)", "arccos": "Arcocoseno (cos⁻¹)", "arctan": "Arcotangente (tan⁻¹)",
    "senh": "Seno hiperbólico", "cosh": "Coseno hiperbólico", "tanh": "Tangente hiperbólica",
    "ln": "Logaritmo natural (base e)", "log10": "Logaritmo base 10", "exp": "Exponencial e^x",
    "√": "Raíz cuadrada", "³√": "Raíz cúbica", "n√": "Raíz enésima: root(radicando, índice), p. ej. root(x,4)",
    "^": "Potencia, por ejemplo x^2", "π": "Número pi ≈ 3.1416",
    "e": "Número de Euler, e ≈ 2.718", "n!": "Factorial", "|x|": "Valor absoluto",
    "x": "Variable x", "DEL": "Borrar un carácter", "C": "Limpiar todo",
    "Derivar": "Calcular la derivada",
}

# Define cómo se acomodan los botones del teclado matemático, fila por fila.
# Cada sublista es una fila, y cada elemento de esa sublista es la etiqueta
# del botón que va en esa posición (columna).
NUMPAD_ROWS = [
    ["sen", "cos", "tan", "arcsen", "arccos", "arctan"],
    ["ln", "log10", "exp", "√", "³√", "n√"],
    ["^", "π", "e", "n!", "|x|", "x"],
    ["7", "8", "9", "(", ")", "DEL"],
    ["4", "5", "6", "+", "−", "C"],
    ["1", "2", "3", "×", "÷", "."],
    ["0", ","],  # + botón "Derivar" ocupando las 4 columnas restantes
]


def _mono_tracked(px, spacing):
    """Fuente IBM Plex Mono con tamaño en px y tracking (QSS no soporta letter-spacing)."""
    # Se arma un objeto QFont a mano porque el archivo de estilos (QSS) no
    # permite controlar el espaciado entre letras (letter-spacing), así que
    # eso se hace por código en vez de por CSS.
    f = QFont("IBM Plex Mono")
    f.setPixelSize(px)
    f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f


def _formato_matematico(expr):
    """Cosmética de la fórmula para lectura tipo libro: ** -> ^ y * -> ·"""
    # Sympy escribe las potencias como ** y las multiplicaciones como *.
    # Para que se vea más como en un libro de matemáticas, se reemplaza
    # ** por ^ y * por el punto de multiplicación (·).
    return str(expr).replace("**", "^").replace("*", "·")


# Clase principal: representa toda la ventana de la aplicación.
# Hereda de QMainWindow, que es la clase base de Qt para ventanas con
# menús, barra de título, etc.
class DerivadoraWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Título de la ventana (aparece en la barra de título del sistema operativo).
        self.setWindowTitle("Calculadora de Derivadas")
        # Tamaño mínimo permitido y tamaño inicial de la ventana.
        self.setMinimumSize(560, 600)
        self.resize(640, 900)

        # Si existe el archivo del ícono, se lo asigna a la ventana.
        icon_path = os.path.join(ASSETS_DIR, "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Se arma toda la interfaz (todos los widgets) en un método aparte.
        self._build_ui()

    def _build_ui(self):
        # Área con scroll para que quepa en pantallas pequeñas.
        # Esto envuelve todo el contenido en un contenedor con barra de
        # desplazamiento, por si la ventana queda más chica que el contenido.
        scroll = QScrollArea()
        scroll.setObjectName("scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        # "central" es el widget que contiene TODO lo demás; se pone dentro
        # del área de scroll, y ese scroll se pone como el widget central
        # de la ventana principal.
        central = QWidget()
        central.setObjectName("central")
        central.setAttribute(Qt.WA_StyledBackground, True)
        scroll.setWidget(central)
        self.setCentralWidget(scroll)

        # Layout vertical principal: todo se va acomodando de arriba hacia abajo.
        root = QVBoxLayout(central)
        root.setContentsMargins(40, 32, 40, 32)  # márgenes alrededor de todo el contenido
        root.setSpacing(0)

        # --- Encabezado: wordmark d/dx + kicker ---
        # "wordmark" es el logo/título estilizado "d/dx", y "kicker" es el
        # textito pequeño de arriba a la derecha ("CÁLCULO · DIFERENCIAL").
        header = QHBoxLayout()
        wordmark = QLabel("d/dx")
        wordmark.setObjectName("wordmark")
        header.addWidget(wordmark)
        header.addStretch(1)  # empuja lo siguiente hacia la derecha
        kicker = QLabel("CÁLCULO · DIFERENCIAL")
        kicker.setObjectName("kicker")
        kicker.setFont(_mono_tracked(11, 2.0))
        kicker.setAlignment(Qt.AlignBottom)
        header.addWidget(kicker)
        root.addLayout(header)

        # Línea horizontal gruesa debajo del encabezado, típica de diseño editorial.
        rule = QFrame()
        rule.setObjectName("ruleStrong")
        rule.setFixedHeight(2)
        root.addSpacing(10)
        root.addWidget(rule)
        root.addSpacing(24)

        # --- 01 · FUNCIÓN ---
        # Sección donde el usuario escribe la función que quiere derivar.
        root.addWidget(self._tag("01 · FUNCIÓN"))
        root.addSpacing(8)

        # Cuadro de texto donde se escribe la función.
        self.funcion_input = QLineEdit()
        self.funcion_input.setObjectName("funcionInput")
        self.funcion_input.setPlaceholderText("x^2 * sen(x)")
        # Si el usuario aprieta Enter dentro del cuadro, se calcula la derivada.
        self.funcion_input.returnPressed.connect(self.calcular)
        # Al editar la función (teclado o numpad) se descarta el resultado anterior,
        # para que sea obvio que hay que volver a derivar (nuevo proceso).
        self.funcion_input.textChanged.connect(self._al_editar)
        root.addWidget(self.funcion_input)

        root.addSpacing(6)
        # Etiqueta que muestra la función tal cual se escribió, ya con formato
        # bonito (con ^ y ·), justo debajo del cuadro de texto.
        self.interpreted_label = QLabel("")
        self.interpreted_label.setObjectName("interpretedLine")
        self.interpreted_label.setWordWrap(True)
        root.addWidget(self.interpreted_label)

        # --- Teclado matemático ---
        root.addSpacing(16)
        root.addWidget(self._tag("TECLADO MATEMÁTICO"))
        root.addSpacing(8)
        root.addWidget(self._build_numpad())

        root.addSpacing(30)

        # --- 02 · DERIVADA ---
        # Sección donde se muestra el resultado de la derivada.
        root.addWidget(self._tag("02 · DERIVADA"))
        root.addSpacing(12)
        self.derivada_label = QLabel("—")  # guion mientras no hay resultado
        self.derivada_label.setObjectName("derivada")
        self.derivada_label.setWordWrap(True)
        root.addWidget(self.derivada_label)
        root.addSpacing(6)
        # Etiqueta que dice "derivada respecto a x" (o la variable que sea).
        self.respecto_label = QLabel("")
        self.respecto_label.setObjectName("interpretedLine")
        root.addWidget(self.respecto_label)

        # Imagen que aparece en las indeterminaciones (meme del usuario).
        # Se prepara acá el QLabel que va a mostrar la imagen, pero empieza
        # oculto (solo se muestra cuando el resultado es una indeterminación).
        self.imagen_label = QLabel()
        self.imagen_label.setObjectName("imagenResultado")
        self.imagen_label.setAlignment(Qt.AlignCenter)
        self._pixmap_indeterminacion = QPixmap()
        _img_path = os.path.join(ASSETS_DIR, "indeterminacion.png")
        # Si el archivo de la imagen existe, se carga y se escala a un ancho fijo.
        if os.path.exists(_img_path):
            self._pixmap_indeterminacion = QPixmap(_img_path).scaledToWidth(
                380, Qt.SmoothTransformation
            )
        self.imagen_label.setPixmap(self._pixmap_indeterminacion)
        self.imagen_label.hide()
        root.addWidget(self.imagen_label)

        root.addSpacing(30)

        # --- 03 · REGLAS APLICADAS ---
        # Sección donde se listan, una por una, las reglas de derivación usadas.
        root.addWidget(self._tag("03 · REGLAS APLICADAS"))
        root.addSpacing(4)
        reglas_box = QWidget()
        self.reglas_layout = QVBoxLayout(reglas_box)
        self.reglas_layout.setContentsMargins(0, 0, 0, 0)
        self.reglas_layout.setSpacing(0)
        root.addWidget(reglas_box)

        root.addSpacing(18)

        # --- Línea de error ---
        # Acá se muestra el mensaje de error si algo salió mal al derivar.
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLine")
        self.error_label.setWordWrap(True)
        root.addWidget(self.error_label)

        # Espacio elástico al final, para que todo el contenido quede pegado
        # arriba y no se estire raro si la ventana es más alta que el contenido.
        root.addStretch(1)

    def _tag(self, texto):
        # Método auxiliar para crear las etiquetas tipo "01 · FUNCIÓN" que
        # aparecen como títulos de cada sección, con la fuente monoespaciada
        # y el espaciado entre letras que se ve en revistas.
        lbl = QLabel(texto)
        lbl.setObjectName("sectionTag")
        lbl.setFont(_mono_tracked(11, 2.0))
        return lbl

    def _build_numpad(self):
        # Arma el teclado matemático como una grilla (filas y columnas) de botones,
        # usando la lista NUMPAD_ROWS definida arriba.
        box = QWidget()
        grid = QGridLayout(box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        # Hace que las 6 columnas se repartan el espacio disponible por igual.
        for c in range(6):
            grid.setColumnStretch(c, 1)

        # Recorre cada fila y cada botón dentro de esa fila, y los va
        # colocando en la posición (fila, columna) correspondiente de la grilla.
        for r, fila in enumerate(NUMPAD_ROWS):
            for c, etiqueta in enumerate(fila):
                grid.addWidget(self._mk_key(etiqueta), r, c)
        # "Derivar" ocupa el resto de la última fila (junto a 0 y ,).
        # Se coloca manualmente en la fila 6, empezando en la columna 2,
        # ocupando 1 fila y 4 columnas de ancho.
        grid.addWidget(self._mk_key("Derivar"), 6, 2, 1, 4)
        return box

    def _mk_key(self, etiqueta):
        # Crea un botón individual del teclado matemático, con su nombre de
        # objeto (para que el archivo de estilos QSS sepa cómo pintarlo según
        # el tipo de botón que sea).
        b = QPushButton(etiqueta)
        if etiqueta == "Derivar":
            objeto = "keyAccent"   # botón destacado, de otro color
        elif etiqueta in ("DEL", "C"):
            objeto = "keyDelete"   # rojo
        elif etiqueta == "x":
            objeto = "keyVar"      # verde
        else:
            objeto = "key"         # botón normal
        b.setObjectName(objeto)
        b.setCursor(Qt.PointingHandCursor)  # cursor de "mano" al pasar por encima
        b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        b.setMinimumHeight(40)
        # Si hay un tooltip definido para esta etiqueta, se lo asigna.
        if etiqueta in TOOLTIPS:
            b.setToolTip(TOOLTIPS[etiqueta])
        # Se conecta el clic del botón a la función _on_key, pasándole la
        # etiqueta correspondiente (se usa un lambda para "capturar" qué
        # botón fue exactamente el que se apretó).
        b.clicked.connect(lambda _=False, e=etiqueta: self._on_key(e))
        return b

    def _on_key(self, etiqueta):
        # Se ejecuta cada vez que se aprieta un botón del teclado matemático.
        # Decide qué hacer según cuál botón fue.
        inp = self.funcion_input
        if etiqueta == "DEL":
            # Borra un carácter hacia atrás, como la tecla backspace normal.
            inp.backspace()
        elif etiqueta == "C":
            # Limpia todo el cuadro de texto y también el panel de resultados.
            inp.clear()
            self._limpiar_resultado()
        elif etiqueta == "Derivar":
            # Simplemente dispara el cálculo de la derivada.
            self.calcular()
            return
        elif etiqueta == "n√":
            # Pregunta el índice de la raíz para que no haya que adivinar el orden.
            # Abre una ventanita pidiendo un número entero entre 2 y 99.
            n, ok = QInputDialog.getInt(
                self, "Raíz enésima",
                "¿Qué raíz quieres?\n2 = cuadrada, 3 = cúbica, 4 = cuarta, 5 = quinta…",
                3, 2, 99)
            if ok:
                # Si el usuario confirmó, se inserta "root(,n)" con el número
                # elegido, y se deja el cursor justo antes de la coma, listo
                # para que el usuario escriba el radicando.
                cierre = f",{n})"
                inp.insert("root(" + cierre)
                inp.setCursorPosition(inp.cursorPosition() - len(cierre))
            inp.setFocus()
            return
        elif etiqueta == ")":
            # Paréntesis inteligente: si ya hay ")" a la derecha, saltar sobre él.
            # Esto evita que se acumulen paréntesis de más si el usuario ya
            # tiene uno puesto justo después del cursor.
            pos = inp.cursorPosition()
            t = inp.text()
            if pos < len(t) and t[pos] == ")":
                inp.setCursorPosition(pos + 1)
            else:
                inp.insert(")")
        else:
            # Para el resto de los botones, se busca en el diccionario INSERT_MAP
            # qué texto insertar y cuánto hay que mover el cursor hacia atrás.
            texto, atras = INSERT_MAP[etiqueta]
            inp.insert(texto)
            if atras:
                inp.setCursorPosition(inp.cursorPosition() - atras)
        # Después de cualquier acción, se vuelve a poner el foco en el cuadro
        # de texto, para que el usuario pueda seguir escribiendo o usando el
        # teclado físico sin tener que hacer clic de nuevo.
        inp.setFocus()

    def _limpiar_reglas(self):
        # Elimina todos los widgets (las filas de reglas) que estén dentro
        # del layout de reglas, uno por uno, para dejarlo vacío antes de
        # volver a pintar una nueva lista de reglas.
        while self.reglas_layout.count():
            item = self.reglas_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _al_editar(self, _texto=None):
        """Cada vez que cambia la función, se limpia el resultado anterior."""
        # Se llama automáticamente cada vez que el texto del cuadro de función
        # cambia (ya sea escribiendo a mano o usando el teclado matemático).
        self._limpiar_resultado()

    def _limpiar_resultado(self):
        """Deja los paneles de resultado en blanco (para 'C' y entrada vacía)."""
        # Resetea todas las etiquetas de resultado a su estado inicial (vacío
        # o con el guion "—"), y oculta la imagen de indeterminación.
        self.interpreted_label.setText("")
        self.derivada_label.setText("—")
        self.derivada_label.show()
        self.respecto_label.setText("")
        self.error_label.setText("")
        self.imagen_label.hide()
        self._limpiar_reglas()

    def _pintar_reglas(self, reglas):
        # Recibe la lista de reglas (texto) que devolvió el motor de derivadas
        # y arma una fila visual por cada una, con su número y su texto.
        self._limpiar_reglas()
        total = len(reglas)
        for i, texto in enumerate(reglas):
            es_ultima = (i == total - 1)
            # La última fila tiene un nombre de objeto distinto (para que el
            # QSS le pueda quitar, por ejemplo, la línea divisoria de abajo).
            row = QFrame()
            row.setObjectName("reglaRowLast" if es_ultima else "reglaRow")
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 9, 0, 9)
            h.setSpacing(16)

            # Número de la regla, con dos dígitos (01, 02, 03...).
            num = QLabel(f"{i + 1:02d}")
            num.setObjectName("reglaNum")
            num.setFixedWidth(26)
            num.setAlignment(Qt.AlignTop)
            h.addWidget(num)

            # Texto de la regla en sí.
            txt = QLabel(texto)
            txt.setObjectName("reglaText")
            txt.setWordWrap(True)
            h.addWidget(txt, 1)

            self.reglas_layout.addWidget(row)

    def calcular(self):
        # Se ejecuta al apretar Enter o el botón "Derivar".
        # Toma el texto del cuadro de función, limpia espacios, y si está
        # vacío no hace nada más que limpiar el panel de resultados.
        texto = self.funcion_input.text().strip()
        if not texto:
            self._limpiar_resultado()
            return

        # Se manda el texto al motor de derivadas (derivador.py), que devuelve
        # un diccionario con el resultado o el error correspondiente.
        resultado = derivar(texto)

        if resultado["exito"]:
            # Caso de éxito: se muestra la función escrita, la derivada
            # calculada, la variable respecto a la que se derivó, y las reglas.
            self.imagen_label.hide()
            self.derivada_label.show()
            self.error_label.setText("")
            # Mostramos la función TAL COMO se escribió (sin simplificar),
            # solo con cosmética ** -> ^ y * -> ·
            self.interpreted_label.setText(
                "= " + _formato_matematico(texto)
            )
            self.derivada_label.setText(
                _formato_matematico(resultado["derivada"])
            )
            self.respecto_label.setText(
                f"derivada respecto a {resultado['variable']}"
            )
            self._pintar_reglas(resultado["reglas"])
        elif resultado.get("tipo") == "indeterminacion":
            # Indeterminación: se muestra la imagen (meme) + el aviso.
            # Se oculta la derivada porque no hay un resultado numérico válido,
            # y se limpia la lista de reglas porque no aplica ninguna.
            self.interpreted_label.setText("= " + _formato_matematico(texto))
            self.derivada_label.hide()
            self.respecto_label.setText("")
            self._limpiar_reglas()
            self.error_label.setText(resultado["error"])
            if not self._pixmap_indeterminacion.isNull():
                self.imagen_label.show()
        else:
            # Error de escritura u otro: se explica el error.
            # Se limpia todo el panel de resultado y solo se deja el mensaje
            # de error visible.
            self.imagen_label.hide()
            self.derivada_label.show()
            self.interpreted_label.setText("")
            self.derivada_label.setText("—")
            self.respecto_label.setText("")
            self._limpiar_reglas()
            self.error_label.setText(resultado["error"])


def cargar_fuentes_personalizadas():
    """Carga las fuentes .ttf/.otf embebidas en assets/fonts."""
    # Busca en la carpeta assets/fonts todos los archivos de fuente y los
    # registra en la aplicación, para poder usarlas aunque no estén
    # instaladas en el sistema operativo del usuario.
    fonts_dir = os.path.join(ASSETS_DIR, "fonts")
    if not os.path.isdir(fonts_dir):
        return
    for filename in os.listdir(fonts_dir):
        if filename.lower().endswith((".ttf", ".otf")):
            QFontDatabase.addApplicationFont(os.path.join(fonts_dir, filename))


def cargar_estilos(app):
    # Busca el archivo style.qss (la hoja de estilos, parecida a CSS pero
    # para aplicaciones Qt) y, si existe, se la aplica a toda la aplicación.
    qss_path = os.path.join(BASE_DIR, "style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main():
    # Punto de entrada de la aplicación: se crea la QApplication (obligatoria
    # en cualquier app de Qt), se cargan las fuentes y estilos personalizados,
    # se crea y muestra la ventana principal, y se arranca el bucle de eventos
    # de la aplicación (lo que mantiene la ventana abierta y respondiendo a
    # clics, teclas, etc, hasta que se cierra).
    app = QApplication(sys.argv)
    cargar_fuentes_personalizadas()
    cargar_estilos(app)

    window = DerivadoraWindow()
    window.show()

    sys.exit(app.exec())


# Esto asegura que main() solo se ejecute si este archivo se corre directamente,
# y no si se importa desde otro archivo.
if __name__ == "__main__":
    main()
