"""
SISFE Scraper - Automatización de consulta de expedientes judiciales de Santa Fe
Usa Playwright para controlar un navegador real y evadir protecciones anti-bot.
"""

import hashlib
import logging
import random
from datetime import datetime
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
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        # Ocultar navigator.webdriver para evadir detección de bot
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.page = await context.new_page()
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
        Flujo: navegar → sección "Matriculados" → seleccionar Circunscripción
               → seleccionar Colegio → ingresar Matrícula → ingresar Contraseña → submit.
        """
        login_url = self.config.get(
            "login_url", "https://sisfe.justiciasantafe.gov.ar"
        )
        circunscripcion = self.config.get("circunscripcion", "Rosario")
        colegio = self.config.get("colegio", "Abogados")
        matricula = self.config.get("matricula", "")
        password = self.config.get("password", "")

        try:
            logger.info(f"Navegando a {login_url}")
            await self.page.goto(login_url, wait_until="load", timeout=60_000)
            await self._pause(1_000, 2_500)  # pausa inicial como humano

            # 1) Buscar y clickear el acceso para "Matriculados"
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

            # 2) Seleccionar Circunscripción (dropdown)
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
                await circ_select.select_option(label=circunscripcion)
                # Esperar a que el dropdown de Colegio se actualice (puede ser dinámico)
                await self._pause(1_200, 2_500)
            else:
                logger.warning("No se encontró el select de Circunscripción.")
                await self._screenshot("debug_login_no_circ_select")

            # 3) Seleccionar Colegio (dropdown)
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
                await col_select.select_option(label=colegio)
                await self._pause(600, 1_500)
            else:
                logger.warning("No se encontró el select de Colegio.")
                await self._screenshot("debug_login_no_col_select")

            # 4) Ingresar Matrícula (tipeo humano)
            mat_selectors = [
                'input[name*="matricul" i]',
                'input[name*="mat" i]',
                'input[placeholder*="matricul" i]',
                'input[name="usuario"]',
                'input[name="username"]',
                'input[type="text"]',
            ]
            mat_field = await self._find_element(mat_selectors, timeout=5_000)
            if mat_field:
                logger.info(f"Ingresando matrícula: {matricula}")
                await self._type_human(mat_field, matricula)
            else:
                logger.error("No se encontró el campo de Matrícula.")
                await self._screenshot("debug_login_no_matricula_field")
                return False

            await self._pause(500, 1_200)

            # 5) Ingresar Contraseña (tipeo humano)
            pass_field = await self.page.wait_for_selector(
                'input[type="password"]', timeout=5_000
            )
            await self._type_human(pass_field, password)

            await self._pause(800, 2_000)  # pausa antes de enviar

            # 6) Submit
            submit = await self._find_element(SUBMIT_SELECTORS, timeout=3_000)
            if submit:
                await submit.click()
            else:
                await self.page.keyboard.press("Enter")

            await self.page.wait_for_load_state("load", timeout=20_000)

            # Verificar resultado
            current_url = self.page.url.lower()
            if "login" not in current_url and "acceso" not in current_url:
                logger.info("Login exitoso")
                return True

            body = await self.page.inner_text("body")
            if any(
                kw in body.lower()
                for kw in ["incorrecta", "inválida", "error", "invalid", "no encontrada"]
            ):
                logger.error("Login falló: credenciales incorrectas")
                await self._screenshot("debug_login_failed")
                return False

            logger.info("Login aparentemente exitoso (sin redirección clara)")
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

    async def _screenshot(self, name: str):
        try:
            path = f"{name}.png"
            await self.page.screenshot(path=path)
            logger.debug(f"Screenshot guardado: {path}")
        except Exception:
            pass
