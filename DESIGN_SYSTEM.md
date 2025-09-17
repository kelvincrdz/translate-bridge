# Design System & UI Guidelines

> Versão 1.0 – Data: 2025-09-17  
> Escopo: Interface Django (templates + CSS + JS utilitário) reconstruída a partir do design base de `Font_figma`.

## 1. Princípios de Design
- Consistência semântica: classes e tokens expressam função (ex: `--primary`, `btn-destructive`).
- Acessibilidade primeiro: contraste adequado, foco visível, navegação por teclado completa.
- Escalabilidade leve: zero build obrigatório (Tailwind CDN) + tokens em CSS custom properties.
- Modo de leitura confortável: foco em tipografia, espaçamento respirável e controle de preferências do leitor.
- Progressive Enhancement: JS adiciona conforto (toasts, tema, progresso) sem quebrar funcionalidade base.

## 2. Arquitetura Frontend
- Templates Django renderizam layout e dados iniciais.
- CSS único em `static/css/style.css` definindo tokens + componentes.
- JS modular em `static/js/`:
  - `utils.js`: helpers (debounce, throttle, storage, fetch CSRF, cls merge).
  - `theme.js`: tema (light/dark/sepia) + preferências de leitura (fonte, tamanho, altura de linha, largura de coluna, cor de fundo de leitura).
  - `toast.js`: sistema de notificações e loading overlay.
  - `library.js`: uploads, tradução placeholder, deleção e downloads.
- Theming: alternância via classe `dark` no `<html>` + custom properties. Estado persistido (localStorage) e sincronizado opcionalmente via endpoint.

## 3. Design Tokens
Tokens expostos como CSS Custom Properties (modo claro: `:root`; modo escuro: `.dark`).

### 3.1. Cores Base & Semânticas
```
--background            #ffffff
--foreground            #020817
--muted                 #eef2f7
--muted-foreground      #687288
--popover               #ffffff
--popover-foreground    #020817
--border                #dae0e7
--input                 #dae0e7
--input-background      #f8fafc
--card                  #ffffff
--card-foreground       #020817
--primary               oklch(55% 0.18 269)
--primary-foreground    #ffffff
--secondary             #e0e7ef
--secondary-foreground  #1d2735
--accent                #e0e7ef
--accent-foreground     #1d2735
--destructive           #d92d20
--destructive-foreground #ffffff
--ring                  #3366ff
--sidebar-background    #ffffff
--sidebar-foreground    #0f172a
--sidebar-primary       #1d4ed8
--sidebar-primary-foreground #ffffff
--sidebar-accent        #2563eb
--sidebar-accent-foreground #ffffff
--sidebar-border        #e2e8f0
--sidebar-ring          #1d4ed8
```

```
.dark overrides →
--background: #0f172a
--foreground: #f1f5f9
--muted: #1e293b
--muted-foreground: #94a3b8
--popover: #0f172a
--popover-foreground: #f1f5f9
--border: #334155
--input: #334155
--input-background: #1e293b
--card: #0f172a
--card-foreground: #f1f5f9
--primary: oklch(70% 0.16 272)
--primary-foreground: #1e293b
--secondary: #1e293b
--secondary-foreground: #f1f5f9
--accent: #1e293b
--accent-foreground: #f1f5f9
--destructive: #f87171
--destructive-foreground: #0f172a
--ring: #6385ff
--sidebar-background: #0f172a
--sidebar-foreground: #f1f5f9
--sidebar-primary: #3b82f6
--sidebar-primary-foreground: #1e293b
--sidebar-accent: #1e293b
--sidebar-accent-foreground: #f1f5f9
--sidebar-border: #1e293b
--sidebar-ring: #1e40af
```

### 3.2. Tipografia
```
--font-sans: system-ui, sans-serif
--font-mono: ui-monospace, SFMono-Regular, Menlo, monospace
--font-weight-normal: 400
--font-weight-medium: 500
--font-weight-semibold: 600
--font-weight-bold: 700
```

