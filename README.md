# ALAHA Program

Agente local que roda no PC do usuário. O **ALAHA Dashboard** conecta a ele via WebSocket, envia a API key da LLM e instruções. O Program usa a LLM remota para planejar e executar ações no sistema operacional.

## Como funciona

1. Instale e execute o ALAHA Program
2. O programa mostra seu **SnowflakeID** — copie esse ID
3. No **ALAHA Dashboard**, cole o SnowflakeID e conecte
4. O Dashboard envia a configuração da LLM (API key, endpoint, modelo)
5. O Dashboard envia instruções de alto nível
6. O Program consulta a LLM remota e converte a resposta em ações locais
7. As ações são executadas no PC (mouse, teclado, apps, comandos)
8. Após cada ação, um screenshot é enviado ao Dashboard
9. Ao final, o resultado é reportado ao Dashboard

## Requisitos

- Python 3.11+
- Windows 10+ ou Ubuntu 20.04+

---

## 🪟 Instalação — Windows

### Opção 1: Instalação Completa (recomendado)

```bat
installer\setup_windows.bat
```

Isso irá:
- ✅ Verificar Python
- ✅ Criar ambiente virtual
- ✅ Instalar dependências
- ✅ Gerar executável (.exe)
- ✅ Criar scripts de execução

### Opção 2: PowerShell (rápido)

```powershell
.\installer\quick_install.ps1
```

### Opção 3: Manual

```bat
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python main.py
```

### Executar em Segundo Plano (Windows)

```bat
:: Usando o script gerado:
run_background.bat

:: Ou manualmente:
start /min "" venv\Scripts\pythonw.exe main.py
```

### Iniciar com o Windows

1. Marque a opção **"Iniciar com o Windows"** na interface do programa
2. Ou copie `run_background.bat` para `shell:startup`
3. Ou use o executável `dist\ALAHAProgram.exe` no Startup

---

## 🐧 Instalação — Linux

### Opção 1: One-liner (mais rápido)

```bash
curl -fsSL https://raw.githubusercontent.com/OctoIA25/ALAHA_program/main/install.sh | bash
```

Ou com `wget`:

```bash
wget -qO- https://raw.githubusercontent.com/OctoIA25/ALAHA_program/main/install.sh | bash
```

Isso irá:
- ✅ Verificar Python
- ✅ Clonar o repositório
- ✅ Criar ambiente virtual
- ✅ Instalar dependências
- ✅ Criar comando `alaha`
- ✅ Iniciar o programa

### Opção 2: Git Clone (manual)

```bash
# Clone o repositório
git clone https://github.com/OctoIA25/ALAHA_program.git ~/.local/share/alaha-program
cd ~/.local/share/alaha-program

# Instale o comando global (uma vez)
bash install.sh

# Depois é só rodar:
alaha
```

No primeiro `alaha`, ele faz bootstrap automático:
- ✅ Instala `python3-tk`/`python3-dev` (quando necessário, via `sudo apt`)
- ✅ Cria `venv` se não existir
- ✅ Instala/atualiza dependências Python
- ✅ Inicia o ALAHA Program

### Opção 3: Setup Completo (com systemd)

```bash
bash installer/setup_linux.sh
```

Isso cria comandos `alaha-program`, `alaha-program-start`, `alaha-program-stop` e serviço systemd.

### Executar em Segundo Plano (Linux)

```bash
# Usando nohup:
nohup alaha &

# Ou usando systemd:
systemctl --user start alaha-program
```

### Iniciar com o Sistema (systemd)

```bash
# Ativar início automático:
systemctl --user enable alaha-program

# Verificar status:
systemctl --user status alaha-program

# Parar:
systemctl --user stop alaha-program
```

### Atualizar o Programa

Sempre que você subir um commit novo, atualize com:

```bash
alaha-update
```

Ou manualmente:

```bash
cd ~/.local/share/alaha-program
git pull
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📦 Gerar Executável Windows

```bat
venv\Scripts\python installer\build_executable.py
```

O executável será gerado em `dist\ALAHAProgram.exe`

## Protocolo de mensagens (para o Dashboard)

O Dashboard conecta ao Program via WebSocket na **porta 7778**.

### Dashboard → Program

#### Configurar LLM
```json
{
  "type": "configure_llm",
  "api_key": "sk-...",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4o"
}
```

#### Enviar instrução (LLM decide as ações)
```json
{
  "type": "instruction",
  "session_id": "uuid",
  "instruction": "Abra o Chrome e pesquise por ALAHA AI"
}
```

#### Enviar ações diretas (sem LLM)
```json
{
  "type": "execute_actions",
  "session_id": "uuid",
  "actions": [
    { "type": "open_app", "app": "chrome" },
    { "type": "wait", "ms": 1500 },
    { "type": "type", "text": "ALAHA AI" },
    { "type": "key", "key": "enter" }
  ]
}
```

### Program → Dashboard

#### Screenshot após ação
```json
{
  "type": "screenshot",
  "session_id": "uuid",
  "action_index": 0,
  "screenshot": "<base64>",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

#### Conclusão
```json
{
  "type": "action_complete",
  "session_id": "uuid",
  "success": true,
  "total_actions": 4
}
```

#### Erro
```json
{
  "type": "error",
  "session_id": "uuid",
  "action_index": 2,
  "message": "Window not found"
}
```

## Build do executável

```bat
python installer/build_executable.py
```

O executável será gerado em `dist/ALAHAProgram.exe`.

## Estrutura

```
alaha-program/
├── main.py                  # Entry point
├── config.json              # Gerado na 1ª execução (snowflake_id)
├── requirements.txt
├── README.md
├── install.sh               # Instalador one-liner para Linux
├── core/
│   ├── identity.py          # SnowflakeID
│   ├── config.py            # Configuração local mínima
│   ├── connection.py        # WebSocket server (porta 7778)
│   ├── heartbeat.py         # Heartbeat
│   ├── dispatcher.py        # Roteamento de mensagens
│   ├── orchestrator.py      # Orquestrador LLM + ações
│   └── logger.py            # Logging central
├── actions/
│   ├── base.py              # Classe base
│   ├── mouse.py             # Mouse actions
│   ├── keyboard.py          # Keyboard actions
│   ├── apps.py              # Open/run apps
│   ├── windows.py           # Window management
│   └── terminal.py          # Wait / terminal
├── llm/
│   ├── client.py            # Cliente HTTP para LLM
│   └── parser.py            # Parser de resposta da LLM
├── screenshot/
│   └── capture.py           # Captura e encode
├── ui/
│   └── main_window.py       # Interface visual mínima
└── installer/
    ├── install_windows.bat  # Instalador Windows
    ├── install_linux.sh     # Instalador Linux
    └── build_executable.py  # PyInstaller build
```

## Segurança

- `snowflake_id` imutável após geração
- Validação estrita de ações antes da execução
- WebSocket server escuta somente conexões locais ou da rede configurada
- O Program não armazena API keys — recebe do Dashboard em tempo real
