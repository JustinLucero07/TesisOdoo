# Análisis Experto — Reportes, Flujo de Ventas y Cabos Sueltos

> Auditoría técnica del sistema · 2026-06-10 · Basada en lectura del código real

---

## 1. EL PROBLEMA MÁS IMPORTANTE: el flujo de venta está roto

Hoy una propiedad puede llegar a "Vendida" por **3 caminos distintos que no se hablan entre sí**:

| Camino | Qué hace | Qué NO hace |
|--------|----------|-------------|
| Botón **"Vender Propiedad"** (wizard) | Estado→vendido, comisión, comprador, precio | ❌ NO crea orden de venta · ❌ NO crea factura |
| Botón **"Generar Factura"** | Factura borrador + estado→vendido | ❌ NO confirma factura · ❌ NO crea orden · ❌ NO comisión |
| `action_create_sale_order` (sin botón visible) | Crea orden de venta | ❌ NO confirma · ❌ NO marca vendida · ❌ NO factura |
| `sale.order.action_confirm` (override) | Solo escribe mensajes en el chatter | ❌ NO marca la propiedad vendida · ❌ NO factura |

**Consecuencia grave:** si vendes con el wizard (el camino normal), la venta **NO aparece** en el módulo nativo de **Ventas (sale.order)** ni en **Facturación (account.move)**. Por eso los reportes nativos de Odoo salen vacíos o inconsistentes — justo lo que notaste.

### ✅ Flujo profesional propuesto (un solo camino ordenado)

```
[Vender Propiedad] (wizard)
        │
        ├─ 1. Crea y CONFIRMA la Orden de Venta (sale.order)  → módulo Ventas
        │
        ├─ 2. Genera y CONTABILIZA la Factura (account.move)  → módulo Facturación
        │      desde la orden (con trazabilidad origen)
        │
        ├─ 3. Marca la propiedad como Vendida (state=sold)
        │
        └─ 4. Registra la Comisión del asesor (estate.commission)
```

Con esto, cada venta queda registrada en **Ventas + Facturación nativos**, y los reportes estándar de Odoo (y los tuyos) cuadran. El wizard tendría opciones: *"¿Confirmar orden?"* y *"¿Contabilizar factura?"* (checkboxes) para flexibilidad.

**Limpieza asociada:** eliminar/ocultar los botones redundantes ("Generar Factura" suelto, `action_create_sale_order` huérfano) para que haya **una sola forma** de vender.

---

## 2. REPORTES — análisis sección por sección

| Sección | Estado | Diagnóstico |
|---------|--------|-------------|
| **Dashboard General** (board) | ⚠️ Redundante | Es un `board.board` con gráficos nativos. Se solapa con "KPIs y Métricas". Dos dashboards confunden. |
| **KPIs y Métricas** (estate.dashboard) | 🟡 Mejorable | Form con HTML generado en Python + hex hardcodeados (no usa la paleta nueva). Ya le agregamos Chart.js y PDF. |
| **Ventas** (7 submenús) | ⚠️ Saturado | Mezcla acciones gráficas sueltas + wizard. Varias ya están como botones en el dashboard → duplicación. |
| **Análisis** (7 submenús) | ✅ Bien | Vistas nativas graph/pivot/list. Profesional y consistente. No tocar. |
| **Informes** | 🟡 OK | Exportar Datos + Liquidación Comisiones. Funcional. |
| **Promedio de Ventas** (wizard) | 🔴 BUG | Muestra **"10000%"** y **"3846%"**. Causa: campos guardan 0-100 pero la vista usa `widget="percentage"` que multiplica ×100 otra vez. |

### Recomendaciones de reportes
1. 🔴 **Arreglar el bug de porcentajes** (10000% → 100%). Fix simple: guardar como ratio 0-1 o quitar el widget.
2. 🟡 **Unificar los dos dashboards** en uno solo ("Dashboard" con pestañas), o renombrar para que no se confundan.
3. 🟡 **Reducir el menú "Ventas"**: dejar wizard + 2 gráficos clave; el resto vive en el dashboard.
4. 🟢 **Aplicar la paleta `--inmobi-*`** a los HTML del dashboard (hoy usan hex sueltos #1e40af, etc.).

---

## 3. CABOS SUELTOS por módulo

| Módulo | Hallazgo | Severidad |
|--------|----------|-----------|
| estate_management | 3 botones de venta paralelos (ver §1) | 🔴 Alta |
| estate_management | `action_create_sale_order` sin botón → método muerto | 🟡 Media |
| estate_reports | Bug % en wizard de ventas | 🔴 Alta |
| estate_reports | Dashboard duplicado (board + KPIs) | 🟡 Media |
| estate_reports | HTML con colores hardcodeados (no paleta) | 🟢 Baja |
| estate_ai_agent | OK tras refactor del mixin | ✅ |

---

## 4. Orden de ejecución recomendado

1. 🔴 **Flujo de venta unificado** (wizard → orden → factura → vendida → comisión) — el cambio de mayor impacto y el que pediste.
2. 🔴 **Bug de porcentajes** en reporte de ventas — rápido y muy visible.
3. 🟡 **Limpiar botones de venta redundantes** — coherencia.
4. 🟡 **Unificar/renombrar dashboards** — claridad.
5. 🟢 **Paleta en HTML del dashboard** — pulido visual.

---

## ✅ Implementación completada (2026-06-10)

| Item | Qué se hizo |
|------|-------------|
| **Flujo de venta unificado** (todo automático) | El wizard **"Vender Propiedad"** ahora: 1) crea y **confirma** la orden de venta (`sale.order`), 2) genera y **contabiliza** la factura (`account.move`), 3) marca la propiedad **Vendida**, 4) registra la **comisión**. Nuevo helper `_process_native_sale`. Cada venta queda en **Ventas y Facturación nativos** → los reportes cuadran. Si la factura falla, la propiedad NO se marca vendida (atómico). |
| **Limpieza de botones** | Quitado el botón suelto "Generar Factura" de la propiedad (una sola forma de vender). Re-anclado el xpath del botón de Ficha PDF. `action_create_sale_order` se conserva (lo usan las **ofertas**). |
| **Bug de porcentajes** | Campos cambiados a ratio 0-1; corregido en los **3 lugares**: vista (`widget="percentage"`), Excel (`0.00%`) y PDF (×100). 10000% → 100%, 3846% → 38.46%. |
| **Dashboards** | "KPIs y Métricas" → **"Dashboard Ejecutivo"** (gerencia: KPIs, Chart.js, filtros, IA, PDF). "Dashboard General" → **"Tablero Gráfico"** (vista nativa, todos). Roles claros, sin solapamiento. |
| **Paleta** | `_PALETTE` centralizada en el modelo del dashboard (espejo de `brand_palette.scss`), aplicada a los gráficos. Única fuente de verdad para colores. |

### Cómo probar el flujo de venta
1. Abre una propiedad **Disponible/Reservada** → botón **"Vender Propiedad"**.
2. Completa comprador, precio, comisión → **Confirmar Venta**.
3. Se abre la **factura contabilizada**. Verifica en:
   - **Ventas** → la orden confirmada vinculada a la propiedad.
   - **Facturación** → la factura publicada.
   - La propiedad queda **Vendida** con su comisión registrada.