### 3.3. Radius
```
--radius: 0.5rem /* base corner */
```
Componentes derivam sub-raios com operações: `calc(var(--radius) - 4px)` em elementos circulares/pílula.

### 3.4. Z-Index Layering
```
.toast z ~ contextual acima de conteúdo regular
.loading-overlay acima de toasts (quando ativo)
.dropdown / popover (quando adicionados futuramente) seguirão +10 step
```
(Formalização futura: criar escala ex: 0, 10, 20, 30, 40.)

### 3.5. Paleta de Gráficos
```
--chart-1 210 70% 50%
--chart-2 280 65% 60%
--chart-3 340 75% 55%
--chart-4 120 60% 45%
--chart-5 30  80% 55%
```
Uso: gerar cores HSL dinamicamente `hsl(var(--chart-1))`.

## 4. Escalas & Espaçamento (Implicítos)
Utilizamos Tailwind CDN para spacing (p-*, m-*, gap-*) sem redefinir tokens próprios. Futuro: extrair escala oficial caso build seja introduzido.

## 5. Theming & Estados
- Alternância: botão / toggle adiciona ou remove classe `dark` em `<html>`.
- Preferências leitor: custom properties dinâmicas (`--reader-font-size`, `--reader-line-height`, `--reader-font-family`).
- Sepia / High-contrast (planejado): strategy → aplicar classe adicional (`.sepia`, `.contrast`) sobrepondo subset de tokens.
- Persistência: localStorage chave `theme` e JSON de preferências `readerPrefs`.
- Sincronização opcional servidor: POST para endpoint `/api/theme/` quando existir sessão autenticada.

## 6. Componentes
Cada componente possui base de util classes. Nota: arquivo atual contém diretivas `@apply` que só produzem CSS válido com pipeline Tailwind (PostCSS). Sem build, estas seções servem como documentação. Duas opções:
1. Introduzir build (recomendado médio prazo).
2. Substituir `@apply` por classes utilitárias diretamente em templates (trade-off: repetição maior).

### 6.1. Botões (`.btn` variantes)
Estados: hover, focus visível (`ring`), disabled (`opacity-50 cursor-not-allowed`). Variantes semânticas: default, destructive, outline, secondary ghost, link. Ícones podem ser alinhados via flex utilities.

### 6.2. Cards
Estrutura: `.card` → (opcional) `.card-header` (.card-title, .card-description) + `.card-content` + `.card-footer`.
Uso: agrupar informação densa (listas de livros, modais, formulários pequenos).

### 6.3. Badge
Classes: `.badge`, variantes: `-default`, `-secondary`, `-destructive`, `-outline`. Uso para status, contagem ou filtros ativos.

### 6.4. Form Inputs
`.input`, `.textarea`, `.label`. Estados: disabled, focus ring, placeholder atenuado. Input base usa `bg-input-background` + borde semântica `--input`.

### 6.5. Progress Bar
Contêiner: `.progress`; indicador dinâmico `.progress-indicator` (largura controlada inline via style width: <percent>). Altura padrão 1rem (h-4). Uso principal: progresso de leitura.

### 6.6. Toasts
Estrutura: `.toast` + modificadores (`.toast-success`, `.toast-error`, `.toast-warning`, `.toast-info`). Entrada animada (`slideInRight`), remoção adiciona `.slide-out` (animação `slideOutRight`). Fechamento manual: botão `.toast-close`.

### 6.7. Scroll Area & Scrollbar
`.scroll-area`, `.scroll-area-viewport`, `.custom-scrollbar` com personalização WebKit + fallback padrão em Firefox (thin + cores tokenizadas).

### 6.8. Reader Content
Classe raiz `.reader-content` aplica fonte dinâmica e tipografia semântica (margens em títulos, parágrafos, blockquotes com borda `--accent`). Adequado para renderização de capítulos EPUB extraídos.

