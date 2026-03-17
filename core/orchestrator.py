import asyncio
import json
import subprocess
import sys
import time
from typing import Optional

from core.logger import get_logger
from core.connection import ConnectionServer
from llm.client import LLMClient
from llm.parser import parse_actions, parse_single_action
from screenshot.capture import capture_screenshot

from actions.base import ActionExecutor
from actions.mouse import (
    MoveAction, ClickAction, DoubleClickAction, RightClickAction, DragAction, ScrollAction,
)
from actions.keyboard import (
    TypeAction, KeyAction, HotkeyAction, KeyDownAction, KeyUpAction,
)
from actions.apps import OpenAppAction, RunCommandAction
from actions.windows import FocusWindowAction, CloseWindowAction, MaximizeWindowAction
from actions.terminal import WaitAction
from actions.navigate import NavigateAction

log = get_logger("orchestrator")

SCREENSHOT_SETTLE_MS = 600
MAX_VISION_STEPS = 40

ACTION_MAP: dict[str, ActionExecutor] = {
    "wait": WaitAction(),
    "move": MoveAction(),
    "click": ClickAction(),
    "double_click": DoubleClickAction(),
    "right_click": RightClickAction(),
    "drag": DragAction(),
    "scroll": ScrollAction(),
    "type": TypeAction(),
    "key": KeyAction(),
    "hotkey": HotkeyAction(),
    "key_down": KeyDownAction(),
    "key_up": KeyUpAction(),
    "open_app": OpenAppAction(),
    "run_command": RunCommandAction(),
    "navigate": NavigateAction(),
    "focus_window": FocusWindowAction(),
    "close_window": CloseWindowAction(),
    "maximize_window": MaximizeWindowAction(),
}

# ---------------------------------------------------------------------------
# SYSTEM PROMPTS — LINUX (PT-BR, robusto e descritivo)
# ---------------------------------------------------------------------------

