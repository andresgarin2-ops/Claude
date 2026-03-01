"""
SISFE Scraper - Automatización de consulta de expedientes judiciales de Santa Fe
Usa Playwright para controlar un navegador real y evadir protecciones anti-bot.
"""

import asyncio
import hashlib
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# Selectores posibles para campos de login (se prueban en orden)
USER_SELECTORS = [
    'input[name="username"]',
    'input[name="usuario"]',
    'input[name="user"]',
    'input[name="login"]',
    'input[type="email"]',
    'input[placeholder*="usuario" i]',
    'input[placeholder*="user" i]',
    'input[placeholder*="email" i]',
]

SUBMIT_SELECTORS = [
    'button[type="submit"]',
    'input[type="submit"]',
    'button:has-text("Ingresar")',
    'button:has-text("Acceder")',
    'button:has-text("Login")',
    'button:has-text("Iniciar")',
]

SEARCH_SELECTORS = [
    'input[placeholder*="expediente" i]',
    'input[name*="expediente" i]',
    'input[name*="numero" i]',
    'input[placeholder*="número" i]',
    'input[placeholder*="numero" i]',
    'input[type="search"]',
    'input[name="nro"]',
    'input[name="number"]',
]

SEARCH_BTN_SELECTORS = [
    'button:has-text("Buscar")',
    'button:has-text("Consultar")',
    'button:has-text("Search")',
    'button[type="submit"]',
    'input[type="submit"]',
]

# Selectores para extraer el último movimiento de una tabla
MOVEMENT_ROW_SELECTORS = [
    'table tbody tr:last-child',
    '.actuacion:last-child',
    '.movimiento:last-child',
    '[class*="actuac"]:last-child',
    '[class*="movim"]:last-child',
    'tr:last-child',
]