## 7. Padrões de Interação
- Foco: sempre utilizamos `focus-visible:ring-2` + `ring-offset` para contraste sobre fundos variados.
- Hover: intensifica cor de fundo (`/80`) ou sublinha (em links). Evitar depender apenas de cor; ícones/alterações de elevação recomendadas futuramente.
- Feedback imediato: toasts aparecem no canto (stack vertical) em até 300ms após ação.
- Progresso de leitura: throttle em scroll para evitar custo excessivo; salvamento eventual via endpoint.
- Upload: feedback visual (loading overlay) + toast sucesso/erro.

## 8. Acessibilidade
- Contraste: paleta atende níveis AA para texto normal (verificar periódicamente após ajustes de cor primária okLCH → testar via ferramenta). 
- Foco: nunca ocultar outline por convenção; substituição sempre com ring visível.
- Semântica: usar `<button>` real para ações; evitar spans clicáveis.
- Prefs do leitor: aumentos de fonte e line-height não devem quebrar layout (usar unidades relativas e `overflow-wrap:anywhere` futuro se necessário).
- Animações: curtas (<400ms) e não essenciais. Fornecer futura opção de reduzir movimento (`prefers-reduced-motion`).

## 9. JavaScript Utilities (Contratos)
- `fetchWithCSRF(url, options)` adiciona header `X-CSRFToken` + trata JSON/erros.
- `debounce(fn, delay)` e `throttle(fn, interval)` para eventos scroll/resize.
- `savePreference(key, value)` e `loadPreference(key, fallback)` abstraem localStorage com fallback.
- `ThemeManager` expõe: `init()`, `setTheme(mode)`, `cycleTheme()`, `applyReaderPrefs(prefs)`.
- `ToastManager`: `show(message, type, options)`, `success()`, `error()`, `info()`, `warning()`, `dismiss(id)`.
- Loading overlay: `showLoading(message)` / `hideLoading()` integrados no mesmo módulo de toast.

## 10. Estrutura de Templates
- `base.html`: layout global, inclui CSS, scripts, toggles, container de toasts, overlay e define data attributes.
- `login.html`, `library.html`, `reader.html`: páginas funcionais; cada uma deve se apoiar apenas nos componentes listados.
- Reuso: blocos de card + botões mantêm consistência sem duplicar estilos inline.

## 11. Convenções de Nomenclatura
- Variáveis CSS: `--<categoria>-<papel>` (ex: `--sidebar-primary-foreground`).
- Classes utilitárias derivadas de Tailwind mantidas sem prefixo extra.
- Componentes com padrão BEM simplificado: `.card-*`, `.toast-*`, `.badge-*`.
- JS: camelCase para funções, PascalCase para construtores (ex: `ThemeManager`).

## 12. Fluxo de Contribuição
1. Adicionar novo token → definir em `:root` + variante em `.dark` (se aplicável) + documentar neste arquivo.
2. Criar componente → prototipar usando util classes. Se repetição surgir, considerar extrair classe com `@apply` (build futuro) ou documentar pattern.
3. Garantir acessibilidade → foco testado via teclado, contraste verificado.
4. Adicionar JS → função pura no módulo existente ou novo módulo em `static/js/` nome descritivo.
5. Atualizar seção relevante neste markdown antes do merge.

## 13. Debt / Futuras Melhorias
- Substituir `@apply` via pipeline oficial (Tailwind CLI ou PostCSS) para produção de CSS expandido.
- Introduzir tokens de spacing e tipografia escalável (ex: `--space-1..n`, `--font-size-sm/md/lg`).
- Modo `sepia` e `high-contrast` (extender classes + tokens parciais).
- Componente de dialog acessível (focus trap) em vez de modais simples.
- Preferências de leitura persistidas no servidor por usuário.
- Suporte a `prefers-reduced-motion` e redução de animações.
- Internacionalização de rótulos UI (hoje PT-BR hardcoded em várias partes).
- Extração de cores para escalas (primary-50..900) se gradientes forem adotados.