_VISION_SYSTEM_PROMPT_LINUX = """Voce e o ALAHA, um agente de IA avancado e totalmente autonomo que controla um computador Linux (Ubuntu).
Voce possui acesso visual COMPLETO a tela atraves de screenshots em tempo real.
Seu objetivo e completar as tarefas do usuario de forma eficiente, inteligente e sem pedir ajuda.

Voce e um ESPECIALISTA em navegacao no sistema operacional Linux. Voce domina:
- O desktop GNOME/XFCE/KDE e seus paineis, menus e atalhos
- Gerenciadores de arquivos (Nautilus, Thunar, Nemo)
- Navegadores web (Chrome, Firefox, Chromium, Edge)
- Terminal e linha de comando bash
- Aplicativos comuns do Linux (LibreOffice, GIMP, VLC, etc.)
- Atalhos de teclado do sistema e dos aplicativos

=== COMO FUNCIONA ===

A cada turno voce recebe um screenshot da tela e deve:
1. PENSAR: Analisar a tela cuidadosamente. O que mudou? Onde estamos no plano? Qual e o proximo passo exato?
2. AGIR: Escolher EXATAMENTE UMA acao para executar.

=== FORMATO DE RESPOSTA (SOMENTE JSON) ===

Para executar uma acao:
{"thinking": "Vejo a area de trabalho do Ubuntu. Preciso abrir o Chrome. Vou usar open_app.", "action": {"type": "open_app", "app": "chrome"}}

Para sinalizar que a tarefa foi concluida:
{"done": true, "message": "Tarefa concluida com sucesso. Enviei a mensagem no WhatsApp."}

=== SISTEMA DE COORDENADAS (IMPORTANTISSIMO) ===

As coordenadas X,Y que voce informa devem corresponder DIRETAMENTE ao screenshot que voce esta vendo.
- O ponto (0, 0) e o canto SUPERIOR ESQUERDO do screenshot.
- A resolucao do screenshot e informada a cada passo (ex: 1366x768).
- Suas coordenadas serao automaticamente convertidas para a resolucao real da tela.
- NAO tente calcular ou converter coordenadas. Use EXATAMENTE as posicoes que voce ve na imagem.

COMO IDENTIFICAR COORDENADAS COM PRECISAO:
1. Localize o elemento alvo no screenshot visualmente.
2. Identifique o CENTRO EXATO do elemento (nao a borda, nao o canto — o CENTRO).
3. Estime X (horizontal, da esquerda para direita) e Y (vertical, de cima para baixo).
4. Use essas coordenadas diretamente na acao.

TECNICA DE GRADE MENTAL:
- Divida o screenshot em quadrantes para estimar posicoes com precisao.
- Para uma imagem 1366x768: centro = (683, 384), canto sup-esq = (0, 0), canto inf-dir = (1366, 768).
- Barra de tarefas do Ubuntu: geralmente no topo (y ~ 0-28) ou lateral esquerda.
- Botoes de janela (fechar/minimizar/maximizar): canto superior-direito ou superior-esquerdo da janela.
- SEMPRE clique no CENTRO do botao ou elemento, NUNCA na borda.

=== ACOES DISPONIVEIS ===

MOUSE:
- {"type": "click", "x": 500, "y": 300} — Clique simples. SEMPRE clique no CENTRO EXATO do elemento alvo.
- {"type": "double_click", "x": 500, "y": 300} — Duplo clique. Para abrir arquivos, selecionar palavras.
- {"type": "right_click", "x": 500, "y": 300} — Clique direito. Abre menus de contexto.
- {"type": "move", "x": 500, "y": 300} — Mover cursor sem clicar. Para hover em menus.
- {"type": "drag", "from_x": 100, "from_y": 200, "to_x": 400, "to_y": 200} — Arrastar.
- {"type": "scroll", "x": 500, "y": 300, "direction": "down", "amount": 3} — Rolar. direction: "up"/"down".

TECLADO:
- {"type": "type", "text": "Ola mundo"} — Digitar texto. Suporta acentos e UTF-8 completo.
- {"type": "key", "key": "enter"} — Tecla unica. Disponiveis: enter, tab, escape, backspace, delete, up, down, left, right, home, end, pageup, pagedown, space, f1-f12, super.
- {"type": "hotkey", "keys": ["ctrl", "c"]} — Combinacao. Exemplos: ["ctrl","c"] copiar, ["ctrl","v"] colar, ["ctrl","a"] selecionar tudo, ["ctrl","l"] barra de endereco, ["ctrl","t"] nova aba, ["ctrl","w"] fechar aba, ["alt","f4"] fechar janela, ["ctrl","alt","t"] terminal, ["super"] lancador.
- {"type": "key_down", "key": "shift"} / {"type": "key_up", "key": "shift"} — Segurar/soltar tecla.

APLICATIVOS:
- {"type": "open_app", "app": "chrome"} — Abrir app. Nomes: chrome, firefox, terminal, files, calculator, code, vscode, libreoffice, gimp, vlc, spotify, telegram, discord, etc.
- {"type": "run_command", "command": "ls -la /home"} — Executar comando bash. Retorna stdout/stderr.

NAVEGACAO WEB:
- {"type": "navigate", "url": "https://web.whatsapp.com"} — MELHOR forma de abrir sites. Foca barra de endereco, limpa, digita URL, pressiona Enter. SEMPRE use em vez de clicar na barra manualmente.

JANELAS:
- {"type": "focus_window", "title": "Chrome"} — Trazer janela para frente.
- {"type": "close_window", "title": "Notepad"} — Fechar janela.
- {"type": "maximize_window", "title": "Chrome"} — Maximizar janela.

ESPERA:
- {"type": "wait", "ms": 2000} — Aguardar milissegundos. ESSENCIAL apos abrir apps ou navegar paginas.

=== NAVEGACAO EM NAVEGADORES WEB (ESTRATEGIA AVANCADA) ===

Quando estiver em um navegador web, use estas tecnicas para navegacao PRECISA:

HIERARQUIA DE CONFIABILIDADE (do mais ao menos confiavel):
1. ATALHOS DE TECLADO: Ctrl+L (barra endereco), Ctrl+T (nova aba), Ctrl+W (fechar aba), Ctrl+F (buscar na pagina), Tab (proximo campo), Shift+Tab (campo anterior), Enter (confirmar/enviar).
2. ACAO "navigate": Para URLs, SEMPRE use navigate. Nunca clique na barra de endereco.
3. NAVEGACAO POR Tab: Em formularios, use Tab para pular entre campos — muito mais confiavel que cliques.
4. CLIQUES PRECISOS: Quando necessario, identifique o CENTRO do elemento com cuidado extremo.

IDENTIFICACAO DE ELEMENTOS NO NAVEGADOR:
- Botoes: bordas definidas com texto centralizado. Clique no CENTRO do texto.
- Links: texto sublinhado ou colorido. Clique no MEIO do texto.
- Campos de input: retangulos claros/brancos. Clique no CENTRO da area.
- Menus dropdown: clique na seta ou texto do menu.
- Abas: clique no CENTRO do texto da aba.
- Barras de rolagem: prefira scroll com acao "scroll" em vez de clicar na barra.

FORMULARIOS WEB:
- Use Tab para navegar entre campos (MUITO mais confiavel que cliques).
- Apos digitar em um campo, Tab vai ao proximo campo.
- Enter submete o formulario.
- Se Tab nao funcionar, clique no CENTRO do campo.

=== GUIAS GERAIS LINUX ===

ABRINDO APLICATIVOS:
- Primario: open_app com nome. Ex: {"type": "open_app", "app": "chrome"}
- Alternativo: run_command. Ex: {"type": "run_command", "command": "google-chrome"}
- Ultimo recurso: key "super" → wait 500ms → type nome → wait 1000ms → key "enter"
- SEMPRE espere 2000-3000ms apos abrir qualquer app.

NAVEGACAO WEB:
- Abrir site: open_app navegador → wait 2000ms → navigate URL → wait 3000-5000ms
- NUNCA clique na barra de endereco. Use SEMPRE navigate.
- Se a pagina nao carregou, wait e tente novamente.

WHATSAPP WEB:
1. open_app "chrome" → wait 2000ms
2. navigate "https://web.whatsapp.com" → wait 5000ms
3. Se logado: clique na caixa de pesquisa (campo "Pesquisar" no topo esquerdo)
4. type nome do contato → wait 1000ms
5. Clique no contato nos resultados
6. wait 500ms → clique no campo de mensagem (barra inferior)
7. type a mensagem → key "enter"

TERMINAL:
- Abrir: hotkey ["ctrl", "alt", "t"] ou open_app "terminal"
- Espere 1000ms, depois type comando + key "enter"

EVITANDO FALHAS:
- ESPERAS: Sempre use "wait" apos abrir apps (2000-3000ms), carregar paginas (3000-5000ms), transicoes (1000-2000ms), apos cliques (500-1000ms).
- RECUPERACAO DE CLIQUES: Se o screenshot NAO mudou apos seu clique, o clique ERROU o alvo. NAO repita o mesmo clique. Em vez disso: (a) reanalise o screenshot e clique em posicao ligeiramente diferente — mais ao CENTRO do elemento, (b) use atalho de teclado equivalente, (c) use Tab para navegar, (d) tente abordagem completamente diferente.
- MENUS: Se um menu fechou, clique novamente no botao que o abriu.
- POPUPS: Feche popups inesperados com botao X, Escape, ou "OK"/"Fechar".

PROATIVIDADE:
- Quebre tarefas vagas em passos concretos.
- NAO peca ajuda ao usuario. Voce tem autonomia total.
- Resolva obstaculos sozinho.

=== REGRAS ABSOLUTAS ===
- Retorne SOMENTE JSON valido. Nenhum texto antes ou depois.
- SEMPRE inclua seu raciocinio no campo "thinking".
- Execute APENAS UMA acao por turno.
- Use coordenadas em pixels do screenshot que voce ve. Elas serao convertidas automaticamente.
"""

