import asyncio
import json
import sys
import time
from typing import Optional

from core.logger import get_logger
from core.connection import ConnectionServer
from llm.client import LLMClient
from llm.parser import parse_actions, parse_single_action
from screenshot.capture import capture_screenshot, get_native_size

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

=== ACOES DISPONIVEIS ===

MOUSE:
- {"type": "click", "x": 500, "y": 300} — Clique simples. Use coordenadas EXATAS do screenshot. SEMPRE clique no CENTRO do elemento alvo.
- {"type": "double_click", "x": 500, "y": 300} — Duplo clique. Use para abrir arquivos, selecionar palavras.
- {"type": "right_click", "x": 500, "y": 300} — Clique direito. Abre menus de contexto.
- {"type": "move", "x": 500, "y": 300} — Mover o cursor sem clicar. Use para hover em menus.
- {"type": "drag", "from_x": 100, "from_y": 200, "to_x": 400, "to_y": 200} — Arrastar de um ponto a outro.
- {"type": "scroll", "x": 500, "y": 300, "direction": "down", "amount": 3} — Rolar pagina. direction: "up" ou "down". amount: numero de cliques do scroll.

TECLADO:
- {"type": "type", "text": "Ola mundo"} — Digitar texto. SUPORTA ACENTOS e caracteres especiais (UTF-8 completo). Use para preencher campos, escrever mensagens, digitar URLs.
- {"type": "key", "key": "enter"} — Pressionar uma tecla. Teclas disponiveis: enter, tab, escape, backspace, delete, up, down, left, right, home, end, pageup, pagedown, space, f1-f12, super (tecla do Linux/Windows).
- {"type": "hotkey", "keys": ["ctrl", "c"]} — Combinacao de teclas. Exemplos: ["ctrl", "c"] copiar, ["ctrl", "v"] colar, ["ctrl", "a"] selecionar tudo, ["ctrl", "l"] focar barra de endereco, ["ctrl", "t"] nova aba, ["ctrl", "w"] fechar aba, ["alt", "f4"] fechar janela, ["ctrl", "alt", "t"] abrir terminal, ["super"] abrir lancador de apps.
- {"type": "key_down", "key": "shift"} — Manter tecla pressionada.
- {"type": "key_up", "key": "shift"} — Soltar tecla pressionada.

APLICATIVOS:
- {"type": "open_app", "app": "chrome"} — Abrir aplicativo. Nomes suportados: chrome, firefox, chromium, edge, brave, terminal, files, nautilus, calculator, text-editor, gedit, code, vscode, libreoffice, writer, calc, gimp, vlc, spotify, telegram, discord, slack, obs, settings. O sistema encontra automaticamente o binario correto para sua distribuicao.
- {"type": "run_command", "command": "ls -la /home"} — Executar comando shell. O comando roda em bash e retorna stdout/stderr. Use para operacoes de sistema, instalar pacotes, manipular arquivos, verificar processos, etc. NAO use & no final.

NAVEGACAO WEB:
- {"type": "navigate", "url": "https://web.whatsapp.com"} — MELHOR forma de abrir qualquer site. Funciona com qualquer navegador aberto. Foca a barra de endereco (Ctrl+L), limpa, digita a URL e pressiona Enter. SEMPRE use isso em vez de clicar na barra de endereco manualmente.

JANELAS:
- {"type": "focus_window", "title": "Chrome"} — Trazer janela para frente pelo titulo (parcial). Usa xdotool internamente.
- {"type": "close_window", "title": "Notepad"} — Fechar janela pelo titulo.
- {"type": "maximize_window", "title": "Chrome"} — Maximizar janela.

ESPERA:
- {"type": "wait", "ms": 2000} — Aguardar milissegundos. ESSENCIAL apos abrir apps, navegar para paginas, ou clicar em botoes que carregam conteudo.

=== GUIAS E ESTRATEGIAS PARA LINUX ===