## 14. Checklist de Qualidade (Antes de Merge)
- [ ] Tokens novos definidos em claro/escuro.
- [ ] Contraste verificado (WCAG AA) para primário, texto-muted, destructive.
- [ ] Componentes possuem estados hover + focus coerentes.
- [ ] Sem regressões de layout em fonte 125% + line-height 1.8.
- [ ] Nenhum seletor órfão (classe declarada sem uso ou vice-versa) – executar auditoria manual.
- [ ] Documentação atualizada (este arquivo revisado).

## 15. Referências
- Tailwind Design Tokens (conceitos) – inspiração para semântica & util classes.
- W3C WCAG 2.1 AA – contraste / acessibilidade.
- OKLCH Color Space – melhor previsibilidade perceptual na escolha de cores primárias.

---
Manter este documento versionado. Alterações significativas: incremente versão e adicione changelog futuro.

---

## 16. Atualizações 1.1 (Unificação & Acessibilidade)

### 16.1. Unificação de Tokens
- Arquivo fonte agora: `static/css/tokens.css` (antes fragmentado em `style.css` + `globals.css`).
- `globals.css` (área React) deixou de declarar paleta; apenas expõe ajustes tipográficos e mapping secundário.
- Semântica única para cores: qualquer novo componente deve consumir somente variáveis `--background|--foreground|--primary|--secondary|--accent|--muted|--destructive|--border|--input|--ring`.

### 16.2. Padrão de Tema
- Alternância: elementos com `[data-theme-toggle]` disparam `window.setAppTheme(next)` provido por `theme.js`.
- Persistência local: `localStorage.theme` (light|dark). Preferência de sistema respeitada no primeiro load se não houver chave.
- Dark mode aplica classe `dark` no `<html>` e relies em overrides em `tokens.css`.

### 16.3. Dialog Acessível (DialogA11y)
Arquivo: `static/js/dialog.js`.
- API: `DialogA11y.openDialog(id)`, `DialogA11y.closeDialog(id)`.
- Features: foco inicial no primeiro elemento interativo, trap de `Tab/Shift+Tab`, restauração de foco ao fechar, `Esc` fecha o topo da stack, múltiplos modais empilháveis.
- Marcação mínima: contêiner com `id="<name>-modal"` + classe de backdrop + atributo `data-dialog`; interno com `role="document"`; título `<h2|h3>` ou `[data-dialog-title]` (id auto-gerado se ausente).
- Botões de fechamento usam `[data-dialog-close="<id>"]` (listener genérico no util) sem necessidade de JS adicional.
- Backdrop click: listener existente fecha apenas o modal clicado (evita fechar outros abertos em stack).

### 16.4. Migração de Modais Existentes
- `library.html` e `reader.html` migrados para DialogA11y. Funções antigas `showModal/hideModal` substituídas em `library.js` por wrappers que chamam `DialogA11y`.
- Removidas duplicações de lógica `Esc` e manipulação manual de classes.

### 16.5. Ações Recomendadas Restantes
- Converter painel de configurações do leitor em dialog verdadeiro (foco / trap) ou adicionar foco inicial + role adequado.
- Introduzir testes manuais de navegação por teclado (script de QA) antes de liberar.

### 16.6. Boas Práticas para Novos Modais
1. Criar contêiner backdrop + flex center com `hidden` padrão.
2. Adicionar `data-dialog` e id único.
3. Interno: `role="document"` e heading com texto claro de ação.
4. Usar `[data-dialog-close]` em todos os botões de fechar ou cancelar.
5. Não remover foco outline; preferir `outline-offset:2px` ou `ring` nativo.
6. Conteúdo inicial focável deve ser o primeiro botão de ação principal ou o título (fallback).

### 16.7. Changelog Resumido
- (+) `tokens.css` centralizado.
- (+) `DialogA11y` util implementado.
- (~) `globals.css` simplificado (remoção de `@apply`, `@theme`).
- (~) Modais refatorados para acessibilidade.
- (-) Dependência de manipulação manual de classes para modais.

