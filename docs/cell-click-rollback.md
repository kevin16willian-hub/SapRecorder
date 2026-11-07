# Rollback: gravação de cliques em células (table control e ALV grid)

## O que foi adicionado
Um clique simples em uma célula só gera o evento `FocusChanged` (não há `Change` até editar). O gravador agora transforma esse evento em linhas de script:

- Table control: `session.findById(".../tblX/ctxtCAMPO[col,lin]").setFocus()  # Título da coluna: valor`
- ALV grid (não verificado ao vivo): `.currentCellRow = n` e `.currentCellColumn = "COL"  # Título: valor`

## Desligar sem alterar código
- Interface: desmarcar a caixa "Cell clicks" antes de gravar.
- Código: `Recorder(session, cell_clicks=False)`.

## Reverter o código
Em `sapgui/recorder.py`:
1. Remover a constante `_TABLE_CELL`.
2. Em `_Sink`: remover os métodos `FocusChanged` e `_click_steps`, o atributo `_last_click` e o parâmetro `cell_clicks` do `__init__`.
3. Em `Recorder`: remover o parâmetro `cell_clicks` do `__init__` e o argumento passado em `_Sink(self.session, self.cell_clicks)` (voltar para `_Sink(self.session)`).
4. Em `Recorder._emit`: remover o bloco que descarta um `setFocus` repetido no mesmo componente.

Em `sapgui/ui.py`:
5. Remover `self.cell_clicks`, o `ttk.Checkbutton` "Cell clicks" e o argumento `cell_clicks=...` na criação do `Recorder`.

Scripts já gravados continuam válidos: as linhas geradas são chamadas comuns (`setFocus`, `currentCellRow`, `currentCellColumn`).

## Efeitos colaterais conhecidos
- Mais linhas no script (uma por clique em célula diferente da anterior).
- O mesmo clique repetido na mesma célula é descartado.