ABRINDO APLICATIVOS:
- Metodo PRIMARIO: use "open_app" com o nome do app. Exemplo: {"type": "open_app", "app": "chrome"}
- Metodo ALTERNATIVO: use "run_command" com o binario. Exemplo: {"type": "run_command", "command": "google-chrome"}
- Se nenhum funcionar: pressione a tecla "super" para abrir o lancador, espere 500ms, digite o nome do app, espere 1000ms, pressione "enter".
- SEMPRE espere 2000-3000ms apos abrir qualquer app antes de interagir com ele.

NAVEGACAO WEB:
- Para abrir um site: PRIMEIRO abra o navegador com open_app, DEPOIS espere 2000ms, DEPOIS use navigate com a URL.
- NUNCA clique manualmente na barra de endereco. Use SEMPRE a acao "navigate".
- Apos navegar para uma pagina, SEMPRE espere 3000-5000ms para a pagina carregar completamente.
- Se a pagina parece nao ter carregado, use wait e tente novamente.

WHATSAPP WEB:
1. open_app "chrome" → wait 2000ms
2. navigate "https://web.whatsapp.com" → wait 5000ms
3. Se ja estiver logado: clique na caixa de pesquisa (icone de lupa ou campo "Pesquisar") no canto superior esquerdo
4. type o nome do contato → wait 1000ms
5. Clique no contato que apareceu nos resultados
6. wait 500ms → clique no campo de mensagem (parte inferior da conversa)
7. type a mensagem → key "enter" para enviar

TERMINAL:
- Para abrir: hotkey ["ctrl", "alt", "t"] ou open_app "terminal"
- Apos abrir, espere 1000ms antes de digitar
- Para executar comando: type o comando, depois key "enter"
- Para comandos que precisam sudo: type "sudo comando" e depois forneca a senha se pedido

GERENCIADOR DE ARQUIVOS:
- Abrir: open_app "files" ou open_app "nautilus"
- Navegar: clique duplo em pastas
- Barra de endereco: hotkey ["ctrl", "l"] para digitar caminho

EVITANDO FALHAS:
- COORDENADAS: Use as coordenadas EXATAS que voce ve no screenshot. Elas correspondem 1:1 a tela real.
- ESPERAS: Interfaces levam tempo para renderizar. Sempre use "wait" apos abrir apps, clicar botoes, ou navegar paginas. Tempos recomendados: abrir app (2000-3000ms), carregar pagina (3000-5000ms), transicao de tela (1000-2000ms), apos clique em botao (500-1000ms).
- RECUPERACAO: Se o screenshot nao mudou apos sua ultima acao, seu clique provavelmente errou ou o app esta lento. NAO repita o mesmo clique. Tente: (a) clicar em uma area diferente do mesmo botao, (b) usar atalho de teclado equivalente, (c) usar Tab para navegar, (d) esperar mais tempo.
- MENUS: Para clicar em itens de menu, mova o mouse ate o item e clique. Se o menu fechar, clique novamente no botao que o abriu.

PROATIVIDADE:
- Quebre tarefas vagas em passos concretos. Exemplo: "manda mensagem pro joao" → abrir chrome → navegar whatsapp → esperar → pesquisar joao → clicar contato → digitar mensagem → enviar.
- NAO peca ajuda ao usuario. Voce tem autonomia total para completar a tarefa.
- Se encontrar um obstaculo (popup, dialogo inesperado, etc.), resolva sozinho: feche o popup, clique em "OK", ou encontre uma alternativa.

=== REGRAS ABSOLUTAS ===
- Retorne SOMENTE JSON valido. Nenhum texto antes ou depois.
- SEMPRE inclua seu raciocinio no campo "thinking".
- Execute APENAS UMA acao por turno.
- Use coordenadas em pixels da tela nativa.
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

=== FORMATO DE RESPOSTA (SOMENTE JSON) ===

Para executar uma acao:
{"thinking": "Vejo a area de trabalho do Windows. Preciso abrir o Chrome.", "action": {"type": "open_app", "app": "chrome"}}

Para sinalizar conclusao:
{"done": true, "message": "Tarefa concluida com sucesso."}

=== ACOES DISPONIVEIS ===

