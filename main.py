"""
main.py - Interfaz de escritorio para la Calculadora de Derivadas
Motor de cálculo: derivador.py
UI: PySide6, dirección de diseño EDITORIAL (revista de matemáticas),
    estilizada con style.qss + fuentes embebidas (Fraunces, IBM Plex Mono).
    Incluye un teclado matemático (numpad) que inserta sintaxis válida
    para evitar errores de tipeo.
"""
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QPushButton, QLabel, QFrame, QScrollArea, QSizePolicy, QInputDialog
)
from PySide6.QtGui import QFontDatabase, QIcon, QFont, QPixmap
from PySide6.QtCore import Qt

from derivador import derivar

def _base_dir():
    # Como .exe (PyInstaller) los datos viven en sys._MEIPASS; en desarrollo,
    # junto a este archivo.
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _base_dir()
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# --- Teclado matemático: etiqueta visible -> (texto a insertar, cursor atrás) ---
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
for _d in "0123456789":
    INSERT_MAP[_d] = (_d, 0)

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
    f = QFont("IBM Plex Mono")
    f.setPixelSize(px)
    f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f


def _formato_matematico(expr):
    """Cosmética de la fórmula para lectura tipo libro: ** -> ^ y * -> ·"""
    return str(expr).replace("**", "^").replace("*", "·")


class DerivadoraWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calculadora de Derivadas")
        self.setMinimumSize(560, 600)
        self.resize(640, 900)

        icon_path = os.path.join(ASSETS_DIR, "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._build_ui()

    def _build_ui(self):
        # Área con scroll para que quepa en pantallas pequeñas
        scroll = QScrollArea()
        scroll.setObjectName("scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        central = QWidget()
        central.setObjectName("central")
        central.setAttribute(Qt.WA_StyledBackground, True)
        scroll.setWidget(central)
        self.setCentralWidget(scroll)

        root = QVBoxLayout(central)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(0)

        # --- Encabezado: wordmark d/dx + kicker ---
        header = QHBoxLayout()
        wordmark = QLabel("d/dx")
        wordmark.setObjectName("wordmark")
        header.addWidget(wordmark)
        header.addStretch(1)
        kicker = QLabel("CÁLCULO · DIFERENCIAL")
        kicker.setObjectName("kicker")
        kicker.setFont(_mono_tracked(11, 2.0))
        kicker.setAlignment(Qt.AlignBottom)
        header.addWidget(kicker)
        root.addLayout(header)

        rule = QFrame()
        rule.setObjectName("ruleStrong")
        rule.setFixedHeight(2)
        root.addSpacing(10)
        root.addWidget(rule)
        root.addSpacing(24)

        # --- 01 · FUNCIÓN ---
        root.addWidget(self._tag("01 · FUNCIÓN"))
        root.addSpacing(8)

        self.funcion_input = QLineEdit()
        self.funcion_input.setObjectName("funcionInput")
        self.funcion_input.setPlaceholderText("x^2 * sen(x)")
        self.funcion_input.returnPressed.connect(self.calcular)
        # Al editar la función (teclado o numpad) se descarta el resultado anterior,
        # para que sea obvio que hay que volver a derivar (nuevo proceso).
        self.funcion_input.textChanged.connect(self._al_editar)
        root.addWidget(self.funcion_input)

        root.addSpacing(6)
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
        root.addWidget(self._tag("02 · DERIVADA"))
        root.addSpacing(12)
        self.derivada_label = QLabel("—")
        self.derivada_label.setObjectName("derivada")
        self.derivada_label.setWordWrap(True)
        root.addWidget(self.derivada_label)
        root.addSpacing(6)
        self.respecto_label = QLabel("")
        self.respecto_label.setObjectName("interpretedLine")
        root.addWidget(self.respecto_label)

        # Imagen que aparece en las indeterminaciones (meme del usuario)
        self.imagen_label = QLabel()
        self.imagen_label.setObjectName("imagenResultado")
        self.imagen_label.setAlignment(Qt.AlignCenter)
        self._pixmap_indeterminacion = QPixmap()
        _img_path = os.path.join(ASSETS_DIR, "indeterminacion.png")
        if os.path.exists(_img_path):
            self._pixmap_indeterminacion = QPixmap(_img_path).scaledToWidth(
                380, Qt.SmoothTransformation
            )
        self.imagen_label.setPixmap(self._pixmap_indeterminacion)
        self.imagen_label.hide()
        root.addWidget(self.imagen_label)

        root.addSpacing(30)

        # --- 03 · REGLAS APLICADAS ---
        root.addWidget(self._tag("03 · REGLAS APLICADAS"))
        root.addSpacing(4)
        reglas_box = QWidget()
        self.reglas_layout = QVBoxLayout(reglas_box)
        self.reglas_layout.setContentsMargins(0, 0, 0, 0)
        self.reglas_layout.setSpacing(0)
        root.addWidget(reglas_box)

        root.addSpacing(18)

        # --- Línea de error ---
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLine")
        self.error_label.setWordWrap(True)
        root.addWidget(self.error_label)

        root.addStretch(1)

    def _tag(self, texto):
        lbl = QLabel(texto)
        lbl.setObjectName("sectionTag")
        lbl.setFont(_mono_tracked(11, 2.0))
        return lbl

    def _build_numpad(self):
        box = QWidget()
        grid = QGridLayout(box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        for c in range(6):
            grid.setColumnStretch(c, 1)

        for r, fila in enumerate(NUMPAD_ROWS):
            for c, etiqueta in enumerate(fila):
                grid.addWidget(self._mk_key(etiqueta), r, c)
        # "Derivar" ocupa el resto de la última fila (junto a 0 y ,)
        grid.addWidget(self._mk_key("Derivar"), 6, 2, 1, 4)
        return box

    def _mk_key(self, etiqueta):
        b = QPushButton(etiqueta)
        if etiqueta == "Derivar":
            objeto = "keyAccent"
        elif etiqueta in ("DEL", "C"):
            objeto = "keyDelete"   # rojo
        elif etiqueta == "x":
            objeto = "keyVar"      # verde
        else:
            objeto = "key"
        b.setObjectName(objeto)
        b.setCursor(Qt.PointingHandCursor)
        b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        b.setMinimumHeight(40)
        if etiqueta in TOOLTIPS:
            b.setToolTip(TOOLTIPS[etiqueta])
        b.clicked.connect(lambda _=False, e=etiqueta: self._on_key(e))
        return b

    def _on_key(self, etiqueta):
        inp = self.funcion_input
        if etiqueta == "DEL":
            inp.backspace()
        elif etiqueta == "C":
            inp.clear()
            self._limpiar_resultado()
        elif etiqueta == "Derivar":
            self.calcular()
            return
        elif etiqueta == "n√":
            # Pregunta el índice de la raíz para que no haya que adivinar el orden
            n, ok = QInputDialog.getInt(
                self, "Raíz enésima",
                "¿Qué raíz quieres?\n2 = cuadrada, 3 = cúbica, 4 = cuarta, 5 = quinta…",
                3, 2, 99)
            if ok:
                cierre = f",{n})"
                inp.insert("root(" + cierre)
                inp.setCursorPosition(inp.cursorPosition() - len(cierre))
            inp.setFocus()
            return
        elif etiqueta == ")":
            # Paréntesis inteligente: si ya hay ")" a la derecha, saltar sobre él
            pos = inp.cursorPosition()
            t = inp.text()
            if pos < len(t) and t[pos] == ")":
                inp.setCursorPosition(pos + 1)
            else:
                inp.insert(")")
        else:
            texto, atras = INSERT_MAP[etiqueta]
            inp.insert(texto)
            if atras:
                inp.setCursorPosition(inp.cursorPosition() - atras)
        inp.setFocus()

    def _limpiar_reglas(self):
        while self.reglas_layout.count():
            item = self.reglas_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _al_editar(self, _texto=None):
        """Cada vez que cambia la función, se limpia el resultado anterior."""
        self._limpiar_resultado()

    def _limpiar_resultado(self):
        """Deja los paneles de resultado en blanco (para 'C' y entrada vacía)."""
        self.interpreted_label.setText("")
        self.derivada_label.setText("—")
        self.derivada_label.show()
        self.respecto_label.setText("")
        self.error_label.setText("")
        self.imagen_label.hide()
        self._limpiar_reglas()

    def _pintar_reglas(self, reglas):
        self._limpiar_reglas()
        total = len(reglas)
        for i, texto in enumerate(reglas):
            es_ultima = (i == total - 1)
            row = QFrame()
            row.setObjectName("reglaRowLast" if es_ultima else "reglaRow")
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 9, 0, 9)
            h.setSpacing(16)

            num = QLabel(f"{i + 1:02d}")
            num.setObjectName("reglaNum")
            num.setFixedWidth(26)
            num.setAlignment(Qt.AlignTop)
            h.addWidget(num)

            txt = QLabel(texto)
            txt.setObjectName("reglaText")
            txt.setWordWrap(True)
            h.addWidget(txt, 1)

            self.reglas_layout.addWidget(row)

    def calcular(self):
        texto = self.funcion_input.text().strip()
        if not texto:
            self._limpiar_resultado()
            return

        resultado = derivar(texto)

        if resultado["exito"]:
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
            # Indeterminación: se muestra la imagen (meme) + el aviso
            self.interpreted_label.setText("= " + _formato_matematico(texto))
            self.derivada_label.hide()
            self.respecto_label.setText("")
            self._limpiar_reglas()
            self.error_label.setText(resultado["error"])
            if not self._pixmap_indeterminacion.isNull():
                self.imagen_label.show()
        else:
            # Error de escritura u otro: se explica el error
            self.imagen_label.hide()
            self.derivada_label.show()
            self.interpreted_label.setText("")
            self.derivada_label.setText("—")
            self.respecto_label.setText("")
            self._limpiar_reglas()
            self.error_label.setText(resultado["error"])


def cargar_fuentes_personalizadas():
    """Carga las fuentes .ttf/.otf embebidas en assets/fonts."""
    fonts_dir = os.path.join(ASSETS_DIR, "fonts")
    if not os.path.isdir(fonts_dir):
        return
    for filename in os.listdir(fonts_dir):
        if filename.lower().endswith((".ttf", ".otf")):
            QFontDatabase.addApplicationFont(os.path.join(fonts_dir, filename))


def cargar_estilos(app):
    qss_path = os.path.join(BASE_DIR, "style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main():
    app = QApplication(sys.argv)
    cargar_fuentes_personalizadas()
    cargar_estilos(app)

    window = DerivadoraWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
