Iniciamos el agente con este comando:

```bash
uv run python -m ui.gradio_app
```

Esperamos que levante la instancia y vamos a:

- http://127.0.0.1:7860

Veremos esta imagen:

![alt text](image.png)

Dale una instrucción básica como:

> "Créame una app básica que permita al usuario escribir dos números, tener un botón que los sume y me muestre el resultado."

(Puede ser un pedido más complejo, pero gastará más tokens.)

El agente empezará a trabajar:

![alt text](image-1.png)

En consola se podrá ver qué está haciendo el agente:

![alt text](image-2.png)

Y dará el resultado:

![alt text](image-3.png)

En el enlace que da se puede acceder a la versión en vivo de la app:

![alt text](image-4.png)

Ahora podemos pedirle, por ejemplo:

> "Agrega un botón que permita multiplicar dichos números, además del botón de suma."

![alt text](image-5.png)

Y me muestra la versión en vivo nuevamente...

> **En proceso de solución:** actualmente genera bien las primeras versiones de la app, pero al solicitar cambios el agente cree haberlos realizado y el resultado es una app sin estilos CSS, solo HTML básico. Y por más que el agente revisa varias veces, no detecta ningún problema. Posiblemente el problema sea con el entorno E2B.