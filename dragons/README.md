# 🐉 Dragones vs. nikeyes

Animación para el README del perfil de GitHub. Cada ciclo dura 16 segundos:

1. **INSERT COIN** parpadea, el contador pasa de **CREDIT 0** a **CREDIT 1** y aparece **READY!** (en la Game Boy, PRESS START).
2. Se monta el nombre.
3. Los cuatro dragones barren el nombre entero a la vez, desde los dos lados: las letras se chamuscan y luego revientan. Disparan mientras quede algo en pie y, cuando los últimos trozos tocan el suelo, se marchan.
4. **GAME OVER**: cada dragón cruza una vez, rápido, de lado a lado escupiendo fuego (dos por encima del cartel y dos por debajo), y vuelta a empezar.

Arriba a la derecha, una **barra de energía (HP)** del nombre pierde un bloque, con parpadeo, por cada letra destruida.

Son SVG animados con CSS, sin JavaScript, así que GitHub los muestra dentro de un `<img>`. Todos están pensados para un perfil en modo claro.

| Archivo | Estilo |
|---|---|
| `out/dragons-pixel.svg` | 1 · Pixel art 8-bit, fondo transparente |
| `out/dragons-gameboy.svg` | 4 · Game Boy, dentro de la consola (empieza con PRESS START) |
| `out/dragons-comic.svg` | 15 · Cómic pop-art con BOOM!, POW!, ZAS! y RAWR! |

## Ponerlo en tu perfil

1. Abre (o crea) el repositorio **`nikeyes/nikeyes`**. Su `README.md` es el que se ve en tu perfil.
2. Sube el SVG elegido, por ejemplo a `assets/dragons-pixel.svg`.
3. Añade esto al `README.md`:

```html
<p align="center">
  <img src="assets/dragons-pixel.svg" alt="nikeyes vs. 4 dragones" width="100%">
</p>
```

> GitHub cachea las imágenes. Si cambias el SVG y no ves el cambio, renómbralo (p. ej. `dragons-pixel-v2.svg`).

## Regenerar o modificar

```bash
pip install fonttools                  # sólo para el estilo comic
python3 generate.py                     # los 3 estilos en ./out
python3 generate.py --theme comic       # sólo uno: pixel | gameboy | comic
python3 generate.py --name octocat      # otro nombre
python3 generate.py --seed 42           # otra partida: otros dragones por cada lado, otras alturas y otro orden
python3 generate.py --fire bola         # otra forma de fuego: llama | bola | chispa
```

Los estilos pixel y gameboy no necesitan nada más que Python 3.8+. El cómic convierte la tipografía de `fonts/` (Google Fonts, licencia OFL) en trazados, para que se vean igual en cualquier navegador sin depender de fuentes instaladas.

### Qué tocar en `generate.py`

- **Guion (`T_COIN_BLINK`, `T_READY`, `T_START`, `T_GAMEOVER`, `T_FADE`…)**: cuándo pasa cada cosa dentro del ciclo de 16 s (`CYCLE`).
- **`DRAGONS`**: un diccionario por dragón con:
  - tamaño en pixel (`sprite`, `px`) y en vectorial (`scale`);
  - aleteo (`flap`) y balanceo (`bob`);
  - fuego (`fire`, `particles`, `puffs`: fuego a "hipos");
  - dirección del barrido (`facing`), cuándo barre (`start`, `end`) y a qué altura (`mouth_y`);
  - su pasada final: por qué carril (`lane`) y cuántos segundos después del GAME OVER (`pass_at`). La velocidad la marca `PASS_TIME` (segundos en cruzar la pantalla).
- **`SETTLE`**: cuánto esperan, mirando, a que los últimos trozos caigan al suelo antes de irse. **`EXTRA_FIRE`**: si al acabar su barrido aún queda nombre en pie, cuánto tiempo más siguen disparando.
- **`FIRE_STYLE`**: la forma del fuego, igual en los tres estilos: `llama` (por defecto), `bola` o `chispa`. También `python3 generate.py --fire bola`.
- **`MOUTH_MARGIN`**: lo más cerca que se pone la boca del borde de la pantalla al barrer. Así los dragones pueden quemar desde el principio las columnas de los extremos (disparando más en picado) en lugar de dejarlas siempre para el final.
- **`HITS_TO_BREAK`**: cuántas llamas aguanta cada trozo del nombre antes de reventar (1 = a la primera).
- **`THEMES`**: colores, barra de energía (`hp`), fondo (`panel`), texto inicial (`start_text`), contador de créditos (`credit`), tipografía del cómic y onomatopeyas (`bursts`).
- **`SPRITES`**: los dragones pixel dibujados con letras (`B` cuerpo, `L` vientre, `W` ala, `D` sombra, `E` ojo, `H` cuernos). **`V_BODY`, `V_WING`…**: el dragón del cómic.

### La coreografía

Los cuatro dragones atacan el nombre **entero**: los que miran a la derecha lo barren de izquierda a derecha y los otros al revés, con los ataques solapados. **Lo que destruye el nombre es el propio fuego**: el script simula cada llama en orden de tiempo, cada una apunta a un trozo que siga en pie, la primera que le llega lo chamusca y la segunda lo revienta (`HITS_TO_BREAK`). Disparan mientras quede algo delante; cuando cae el último trozo se separan un poco, esperan a que los escombros toquen el suelo (`SETTLE`) y se marchan por arriba. Entonces aparece el GAME OVER y cada uno vuelve en una pasada rápida de lado a lado: los que miran a la derecha por encima del cartel y los que miran a la izquierda por debajo, con un chorro de fuego por delante.

**La semilla (`--seed`)** decide la partida. Con la de por defecto (1987) sale siempre la coreografía de la lista `DRAGONS`. Con cualquier otra se reparten de nuevo, dentro de márgenes seguros: qué dragones barren hacia cada lado, cuándo entra cada uno, a qué altura ataca, por qué carril y en qué orden hacen la pasada final. También cambian el orden en que caen los trozos y cómo saltan los escombros. Una misma semilla da siempre el mismo resultado, así que si una te gusta, apúntala.

**Reglas que el propio script vigila:**
- Ningún trozo cae sin que le haya llegado una llama, y ninguna llama va a un trozo que ya no existe. Si delante del dragón ya no queda nada, no dispara.
- Una llama sólo sale si la boca del dragón está dentro de la pantalla: nunca hay fuego sin dragón.
- La pasada final de cada dragón tiene que empezar cuando ya ha terminado de salir. Si no, el dragón parpadearía saltando de sitio, así que `generate.py` se niega a generar y te dice qué `pass_at` subir.

### Cómo funciona

Todo se calcula en Python sobre un único ciclo y se escribe como `@keyframes` CSS, por eso queda sincronizado al repetirse:

- En los estilos **pixel**, cada píxel del nombre es un elemento que cae, se enciende al recibir la llama y sale volando o cae al suelo como brasa.
- En el **cómic**, cada letra se trocea con una rejilla de recortes (`clipPath`). Los trozos se mueven por separado, así que las letras se rompen de verdad.
- Los dragones siguen curvas suaves (splines) con un ligero balanceo y alternan dos posiciones de alas.
- Cada llama nace en la boca, vuela en línea recta girada en la dirección del chorro (la cola apunta al dragón), crece, cambia de color y muere al llegar. Donde revienta un trozo saltan unas chispas que se quedan en su sitio.