# ---------------------------------------------------------------------------
# SYSTEM PROMPTS — WINDOWS (PT-BR)
# ---------------------------------------------------------------------------

_VISION_SYSTEM_PROMPT_WINDOWS = """Voce e o ALAHA, um agente de IA avancado e totalmente autonomo que controla um computador Windows.
Voce possui acesso visual COMPLETO a tela atraves de screenshots em tempo real.
Seu objetivo e completar as tarefas do usuario de forma eficiente, inteligente e sem pedir ajuda.

=== COMO FUNCIONA ===

A cada turno voce recebe um screenshot da tela e deve:
1. PENSAR: Analisar a tela cuidadosamente. O que mudou? Onde estamos no plano? Qual e o proximo passo exato?
2. AGIR: Escolher EXATAMENTE UMA acao para executar.

=== SISTEMA DE COORDENADAS (IMPORTANTISSIMO) ===

As coordenadas X,Y devem corresponder DIRETAMENTE ao screenshot que voce esta vendo.
- O ponto (0, 0) e o canto SUPERIOR ESQUERDO.
- A resolucao do screenshot e informada a cada passo.
- Suas coordenadas serao convertidas automaticamente para a resolucao real da tela.
- NAO tente converter coordenadas. Use EXATAMENTE as posicoes da imagem.
- SEMPRE clique no CENTRO EXATO do elemento alvo (nao na borda).

TECNICA DE GRADE MENTAL:
- Divida o screenshot em quadrantes para precisao.
- Barra de tarefas do Windows: geralmente na parte inferior (y proximo ao maximo).
- Botoes de janela (fechar/minimizar/maximizar): canto superior-direito.

=== FORMATO DE RESPOSTA (SOMENTE JSON) ===

Para executar uma acao:
{"thinking": "Vejo a area de trabalho do Windows. Preciso abrir o Chrome.", "action": {"type": "open_app", "app": "chrome"}}

Para sinalizar conclusao:
{"done": true, "message": "Tarefa concluida com sucesso."}

=== ACOES DISPONIVEIS ===

MOUSE:
- {"type": "click", "x": 500, "y": 300} — Clique no CENTRO EXATO do elemento.
- {"type": "double_click", "x": 500, "y": 300}
- {"type": "right_click", "x": 500, "y": 300}
- {"type": "move", "x": 500, "y": 300}
- {"type": "drag", "from_x": 100, "from_y": 200, "to_x": 400, "to_y": 200}
- {"type": "scroll", "x": 500, "y": 300, "direction": "down", "amount": 3}

TECLADO:
- {"type": "type", "text": "Ola mundo"} — Digitar texto.
- {"type": "key", "key": "enter"} — Teclas: enter, tab, escape, backspace, delete, up, down, left, right, home, end, pageup, pagedown, space, f1-f12, win.
- {"type": "hotkey", "keys": ["ctrl", "c"]}
- {"type": "key_down", "key": "shift"} / {"type": "key_up", "key": "shift"}

APLICATIVOS:
- {"type": "open_app", "app": "chrome"}
- {"type": "run_command", "command": "dir"}

NAVEGACAO WEB:
- {"type": "navigate", "url": "https://google.com"} — MELHOR forma de abrir sites. SEMPRE use em vez de clicar na barra de endereco.

JANELAS:
- {"type": "focus_window", "title": "Chrome"}
- {"type": "close_window", "title": "Notepad"}
- {"type": "maximize_window", "title": "Chrome"}

ESPERA:
- {"type": "wait", "ms": 2000}

=== NAVEGACAO EM NAVEGADORES WEB ===

HIERARQUIA DE CONFIABILIDADE:
1. ATALHOS: Ctrl+L (barra endereco), Ctrl+T (nova aba), Tab (proximo campo), Enter (confirmar).
2. ACAO "navigate": Para URLs, SEMPRE use navigate.
3. Tab: Em formularios, use Tab para pular campos — mais confiavel que cliques.
4. CLIQUES: Quando necessario, clique no CENTRO EXATO do elemento.

ELEMENTOS NO NAVEGADOR:
- Botoes: clique no CENTRO do texto do botao.
- Links: clique no MEIO do texto.
- Campos de input: clique no CENTRO do retangulo do campo.
- Use Tab para navegar formularios.

=== DICAS WINDOWS ===

ABRIR APPS:
1. key "win" → wait 500ms → type nome do app → wait 1000ms → key "enter"
2. Ou use open_app diretamente.

NAVEGACAO: Use "navigate" em vez de clicar na barra de endereco.
ESPERAS: Sempre espere apos abrir apps (2000ms) e apos navegar (3000-5000ms).
RECUPERACAO DE CLIQUES: Se o screenshot NAO mudou apos seu clique, o clique ERROU. NAO repita. Tente: (a) clicar mais ao CENTRO, (b) usar atalho de teclado, (c) Tab, (d) abordagem diferente.

=== REGRAS ABSOLUTAS ===
- Retorne SOMENTE JSON valido.
- SEMPRE inclua "thinking".
- Execute UMA acao por turno.
- Use coordenadas em pixels do screenshot. Elas serao convertidas automaticamente.
"""

