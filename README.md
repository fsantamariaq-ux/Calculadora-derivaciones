CALCULADORA DE DERIVADAS
========================

PARA USAR LA APP
----------------
Haz doble clic en:  CalculadoraDerivadas.exe
(No necesitas instalar Python ni nada. Funciona sola.)


QUÉ HAY EN ESTA CARPETA
-----------------------
- CalculadoraDerivadas.exe : la aplicación lista para usar.
- DOCUMENTACION.md         : documento técnico (referencia general del proyecto).
- PASO-A-PASO.md           : documento FORMAL del paso a paso de la construccion,
                             con las bases matematicas y logicas justificadas.
                             (Este es el que sirve para el informe/sustentacion.)
- codigo-fuente/           : el código, por si algún día quieres editarlo
                             o volver a compilar el .exe.


CÓMO SE USA LA APP
------------------
1. Escribe la función (o úsala con el teclado matemático de botones).
   - Puedes escribir "45x" (se entiende como 45*x).
   - Notación de clase: sen, cos, arcsen, senh, raíces (raiz cuadrada,
     cubica y enesima), etc.
2. Pulsa "Derivar".
3. Verás la derivada y, abajo, LAS REGLAS que se aplicaron (paso a paso).

Notas:
- Si borras o cambias la función, el resultado se limpia solo.
- Si la función lleva a una indeterminacion (division por cero, etc.),
  aparece una imagen.
- Si escribes algo mal, te explica el error.


VERSIÓN FINAL
-------------
Incluye: notacion colombiana, teclado matematico, multiplicacion implicita,
auto-limpiado, deteccion completa de reglas, imagen en indeterminaciones,
y seguridad reforzada (probada contra ataques).
