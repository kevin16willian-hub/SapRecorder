# SAP Recorder

Aplicação Python para gravar interações com o SAP GUI Scripting e gerar código reutilizável em automações.

## Requisitos

- Windows com o SAP GUI for Windows instalado e aberto.
- SAP GUI Scripting habilitado no cliente e no servidor SAP.
- Python 3.10 ou superior, com a mesma arquitetura (32 ou 64 bits) do SAP GUI.

## Instalação

No PowerShell, na pasta do projeto:

```powershell
python -m pip install -r requirements.txt
```

## Como executar

```powershell
python -m sapgui
```

Na janela do gravador:

1. Clique em **Refresh** para listar as sessões SAP abertas e selecione uma.
2. Clique em **Record** e interaja com o SAP.
3. Clique em **Stop** para encerrar a gravação.
4. Use **Copy** para copiar as linhas geradas ou **Save .py** para salvá-las.

O gravador também registra cliques em células de tabelas e grades ALV. Essa opção pode ser desabilitada antes de iniciar a gravação, desmarcando **Cell clicks**.

## O que é registrado

As ações são convertidas em operações sobre componentes identificados pelo SAP, como atribuições de propriedades e chamadas de métodos. O código gerado usa `session.findById(...)`; para executá-lo, forneça uma sessão SAP válida no contexto da sua automação. Revise e teste o script em um ambiente apropriado antes de usá-lo em processos reais.

## Estrutura do projeto

- `sapgui/connection.py`: conexão com o SAP GUI e descoberta de sessões.
- `sapgui/recorder.py`: gravação de eventos e conversão em passos.
- `sapgui/model.py`: modelos de passos e scripts, com persistência JSON.
- `sapgui/codegen.py`: geração de código Python.
- `sapgui/player.py`: execução de scripts modelados sobre uma sessão.
- `sapgui/ui.py`: interface gráfica do gravador.
- `docs/`: notas técnicas e documentação do comportamento do gravador.

## Documentação adicional

- [Rollback da gravação de cliques em células](docs/cell-click-rollback.md)

## Limitações

- O projeto depende da API COM do SAP GUI for Windows e não funciona em outros sistemas operacionais.
- A gravação exige uma sessão SAP aberta e acessível por meio do SAP GUI Scripting.
- A compatibilidade de arquitetura entre Python e SAP GUI é necessária para a integração COM.