# ---------------------------------------------------------------------------
# Seletor de prompt por SO
# ---------------------------------------------------------------------------

VISION_SYSTEM_PROMPT = _VISION_SYSTEM_PROMPT_LINUX if sys.platform.startswith("linux") else _VISION_SYSTEM_PROMPT_WINDOWS


_IS_LINUX = sys.platform.startswith("linux")


def _get_active_window_info() -> dict:
    """Detect the currently focused window (Linux only via xdotool)."""
    if not _IS_LINUX:
        return {}
    try:
        name = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip()
        if not name:
            return {}
        is_browser = any(
            b in name.lower()
            for b in ("chrome", "firefox", "chromium", "edge", "brave", "opera", "mozilla")
        )
        return {"window_name": name, "is_browser": is_browser}
    except Exception:
        return {}


class Orchestrator:
    def __init__(self, connection: ConnectionServer, llm: LLMClient):
        self.connection = connection
        self.llm = llm
        self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _scale_coords(
        action: dict,
        sent_w: int, sent_h: int,
        native_w: int, native_h: int,
    ) -> dict:
        """Scale coordinates from LLM image-space to native screen-space."""
        if sent_w <= 0 or sent_h <= 0:
            return action
        if sent_w == native_w and sent_h == native_h:
            return action

        scale_x = native_w / sent_w
        scale_y = native_h / sent_h
        scaled = dict(action)

        for key in ("x", "from_x", "to_x"):
            if key in scaled and isinstance(scaled[key], (int, float)):
                scaled[key] = int(round(scaled[key] * scale_x))
        for key in ("y", "from_y", "to_y"):
            if key in scaled and isinstance(scaled[key], (int, float)):
                scaled[key] = int(round(scaled[key] * scale_y))

        return scaled

    @staticmethod
    def _clamp_coords(action: dict, native_w: int, native_h: int) -> dict:
        """Clamp coordinates to valid screen bounds."""
        clamped = dict(action)
        for key in ("x", "from_x", "to_x"):
            if key in clamped and isinstance(clamped[key], (int, float)):
                clamped[key] = max(0, min(int(clamped[key]), native_w - 1))
        for key in ("y", "from_y", "to_y"):
            if key in clamped and isinstance(clamped[key], (int, float)):
                clamped[key] = max(0, min(int(clamped[key]), native_h - 1))
        return clamped

    # ------------------------------------------------------------------
    # Vision loop (main instruction handler)
    # ------------------------------------------------------------------

    async def handle_instruction(self, message: dict) -> None:
        session_id = message.get("session_id", "unknown")
        instruction = message.get("instruction", "")

        if not instruction:
            log.warning("Empty instruction received")
            await self._send_error(session_id, 0, "Empty instruction")
            return

        if not self.llm.is_configured:
            log.error("LLM not configured, cannot process instruction")
            await self._send_error(session_id, 0, "LLM not configured")
            return

        self._busy = True
        log.info(f"Vision loop started: {instruction[:80]}")
        action_history: list[dict] = []
        stuck_count = 0
        consecutive_errors = 0
        last_action_key: Optional[str] = None

        try:
            for step in range(MAX_VISION_STEPS):
                sc = capture_screenshot()
                screenshot_b64 = sc["image"]
                sent_w = sc["sent_w"]
                sent_h = sc["sent_h"]
                native_w = sc["native_w"]
                native_h = sc["native_h"]

                if not screenshot_b64:
                    await self._send_error(session_id, step, "Failed to capture screenshot")
                    return

                messages = self._build_vision_messages(
                    instruction, action_history, step,
                    stuck_count, consecutive_errors,
                    sent_w=sent_w, sent_h=sent_h,
                    native_w=native_w, native_h=native_h,
                )
                llm_response = await self.llm.chat_with_vision(messages, screenshot_b64)
                result = parse_single_action(llm_response)

                if result is None:
                    log.warning(f"LLM returned invalid response at step {step + 1}, retrying...")
                    action_history.append({
                        "action": {"type": "parse_error"},
                        "success": False,
                        "error": "Resposta invalida da LLM. Retorne SOMENTE JSON valido.",
                        "thinking": "",
                    })
                    consecutive_errors += 1
                    if consecutive_errors >= 5:
                        await self._send_error(session_id, step, "LLM returned 5 consecutive invalid responses")
                        return
                    continue

                if result.get("done"):
                    done_message = result.get("message", "")
                    log.info(f"Task complete at step {step + 1}: {done_message}")
                    final_sc = capture_screenshot()
                    if final_sc["image"]:
                        await self.connection.send({
                            "type": "screenshot",
                            "session_id": session_id,
                            "action_index": step,
                            "screenshot": final_sc["image"],
                            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        })
                    await self.connection.send({
                        "type": "action_complete",
                        "session_id": session_id,
                        "success": True,
                        "total_actions": step,
                        "message": done_message,
                    })
                    return

                thinking = result.pop("__thinking__", "")
                if thinking:
                    log.info(f"[step {step + 1}] thinking: {thinking[:120]}")
                    await self.connection.send({
                        "type": "agent_thinking",
                        "session_id": session_id,
                        "step": step + 1,
                        "thinking": thinking,
                    })

                action_type = result.get("type", "unknown")
                executor = ACTION_MAP.get(action_type)

                if not executor:
                    log.warning(f"Unknown action type at step {step}: {action_type}")
                    action_history.append({"action": result, "success": False, "error": f"Acao desconhecida: {action_type}. Use apenas acoes validas.", "thinking": thinking})
                    consecutive_errors += 1
                    continue

                # --- Scale LLM coords (image-space) → native screen coords ---
                result = self._scale_coords(result, sent_w, sent_h, native_w, native_h)
                result = self._clamp_coords(result, native_w, native_h)

                current_action_key = json.dumps(result, sort_keys=True)
                if current_action_key == last_action_key:
                    stuck_count += 1
                    log.warning(f"Same action repeated ({stuck_count}x): {action_type}")
                    if stuck_count >= 5:
                        await self._send_error(session_id, step, "Bot travado: mesma acao repetida 5 vezes sem progresso")
                        return
                else:
                    stuck_count = 0
                    last_action_key = current_action_key

                log.info(f"Vision step [{step + 1}/{MAX_VISION_STEPS}]: {action_type}")

                exec_result = {"success": False, "message": "Unknown error"}
                try:
                    exec_result = await executor.execute(result)
                    success = exec_result.get("success", False)
                    error_msg = exec_result.get("message", "") if not success else ""
                    action_history.append({"action": result, "success": success, "error": error_msg, "thinking": thinking})
                    if not success:
                        consecutive_errors += 1
                    else:
                        consecutive_errors = 0
                except Exception as e:
                    action_history.append({"action": result, "success": False, "error": str(e), "thinking": thinking})
                    consecutive_errors += 1

                settle_ms = SCREENSHOT_SETTLE_MS
                if action_type in ("open_app", "run_command"):
                    settle_ms = max(settle_ms, 1500)
                elif action_type == "navigate":
                    settle_ms = max(settle_ms, 2000)
                elif action_type == "wait":
                    settle_ms = 100
                await asyncio.sleep(settle_ms / 1000)

                hl_x = exec_result.get("x") if exec_result.get("success") else None
                hl_y = exec_result.get("y") if exec_result.get("success") else None
                post_sc = capture_screenshot(hl_x, hl_y)
                if post_sc["image"]:
                    await self.connection.send({
                        "type": "screenshot",
                        "session_id": session_id,
                        "action_index": step,
                        "screenshot": post_sc["image"],
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    })

            await self._send_error(
                session_id,
                MAX_VISION_STEPS - 1,
                f"Limite de passos ({MAX_VISION_STEPS}) atingido sem completar a tarefa",
            )

        except Exception as e:
            log.error(f"Vision loop error: {e}")
            await self._send_error(session_id, 0, str(e))
        finally:
            self._busy = False

    async def handle_execute_actions(self, message: dict) -> None:
        session_id = message.get("session_id", "unknown")
        actions = message.get("actions", [])

        if not actions:
            await self._send_error(session_id, 0, "No actions provided")
            return

        self._busy = True
        try:
            await self._execute_actions(session_id, actions)
        finally:
            self._busy = False

    async def _execute_actions(self, session_id: str, actions: list[dict]) -> None:
        total = len(actions)
        log.info(f"Executing {total} actions for session {session_id}")

        for i, action in enumerate(actions):
            action_type = action.get("type", "unknown")
            executor = ACTION_MAP.get(action_type)

            if not executor:
                log.warning(f"Unknown action type: {action_type}")
                await self._send_error(session_id, i, f"Unknown action: {action_type}")
                continue

            log.info(f"Action [{i+1}/{total}]: {action_type}")

            try:
                result = await executor.execute(action)

                if not result.get("success"):
                    await self._send_error(session_id, i, result.get("message", "Unknown error"))
                    continue

                await asyncio.sleep(SCREENSHOT_SETTLE_MS / 1000)

                highlight_x = action.get("x")
                highlight_y = action.get("y")
                sc = capture_screenshot(highlight_x, highlight_y)

                if sc["image"]:
                    await self.connection.send({
                        "type": "screenshot",
                        "session_id": session_id,
                        "action_index": i,
                        "screenshot": sc["image"],
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    })

            except Exception as e:
                log.error(f"Action execution error at index {i}: {e}")
                await self._send_error(session_id, i, str(e))

        await self.connection.send({
            "type": "action_complete",
            "session_id": session_id,
            "success": True,
            "total_actions": total,
        })
        log.info(f"All {total} actions completed for session {session_id}")

    def _build_vision_messages(
        self, instruction: str, action_history: list[dict], step: int,
        stuck_count: int = 0, consecutive_errors: int = 0,
        sent_w: int = 0, sent_h: int = 0,
        native_w: int = 0, native_h: int = 0,
    ) -> list[dict]:

        history_text = ""
        if action_history:
            lines = []
            recent = action_history[-12:]
            for i, h in enumerate(recent):
                action_str = json.dumps(h["action"], ensure_ascii=False)
                status = "OK" if h["success"] else f"FALHOU: {h.get('error', '')}"
                thinking_hint = f" | pensou: {h['thinking'][:80]}" if h.get("thinking") else ""
                lines.append(f"  {i + 1}. {action_str} -> {status}{thinking_hint}")
            history_text = "\nHistorico de acoes executadas:\n" + "\n".join(lines)

        warnings = []
        if stuck_count >= 2:
            warnings.append(
                f"AVISO CRITICO - TRAVADO: Voce repetiu a MESMA acao {stuck_count} vezes sem progresso. "
                "Olhe o screenshot com MUITA atencao. Seu clique pode ter errado o alvo ou o app esta lento. "
                "MUDE DE ABORDAGEM AGORA: use navegacao por teclado (Tab, Enter), clique em area diferente, "
                "use um atalho de teclado, ou tente uma estrategia completamente diferente."
            )
        if consecutive_errors >= 2:
            warnings.append(
                f"AVISO - ERROS CONSECUTIVOS: As ultimas {consecutive_errors} acoes FALHARAM. "
                "Leia as mensagens de erro no historico acima. Corrija os parametros ou use um tipo de acao diferente. "
                "Se um app nao abriu, tente run_command ou a tecla super + digitar o nome."
            )

        warning_text = "\n\n" + "\n".join(warnings) if warnings else ""

        steps_remaining = MAX_VISION_STEPS - step - 1
        urgency = ""
        if steps_remaining <= 5:
            urgency = f"\nATENCAO: Restam apenas {steps_remaining} passos. Finalize a tarefa rapidamente ou sinalize conclusao."

        # Active window context (Linux only)
        window_ctx = ""
        win_info = _get_active_window_info()
        if win_info:
            window_ctx = f"\nJanela ativa: {win_info.get('window_name', 'desconhecida')}"
            if win_info.get("is_browser"):
                window_ctx += " [NAVEGADOR DETECTADO — prefira atalhos de teclado e Tab para navegar]"

        user_text = (
            f"Tarefa: {instruction}\n"
            f"Passo atual: {step + 1}/{MAX_VISION_STEPS}\n"
            f"Resolucao do screenshot: {sent_w}x{sent_h} pixels"
            f"{window_ctx}"
            f"{history_text}"
            f"{warning_text}"
            f"{urgency}\n\n"
            "Analise o screenshot atentamente. Use coordenadas baseadas na imagem que voce ve.\n"
            'Responda SOMENTE com JSON valido no formato:\n'
            '{"thinking": "o que eu vejo e o que vou fazer", "action": {...}}\n'
            'Ou {"done": true, "message": "..."} se a tarefa esta completa.'
        )
        return [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]

    async def _send_error(self, session_id: str, action_index: int, message: str) -> None:
        await self.connection.send({
            "type": "error",
            "session_id": session_id,
            "action_index": action_index,
            "message": message,
        })