class SISFEScraper:
    def __init__(self, config):
        self.config = config
        self._playwright = None
        self._browser = None
        self.page = None

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._cookies_path = Path(
            self.config.get("cookies_file", "sisfe_cookies.json")
        )
        # Headless solo si ya tenemos cookies guardadas. Si no, abre visible
        # para que el usuario resuelva el reCAPTCHA manualmente.
        headless = self._cookies_path.exists()
        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        # Ocultar navigator.webdriver para evadir detección de bot
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        # Cargar sesión guardada si existe
        if self._cookies_path.exists():
            cookies = json.loads(self._cookies_path.read_text(encoding="utf-8"))
            await self._context.add_cookies(cookies)
            logger.info(f"Sesión cargada desde {self._cookies_path}")
        self.page = await self._context.new_page()
        return self

    async def __aexit__(self, *args):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _pause(self, min_ms: int = 800, max_ms: int = 2500):
        """Pausa aleatoria para simular comportamiento humano."""
        ms = random.randint(min_ms, max_ms)
        await self.page.wait_for_timeout(ms)

    async def _type_human(self, element, text: str):
        """Tipea carácter a carácter con velocidad humana (40-120 ms por tecla)."""
        await element.click()
        await self._pause(200, 500)
        for char in text:
            await element.type(char)
            await self.page.wait_for_timeout(random.randint(40, 120))

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(self) -> bool:
        """
        Login en SISFE para matriculados.

        Si existe sisfe_cookies.json (sesión previa), intenta reutilizarla.
        Si no existe o está expirada, abre el navegador en modo visible,
        rellena el formulario automáticamente y pide al usuario que resuelva
        el reCAPTCHA y haga click en 'Ingresar'. Luego guarda las cookies.
        """
        login_url = self.config.get(
            "login_url", "https://sisfe.justiciasantafe.gov.ar"
        )
        search_url = self.config.get(
            "search_url", "https://sisfe.justiciasantafe.gov.ar/buscar-expediente"
        )
        circunscripcion = self.config.get("circunscripcion", "Rosario")
        colegio = self.config.get("colegio", "Abogados")
        matricula = self.config.get("matricula", "")
        password = self.config.get("password", "")

        # ── 0) Verificar sesión guardada ──────────────────────────────────
        if self._cookies_path.exists():
            try:
                await self.page.goto(search_url, wait_until="load", timeout=20_000)
                if (
                    "login" not in self.page.url.lower()
                    and "acceso" not in self.page.url.lower()
                ):
                    logger.info("Sesión previa válida — login omitido.")
                    return True
                logger.info("Sesión expirada, se rehace el login...")
                self._cookies_path.unlink()
            except Exception:
                pass

        try:
            # ── 1) Navegar a la página de login ───────────────────────────
            logger.info(f"Navegando a {login_url}")
            await self.page.goto(login_url, wait_until="load", timeout=60_000)
            await self._pause(1_000, 2_500)

            # ── 2) Click en "Matriculados" ────────────────────────────────
            matriculados_selectors = [
                'a:has-text("Matriculados")',
                'a:has-text("matriculados")',
                'button:has-text("Matriculados")',
                '[href*="matriculado"]',
                'a:has-text("Ingresar")',
            ]
            mat_link = await self._find_element(matriculados_selectors, timeout=5_000)
            if mat_link:
                logger.info("Sección Matriculados encontrada, haciendo click...")
                await self._pause(500, 1_200)
                await mat_link.click()
                await self.page.wait_for_load_state("load", timeout=15_000)
                await self._pause(800, 2_000)
            else:
                logger.warning(
                    "No se encontró el link de Matriculados. "
                    "Intentando continuar en la página actual."
                )
                await self._screenshot("debug_login_no_matriculados_link")

            # ── 3) Seleccionar Circunscripción ────────────────────────────
            circ_selectors = [
                'select[name*="circunscripcion" i]',
                'select[name*="circ" i]',
                'select[name*="jurisdiccion" i]',
                'select[id*="circunscripcion" i]',
                'select[id*="circ" i]',
                'select:first-of-type',
            ]
            circ_select = await self._find_element(circ_selectors, timeout=5_000)
            if circ_select:
                logger.info(f"Seleccionando circunscripción: {circunscripcion}")
                await self._pause(400, 900)
                await self._select_by_partial_text(circ_select, circunscripcion)
                await self._pause(1_200, 2_500)
            else:
                logger.warning("No se encontró el select de Circunscripción.")
                await self._screenshot("debug_login_no_circ_select")

            # ── 4) Seleccionar Colegio ────────────────────────────────────
            col_selectors = [
                'select[name*="colegio" i]',
                'select[name*="col" i]',
                'select[id*="colegio" i]',
                'select:nth-of-type(2)',
            ]
            col_select = await self._find_element(col_selectors, timeout=5_000)
            if col_select:
                logger.info(f"Seleccionando colegio: {colegio}")
                await self._pause(400, 900)
                await self._select_by_partial_text(col_select, colegio)
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=10_000)
                except PlaywrightTimeout:
                    pass  # La página puede no alcanzar networkidle (reCAPTCHA, etc.)
                await self._pause(1_500, 3_000)
            else:
                logger.warning("No se encontró el select de Colegio.")
                await self._screenshot("debug_login_no_col_select")

            # ── 5 y 6) Intentar auto-completar Matrícula y Contraseña ────────
            # Primero intenta Tab desde el dropdown de colegio (más robusto que selectores)
            auto_filled = False
            if col_select:
                try:
                    await col_select.press("Tab")
                    await self._pause(400, 800)
                    await self.page.keyboard.type(matricula, delay=random.randint(40, 100))
                    await self._pause(300, 700)
                    await self.page.keyboard.press("Tab")
                    await self._pause(300, 600)
                    await self.page.keyboard.type(password, delay=random.randint(40, 100))
                    auto_filled = True
                    logger.info("Matrícula y contraseña completadas via teclado.")
                except Exception as exc:
                    logger.warning(f"Auto-completado via Tab falló: {exc}")

            # ── 7) Pedir acción al usuario ─────────────────────────────────
            if auto_filled:
                print("\n" + "=" * 60)
                print("  ACCIÓN REQUERIDA EN EL NAVEGADOR:")
                print("  1. Verificá que Matrícula y Contraseña estén correctas")
                print("  2. Tildá el checkbox 'No soy un robot'")
                print("  3. Resolvé el desafío si aparece")
                print("  4. Hacé click en 'Ingresar'")
                print("  El bot va a continuar automáticamente.")
                print("=" * 60 + "\n")
            else:
                print("\n" + "=" * 60)
                print("  ACCIÓN REQUERIDA EN EL NAVEGADOR:")
                print(f"  1. Completá el campo MATRÍCULA con: {matricula}")
                print("  2. Completá el campo CONTRASEÑA")
                print("  3. Tildá el checkbox 'No soy un robot'")
                print("  4. Resolvé el desafío si aparece")
                print("  5. Hacé click en 'Ingresar'")
                print("  El bot va a continuar automáticamente.")
                print("=" * 60 + "\n")
            logger.info("Esperando que el usuario complete el login (hasta 3 min)...")

            url_antes = self.page.url
            for _ in range(360):  # hasta 3 minutos
                await asyncio.sleep(0.5)
                if self.page.url != url_antes:
                    break
            else:
                logger.error("Timeout: el reCAPTCHA no fue resuelto en 3 minutos.")
                return False

            await self.page.wait_for_load_state("load", timeout=20_000)

            # ── 8) Verificar resultado y guardar cookies ──────────────────
            current_url = self.page.url.lower()
            if "login" in current_url or "acceso" in current_url:
                body = await self.page.inner_text("body")
                if any(
                    kw in body.lower()
                    for kw in ["incorrecta", "inválida", "error", "invalid"]
                ):
                    logger.error("Login falló: credenciales incorrectas.")
                    await self._screenshot("debug_login_failed")
                    return False

            await self._save_cookies()
            logger.info("Login exitoso — sesión guardada.")
            return True

        except Exception as exc:
            logger.error(f"Excepción durante login: {exc}")
            await self._screenshot("debug_login_exception")
            return False

    # ------------------------------------------------------------------
    # Consulta de expediente
    # ------------------------------------------------------------------

    async def get_expediente_state(self, codigo: str) -> dict | None:
        search_url = self.config.get(
            "search_url",
            "https://sisfe.justiciasantafe.gov.ar/buscar-expediente",
        )
        try:
            logger.info(f"Consultando expediente {codigo}")
            await self._pause(2_000, 5_000)  # pausa antes de cada consulta
            await self.page.goto(search_url, wait_until="load", timeout=60_000)
            await self._pause(800, 2_000)

            filled = await self._fill_search_field(codigo)
            if not filled:
                logger.error(f"No se pudo ingresar el código {codigo}")
                await self._screenshot(f"debug_{codigo.replace('-', '_')}_no_field")
                return None

            # Confirmar búsqueda
            search_btn = await self._find_element(SEARCH_BTN_SELECTORS, timeout=2_000)
            if search_btn:
                await search_btn.click()
            else:
                await self.page.keyboard.press("Enter")

            await self.page.wait_for_load_state("load", timeout=20_000)

            # Capturar contenido completo para detectar cualquier cambio
            content = await self.page.inner_text("body")
            content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

            last_movement = await self._extract_last_movement()

            return {
                "hash": content_hash,
                "content_preview": content[:500],
                "last_movement": last_movement,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as exc:
            logger.error(f"Excepción consultando {codigo}: {exc}")
            await self._screenshot(f"debug_{codigo.replace('-', '_')}_exception")
            return None

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    async def _fill_search_field(self, codigo: str) -> bool:
        """Intenta llenar el campo de búsqueda con el código del expediente."""

        # 1) Intentar campo único que acepte el código completo
        field = await self._find_element(SEARCH_SELECTORS, timeout=2_000)
        if field:
            await field.fill(codigo)
            return True

        # 2) Intentar campos separados por el separador '-'
        # Formato esperado: "21-02343434-2"
        partes = codigo.split("-")
        if len(partes) == 3:
            prefijo, numero, sufijo = partes
            filled_count = 0
            for value, name_hint in [
                (prefijo, "jur"),
                (numero, "num"),
                (sufijo, "suf"),
            ]:
                partial_selectors = [
                    f'input[name*="{name_hint}" i]',
                    f'input[placeholder*="{name_hint}" i]',
                ]
                f = await self._find_element(partial_selectors, timeout=1_000)
                if f:
                    await f.fill(value)
                    filled_count += 1

            if filled_count > 0:
                return True

        logger.warning(
            "No se encontraron campos de búsqueda; "
            "es posible que la UI del SISFE haya cambiado. "
            "Revisá debug_*.png para más detalles."
        )
        return False

    async def _extract_last_movement(self) -> str | None:
        """Extrae el texto de la última fila de actuaciones si existe tabla."""
        for selector in MOVEMENT_ROW_SELECTORS:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    text = (await element.inner_text()).strip()
                    if text:
                        return text[:300]
            except Exception:
                continue
        return None

    async def _find_element(self, selectors: list[str], timeout: int = 2_000):
        """Prueba selectores en orden y devuelve el primero que encuentre."""
        for selector in selectors:
            try:
                element = await self.page.wait_for_selector(
                    selector, timeout=timeout
                )
                if element:
                    return element
            except PlaywrightTimeout:
                continue
        return None

    async def _select_by_partial_text(self, select_element, text: str):
        """
        Selecciona la primera opción cuyo texto contenga `text` (insensible a mayúsculas).
        Primero intenta coincidencia exacta; si falla, usa coincidencia parcial via JS.
        """
        try:
            await select_element.select_option(label=text)
            return
        except Exception:
            pass
        # Fallback: buscar opción que contenga el texto
        try:
            value = await self.page.evaluate(
                """([el, txt]) => {
                    const opts = Array.from(el.options);
                    const match = opts.find(o => o.text.toLowerCase().includes(txt.toLowerCase()));
                    if (match) { el.value = match.value; el.dispatchEvent(new Event('change', {bubbles:true})); return match.value; }
                    return null;
                }""",
                [select_element, text],
            )
            if value:
                logger.info(f"Opción seleccionada por texto parcial: '{text}' → valor '{value}'")
            else:
                logger.warning(f"No se encontró opción que contenga '{text}'")
        except Exception as exc:
            logger.warning(f"_select_by_partial_text falló: {exc}")

    async def _find_matricula_field(self):
        """
        Busca el campo de matrícula en la página principal y en todos los iframes.
        Loguea información de diagnóstico para facilitar el debugging.
        """
        skip = {"password", "hidden", "submit", "button", "checkbox", "radio", "file", "image"}

        # ── Diagnóstico: listar todos los inputs de la página principal ───
        try:
            inputs_info = await self.page.evaluate("""
                () => Array.from(document.querySelectorAll('input')).map(i => ({
                    type: i.type, name: i.name, id: i.id,
                    placeholder: i.placeholder,
                    visible: i.offsetParent !== null && i.style.display !== 'none'
                }))
            """)
            logger.info(f"Inputs en página principal: {inputs_info}")
        except Exception as exc:
            logger.warning(f"No se pudo listar inputs: {exc}")

        frames = self.page.frames
        logger.info(f"Frames detectados: {len(frames)} — URLs: {[f.url for f in frames]}")

        # ── Buscar en página principal ────────────────────────────────────
        try:
            for inp in await self.page.query_selector_all("input"):
                inp_type = (await inp.get_attribute("type") or "text").lower()
                if inp_type not in skip and await inp.is_visible():
                    logger.info(f"Campo en página principal (type='{inp_type}')")
                    return inp
        except Exception as exc:
            logger.warning(f"Error buscando en página principal: {exc}")

        # ── Buscar dentro de cada iframe ──────────────────────────────────
        for i, frame in enumerate(frames):
            if frame == self.page.main_frame:
                continue
            try:
                logger.info(f"Buscando en frame {i}: {frame.url}")
                for inp in await frame.query_selector_all("input"):
                    inp_type = (await inp.get_attribute("type") or "text").lower()
                    if inp_type not in skip and await inp.is_visible():
                        logger.info(f"Campo en frame {i} (type='{inp_type}')")
                        return inp
            except Exception as exc:
                logger.warning(f"Error en frame {i}: {exc}")

        return None

    async def _save_cookies(self):
        """Guarda las cookies de sesión actuales en disco."""
        cookies = await self._context.cookies()
        self._cookies_path.write_text(
            json.dumps(cookies, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(f"Sesión guardada en {self._cookies_path}")

    async def _screenshot(self, name: str):
        try:
            path = f"{name}.png"
            await self.page.screenshot(path=path)
            logger.debug(f"Screenshot guardado: {path}")
        except Exception:
            pass