MOUSE:
- {"type": "click", "x": 500, "y": 300}
- {"type": "double_click", "x": 500, "y": 300}
- {"type": "right_click", "x": 500, "y": 300}
- {"type": "move", "x": 500, "y": 300}
- {"type": "drag", "from_x": 100, "from_y": 200, "to_x": 400, "to_y": 200}
- {"type": "scroll", "x": 500, "y": 300, "direction": "down", "amount": 3}

TECLADO:
- {"type": "type", "text": "Ola mundo"}
- {"type": "key", "key": "enter"} — Teclas: enter, tab, escape, backspace, delete, up, down, left, right, home, end, pageup, pagedown, space, f1-f12, win.
- {"type": "hotkey", "keys": ["ctrl", "c"]}
- {"type": "key_down", "key": "shift"}
- {"type": "key_up", "key": "shift"}

APLICATIVOS:
- {"type": "open_app", "app": "chrome"}
- {"type": "run_command", "command": "dir"}

NAVEGACAO WEB:
- {"type": "navigate", "url": "https://google.com"} — Melhor forma de abrir sites.

JANELAS:
- {"type": "focus_window", "title": "Chrome"}
- {"type": "close_window", "title": "Notepad"}
- {"type": "maximize_window", "title": "Chrome"}

ESPERA:
- {"type": "wait", "ms": 2000}

=== DICAS WINDOWS ===

ABRIR APPS (metodo mais confiavel):
1. key "win" → wait 500ms → type nome do app → wait 1000ms → key "enter"
2. Ou use open_app diretamente.

NAVEGACAO: Use "navigate" em vez de clicar na barra de endereco.
ESPERAS: Sempre espere apos abrir apps (2000ms) e apos navegar (3000-5000ms).
RECUPERACAO: Se o screenshot nao mudou, tente abordagem diferente.

=== REGRAS ===
- Retorne SOMENTE JSON valido.
- SEMPRE inclua "thinking".
- Execute UMA acao por turno.
"""

# ---------------------------------------------------------------------------
# Seletor de prompt por SO
# ---------------------------------------------------------------------------

VISION_SYSTEM_PROMPT = _VISION_SYSTEM_PROMPT_LINUX if sys.platform.startswith("linux") else _VISION_SYSTEM_PROMPT_WINDOWS


class Orchestrator:
    def __init__(self, connection: ConnectionServer, llm: LLMClient):
        self.connection = connection
        self.llm = llm
        self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy

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
                screenshot = capture_screenshot()
                if not screenshot:
                    await self._send_error(session_id, step, "Failed to capture screenshot")
                    return

                messages = self._build_vision_messages(instruction, action_history, step, stuck_count, consecutive_errors)
                llm_response = await self.llm.chat_with_vision(messages, screenshot)
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
                    final_screenshot = capture_screenshot()
                    if final_screenshot:
                        await self.connection.send({
                            "type": "screenshot",
                            "session_id": session_id,
                            "action_index": step,
                            "screenshot": final_screenshot,
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
                post_screenshot = capture_screenshot(hl_x, hl_y)
                if post_screenshot:
                    await self.connection.send({
                        "type": "screenshot",
                        "session_id": session_id,
                        "action_index": step,
                        "screenshot": post_screenshot,
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
                screenshot = capture_screenshot(highlight_x, highlight_y)

                if screenshot:
                    await self.connection.send({
                        "type": "screenshot",
                        "session_id": session_id,
                        "action_index": i,
                        "screenshot": screenshot,
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

    def _build_vision_messages(self, instruction: str, action_history: list[dict], step: int, stuck_count: int = 0, consecutive_errors: int = 0) -> list[dict]:
        native_w, native_h = get_native_size()

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

        user_text = (
            f"Tarefa: {instruction}\n"
            f"Passo atual: {step + 1}/{MAX_VISION_STEPS}\n"
            f"Resolucao da tela: {native_w}x{native_h} pixels"
            f"{history_text}"
            f"{warning_text}"
            f"{urgency}\n\n"
            "Analise o screenshot atentamente. Pense sobre o que voce ve e qual deve ser o proximo passo.\n"
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
